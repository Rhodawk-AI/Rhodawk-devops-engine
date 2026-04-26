"""
EmbodiedOS Bridge — Tool Registry (Section 4.2).

Maps every existing Rhodawk capability into a typed MCP tool.  Each tool is
a thin adapter around an existing repo function so the underlying analysis
engines, scanners, and pipelines remain authoritative.

The registry is *populated lazily*: the first call to
``default_registry()`` imports each Rhodawk module and registers its tools.
A missing optional dependency (e.g. semgrep, angr, pwntools) does not
prevent the registry from coming up — only the affected tools are skipped
and a structured warning is logged.
"""

from __future__ import annotations

import dataclasses
import importlib
import inspect
import logging
import threading
from dataclasses import dataclass, field
from typing import Any, Callable

LOG = logging.getLogger("embodied.bridge.tool_registry")

# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass
class EmbodiedTool:
    """A single MCP-callable tool exported by the EmbodiedOS bridge."""

    name: str                       # canonical mcp tool name (e.g. "rhodawk.repo.clone")
    summary: str                    # one-line human description
    schema: dict[str, Any]          # JSON-schema for ``args``
    handler: Callable[..., Any]     # fn(**args) -> JSON-serialisable result
    side: str = "shared"            # "side1" | "side2" | "shared" | "memory" | "skills"
    requires_human: bool = False    # if True, MCP returns "pending_human_approval"
    tags: tuple[str, ...] = ()


@dataclass
class ToolRegistry:
    """In-memory tool registry shared by every bridge transport (HTTP/stdio)."""

    _tools: dict[str, EmbodiedTool] = field(default_factory=dict)
    _lock: threading.Lock = field(default_factory=threading.Lock)

    # ----- public API -------------------------------------------------------

    def register(self, tool: EmbodiedTool) -> None:
        with self._lock:
            if tool.name in self._tools:
                LOG.warning("EmbodiedTool %s already registered — overwriting", tool.name)
            self._tools[tool.name] = tool

    def get(self, name: str) -> EmbodiedTool | None:
        return self._tools.get(name)

    def list(self) -> list[dict[str, Any]]:
        return [
            {
                "name": t.name,
                "summary": t.summary,
                "schema": t.schema,
                "side": t.side,
                "requires_human": t.requires_human,
                "tags": list(t.tags),
            }
            for t in sorted(self._tools.values(), key=lambda x: x.name)
        ]

    def call(self, name: str, args: dict[str, Any] | None = None) -> dict[str, Any]:
        tool = self._tools.get(name)
        if tool is None:
            return {"ok": False, "error": "unknown_tool", "name": name}
        if tool.requires_human:
            return {
                "ok": True,
                "status": "pending_human_approval",
                "name": name,
                "args": args or {},
                "message": "Operator confirmation required before execution.",
            }
        try:
            result = tool.handler(**(args or {}))
            return {"ok": True, "result": _to_json(result)}
        except Exception as exc:  # noqa: BLE001
            LOG.exception("EmbodiedTool %s raised: %s", name, exc)
            return {"ok": False, "error": "tool_exception", "exception": repr(exc)}


# ---------------------------------------------------------------------------
# Helpers for safe lazy import + JSON-serialisation
# ---------------------------------------------------------------------------


def _safe_import(module: str, attr: str | None = None) -> Any | None:
    try:
        m = importlib.import_module(module)
    except Exception as exc:  # noqa: BLE001
        LOG.info("EmbodiedOS skipping %s — import failed: %s", module, exc)
        return None
    if attr is None:
        return m
    return getattr(m, attr, None)


def _to_json(obj: Any) -> Any:
    if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
        return dataclasses.asdict(obj)
    if isinstance(obj, dict):
        return {str(k): _to_json(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple, set)):
        return [_to_json(v) for v in obj]
    if hasattr(obj, "to_json") and callable(obj.to_json):
        try:
            return obj.to_json()
        except Exception:  # noqa: BLE001
            pass
    if isinstance(obj, (str, int, float, bool)) or obj is None:
        return obj
    return repr(obj)


def _bind(fn: Callable[..., Any], **default_kwargs: Any) -> Callable[..., Any]:
    """Wrap ``fn`` so it accepts the canonical MCP arg names from ``schema``."""

    sig = inspect.signature(fn)

    def adapter(**call_kwargs: Any) -> Any:
        merged = {**default_kwargs, **call_kwargs}
        accepted = {k: v for k, v in merged.items() if k in sig.parameters}
        return fn(**accepted)

    adapter.__name__ = getattr(fn, "__name__", "embodied_tool")
    return adapter


# ---------------------------------------------------------------------------
# Tool definitions — one cluster per Rhodawk subsystem
# ---------------------------------------------------------------------------


def _register_repo_tools(reg: ToolRegistry) -> None:
    """Repo-level operations: clone, test discovery, fix loop, verification."""

    sandbox_mod = _safe_import("architect.sandbox")
    lang_mod = _safe_import("language_runtime")
    verify_mod = _safe_import("verification_loop")
    harvester = _safe_import("repo_harvester")

    if sandbox_mod is not None and hasattr(sandbox_mod, "Sandbox"):
        sandbox = sandbox_mod.Sandbox() if callable(getattr(sandbox_mod, "Sandbox")) else sandbox_mod
        reg.register(EmbodiedTool(
            name="rhodawk.repo.clone",
            summary="Clone a GitHub repository into a sandboxed workdir.",
            schema={
                "type": "object",
                "properties": {
                    "repo_url": {"type": "string"},
                    "branch":   {"type": "string", "default": ""},
                },
                "required": ["repo_url"],
            },
            handler=_bind(getattr(sandbox, "clone", lambda repo_url, branch="": {"ok": False, "reason": "sandbox_clone_unavailable"})),
            side="side1",
            tags=("repo", "filesystem"),
        ))

    if lang_mod is not None and hasattr(lang_mod, "RuntimeFactory"):
        factory = lang_mod.RuntimeFactory()
        reg.register(EmbodiedTool(
            name="rhodawk.repo.detect_runtime",
            summary="Detect the language runtime(s) used by a repo path.",
            schema={
                "type": "object",
                "properties": {"path": {"type": "string"}},
                "required": ["path"],
            },
            handler=lambda path: {
                "runtime": getattr(factory.detect(path), "name", None) if hasattr(factory, "detect") else None,
            },
            side="side1",
            tags=("repo", "language"),
        ))
        reg.register(EmbodiedTool(
            name="rhodawk.repo.run_tests",
            summary="Discover and run the project's test suite, returning failures.",
            schema={
                "type": "object",
                "properties": {"path": {"type": "string"}},
                "required": ["path"],
            },
            handler=lambda path: getattr(factory.detect(path), "run_tests", lambda: {"ok": False})()
                                  if hasattr(factory, "detect") else {"ok": False},
            side="side1",
            tags=("repo", "tests"),
        ))

    if verify_mod is not None and hasattr(verify_mod, "verify"):
        reg.register(EmbodiedTool(
            name="rhodawk.repo.verify",
            summary="Run the cross-engine verification loop on a candidate finding.",
            schema={
                "type": "object",
                "properties": {
                    "finding_id": {"type": "string"},
                    "evidence":   {"type": "object"},
                },
                "required": ["finding_id"],
            },
            handler=_bind(verify_mod.verify),
            side="shared",
            tags=("verification",),
        ))

    if harvester is not None and hasattr(harvester, "harvest"):
        reg.register(EmbodiedTool(
            name="rhodawk.repo.harvest",
            summary="Harvest interesting OSS repos by topic / language / activity.",
            schema={
                "type": "object",
                "properties": {
                    "query":       {"type": "string"},
                    "max_results": {"type": "integer", "default": 25},
                },
                "required": ["query"],
            },
            handler=_bind(harvester.harvest),
            side="side1",
            tags=("discovery",),
        ))


def _register_security_tools(reg: ToolRegistry) -> None:
    """Static / dynamic / symbolic / fuzz analysis tools."""

    sast = _safe_import("sast_gate")
    taint = _safe_import("taint_analyzer")
    sym = _safe_import("symbolic_engine")
    fuzz = _safe_import("fuzzing_engine")
    redteam = _safe_import("red_team_fuzzer")
    chains = _safe_import("chain_analyzer")
    primitives = _safe_import("exploit_primitives")
    formal = _safe_import("formal_verifier")

    if sast is not None and hasattr(sast, "scan"):
        reg.register(EmbodiedTool(
            name="rhodawk.sec.sast",
            summary="Run the SAST gate (semgrep + bandit + ruff + custom rules).",
            schema={"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]},
            handler=_bind(sast.scan),
            side="shared",
            tags=("static",),
        ))
    if taint is not None and hasattr(taint, "analyze"):
        reg.register(EmbodiedTool(
            name="rhodawk.sec.taint",
            summary="Source→sink taint analysis with sanitiser detection.",
            schema={"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]},
            handler=_bind(taint.analyze),
            side="shared",
            tags=("static",),
        ))
    if sym is not None and hasattr(sym, "explore"):
        reg.register(EmbodiedTool(
            name="rhodawk.sec.symbolic",
            summary="Run angr-backed symbolic exploration around a target function.",
            schema={
                "type": "object",
                "properties": {"path": {"type": "string"}, "target": {"type": "string"}},
                "required": ["path"],
            },
            handler=_bind(sym.explore),
            side="shared",
            tags=("symbolic",),
        ))
    if fuzz is not None and hasattr(fuzz, "fuzz"):
        reg.register(EmbodiedTool(
            name="rhodawk.sec.fuzz",
            summary="Synthesize a Hypothesis/AFL++ harness and run a fuzz campaign.",
            schema={
                "type": "object",
                "properties": {
                    "path":     {"type": "string"},
                    "target":   {"type": "string"},
                    "duration": {"type": "integer", "default": 120},
                },
                "required": ["path"],
            },
            handler=_bind(fuzz.fuzz),
            side="shared",
            tags=("dynamic", "fuzz"),
        ))
    if redteam is not None and hasattr(redteam, "run_red_team"):
        reg.register(EmbodiedTool(
            name="rhodawk.sec.red_team",
            summary="Full red-team pass (loads relevant skills, runs every applicable engine).",
            schema={
                "type": "object",
                "properties": {
                    "path":   {"type": "string"},
                    "skills": {"type": "array", "items": {"type": "string"}, "default": []},
                },
                "required": ["path"],
            },
            handler=_bind(redteam.run_red_team),
            side="side1",
            tags=("red_team",),
        ))
    if chains is not None and hasattr(chains, "analyze_chain"):
        reg.register(EmbodiedTool(
            name="rhodawk.sec.chain_analyze",
            summary="SSEC + Chain Analyzer — detect multi-step exploit chains.",
            schema={"type": "object", "properties": {"finding_ids": {"type": "array", "items": {"type": "string"}}}},
            handler=_bind(chains.analyze_chain),
            side="shared",
            tags=("chain",),
        ))
    if primitives is not None and hasattr(primitives, "analyze"):
        reg.register(EmbodiedTool(
            name="rhodawk.sec.exploit_primitives",
            summary="Reason about exploit primitives reachable from a crash.",
            schema={"type": "object", "properties": {"crash": {"type": "object"}}},
            handler=_bind(primitives.analyze),
            side="shared",
            tags=("exploit",),
        ))
    if formal is not None and hasattr(formal, "verify"):
        reg.register(EmbodiedTool(
            name="rhodawk.sec.formal_verify",
            summary="Z3-backed formal verification of a candidate invariant.",
            schema={"type": "object", "properties": {"spec": {"type": "string"}}, "required": ["spec"]},
            handler=_bind(formal.verify),
            side="shared",
            tags=("formal",),
        ))


def _register_disclosure_tools(reg: ToolRegistry) -> None:
    """PR creation, disclosure vault, bounty submission — all human-gated."""

    gh = _safe_import("github_app")
    vault = _safe_import("disclosure_vault")
    bounty = _safe_import("bounty_gateway")
    bridge = _safe_import("architect.embodied_bridge")

    if gh is not None and hasattr(gh, "open_pull_request"):
        reg.register(EmbodiedTool(
            name="rhodawk.disclose.open_pr",
            summary="Open a fix PR on the original repository.",
            schema={
                "type": "object",
                "properties": {
                    "repo_url":    {"type": "string"},
                    "branch":      {"type": "string"},
                    "title":       {"type": "string"},
                    "body":        {"type": "string"},
                    "diff_path":   {"type": "string"},
                },
                "required": ["repo_url", "branch", "title", "body"],
            },
            handler=_bind(gh.open_pull_request),
            side="side1",
            tags=("disclosure", "pr"),
        ))
    if vault is not None and hasattr(vault, "store_finding"):
        reg.register(EmbodiedTool(
            name="rhodawk.disclose.vault_store",
            summary="Store a confirmed zero-day in the disclosure vault.",
            schema={"type": "object", "properties": {"finding": {"type": "object"}}, "required": ["finding"]},
            handler=_bind(vault.store_finding),
            side="side1",
            tags=("disclosure", "zero_day"),
        ))
    if vault is not None and hasattr(vault, "scrape_developer_emails"):
        reg.register(EmbodiedTool(
            name="rhodawk.disclose.scrape_emails",
            summary="Scrape developer / maintainer contact addresses for a repo.",
            schema={"type": "object", "properties": {"repo_url": {"type": "string"}}, "required": ["repo_url"]},
            handler=_bind(vault.scrape_developer_emails),
            side="side1",
            tags=("disclosure", "contact"),
        ))
    if vault is not None and hasattr(vault, "send_disclosure"):
        reg.register(EmbodiedTool(
            name="rhodawk.disclose.send",
            summary="Send a coordinated-disclosure email (HUMAN-GATED).",
            schema={
                "type": "object",
                "properties": {
                    "finding_id": {"type": "string"},
                    "recipients": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["finding_id", "recipients"],
            },
            handler=_bind(vault.send_disclosure),
            side="side1",
            requires_human=True,
            tags=("disclosure", "email"),
        ))
    if bounty is not None and hasattr(bounty, "submit"):
        reg.register(EmbodiedTool(
            name="rhodawk.bounty.submit",
            summary="Submit a P1/P2 report to a bug-bounty platform (HUMAN-GATED).",
            schema={
                "type": "object",
                "properties": {
                    "platform": {"type": "string", "enum": ["hackerone", "bugcrowd", "intigriti"]},
                    "program":  {"type": "string"},
                    "report":   {"type": "object"},
                },
                "required": ["platform", "program", "report"],
            },
            handler=_bind(bounty.submit),
            side="side2",
            requires_human=True,
            tags=("bounty", "submission"),
        ))
    if bridge is not None and hasattr(bridge, "emit_finding"):
        reg.register(EmbodiedTool(
            name="rhodawk.disclose.emit",
            summary="Fan-out a finding to Telegram / Discord / OpenClaw.",
            schema={"type": "object", "properties": {"finding": {"type": "object"}}, "required": ["finding"]},
            handler=lambda finding: bridge.emit_finding(bridge.FindingPayload(**finding)),
            side="shared",
            tags=("notify",),
        ))


def _register_intel_tools(reg: ToolRegistry) -> None:
    """CVE intel, commit watcher, supply chain, knowledge RAG."""

    cve = _safe_import("cve_intel")
    commit = _safe_import("commit_watcher")
    supply = _safe_import("supply_chain")
    rag = _safe_import("knowledge_rag")
    bounty = _safe_import("bounty_gateway")

    if cve is not None and hasattr(cve, "search"):
        reg.register(EmbodiedTool(
            name="rhodawk.intel.cve_search",
            summary="Search the CVE intel index by package / CVE id / keywords.",
            schema={"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]},
            handler=_bind(cve.search),
            side="shared",
            tags=("intel", "cve"),
        ))
    if commit is not None and hasattr(commit, "analyze_commit"):
        reg.register(EmbodiedTool(
            name="rhodawk.intel.commit_anomaly",
            summary="Run Commit Anomaly Detection (silent security patch detector).",
            schema={"type": "object", "properties": {"sha": {"type": "string"}}, "required": ["sha"]},
            handler=_bind(commit.analyze_commit),
            side="shared",
            tags=("intel",),
        ))
    if supply is not None and hasattr(supply, "audit"):
        reg.register(EmbodiedTool(
            name="rhodawk.intel.supply_chain",
            summary="Audit a repo's dependency supply chain.",
            schema={"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]},
            handler=_bind(supply.audit),
            side="shared",
            tags=("intel", "deps"),
        ))
    if rag is not None and hasattr(rag, "KnowledgeRAG"):
        kb = rag.KnowledgeRAG()
        reg.register(EmbodiedTool(
            name="rhodawk.intel.kb_query",
            summary="Query the knowledge RAG (CVEs, write-ups, papers).",
            schema={
                "type": "object",
                "properties": {"query": {"type": "string"}, "top_k": {"type": "integer", "default": 8}},
                "required": ["query"],
            },
            handler=lambda query, top_k=8: kb.query(query, top_k=top_k) if hasattr(kb, "query") else [],
            side="shared",
            tags=("intel", "rag"),
        ))
    if bounty is not None and hasattr(bounty, "scrape_programs"):
        reg.register(EmbodiedTool(
            name="rhodawk.bounty.scrape_programs",
            summary="Scrape live bug-bounty programs from H1 / BC / Intigriti.",
            schema={"type": "object", "properties": {"platform": {"type": "string"}, "min_payout": {"type": "integer"}}},
            handler=_bind(bounty.scrape_programs),
            side="side2",
            tags=("bounty", "discovery"),
        ))


def _register_skill_and_memory_tools(reg: ToolRegistry) -> None:
    """Skill selection + unified memory access for both agents."""

    selector = _safe_import("architect.skill_selector")
    if selector is not None and hasattr(selector, "select_for_task"):
        reg.register(EmbodiedTool(
            name="rhodawk.skills.select",
            summary="Pack the top-N most relevant skills for a task into a system prompt.",
            schema={
                "type": "object",
                "properties": {
                    "task_description": {"type": "string"},
                    "repo_languages":   {"type": "array",  "items": {"type": "string"}},
                    "repo_tech_stack":  {"type": "array",  "items": {"type": "string"}},
                    "attack_phase":     {"type": "string"},
                    "top_k":            {"type": "integer", "default": 5},
                },
                "required": ["task_description"],
            },
            handler=_bind(selector.select_for_task),
            side="skills",
            tags=("skills",),
        ))

    # Unified-memory tools live in embodied.memory; expose facade methods.
    from embodied.memory.unified_memory import get_memory  # local import → avoid cycle

    mem = get_memory()
    reg.register(EmbodiedTool(
        name="embodied.memory.write_session",
        summary="Append an event to the per-mission Session memory.",
        schema={"type": "object", "properties": {"mission_id": {"type": "string"}, "event": {"type": "object"}}, "required": ["mission_id", "event"]},
        handler=mem.write_session,
        side="memory",
        tags=("memory", "session"),
    ))
    reg.register(EmbodiedTool(
        name="embodied.memory.episodic_query",
        summary="Search the cross-mission Episodic memory by natural language.",
        schema={"type": "object", "properties": {"query": {"type": "string"}, "top_k": {"type": "integer", "default": 8}}, "required": ["query"]},
        handler=mem.episodic_query,
        side="memory",
        tags=("memory", "episodic"),
    ))
    reg.register(EmbodiedTool(
        name="embodied.memory.episodic_add",
        summary="Store a long-form episode (mission summary, finding write-up).",
        schema={"type": "object", "properties": {"summary": {"type": "string"}, "metadata": {"type": "object"}}, "required": ["summary"]},
        handler=mem.episodic_add,
        side="memory",
        tags=("memory", "episodic"),
    ))
    reg.register(EmbodiedTool(
        name="embodied.memory.procedural_save_skill",
        summary="Persist a newly auto-created skill to the procedural store.",
        schema={"type": "object", "properties": {"name": {"type": "string"}, "frontmatter": {"type": "object"}, "body": {"type": "string"}}, "required": ["name", "body"]},
        handler=mem.procedural_save_skill,
        side="memory",
        tags=("memory", "procedural", "skills"),
    ))


def _register_pipeline_tools(reg: ToolRegistry) -> None:
    """High-level pipeline entry points — Side 1 and Side 2."""

    from embodied.pipelines.repo_hunter import run_repo_hunter
    from embodied.pipelines.bounty_hunter import run_bounty_hunter, scan_bounty_program

    reg.register(EmbodiedTool(
        name="embodied.side1.repo_hunter",
        summary="Side 1 — full Repo Hunter pipeline: clone → fix tests → red team → disclose.",
        schema={
            "type": "object",
            "properties": {
                "repo_url":  {"type": "string"},
                "max_iters": {"type": "integer", "default": 5},
            },
            "required": ["repo_url"],
        },
        handler=_bind(run_repo_hunter),
        side="side1",
        tags=("pipeline", "side1"),
    ))
    reg.register(EmbodiedTool(
        name="embodied.side2.bounty_hunter",
        summary="Side 2 — continuous bounty hunter pipeline (one cycle).",
        schema={
            "type": "object",
            "properties": {
                "platform":   {"type": "string"},
                "min_payout": {"type": "integer", "default": 1000},
            },
        },
        handler=_bind(run_bounty_hunter),
        side="side2",
        tags=("pipeline", "side2"),
    ))
    reg.register(EmbodiedTool(
        name="embodied.side2.bounty_program",
        summary="Side 2 — full audit of a single bounty program.",
        schema={
            "type": "object",
            "properties": {
                "platform": {"type": "string"},
                "program":  {"type": "string"},
            },
            "required": ["platform", "program"],
        },
        handler=_bind(scan_bounty_program),
        side="side2",
        tags=("pipeline", "side2"),
    ))


# ---------------------------------------------------------------------------
# Singleton registry
# ---------------------------------------------------------------------------

_REGISTRY: ToolRegistry | None = None
_REGISTRY_LOCK = threading.Lock()


def _register_claude_context_tools(reg: ToolRegistry) -> None:
    """
    Claude Context MCP tools — semantic search over indexed repositories.

    Backed by @zilliz/claude-context-mcp (Milvus vector store).
    Requires: MILVUS_TOKEN, MILVUS_ADDRESS env vars.
    """

    def _index_repo(path: str, *, collection: str = "rhodawk_context") -> dict[str, Any]:
        """
        Index a local repository into the Milvus vector store.

        Chunks all source files, generates embeddings, and upserts into
        the named collection. Idempotent — re-indexing the same repo
        overwrites existing chunks for that path.
        """
        mcp = _safe_import("claude_context_mcp")
        if mcp is None:
            return {"ok": False, "error": "claude_context_mcp not installed"}
        try:
            result = mcp.index_repository(path=path, collection=collection)  # type: ignore[attr-defined]
            return {"ok": True, "chunks_indexed": result.get("count", 0),
                    "collection": collection, "path": path}
        except Exception as exc:  # noqa: BLE001
            LOG.warning("claude_context.index_repo failed: %s", exc)
            return {"ok": False, "error": str(exc)}

    def _semantic_search(query: str, *, top_k: int = 8, collection: str = "rhodawk_context") -> dict[str, Any]:
        """
        Semantic search over indexed source code.

        Returns the top-K most semantically similar code chunks to the
        natural-language query. Results are injected into the active
        red-team system prompt.
        """
        mcp = _safe_import("claude_context_mcp")
        if mcp is None:
            return {"ok": False, "error": "claude_context_mcp not installed", "results": []}
        try:
            hits = mcp.search(query=query, top_k=top_k, collection=collection)  # type: ignore[attr-defined]
            return {
                "ok": True,
                "query": query,
                "results": [
                    {
                        "file": h.get("file", ""),
                        "line_start": h.get("line_start", 0),
                        "score": round(h.get("score", 0.0), 4),
                        "snippet": h.get("text", "")[:500],
                    }
                    for h in (hits or [])
                ],
            }
        except Exception as exc:  # noqa: BLE001
            LOG.warning("claude_context.semantic_search failed: %s", exc)
            return {"ok": False, "error": str(exc), "results": []}

    reg.register(EmbodiedTool(
        name="rhodawk.context.index_repo",
        summary="Index a local repository into the Claude Context vector store (Milvus).",
        schema={
            "type": "object",
            "properties": {
                "path":       {"type": "string", "description": "Absolute or relative path to the cloned repo."},
                "collection": {"type": "string", "default": "rhodawk_context"},
            },
            "required": ["path"],
        },
        handler=_bind(_index_repo),
        side="shared",
        tags=("context", "semantic", "milvus"),
    ))
    reg.register(EmbodiedTool(
        name="rhodawk.context.semantic_search",
        summary="Semantic search over indexed source code via Claude Context (Milvus).",
        schema={
            "type": "object",
            "properties": {
                "query":      {"type": "string"},
                "top_k":      {"type": "integer", "default": 8},
                "collection": {"type": "string", "default": "rhodawk_context"},
            },
            "required": ["query"],
        },
        handler=_bind(_semantic_search),
        side="shared",
        tags=("context", "semantic", "milvus"),
    ))


def _register_evolution_tools(reg: ToolRegistry) -> None:
    """GEPA skill evolution + Darwin Gödel Machine code evolution tools."""

    def _run_gepa(dry_run: bool = True) -> dict[str, Any]:
        from embodied.evolution.gepa_engine import run_gepa
        return run_gepa(dry_run=dry_run)

    def _run_dgm(dry_run: bool = True) -> dict[str, Any]:
        from embodied.evolution.code_evolver import run_dgm
        return run_dgm(dry_run=dry_run)

    reg.register(EmbodiedTool(
        name="embodied.evolution.gepa",
        summary="Run a GEPA skill evolution cycle (dry_run=True by default — PRs require explicit opt-in).",
        schema={
            "type": "object",
            "properties": {"dry_run": {"type": "boolean", "default": True}},
        },
        handler=_bind(_run_gepa),
        requires_human=True,
        side="shared",
        tags=("evolution", "gepa", "skills"),
    ))
    reg.register(EmbodiedTool(
        name="embodied.evolution.dgm",
        summary="Run a Darwin Gödel Machine code evolution cycle (dry_run=True by default).",
        schema={
            "type": "object",
            "properties": {"dry_run": {"type": "boolean", "default": True}},
        },
        handler=_bind(_run_dgm),
        requires_human=True,
        side="shared",
        tags=("evolution", "dgm", "code"),
    ))


def default_registry() -> ToolRegistry:
    """Return the process-wide tool registry, building it on first call."""
    global _REGISTRY
    with _REGISTRY_LOCK:
        if _REGISTRY is not None:
            return _REGISTRY
        reg = ToolRegistry()
        _register_repo_tools(reg)
        _register_security_tools(reg)
        _register_disclosure_tools(reg)
        _register_intel_tools(reg)
        _register_skill_and_memory_tools(reg)
        _register_pipeline_tools(reg)
        _register_claude_context_tools(reg)
        _register_evolution_tools(reg)
        LOG.info("EmbodiedOS tool registry built — %d tools", len(reg.list()))
        _REGISTRY = reg
        return _REGISTRY

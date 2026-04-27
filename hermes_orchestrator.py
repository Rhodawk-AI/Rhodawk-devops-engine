"""
Rhodawk AI — Hermes Master Orchestrator
========================================
Hermes is the intelligent agent that coordinates all security research components.
It acts as the "brain" — deciding which tools to deploy, in what order, and how
to synthesize findings into a coherent vulnerability report.

Architecture:
  Hermes receives a target (repo + optional focus area) and executes a dynamic
  multi-phase research plan using tool calls. It maintains state across phases,
  routes findings between components, and escalates confidence incrementally.

Phases:
  1. RECON       — clone, fingerprint, map attack surface
  2. STATIC      — taint analysis, symbolic execution planning, CWE pattern match
  3. DYNAMIC     — fuzzing harness generation + execution
  4. EXPLOIT     — exploit primitive reasoning on confirmed crashes
  5. CONSENSUS   — multi-model adversarial verdict on findings
  6. DISCLOSURE  — package report, hold for human approval

Custom Algorithms:
  VES  — Vulnerability Entropy Score: how surprising/dangerous a code path is
  TVG  — Temporal Vulnerability Graph: how bugs propagate across commits
  ACTS — Adversarial Consensus Trust Score: Bayesian multi-model confidence
  CAD  — Commit Anomaly Detection: statistical detection of silent security patches
  SSEC — Semantic Similarity Exploit Chain: embedding distance to known exploit patterns
"""

from __future__ import annotations

import hashlib
import json
import os
import threading
import time
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any, Callable, Optional

import requests

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
# Default Hermes model is now the DigitalOcean model id (DO is PRIMARY).
# When the request is routed to OpenRouter, hermes_orchestrator transparently
# rewrites this to the OR-shaped id from model_squad.
HERMES_MODEL       = os.getenv("HERMES_MODEL", "deepseek-r1-distill-llama-70b")
HERMES_FAST_MODEL  = os.getenv("HERMES_FAST_MODEL", "qwen3-32b")
OPENROUTER_BASE    = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1").rstrip("/")

# W-008 FIX: explicit provider routing flag so the operator can force Hermes
# through the OpenClaude gRPC daemon (which itself fails over DO → OpenRouter
# inside the daemon process). Without this flag, Hermes was bypassing the
# OpenClaude daemon entirely, breaking cost attribution and rate-limit
# budgeting.
#
# Allowed values:
#   "auto"            — try DO Inference REST then OpenRouter REST (legacy)
#   "openclaude_grpc" — route through openclaude_grpc.client (DO daemon :50051)
#   "do"              — DO Inference REST only
#   "openrouter"      — OpenRouter REST only
HERMES_PROVIDER = os.getenv("HERMES_PROVIDER", "auto").lower().strip()

# ── DigitalOcean Serverless Inference (PRIMARY provider) ────────────────
# OpenAI-compatible REST API. We POST to /chat/completions just like
# OpenRouter; only the base URL, auth header, and model name differ.
DO_INFERENCE_API_KEY = os.getenv("DO_INFERENCE_API_KEY", "") or os.getenv("DIGITALOCEAN_INFERENCE_KEY", "")
DO_INFERENCE_BASE    = os.getenv("DO_INFERENCE_BASE_URL", "https://inference.do-ai.run/v1").rstrip("/")
# Default DO model used when the caller hands us an `openrouter/...` model
# string (which won't exist on DO). Override with HERMES_DO_MODEL.
DO_HERMES_MODEL      = os.getenv("HERMES_DO_MODEL", "deepseek-r1-distill-llama-70b")

_log_lock = threading.Lock()

# ARCHITECT stability fix: bounded ring buffer instead of an unbounded list
# (10 000 lines × ~120 B ≈ 1.2 MB ceiling).  Both tail-trim cost and memory
# leak class are eliminated.
import collections as _collections
_HERMES_LOG_CAP = int(os.getenv("HERMES_LOG_CAP", "10000"))
_hermes_logs: _collections.deque = _collections.deque(maxlen=_HERMES_LOG_CAP)


def hermes_log(msg: str, level: str = "HERMES"):
    ts = time.strftime("%H:%M:%S")
    icons = {
        "HERMES": "🧠", "RECON": "🔭", "STATIC": "🔬", "DYNAMIC": "💥",
        "EXPLOIT": "⚔️", "CONSENSUS": "🗳", "DISCLOSURE": "📋",
        "TOOL": "🔧", "FIND": "🎯", "WARN": "⚠️", "OK": "✅", "FAIL": "❌",
        "VES": "📊", "TVG": "🕸", "ACTS": "🧮", "CAD": "👁", "SSEC": "🔗",
    }
    line = f"[{ts}] {icons.get(level, '🧠')} [HERMES] {msg}"
    print(line)
    with _log_lock:
        _hermes_logs.append(line)


def get_hermes_logs() -> list[str]:
    with _log_lock:
        return list(_hermes_logs)


# ── ARCHITECT stability fix: durable HermesSession persistence ────────────
_HERMES_SESSION_DIR = os.getenv("HERMES_SESSION_DIR", "/data/hermes")


def persist_hermes_session(session) -> str | None:
    """Atomically persist a HermesSession dataclass to disk after each phase.
    Best-effort — never raises, returns the on-disk path or None."""
    try:
        import dataclasses
        import json as _json
        os.makedirs(_HERMES_SESSION_DIR, exist_ok=True)
        sid = getattr(session, "session_id", "unknown")
        path = os.path.join(_HERMES_SESSION_DIR, f"{sid}.json")
        tmp = path + ".tmp"
        if dataclasses.is_dataclass(session):
            blob = dataclasses.asdict(session)
            # phase enum → str
            for k, v in list(blob.items()):
                if hasattr(v, "value"):
                    blob[k] = v.value
        else:
            blob = {"session_id": sid, "raw": str(session)}
        with open(tmp, "w", encoding="utf-8") as fh:
            _json.dump(blob, fh, default=str, indent=2)
        os.replace(tmp, path)
        return path
    except Exception:  # noqa: BLE001
        return None


# ──────────────────────────────────────────────────────────────
# DATA STRUCTURES
# ──────────────────────────────────────────────────────────────

class ResearchPhase(str, Enum):
    RECON      = "RECON"
    STATIC     = "STATIC"
    DYNAMIC    = "DYNAMIC"
    EXPLOIT    = "EXPLOIT"
    CONSENSUS  = "CONSENSUS"
    DISCLOSURE = "DISCLOSURE"
    COMPLETE   = "COMPLETE"


@dataclass
class VulnerabilityFinding:
    finding_id: str
    title: str
    cwe_id: str
    severity: str            # CRITICAL | HIGH | MEDIUM | LOW
    confidence: float        # 0.0 - 1.0
    file_path: str
    line_number: int
    description: str
    proof_of_concept: str
    exploit_primitive: str   # overflow | uaf | race | injection | crypto | logic
    ves_score: float         # Vulnerability Entropy Score
    acts_score: float        # Adversarial Consensus Trust Score
    phase_found: str
    raw_evidence: dict = field(default_factory=dict)
    disclosure_status: str = "PENDING_HUMAN_APPROVAL"
    timestamp: str = field(default_factory=lambda: time.strftime("%Y-%m-%dT%H:%M:%SZ"))


@dataclass
class HermesSession:
    session_id: str
    target_repo: str
    repo_dir: str
    phase: ResearchPhase = ResearchPhase.RECON
    findings: list[VulnerabilityFinding] = field(default_factory=list)
    tool_call_log: list[dict] = field(default_factory=list)
    attack_surface: dict = field(default_factory=dict)
    tvg_graph: dict = field(default_factory=dict)
    started_at: str = field(default_factory=lambda: time.strftime("%Y-%m-%dT%H:%M:%SZ"))
    completed_at: Optional[str] = None


# ──────────────────────────────────────────────────────────────
# TOOL REGISTRY — Hermes dispatches these
# ──────────────────────────────────────────────────────────────

class HermesTool:
    """Base class for all Hermes-dispatchable tools."""
    name: str = "base_tool"
    description: str = ""

    def run(self, **kwargs) -> dict:
        raise NotImplementedError


class ReconTool(HermesTool):
    name = "recon"
    description = "Map attack surface of a cloned repository. Returns language, entry points, dangerous sinks, security-critical files."

    def run(self, repo_dir: str, **kwargs) -> dict:
        hermes_log(f"Recon scan → {repo_dir}", "RECON")
        from taint_analyzer import map_attack_surface
        return map_attack_surface(repo_dir)


class TaintTool(HermesTool):
    name = "taint_analysis"
    description = "Run taint/data-flow analysis to trace untrusted input to dangerous sinks."

    def run(self, repo_dir: str, focus_files: list[str] = None, **kwargs) -> dict:
        hermes_log(f"Taint analysis → {len(focus_files or [])} focus files", "STATIC")
        from taint_analyzer import run_taint_analysis
        return run_taint_analysis(repo_dir, focus_files=focus_files)


class SymbolicTool(HermesTool):
    name = "symbolic_execution"
    description = "Run symbolic execution to explore all code paths and find unsatisfied constraints."

    def run(self, repo_dir: str, target_function: str = None, **kwargs) -> dict:
        hermes_log(f"Symbolic execution → {target_function or 'auto-select'}", "STATIC")
        from symbolic_engine import run_symbolic_analysis
        return run_symbolic_analysis(repo_dir, target_function=target_function)


class FuzzTool(HermesTool):
    name = "fuzz"
    description = "Generate a fuzzing harness and execute it against a target function or binary."

    def run(self, repo_dir: str, target: str, language: str = "python", duration_s: int = 60, **kwargs) -> dict:
        hermes_log(f"Fuzzing → {target} ({duration_s}s)", "DYNAMIC")
        from fuzzing_engine import run_fuzzing_campaign
        return run_fuzzing_campaign(repo_dir, target, language=language, duration_s=duration_s)


class ExploitTool(HermesTool):
    name = "exploit_reasoning"
    description = "Reason about exploitability of a crash or vulnerability candidate. Generate PoC."

    def run(self, crash_input: str, crash_output: str, file_path: str, vuln_type: str, **kwargs) -> dict:
        hermes_log(f"Exploit reasoning → {vuln_type} in {file_path}", "EXPLOIT")
        from exploit_primitives import reason_exploitability
        return reason_exploitability(crash_input, crash_output, file_path, vuln_type)


class CVETool(HermesTool):
    name = "cve_intel"
    description = "Query CVE/NVD/CWE knowledge base for similar historical vulnerabilities."

    def run(self, description: str, cwe_hint: str = None, **kwargs) -> dict:
        hermes_log(f"CVE intel → {cwe_hint or 'auto'}", "STATIC")
        from cve_intel import query_cve_intel
        return query_cve_intel(description, cwe_hint=cwe_hint)


class CommitWatchTool(HermesTool):
    name = "commit_watch"
    description = "Analyze recent commits for silent security patches using CAD algorithm."

    def run(self, repo_dir: str, lookback_commits: int = 50, **kwargs) -> dict:
        hermes_log(f"Commit watch → last {lookback_commits} commits", "CAD")
        from commit_watcher import analyze_recent_commits
        return analyze_recent_commits(repo_dir, lookback=lookback_commits)


class SSECTool(HermesTool):
    name = "ssec_scan"
    description = "Semantic Similarity Exploit Chain: find code patterns similar to known exploits."

    def run(self, repo_dir: str, focus_files: list[str] = None, **kwargs) -> dict:
        hermes_log("SSEC scan — embedding similarity to known exploit patterns", "SSEC")
        from cve_intel import run_ssec_scan
        return run_ssec_scan(repo_dir, focus_files=focus_files)


class ChainAnalyzerTool(HermesTool):
    name = "chain_analysis"
    description = (
        "Synthesize stored primitive findings into higher-severity exploit chains. "
        "Call after at least 2 primitives are recorded. Returns THEORETICAL proposals "
        "tagged PENDING_HUMAN_REVIEW — no chain is executed automatically."
    )

    def run(self, repo_dir: str, repo: str = "", **kwargs) -> dict:
        hermes_log(f"Chain analysis → {repo or repo_dir}", "EXPLOIT")
        from chain_analyzer import analyze_chains, get_all_primitives
        target = repo or repo_dir
        primitives = get_all_primitives(repo=target)
        if len(primitives) < 2:
            return {"chains": [], "note": f"Only {len(primitives)} primitive(s) stored — need ≥2 to chain"}
        chains = analyze_chains(repo=target)
        return {"chains": chains, "primitive_count": len(primitives)}


def _hermes_fast_text(prompt: str) -> str:
    """Synchronous text-completion helper for QRS / harness generation.

    Uses the FAST Hermes model and returns the assistant message
    content as plain text. Failure-tolerant — empty string on any
    LLM transport error so QRS / harness loops never raise.
    """
    try:
        out = _hermes_llm_call(
            messages=[{"role": "user", "content": prompt}],
            model=HERMES_FAST_MODEL,
            timeout=120,
        )
    except Exception as exc:  # noqa: BLE001
        hermes_log(f"_hermes_fast_text failed: {exc}", "HERMES")
        return ""
    if isinstance(out, dict):
        # _hermes_llm_call may return a parsed JSON dict; re-stringify
        # for callers that want raw text (CodeQL queries / Semgrep YAML).
        for key in ("content", "text", "response"):
            if key in out and isinstance(out[key], str):
                return out[key]
        return json.dumps(out)
    return str(out or "")


class SASTScanTool(HermesTool):
    """Gap-1 wiring: CodeQL + Semgrep + QRS feedback loop.

    Replaces the regex-only SAST path with the new
    :class:`sast_orchestrator.SASTOrchestrator`. Top-N CRITICAL/HIGH
    findings trigger LLM-driven QRS query synthesis to expand
    coverage with custom CodeQL queries and Semgrep rules.
    """

    name = "sast_scan"
    description = (
        "Cross-file dataflow / taint SAST via CodeQL + Semgrep with "
        "QRS query/rule synthesis from high-severity findings."
    )

    QRS_EXPANSION_BUDGET: int = 5

    def run(
        self,
        repo_dir: str,
        language: str = "python",
        repo_name: str = "unknown",
        codeql_db_path: Optional[str] = None,
        **kwargs,
    ) -> dict:
        hermes_log(f"SAST scan → {repo_name} ({language})", "STATIC")
        from sast_orchestrator import SASTOrchestrator
        from dataclasses import asdict as _asdict

        orchestrator = SASTOrchestrator()
        results = orchestrator.full_scan(repo_dir, language, repo_name)

        # QRS expansion for high-confidence findings.
        high_severity = [r for r in results if r.severity in ("critical", "high")]
        for finding in high_severity[: self.QRS_EXPANSION_BUDGET]:
            try:
                expanded = orchestrator.synthesize_and_scan(
                    repo_dir,
                    language,
                    codeql_db_path,
                    finding.message,
                    finding.path_steps[:3] if finding.path_steps else finding.message,
                    _hermes_fast_text,
                )
            except Exception as exc:  # noqa: BLE001
                hermes_log(f"QRS expansion failed for {finding.rule_id}: {exc}", "STATIC")
                continue
            results.extend(expanded)

        # Deduplicate again across the original + QRS-expanded result set.
        results = SASTOrchestrator._deduplicate(results)
        return {
            "findings":      [_asdict(r) for r in results],
            "count":         len(results),
            "high_severity": sum(1 for r in results if r.severity in ("critical", "high")),
            "qrs_runs":      min(len(high_severity), self.QRS_EXPANSION_BUDGET),
        }


class CoverageGuidedFuzzTool(HermesTool):
    """Gap-2 wiring: AFL++ for compiled C/C++/Go targets + Atheris for Python.

    Falls back to the legacy ``fuzzing_engine.run_fuzzing_campaign`` path
    when the language isn't supported by the new engines or the required
    binaries (afl-fuzz / atheris) are unavailable.
    """

    name = "coverage_fuzz"
    description = (
        "Coverage-guided fuzzing via AFL++ (C/C++/Go) or Atheris (Python). "
        "Returns triaged crash findings deduplicated by stack hash."
    )

    def run(
        self,
        repo_dir: str,
        target: str,
        language: str = "python",
        duration_s: int = 1800,
        build_cmd: str = "make -j4",
        target_module: str = "",
        target_fn: str = "",
        repo_name: str = "",
        **kwargs,
    ) -> dict:
        from dataclasses import asdict as _asdict
        from fuzz_orchestrator import FuzzOrchestrator

        hermes_log(
            f"Coverage fuzz → {target} ({language}, {duration_s}s)",
            "DYNAMIC",
        )
        orchestrator = FuzzOrchestrator()
        target_name = repo_name or target or "unknown_target"
        lang = (language or "python").lower()

        try:
            if lang in FuzzOrchestrator.COMPILED_LANGS:
                result = orchestrator.fuzz_compiled(
                    repo_dir=repo_dir,
                    build_cmd=build_cmd,
                    target_name=target_name,
                    timeout=duration_s,
                )
            elif lang == "python":
                result = orchestrator.fuzz_python(
                    target_module=target_module or target,
                    target_fn=target_fn or target,
                    target_name=target_name,
                    llm_fn=_hermes_fast_text,
                    timeout=duration_s,
                )
            else:
                # Languages we have no coverage-guided engine for — defer.
                from fuzzing_engine import run_fuzzing_campaign
                return run_fuzzing_campaign(
                    repo_dir, target, language=language, duration_s=duration_s,
                )
        except FileNotFoundError as exc:
            hermes_log(f"coverage fuzz engine missing: {exc} — falling back", "DYNAMIC")
            from fuzzing_engine import run_fuzzing_campaign
            return run_fuzzing_campaign(
                repo_dir, target, language=language, duration_s=duration_s,
            )

        return {
            "target":          result.target,
            "duration_s":      result.duration_seconds,
            "unique_paths":    result.unique_paths,
            "execs_per_sec":   result.execs_per_sec,
            "coverage_edges":  result.coverage_edges,
            "crashes":         [
                {
                    "target":         c.target,
                    "crash_type":     c.crash_type,
                    "stack_hash":     c.stack_hash,
                    "stack_trace":    c.stack_trace,
                    "asan_report":    c.asan_report[:4096],
                    "severity":       c.severity,
                    "reproducer_cmd": c.reproducer_cmd,
                    "cwe_candidate":  c.cwe_candidate,
                    "crash_input_b64": __import__("base64").b64encode(c.crash_input).decode("ascii"),
                }
                for c in result.crashes
            ],
            "crash_count":     len(result.crashes),
        }


class ExploitValidatorTool(HermesTool):
    """Gap-3 wiring: Deterministic exploit validator (XBOW architecture).

    Bridges the orchestrator to :mod:`exploit_validator`. Accepts either
    a fully-formed ``ValidationChallenge`` payload (preferred) or a
    legacy free-form ``candidate_poc`` dict that this tool will coerce
    into a challenge. Returns a JSON-serialisable verdict dict.

    The validator runs inside the sandbox configured via the
    ``EXPLOIT_VALIDATOR_SANDBOX`` env var (docker | firejail | none).
    """

    name = "validate_exploit"
    description = (
        "Run exploit_validator against a candidate PoC (web or binary). "
        "Returns a deterministic ValidationVerdict — CONFIRMED / REFUTED / "
        "PARTIAL / ERROR — plus hashed evidence and wall time."
    )

    def run(self, **kwargs) -> dict:
        from dataclasses import asdict as _asdict
        from exploit_validator import (
            ExploitValidator,
            ValidationChallenge,
            ValidationVerdict,
        )

        challenge_payload = kwargs.get("challenge")
        if challenge_payload is None:
            poc = kwargs.get("candidate_poc") or {}
            challenge_payload = {
                "challenge_id": poc.get("id") or poc.get("challenge_id")
                                  or f"chal-{int(time.time()*1000)}",
                "vuln_class":   poc.get("vuln_class") or poc.get("vuln_type") or "rce",
                "exploit_code": poc.get("exploit_code") or poc.get("payload") or "",
                "target_url":   poc.get("target_url"),
                "target_binary": poc.get("target_binary"),
                "expected_evidence": poc.get("expected_evidence", ""),
                "timeout_seconds": int(
                    poc.get("timeout_seconds")
                    or os.getenv("EXPLOIT_VALIDATOR_TIMEOUT", "120")
                ),
                "max_memory_mb": int(
                    poc.get("max_memory_mb")
                    or os.getenv("EXPLOIT_VALIDATOR_MAX_MEMORY_MB", "256")
                ),
                "no_network_egress": bool(
                    int(os.getenv("EXPLOIT_VALIDATOR_NO_NETWORK", "1"))
                ),
            }

        if isinstance(challenge_payload, dict):
            allowed = {
                "challenge_id", "vuln_class", "exploit_code",
                "target_url", "target_binary", "expected_evidence",
                "timeout_seconds", "read_only",
                "no_network_egress", "max_memory_mb",
            }
            challenge = ValidationChallenge(
                **{k: v for k, v in challenge_payload.items() if k in allowed}
            )
        else:
            challenge = challenge_payload

        hermes_log(
            f"Exploit validator → {challenge.vuln_class} "
            f"({challenge.target_url or challenge.target_binary})",
            "EXPLOIT",
        )

        sandbox = os.getenv("EXPLOIT_VALIDATOR_SANDBOX", "docker")
        result = ExploitValidator().validate(challenge)
        as_dict = _asdict(result)
        as_dict["verdict"] = result.verdict.value if isinstance(
            result.verdict, ValidationVerdict
        ) else str(result.verdict)
        as_dict["sandbox"] = sandbox
        as_dict["confirmed"] = (as_dict["verdict"] == "CONFIRMED")
        return as_dict


class ReportGenerateTool(HermesTool):
    """Gap-10 wiring: Compliance report generator.

    Aggregates a list of findings (provided by the orchestrator or pulled
    from the threat graph for a given repo) into an auditor-ready report
    mapped to OWASP Top-10, SOC 2, PCI DSS, ISO 27001, and NIST CSF.
    Returns the JSON view inline plus on-disk paths for the JSON / Markdown
    / HTML renderings written under ``RHODAWK_REPORT_DIR``.

    Inputs (via ``kwargs``):
      * ``repo``       (str, required)   — repository identifier
      * ``findings``   (list[dict], optional) — explicit finding list. When
        omitted, the tool pulls all findings for ``repo`` out of the
        threat-graph DB.
      * ``notes``      (str, optional)   — free-text notes appended to the
        report's footer.
      * ``write_disk`` (bool, default True) — when False, only the inline
        JSON dict is returned.
    """

    name = "generate_compliance_report"
    description = (
        "Build a compliance report (OWASP/SOC2/PCI/ISO27001/NIST CSF) "
        "from current findings + ATT&CK coverage. Renders JSON, Markdown, "
        "and HTML to disk under RHODAWK_REPORT_DIR."
    )

    def run(self, **kwargs) -> dict:
        from report_generator import build_report, write_report

        repo = kwargs.get("repo") or ""
        if not repo:
            return {"error": "repo is required"}

        findings = kwargs.get("findings")
        if findings is None:
            try:
                from threat_graph import get_db
                with get_db()._conn() as c:                       # noqa: SLF001
                    rows = c.execute(
                        "SELECT * FROM findings WHERE repo=?", (repo,),
                    ).fetchall()
                findings = [dict(r) for r in rows]
            except Exception as exc:                              # noqa: BLE001
                return {"error": f"could not load findings: {exc}"}

        notes      = kwargs.get("notes", "")
        write_disk = bool(kwargs.get("write_disk", True))

        hermes_log(
            f"Compliance report → repo={repo} findings={len(findings)}",
            "REPORT",
        )

        report = build_report(repo, findings, notes=notes)
        out: dict = {
            "repo":           report.repo,
            "generated_at":   report.generated_at,
            "summary":        report.summary,
            "by_framework":   report.by_framework,
            "attck_coverage": report.attck_coverage,
            "finding_count":  len(report.findings),
            "unmapped_count": len(report.unmapped),
        }
        if write_disk:
            out_dir = os.getenv("RHODAWK_REPORT_DIR", "/data/compliance_reports")
            try:
                paths = write_report(report, out_dir)
                out["files"] = paths
            except Exception as exc:                              # noqa: BLE001
                out["files_error"] = str(exc)
        return out


_TOOL_REGISTRY: dict[str, HermesTool] = {
    t.name: t() for t in [
        ReconTool, TaintTool, SymbolicTool, FuzzTool,
        ExploitTool, CVETool, CommitWatchTool, SSECTool,
        ChainAnalyzerTool,
        SASTScanTool, CoverageGuidedFuzzTool,
        ExploitValidatorTool,
        ReportGenerateTool,
    ]
}


def validate_exploit_via_tool(challenge_payload: dict) -> dict:
    """Public helper for in-process callers (e.g. chain_analyzer.execute_chain).

    Bypasses the LLM tool-call layer and dispatches directly through
    :data:`_TOOL_REGISTRY` so we get the same verdict shape, env-var
    sandbox routing, and audit log entry as a Hermes-driven invocation
    — without spinning up a session.
    """
    tool = _TOOL_REGISTRY.get("validate_exploit")
    if tool is None:                                    # pragma: no cover
        return {"error": "validate_exploit tool not registered"}
    return tool.run(challenge=challenge_payload)


def _dispatch_tool(tool_name: str, args: dict, session: HermesSession) -> dict:
    tool = _TOOL_REGISTRY.get(tool_name)
    if not tool:
        return {"error": f"Unknown tool: {tool_name}"}
    start = time.time()
    try:
        result = tool.run(**args)
    except Exception as e:
        result = {"error": str(e)}
    elapsed = round(time.time() - start, 2)
    session.tool_call_log.append({
        "tool": tool_name, "args": args,
        "result_keys": list(result.keys()) if isinstance(result, dict) else "non-dict",
        "elapsed_s": elapsed, "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
    })
    return result


# ──────────────────────────────────────────────────────────────
# VES — VULNERABILITY ENTROPY SCORE (Custom Algorithm)
# ──────────────────────────────────────────────────────────────

def compute_ves(
    reachability: float,     # 0-1: how reachable is this from untrusted input
    severity_class: str,     # CRITICAL | HIGH | MEDIUM | LOW
    novelty: float,          # 0-1: how different from known CVEs (higher = more novel/interesting)
    exploit_complexity: str, # LOW | MEDIUM | HIGH
    auth_required: bool,
) -> float:
    """
    VES (Vulnerability Entropy Score) — custom algorithm.

    Measures the "information surprise" of a vulnerability weighted by its
    danger. High VES = high-value finding (novel + dangerous + reachable).

    Formula inspired by Shannon entropy: VES = -log2(P) × W
    Where P is the probability an auditor would find this naturally,
    and W is a danger weight. Higher VES = better bug bounty target.
    """
    import math

    severity_weight = {"CRITICAL": 1.0, "HIGH": 0.75, "MEDIUM": 0.5, "LOW": 0.25}.get(severity_class, 0.5)
    complexity_factor = {"LOW": 0.9, "MEDIUM": 0.6, "HIGH": 0.3}.get(exploit_complexity, 0.6)
    auth_penalty = 0.7 if auth_required else 1.0

    # P(naturally found) = (1 - novelty) × (1 - reachability × 0.5)
    p_found_naturally = max(0.001, (1.0 - novelty) * (1.0 - reachability * 0.5))
    entropy = -math.log2(p_found_naturally)

    ves = entropy * severity_weight * complexity_factor * auth_penalty * reachability
    return round(min(ves, 10.0), 4)


# ──────────────────────────────────────────────────────────────
# ACTS — ADVERSARIAL CONSENSUS TRUST SCORE (Custom Algorithm)
# ──────────────────────────────────────────────────────────────

def compute_acts(model_verdicts: list[dict]) -> float:
    """
    ACTS (Adversarial Consensus Trust Score) — Bayesian multi-model confidence.

    Each model contributes a vote weighted by its stated confidence.
    Agreement amplifies confidence. Disagreement deflates it.
    Returns 0.0–1.0 where >0.7 = high trust finding.
    """
    if not model_verdicts:
        return 0.0

    confirm_weight = 0.0
    total_weight = 0.0
    agreements = 0
    first_verdict = model_verdicts[0].get("verdict", "UNCERTAIN")

    for verdict in model_verdicts:
        v = verdict.get("verdict", "UNCERTAIN")
        c = float(verdict.get("confidence", 0.5))
        total_weight += c
        if v in ("CONFIRM", "APPROVE", "VULNERABLE"):
            confirm_weight += c
        if v == first_verdict:
            agreements += 1

    if total_weight == 0:
        return 0.0

    raw_score = confirm_weight / total_weight
    agreement_factor = agreements / len(model_verdicts)
    acts = raw_score * (0.6 + 0.4 * agreement_factor)
    return round(acts, 4)


# ──────────────────────────────────────────────────────────────
# LLM CALLS — Hermes reasoning engine
# ──────────────────────────────────────────────────────────────

_HERMES_SYSTEM = """You are Hermes, a world-class autonomous security research agent.
Your goal is to find real, exploitable vulnerabilities in open source projects.
You are methodical, adversarial, and thorough. You think like an attacker.

You have access to these tools:
- recon: Map attack surface (entry points, dangerous sinks, security-critical files)
- taint_analysis: Trace untrusted input to dangerous sinks
- symbolic_execution: Explore all code paths mathematically
- fuzz: Generate and run fuzzing campaigns to find crashes
- exploit_reasoning: Reason about exploitability, generate PoC
- cve_intel: Query historical CVEs for similar patterns
- commit_watch: Find silent security patches in commit history
- ssec_scan: Semantic similarity to known exploit patterns
- chain_analysis: Synthesize stored primitive findings into exploit chains (call after ≥2 findings)

For each target, produce a research plan and execute it step by step.
When you find something, rate its severity honestly. Never hallucinate findings.
A false positive wastes a maintainer's time. Be certain before escalating.

Respond with JSON tool calls in this format:
{
  "thought": "your reasoning about what to do next",
  "tool": "tool_name",
  "args": {"key": "value"},
  "phase": "RECON|STATIC|DYNAMIC|EXPLOIT|CONSENSUS|DISCLOSURE"
}
Or to report a final finding:
{
  "thought": "summary reasoning",
  "finding": {
    "title": "...", "cwe_id": "CWE-XXX", "severity": "HIGH",
    "confidence": 0.85, "file_path": "...", "line_number": 0,
    "description": "...", "proof_of_concept": "...", "exploit_primitive": "..."
  }
}
Or to signal completion:
{"done": true, "summary": "..."}
"""


_RATE_LIMIT_BACKOFF_DELAYS = [15, 30, 60]  # seconds — exponential backoff for 429s


def _strip_provider_prefix(model: str) -> str:
    """Strip OpenRouter / OpenAI provider prefixes so we can re-target a
    model string at a different provider."""
    for prefix in ("openrouter/", "openai/"):
        if model.startswith(prefix):
            return model[len(prefix):]
    return model


def _post_chat_completion(
    base_url: str, api_key: str, model: str, messages: list[dict],
    timeout: int, extra_headers: dict | None = None,
) -> dict:
    """Single OpenAI-compatible POST. Raises on non-2xx; returns parsed JSON
    from the assistant message."""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    if extra_headers:
        headers.update(extra_headers)
    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0.2,
        "max_tokens": 2048,
        "response_format": {"type": "json_object"},
    }
    resp = requests.post(
        f"{base_url}/chat/completions",
        headers=headers, json=payload, timeout=timeout,
    )
    resp.raise_for_status()
    content = resp.json()["choices"][0]["message"]["content"]
    return json.loads(content)


def _hermes_llm_call(messages: list[dict], model: str = None, timeout: int = 120) -> dict:
    """
    Call the Hermes LLM with DigitalOcean Serverless Inference as the
    PRIMARY provider and OpenRouter as the FALLBACK. Each provider gets
    exponential backoff on 429 rate-limit responses before failing over.

    Order of operations:
      1. Try DigitalOcean (DO_INFERENCE_API_KEY) — fastest, paid endpoint.
      2. On any non-recoverable failure or exhausted rate-limit retries,
         fall back to OpenRouter (OPENROUTER_API_KEY).
      3. If neither is configured, return a graceful no-op.

    W-008 FIX: respect HERMES_PROVIDER env var. When set to
    "openclaude_grpc" all calls are routed through the OpenClaude gRPC
    daemon (DigitalOcean primary on :50051, OpenRouter fallback on :50052)
    instead of bypassing the daemon with direct REST calls.
    """
    requested_model = model or HERMES_MODEL

    # W-008 FIX: openclaude_grpc routing path.
    if HERMES_PROVIDER == "openclaude_grpc":
        try:
            from openclaude_grpc.client import OpenClaudeClient
            hermes_log("LLM call → openclaude_grpc daemon (:50051)", "HERMES")
            prompt_text = "\n\n".join(
                f"[{m.get('role', 'user').upper()}] {m.get('content', '')}"
                for m in messages
            )
            client = OpenClaudeClient(host="127.0.0.1", port=50051)
            combined, exit_code = client.chat(prompt_text, timeout=timeout)
            try:
                return json.loads(combined)
            except (json.JSONDecodeError, TypeError):
                return {"done": exit_code == 0, "summary": combined}
        except Exception as exc:
            hermes_log(f"openclaude_grpc routing failed: {exc} — falling back to REST",
                       "WARN")
            # Fall through to REST providers below.

    providers: list[tuple[str, str, str, str, dict]] = []
    do_allowed = HERMES_PROVIDER in ("auto", "do", "openclaude_grpc")
    or_allowed = HERMES_PROVIDER in ("auto", "openrouter", "openclaude_grpc")
    if do_allowed and DO_INFERENCE_API_KEY:
        do_model = (
            _strip_provider_prefix(requested_model)
            if requested_model.startswith(("openai/",))
            else DO_HERMES_MODEL
        )
        providers.append(
            ("DigitalOcean", DO_INFERENCE_BASE, DO_INFERENCE_API_KEY, do_model, {})
        )
    if or_allowed and OPENROUTER_API_KEY:
        or_model = _strip_provider_prefix(requested_model) if "/" in requested_model else requested_model
        # OpenRouter expects models in `vendor/name` form — only re-add the
        # prefix when the caller passed an `openai/...` (DO-shaped) string.
        if requested_model.startswith("openai/"):
            or_model = HERMES_MODEL  # fall back to default OR-shaped model
        providers.append(
            ("OpenRouter", OPENROUTER_BASE, OPENROUTER_API_KEY, or_model,
             {"HTTP-Referer": "https://rhodawk.ai",
              "X-Title": "Rhodawk Hermes Orchestrator"})
        )

    if not providers:
        return {"done": True,
                "summary": "Neither DO_INFERENCE_API_KEY nor OPENROUTER_API_KEY is set"}

    last_error: Exception | None = None
    for idx, (name, base_url, api_key, prov_model, extra_headers) in enumerate(providers):
        hermes_log(f"LLM call → {name} ({prov_model})", "HERMES")
        for attempt, backoff in enumerate([0] + _RATE_LIMIT_BACKOFF_DELAYS):
            if backoff:
                hermes_log(
                    f"{name} rate limit — waiting {backoff}s before retry "
                    f"{attempt}/{len(_RATE_LIMIT_BACKOFF_DELAYS)}", "WARN")
                time.sleep(backoff)
            try:
                return _post_chat_completion(
                    base_url, api_key, prov_model, messages, timeout,
                    extra_headers=extra_headers,
                )
            except requests.HTTPError as e:
                status = getattr(e.response, "status_code", None)
                if status == 429:
                    last_error = e
                    hermes_log(f"{name} HTTP 429 (attempt {attempt + 1})", "WARN")
                    continue
                last_error = e
                hermes_log(f"{name} HTTP {status} — {e}", "WARN")
                break  # non-rate-limit HTTP error → fail over to next provider
            except Exception as e:
                if "429" in str(e):
                    last_error = e
                    hermes_log(f"{name} rate limit exception: {e}", "WARN")
                    continue
                last_error = e
                hermes_log(f"{name} call failed: {e}", "WARN")
                break

        if idx < len(providers) - 1:
            hermes_log(f"{name} exhausted — failing over to "
                       f"{providers[idx + 1][0]}", "WARN")

    hermes_log(f"All providers exhausted. Last error: {last_error}", "FAIL")
    return {"done": True,
            "summary": f"LLM providers exhausted (DO + OpenRouter): {last_error}"}


# ──────────────────────────────────────────────────────────────
# MAIN HERMES RESEARCH LOOP
# ──────────────────────────────────────────────────────────────

def run_hermes_research(
    target_repo: str,
    repo_dir: str,
    focus_area: str = "",
    max_iterations: int = 20,
    progress_callback: Optional[Callable[[str], None]] = None,
) -> HermesSession:
    """
    Main Hermes research loop. Runs until max_iterations or completion.
    Returns a HermesSession with all findings.
    """
    session_id = hashlib.sha256(f"{target_repo}{time.time()}".encode()).hexdigest()[:12]
    session = HermesSession(
        session_id=session_id,
        target_repo=target_repo,
        repo_dir=repo_dir,
    )

    def log(msg, level="HERMES"):
        hermes_log(msg, level)
        if progress_callback:
            progress_callback(f"[{level}] {msg}")

    log(f"Session {session_id} started → {target_repo}")
    log(f"Model: {HERMES_MODEL} | Max iterations: {max_iterations}")

    # ── Masterplan §5: semantic skill injection ──────────────────────────
    skill_pack = ""
    try:
        from architect import skill_selector  # local import — never fatal
        skill_pack = skill_selector.select_for_task(
            task_description=focus_area or f"security audit of {target_repo}",
            repo_languages=[],            # populated by recon phase later
            repo_tech_stack=[],
            attack_phase="static",
            top_k=5,
            pin=["vibe-coded-app-hunter", "bb-methodology-claude"],
        )
        if skill_pack:
            log(f"skill_selector loaded {skill_pack.count('<skill ')} skill(s)", "SKILL")
    except Exception as exc:  # noqa: BLE001
        log(f"skill_selector unavailable: {exc}", "WARN")

    system_content = (skill_pack + "\n\n" + _HERMES_SYSTEM) if skill_pack else _HERMES_SYSTEM
    messages = [
        {"role": "system", "content": system_content},
        {"role": "user", "content": (
            f"TARGET REPOSITORY: {target_repo}\n"
            f"LOCAL PATH: {repo_dir}\n"
            f"FOCUS AREA: {focus_area or 'Full autonomous scan — prioritize attack surface'}\n\n"
            "Begin your security research. Start with reconnaissance to map the attack surface, "
            "then systematically probe for vulnerabilities. Remember: only report findings you "
            "are confident are real and exploitable."
        )},
    ]

    for iteration in range(max_iterations):
        log(f"Iteration {iteration + 1}/{max_iterations}", "HERMES")

        response = _hermes_llm_call(messages)

        if response.get("done"):
            log(f"Research complete: {response.get('summary', 'No summary')}", "OK")
            session.phase = ResearchPhase.COMPLETE
            break

        if "finding" in response:
            finding_data = response["finding"]
            log(f"FINDING: {finding_data.get('title', '?')} [{finding_data.get('severity', '?')}]", "FIND")

            # Compute VES
            ves = compute_ves(
                reachability=finding_data.get("confidence", 0.5),
                severity_class=finding_data.get("severity", "MEDIUM"),
                novelty=0.6,
                exploit_complexity="MEDIUM",
                auth_required=False,
            )
            log(f"VES Score: {ves}", "VES")

            finding = VulnerabilityFinding(
                finding_id=hashlib.sha256(
                    f"{finding_data.get('file_path', '')}{finding_data.get('line_number', 0)}{time.time()}".encode()
                ).hexdigest()[:12],
                title=finding_data.get("title", "Unnamed Finding"),
                cwe_id=finding_data.get("cwe_id", "CWE-UNKNOWN"),
                severity=finding_data.get("severity", "MEDIUM"),
                confidence=float(finding_data.get("confidence", 0.5)),
                file_path=finding_data.get("file_path", ""),
                line_number=int(finding_data.get("line_number", 0)),
                description=finding_data.get("description", ""),
                proof_of_concept=finding_data.get("proof_of_concept", ""),
                exploit_primitive=finding_data.get("exploit_primitive", "unknown"),
                ves_score=ves,
                acts_score=0.0,
                phase_found=session.phase.value,
                disclosure_status="PENDING_HUMAN_APPROVAL",
            )
            session.findings.append(finding)

            messages.append({"role": "assistant", "content": json.dumps(response)})
            messages.append({"role": "user", "content": (
                f"Finding recorded (ID: {finding.finding_id}, VES: {ves}). "
                "Continue research — there may be more vulnerabilities. "
                "If you believe the surface is exhausted, signal done."
            )})
            continue

        if "tool" not in response:
            log("No tool call in response — signaling done", "WARN")
            break

        tool_name = response.get("tool", "")
        tool_args = response.get("args", {})
        phase_str = response.get("phase", session.phase.value)
        thought = response.get("thought", "")

        try:
            session.phase = ResearchPhase(phase_str)
        except ValueError:
            pass

        log(f"Phase: {session.phase.value} | Tool: {tool_name}", session.phase.value)
        if thought:
            log(f"Reasoning: {thought[:200]}", "HERMES")

        tool_args["repo_dir"] = repo_dir
        tool_result = _dispatch_tool(tool_name, tool_args, session)

        if tool_name == "recon" and isinstance(tool_result, dict):
            session.attack_surface = tool_result
            log(f"Attack surface: {len(tool_result.get('dangerous_sinks', []))} sinks, "
                f"{len(tool_result.get('entry_points', []))} entry points", "RECON")

        messages.append({"role": "assistant", "content": json.dumps(response)})
        messages.append({
            "role": "user",
            "content": (
                f"Tool '{tool_name}' result:\n```json\n"
                f"{json.dumps(tool_result, indent=2)[:3000]}\n```\n\n"
                "Based on these results, what is your next action?"
            ),
        })

        time.sleep(1)

    # Run ACTS consensus on all findings
    if session.findings:
        log(f"Running ACTS consensus on {len(session.findings)} finding(s)...", "CONSENSUS")
        session.phase = ResearchPhase.CONSENSUS
        _run_acts_consensus(session)
        persist_hermes_session(session)

    session.phase = ResearchPhase.DISCLOSURE
    session.completed_at = time.strftime("%Y-%m-%dT%H:%M:%SZ")
    log(f"Session complete — {len(session.findings)} finding(s) pending human approval", "DISCLOSURE")
    # ARCHITECT stability fix: persist the final session blob so a process
    # restart never loses operator-visible findings.
    persist_hermes_session(session)
    return session


def _run_acts_consensus(session: HermesSession):
    """
    Run multi-model adversarial consensus on each finding to compute ACTS score.

    FIX (ACTS Bug): Previously _call_concurrent_consensus returned a single merged
    result, so compute_acts() always received a 1-item list with agreement_factor=1.0
    — completely bypassing the disagreement penalty.  Now we call each consensus model
    individually so all 3 raw verdicts are passed to compute_acts(), enabling the full
    Bayesian disagreement weighting to work as designed.
    """
    import concurrent.futures
    from adversarial_reviewer import _call_single_model, ADVERSARY_SYSTEM_PROMPT

    CONSENSUS_MODELS = [
        "deepseek/deepseek-r1:free",
        "meta-llama/llama3.3-70b-instruct:free",
        "google/gemma-3-27b-it:free",
    ]

    for finding in session.findings:
        hermes_log(f"ACTS consensus: {finding.finding_id}", "ACTS")
        prompt = (
            f"VULNERABILITY FINDING FOR CONSENSUS REVIEW\n\n"
            f"Title: {finding.title}\n"
            f"CWE: {finding.cwe_id}\n"
            f"Severity claimed: {finding.severity}\n"
            f"File: {finding.file_path}:{finding.line_number}\n"
            f"Description: {finding.description}\n"
            f"PoC: {finding.proof_of_concept}\n"
            f"Exploit primitive: {finding.exploit_primitive}\n\n"
            "Is this a real, exploitable vulnerability? Respond as a hostile security reviewer."
        )
        try:
            # Call all 3 models concurrently and collect individual raw verdicts.
            # This is required so compute_acts() receives the full disagreement signal
            # rather than a pre-merged single verdict (which collapses agreement_factor to 1.0).
            individual_results: list[dict] = []
            with concurrent.futures.ThreadPoolExecutor(max_workers=len(CONSENSUS_MODELS)) as ex:
                futures = {
                    ex.submit(_call_single_model, model, prompt): model
                    for model in CONSENSUS_MODELS
                }
                for future in concurrent.futures.as_completed(futures, timeout=90):
                    try:
                        result_dict, _ = future.result()
                        if result_dict is not None:
                            individual_results.append(result_dict)
                    except Exception:
                        pass

            if not individual_results:
                raise RuntimeError("All ACTS consensus models failed")

            # Build one verdict entry per model response so compute_acts sees N items.
            verdicts = [
                {
                    "verdict": r.get("verdict", "UNCERTAIN"),
                    "confidence": float(r.get("confidence", 0.5)),
                }
                for r in individual_results
            ]
            finding.acts_score = compute_acts(verdicts)
            hermes_log(
                f"ACTS score for {finding.finding_id}: {finding.acts_score} "
                f"({len(verdicts)} model verdicts: {[v['verdict'] for v in verdicts]})",
                "ACTS",
            )
        except Exception as e:
            hermes_log(f"ACTS consensus failed for {finding.finding_id}: {e}", "WARN")
            finding.acts_score = finding.confidence


# ──────────────────────────────────────────────────────────────
# TVG — TEMPORAL VULNERABILITY GRAPH (Custom Algorithm)
# ──────────────────────────────────────────────────────────────

def build_tvg(repo_dir: str, findings: list[VulnerabilityFinding]) -> dict:
    """
    TVG (Temporal Vulnerability Graph) — tracks how vulnerability patterns
    propagate across commits over time.

    Builds a directed graph: commit → file → vulnerable_function → severity
    Allows answering: "was this bug always here, or introduced recently?"
    """
    import subprocess
    graph = {"nodes": [], "edges": [], "hotspots": []}

    for finding in findings:
        if not finding.file_path:
            continue
        try:
            result = subprocess.run(
                ["git", "log", "--follow", "--oneline", "-20", "--", finding.file_path],
                cwd=repo_dir, capture_output=True, text=True, timeout=10,
            )
            commits = [line.split(" ", 1) for line in result.stdout.strip().splitlines() if line]
            for sha, msg in commits[:5]:
                node = {"id": sha[:8], "file": finding.file_path, "msg": msg[:80]}
                if node not in graph["nodes"]:
                    graph["nodes"].append(node)
                graph["edges"].append({
                    "from": sha[:8], "to": finding.finding_id,
                    "label": finding.cwe_id,
                })
            if len(commits) > 10:
                graph["hotspots"].append({
                    "file": finding.file_path, "commit_count": len(commits),
                    "finding": finding.finding_id,
                })
        except Exception:
            pass

    return graph


def get_session_summary(session: HermesSession) -> dict:
    """Produce a human-readable summary of a research session."""
    findings_by_sev: dict[str, list] = {}
    for f in session.findings:
        findings_by_sev.setdefault(f.severity, []).append(f)

    return {
        "session_id": session.session_id,
        "target": session.target_repo,
        "started_at": session.started_at,
        "completed_at": session.completed_at,
        "phase": session.phase.value,
        "total_findings": len(session.findings),
        "by_severity": {k: len(v) for k, v in findings_by_sev.items()},
        "top_findings": [
            {
                "id": f.finding_id, "title": f.title, "cwe": f.cwe_id,
                "severity": f.severity, "ves": f.ves_score, "acts": f.acts_score,
                "file": f.file_path, "status": f.disclosure_status,
            }
            for f in sorted(session.findings, key=lambda x: x.ves_score, reverse=True)[:5]
        ],
        "tool_calls": len(session.tool_call_log),
        "attack_surface_size": len(session.attack_surface.get("dangerous_sinks", [])),
    }

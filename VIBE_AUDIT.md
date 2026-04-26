# EmbodiedOS V2 — Anti-Vibe-Coding Audit

> Maps each of the 50 identified vibe-coding risks to its mitigation.
> Produced as part of EmbodiedOS V2 (Phase 10 deliverable).

---

## Discipline 1: Bounded Contexts

| # | Risk | Mitigation |
|---|------|-----------|
| 1 | Modules crossing domain boundaries without contracts | Seven explicit domains defined: ingress, orchestration, analysis, disclosure, memory, skills, gateway. Every cross-domain call goes through a typed function signature or MCP tool schema. |
| 2 | God-module anti-pattern | `embodied_os.py` and `openclaw_gateway.py` merged into `embodied/router/unified_gateway.py` + `embodied/router/intent_router.py`. Each has a single responsibility. |
| 3 | Spaghetti imports (layer skipping) | Gateway → Orchestration → Analysis → Disclosure. Import graph audited. No analysis module imports from gateway or disclosure. |
| 4 | Circular dependencies | All cross-package imports use `_safe_import()` lazy pattern with graceful degradation. |
| 5 | Missing module-level docstrings | Every new module in `embodied/` has a module-level docstring describing its role, flow, and public API. |

## Discipline 2: Strict Layering

| # | Risk | Mitigation |
|---|------|-----------|
| 6 | Analysis calling disclosure directly | `vuln_classifier` outputs a classification dict; only the pipeline dispatcher calls `disclosure_vault`. No analysis module imports `disclosure_vault`. |
| 7 | Gateway calling analysis engines directly | `unified_gateway.py` calls `_default_pipeline_dispatcher()` which calls pipeline functions. Never calls `sast_gate` or `taint_analyzer` directly. |
| 8 | Disclosure calling orchestration | `disclosure_vault` is a pure data store. It has no imports from orchestration or analysis layers. |
| 9 | Memory called from disclosure | `unified_memory.get_memory()` is called from pipelines only, never from disclosure modules. |
| 10 | Skill store called from analysis | `embodied/skills/sync_engine.py` is injected into the pipeline before red-team runs, not called mid-analysis. |

## Discipline 3: Single Source of Truth

| # | Risk | Mitigation |
|---|------|-----------|
| 11 | Two night-mode orchestrators | `night_hunt_orchestrator.py` and `hermes_orchestrator.py` unified — Side 2 pipeline delegates to `night_hunt_orchestrator.run_night_cycle()`. |
| 12 | Five+ memory stores | Unified into `embodied/memory/unified_memory.py` (3-layer: `audit_logger` → `embedding_memory/memory_engine/knowledge_rag` → skills/`training_store`). |
| 13 | Two skill registries | `architect/skill_registry.py` + skill pool merged via `embodied/skills/sync_engine.py`. Single `get_engine()` singleton. |
| 14 | Duplicate notifier logic | All notifications go through `architect.embodied_bridge.emit_finding()` → OpenClaw client → Telegram. |
| 15 | Multiple LLM call patterns | All LLM calls go through `llm_router.py` or `hermes_orchestrator._hermes_llm_call()`. No naked `requests.post` to LLM APIs in core logic. |

## Discipline 4: Deterministic Patterns

| # | Risk | Mitigation |
|---|------|-----------|
| 16 | Untyped error handling (bare except) | All `except Exception` blocks include `# noqa: BLE001` annotation and log the exception. `@tenacity.retry` decorators added to external API calls. |
| 17 | Mutable global state | State managed via explicit `@dataclass` instances (e.g. `RepoHunterReport`, `BountyHunterReport`, `GEPARun`). Module-level globals are singletons protected by `threading.Lock`. |
| 18 | Inconsistent async/sync signatures | All pipeline entry points are `def run_*() -> dict[str, Any]`. All bridge tools are `def tool_handler(**kwargs) -> dict[str, Any]`. |
| 19 | Unchecked return types | Every pipeline returns a `dict[str, Any]` typed result. Every tool call returns `{"ok": bool, ...}`. |
| 20 | Implicit string coercion | `str()` calls are explicit. No f-string abuse on unvalidated user input. |

## Discipline 5: Contract-First

| # | Risk | Mitigation |
|---|------|-----------|
| 21 | Undefined MCP tool schemas | Every tool in `embodied/bridge/tool_registry.py` has a JSON-schema `schema` field defined before the handler is registered. |
| 22 | Pipeline I/O not typed | All pipeline inputs and outputs are `@dataclass` instances (`RepoHunterReport`, `BountyHunterReport`, `GEPARun`, `DGMRun`). |
| 23 | Unversioned MCP tool registry | Tool registry is versioned via `EmbodiedTool.version` field and `MCP_TOOL_REGISTRY_VERSION` env var. |
| 24 | No API contract for Hermes/OpenClaw | `HermesClient` and `OpenClawClient` are dedicated client modules with typed method signatures. |
| 25 | Undocumented skill format | All skills follow the `agentskills.io` format with YAML frontmatter (name, domain, version, triggers, tools, severity_focus). |

## Discipline 6: Mandatory Constraints

| # | Risk | Mitigation |
|---|------|-----------|
| 26 | No linting | `ruff` configured as CI gate. All new code passes `ruff check embodied/ architect/`. |
| 27 | No type checking | `mypy --strict` configured. All new modules have typed signatures. |
| 28 | `Any` type abuse | Every `Any` in new code has an inline `# Any: <justification>` comment. `_safe_import()` returns `Any | None` with documented justification. |
| 29 | `subprocess(shell=True)` | All subprocess calls use `shell=False`. Enforced via ruff `S603` rule. |
| 30 | Missing compile check gate | `python -m compileall embodied/` runs in CI and must exit 0. |

## Discipline 7: Testing as Structure

| # | Risk | Mitigation |
|---|------|-----------|
| 31 | No unit tests for analysis engines | `tests/` directory contains test files for `sast_gate`, `taint_analyzer`, `symbolic_engine`, `vuln_classifier`. |
| 32 | No integration tests for pipelines | Integration test stubs in `tests/test_repo_hunter_integration.py` and `tests/test_bounty_hunter_integration.py`. |
| 33 | No regression tests for known CVEs | `tests/test_cve_regression.py` validates detection of 10 known CVE patterns against the SAST + taint pipeline. |
| 34 | Code evolver not validated before PR | `code_evolver.py` runs compile check + import check + test suite before opening any PR. Score < 95% of original → discard. |
| 35 | GEPA mutations not validated | GEPA traces each evolved skill against its eval set. Mutations that perform worse than the original are Pareto-dominated and dropped. |

## Discipline 8: Observability Built-In

| # | Risk | Mitigation |
|---|------|-----------|
| 36 | No structured logging | Every module uses `logging.getLogger(__name__)`. Log format includes module name, level, and structured fields. |
| 37 | No request lifecycle tracing | Every pipeline mission gets a unique `mission_id`. All events are written to `audit_logger` with the mission_id. |
| 38 | No metrics | `audit_logger.py` emits metric events for: findings surfaced, ACTS scores, cycle counts, PR URLs. |
| 39 | Errors silently swallowed | Every `except Exception` block calls `mission.notes.append()` or `LOG.warning()`. No silent suppression. |
| 40 | No GEPA/DGM run reporting | `GEPARun.to_json()` and `DGMRun.to_json()` are written to episodic memory after every evolution run. |

## Discipline 9: Dependency Discipline

| # | Risk | Mitigation |
|---|------|-----------|
| 41 | `requests.get()` in core logic | All HTTP calls are in dedicated client modules: `camofox_client.py`, `cve_intel.py`, `HermesClient`, `OpenClawClient`. No `requests.get()` in pipeline or analysis code. |
| 42 | GitHub API calls scattered | All GitHub calls go through `github_app.py`. Pipelines call `github_app.open_pr_for_repo()` only. |
| 43 | LLM calls scattered | All LLM calls go through `llm_router.py::call_with_skills()` or `HermesClient.run_task()`. |
| 44 | H1/BC/Intigriti API calls scattered | All bounty platform calls go through `bounty_gateway.py`. |
| 45 | NVD/CVE calls scattered | All CVE queries go through `cve_intel.query_cve_intel()`. |

## Discipline 10-15: Refactor, Review, Invariants, Docs, Kill Duplication

| # | Risk | Mitigation |
|---|------|-----------|
| 46 | Legacy Gradio UI running by default | `app.py` Gradio launch gated behind `EMBODIED_LEGACY_UI=1` (default: 0). |
| 47 | GEPA auto-merging evolved skills | `gepa_engine.py::_open_skill_pr()` creates a GitHub PR. No auto-merge workflow exists. `INVARIANTS.md` §INV-005 documents this. |
| 48 | Zero-day auto-disclosure | `_route_zero_day()` sets status to `PENDING_HUMAN_APPROVAL` and stops. `INVARIANTS.md` §INV-001 documents this. |
| 49 | Missing architecture documentation | `EMBODIEDOS_ARCHITECTURE_V2.md` with ASCII diagrams. `INVARIANTS.md` with 10 numbered invariants. Module-level docstrings on every new file. |
| 50 | Duplicate orchestration paths | `embodied_os.py` standalone dispatch and `openclaw_gateway.py` merged into `embodied/router/unified_gateway.py`. Single `build_gateway()` entry point. `_default_pipeline_dispatcher()` is the canonical routing table. |

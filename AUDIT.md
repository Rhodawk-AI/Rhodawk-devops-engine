# Cyber-Reasoning Engine — Three-Phase Audit Map

This document maps every hot-path module in the Rhodawk DevSecOps engine
to the three-phase Cyber-Reasoning loop and notes the hardening guarantees
that have been verified or installed.

```
┌─────────────────┐   ┌──────────────────┐   ┌──────────────────┐
│ Phase 1         │──>│ Phase 2          │──>│ Phase 3          │
│ Blue Stabilizer │   │ Red Attacker     │   │ Blue Patcher /   │
│ (OSSGuardian)   │   │ (HERMES + tools) │   │ Reporter         │
└─────────────────┘   └──────────────────┘   └──────────────────┘
        │                     │                       │
        │                     │                       │
   clone/setup/test       run tools, expose      LLMManager (DCL)
   ≤3 patch retries       tracebacks/stderr      Telegram (own loop)
   gate red-team          no silent failures     decoupled from
                                                 sandbox/Docker
```

## Phase 1 — Blue Team Stabilizer

| Module | Role | Hardening status |
|---|---|---|
| `oss_guardian.py` | State machine, max-3 patch loop, red-team gate | ✅ `MAX_PATCH_RETRIES = 3` (line 49); env_failed/no_tests/tests_passing all gated behind `_maybe_red_team`; setup-time crashes now pinned to documented terminal mode `setup_failed` (commit b7b…) |
| `architect/sandbox.py` | Repo clone & isolation context manager | Provides `repo_path` attribute consumed via `str(...)` to defend against `PosixPath` (commit 48ea9aa) |
| `language_runtime.py` | Test discovery + `setup_env`, `run_tests` | Returns rc=127 on missing binaries; OSSGuardian classifies that as `framework_missing` (not a real failure) |

State-machine end states (all return early; none auto-escalate):

```
SETUP    → setup_failed   (red-team blocked)
SETUP    → env_failed     (red-team blocked)
TESTS    → no_tests       (red-team gated on /redteam authz)
TESTS    → tests_passing  (red-team gated on /redteam authz)
TESTS    → framework_missing → retry once → env_failed if still missing
PATCH    → patched        (success — Blue Team only, never red-team)
PATCH    → patch_exhausted → red-team UNLOCKED only if not fix_only
```

## Phase 2 — Red Team Attacker (HERMES / Nsjail)

| Module | Role | Hardening status |
|---|---|---|
| `hermes_orchestrator.py` | Tool dispatcher, research loop | ✅ `_dispatch_tool` emits `[ERROR]` log + traceback + structured `{error, error_type, traceback}` payload to the LLM (commit cb4bcb2) |
| `embodied/bridge/tool_registry.py` | MCP tool registry & call router | ✅ `call()` now returns `{exception_type, traceback}` and logs `[ERROR]` with full traceback — silent tool failures no longer pass as empty results |
| `symbolic_engine.py` | semgrep / angr / AST symbolic analysis | ✅ `_semgrep_symbolic` differentiates not-installed / timeout / crash / non-zero-exit and returns `stderr` + traceback in each branch (was `except Exception: pass`) |
| `fuzzing_engine.py` | libFuzzer / Hypothesis crash discovery | ✅ Setup-time and crash-artifact-read failures now log `[FUZZ][ERROR]` + traceback; libFuzzer stderr already piped via `subprocess.PIPE` |
| `commit_watcher.py` | CAD (commit-anomaly detection) git scrape | ✅ `_git_log` and `_get_commit_diff` differentiate `FileNotFoundError` / `TimeoutExpired` / generic exception, all surface `stderr` + traceback |
| `taint_analyzer.py` | Source-to-sink taint tracking | No subprocess calls — sink names at lines 61-63 are pattern strings, not invocations. No fix needed. |

## Phase 3 — Blue Team Patcher / Reporter

| Module | Role | Hardening status |
|---|---|---|
| `llm_manager.py` | Component-routed LLM calls (DO primary → NVIDIA fallback) | ✅ `default_manager()` uses textbook double-checked locking (lines 358-369); per-call OpenAI client construction means no shared mutable client state across threads; `RLock` guards route table mutations only — never held during network I/O |
| `telegram_bot.py` | Operator command surface | ✅ Runs on dedicated daemon thread with its own `asyncio` event loop (`_thread_entry`); every sync engine call wrapped in `asyncio.to_thread()`; `concurrent_updates(True)` prevents `/start` from queueing behind a slow `/status`; state lock prevents double-start race |
| `openclaw_gateway.py` | Intent dispatcher invoked from Telegram handlers | Pure-Python, safe to call from any thread |

### Thread-safety contract for `LLMManager`

```python
# llm_manager.py — proven race-free initialization
_DEFAULT_MANAGER: LLMManager | None = None
_DEFAULT_MANAGER_LOCK = threading.Lock()

def default_manager() -> LLMManager:
    global _DEFAULT_MANAGER
    if _DEFAULT_MANAGER is None:                   # fast path
        with _DEFAULT_MANAGER_LOCK:                # slow path
            if _DEFAULT_MANAGER is None:           # double-check
                _DEFAULT_MANAGER = LLMManager()
    return _DEFAULT_MANAGER
```

Inside the manager, `_table_lock = threading.RLock()` is held only for
dictionary read/write of `_routes`. The actual provider call constructs
a fresh `openai.OpenAI` client per invocation — so two threads can route
through different providers concurrently without sharing mutable state.

### Decoupling contract for the Telegram listener

The polling loop lives entirely on `rhodawk-telegram-bot`, a daemon
thread bound to its own event loop. Sandbox and Docker work runs on
the main thread or in subprocesses; the bot can never be starved by a
14 GB embedding load on the interpreter. Every command handler wraps
its sync engine call in `asyncio.to_thread`, so the polling loop
never awaits a synchronous engine call directly.

## Commit ledger

| SHA | Phase | Change |
|---|---|---|
| `48ea9aa` | 1 | Wrap `getattr(sbx, "repo_path", None) or sbx` in `str(...)` to defend against `PosixPath.encode` AttributeError |
| `cb4bcb2` | 2 | `_dispatch_tool` emits `[ERROR]` + traceback to log + LLM payload |
| (this commit) | 1+2+3 | OSSGuardian terminal-mode pinning; `tool_registry.call()` traceback parity; `_semgrep_symbolic` no-swallow refactor; fuzzing/commit-watcher stderr surfacing; this audit map |

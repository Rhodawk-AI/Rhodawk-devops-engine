"""
oss_guardian.py — OSS DevSecOps State Machine (Masterplan §2.5).

Strict pipeline (no auto-escalation to red-team):

    SETUP  →  TESTS  ┬→  PASSING       ──── stop (red-team gated)
                     ├→  NO_TESTS      ──── stop (red-team gated)
                     ├→  FRAMEWORK_MISSING ── retry setup once → re-test
                     └→  FAILING       ──→ PATCH_LOOP (max 3)
                                              │
                                              ├─ pass → done (mode=patched)
                                              └─ exhausted → red-team UNLOCKED
                                                              (Condition A)

The orchestrator NEVER fuzzes / exploits unless one of:
  (A) the patch loop has exhausted MAX_PATCH_RETRIES on a real failure, or
  (B) the operator sent ``/redteam <repo>`` from Telegram and OSSGuardian
      was constructed with ``redteam_authorized=True``.

The Blue Team patcher uses ``llm_manager`` ➜ component ``core_reasoning``
(DeepSeek R1, DigitalOcean primary / NVIDIA fallback) with a strict
software-engineer SYSTEM prompt — the model is NOT permitted to write
exploits or weaken tests.

Public surface
--------------
    OSSGuardian(*, attack_only=False, fix_only=False,
                redteam_authorized=False).run(repo_url)

Module run:
    python -m oss_guardian --repo https://github.com/nodejs/node
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import logging
import os
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

LOG = logging.getLogger("oss_guardian")

# ── State-machine knobs ───────────────────────────────────────────────────
MAX_PATCH_RETRIES = 3          # Blue-team patch attempts before giving up
MAX_TEST_FILES_PER_RUN = 25    # cap a single test sweep so a giant repo
                               # cannot stall the loop forever
SINGLE_TEST_TIMEOUT = 120      # seconds per discovered test file
PATCH_FILE_CHAR_CAP = 8_000    # how much of each source file we feed the LLM
PATCH_LOG_CHAR_CAP = 4_000     # how much of each failing test log we feed
PATCH_MAX_CTX_FILES = 6        # extra source files included alongside the
                               # failing test files
PATCH_MAX_FAILING_INCLUDED = 4 # failing tests included in the patch prompt

# Markers that mean "the test framework / runtime itself is missing", as
# distinct from "tests were collected and failed". Detected by substring
# match against the combined stdout/stderr of the test invocation.
_FRAMEWORK_MISSING_MARKERS = (
    # Python
    "ModuleNotFoundError: No module named 'pytest'",
    "ImportError: No module named pytest",
    "pytest: command not found",
    "No such file or directory: 'pytest'",
    "command not found: pytest",
    # Node / JS
    "Cannot find module 'jest'",
    "Cannot find module 'vitest'",
    "Cannot find module 'mocha'",
    "command not found: jest",
    "command not found: vitest",
    "command not found: mocha",
    "npm ERR! missing script: test",
    "sh: jest: not found",
    "sh: vitest: not found",
    "sh: mocha: not found",
    # Generic shell exec failures
    "No such file or directory",
)

# Strict SYSTEM prompt — the patcher is a SOFTWARE ENGINEER, never a
# security researcher. Pinned at the top of every patch request.
_PATCHER_SYSTEM_PROMPT = (
    "You are a senior software engineer fixing failing tests in an "
    "open-source repository.\n\n"
    "ROLE CONSTRAINTS (NON-NEGOTIABLE):\n"
    "- You are a SOFTWARE ENGINEER. You are NOT a security researcher, "
    "penetration tester, hacker, fuzzer, or red-teamer.\n"
    "- Your ONLY goal is to make the failing tests pass by editing the "
    "application/library code.\n"
    "- You are FORBIDDEN from producing exploit payloads, fuzz harnesses, "
    "shell-access code, telemetry, or any security tooling.\n"
    "- You MUST NOT delete, skip, or weaken assertions in the test files "
    "to make them pass. Fix the production code instead.\n"
    "- Prefer the smallest viable diff. Do not refactor unrelated code.\n"
    "- Do not add new third-party dependencies unless absolutely required.\n\n"
    "OUTPUT CONTRACT:\n"
    "Respond with a SINGLE JSON object and nothing else — no prose, no "
    "markdown fences. Schema:\n"
    "{\n"
    '  "rationale": "<one short sentence on the root cause>",\n'
    '  "files": [\n'
    '    {"path": "relative/path.py", "content": "<full new file contents>"}\n'
    "  ]\n"
    "}\n"
    "- 'files' must contain the FULL replacement contents of every file you "
    "modify. Partial diffs are not accepted.\n"
    "- 'path' must be a relative POSIX path inside the repository — never "
    "absolute, never containing '..'.\n"
    "- Omit files you are not modifying.\n"
    "- If you cannot determine a fix, return {\"rationale\": \"<reason>\", "
    "\"files\": []}."
)


# ── Result dataclasses ────────────────────────────────────────────────────
@dataclass
class OSSCampaign:
    repo_url: str
    mode: str  # "setup_failed" | "no_tests" | "tests_passing" | "patching"
               # | "patched" | "patch_exhausted" | "redteam" | "denied"
               # | "env_failed" | "attack" | "fix"
    findings: list[dict] = field(default_factory=list)
    pr_url: str | None = None
    error: str | None = None
    notes: list[str] = field(default_factory=list)
    patch_attempts: int = 0
    redteam_invoked: bool = False
    test_status: str = "unknown"
    # Structured timeline of every milestone — what the markdown
    # narrative renderer walks to produce the end-to-end story
    # (clone → setup → discover → run → patch attempt N → red-team
    # tool calls → findings → patches). Each entry is
    # {"ts": iso8601, "phase": str, "kind": str, "data": dict}.
    events: list[dict] = field(default_factory=list)
    started_at: str = field(
        default_factory=lambda: time.strftime("%Y-%m-%dT%H:%M:%SZ"),
    )
    completed_at: str | None = None
    setup_warnings: list[str] = field(default_factory=list)
    report_path: str | None = None

    def event(self, phase: str, kind: str, **data: Any) -> None:
        """Record one structured milestone."""
        self.events.append({
            "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "phase": phase,
            "kind": kind,
            "data": data,
        })

    def to_json(self) -> dict[str, Any]:
        return dataclasses.asdict(self)


# ── Lazy stage helpers (kept tiny so this module typechecks alone) ─────────
def _open_sandbox(repo_url: str):
    from architect import sandbox
    return sandbox.open_sandbox(repo_url)


def _detect_runtime(repo_path: str):
    # language_runtime exposes RuntimeFactory.for_repo as the canonical
    # auto-detect entry point — there is no module-level detect_runtime.
    from language_runtime import RuntimeFactory
    return RuntimeFactory.for_repo(repo_path)


def _hermes_attack(repo_path: str, language: str):
    # run_hermes_research requires both target_repo (the URL/identifier
    # used for session bookkeeping) and repo_dir (the on-disk path the
    # tools actually read from). For the OSS-Guardian path the sandbox
    # gives us a single local path that serves both purposes.
    from hermes_orchestrator import run_hermes_research
    return run_hermes_research(target_repo=repo_path,
                               repo_dir=repo_path,
                               focus_area=f"oss-guardian:{language}",
                               max_iterations=6)


def _route_disclosure(finding: dict) -> dict:
    """Route a finding to the right submission lane."""
    sev = str(finding.get("severity", "P3")).upper()
    cve = finding.get("cve_id")
    acts = float(finding.get("acts_score", 0.0))
    if acts < 0.80 or sev not in ("P1", "P2"):
        return {"lane": "skip", "reason": "below-quality-gate"}
    if cve:
        return {"lane": "github_pr", "reason": "existing CVE"}
    return {"lane": "disclosure_vault", "reason": "novel zero-day"}


# ── Main runner ────────────────────────────────────────────────────────────
class OSSGuardian:
    """
    Autonomous open-source DevSecOps runner.

    Constructor flags:
      attack_only         : skip the patch loop (still requires
                            redteam_authorized=True to actually attack).
      fix_only            : never red-team, even if patch loop exhausts.
      redteam_authorized  : Condition B from the spec — set this to True
                            when invoked via the operator's /redteam
                            command from Telegram.
    """

    def __init__(
        self,
        *,
        attack_only: bool = False,
        fix_only: bool = False,
        redteam_authorized: bool = False,
    ):
        self.attack_only = attack_only
        self.fix_only = fix_only
        self.redteam_authorized = redteam_authorized

    # ── public entry ───────────────────────────────────────────────────────
    def run(self, repo_url: str) -> OSSCampaign:
        camp = OSSCampaign(repo_url=repo_url, mode="setup")
        camp.event("PHASE_1", "campaign_started", repo_url=repo_url,
                   flags={"attack_only": self.attack_only,
                          "fix_only": self.fix_only,
                          "redteam_authorized": self.redteam_authorized})
        repo_path = ""
        try:
            with _open_sandbox(repo_url) as sbx:
                repo_path = str(getattr(sbx, "repo_path", None) or sbx)
                camp.event("PHASE_1", "sandbox_opened", repo_path=repo_path,
                           backend=getattr(sbx, "backend", "unknown"))
                runtime = _detect_runtime(repo_path)
                language = getattr(runtime, "language", "unknown")
                camp.notes.append(f"runtime:{language}")
                camp.event("PHASE_1", "runtime_detected", language=language)

                # 1) Provision the test environment FIRST so we can tell a
                #    missing framework apart from a real test failure.
                env_config = self._safe_setup_env(runtime, repo_path, camp)
                if env_config is None:
                    camp.mode = "env_failed"
                    camp.event("PHASE_1", "env_failed",
                               reason="setup_env returned None")
                    return camp
                # Hoist any structured setup warnings out of the runtime.
                sw = getattr(env_config, "setup_warnings", None) or []
                if sw:
                    camp.setup_warnings.extend(sw)
                    camp.event("PHASE_1", "setup_warnings",
                               warnings=sw[:5], total=len(sw))

                # 2) Run the project's own test suite.
                test_state = self._run_test_suite(runtime, repo_path, env_config)
                camp.test_status = test_state["status"]
                camp.event("PHASE_1", "test_sweep",
                           status=test_state["status"],
                           tests_run=test_state.get("tests_run", 0),
                           failure_count=len(test_state.get("failures") or []))

                # 3) Framework missing → re-install once, retest.
                if test_state["status"] == "framework_missing":
                    camp.notes.append(
                        "test framework missing — re-running setup_env "
                        "(installing requirements.txt / package.json deps)"
                    )
                    env_config = self._safe_setup_env(
                        runtime, repo_path, camp, force=True
                    )
                    if env_config is not None:
                        test_state = self._run_test_suite(
                            runtime, repo_path, env_config
                        )
                        camp.test_status = test_state["status"]
                    if test_state["status"] == "framework_missing":
                        camp.mode = "env_failed"
                        camp.notes.append(
                            "test framework still missing after dependency "
                            "re-install — refusing to proceed (would otherwise "
                            "be misclassified as a test failure)"
                        )
                        return camp

                # 4) No tests in the repo — refuse to escalate without
                #    explicit /redteam authorization.
                if test_state["status"] == "no_tests":
                    camp.mode = "no_tests"
                    camp.notes.append(
                        "no test files discovered — Blue Team has nothing to "
                        "patch; red team is gated behind /redteam authorization"
                    )
                    return self._maybe_red_team(
                        runtime, repo_path, camp, language,
                        reason="no_tests",
                    )

                # 5) Tests passing — DO NOT auto-escalate to red team.
                if test_state["status"] == "passed":
                    camp.mode = "tests_passing"
                    camp.notes.append(
                        "all discovered tests passing — red team gated; "
                        "send /redteam <repo> to authorize an offensive run"
                    )
                    return self._maybe_red_team(
                        runtime, repo_path, camp, language,
                        reason="tests_passing",
                    )

                # 6) Real test failures → Blue Team patch loop.
                #    Exception: caller asked for attack_only AND already
                #    has /redteam authorization → skip the patch loop.
                if self.attack_only and self.redteam_authorized:
                    camp.notes.append(
                        "attack_only + redteam_authorized — skipping Blue "
                        "Team patch loop (operator override)"
                    )
                    return self._red_team(runtime, repo_path, camp, language,
                                          reason="operator_override")

                if self.attack_only and not self.redteam_authorized:
                    camp.mode = "denied"
                    camp.notes.append(
                        "attack_only requested but /redteam not authorized — "
                        "refusing offensive escalation (Condition B not met)"
                    )
                    return camp

                camp.mode = "patching"
                camp.notes.append(
                    f"{len(test_state['failures'])} failing test file(s) — "
                    f"entering Blue Team patch loop "
                    f"(MAX_PATCH_RETRIES={MAX_PATCH_RETRIES})"
                )
                patched = self._patch_loop(
                    runtime=runtime,
                    repo_path=repo_path,
                    env_config=env_config,
                    initial_state=test_state,
                    camp=camp,
                )
                if patched:
                    camp.mode = "patched"
                    camp.test_status = "passed"
                    camp.notes.append(
                        "Blue Team succeeded — tests now passing without "
                        "ever entering red team mode"
                    )
                    return camp

                # Patch loop exhausted → Condition A satisfied.
                camp.mode = "patch_exhausted"
                camp.notes.append(
                    f"patch loop exhausted after {camp.patch_attempts} "
                    f"attempts — Condition A satisfied, red team UNLOCKED"
                )
                if self.fix_only:
                    camp.notes.append(
                        "fix_only=True — refusing to red-team even after "
                        "patch exhaustion"
                    )
                    return camp
                return self._red_team(runtime, repo_path, camp, language,
                                      reason="patch_exhausted")
        except Exception as exc:  # noqa: BLE001
            LOG.exception("OSSGuardian crashed on %s: %s", repo_url, exc)
            camp.error = str(exc)
            # Pin the campaign to a documented terminal mode so the
            # state machine is exhaustive — an un-set mode here would
            # leave the orchestrator unable to tell setup-time crashes
            # apart from successful "patching" runs, and could leak into
            # a red-team trigger upstream. setup_failed is gated below
            # red team in every consumer.
            if camp.mode in ("setup", "patching"):
                camp.mode = "setup_failed"
        camp.completed_at = time.strftime("%Y-%m-%dT%H:%M:%SZ")
        camp.event("PHASE_3", "campaign_completed",
                   mode=camp.mode, test_status=camp.test_status,
                   findings_count=len(camp.findings),
                   patch_attempts=camp.patch_attempts,
                   redteam_invoked=camp.redteam_invoked,
                   error=camp.error)
        return camp

    # ── stage: env setup ──────────────────────────────────────────────────
    def _safe_setup_env(self, runtime, repo_path: str, camp: OSSCampaign,
                        *, force: bool = False):
        try:
            env_config = runtime.setup_env(repo_path)
            camp.notes.append(
                "setup_env OK"
                + (" (forced re-install)" if force else "")
                + f" → {getattr(env_config, 'env_dir', '?')}"
            )
            return env_config
        except Exception as exc:  # noqa: BLE001
            LOG.warning("setup_env failed: %s", exc)
            camp.notes.append(f"setup_env failed: {exc}")
            return None

    # ── stage: run the whole discovered test suite ─────────────────────────
    def _run_test_suite(self, runtime, repo_path: str, env_config) -> dict:
        """
        Run every discovered test file once and aggregate the results.

        Returns one of:
          {"status": "no_tests"}
          {"status": "framework_missing", "raw": "<combined output>"}
          {"status": "passed", "tests_run": N}
          {"status": "failed", "failures": [{path,output,code}, ...],
           "tests_run": N}
        """
        try:
            tests = runtime.discover_tests(repo_path) or []
        except Exception as exc:  # noqa: BLE001
            LOG.warning("discover_tests crashed: %s", exc)
            tests = []
        if not tests:
            return {"status": "no_tests"}

        tests = tests[:MAX_TEST_FILES_PER_RUN]
        failures: list[dict] = []
        framework_missing_seen = False
        framework_missing_blob = ""
        for tp in tests:
            try:
                output, code = runtime.run_tests(
                    tp, repo_path, env_config, timeout=SINGLE_TEST_TIMEOUT
                )
            except Exception as exc:  # noqa: BLE001
                output = f"[run_tests crashed: {exc}]"
                code = 1
            if self._looks_like_framework_missing(output, code):
                framework_missing_seen = True
                framework_missing_blob = output
                # Don't keep iterating once the framework itself is broken —
                # every other invocation will report the same root cause.
                break
            if code != 0:
                failures.append({"path": tp, "output": output, "code": code})

        if framework_missing_seen:
            return {"status": "framework_missing", "raw": framework_missing_blob}
        if not failures:
            return {"status": "passed", "tests_run": len(tests)}
        return {
            "status": "failed",
            "failures": failures,
            "tests_run": len(tests),
        }

    @staticmethod
    def _looks_like_framework_missing(output: str, code: int) -> bool:
        # Exit code 127 from the underlying _run wrapper means the test
        # binary itself wasn't found (FileNotFoundError caught in
        # LanguageRuntime._run).
        if code == 127:
            return True
        if not output:
            return False
        haystack = output[:8000]
        return any(marker in haystack for marker in _FRAMEWORK_MISSING_MARKERS)

    # ── stage: Blue Team patch loop ───────────────────────────────────────
    def _patch_loop(
        self,
        *,
        runtime,
        repo_path: str,
        env_config,
        initial_state: dict,
        camp: OSSCampaign,
    ) -> bool:
        """
        Up to MAX_PATCH_RETRIES rounds of (request patch ➜ apply ➜ retest).
        Returns True if the suite is green at the end of any round.

        Every milestone is recorded as a structured event so the markdown
        narrative renderer can tell the operator EXACTLY what happened on
        each attempt — what failed, what the LLM proposed, what was
        applied, and what the post-patch test sweep returned.
        """
        import traceback as _tb
        state = initial_state
        camp.event("PHASE_1", "patch_loop_started",
                   max_retries=MAX_PATCH_RETRIES,
                   initial_failure_count=len(initial_state.get("failures") or []))
        for attempt in range(1, MAX_PATCH_RETRIES + 1):
            camp.patch_attempts = attempt
            camp.event("PHASE_1", "patch_attempt_start",
                       attempt=attempt,
                       failing=[f["path"] for f in (state.get("failures") or [])][:8])
            try:
                patch = self._request_patch(
                    repo_path=repo_path,
                    failing_state=state,
                    attempt=attempt,
                )
            except Exception as exc:  # noqa: BLE001
                tb_text = _tb.format_exc()
                LOG.warning("patch attempt %d: LLM call failed: %s\n%s",
                            attempt, exc, tb_text)
                camp.notes.append(
                    f"patch attempt {attempt}: LLM unavailable — {exc}"
                )
                camp.event("PHASE_1", "patch_llm_failed",
                           attempt=attempt,
                           exception_type=type(exc).__name__,
                           exception=repr(exc),
                           traceback=tb_text)
                # Without an LLM there is nothing to apply; no point retrying.
                break

            files = patch.get("files") or []
            rationale = (patch.get("rationale") or "").strip()
            if not files:
                camp.notes.append(
                    f"patch attempt {attempt}: model returned no files "
                    f"(rationale={rationale!r}) — skipping apply"
                )
                camp.event("PHASE_1", "patch_empty",
                           attempt=attempt, rationale=rationale)
                continue

            # Capture the pre-patch contents so the report can show the
            # actual diff the LLM made — this is the "how did blue team
            # patch it" detail the operator wants to see.
            pre_snapshots: dict[str, str] = {}
            for f in files:
                rel = self._sanitize_relpath(f["path"], os.path.realpath(repo_path))
                if rel is None:
                    continue
                full = os.path.join(os.path.realpath(repo_path), rel)
                try:
                    pre_snapshots[rel] = Path(full).read_text(errors="replace")
                except OSError:
                    pre_snapshots[rel] = ""  # new file

            applied = self._apply_patch_files(files, repo_path, camp, attempt)
            if not applied:
                camp.notes.append(
                    f"patch attempt {attempt}: nothing applied (all files "
                    f"rejected); aborting patch loop"
                )
                camp.event("PHASE_1", "patch_apply_failed",
                           attempt=attempt, rationale=rationale)
                break

            camp.notes.append(
                f"patch attempt {attempt}: applied {applied} file(s) "
                f"— rationale: {rationale[:200]!r}"
            )
            # Record the patch with before/after summaries (capped to
            # keep the JSON event log under control).
            file_diffs = []
            for f in files[:6]:
                rel = self._sanitize_relpath(f["path"], os.path.realpath(repo_path))
                if rel is None:
                    continue
                pre = pre_snapshots.get(rel, "")
                post = f.get("content", "")
                file_diffs.append({
                    "path": rel,
                    "pre_len": len(pre),
                    "post_len": len(post),
                    "pre_head": pre[:600],
                    "post_head": post[:600],
                    "pre_was_new": pre == "",
                })
            camp.event("PHASE_1", "patch_applied",
                       attempt=attempt, applied=applied,
                       rationale=rationale, files=file_diffs)

            state = self._run_test_suite(runtime, repo_path, env_config)
            camp.test_status = state["status"]
            camp.event("PHASE_1", "post_patch_test_sweep",
                       attempt=attempt, status=state["status"],
                       tests_run=state.get("tests_run", 0),
                       failure_count=len(state.get("failures") or []))
            if state["status"] == "passed":
                camp.event("PHASE_1", "patch_loop_success", attempt=attempt)
                return True
            if state["status"] == "framework_missing":
                camp.notes.append(
                    f"patch attempt {attempt}: patched code broke the test "
                    f"framework — aborting patch loop"
                )
                camp.event("PHASE_1", "patch_broke_framework",
                           attempt=attempt)
                return False
            # status == "failed" → loop and try again
        camp.event("PHASE_1", "patch_loop_exhausted",
                   attempts=camp.patch_attempts)
        return False

    # ── Blue Team patch request ───────────────────────────────────────────
    def _request_patch(
        self,
        *,
        repo_path: str,
        failing_state: dict,
        attempt: int,
    ) -> dict:
        """
        Ask `core_reasoning` (DeepSeek R1) for a JSON patch.

        Returns ``{"rationale": str, "files": [{path, content}, ...]}``.
        On any structural error returns ``{"rationale": "<err>", "files": []}``.
        """
        # Late import so unit tests can stub llm_manager.
        from llm_manager import default_manager

        failures = failing_state.get("failures") or []
        included = failures[:PATCH_MAX_FAILING_INCLUDED]

        # Collect candidate source files referenced from the tracebacks
        # (plus the failing test files themselves) so the model has the
        # actual code in front of it instead of guessing.
        ctx_paths: list[str] = []
        for f in included:
            ctx_paths.append(f["path"])
            ctx_paths.extend(self._extract_source_paths(f.get("output", "")))
        ctx_files = self._materialize_files(ctx_paths, repo_path)

        user_payload = {
            "attempt": attempt,
            "max_attempts": MAX_PATCH_RETRIES,
            "failing_tests": [
                {
                    "test_path": f["path"],
                    "exit_code": f.get("code"),
                    "output_tail": (f.get("output") or "")[-PATCH_LOG_CHAR_CAP:],
                }
                for f in included
            ],
            "repo_files": ctx_files,
            "instructions": (
                "Read the failing test logs and the included source files. "
                "Identify the SMALLEST change to the production code that "
                "would make the failing tests pass. Return the full "
                "replacement contents of every file you modify. Reply with "
                "JSON only — schema fixed by the SYSTEM message."
            ),
        }

        messages = [
            {"role": "system", "content": _PATCHER_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": json.dumps(user_payload, ensure_ascii=False),
            },
        ]

        mgr = default_manager()
        text = mgr.chat_text(
            "core_reasoning",
            messages,
            json_mode=True,
            temperature=0.1,
            max_tokens=4096,
        )
        return self._parse_patch_response(text)

    @staticmethod
    def _parse_patch_response(text: str) -> dict:
        if not text:
            return {"rationale": "empty response", "files": []}
        # DeepSeek R1 occasionally wraps output in <think>...</think> reasoning
        # blocks even with JSON mode; strip them defensively.
        cleaned = re.sub(r"<think>.*?</think>", "", text,
                         flags=re.DOTALL | re.IGNORECASE).strip()
        # Strip common code-fence wrappers if the model ignores the
        # "no markdown" instruction.
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```[a-zA-Z]*\s*", "", cleaned)
            cleaned = re.sub(r"\s*```\s*$", "", cleaned)
        try:
            obj = json.loads(cleaned)
        except json.JSONDecodeError:
            # Last-ditch: find the first {...} balanced span.
            m = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
            if not m:
                return {"rationale": f"non-JSON response: {cleaned[:160]!r}",
                        "files": []}
            try:
                obj = json.loads(m.group(0))
            except json.JSONDecodeError:
                return {"rationale": "unparseable JSON", "files": []}
        if not isinstance(obj, dict):
            return {"rationale": "JSON was not an object", "files": []}
        files = obj.get("files") if isinstance(obj.get("files"), list) else []
        clean_files = []
        for entry in files:
            if not isinstance(entry, dict):
                continue
            p = entry.get("path")
            c = entry.get("content")
            if isinstance(p, str) and isinstance(c, str) and p.strip():
                clean_files.append({"path": p.strip(), "content": c})
        return {
            "rationale": str(obj.get("rationale", "")).strip(),
            "files": clean_files,
        }

    # ── Patch context helpers ─────────────────────────────────────────────
    _SRC_PATH_RX = re.compile(
        r'(?:File "|at .*?\(|^\s+at\s+|^\s*-->\s*)'
        r'([A-Za-z0-9_./\\-]+\.(?:py|js|ts|jsx|tsx|java|go|rs|rb))'
        r'(?:"|:|\s)',
        re.MULTILINE,
    )

    @classmethod
    def _extract_source_paths(cls, output: str) -> list[str]:
        if not output:
            return []
        seen: list[str] = []
        for m in cls._SRC_PATH_RX.finditer(output):
            p = m.group(1).replace("\\", "/")
            if p not in seen:
                seen.append(p)
        return seen

    @classmethod
    def _materialize_files(
        cls, paths: list[str], repo_path: str
    ) -> list[dict]:
        out: list[dict] = []
        repo_real = os.path.realpath(repo_path)
        seen: set[str] = set()
        for raw in paths:
            if len(out) >= PATCH_MAX_CTX_FILES + PATCH_MAX_FAILING_INCLUDED:
                break
            rel = cls._sanitize_relpath(raw, repo_real)
            if not rel or rel in seen:
                continue
            full = os.path.join(repo_real, rel)
            if not os.path.isfile(full):
                # Walk up: tracebacks sometimes start at the repo subpath
                # (e.g. "src/foo/bar.py" when the file is at "/.../src/foo/bar.py").
                # _sanitize_relpath already preserves that shape, so a
                # misshapen path means the file genuinely isn't present.
                continue
            try:
                content = Path(full).read_text(errors="replace")
            except OSError:
                continue
            if len(content) > PATCH_FILE_CHAR_CAP:
                head = content[: PATCH_FILE_CHAR_CAP // 2]
                tail = content[-PATCH_FILE_CHAR_CAP // 2 :]
                content = (
                    f"{head}\n\n# ── [oss_guardian] file truncated "
                    f"(orig {len(content)} chars) ──\n\n{tail}"
                )
            seen.add(rel)
            out.append({"path": rel, "content": content})
        return out

    @staticmethod
    def _sanitize_relpath(raw: str, repo_real: str) -> str | None:
        """Return a clean repo-relative POSIX path or None if it escapes."""
        if not raw or raw.strip() in ("", "."):
            return None
        candidate = raw.replace("\\", "/").strip().lstrip("/")
        # Block obvious traversal attempts.
        if ".." in candidate.split("/"):
            return None
        full = os.path.realpath(os.path.join(repo_real, candidate))
        try:
            rel = os.path.relpath(full, repo_real)
        except ValueError:
            return None
        if rel.startswith(".."):
            return None
        return rel.replace("\\", "/")

    def _apply_patch_files(
        self,
        files: list[dict],
        repo_path: str,
        camp: OSSCampaign,
        attempt: int,
    ) -> int:
        repo_real = os.path.realpath(repo_path)
        applied = 0
        for entry in files:
            rel = self._sanitize_relpath(entry["path"], repo_real)
            if rel is None:
                camp.notes.append(
                    f"patch attempt {attempt}: rejected unsafe path "
                    f"{entry['path']!r}"
                )
                continue
            full = os.path.join(repo_real, rel)
            try:
                os.makedirs(os.path.dirname(full) or repo_real, exist_ok=True)
                Path(full).write_text(entry["content"])
                applied += 1
            except OSError as exc:
                camp.notes.append(
                    f"patch attempt {attempt}: failed to write {rel}: {exc}"
                )
        return applied

    # ── stage: red team (gated) ───────────────────────────────────────────
    def _maybe_red_team(
        self,
        runtime,
        repo_path: str,
        camp: OSSCampaign,
        language: str,
        *,
        reason: str,
    ) -> OSSCampaign:
        """Only escalates if /redteam authorization (Condition B) is set."""
        if self.fix_only:
            camp.notes.append("fix_only=True — red team suppressed")
            return camp
        if not self.redteam_authorized:
            camp.notes.append(
                "red team gated — Condition B (/redteam) not authorized"
            )
            return camp
        return self._red_team(runtime, repo_path, camp, language, reason=reason)

    def _red_team(
        self,
        runtime,
        repo_path: str,
        camp: OSSCampaign,
        language: str,
        *,
        reason: str,
    ) -> OSSCampaign:
        import traceback as _tb
        camp.notes.append(f"red team launched (reason={reason})")
        camp.redteam_invoked = True
        camp.event("PHASE_2", "red_team_started",
                   reason=reason, language=language)
        camp.mode = "redteam" if camp.mode in ("setup", "tests_passing",
                                               "no_tests") else camp.mode
        try:
            session = _hermes_attack(repo_path, language)
            camp.findings = self._extract_findings(session)
            # Capture the red-team session metadata so the markdown
            # narrative can show: how many iterations, which tools were
            # called in what order, and what each finding looked like.
            tool_log = list(getattr(session, "tool_call_log", []) or [])
            camp.event("PHASE_2", "red_team_completed",
                       session_id=getattr(session, "session_id", "?"),
                       phase=getattr(getattr(session, "phase", None),
                                     "value", "?"),
                       tool_calls=len(tool_log),
                       tools_used=sorted({
                           str(c.get("tool") or c.get("name") or "?")
                           for c in tool_log
                       }),
                       findings_count=len(camp.findings))
            for f in camp.findings:
                camp.event("PHASE_2", "finding_recorded",
                           finding_id=f.get("finding_id") or f.get("id") or "?",
                           title=f.get("title", "?"),
                           severity=f.get("severity", "?"),
                           cwe=f.get("cwe_id") or f.get("cwe") or "?",
                           file_path=f.get("file_path", ""),
                           ves_score=f.get("ves_score", 0.0),
                           acts_score=f.get("acts_score", 0.0))
            self._route_findings(camp.findings, camp)
        except Exception as exc:  # noqa: BLE001
            tb_text = _tb.format_exc()
            camp.notes.append(f"red team crashed: {exc}")
            LOG.exception("red team crashed: %s", exc)
            camp.error = str(exc)
            camp.event("PHASE_2", "red_team_crashed",
                       exception_type=type(exc).__name__,
                       exception=repr(exc), traceback=tb_text)
        return camp

    def _extract_findings(self, session) -> list[dict]:
        out: list[dict] = []
        for f in getattr(session, "findings", []) or []:
            if dataclasses.is_dataclass(f):
                out.append(dataclasses.asdict(f))
            elif isinstance(f, dict):
                out.append(f)
            else:
                out.append({"raw": repr(f)})
        return out

    def _route_findings(self, findings: list[dict], camp: OSSCampaign) -> None:
        try:
            from architect import embodied_bridge
            from architect.embodied_bridge import FindingPayload
        except Exception:  # noqa: BLE001
            embodied_bridge = None
            FindingPayload = None  # type: ignore[assignment]
        try:
            import disclosure_vault  # type: ignore
        except Exception:  # noqa: BLE001
            disclosure_vault = None

        for f in findings:
            decision = _route_disclosure(f)
            f["routing"] = decision
            if decision["lane"] == "disclosure_vault" and disclosure_vault is not None:
                try:
                    disclosure_vault.intake(f, source="oss_guardian")  # type: ignore[attr-defined]
                except Exception as exc:  # noqa: BLE001
                    LOG.warning("disclosure_vault.intake failed: %s", exc)
            if embodied_bridge is not None and FindingPayload is not None:
                try:
                    payload = FindingPayload(
                        finding_id=str(f.get("finding_id") or f.get("id") or "?"),
                        title=str(f.get("title") or "(untitled)"),
                        severity=str(f.get("severity") or "P3"),
                        cwe=str(f.get("cwe") or "?"),
                        repo=camp.repo_url,
                        file_path=str(f.get("file_path") or ""),
                        description=str(f.get("description") or ""),
                        proof_of_concept=str(f.get("proof_of_concept") or ""),
                        acts_score=float(f.get("acts_score") or 0.0),
                    )
                    embodied_bridge.emit_finding(payload)
                except Exception as exc:  # noqa: BLE001
                    LOG.warning("embodied_bridge.emit_finding failed: %s", exc)


# ─────────────────────────────────────────────────────────────────────────────
# End-to-end Markdown narrative renderer
#
# The compliance renderer in `report_generator.py` is intentionally
# limited to CWE/OWASP/SOC2 mappings. The operator wants the full
# story — every test failure, every patch attempt with diff and
# rationale, every red-team tool call, every finding with PoC, every
# blue-team patch. This walks the structured `OSSCampaign.events`
# log produced above and renders it as a single Telegram-friendly
# Markdown report.
# ─────────────────────────────────────────────────────────────────────────────
def _md_escape(s: str) -> str:
    return (s or "").replace("`", "\u02cb").replace("\u200b", "")


def _md_code_block(text: str, lang: str = "") -> str:
    """Render a fenced code block, escaping any nested triple-backticks."""
    body = (text or "").replace("```", "``\u200b`")
    return f"```{lang}\n{body}\n```"


def render_campaign_markdown(camp: OSSCampaign) -> str:
    """End-to-end story of a campaign, written for the operator on Telegram.

    Walks ``camp.events`` chronologically and renders each phase. Safe to
    call on partial campaigns (env_failed, patch_exhausted, crashed).
    """
    lines: list[str] = []
    lines.append(f"# Rhodawk Campaign Report — `{_md_escape(camp.repo_url)}`")
    lines.append("")
    lines.append(f"- **Started:** `{camp.started_at}`")
    lines.append(f"- **Completed:** `{camp.completed_at or '(in flight)'}`")
    lines.append(f"- **Final mode:** `{camp.mode}`")
    lines.append(f"- **Test status:** `{camp.test_status}`")
    lines.append(f"- **Patch attempts:** `{camp.patch_attempts}`")
    lines.append(f"- **Red team invoked:** `{camp.redteam_invoked}`")
    lines.append(f"- **Findings:** `{len(camp.findings)}`")
    if camp.error:
        lines.append(f"- **Error:** `{_md_escape(camp.error)}`")
    if camp.pr_url:
        lines.append(f"- **PR:** {camp.pr_url}")
    lines.append("")

    if camp.setup_warnings:
        lines.append("## Environment Warnings")
        for w in camp.setup_warnings[:20]:
            lines.append(f"- {_md_escape(w)}")
        lines.append("")

    # ── Phase 1: Blue Team (clone → setup → tests → patch loop) ──
    p1 = [e for e in camp.events if e.get("phase") == "PHASE_1"]
    if p1:
        lines.append("## Phase 1 — Blue Team (Get Tests Green)")
        lines.append("")
        for ev in p1:
            kind = ev.get("kind", "")
            data = ev.get("data", {}) or {}
            ts = ev.get("ts", "")
            if kind == "campaign_started":
                lines.append(f"- `{ts}` campaign started, flags=`{data.get('flags')}`")
            elif kind == "sandbox_opened":
                lines.append(
                    f"- `{ts}` sandbox opened at `{_md_escape(data.get('repo_path',''))}` "
                    f"(backend=`{data.get('backend','?')}`)"
                )
            elif kind == "runtime_detected":
                lines.append(f"- `{ts}` runtime detected: **{data.get('language','?')}**")
            elif kind == "env_failed":
                lines.append(f"- `{ts}` ❌ environment setup failed — "
                             f"{_md_escape(data.get('reason',''))}")
            elif kind == "setup_warnings":
                lines.append(
                    f"- `{ts}` ⚠️ {data.get('total',0)} setup warning(s); "
                    f"first: `{_md_escape((data.get('warnings') or [''])[0])[:160]}`"
                )
            elif kind == "test_sweep":
                lines.append(
                    f"- `{ts}` initial test sweep → **{data.get('status','?')}** "
                    f"({data.get('tests_run',0)} run, "
                    f"{data.get('failure_count',0)} failing)"
                )
            elif kind == "patch_loop_started":
                lines.append("")
                lines.append(
                    f"### Patch loop (max {data.get('max_retries')} attempts, "
                    f"{data.get('initial_failure_count',0)} failing test file(s))"
                )
            elif kind == "patch_attempt_start":
                lines.append("")
                lines.append(f"#### Attempt {data.get('attempt')} — `{ts}`")
                failing = data.get("failing") or []
                if failing:
                    lines.append("Failing test files:")
                    for p in failing:
                        lines.append(f"- `{_md_escape(p)}`")
            elif kind == "patch_llm_failed":
                lines.append(
                    f"- ❌ LLM patch request failed: "
                    f"`{_md_escape(data.get('exception_type',''))}`: "
                    f"{_md_escape(data.get('exception',''))}"
                )
                tb = data.get("traceback") or ""
                if tb:
                    lines.append(_md_code_block(tb[-1200:], "text"))
            elif kind == "patch_empty":
                lines.append(
                    f"- ⚠️ model returned no files. Rationale: "
                    f"`{_md_escape(data.get('rationale',''))[:280]}`"
                )
            elif kind == "patch_apply_failed":
                lines.append(
                    f"- ❌ all proposed files were rejected by the safety "
                    f"sanitizer. Rationale: `{_md_escape(data.get('rationale',''))[:280]}`"
                )
            elif kind == "patch_applied":
                lines.append(
                    f"- ✅ applied **{data.get('applied',0)}** file(s)"
                )
                rationale = data.get("rationale") or ""
                if rationale:
                    lines.append("")
                    lines.append("**Rationale:**")
                    lines.append("")
                    lines.append("> " + _md_escape(rationale).replace("\n", "\n> "))
                    lines.append("")
                for fd in data.get("files") or []:
                    label = "new file" if fd.get("pre_was_new") else "modified"
                    lines.append(
                        f"- `{_md_escape(fd.get('path',''))}` ({label}, "
                        f"{fd.get('pre_len',0)}→{fd.get('post_len',0)} chars)"
                    )
                    pre = (fd.get("pre_head") or "")
                    post = (fd.get("post_head") or "")
                    if pre or post:
                        lines.append("")
                        lines.append("Before (head):")
                        lines.append(_md_code_block(pre or "(empty / new file)", "text"))
                        lines.append("After (head):")
                        lines.append(_md_code_block(post or "(empty)", "text"))
            elif kind == "post_patch_test_sweep":
                emoji = "✅" if data.get("status") == "passed" else "❌"
                lines.append(
                    f"- {emoji} post-patch tests → **{data.get('status','?')}** "
                    f"({data.get('tests_run',0)} run, "
                    f"{data.get('failure_count',0)} failing)"
                )
            elif kind == "patch_broke_framework":
                lines.append(
                    f"- ❌ patch broke the test framework — aborting loop"
                )
            elif kind == "patch_loop_success":
                lines.append(
                    f"- 🎉 **patch loop succeeded** on attempt "
                    f"{data.get('attempt')}"
                )
            elif kind == "patch_loop_exhausted":
                lines.append(
                    f"- ❌ patch loop exhausted after "
                    f"{data.get('attempts')} attempt(s)"
                )
        lines.append("")

    # ── Phase 2: Red Team (HERMES) ──
    p2 = [e for e in camp.events if e.get("phase") == "PHASE_2"]
    if p2:
        lines.append("## Phase 2 — Red Team (HERMES Adversarial Sweep)")
        lines.append("")
        for ev in p2:
            kind = ev.get("kind", "")
            data = ev.get("data", {}) or {}
            ts = ev.get("ts", "")
            if kind == "red_team_started":
                lines.append(
                    f"- `{ts}` red team launched (reason=`{data.get('reason')}`, "
                    f"language=`{data.get('language')}`)"
                )
            elif kind == "red_team_completed":
                lines.append(
                    f"- `{ts}` red team complete — session "
                    f"`{data.get('session_id','?')}`, phase `{data.get('phase','?')}`, "
                    f"**{data.get('tool_calls',0)}** tool call(s), "
                    f"**{data.get('findings_count',0)}** finding(s)"
                )
                tools = data.get("tools_used") or []
                if tools:
                    lines.append(
                        "- Tools exercised: " + ", ".join(
                            f"`{_md_escape(t)}`" for t in tools
                        )
                    )
            elif kind == "red_team_crashed":
                lines.append(
                    f"- ❌ red team crashed: "
                    f"`{_md_escape(data.get('exception_type',''))}`: "
                    f"{_md_escape(data.get('exception',''))}"
                )
                tb = data.get("traceback") or ""
                if tb:
                    lines.append(_md_code_block(tb[-1200:], "text"))
            elif kind == "finding_recorded":
                lines.append("")
                lines.append(
                    f"### Finding `{_md_escape(str(data.get('finding_id','?')))}` — "
                    f"{_md_escape(str(data.get('title','(untitled)')))}"
                )
                lines.append(
                    f"- **Severity:** `{data.get('severity','?')}`  "
                    f"**CWE:** `{data.get('cwe','?')}`  "
                    f"**VES:** `{data.get('ves_score',0):.2f}`  "
                    f"**ACTS:** `{data.get('acts_score',0):.2f}`"
                )
                fp = data.get("file_path") or ""
                if fp:
                    lines.append(f"- **Location:** `{_md_escape(fp)}`")
        lines.append("")

    # ── Findings detail (PoC + remediation when present) ──
    if camp.findings:
        lines.append("## Findings Detail")
        lines.append("")
        for f in camp.findings:
            fid = f.get("finding_id") or f.get("id") or "?"
            title = f.get("title") or f.get("description") or "(untitled)"
            lines.append(f"### `{_md_escape(str(fid))}` — {_md_escape(str(title))}")
            sev = f.get("severity", "?")
            cwe = f.get("cwe_id") or f.get("cwe") or "?"
            lines.append(f"- **Severity:** `{sev}`  **CWE:** `{cwe}`")
            fp = f.get("file_path") or ""
            ln = f.get("line_number") or f.get("line") or ""
            if fp:
                loc = f"`{_md_escape(fp)}`" + (f":`{ln}`" if ln else "")
                lines.append(f"- **Location:** {loc}")
            desc = f.get("description") or ""
            if desc and desc != title:
                lines.append("")
                lines.append("**Description:**")
                lines.append("")
                lines.append("> " + _md_escape(desc).replace("\n", "\n> "))
            poc = f.get("poc") or f.get("proof_of_concept") or ""
            if poc:
                lines.append("")
                lines.append("**Proof of concept:**")
                lines.append(_md_code_block(str(poc)[:2000], "text"))
            rem = f.get("remediation") or f.get("recommendation") or ""
            if rem:
                lines.append("")
                lines.append("**Remediation:**")
                lines.append("")
                lines.append("> " + _md_escape(str(rem)).replace("\n", "\n> "))
            lines.append("")

    # ── Notes (chronological) ──
    if camp.notes:
        lines.append("## Operator Notes")
        for n in camp.notes:
            lines.append(f"- {_md_escape(n)}")
        lines.append("")

    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="oss_guardian")
    ap.add_argument("--repo", required=True, help="GitHub repo URL or local path")
    ap.add_argument("--attack-only", action="store_true",
                    help="skip the patch loop (still requires --redteam)")
    ap.add_argument("--fix-only", action="store_true",
                    help="never red-team, even if patch loop exhausts")
    ap.add_argument("--redteam", action="store_true",
                    help="grant red-team authorization (Condition B)")
    ap.add_argument("--out", help="Write campaign JSON to this path")
    ap.add_argument("--md-out", help="Write the Markdown narrative to this path")
    args = ap.parse_args(argv)

    g = OSSGuardian(
        attack_only=args.attack_only,
        fix_only=args.fix_only,
        redteam_authorized=args.redteam,
    )
    camp = g.run(args.repo)
    js = camp.to_json()
    if args.out:
        Path(args.out).write_text(json.dumps(js, indent=2))
    else:
        print(json.dumps(js, indent=2))
    if args.md_out:
        Path(args.md_out).write_text(render_campaign_markdown(camp))
    return 0 if not camp.error else 1


if __name__ == "__main__":
    raise SystemExit(main())

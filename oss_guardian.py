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
        repo_path = ""
        try:
            with _open_sandbox(repo_url) as sbx:
                repo_path = str(getattr(sbx, "repo_path", None) or sbx)
                runtime = _detect_runtime(repo_path)
                language = getattr(runtime, "language", "unknown")
                camp.notes.append(f"runtime:{language}")

                # 1) Provision the test environment FIRST so we can tell a
                #    missing framework apart from a real test failure.
                env_config = self._safe_setup_env(runtime, repo_path, camp)
                if env_config is None:
                    camp.mode = "env_failed"
                    return camp

                # 2) Run the project's own test suite.
                test_state = self._run_test_suite(runtime, repo_path, env_config)
                camp.test_status = test_state["status"]

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
        """
        state = initial_state
        for attempt in range(1, MAX_PATCH_RETRIES + 1):
            camp.patch_attempts = attempt
            try:
                patch = self._request_patch(
                    repo_path=repo_path,
                    failing_state=state,
                    attempt=attempt,
                )
            except Exception as exc:  # noqa: BLE001
                LOG.warning("patch attempt %d: LLM call failed: %s", attempt, exc)
                camp.notes.append(
                    f"patch attempt {attempt}: LLM unavailable — {exc}"
                )
                # Without an LLM there is nothing to apply; no point retrying.
                break

            files = patch.get("files") or []
            rationale = (patch.get("rationale") or "").strip()
            if not files:
                camp.notes.append(
                    f"patch attempt {attempt}: model returned no files "
                    f"(rationale={rationale!r}) — skipping apply"
                )
                # Still re-run tests in case prior attempt's patch needs
                # a fresh look; otherwise abort on the next iteration.
                continue
            applied = self._apply_patch_files(files, repo_path, camp, attempt)
            if not applied:
                camp.notes.append(
                    f"patch attempt {attempt}: nothing applied (all files "
                    f"rejected); aborting patch loop"
                )
                break
            camp.notes.append(
                f"patch attempt {attempt}: applied {applied} file(s) "
                f"— rationale: {rationale[:200]!r}"
            )
            state = self._run_test_suite(runtime, repo_path, env_config)
            camp.test_status = state["status"]
            if state["status"] == "passed":
                return True
            if state["status"] == "framework_missing":
                # The patch broke the env — undo would be ideal but we
                # don't snapshot. Bail; do not red-team off a broken env.
                camp.notes.append(
                    f"patch attempt {attempt}: patched code broke the test "
                    f"framework — aborting patch loop"
                )
                return False
            # status == "failed" → loop and try again
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
        camp.notes.append(f"red team launched (reason={reason})")
        camp.redteam_invoked = True
        camp.mode = "redteam" if camp.mode in ("setup", "tests_passing",
                                               "no_tests") else camp.mode
        try:
            session = _hermes_attack(repo_path, language)
            camp.findings = self._extract_findings(session)
            self._route_findings(camp.findings, camp)
        except Exception as exc:  # noqa: BLE001
            camp.notes.append(f"red team crashed: {exc}")
            LOG.exception("red team crashed: %s", exc)
            camp.error = str(exc)
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
    return 0 if not camp.error else 1


if __name__ == "__main__":
    raise SystemExit(main())

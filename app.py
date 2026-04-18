"""
Rhodawk AI — Autonomous DevSecOps Control Plane v4.0
=====================================================
Full loop:
  1. Clone repo → discover tests → run pytest
  2. FAIL → retrieve similar fixes from memory (data flywheel)
  3. Dispatch Aider with failure + memory context via MCP tools
  4. Re-run tests on the patched code (verification — CLOSES THE LOOP)
  5. If still failing → retry with new failure context (up to MAX_RETRIES)
  6. SAST gate: bandit + 16-pattern secret scanner
  7. Supply chain gate: pip-audit + typosquatting detection
  8. Adversarial LLM review: 3-model concurrent consensus (Qwen∥Gemma∥Mistral)
  9. Z3 formal verification gate (bounded integer/bounds checking)
  10. If adversary REJECTs → loop back with critique as context
  11. Conviction engine: auto-merge if all trust criteria met
  12. All clear → open PR, record to training store, update memory
  13. LoRA scheduler: export training data when threshold reached
  14. Repo harvester: autonomous target selection (antagonist mode)
  15. Webhook server runs in parallel for event-driven triggers
"""

import hashlib
import json
import os
import signal
import subprocess
import tempfile
import threading
import time
from typing import Optional

import gradio as gr
import requests
from git import Repo
from tenacity import retry, stop_after_attempt, wait_exponential

from adversarial_reviewer import run_adversarial_review
from audit_logger import export_compliance_report, log_audit_event, read_audit_trail, verify_chain_integrity
from conviction_engine import evaluate_conviction, auto_merge_pr
from formal_verifier import run_formal_verification
from github_app import get_github_token
from job_queue import JobStatus, get_job_status_enum, get_metrics, list_all_jobs, upsert_job
from lora_scheduler import maybe_trigger_training, get_scheduler_status
from memory_engine import get_memory_stats, record_fix_outcome, retrieve_similar_fixes
from embedding_memory import retrieve_similar_fixes_v2
from notifier import (
    notify,
    notify_audit_complete,
    notify_audit_start,
    notify_chain_integrity,
    notify_patch_failed,
    notify_pr_created,
    notify_sast_blocked,
    notify_test_failed,
)
from sast_gate import run_sast_gate
from red_team_fuzzer import get_red_team_logs, get_red_team_stats, run_red_team_cegis
from supply_chain import run_supply_chain_gate
from training_store import export_training_data, get_statistics, initialize_store, record_attempt, update_test_result
from verification_loop import (
    MAX_RETRIES,
    ADVERSARIAL_REJECTION_MULTIPLIER,
    VerificationAttempt,
    VerificationResult,
    build_initial_prompt,
    build_retry_prompt,
)
from webhook_server import set_job_dispatcher, start_webhook_server
from worker_pool import MAX_WORKERS, run_parallel_audit
from language_runtime import RuntimeFactory, LanguageRuntime, EnvConfig

# Module-level runtime handle — set once per audit run.
# BUG-007 FIX: Protected by a lock so concurrent webhook-triggered audits do not
# overwrite _active_runtime while workers are mid-flight reading it.
_active_runtime: LanguageRuntime | None = None
_active_runtime_lock = threading.Lock()

# ──────────────────────────────────────────────────────────────
# SECRETS — env only, never hardcoded
# ──────────────────────────────────────────────────────────────
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_REPO = os.getenv("GITHUB_REPO", "")          # Optional — can be set via chat inbox
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
TENANT_ID = os.getenv("RHODAWK_TENANT_ID", "default")
MODEL = os.getenv("RHODAWK_MODEL", "openrouter/qwen/qwen-2.5-coder-32b-instruct:free")
RED_TEAM_ENABLED = os.getenv("RHODAWK_RED_TEAM_ENABLED", "true").lower() != "false"

# Only GITHUB_TOKEN and OPENROUTER_API_KEY are truly required at startup.
# GITHUB_REPO is now optional — it can be supplied via the chat inbox at runtime.
for _key, _val in [("GITHUB_TOKEN", GITHUB_TOKEN), ("OPENROUTER_API_KEY", OPENROUTER_API_KEY)]:
    if not _val:
        raise EnvironmentError(
            f"Required secret '{_key}' is not set. "
            "Add it in HuggingFace Space Settings → Secrets."
        )

# ──────────────────────────────────────────────────────────────
# PATHS & CONSTANTS
# ──────────────────────────────────────────────────────────────
PERSISTENT_DIR = "/data"
REPO_DIR = f"{PERSISTENT_DIR}/repo"
VENV_DIR = f"{PERSISTENT_DIR}/target_venv"
MCP_RUNTIME_CONFIG = "/tmp/mcp_runtime.json"

# ──────────────────────────────────────────────────────────────
# BUG-005 FIX: Explicit startup initialization — ensures SQLite tables exist
# even if the module-level call in training_store.py is optimized away or
# the import order changes in the future.
# ──────────────────────────────────────────────────────────────
initialize_store()

# ──────────────────────────────────────────────────────────────
# GLOBAL STATE
# ──────────────────────────────────────────────────────────────
dashboard_logs: list[str] = []
_log_lock = threading.Lock()
_audit_event = threading.Event()

# Chat inbox state — list of {"role": ..., "content": ...} dicts
_inbox_history: list[dict] = []
_inbox_lock = threading.Lock()


def ui_log(message: str, level: str = "INFO"):
    ts = time.strftime("%H:%M:%S")
    icons = {"OK": "✅", "FAIL": "❌", "WARN": "⚠", "SAST": "🛡", "ADV": "🔴", "PR": "🔁",
             "SKIP": "⏭", "MEM": "🧠", "CHAIN": "⛓", "SUPPLY": "📦", "RETRY": "🔄", "INFO": "  ",
             "RED": "⚔️", "ATTACK": "🗡", "CRASH": "💥", "BENCH": "🧪", "POOL": "⚡"}
    line = f"[{ts}] {icons.get(level, '  ')} {message}"
    print(line)
    with _log_lock:
        dashboard_logs.append(line)
        if len(dashboard_logs) > 300:
            dashboard_logs.pop(0)


# ──────────────────────────────────────────────────────────────
# SUBPROCESS RUNNER — shell=False enforced, secrets stripped
# ──────────────────────────────────────────────────────────────
def run_subprocess_safe(cmd: list, cwd: str = REPO_DIR, timeout: int = 300,
                        env_overrides: dict = None, raise_on_error: bool = True) -> tuple[str, int]:
    if isinstance(cmd, str):
        raise TypeError("SECURITY: String commands forbidden. Use list.")
    env = os.environ.copy()
    for k in ["OPENROUTER_API_KEY", "GITHUB_TOKEN", "GITHUB_PERSONAL_ACCESS_TOKEN",
               "TELEGRAM_BOT_TOKEN", "SLACK_WEBHOOK_URL", "RHODAWK_WEBHOOK_SECRET"]:
        env.pop(k, None)
    if env_overrides:
        env.update(env_overrides)
    proc = None
    try:
        proc = subprocess.Popen(cmd, shell=False, cwd=cwd, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, text=True, env=env, start_new_session=True)
        stdout, stderr = proc.communicate(timeout=timeout)
        output = (stdout or "") + "\n" + (stderr or "")
        if raise_on_error and proc.returncode != 0:
            raise subprocess.CalledProcessError(proc.returncode, cmd, stdout, stderr)
        return output, proc.returncode
    except subprocess.TimeoutExpired:
        if proc:
            try:
                os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
            except ProcessLookupError:
                pass
            proc.communicate()
        raise RuntimeError(f"Command timed out after {timeout}s: {cmd[0]}")


# ──────────────────────────────────────────────────────────────
# GIT HELPERS
# ──────────────────────────────────────────────────────────────
def configure_git_credentials():
    """
    Set up git credential storage.

    ROOT CAUSE FIX: the previous implementation called
        git config --global credential.helper 'store --file /tmp/.git-credentials'
    which writes to $HOME/.gitconfig. In HuggingFace Spaces $HOME=/home/rhodawk
    is often not writable at container runtime, causing exit-255 (fatal).

    Fix: write the gitconfig file directly — no git subprocess needed —
    then export GIT_CONFIG_GLOBAL so every subsequent git call in this
    process picks it up automatically (os.environ is copied by run_subprocess_safe).
    """
    cred_path = "/tmp/.git-credentials"
    with open(cred_path, "w") as f:
        f.write(f"https://x-token:{GITHUB_TOKEN}@github.com\n")
    os.chmod(cred_path, 0o600)

    gitconfig_path = "/tmp/.gitconfig"
    with open(gitconfig_path, "w") as f:
        f.write(
            f"[credential]\n\thelper = store --file {cred_path}\n"
            f"[user]\n\tname = Rhodawk AI\n\temail = agent@rhodawk.ai\n"
            f"[safe]\n\tdirectory = *\n"
        )
    os.chmod(gitconfig_path, 0o600)

    # Export to parent process env — all child subprocesses inherit this
    os.environ["GIT_CONFIG_GLOBAL"] = gitconfig_path
    ui_log(f"Git credentials configured → {gitconfig_path}", "INFO")


def write_mcp_config() -> str:
    config = {
        "mcpServers": {
            "fetch-docs": {
                "command": "uvx", "args": ["mcp-server-fetch"],
                "env": {
                    "FETCH_ALLOWED_DOMAINS": (
                        ",".join(_active_runtime.get_mcp_domains())
                        if _active_runtime
                        else "docs.python.org,pypi.org,docs.github.com"
                    )
                }
            },
            "github-manager": {
                "command": "npx", "args": ["-y", "@modelcontextprotocol/server-github"],
                "env": {"GITHUB_PERSONAL_ACCESS_TOKEN": GITHUB_TOKEN}
            },
        }
    }
    with open(MCP_RUNTIME_CONFIG, "w") as f:
        json.dump(config, f, indent=2)
    os.chmod(MCP_RUNTIME_CONFIG, 0o600)
    return MCP_RUNTIME_CONFIG


def safe_git_pull():
    _, code = run_subprocess_safe(["git", "pull", "--ff-only", "origin", "main"], cwd=REPO_DIR, raise_on_error=False)
    if code != 0:
        run_subprocess_safe(["git", "fetch", "origin"], cwd=REPO_DIR)
        run_subprocess_safe(["git", "reset", "--hard", "origin/main"], cwd=REPO_DIR)
        run_subprocess_safe(["git", "clean", "-fd"], cwd=REPO_DIR)


def cleanup_stale_branch(branch_name: str):
    run_subprocess_safe(["git", "branch", "-D", branch_name], cwd=REPO_DIR, raise_on_error=False)
    run_subprocess_safe(["git", "push", "origin", "--delete", branch_name], cwd=REPO_DIR, raise_on_error=False)


def create_fix_branch(branch_name: str) -> bool:
    run_subprocess_safe(["git", "checkout", "main"], cwd=REPO_DIR, raise_on_error=False)
    run_subprocess_safe(["git", "pull", "--ff-only", "origin", "main"], cwd=REPO_DIR, raise_on_error=False)
    run_subprocess_safe(["git", "branch", "-D", branch_name], cwd=REPO_DIR, raise_on_error=False)
    _, code = run_subprocess_safe(["git", "checkout", "-b", branch_name], cwd=REPO_DIR, raise_on_error=False)
    return code == 0


def ensure_fix_committed(test_path: str) -> None:
    status, _ = run_subprocess_safe(["git", "status", "--porcelain"], cwd=REPO_DIR, raise_on_error=False)
    if not status.strip():
        return
    run_subprocess_safe(["git", "add", "."], cwd=REPO_DIR, raise_on_error=False)
    message = f"[Rhodawk] Auto-heal {os.path.basename(test_path)}"
    run_subprocess_safe(["git", "commit", "-m", message], cwd=REPO_DIR, raise_on_error=False)


def push_fix_branch(branch_name: str) -> bool:
    _, code = run_subprocess_safe(["git", "push", "-u", "origin", branch_name], cwd=REPO_DIR, raise_on_error=False)
    return code == 0


def create_github_pr(repo: str, branch: str, test_path: str, token: str) -> str:
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-API-Version": "2022-11-28",
    }
    payload = {
        "title": f"[Rhodawk] Auto-heal: {os.path.basename(test_path)}",
        "head": branch,
        "base": "main",
        "body": (
            "## Rhodawk AI Autonomous Fix\n\n"
            "This PR was generated autonomously by Rhodawk AI v3.0.\n"
            "- Tests verified green after fix\n"
            "- SAST gate passed\n"
            "- Supply chain gate passed\n"
            "- Adversarial LLM review completed\n\n"
            f"**Test fixed:** `{test_path}`\n"
        ),
        "draft": False,
    }
    resp = requests.post(
        f"https://api.github.com/repos/{repo}/pulls",
        headers=headers,
        json=payload,
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()["html_url"]


def get_current_diff() -> str:
    try:
        diff, _ = run_subprocess_safe(["git", "diff", "HEAD~1", "HEAD", "--unified=3"], cwd=REPO_DIR, raise_on_error=False)
        return diff
    except Exception:
        try:
            diff, _ = run_subprocess_safe(["git", "diff", "--unified=3"], cwd=REPO_DIR, raise_on_error=False)
            return diff
        except Exception:
            return ""


def get_changed_files() -> list[str]:
    try:
        out, _ = run_subprocess_safe(["git", "diff", "--name-only", "HEAD~1", "HEAD"], cwd=REPO_DIR, raise_on_error=False)
        return [f.strip() for f in out.splitlines() if f.strip()]
    except Exception:
        return []


def setup_target_venv() -> str:
    import sys as _sys

    # FIX: ensure /data (PERSISTENT_DIR) exists before writing into it.
    os.makedirs(PERSISTENT_DIR, exist_ok=True)

    if not os.path.exists(VENV_DIR):
        ui_log("Creating isolated virtualenv via uv...")
        # FIX: pass --python explicitly; without it uv exits 2 on Space restarts
        # when its managed-Python cache is cold or UV_PYTHON is unresolvable.
        _, code = run_subprocess_safe(
            ["uv", "venv", "--python", _sys.executable, VENV_DIR],
            cwd="/tmp", raise_on_error=False,
        )
        if code != 0:
            # FIX: fallback to stdlib venv so the audit can continue even when
            # uv's Python resolution fails inside the container.
            ui_log(f"⚠️  uv venv failed (exit {code}) — falling back to python -m venv...")
            run_subprocess_safe(
                [_sys.executable, "-m", "venv", VENV_DIR],
                cwd="/tmp", raise_on_error=True,
            )

    pytest_bin = os.path.join(VENV_DIR, "bin", "pytest")
    req_path = os.path.join(REPO_DIR, "requirements.txt")
    if os.path.exists(req_path):
        ui_log("Installing target repo deps via uv...")
        run_subprocess_safe(
            ["uv", "pip", "install", "--python", VENV_DIR, "--quiet", "-r", req_path],
            cwd=REPO_DIR, timeout=600, raise_on_error=False,
        )
    return pytest_bin


# ──────────────────────────────────────────────────────────────
# AIDER RUNNER
# ──────────────────────────────────────────────────────────────
def run_aider(mcp_config_path: str, prompt: str, context_files: list[str]) -> tuple[str, int]:
    fd, prompt_path = tempfile.mkstemp(prefix="aider_prompt_", suffix=".txt")
    try:
        with os.fdopen(fd, "w") as f:
            f.write(prompt)
        valid = [f for f in context_files if os.path.exists(os.path.join(REPO_DIR, f))]
        cmd = ["aider", "--model", MODEL, "--yes", "--no-stream",
               "--message-file", prompt_path]
        if mcp_config_path and os.path.exists(mcp_config_path):
            cmd += ["--mcp-config", mcp_config_path]
        cmd += valid
        return run_subprocess_safe(cmd, cwd=REPO_DIR, timeout=600,
                                   env_overrides={"OPENROUTER_API_KEY": OPENROUTER_API_KEY},
                                   raise_on_error=False)
    finally:
        try:
            os.unlink(prompt_path)
        except OSError:
            pass


# ──────────────────────────────────────────────────────────────
# THE FULL LOOP
# ──────────────────────────────────────────────────────────────
def process_failing_test(
    test_path: str,
    initial_failure: str,
    env_config: EnvConfig,
    mcp_config_path: str,
    job_id: str,
    branch_name: str,
    target_repo: str = "",          # ← added: passed from audit loop
) -> VerificationResult:
    """
    Core autonomous healing loop:
      memory retrieval → aider fix → test verification → adversarial review
      → SAST gate → supply chain gate → PR open
    Retries up to MAX_RETRIES with accumulating context.
    """
    repo_ref = target_repo or GITHUB_REPO   # fall back to env var if not supplied
    filename = os.path.basename(test_path)
    src_file = test_path.replace("test_", "")
    context_files = [test_path]

    if os.path.exists(os.path.join(REPO_DIR, src_file)):
        context_files.append(src_file)
    else:
        fallback_src = f"src/{filename.replace('test_', '')}"
        if os.path.exists(os.path.join(REPO_DIR, fallback_src)):
            src_file = fallback_src
            context_files.append(src_file)

    if os.path.exists(os.path.join(REPO_DIR, "requirements.txt")):
        context_files.append("requirements.txt")

    attempt_history: list[VerificationAttempt] = []
    current_failure = initial_failure

    cleanup_stale_branch(branch_name)
    if not create_fix_branch(branch_name):
        return VerificationResult(
            success=False,
            attempts=attempt_history,
            failure_reason=f"Unable to create fix branch {branch_name}",
        )

    max_total_attempts = MAX_RETRIES + max(0, ADVERSARIAL_REJECTION_MULTIPLIER)
    for attempt_num in range(1, max_total_attempts + 1):
        ui_log(f"Attempt {attempt_num}/{max_total_attempts}: {test_path}", "RETRY" if attempt_num > 1 else "INFO")

        # ── Step 1: Retrieve similar fixes ──────────────────────
        try:
            similar_fixes = retrieve_similar_fixes_v2(current_failure, top_k=3)
        except Exception:
            similar_fixes = retrieve_similar_fixes(current_failure, top_k=3)
        if similar_fixes:
            ui_log(f"Memory: found {len(similar_fixes)} similar past fix(es) (best similarity: {similar_fixes[0]['similarity']})", "MEM")

        # ── Step 2: Build prompt ────────────────────────────────
        if attempt_num == 1:
            prompt = build_initial_prompt(test_path, src_file, branch_name, current_failure, similar_fixes, repo_dir=REPO_DIR)
        else:
            prompt = build_retry_prompt(test_path, src_file, branch_name, initial_failure, attempt_history, similar_fixes, repo_dir=REPO_DIR)

        prompt_hash = hashlib.sha256(prompt.encode()).hexdigest()[:16]

        log_audit_event("AIDER_DISPATCH", job_id, repo_ref, MODEL, {
            "test": test_path, "attempt": attempt_num, "prompt_hash": prompt_hash,
            "memory_hits": len(similar_fixes),
        }, "DISPATCHED")

        # ── Step 3: Run Aider ───────────────────────────────────
        aider_output, aider_code = run_aider(mcp_config_path, prompt, context_files)

        if aider_code != 0:
            ui_log(f"Aider non-zero exit on attempt {attempt_num}", "WARN")
            ui_log(f"AIDER CRASH REASON: {aider_output.strip()[:800]}", "FAIL")
            attempt_history.append(VerificationAttempt(
                attempt_number=attempt_num, prompt_hash=prompt_hash,
                aider_exit_code=aider_code, test_exit_code=-1,
                test_output="Aider failed to produce output", diff_produced="",
            ))
            record_fix_outcome(current_failure, test_path, "", success=False)
            if attempt_num < max_total_attempts:
                time.sleep(5)
                continue
            return VerificationResult(success=False, attempts=attempt_history,
                                      failure_reason=f"Aider failed on all {MAX_RETRIES} attempts")

        # ── Step 4: Get diff ─────────────────────────────────────
        diff_text = get_current_diff()
        changed_files = get_changed_files()

        # ── Step 5: RE-RUN TESTS ────────────────────────────────
        ui_log(f"Verifying fix — re-running tests (attempt {attempt_num})...", "INFO")
        test_output, test_code = _active_runtime.run_tests(
            test_path, REPO_DIR, env_config, timeout=120
        )

        attempt = VerificationAttempt(
            attempt_number=attempt_num, prompt_hash=prompt_hash,
            aider_exit_code=aider_code, test_exit_code=test_code,
            test_output=test_output, diff_produced=diff_text,
        )
        attempt_history.append(attempt)

        # ── Step 6: SAST gate ────────────────────────────────────
        ui_log("Running SAST gate on AI diff...", "SAST")
        sast_report = _active_runtime.run_sast(diff_text, changed_files, REPO_DIR)
        log_audit_event("SAST_SCAN", job_id, repo_ref, MODEL, {
            "attempt": attempt_num, "passed": sast_report.passed,
            "findings": len(sast_report.findings), "blocked_reason": sast_report.blocked_reason,
        }, "PASSED" if sast_report.passed else "BLOCKED")

        if not sast_report.passed:
            ui_log(f"SAST BLOCKED: {sast_report.blocked_reason}", "SAST")
            notify_sast_blocked(test_path, sast_report.blocked_reason)
            record_fix_outcome(current_failure, test_path, diff_text, success=False)
            run_subprocess_safe(["git", "checkout", "."], cwd=REPO_DIR, raise_on_error=False)
            current_failure = f"Previous fix was SAST-blocked: {sast_report.blocked_reason}\n\nOriginal failure:\n{initial_failure}"
            if attempt_num < max_total_attempts:
                continue
            return VerificationResult(success=False, attempts=attempt_history,
                                      failure_reason="SAST gate blocked all attempts")

        # ── Step 7: Supply chain gate ────────────────────────────
        ui_log("Running supply chain gate...", "SUPPLY")
        sc_report = _active_runtime.run_supply_chain(diff_text, REPO_DIR)
        log_audit_event("SUPPLY_CHAIN_SCAN", job_id, repo_ref, MODEL, {
            "attempt": attempt_num, "passed": sc_report.passed,
            "new_packages": sc_report.new_packages, "blocked_reason": sc_report.blocked_reason,
        }, "PASSED" if sc_report.passed else "BLOCKED")

        if not sc_report.passed:
            ui_log(f"SUPPLY CHAIN BLOCKED: {sc_report.blocked_reason}", "SUPPLY")
            run_subprocess_safe(["git", "checkout", "."], cwd=REPO_DIR, raise_on_error=False)
            current_failure = f"Previous fix introduced supply chain risk: {sc_report.blocked_reason}\n\nOriginal:\n{initial_failure}"
            if attempt_num < max_total_attempts:
                continue
            return VerificationResult(success=False, attempts=attempt_history,
                                      failure_reason="Supply chain gate blocked all attempts")

        # ── Step 7b: Z3 FORMAL VERIFICATION ─────────────────────
        z3_result = run_formal_verification(diff_text)
        if z3_result["verdict"] == "UNSAFE":
            ui_log(f"Z3 formal verification UNSAFE: {z3_result['summary']}", "SAST")
            log_audit_event("Z3_UNSAFE", job_id, repo_ref, MODEL, {
                "attempt": attempt_num, "issues": z3_result["issues"],
                "summary": z3_result["summary"],
            }, "BLOCKED")
            record_fix_outcome(current_failure, test_path, diff_text, success=False)
            run_subprocess_safe(["git", "checkout", "."], cwd=REPO_DIR, raise_on_error=False)
            issues_text = "\n".join(z3_result["issues"])
            current_failure = (
                f"Your previous fix was REJECTED by Z3 formal verification.\n"
                f"Issues:\n{issues_text}\n\n"
                f"Original:\n{initial_failure}"
            )
            if attempt_num < max_total_attempts:
                continue
            return VerificationResult(success=False, attempts=attempt_history,
                                      failure_reason="Z3 formal verification rejected all attempts")
        elif z3_result["verdict"] == "SAFE":
            ui_log(f"Z3: {z3_result['summary']}", "INFO")

        # ── Step 8: ADVERSARIAL LLM REVIEW ──────────────────────
        ui_log("Dispatching adversarial reviewer (red team)...", "ADV")
        adv_review = run_adversarial_review(diff_text, test_path, initial_failure, repo_ref)
        verdict = adv_review.get("verdict", "CONDITIONAL")

        log_audit_event("ADVERSARIAL_REVIEW", job_id, repo_ref, MODEL, {
            "attempt": attempt_num, "verdict": verdict,
            "model": adv_review.get("model_used"), "review_hash": adv_review.get("review_hash"),
            "critical_issues": adv_review.get("critical_issues", []),
            "summary": adv_review.get("summary", ""),
        }, verdict)

        if adv_review.get("warnings"):
            for w in adv_review["warnings"]:
                ui_log(f"Adversary warning: {w}", "ADV")

        if verdict == "REJECT":
            ui_log(f"ADVERSARIAL REJECTED: {adv_review.get('summary', '')}", "ADV")
            for issue in adv_review.get("critical_issues", []):
                ui_log(f"  Critical: {issue}", "ADV")
            record_fix_outcome(current_failure, test_path, diff_text, success=False)
            run_subprocess_safe(["git", "checkout", "."], cwd=REPO_DIR, raise_on_error=False)
            critique = adv_review.get("retry_guidance", "")
            issues = "\n".join(adv_review.get("critical_issues", []))
            current_failure = (
                f"Your previous fix was REJECTED by adversarial review.\n"
                f"Critical issues found:\n{issues}\n"
                f"Guidance: {critique}\n\n"
                f"Original failure:\n{initial_failure}"
            )
            if attempt_num < max_total_attempts:
                continue
            return VerificationResult(success=False, attempts=attempt_history,
                                      failure_reason="Adversarial reviewer rejected all attempts")

        # ── Step 9: Check if tests pass ──────────────────────────
        if test_code != 0:
            ui_log(f"Tests still failing after attempt {attempt_num}. Retrying...", "RETRY")
            record_fix_outcome(current_failure, test_path, diff_text, success=False)
            current_failure = (
                f"Attempt {attempt_num} fix did not solve the problem.\n"
                f"New failure:\n{test_output[:1500]}\n\n"
                f"Original failure:\n{initial_failure}"
            )
            run_subprocess_safe(["git", "checkout", "."], cwd=REPO_DIR, raise_on_error=False)
            if attempt_num < max_total_attempts:
                continue
            return VerificationResult(success=False, attempts=attempt_history,
                                      failure_reason=f"Tests still failing after {MAX_RETRIES} attempts",
                                      final_test_output=test_output)

        # ── EVERYTHING PASSED ────────────────────────────────────
        ui_log(f"VERIFIED GREEN on attempt {attempt_num}: {test_path}", "OK")
        ensure_fix_committed(test_path)
        diff_text = get_current_diff()
        record_fix_outcome(current_failure, test_path, diff_text, success=True)
        return VerificationResult(
            success=True, attempts=attempt_history,
            final_diff=diff_text, final_test_output=test_output,
            total_attempts=attempt_num,
        )

    return VerificationResult(success=False, attempts=attempt_history,
                              failure_reason="Max retries exceeded")


# ──────────────────────────────────────────────────────────────
# MAIN AUDIT ORCHESTRATOR
# ──────────────────────────────────────────────────────────────
def process_audit_test(
    test_path: str,
    env_config: EnvConfig,          # ← replaces pytest_bin
    mcp_config_path: str,
    tenant_id: str,
    target_repo: str,
) -> dict:
    filename = os.path.basename(test_path)
    branch_name = f"rhodawk/auto-patch/{filename.replace('.py','').replace('_','-')}"

    current_status = get_job_status_enum(tenant_id, target_repo, test_path)
    if current_status == JobStatus.DONE:
        ui_log(f"Skipping (DONE): {test_path}", "SKIP")
        return {"skipped": True}
    if current_status == JobStatus.RUNNING:
        ui_log(f"Cleaning interrupted job: {test_path}", "WARN")
        cleanup_stale_branch(branch_name)
        safe_git_pull()

    job_id = upsert_job(tenant_id, target_repo, test_path, JobStatus.RUNNING)
    ui_log(f"Testing: {test_path} [job:{job_id}]")

    initial_output, pytest_code = _active_runtime.run_tests(
        test_path, REPO_DIR, env_config, timeout=120
    )

    if pytest_code == 0:
        ui_log(f"PASSED: {test_path}", "OK")
        upsert_job(tenant_id, target_repo, test_path, JobStatus.DONE, "tests passed")
        log_audit_event("TEST_PASS", job_id, target_repo, MODEL,
                        {"test": test_path, "attempt": 0}, "PASSED")
        record_attempt(tenant_id, target_repo, test_path, initial_output, MODEL,
                       "baseline", 0, test_passed_after=True)
        return {"success": True, "already_green": True}

    ui_log(f"FAILED: {test_path} — entering healing loop...", "FAIL")
    notify_test_failed(test_path)
    log_audit_event("TEST_FAIL", job_id, target_repo, MODEL, {"test": test_path}, "FAILED")

    result = process_failing_test(
        test_path, initial_output, env_config, mcp_config_path,
        job_id, branch_name, target_repo=target_repo,
    )

    attempt_id = record_attempt(
        tenant_id, target_repo, test_path, initial_output, MODEL,
        hashlib.sha256(initial_output.encode()).hexdigest()[:16],
        attempt_number=result.total_attempts or len(result.attempts),
        diff_produced=result.final_diff,
        test_passed_after=result.success,
    )

    if result.success:
        pr_url = ""
        fork_mode = os.getenv("RHODAWK_FORK_MODE", "false").lower() == "true"
        try:
            if push_fix_branch(branch_name):
                from github_app import open_pr_for_repo
                pr_url = open_pr_for_repo(
                    target_repo, branch_name, test_path,
                    get_github_token(target_repo), fork_mode=fork_mode,
                )
        except Exception as e:
            ui_log(f"PR creation failed for {test_path}: {e}", "WARN")

        update_test_result(attempt_id, True, pr_url)
        upsert_job(tenant_id, target_repo, test_path, JobStatus.DONE,
                   f"healed in {result.total_attempts} attempt(s) — PR submitted",
                   pr_url=pr_url, model_version=MODEL)
        if pr_url:
            notify_pr_created(test_path, pr_url)
        ui_log(f"PR submitted for {test_path} (healed in {result.total_attempts} attempt(s))", "PR")
        log_audit_event("PR_SUBMITTED", job_id, target_repo, MODEL,
                        {"test": test_path, "attempts": result.total_attempts,
                         "branch": branch_name, "pr_url": pr_url,
                         "fork_mode": fork_mode}, "SUCCESS")

        # ── Conviction auto-merge check ───────────────────────────
        if pr_url:
            try:
                last_adv = {}
                for attempt in reversed(result.attempts or []):
                    if hasattr(attempt, "adv_review") and attempt.adv_review:
                        last_adv = attempt.adv_review
                        break

                similar = retrieve_similar_fixes_v2(result.final_test_output or "", top_k=5)
                sast_count = sum(
                    len(a.sast_findings) if hasattr(a, "sast_findings") else 0
                    for a in (result.attempts or [])
                )
                sc_new_pkgs: list = []
                should_merge, conviction_reason = evaluate_conviction(
                    adversarial_review=last_adv,
                    similar_fixes=similar,
                    test_attempts=result.total_attempts or 1,
                    sast_findings_count=sast_count,
                    new_packages=sc_new_pkgs,
                )
                if should_merge:
                    token = get_github_token(target_repo)
                    ok, merge_msg = auto_merge_pr(target_repo, pr_url, token)
                    if ok:
                        ui_log(f"AUTO-MERGED: {pr_url} ({conviction_reason})", "PR")
                        log_audit_event("AUTO_MERGE", job_id, target_repo, MODEL,
                                        {"pr_url": pr_url, "reason": conviction_reason}, "MERGED")
                    else:
                        ui_log(f"Auto-merge attempted but failed: {merge_msg}", "WARN")
                else:
                    ui_log(f"Conviction not met ({conviction_reason}) — PR requires human review", "INFO")
            except Exception as e:
                ui_log(f"Conviction check error (non-blocking): {e}", "WARN")

        run_subprocess_safe(["git", "checkout", "main"], cwd=REPO_DIR, raise_on_error=False)
        safe_git_pull()
        return {"success": True, "pr_url": pr_url}

    update_test_result(attempt_id, False)
    upsert_job(tenant_id, target_repo, test_path, JobStatus.FAILED, result.failure_reason)
    notify_patch_failed(test_path)
    ui_log(f"UNRESOLVED after {MAX_RETRIES} attempts: {result.failure_reason}", "FAIL")
    log_audit_event("HEALING_EXHAUSTED", job_id, target_repo, MODEL,
                    {"test": test_path, "reason": result.failure_reason}, "FAILED")
    run_subprocess_safe(["git", "checkout", "main"], cwd=REPO_DIR, raise_on_error=False)
    safe_git_pull()
    return {"success": False, "error": result.failure_reason}


def enterprise_audit_loop(repo_override: str = None, branch: str = "main", specific_test: str = None):
    target_repo = repo_override or GITHUB_REPO
    if not target_repo:
        ui_log("No target repo configured. Enter one in the chat inbox or set GITHUB_REPO.", "FAIL")
        _audit_event.clear()
        return

    ui_log("═" * 70)
    ui_log(f"AUDIT START — Tenant: {TENANT_ID} | Repo: {target_repo} | Model: {MODEL}")
    notify_audit_start(target_repo)
    log_audit_event("AUDIT_START", "orchestrator", target_repo, MODEL,
                    {"tenant": TENANT_ID, "branch": branch}, "STARTED")

    # Prune stale completed jobs at the start of each audit run (TTL fix)
    from job_queue import prune_done_jobs
    pruned = prune_done_jobs(max_age_hours=72)
    if pruned:
        ui_log(f"Pruned {pruned} completed job(s) older than 72h from queue.", "INFO")

    cred_path = "/tmp/.git-credentials"
    try:
        configure_git_credentials()
        mcp_config_path = write_mcp_config()

        if not os.path.exists(REPO_DIR):
            ui_log("Cloning repository...")
            Repo.clone_from(f"https://github.com/{target_repo}.git", REPO_DIR)
        else:
            ui_log("Syncing to latest origin/main...")
            safe_git_pull()

        # ── Language detection ────────────────────────────────────────
        # BUG-007 FIX: acquire lock before overwriting _active_runtime so a
        # concurrent webhook-triggered audit cannot swap the runtime under
        # in-flight workers from a previous audit.
        global _active_runtime
        with _active_runtime_lock:
            _active_runtime = RuntimeFactory.for_repo(REPO_DIR)
        ui_log(f"Detected language: {_active_runtime.language.upper()}", "INFO")

        env_config = _active_runtime.setup_env(REPO_DIR, PERSISTENT_DIR)

        # ── Test discovery ────────────────────────────────────────────
        if specific_test:
            relative_tests = (
                [specific_test]
                if os.path.exists(os.path.join(REPO_DIR, specific_test))
                else []
            )
        else:
            relative_tests = _active_runtime.discover_tests(REPO_DIR)

        ui_log(f"Discovered {len(relative_tests)} test file(s) [{_active_runtime.language}].")

        pool_result = run_parallel_audit(
            relative_tests, process_audit_test,
            env_config=env_config, mcp_config_path=mcp_config_path,
            tenant_id=TENANT_ID, target_repo=target_repo,
        )
        ui_log(
            f"Worker pool complete — workers={MAX_WORKERS}, healed={pool_result['healed']}, "
            f"already_green={pool_result['already_green']}, "
            f"failed={pool_result['failed']}, skipped={pool_result['skipped']}",
            "POOL",
        )

        all_green = all(
            get_job_status_enum(TENANT_ID, target_repo, t) == JobStatus.DONE
            for t in relative_tests
        )

        if all_green and RED_TEAM_ENABLED and relative_tests:
            ui_log("All tests GREEN — activating Red Team CEGIS.", "RED")
            run_red_team_cegis(
                repo_dir=REPO_DIR,
                env_config=env_config,
                mcp_config_path=mcp_config_path,
                blue_team_fn=process_failing_test,
                tenant_id=TENANT_ID,
                log_audit_fn=log_audit_event,
                notify_fn=notify,
            )

    except Exception as e:
        ui_log(f"FATAL: {e}", "FAIL")
        notify(f"🔴 *FATAL*\n`{e}`", "ERROR")
        log_audit_event("AUDIT_CRASH", "orchestrator", target_repo, MODEL, {"error": str(e)}, "CRASHED")
        return
    finally:
        # BUG-008 FIX: Always scrub plaintext credentials from /tmp after audit
        try:
            if os.path.exists(cred_path):
                os.unlink(cred_path)
                ui_log("Git credentials file scrubbed from /tmp.", "INFO")
        except OSError:
            pass
        _audit_event.clear()

    final_metrics = get_metrics()
    training_stats = get_statistics()
    notify_audit_complete(final_metrics)

    is_valid, integrity_msg = verify_chain_integrity()
    notify_chain_integrity(is_valid, integrity_msg)

    ui_log("═" * 70)
    ui_log(
        f"AUDIT COMPLETE — Fix success rate: {training_stats['fix_success_rate']} | "
        f"SAST blocks: {training_stats['sast_blocked']} | "
        f"Adversarial rejects: {training_stats['adversarially_rejected']} | "
        f"Patterns learned: {training_stats['patterns_learned']}"
    )
    log_audit_event("AUDIT_COMPLETE", "orchestrator", target_repo, MODEL,
                    {**final_metrics, **training_stats}, "COMPLETE")

    # ── LoRA fine-tune scheduler ──────────────────────────────
    try:
        lora_status = maybe_trigger_training()
        ui_log(lora_status, "INFO")
    except Exception as e:
        ui_log(f"LoRA scheduler check failed (non-blocking): {e}", "WARN")

    # Update chat inbox with completion notice
    with _inbox_lock:
        m = final_metrics
        _inbox_history.append({"role": "user", "content": f"✅ Audit complete: `{target_repo}`"})
        _inbox_history.append({
            "role": "assistant",
            "content": (
                f"**Audit finished.**\n"
                f"- Tests scanned: {m['total']}\n"
                f"- Verified green: {m['done']}\n"
                f"- PRs generated: {m['prs_created']}\n"
                f"- SAST blocked: {m['sast_blocked']}\n"
                f"- Fix rate: {training_stats['fix_success_rate']}"
            )
        })


# ──────────────────────────────────────────────────────────────
# CHAT INBOX — target repo input
# ──────────────────────────────────────────────────────────────
def submit_repo_audit(repo_input: str, chat_history: list) -> tuple[list, str]:
    """
    Called when user submits a repo via the chat inbox.
    Validates, kicks off the audit in a background thread, and
    returns an updated chat history using the messages format.
    """
    repo = (repo_input or "").strip()

    if not repo:
        return chat_history + [
            {"role": "user", "content": "(empty)"},
            {"role": "assistant", "content": "⚠️ Please enter a repository in the format `owner/repo`."},
        ], ""

    if "/" not in repo or len(repo.split("/")) != 2:
        return chat_history + [
            {"role": "user", "content": repo},
            {"role": "assistant", "content": f'❌ Invalid format: `{repo}`\nUse `owner/repo` — e.g. `MogasalaHemagiri/Multi-Agent-Code-Stabilizer`'},
        ], repo

    if _audit_event.is_set():
        return chat_history + [
            {"role": "user", "content": repo},
            {"role": "assistant", "content": "⚠️ An audit is already running. Please wait for it to complete before submitting another repo."},
        ], ""

    _audit_event.set()
    threading.Thread(
        target=enterprise_audit_loop,
        kwargs={"repo_override": repo},
        daemon=True,
    ).start()

    return chat_history + [
        {"role": "user", "content": f"🎯 Audit: `{repo}`"},
        {
            "role": "assistant",
            "content": (
                f"🚀 **Audit started for `{repo}`**\n\n"
                f"Watch the **Live Agent Log** below for real-time progress.\n"
                f"I'll post results here when the audit completes.\n\n"
                f"_Model: `{MODEL}` · Tenant: `{TENANT_ID}`_"
            ),
        },
    ], ""


def get_inbox_history() -> list:
    """Pull any background-posted messages (e.g. audit-complete) into the chat."""
    with _inbox_lock:
        msgs = list(_inbox_history)
        _inbox_history.clear()
    return msgs or []


def trigger_audit_fn():
    """Legacy button handler — uses GITHUB_REPO env var if set."""
    if not GITHUB_REPO:
        return "⚠️ No GITHUB_REPO env var set. Use the chat inbox above to enter a repo."
    if _audit_event.is_set():
        return "⚠️ Audit already running."
    _audit_event.set()
    threading.Thread(target=enterprise_audit_loop, daemon=True).start()
    return f"🚀 Audit triggered for `{GITHUB_REPO}` — full healing loop deployed."


# ──────────────────────────────────────────────────────────────
# WEBHOOK DISPATCHER
# ──────────────────────────────────────────────────────────────
def _webhook_dispatch(**kwargs):
    if not _audit_event.is_set():
        _audit_event.set()
        threading.Thread(target=enterprise_audit_loop, kwargs=kwargs, daemon=True).start()

set_job_dispatcher(_webhook_dispatch)

# ──────────────────────────────────────────────────────────────
# AUTONOMOUS HARVESTER (antagonist mode)
# ──────────────────────────────────────────────────────────────
try:
    from repo_harvester import start_harvester
    start_harvester(dispatch_fn=_webhook_dispatch)
except Exception as _e:
    pass  # harvester is optional — disabled by default


# ──────────────────────────────────────────────────────────────
# DASHBOARD DATA GETTERS
# ──────────────────────────────────────────────────────────────
def get_live_logs() -> str:
    with _log_lock:
        return "\n".join(dashboard_logs[-100:])


def get_metrics_row():
    m = get_metrics()
    status = "🟡 Running..." if _audit_event.is_set() else "🟢 Idle / Secure"
    return (status, m["total"], m["done"], m["prs_created"], m["failed"], m["sast_blocked"])


def get_job_table() -> list[list]:
    jobs = list_all_jobs()[:30]
    rows = []
    for j in jobs:
        icons = {"DONE": "✅", "FAILED": "❌", "SAST_BLOCKED": "🛡 Blocked",
                 "RUNNING": "🔄", "PENDING": "⏳"}
        rows.append([j.get("test_path", ""), icons.get(j["status"], j["status"]),
                     j.get("pr_url", "—"), j.get("model_version", "—"), j.get("updated_at", "")])
    return rows or [["No jobs yet", "", "", "", ""]]


def get_audit_display() -> str:
    events = read_audit_trail(40)
    if not events:
        return "No audit events yet."
    lines = []
    for e in reversed(events):
        lines.append(
            f"[{e['timestamp_utc']}] {e['event_type']:25s} | {e['outcome']:10s} | "
            f"hash:{e['entry_hash'][:12]}..."
        )
    return "\n".join(lines)


def get_chain_integrity_display() -> str:
    valid, msg = verify_chain_integrity()
    return f"{'🔒 VERIFIED' if valid else '🚨 COMPROMISED'} — {msg}"


def get_training_stats_display() -> str:
    try:
        stats = get_statistics()
        mem = get_memory_stats()
        return (
            f"Total fix attempts:        {stats['total_attempts']}\n"
            f"Successful fixes:          {stats['successful_fixes']} ({stats['fix_success_rate']})\n"
            f"SAST blocked:              {stats['sast_blocked']}\n"
            f"Adversarially rejected:    {stats['adversarially_rejected']}\n"
            f"Human-merged PRs:          {stats['human_merged']}\n"
            f"Memory patterns stored:    {mem['patterns_stored']} ({mem['successful_patterns']} with success signal)\n\n"
            f"Top recurring failures:\n" +
            "\n".join(f"  {t['attempts']}x  {t['path']}" for t in stats.get("top_failing_tests", []))
        )
    except Exception as e:
        return f"Stats unavailable: {e}"


def get_training_export() -> str:
    try:
        data = export_training_data(limit=100)
        if not data:
            return "No training data yet. Run audits to accumulate (failure, fix) pairs."
        lines = data.split("\n")
        return f"# {len(lines)} training examples (JSONL format)\n# Copy and use for fine-tuning\n\n" + data[:8000]
    except Exception as e:
        return f"Export failed: {e}"


def get_webhook_log_display() -> str:
    from webhook_server import get_webhook_log
    events = get_webhook_log(30)
    if not events:
        return (
            "No webhook events yet.\n\n"
            "Webhook endpoint: POST http://this-space:7861/webhook/github\n"
            "Health check:     GET  http://this-space:7861/webhook/health"
        )
    lines = [
        f"[{e['timestamp']}] {e['event_type']:20s} | {e['status']:8s} | "
        f"{e.get('repo','')} | {e.get('detail','')}"
        for e in events
    ]
    return "\n".join(lines)


def get_red_team_display() -> str:
    stats = get_red_team_stats()
    return (
        f"Zero-days discovered: {stats['zero_days_discovered']}\n"
        f"Property-based tests generated: {stats['pbts_generated']}\n"
        f"Artifacts directory: {stats['red_team_dir']}\n\n"
        f"Recent Red Team logs:\n{stats['recent_logs']}"
    )


def trigger_swebench_eval(max_instances: int = 25) -> str:
    def _run():
        try:
            from swebench_harness import run_swebench_eval
            # BUG-009 / GAP-F FIX: Route through Rhodawk's own healing loop so
            # pass@1 metrics are produced by the same pipeline used in production,
            # not by an external stub command.
            with _active_runtime_lock:
                runtime = _active_runtime
            env_cfg = runtime.setup_env(REPO_DIR, PERSISTENT_DIR) if runtime else None
            mcp_cfg = write_mcp_config()
            result = run_swebench_eval(
                max_instances=int(max_instances),
                process_fn=process_failing_test if runtime else None,
                env_config=env_cfg,
                mcp_config_path=mcp_cfg,
                repo_dir=REPO_DIR,
            )
            ui_log(
                f"SWE-bench complete — pass@1={result['pass_at_1']:.2%}, "
                f"resolved={result['resolved']}/{result['total']} "
                f"(mode={result.get('mode', 'unknown')})",
                "BENCH",
            )
        except Exception as e:
            ui_log(f"SWE-bench eval failed: {e}", "BENCH")
    threading.Thread(target=_run, daemon=True).start()
    return f"SWE-bench Verified evaluation started for {int(max_instances)} instance(s) via Rhodawk loop."


def get_swebench_display() -> str:
    path = "/data/swebench_report.md"
    if not os.path.exists(path):
        return "No SWE-bench report yet. Start an evaluation to generate pass@1 results."
    with open(path, "r", encoding="utf-8") as f:
        return f.read()[:12000]


def export_compliance_display() -> str:
    try:
        return f"Compliance report exported: {export_compliance_report()}"
    except Exception as e:
        return f"Compliance export failed: {e}"


def reset_queue():
    import shutil
    shutil.rmtree("/data/jobs", ignore_errors=True)
    return "✅ Job queue cleared."


# ──────────────────────────────────────────────────────────────
# GRADIO ENTERPRISE DASHBOARD
# ──────────────────────────────────────────────────────────────
THEME = gr.themes.Base(
    primary_hue="violet", secondary_hue="slate", neutral_hue="slate",
    font=[gr.themes.GoogleFont("Inter"), "ui-sans-serif", "system-ui"],
).set(
    body_background_fill="#0a0a0f",
    body_text_color="#e2e8f0",
    block_background_fill="#12121c",
    block_border_color="#1e1e2e",
    block_label_text_color="#64748b",
    input_background_fill="#0a0a0f",
    button_primary_background_fill="#5b21b6",
    button_primary_background_fill_hover="#6d28d9",
    button_primary_text_color="#ffffff",
)

with gr.Blocks(title="Rhodawk AI — Code Review Monster") as demo:

    gr.HTML("""
    <div style="padding:20px 0 4px 0; border-bottom:1px solid #1e1e2e; margin-bottom:16px;">
      <div style="display:flex; align-items:center; gap:14px;">
        <span style="font-size:2.2rem;">🦅</span>
        <div>
          <h1 style="margin:0; font-size:1.5rem; font-weight:800; color:#f1f5f9; letter-spacing:-0.03em;">
            Rhodawk AI <span style="color:#7c3aed; font-size:0.9rem; font-weight:600; margin-left:8px;">v3.0</span>
          </h1>
          <p style="margin:2px 0 0; font-size:0.8rem; color:#475569; letter-spacing:0.02em;">
            AUTONOMOUS DEVSECOPS CONTROL PLANE &nbsp;·&nbsp;
            CLOSED VERIFICATION LOOP &nbsp;·&nbsp;
            ADVERSARIAL LLM REVIEW &nbsp;·&nbsp;
            DATA FLYWHEEL &nbsp;·&nbsp;
            SUPPLY CHAIN GATE
          </p>
        </div>
      </div>
    </div>
    """)

    with gr.Tabs():

        # ── TAB 1: LIVE OPERATIONS ──────────────────────────────
        with gr.Tab("⚡ Live Operations"):

            # ── STATUS BAR ──────────────────────────────────────
            with gr.Row():
                stat_status = gr.Textbox(label="System Status", interactive=False, scale=3)
                stat_total  = gr.Number(label="Tests Scanned",  interactive=False)
                stat_done   = gr.Number(label="Verified Green", interactive=False)
                stat_prs    = gr.Number(label="PRs Generated",  interactive=False)
                stat_failed = gr.Number(label="Failed",         interactive=False)
                stat_sast   = gr.Number(label="SAST Blocked",   interactive=False)

            # ── CHAT INBOX ──────────────────────────────────────
            gr.HTML("""
            <div style="margin:20px 0 8px 0; padding:12px 16px;
                        background:#0f0f1a; border:1px solid #2d2d44;
                        border-radius:10px;">
              <span style="font-size:0.85rem; font-weight:700;
                           color:#7c3aed; letter-spacing:0.06em;
                           text-transform:uppercase;">
                🎯 Audit Inbox
              </span>
              <span style="font-size:0.78rem; color:#475569; margin-left:10px;">
                Enter a GitHub repo below to launch a full autonomous healing audit
              </span>
            </div>
            """)

            inbox_chatbot = gr.Chatbot(
                label="",
                height=240,
                show_label=False,
            )

            with gr.Row():
                repo_textbox = gr.Textbox(
                    placeholder="owner/repo  (e.g. MogasalaHemagiri/Multi-Agent-Code-Stabilizer)",
                    show_label=False,
                    scale=5,
                    lines=1,
                    max_lines=1,
                    container=False,
                )
                run_btn = gr.Button("🚀 Run Audit", variant="primary", scale=1, min_width=120)

            run_btn.click(
                submit_repo_audit,
                inputs=[repo_textbox, inbox_chatbot],
                outputs=[inbox_chatbot, repo_textbox],
            )
            repo_textbox.submit(
                submit_repo_audit,
                inputs=[repo_textbox, inbox_chatbot],
                outputs=[inbox_chatbot, repo_textbox],
            )

            gr.HTML("<div style='height:4px;'></div>")

            # ── LEGACY TRIGGER ROW (uses GITHUB_REPO env if set) ─
            with gr.Row():
                btn_audit = gr.Button("🚀 Trigger Full Healing Audit (env GITHUB_REPO)", variant="secondary", scale=3)
                btn_reset = gr.Button("🗑 Reset Queue", variant="secondary", scale=1)

            trigger_out = gr.Textbox(label="", interactive=False, show_label=False)
            btn_audit.click(trigger_audit_fn, outputs=trigger_out)
            btn_reset.click(reset_queue, outputs=trigger_out)

            # ── LIVE LOG ─────────────────────────────────────────
            live_logs = gr.TextArea(label="Live Agent Execution Log", lines=26, interactive=False)

        # ── TAB 2: JOB QUEUE ───────────────────────────────────
        with gr.Tab("📋 Job Queue"):
            gr.Markdown("### Namespaced job store — per (tenant, repo, test)")
            job_table = gr.Dataframe(
                headers=["Test Path", "Status", "PR URL", "Model", "Updated At"],
                datatype=["str", "str", "str", "str", "str"], interactive=False, wrap=True,
            )
            gr.Button("🔄 Refresh", variant="secondary").click(get_job_table, outputs=job_table)

        # ── TAB 3: AUDIT TRAIL ─────────────────────────────────
        with gr.Tab("🔒 Audit Trail"):
            gr.Markdown(
                "### SHA-256 chained audit log — every AI action is cryptographically linked\n"
                "Covers: dispatch → SAST scan → supply chain → adversarial review → PR submission"
            )
            chain_status = gr.Textbox(label="Chain Integrity Status", interactive=False)
            audit_log = gr.TextArea(label="Events (latest first)", lines=20, interactive=False)
            gr.Button("🔍 Verify Chain", variant="secondary").click(
                fn=lambda: (get_chain_integrity_display(), get_audit_display()),
                outputs=[chain_status, audit_log]
            )

        # ── TAB 4: DATA FLYWHEEL ───────────────────────────────
        with gr.Tab("🧠 Data Flywheel"):
            gr.Markdown(
                "### Proprietary training data pipeline\n"
                "Every `(failure, fix, adversarial_verdict, test_result)` tuple is stored. "
                "Export as HuggingFace-compatible JSONL for model fine-tuning."
            )
            stats_display   = gr.TextArea(label="Flywheel Statistics",        lines=12, interactive=False)
            training_export = gr.TextArea(label="Training Data Export (JSONL)", lines=14, interactive=False)
            with gr.Row():
                gr.Button("📊 Refresh Stats",  variant="secondary").click(get_training_stats_display, outputs=stats_display)
                gr.Button("⬇ Export JSONL",    variant="secondary").click(get_training_export,        outputs=training_export)

        # ── TAB 5: WEBHOOKS ────────────────────────────────────
        with gr.Tab("🔗 Webhooks"):
            gr.Markdown(f"""
### Event-Driven Trigger Server (Port 7861)

```
POST /webhook/github    — GitHub push/check_run events (HMAC-SHA256 validated)
POST /webhook/ci        — Generic CI failure: {{"repo": "owner/repo", "test_path": "tests/..."}}
POST /webhook/trigger   — Manual trigger
GET  /webhook/health    — Liveness probe
GET  /webhook/queue     — Current job status (JSON)
```
            """)
            webhook_log = gr.TextArea(label="Webhook Event Log", lines=15, interactive=False)
            gr.Button("🔄 Refresh", variant="secondary").click(get_webhook_log_display, outputs=webhook_log)

        # ── TAB 6: RED TEAM ────────────────────────────────────
        with gr.Tab("⚔️ Red Team"):
            gr.Markdown(
                "### Autonomous Red Team CEGIS\n"
                "When all tests are green, Rhodawk attacks the repo with generated property-based tests "
                "and hands reproducible zero-days back to Blue Team for patching."
            )
            red_team_box = gr.TextArea(label="Red Team Stats & Logs", lines=22, interactive=False)
            gr.Button("🔄 Refresh Red Team Stats", variant="secondary").click(get_red_team_display, outputs=red_team_box)

        # ── TAB 7: SWE-BENCH ──────────────────────────────────
        with gr.Tab("🧪 SWE-bench"):
            gr.Markdown("### SWE-bench Verified Evaluation")
            with gr.Row():
                swebench_count   = gr.Number(label="Max instances", value=25, precision=0)
                swebench_start   = gr.Button("Start Evaluation",  variant="primary")
                swebench_refresh = gr.Button("Refresh Report",     variant="secondary")
            swebench_status = gr.Textbox(label="Status", interactive=False)
            swebench_report = gr.TextArea(label="SWE-bench Report", lines=24, interactive=False)
            swebench_start.click(trigger_swebench_eval, inputs=swebench_count, outputs=swebench_status)
            swebench_refresh.click(get_swebench_display, outputs=swebench_report)

        # ── TAB 8: HARVESTER (Antagonist Mode) ───────────────────
        with gr.Tab("🌐 Harvester"):
            gr.Markdown(
                "### Autonomous Repository Harvester\n"
                "Scans public GitHub for repos with failing CI and queues them for autonomous healing.\n\n"
                "**Enable:** set `RHODAWK_HARVESTER_ENABLED=true` in Space Secrets.\n"
                "**Poll interval:** `RHODAWK_HARVESTER_POLL_SECONDS` (default 21600 = 6h)\n"
                "**Fork mode:** set `RHODAWK_FORK_MODE=true` to fix repos without push access."
            )
            harvester_box = gr.TextArea(label="Harvest Feed", lines=20, interactive=False)
            gr.Button("🔄 Refresh Feed", variant="secondary").click(
                fn=lambda: __import__("repo_harvester").get_feed_summary(),
                outputs=harvester_box,
            )

        # ── TAB 9: LORA SCHEDULER ─────────────────────────────
        with gr.Tab("🧬 LoRA Scheduler"):
            gr.Markdown(
                "### LoRA Fine-Tune Scheduler\n"
                "Exports accumulated (failure → fix) pairs in instruction-tuning JSONL format "
                "when the data threshold is reached.\n\n"
                "**Enable:** set `RHODAWK_LORA_ENABLED=true`\n"
                "**Min samples:** `RHODAWK_LORA_MIN_SAMPLES` (default 50)\n"
                "**Max age:** `RHODAWK_LORA_MAX_AGE_HOURS` (default 168h = 1 week)\n"
                "**Output:** `/data/lora_exports/lora_training_data_*.jsonl`"
            )
            lora_status_box = gr.TextArea(label="Scheduler Status", lines=10, interactive=False)
            lora_export_btn = gr.Button("⬇ Force Export Now", variant="secondary")
            lora_result_box = gr.TextArea(label="Export Result", lines=5, interactive=False)

            def _force_lora_export():
                try:
                    from lora_scheduler import run_training_export
                    result = run_training_export()
                    return str(result)
                except Exception as e:
                    return f"Export error: {e}"

            gr.Button("🔄 Refresh Status", variant="secondary").click(
                get_scheduler_status, outputs=lora_status_box
            )
            lora_export_btn.click(_force_lora_export, outputs=lora_result_box)

        # ── TAB 10: ARCHITECTURE ──────────────────────────────
        with gr.Tab("ℹ️ Architecture"):
            compliance_out = gr.Textbox(label="Compliance Export", interactive=False)
            gr.Button("Export SOC 2 Evidence Summary", variant="secondary").click(
                export_compliance_display, outputs=compliance_out
            )
            gr.Markdown(f"""
### Rhodawk AI v4.0 — Capability Stack

**Tenant:** `{TENANT_ID}` | **Model:** `{MODEL}`
> Target repo is supplied at runtime via the **Audit Inbox** chat input (no restart required).

---

| Layer | Technology | What it does |
|---|---|---|
| AI Agent | Aider + OpenRouter/Qwen | Autonomous patch generation |
| MCP Tools | fetch-docs, github-manager | Documentation + PR creation |
| **Verification Loop** | Any-language test re-run per attempt | **Closes the loop — tests the fix before PR** |
| **Adversarial Review** | 3-model concurrent consensus (Qwen∥Gemma∥Mistral) | **Majority vote, 2/3 threshold** |
| **Formal Verification** | Z3 SMT solver (bounds + div-by-zero) | **Math-verified integer safety** |
| **Conviction Engine** | Multi-criteria trust gate | **Auto-merges PRs meeting all safety criteria** |
| **Memory Engine** | SQLite + optional Qdrant/CodeBERT | **Cross-repo semantic retrieval of similar fixes** |
| **Supply Chain Gate** | pip-audit + typosquatting + PyPI metadata | **Catches malicious dependencies in AI diffs** |
| **LoRA Scheduler** | SFT JSONL exporter | **Exports proprietary training data on schedule** |
| **Repo Harvester** | GitHub search + failing CI detector | **Autonomous target selection (antagonist mode)** |
| **Fork-and-PR Mode** | Cross-repo PR creation via fork | **Fix any public repo without push access** |
| **Process Isolation** | multiprocessing.Process per job | **Crash-safe per-test subprocess isolation** |
| SAST Gate | bandit + semgrep + secret/injection patterns | Pre-PR security scanning |
| Audit Trail | SHA-256 JSONL chain | SOC 2 / ISO 27001 evidence |
| Training Store | SQLite (failure→fix→outcome) | Fine-tuning dataset accumulation |
| Webhook Server | HTTP on :7861 + HMAC + rate limit | Event-driven GitHub/CI triggers |
| Worker Pool | ThreadPoolExecutor | Parallel audit execution |
| Language Support | Python / JS / TS / Java / Go / Rust / Ruby | Any-language test healing |
| SWE-bench Harness | SWE-bench Verified | pass@1 benchmarking reports |
| Notifications | Telegram + Slack | Multi-channel alerting |
| Virtualenv | uv | Blazing-fast isolated Python env |

---

### New in v4.0

**Peak enhancements:**
- Concurrent 3-model adversarial consensus (Qwen∥Gemma∥Mistral, 2/3 majority threshold)
- Z3 SMT solver for bounded formal verification of integer arithmetic and bounds in diffs
- Qdrant + CodeBERT embedding backend (set `RHODAWK_EMBEDDING_BACKEND=qdrant`)
- Conviction engine — autonomous merge when all trust criteria are simultaneously satisfied
- LoRA fine-tune scheduler — automatic training data export when threshold reached
- Process isolation per test job (`RHODAWK_PROCESS_ISOLATE=true`)

**Antagonist additions:**
- Repository harvester — scans GitHub for failing CI, queues targets autonomously
- Fork-and-PR mode — fix any public repo, no push access required (`RHODAWK_FORK_MODE=true`)
- 24/7 continuous loop via harvester dispatch → audit → heal → PR cycle
- Public leaderboard (`public_leaderboard.py`) — real numbers, real PRs, no fake metrics
            """)

    # ── AUTO-REFRESH ────────────────────────────────────────────
    timer = gr.Timer(3)
    timer.tick(get_live_logs,   outputs=live_logs)
    timer.tick(get_metrics_row, outputs=[stat_status, stat_total, stat_done, stat_prs, stat_failed, stat_sast])

    demo.load(get_live_logs,            outputs=live_logs)
    demo.load(get_metrics_row,          outputs=[stat_status, stat_total, stat_done, stat_prs, stat_failed, stat_sast])
    demo.load(get_job_table,            outputs=job_table)
    demo.load(get_audit_display,        outputs=audit_log)
    demo.load(get_chain_integrity_display, outputs=chain_status)
    demo.load(get_training_stats_display,  outputs=stats_display)
    demo.load(get_webhook_log_display,  outputs=webhook_log)
    demo.load(get_red_team_display,     outputs=red_team_box)
    demo.load(get_swebench_display,     outputs=swebench_report)


if __name__ == "__main__":
    ui_log(f"Rhodawk AI v3.0 starting — Tenant: {TENANT_ID} | Model: {MODEL}")

    # MINOR BUG FIX: Pre-warm the embedding model in a background thread so the
    # first real retrieval call does not block on a multi-second model download.
    def _prewarm():
        try:
            from embedding_memory import pre_warm_model
            ok = pre_warm_model()
            ui_log(
                "Embedding model pre-warmed successfully." if ok
                else "Embedding model pre-warm failed — will retry on first use.",
                "MEM"
            )
        except Exception as _e:
            ui_log(f"Embedding model pre-warm error (non-fatal): {_e}", "MEM")

    threading.Thread(target=_prewarm, daemon=True).start()

    ui_log("Starting webhook server on port 7861...")
    start_webhook_server()
    ui_log("Webhook server running. Launching dashboard...")
    port = int(os.environ.get("PORT", 7860))
    demo.launch(server_name="0.0.0.0", server_port=port, share=False, show_error=True, theme=THEME)

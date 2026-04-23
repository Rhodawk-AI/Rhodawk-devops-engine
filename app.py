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
import shutil
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
from hermes_orchestrator import (
    run_hermes_research, get_hermes_logs, get_session_summary,
    compute_ves, build_tvg,
)
from bounty_gateway import (
    get_pipeline, get_pipeline_summary, human_approve, human_reject,
    submit_to_hackerone, submit_github_advisory, add_to_pipeline,
)
from vuln_classifier import classify_vulnerability, get_all_cwes
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
from language_runtime import RuntimeFactory, LanguageRuntime, EnvConfig, kill_runtime_processes

# ── Mythos-level upgrade integration ────────────────────────────────────────
# Imports below are all wrapped: a missing optional native dep (Joern, KLEE,
# pwntools, …) MUST never break Rhodawk boot. The package itself is pure
# Python; every heavy bridge has an `available()` guard.
try:
    from mythos import MYTHOS_VERSION, build_default_orchestrator
    from mythos.integration import mythos_enabled, maybe_run_mythos
    from mythos.diagnostics import availability_matrix as mythos_availability_matrix
    _MYTHOS_OK = True
    _MYTHOS_IMPORT_ERR = ""
except Exception as _e:  # noqa: BLE001
    MYTHOS_VERSION = "unavailable"
    _MYTHOS_OK = False
    _MYTHOS_IMPORT_ERR = f"{type(_e).__name__}: {_e}"

    def mythos_enabled() -> bool:
        return False

    def maybe_run_mythos(target):
        return None

    def mythos_availability_matrix():
        return {"_error": _MYTHOS_IMPORT_ERR}

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

# ── DigitalOcean Serverless Inference (PRIMARY) ──────────────────────────
# OpenAI-compatible endpoint. Uses an OpenAI-style API surface so we can
# reuse aider via --openai-api-base / --openai-api-key.
# Get an API key from: https://cloud.digitalocean.com/gen-ai/agents (Inference)
DO_INFERENCE_API_KEY = os.getenv("DO_INFERENCE_API_KEY") or os.getenv("DIGITALOCEAN_INFERENCE_KEY")
DO_INFERENCE_BASE_URL = os.getenv("DO_INFERENCE_BASE_URL", "https://inference.do-ai.run/v1").rstrip("/")
DO_INFERENCE_MODEL = os.getenv("DO_INFERENCE_MODEL", "llama3.3-70b-instruct")

TENANT_ID = os.getenv("RHODAWK_TENANT_ID", "default")
# Default Aider model — DO inference primary, OpenRouter fallback.
# When DO_INFERENCE_API_KEY is set we hand aider an `openai/<model>` route
# pointed at DigitalOcean. Otherwise we fall back to the OpenRouter model.
_DEFAULT_AIDER_MODEL = (
    f"openai/{DO_INFERENCE_MODEL}" if DO_INFERENCE_API_KEY
    else "openrouter/qwen/qwen-2.5-coder-32b-instruct:free"
)
MODEL = os.getenv("RHODAWK_MODEL", _DEFAULT_AIDER_MODEL)
# Explicit fallback model (always OpenRouter) — used if DO inference fails.
FALLBACK_MODEL = os.getenv(
    "RHODAWK_FALLBACK_MODEL",
    "openrouter/qwen/qwen-2.5-coder-32b-instruct:free",
)
RED_TEAM_ENABLED = os.getenv("RHODAWK_RED_TEAM_ENABLED", "true").lower() != "false"
PAID_API_KEY_WARNING = (
    "Please use a PAID API KEY without rate limits. Free-tier API keys usually hit "
    "8 to 9 requests per minute, but this system needs 25+ requests per minute and "
    "high context windows."
)

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
REPO_DIR = f"{PERSISTENT_DIR}/repo"          # default; overridden per-audit below
VENV_DIR = f"{PERSISTENT_DIR}/target_venv"
MCP_RUNTIME_CONFIG = "/tmp/mcp_runtime.json"

# ── Per-audit repo dir — updated atomically at audit start ────────────────────
# Because _audit_event ensures only one audit runs at a time, updating this
# global at audit start is safe without an additional lock.
_current_target_repo: str = ""

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
_active_process_groups: set[int] = set()
_process_lock = threading.Lock()

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
    pgid = None
    try:
        proc = subprocess.Popen(cmd, shell=False, cwd=cwd, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, text=True, env=env, start_new_session=True)
        try:
            pgid = os.getpgid(proc.pid)
            with _process_lock:
                _active_process_groups.add(pgid)
        except ProcessLookupError:
            pgid = None
        stdout, stderr = proc.communicate(timeout=timeout)
        output = (stdout or "") + "\n" + (stderr or "")
        if raise_on_error and proc.returncode != 0:
            raise subprocess.CalledProcessError(proc.returncode, cmd, stdout, stderr)
        return output, proc.returncode
    except FileNotFoundError as e:
        if raise_on_error:
            raise
        return str(e), 127
    except subprocess.TimeoutExpired:
        if proc:
            try:
                os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
            except ProcessLookupError:
                pass
            proc.communicate()
        raise RuntimeError(f"Command timed out after {timeout}s: {cmd[0]}")
    finally:
        if pgid is not None:
            with _process_lock:
                _active_process_groups.discard(pgid)


def _kill_active_processes() -> int:
    with _process_lock:
        groups = list(_active_process_groups)
        _active_process_groups.clear()
    killed = kill_runtime_processes()
    for pgid in groups:
        try:
            os.killpg(pgid, signal.SIGTERM)
            killed += 1
        except ProcessLookupError:
            continue
    time.sleep(0.2)
    for pgid in groups:
        try:
            os.killpg(pgid, signal.SIGKILL)
        except ProcessLookupError:
            continue
    return killed


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
    """
    Write the full 25-server cybersecurity MCP config to /tmp/mcp_runtime.json.
    Secrets are injected from environment at runtime — never stored in source.
    Rhodawk AI v5.0 — OpenClaw Hermes agent MCP suite.
    """
    _fetch_domains = ",".join(_active_runtime.get_mcp_domains()) if _active_runtime else (
        "docs.python.org,pypi.org,docs.github.com,packaging.python.org,peps.python.org,"
        "cwe.mitre.org,nvd.nist.gov,owasp.org,portswigger.net,hackerone.com,bugcrowd.com,"
        "cve.org,exploit-db.com,docs.rs,go.dev,nodejs.org,developer.mozilla.org,shodan.io,"
        "virustotal.com,osv.dev,snyk.io,vulners.com,seclists.org,packetstormsecurity.com,"
        "securityfocus.com,cisa.gov,zerodayinitiative.com,huntr.com,intigriti.com,"
        "yeswehack.com,vdp.hackerone.com,api.github.com,raw.githubusercontent.com,"
        "archive.org,web.archive.org,semgrep.dev,rules.semgrep.dev,github.com,"
        "security.snyk.io,opencve.io,vuldb.com,rapid7.com,metasploit.com,www.rapid7.com"
    )

    _brave_key = os.getenv("BRAVE_API_KEY", "")
    _hackerone_token = os.getenv("HACKERONE_API_TOKEN", "")
    _hackerone_key = os.getenv("HACKERONE_API_KEY", "")
    _nvd_key = os.getenv("NVD_API_KEY", "")
    _semgrep_token = os.getenv("SEMGREP_APP_TOKEN", "")
    _nuclei_key = os.getenv("NUCLEI_API_KEY", "")
    _db_url = os.getenv("DATABASE_URL", "")
    _openrouter_key = os.getenv("OPENROUTER_API_KEY", "")

    config = {
        "mcpServers": {
            "fetch-docs": {
                "command": "uvx",
                "args": ["mcp-server-fetch"],
                "description": "Fetch security docs, CVE advisories, exploit PoCs, and vendor bulletins",
                "env": {"FETCH_ALLOWED_DOMAINS": _fetch_domains}
            },
            "github-manager": {
                "command": "npx",
                "args": ["-y", "@modelcontextprotocol/server-github"],
                "description": "GitHub API: create PRs, open security advisories, manage issues, query commit history",
                "env": {"GITHUB_PERSONAL_ACCESS_TOKEN": GITHUB_TOKEN}
            },
            "filesystem-research": {
                "command": "npx",
                "args": ["-y", "@modelcontextprotocol/server-filesystem",
                         "/data/repo", "/tmp/research", "/tmp/findings"],
                "description": "Read-only access to cloned repos, research scratch space, and findings output"
            },
            "memory-store": {
                "command": "npx",
                "args": ["-y", "@modelcontextprotocol/server-memory"],
                "description": "Persistent knowledge graph — exploit chains, CWE patterns, cross-session vulnerability memory"
            },
            "sequential-thinking": {
                "command": "npx",
                "args": ["-y", "@modelcontextprotocol/server-sequential-thinking"],
                "description": "Structured chain-of-thought for complex multi-step vulnerability analysis"
            },
            "web-search": {
                "command": "npx",
                "args": ["-y", "@modelcontextprotocol/server-brave-search"],
                "description": "Search CVEs, exploit PoCs, vendor advisories, bug bounty writeups, security research",
                "env": {"BRAVE_API_KEY": _brave_key}
            },
            "git-forensics": {
                "command": "npx",
                "args": ["-y", "@modelcontextprotocol/server-git", "--repository", "/data/repo"],
                "description": "Deep git history: silent security patches (CAD), blame tracking, commit anomaly detection"
            },
            "sqlite-findings": {
                "command": "npx",
                "args": ["-y", "@modelcontextprotocol/server-sqlite",
                         "--db-path", "/data/rhodawk_findings.db"],
                "description": "Local findings store — fast queries on vulnerability metadata, CVSS scores, bounty estimates"
            },
            "nuclei-scanner": {
                "command": "uvx",
                "args": ["mcp-server-shell", "--allow-commands", "nuclei"],
                "description": "Nuclei template-based DAST — CVE detection, misconfig scanning, web vulnerability discovery",
                "env": {
                    "NUCLEI_TEMPLATES_PATH": "/data/nuclei-templates",
                    "NUCLEI_API_KEY": _nuclei_key
                }
            },
            "semgrep-sast": {
                "command": "uvx",
                "args": ["mcp-server-shell", "--allow-commands", "semgrep"],
                "description": "Semgrep SAST — taint analysis, CWE patterns, secrets detection across 30+ languages",
                "env": {"SEMGREP_APP_TOKEN": _semgrep_token}
            },
            "trufflehog-secrets": {
                "command": "uvx",
                "args": ["mcp-server-shell", "--allow-commands", "trufflehog"],
                "description": "TruffleHog v3 — high-signal secret scanning with 700+ detectors across git history"
            },
            "bandit-sast": {
                "command": "uvx",
                "args": ["mcp-server-shell", "--allow-commands", "bandit"],
                "description": "Bandit Python SAST — AST-level detection of dangerous patterns and injection sinks"
            },
            "pip-audit-sca": {
                "command": "uvx",
                "args": ["mcp-server-shell", "--allow-commands", "pip-audit"],
                "description": "pip-audit SCA — known vulnerabilities in Python dependencies via OSV and PyPI Advisory DB"
            },
            "osv-scanner": {
                "command": "uvx",
                "args": ["mcp-server-shell", "--allow-commands", "osv-scanner"],
                "description": "OSV Scanner — multi-ecosystem SCA using the Open Source Vulnerability database (Google)"
            },
            "z3-formal-verifier": {
                "command": "uvx",
                "args": ["mcp-server-shell", "--allow-commands", "python3"],
                "description": "Z3 SMT solver — formal verification of integer bounds, overflow invariants, protocol properties"
            },
            "hypothesis-fuzzer": {
                "command": "uvx",
                "args": ["mcp-server-shell", "--allow-commands", "python3,pytest"],
                "description": "Hypothesis PBT fuzzer — property-based testing for overflow, encoding, aliasing bugs"
            },
            "atheris-fuzzer": {
                "command": "uvx",
                "args": ["mcp-server-shell", "--allow-commands", "python3"],
                "description": "Atheris coverage-guided fuzzer — libFuzzer-backed Python fuzzing for parser and protocol bugs"
            },
            "angr-symbolic": {
                "command": "uvx",
                "args": ["mcp-server-shell", "--allow-commands", "python3"],
                "description": "angr symbolic execution — binary analysis, path exploration, constraint solving"
            },
            "radon-complexity": {
                "command": "uvx",
                "args": ["mcp-server-shell", "--allow-commands", "radon"],
                "description": "Radon AST complexity analysis — cyclomatic complexity, attack surface ranking"
            },
            "ruff-linter": {
                "command": "uvx",
                "args": ["mcp-server-shell", "--allow-commands", "ruff"],
                "description": "Ruff ultra-fast Python linter — anti-patterns correlating with security bugs"
            },
            # aider-patcher removed — code generation now flows through the
            # vendored OpenClaude headless gRPC daemon (see openclaude_grpc/).
            # The model itself talks to the rest of the MCP suite directly,
            # so no recursive "patcher" MCP server is needed.
            "cve-intelligence": {
                "command": "uvx",
                "args": ["mcp-server-fetch"],
                "description": "NVD/NIST CVE API — full CVE details, CVSS vectors, CWE mappings, affected versions",
                "env": {
                    "FETCH_ALLOWED_DOMAINS": (
                        "nvd.nist.gov,cve.org,cve.mitre.org,www.cvedetails.com,"
                        "vulners.com,osv.dev,opencve.io"
                    ),
                    "NVD_API_KEY": _nvd_key
                }
            },
            "bounty-platform": {
                "command": "uvx",
                "args": ["mcp-server-fetch"],
                "description": "Bug bounty APIs — HackerOne report submission, GitHub Security Advisories, Bugcrowd",
                "env": {
                    "FETCH_ALLOWED_DOMAINS": (
                        "api.hackerone.com,api.bugcrowd.com,api.intigriti.com,"
                        "api.yeswehack.com,api.github.com"
                    ),
                    "HACKERONE_API_TOKEN": _hackerone_token,
                    "HACKERONE_API_KEY": _hackerone_key
                }
            },
            "supply-chain-monitor": {
                "command": "uvx",
                "args": ["mcp-server-fetch"],
                "description": "Supply chain security — PyPI typosquatting, dependency confusion, malicious packages",
                "env": {
                    "FETCH_ALLOWED_DOMAINS": (
                        "pypi.org,api.pypi.org,registry.npmjs.org,crates.io,"
                        "deps.dev,socket.dev,api.socket.dev"
                    )
                }
            },
        }
    }
    os.makedirs(os.path.dirname(MCP_RUNTIME_CONFIG), exist_ok=True)
    with open(MCP_RUNTIME_CONFIG, "w") as f:
        json.dump(config, f, indent=2)
    os.chmod(MCP_RUNTIME_CONFIG, 0o600)
    ui_log(f"MCP config written: {len(config['mcpServers'])} servers → {MCP_RUNTIME_CONFIG}", "INFO")
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
###############################################################################
# OpenClaude gRPC bridge — replaces the legacy aider subprocess shell-out.
#
# Two daemons run side-by-side inside the container (see entrypoint.sh):
#   :50051  → DigitalOcean Inference  (PRIMARY)
#   :50052  → OpenRouter              (FALLBACK)
# `run_openclaude` walks the chain in order, returning the first 0-exit
# response, or the last failure if both providers reject the prompt.
#
# The signature mirrors the old `run_aider` exactly so every caller in this
# module — the 15-step healing loop, conviction engine, adversarial review
# wrappers — keeps working without modification.
###############################################################################
from openclaude_grpc import run_openclaude as _run_openclaude_bridge

# Provider chain configuration (resolved once at import time).
_OPENCLAUDE_PRIMARY_PORT = (
    int(os.getenv("OPENCLAUDE_GRPC_PORT_DO", "50051"))
    if DO_INFERENCE_API_KEY else 0
)
_OPENCLAUDE_FALLBACK_PORT = (
    int(os.getenv("OPENCLAUDE_GRPC_PORT_OR", "50052"))
    if OPENROUTER_API_KEY else 0
)
_OPENCLAUDE_PRIMARY_MODEL = DO_INFERENCE_MODEL if DO_INFERENCE_API_KEY else ""
_OPENCLAUDE_FALLBACK_MODEL = os.getenv(
    "OPENROUTER_MODEL",
    "qwen/qwen-2.5-coder-32b-instruct:free",
)


def run_aider(mcp_config_path: str, prompt: str, context_files: list[str]) -> tuple[str, int]:
    """Backwards-compatible alias kept so existing call sites and tests do
    not break. Internally delegates to the OpenClaude gRPC bridge."""
    return run_openclaude(mcp_config_path, prompt, context_files)


def run_openclaude(mcp_config_path: str, prompt: str,
                   context_files: list[str]) -> tuple[str, int]:
    """Issue one healing turn against the OpenClaude gRPC daemons.

    Returns the same ``(combined_output, exit_code)`` tuple shape that
    aider used to return so the rest of the orchestrator (validation
    loop, SAST gate, conviction engine, red-team checks) plugs in
    unchanged.
    """
    if _OPENCLAUDE_PRIMARY_PORT == 0 and _OPENCLAUDE_FALLBACK_PORT == 0:
        return (
            "No inference provider configured: set DO_INFERENCE_API_KEY "
            "or OPENROUTER_API_KEY",
            1,
        )

    valid = [f for f in context_files
             if os.path.exists(os.path.join(REPO_DIR, f))]

    return _run_openclaude_bridge(
        mcp_config_path,
        prompt,
        valid,
        repo_dir=REPO_DIR,
        primary_port=_OPENCLAUDE_PRIMARY_PORT,
        fallback_port=_OPENCLAUDE_FALLBACK_PORT,
        primary_label="DigitalOcean",
        fallback_label="OpenRouter",
        primary_model=_OPENCLAUDE_PRIMARY_MODEL,
        fallback_model=_OPENCLAUDE_FALLBACK_MODEL,
        timeout=int(os.getenv("OPENCLAUDE_TIMEOUT", "600")),
        log_fn=ui_log,
    )


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
        if not _audit_event.is_set():
            return VerificationResult(
                success=False,
                attempts=attempt_history,
                failure_reason="Audit terminated by operator",
            )
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
            # Show full output (not truncated) so argparse "error: unrecognized
            # arguments" lines at the tail are not cut off.
            ui_log(f"AIDER CRASH REASON: {aider_output.strip()}", "FAIL")
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
    if not _audit_event.is_set():
        return {"skipped": True, "error": "Audit terminated by operator"}

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
    global REPO_DIR, _current_target_repo

    target_repo = _normalize_repo(repo_override or "") or _normalize_repo(GITHUB_REPO) or (repo_override or GITHUB_REPO or "").strip()
    if not target_repo:
        ui_log("No target repo configured. Enter one in the chat inbox or set GITHUB_REPO.", "FAIL")
        _audit_event.clear()
        return

    # ── KEY FIX: give every repo its own directory so switching repos
    # never re-uses a stale clone from a previous audit. ─────────────
    safe_name = target_repo.replace("/", "_").replace(".", "_")
    REPO_DIR = f"{PERSISTENT_DIR}/repo_{safe_name}"
    _current_target_repo = target_repo

    ui_log("═" * 70)
    ui_log(f"AUDIT START — Tenant: {TENANT_ID} | Repo: {target_repo} | Dir: {REPO_DIR} | Model: {MODEL}")
    ui_log(PAID_API_KEY_WARNING, "WARN")
    notify_audit_start(target_repo)
    log_audit_event("AUDIT_START", "orchestrator", target_repo, MODEL,
                    {"tenant": TENANT_ID, "branch": branch, "repo_dir": REPO_DIR}, "STARTED")

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
            ui_log(f"Cloning {target_repo} → {REPO_DIR} ...")
            # FIX-009: Use run_subprocess_safe instead of Repo.clone_from so that
            # GIT_CONFIG_GLOBAL (set by configure_git_credentials) is propagated to
            # the git subprocess via os.environ.copy().  gitpython's Repo.clone_from
            # spawns its own subprocess which inherits os.environ, but only when the
            # env parameter is not overridden — using run_subprocess_safe is safer
            # because it explicitly copies os.environ (including GIT_CONFIG_GLOBAL).
            run_subprocess_safe(
                ["git", "clone", "-v", f"https://github.com/{target_repo}.git", REPO_DIR],
                cwd="/tmp", raise_on_error=True,
            )
        else:
            ui_log(f"Repo dir exists — syncing {target_repo} to latest origin/main ...")
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
        if not _audit_event.is_set():
            ui_log("Audit terminated during environment setup.", "WARN")
            return

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
            should_stop=lambda: not _audit_event.is_set(),
        )
        if not _audit_event.is_set():
            ui_log("Audit terminated before worker pool completed.", "WARN")
            return
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
# REPO INPUT NORMALISER
# Accepts any of:
#   owner/repo
#   https://github.com/owner/repo
#   https://github.com/owner/repo.git
#   github.com/owner/repo
# ──────────────────────────────────────────────────────────────
def _normalize_repo(raw: str) -> str:
    """Return 'owner/repo' from any common GitHub URL format, or '' if invalid."""
    s = raw.strip().rstrip("/").removesuffix(".git")
    # Strip common prefixes
    for prefix in ("https://github.com/", "http://github.com/", "github.com/"):
        if s.startswith(prefix):
            s = s[len(prefix):]
            break
    parts = [p for p in s.split("/") if p]
    if len(parts) == 2:
        return f"{parts[0]}/{parts[1]}"
    return ""


# ──────────────────────────────────────────────────────────────
# TERMINATE / STOP AUDIT
# ──────────────────────────────────────────────────────────────
def terminate_audit() -> str:
    """
    Force-stop a running audit.
    Clears _audit_event so the next submission is accepted immediately.
    The background thread will finish its current subprocess naturally —
    we cannot kill daemon threads in Python, but clearing the event means:
      1. No new test jobs are dispatched after the current one finishes
      2. The inbox immediately accepts new repo submissions
    """
    if not _audit_event.is_set():
        return "ℹ️ No audit is currently running."
    _audit_event.clear()
    killed = _kill_active_processes()
    ui_log(f"⛔ Audit terminated by operator. Stopped {killed} active subprocess group(s).", "WARN")
    return f"⛔ Audit stopped. Terminated {killed} active subprocess group(s). You can now submit a new repository."


# ──────────────────────────────────────────────────────────────
# CHAT INBOX — target repo input
# ──────────────────────────────────────────────────────────────
def submit_repo_audit(repo_input: str, chat_history: list) -> tuple[list, str]:
    """
    Called when user submits a repo via the chat inbox.
    Validates, kicks off the audit in a background thread, and
    returns an updated chat history using the messages format.
    Accepts owner/repo, full GitHub URLs, and .git suffixes.
    """
    raw = (repo_input or "").strip()

    if not raw:
        return chat_history + [
            {"role": "user", "content": "(empty)"},
            {"role": "assistant", "content": "⚠️ Please enter a repository — e.g. `OWASP/pygoat` or `https://github.com/OWASP/pygoat`."},
        ], ""

    repo = _normalize_repo(raw)
    if not repo:
        return chat_history + [
            {"role": "user", "content": raw},
            {"role": "assistant", "content": (
                f'❌ Could not parse `{raw}` as a GitHub repo.\n'
                'Accepted formats:\n'
                '- `owner/repo`\n'
                '- `https://github.com/owner/repo`\n'
                '- `https://github.com/owner/repo.git`'
            )},
        ], raw

    if _audit_event.is_set():
        return chat_history + [
            {"role": "user", "content": repo},
            {"role": "assistant", "content": (
                "⚠️ An audit is already running.\n"
                "Click **⛔ Terminate Audit** to stop it, then submit a new repo."
            )},
        ], ""

    _audit_event.set()
    ui_log(PAID_API_KEY_WARNING, "WARN")
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
                f"⚠️ **{PAID_API_KEY_WARNING}**\n\n"
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


def trigger_audit_fn(repo_input: str = ""):
    """Legacy button handler — uses typed repo first, then GITHUB_REPO env var."""
    raw = (repo_input or "").strip()
    repo = _normalize_repo(raw) if raw else ""
    target_repo = repo or _normalize_repo(GITHUB_REPO) or GITHUB_REPO
    if raw and not repo:
        return "⚠️ Could not parse that repo. Use owner/repo or a GitHub URL."
    if not target_repo:
        return "⚠️ Enter a repo above or set GITHUB_REPO."
    if _audit_event.is_set():
        return "⚠️ Audit already running."
    _audit_event.set()
    ui_log(PAID_API_KEY_WARNING, "WARN")
    threading.Thread(
        target=enterprise_audit_loop,
        kwargs={"repo_override": target_repo},
        daemon=True,
    ).start()
    return f"⚠️ {PAID_API_KEY_WARNING}\n\n🚀 Audit triggered for `{target_repo}` — full healing loop deployed."


# ──────────────────────────────────────────────────────────────
# WEBHOOK DISPATCHER
# ──────────────────────────────────────────────────────────────
def _webhook_dispatch(**kwargs):
    if not _audit_event.is_set():
        _audit_event.set()
        ui_log(PAID_API_KEY_WARNING, "WARN")
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


def get_combined_refresh():
    """
    FIX (Timer Bug): Collapse 3 concurrent SSE streams into a single tick.
    Previously gr.Timer fired 3 separate server-sent-event streams every 3 s
    per browser session — under concurrent users this could exhaust HuggingFace
    Space connection limits and freeze the UI.  A single tick that returns all
    data at once is equivalent but uses only one connection.
    """
    logs = get_live_logs()
    metrics = get_metrics_row()
    hermes_logs = hermes_get_live_logs()
    return (logs,) + metrics + (hermes_logs,)


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
    from webhook_server import clear_webhook_log
    shutil.rmtree("/data/jobs", ignore_errors=True)
    for path in [
        "/data/audit_trail.jsonl",
        "/data/rhodawk_soc2_audit_summary.md",
        "/data/swebench_report.md",
    ]:
        try:
            if os.path.exists(path):
                os.unlink(path)
        except OSError:
            pass
    shutil.rmtree("/data/lora_exports", ignore_errors=True)
    clear_webhook_log()
    with _log_lock:
        dashboard_logs.clear()
    with _inbox_lock:
        _inbox_history.clear()
    # Also unblock the audit event so a new repo can be submitted immediately
    _audit_event.clear()
    _kill_active_processes()
    ui_log("🗑 Queue, live logs, audit trail, webhook logs, reports, and audit lock cleared by operator.", "WARN")
    return "✅ Queue reset complete. Live logs, audit trail, webhook logs, reports, and running audit state were cleared."


# ──────────────────────────────────────────────────────────────
# ETHICAL SECURITY RESEARCH PIPELINE
# Human approval gate at every stage — nothing disclosed automatically
# ──────────────────────────────────────────────────────────────

def _research_clone(repo: str) -> str:
    """Clone repo to a local research directory (read-only analysis)."""
    repo_dir = f"/tmp/research_{repo.replace('/', '_')}"
    if not os.path.exists(repo_dir):
        ui_log(f"Cloning {repo} for static analysis...", "INFO")
        # FIX-009: Use run_subprocess_safe so GIT_CONFIG_GLOBAL credentials are inherited.
        run_subprocess_safe(
            ["git", "clone", "-v", f"https://github.com/{repo}.git", repo_dir],
            cwd="/tmp", raise_on_error=True,
        )
    return repo_dir


def run_semantic_analysis(repo_input: str) -> tuple[str, str]:
    """Pure static analysis — no code executed."""
    repo = (repo_input or "").strip()
    if not repo or "/" not in repo or len(repo.split("/")) != 2:
        return "❌ Use format: owner/repo", ""
    try:
        from semantic_extractor import run_semantic_extraction
        from language_runtime import RuntimeFactory
        repo_dir = _research_clone(repo)
        runtime = RuntimeFactory.for_repo(repo_dir)
        result = run_semantic_extraction(repo_dir, runtime.language)
        gaps = result.get("assumption_gaps", [])
        summary = (
            f"Static analysis complete.\n"
            f"Language: {result.get('language', 'unknown')}\n"
            f"Files analysed: {len(result.get('analyzed_files', []))}\n"
            f"Assumption gaps found: {len(gaps)}\n\n"
            f"All findings tagged requires_human_verification=true."
        )
        ui_log(f"Semantic analysis: {repo} → {len(gaps)} gap(s)", "INFO")
        return summary, json.dumps(result, indent=2)[:10000]
    except Exception as e:
        return f"Analysis failed: {e}", ""


def generate_harness_for_review(gap_json: str, repo_input: str) -> str:
    """Generate PoC harness for operator review — NOT executed here."""
    try:
        from harness_factory import generate_poc_harness
        gap = json.loads(gap_json)
        repo_dir = f"/tmp/research_{repo_input.strip().replace('/', '_')}"
        result = generate_poc_harness(gap, repo_dir)
        if "error" in result:
            return f"Generation failed: {result['error']}"
        return (
            f"Status: {result['status']}\n"
            f"Gap ID: {result['gap_id']}\n\n"
            f"--- REVIEW THIS CODE BEFORE APPROVING EXECUTION ---\n\n"
            f"{result['harness_code']}"
        )
    except Exception as e:
        return f"Error: {e}"


def execute_approved_harness(harness_code: str, repo_input: str, venv_path: str) -> str:
    """
    Sandbox execution — only after operator reads and approves harness.
    No network access, secrets stripped, 30 s timeout.
    """
    if not harness_code.strip():
        return "❌ No harness code provided."
    try:
        from harness_factory import run_harness_in_sandbox
        repo_dir = f"/tmp/research_{repo_input.strip().replace('/', '_')}"
        effective_venv = venv_path.strip() or VENV_DIR
        # FIX (Venv Path Bug): If no audit has run yet the venv may not exist;
        # create it on-demand so standalone Security Research tab execution succeeds.
        if not os.path.exists(effective_venv):
            try:
                setup_target_venv()
            except Exception as _ve:
                return f"⚠️  Could not set up venv at {effective_venv}: {_ve}\nPlease run an audit first or specify an existing venv path."
        r = run_harness_in_sandbox(harness_code, repo_dir, effective_venv)
        status = "⚠️  GAP TRIGGERED in sandbox" if r.get("triggered") else "✅ Not triggered"
        return (
            f"{status}\n\n"
            f"Exit code : {r.get('exit_code', 'N/A')}\n"
            f"Timed out : {r.get('timed_out', False)}\n\n"
            f"Stdout:\n{r.get('stdout', '')}\n\n"
            f"Stderr:\n{r.get('stderr', '')}"
        )
    except Exception as e:
        return f"Sandbox error: {e}"


def store_primitive_finding(
    repo_input: str, gap_id: str, severity: str,
    description: str, triggered_str: str, sandbox_output: str,
) -> str:
    try:
        from chain_analyzer import store_primitive
        triggered = "TRIGGERED: True" in (sandbox_output or "")
        fid = store_primitive(
            repo=repo_input.strip(), gap_id=gap_id.strip(),
            severity=severity.strip(), description=description.strip(),
            triggered=triggered, confidence="MEDIUM",
            harness_result={"stdout": sandbox_output},
        )
        return f"✅ Primitive stored with ID: {fid}"
    except Exception as e:
        return f"Error: {e}"


def run_chain_analysis(repo_input: str) -> str:
    try:
        from chain_analyzer import analyze_chains, get_pending_chains
        repo = repo_input.strip()
        chains = analyze_chains(repo) if repo else []
        pending = get_pending_chains(repo if repo else None)
        if not pending:
            return "No chains identified yet. Store primitive findings first."
        lines = []
        for c in pending:
            lines.append(
                f"[{c['id']}] {c['severity']} | Confidence: {c['confidence']}\n"
                f"  Repo: {c['repo']}\n"
                f"  {c['description'][:200]}\n"
                f"  Status: {c['status']}"
            )
        return f"Proposed chains (PENDING HUMAN REVIEW):\n\n" + "\n\n".join(lines)
    except Exception as e:
        return f"Error: {e}"


def get_vault_display() -> str:
    try:
        from disclosure_vault import get_all_disclosures
        items = get_all_disclosures()
        if not items:
            return "No disclosures yet."
        lines = []
        for d in items:
            lines.append(
                f"[{d['id']}] {d['severity']} — {d['repo']}\n"
                f"  Title : {d['title'][:70]}\n"
                f"  Status: {d['status']} | Days remaining: {d['days_remaining']}\n"
                f"  Bug Bounty: {d.get('bug_bounty_program','N/A')}"
            )
        return "\n\n".join(lines)
    except Exception as e:
        return f"Error: {e}"


def read_dossier_fn(disclosure_id: str) -> str:
    try:
        from disclosure_vault import read_dossier
        return read_dossier(disclosure_id.strip())
    except Exception as e:
        return f"Error: {e}"


def compile_dossier_fn(
    repo_input: str, gap_json: str, harness_result: str, bug_bounty: str,
) -> str:
    try:
        from disclosure_vault import compile_dossier
        gap = json.loads(gap_json) if gap_json.strip() else {}
        did = compile_dossier(
            repo=repo_input.strip(),
            semantic_graph={},
            assumption_gap=gap,
            harness_result={"stdout": harness_result, "triggered": "TRIGGERED: True" in harness_result},
            bug_bounty_program=bug_bounty.strip(),
        )
        return f"✅ Dossier compiled. Disclosure ID: {did}\nStatus: DRAFT — awaiting human approval."
    except Exception as e:
        return f"Error: {e}"


def approve_and_prepare_msg(disclosure_id: str, approver: str) -> str:
    try:
        from disclosure_vault import approve_disclosure, prepare_disclosure_message
        approve_disclosure(disclosure_id.strip(), approver.strip() or "operator")
        msg = prepare_disclosure_message(disclosure_id.strip())
        return f"✅ Approved by: {approver}\n\n--- DISCLOSURE MESSAGE (send manually) ---\n\n{msg}"
    except Exception as e:
        return f"Error: {e}"


def reject_disclosure_fn(disclosure_id: str) -> str:
    try:
        from disclosure_vault import reject_disclosure
        reject_disclosure(disclosure_id.strip())
        return f"✅ Disclosure {disclosure_id.strip()} rejected and archived."
    except Exception as e:
        return f"Error: {e}"


# ──────────────────────────────────────────────────────────────
# HERMES ORCHESTRATOR HELPERS
# ──────────────────────────────────────────────────────────────

_hermes_sessions: dict = {}
_hermes_active_session_id: str = ""
_hermes_running = threading.Event()


def _hermes_run_background(
    target_repo: str,
    repo_dir: str,
    focus_area: str,
    max_iterations: int,
) -> None:
    global _hermes_active_session_id
    _hermes_running.set()
    try:
        session = run_hermes_research(
            target_repo=target_repo,
            repo_dir=repo_dir,
            focus_area=focus_area,
            max_iterations=int(max_iterations),
        )
        _hermes_sessions[session.session_id] = session
        _hermes_active_session_id = session.session_id

        # ── Mythos refinement pass ────────────────────────────────────────
        # When RHODAWK_MYTHOS=1 the multi-agent Planner/Explorer/Executor
        # loop runs *after* Hermes and folds extra findings + a probabilistic
        # attack-graph into the same disclosure pipeline. Failures here are
        # logged but never break Hermes' own findings.
        try:
            mythos_dossier = maybe_run_mythos({
                "repo": target_repo,
                "repo_path": repo_dir,
                "focus": focus_area,
                "languages": [],
                "frameworks": [],
                "dependencies": [],
                "harness_dir": f"/tmp/mythos/{target_repo.replace('/', '_')}",
            })
            if mythos_dossier:
                ui_log(f"Mythos returned {len(mythos_dossier.get('iterations', []))} "
                       f"iteration(s)", "MYTHOS")
                session.mythos_dossier = mythos_dossier  # type: ignore[attr-defined]
        except Exception as _me:  # noqa: BLE001
            ui_log(f"Mythos refinement failed (non-fatal): {_me}", "MYTHOS")

        for finding in session.findings:
            add_to_pipeline(
                finding_id=finding.finding_id,
                title=finding.title,
                description=finding.description,
                proof_of_concept=finding.proof_of_concept,
                target_repo=target_repo,
                cwe_id=finding.cwe_id,
                severity=finding.severity,
                estimated_cvss=round(finding.ves_score, 1),
                bounty_tier="P1" if finding.ves_score >= 8 else "P2" if finding.ves_score >= 5 else "P3",
                exploit_class=finding.exploit_primitive,
            )
    finally:
        _hermes_running.clear()


def hermes_start_research(
    target_repo: str, local_path: str, focus_area: str, max_iter: str
) -> str:
    if _hermes_running.is_set():
        return "⚠️ Hermes is already running a research session. Wait for it to complete."
    if not target_repo.strip():
        return "❌ Target repository is required (e.g. owner/repo)"

    repo_dir = local_path.strip() or f"/data/repo/{target_repo.split('/')[-1]}"
    if not os.path.isdir(repo_dir):
        return f"❌ Local path not found: {repo_dir}\nClone the repo first using the main Audit tab."

    t = threading.Thread(
        target=_hermes_run_background,
        args=(target_repo.strip(), repo_dir, focus_area.strip(), max_iter or 15),
        daemon=True, name="hermes-research",
    )
    t.start()
    return (
        f"🧠 Hermes started on {target_repo}\n"
        f"Focus: {focus_area or 'Full autonomous scan'}\n"
        f"Max iterations: {max_iter}\n\n"
        "Watch the live logs below. Findings will appear in the Disclosure Pipeline tab."
    )


def hermes_get_live_logs() -> str:
    logs = get_hermes_logs()
    status = "🔄 RUNNING" if _hermes_running.is_set() else "⏸ IDLE"
    header = f"[HERMES STATUS: {status}]\n{'─' * 50}\n"
    return header + "\n".join(logs[-80:]) if logs else header + "No logs yet."


def hermes_get_session_summary() -> str:
    if not _hermes_active_session_id:
        return "No session completed yet."
    session = _hermes_sessions.get(_hermes_active_session_id)
    if not session:
        return "Session not found."
    summary = get_session_summary(session)
    lines = [
        f"Session: {summary['session_id']}",
        f"Target: {summary['target']}",
        f"Phase: {summary['phase']}",
        f"Started: {summary['started_at']}",
        f"Completed: {summary.get('completed_at', 'in progress')}",
        f"Total findings: {summary['total_findings']}",
        f"By severity: {summary['by_severity']}",
        f"Tool calls: {summary['tool_calls']}",
        f"Attack surface sinks: {summary['attack_surface_size']}",
        "",
        "TOP FINDINGS (by VES score):",
    ]
    for f in summary["top_findings"]:
        lines.append(
            f"  [{f['severity']}] {f['title'][:60]}\n"
            f"    CWE: {f['cwe']} | VES: {f['ves']} | ACTS: {f['acts']}\n"
            f"    File: {f['file']} | Status: {f['status']}"
        )
    return "\n".join(lines)


def hermes_get_pipeline_display() -> str:
    return get_pipeline_summary()


def hermes_approve_finding(record_id: str, notes: str) -> str:
    if not record_id.strip():
        return "❌ Record ID required"
    result = human_approve(record_id.strip(), notes.strip())
    return f"✅ Finding {record_id} approved.\n{result}"


def hermes_reject_finding(record_id: str, notes: str) -> str:
    if not record_id.strip():
        return "❌ Record ID required"
    result = human_reject(record_id.strip(), notes.strip())
    return f"❌ Finding {record_id} rejected.\n{result}"


def hermes_submit_hackerone(record_id: str) -> str:
    if not record_id.strip():
        return "❌ Record ID required"
    result = submit_to_hackerone(record_id.strip())
    if result.get("success"):
        return f"✅ Submitted to HackerOne: {result.get('url')}"
    return f"❌ Submission failed: {result.get('error')}"


def hermes_submit_github(record_id: str, owner_repo: str) -> str:
    if not record_id.strip() or not owner_repo.strip():
        return "❌ Record ID and owner/repo required"
    parts = owner_repo.strip().split("/")
    if len(parts) != 2:
        return "❌ Format must be owner/repo"
    result = submit_github_advisory(record_id.strip(), parts[0], parts[1])
    if result.get("success"):
        return f"✅ GitHub Advisory created: {result.get('url')}"
    return f"❌ Submission failed: {result.get('error')}"


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

with gr.Blocks(title="Rhodawk AI — Code Review Monster", theme=THEME) as demo:

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
                type="messages",
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

            # ── CONTROLS ROW ──────────────────────────────────────
            with gr.Row():
                btn_audit     = gr.Button("🚀 Trigger Audit (repo above or env fallback)", variant="secondary", scale=3)
                btn_terminate = gr.Button("⛔ Terminate Audit", variant="stop", scale=2)
                btn_reset     = gr.Button("🗑 Reset Queue", variant="secondary", scale=1)

            trigger_out = gr.Textbox(label="", interactive=False, show_label=False)
            btn_audit.click(trigger_audit_fn, inputs=repo_textbox, outputs=trigger_out)
            btn_terminate.click(terminate_audit, outputs=trigger_out)
            btn_reset.click(reset_queue,        outputs=trigger_out)

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

        # ── TAB 9b: MYTHOS UPGRADE ────────────────────────────
        # Wires the multi-agent / probabilistic / RL upgrade plane into the
        # operator dashboard. See `mythos/MYTHOS_PLAN.md` and
        # `ARCHITECTURE_ANALYSIS.md` for the full design.
        with gr.Tab("🜲 Mythos"):
            gr.Markdown(
                f"### Mythos-Level Upgrade — v{MYTHOS_VERSION}\n"
                "Multi-agent (Planner / Explorer / Executor) + probabilistic "
                "reasoning + RL self-improvement + 6 new MCP servers + FastAPI "
                "productization API. **Opt in** with `RHODAWK_MYTHOS=1`. The "
                "productization API auto-boots in a thread when `MYTHOS_API=1`."
            )
            mythos_status_box = gr.TextArea(
                label="Mythos Status & Capability Matrix", lines=22, interactive=False)
            mythos_run_box = gr.TextArea(
                label="Last Sample Campaign Output (JSON)", lines=18, interactive=False)
            with gr.Row():
                mythos_refresh_btn = gr.Button("🔄 Refresh Status", variant="secondary")
                mythos_smoke_btn   = gr.Button("🚀 Run Sample Campaign", variant="primary")

            mythos_refresh_btn.click(lambda: get_mythos_status_display(),
                                     outputs=mythos_status_box)
            mythos_smoke_btn.click(lambda: run_mythos_sample_campaign(),
                                   outputs=mythos_run_box)
            demo_mythos_load = mythos_status_box

        # ── TAB 9c: ARCHITECT control plane ───────────────────
        # Surfaces the ARCHITECT masterplan runtime: skill registry stats,
        # model-tier router, EmbodiedOS bridge wiring, autonomous night-mode
        # status. Optional — degrades gracefully when the architect package
        # is missing.
        with gr.Tab("🏛 ARCHITECT"):
            try:
                from architect import (
                    ARCHITECT_VERSION, model_router as _arch_router,
                    skill_registry as _arch_skills,
                    embodied_bridge as _arch_bridge,
                )
                _arch_loaded = True
                _arch_err = ""
            except Exception as _e:  # noqa: BLE001
                _arch_loaded = False
                _arch_err = f"{type(_e).__name__}: {_e}"
                ARCHITECT_VERSION = "unavailable"

            gr.Markdown(
                f"### ARCHITECT — Superhuman Autonomous Security Agent v{ARCHITECT_VERSION}\n"
                "Runtime control-plane for the ARCHITECT masterplan. Owns the "
                "model-tier router, skill registry, EmbodiedOS bridge, and the "
                "autonomous night-mode bug-bounty loop. Opt in with "
                "`ARCHITECT_NIGHTMODE=1`."
            )
            arch_status_box = gr.TextArea(
                label="ARCHITECT status", lines=22, interactive=False)

            def _arch_status() -> str:
                import json as _j
                if not _arch_loaded:
                    return f"ARCHITECT package failed to load: {_arch_err}"
                payload = {
                    "version": ARCHITECT_VERSION,
                    "model_router": {
                        "budget": _arch_router.budget_status(),
                        "routes": _arch_router.all_routes(),
                    },
                    "skill_registry": _arch_skills.stats(),
                    "embodied_channels": _arch_bridge.channels(),
                    "nightmode_enabled": os.getenv("ARCHITECT_NIGHTMODE", "0"),
                    "nightmode_hour": os.getenv("ARCHITECT_NIGHTMODE_HOUR", "18"),
                    "acts_gate": float(os.getenv("ARCHITECT_ACTS_GATE", "0.72")),
                }
                return _j.dumps(payload, indent=2, default=str)

            with gr.Row():
                gr.Button("🔄 Refresh ARCHITECT Status", variant="secondary").click(
                    _arch_status, outputs=arch_status_box)
                gr.Button("🌙 Run Night-Mode Cycle Now", variant="primary").click(
                    lambda: (__import__("architect.nightmode",
                                       fromlist=["run_one_cycle"]).run_one_cycle()
                             if _arch_loaded else "ARCHITECT not loaded"),
                    outputs=arch_status_box)

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

        # ── TAB 11: ETHICAL SECURITY RESEARCH ────────────────────
        with gr.Tab("🔬 Security Research"):
            gr.Markdown("""
### Ethical Security Research Pipeline

Static analysis → Human review → Responsible disclosure

**Every stage requires explicit operator approval. Nothing is disclosed automatically.**  
All PoC testing is local and sandboxed. No live systems are attacked.
            """)

            with gr.Tabs():

                # Step 1 — Semantic Analysis
                with gr.Tab("1. Semantic Analysis"):
                    gr.Markdown(
                        "**Static analysis only — no code executed.** "
                        "Hermes maps the repo's trust state machine and identifies assumption gaps."
                    )
                    sr_repo = gr.Textbox(
                        label="Open-source repository (owner/repo)",
                        placeholder="e.g. psf/requests  or  pallets/flask",
                    )
                    sr_analyze_btn = gr.Button("🔍 Run Semantic Analysis", variant="primary")
                    sr_summary = gr.Textbox(label="Summary", interactive=False, lines=6)
                    sr_graph   = gr.TextArea(label="State Machine Graph + Assumption Gaps (JSON)", lines=22, interactive=False)
                    sr_analyze_btn.click(
                        run_semantic_analysis,
                        inputs=sr_repo,
                        outputs=[sr_summary, sr_graph],
                    )

                # Step 2 — Harness Generation
                with gr.Tab("2. Generate PoC (Review Only)"):
                    gr.Markdown(
                        "Paste a single assumption gap JSON from Step 1. "
                        "Hermes generates a minimal PoC harness **for your review**. "
                        "The harness is NOT executed here."
                    )
                    sr_gap_input  = gr.TextArea(label="Assumption Gap JSON", lines=10)
                    sr_repo2      = gr.Textbox(label="Repository (owner/repo)")
                    sr_gen_btn    = gr.Button("⚙️ Generate Harness for Review", variant="secondary")
                    sr_harness    = gr.TextArea(
                        label="Generated Harness — READ CAREFULLY BEFORE PROCEEDING",
                        lines=22, interactive=True,
                    )
                    sr_gen_btn.click(
                        generate_harness_for_review,
                        inputs=[sr_gap_input, sr_repo2],
                        outputs=sr_harness,
                    )

                # Step 3 — Sandbox Execution
                with gr.Tab("3. Sandbox Execution (Operator Approved)"):
                    gr.Markdown("""
**By clicking Execute you confirm:**
- You have read every line of the harness above
- You authorise local sandbox execution only
- No network connections will be made
- Execution is time-limited to 30 seconds
                    """)
                    sr_exec_code = gr.TextArea(label="Harness Code (reviewed by operator)", lines=15)
                    with gr.Row():
                        sr_exec_repo = gr.Textbox(label="Repository (owner/repo)", scale=3)
                        sr_exec_venv = gr.Textbox(label="Venv path", value="/data/target_venv", scale=2)
                    sr_exec_btn  = gr.Button("🚀 Execute in Sandbox (I have reviewed this code)", variant="primary")
                    sr_exec_out  = gr.TextArea(label="Sandbox Result", lines=12, interactive=False)
                    sr_exec_btn.click(
                        execute_approved_harness,
                        inputs=[sr_exec_code, sr_exec_repo, sr_exec_venv],
                        outputs=sr_exec_out,
                    )

                # Step 4 — Store & Chain Analysis
                with gr.Tab("4. Chain Analysis"):
                    gr.Markdown(
                        "Store primitive findings, then ask Hermes to propose theoretical chains. "
                        "All chain proposals are tagged PENDING_HUMAN_REVIEW."
                    )
                    with gr.Row():
                        sr_prim_repo  = gr.Textbox(label="Repository", scale=2)
                        sr_prim_gapid = gr.Textbox(label="Gap ID", scale=1)
                        sr_prim_sev   = gr.Textbox(label="Severity", value="P2", scale=1)
                    sr_prim_desc    = gr.Textbox(label="Description", lines=2)
                    sr_prim_sandbox = gr.TextArea(label="Sandbox Output (from Step 3)", lines=5)
                    sr_store_btn    = gr.Button("💾 Store Primitive Finding", variant="secondary")
                    sr_store_out    = gr.Textbox(label="", interactive=False)
                    sr_store_btn.click(
                        store_primitive_finding,
                        inputs=[sr_prim_repo, sr_prim_gapid, sr_prim_sev, sr_prim_desc, sr_prim_gapid, sr_prim_sandbox],
                        outputs=sr_store_out,
                    )
                    gr.HTML("<hr/>")
                    sr_chain_repo = gr.Textbox(label="Repository for chain analysis (leave blank for all)")
                    sr_chain_btn  = gr.Button("🔗 Analyse Chains", variant="secondary")
                    sr_chain_out  = gr.TextArea(label="Proposed Chains (PENDING HUMAN REVIEW)", lines=14, interactive=False)
                    sr_chain_btn.click(run_chain_analysis, inputs=sr_chain_repo, outputs=sr_chain_out)

                # Step 5 — Disclosure Vault
                with gr.Tab("5. Disclosure Vault"):
                    gr.Markdown("""
**Human approval is mandatory before any disclosure is sent.**  
Approved disclosures generate a message you send manually via the maintainer's security policy.
                    """)
                    with gr.Row():
                        sr_vault_repo   = gr.Textbox(label="Repository (owner/repo)", scale=3)
                        sr_vault_bounty = gr.Textbox(label="Bug bounty programme URL", scale=2)
                    sr_vault_gap  = gr.TextArea(label="Assumption Gap JSON", lines=6)
                    sr_vault_poc  = gr.TextArea(label="Sandbox output from Step 3", lines=4)
                    sr_compile_btn = gr.Button("📋 Compile Disclosure Dossier", variant="secondary")
                    sr_compile_out = gr.Textbox(label="", interactive=False)
                    sr_compile_btn.click(
                        compile_dossier_fn,
                        inputs=[sr_vault_repo, sr_vault_gap, sr_vault_poc, sr_vault_bounty],
                        outputs=sr_compile_out,
                    )

                    gr.HTML("<hr/>")
                    gr.Button("🔄 Refresh Vault", variant="secondary").click(
                        get_vault_display, outputs=gr.TextArea(label="All Disclosures", lines=10, interactive=False)
                    )

                    gr.HTML("<hr/>")
                    sr_did       = gr.Textbox(label="Disclosure ID")
                    sr_read_btn  = gr.Button("📄 Read Full Dossier", variant="secondary")
                    sr_dossier   = gr.TextArea(label="Dossier (read before approving)", lines=24, interactive=False)
                    sr_read_btn.click(read_dossier_fn, inputs=sr_did, outputs=sr_dossier)

                    gr.HTML("<hr/>")
                    sr_approver  = gr.Textbox(label="Your name (approval record)")
                    with gr.Row():
                        sr_approve_btn = gr.Button("✅ Approve & Prepare Disclosure Message", variant="primary")
                        sr_reject_btn  = gr.Button("❌ Reject & Archive", variant="secondary")
                    sr_approval_out = gr.TextArea(label="Result / Disclosure Message (send manually)", lines=14, interactive=False)
                    sr_approve_btn.click(
                        approve_and_prepare_msg,
                        inputs=[sr_did, sr_approver],
                        outputs=sr_approval_out,
                    )
                    sr_reject_btn.click(reject_disclosure_fn, inputs=sr_did, outputs=sr_approval_out)

        # ── HERMES AI SECURITY RESEARCHER TAB ──────────────────────
        with gr.Tab("🧠 Hermes Zero-Day"):
            gr.Markdown("""
# Hermes — Autonomous Zero-Day Research Engine

Hermes is your AI security researcher. Point it at any open source project and it will:
- **Map the attack surface** (entry points, dangerous sinks, security-critical files)
- **Run taint analysis** to trace untrusted input to dangerous sinks
- **Perform symbolic execution** to find unchecked code paths
- **Generate and run fuzz campaigns** to find crashes
- **Reason about exploitability** (CVSS, PoC generation)
- **Score findings** with VES (Vulnerability Entropy Score) + ACTS (Adversarial Consensus)

**ALL findings require human approval before any disclosure is sent.**
""")
            with gr.Tabs():
                with gr.Tab("🚀 Launch Research"):
                    gr.Markdown("### Start an autonomous security research session")
                    with gr.Row():
                        hermes_repo     = gr.Textbox(label="Target Repository (owner/repo)", placeholder="torvalds/linux", scale=2)
                        hermes_path     = gr.Textbox(label="Local Clone Path", placeholder="/data/repo/linux", scale=2)
                    hermes_focus    = gr.Textbox(
                        label="Focus Area (optional)",
                        placeholder="memory management subsystem, authentication middleware, crypto primitives...",
                    )
                    with gr.Row():
                        hermes_max_iter = gr.Slider(minimum=5, maximum=30, value=15, step=1, label="Max Research Iterations")
                        hermes_launch   = gr.Button("🧠 Launch Hermes", variant="primary", scale=1)
                    hermes_launch_out = gr.Textbox(label="Status", interactive=False, lines=5)
                    hermes_launch.click(
                        hermes_start_research,
                        inputs=[hermes_repo, hermes_path, hermes_focus, hermes_max_iter],
                        outputs=hermes_launch_out,
                    )

                with gr.Tab("📡 Live Research Logs"):
                    hermes_live_logs = gr.TextArea(
                        label="Hermes Research Log (auto-refreshes)",
                        lines=30, interactive=False,
                    )
                    gr.Button("🔄 Refresh Logs", variant="secondary").click(
                        hermes_get_live_logs, outputs=hermes_live_logs
                    )

                with gr.Tab("📊 Session Summary"):
                    hermes_summary_out = gr.TextArea(label="Last Session Summary", lines=25, interactive=False)
                    gr.Button("📊 Get Summary", variant="secondary").click(
                        hermes_get_session_summary, outputs=hermes_summary_out
                    )

                with gr.Tab("🔒 Disclosure Pipeline"):
                    gr.Markdown("""
### Human-Approval Gate

All findings sit here as **PENDING_HUMAN_APPROVAL** until you explicitly approve them.
Hermes never auto-submits. You review, then approve or reject each finding individually.
After approval, you can submit to HackerOne or create a GitHub Security Advisory.

**90-day disclosure countdown starts on approval.**
""")
                    hermes_pipeline_out = gr.TextArea(label="Pipeline Status", lines=12, interactive=False)
                    gr.Button("🔄 Refresh Pipeline", variant="secondary").click(
                        hermes_get_pipeline_display, outputs=hermes_pipeline_out
                    )

                    gr.HTML("<hr/>")
                    gr.Markdown("#### Review & Approve/Reject a Finding")
                    with gr.Row():
                        hermes_record_id = gr.Textbox(label="Record ID", scale=2)
                        hermes_notes     = gr.Textbox(label="Analyst Notes", scale=3)
                    with gr.Row():
                        hermes_approve_btn = gr.Button("✅ Approve Finding", variant="primary")
                        hermes_reject_btn  = gr.Button("❌ Reject Finding", variant="secondary")
                    hermes_approval_out = gr.Textbox(label="Result", interactive=False)
                    hermes_approve_btn.click(
                        hermes_approve_finding,
                        inputs=[hermes_record_id, hermes_notes],
                        outputs=hermes_approval_out,
                    )
                    hermes_reject_btn.click(
                        hermes_reject_finding,
                        inputs=[hermes_record_id, hermes_notes],
                        outputs=hermes_approval_out,
                    )

                    gr.HTML("<hr/>")
                    gr.Markdown("#### Submit Approved Finding (requires credentials in env vars)")
                    with gr.Row():
                        hermes_submit_record = gr.Textbox(label="Approved Record ID", scale=2)
                        hermes_gh_repo       = gr.Textbox(label="GitHub owner/repo (for GHSA)", placeholder="torvalds/linux", scale=2)
                    with gr.Row():
                        hermes_h1_btn  = gr.Button("🎯 Submit to HackerOne", variant="primary")
                        hermes_gh_btn  = gr.Button("🐙 Create GitHub Advisory", variant="secondary")
                    hermes_submit_out = gr.Textbox(label="Submission Result", interactive=False)
                    hermes_h1_btn.click(
                        hermes_submit_hackerone,
                        inputs=[hermes_submit_record],
                        outputs=hermes_submit_out,
                    )
                    hermes_gh_btn.click(
                        hermes_submit_github,
                        inputs=[hermes_submit_record, hermes_gh_repo],
                        outputs=hermes_submit_out,
                    )

                with gr.Tab("📚 CWE Reference"):
                    gr.Markdown("### CWE Taxonomy — Coverage Map")
                    cwe_table_data = [
                        [c["cwe_id"], c["name"], c["category"], c["severity"],
                         str(c["cvss_base"]), c.get("owasp", "")]
                        for c in get_all_cwes()
                    ]
                    gr.Dataframe(
                        value=cwe_table_data,
                        headers=["CWE ID", "Name", "Category", "Severity", "CVSS", "OWASP"],
                        interactive=False,
                    )

    # ── AUTO-REFRESH ────────────────────────────────────────────
    # FIX (Timer Bug): Single tick replaces 3 concurrent SSE streams.
    # get_combined_refresh() returns all 8 outputs at once, using one connection
    # instead of three — prevents connection-limit freezes under multiple users.
    timer = gr.Timer(3)
    timer.tick(
        get_combined_refresh,
        outputs=[live_logs, stat_status, stat_total, stat_done, stat_prs, stat_failed, stat_sast, hermes_live_logs],
    )

    demo.load(get_live_logs,            outputs=live_logs)
    demo.load(get_metrics_row,          outputs=[stat_status, stat_total, stat_done, stat_prs, stat_failed, stat_sast])
    demo.load(hermes_get_live_logs,     outputs=hermes_live_logs)
    demo.load(hermes_get_pipeline_display, outputs=hermes_pipeline_out)
    demo.load(get_job_table,            outputs=job_table)
    demo.load(get_audit_display,        outputs=audit_log)
    demo.load(get_chain_integrity_display, outputs=chain_status)
    demo.load(get_training_stats_display,  outputs=stats_display)
    demo.load(get_webhook_log_display,  outputs=webhook_log)
    demo.load(get_red_team_display,     outputs=red_team_box)
    demo.load(get_swebench_display,     outputs=swebench_report)


# ─── Mythos status + sample campaign helpers (used by the Mythos tab) ────────
def get_mythos_status_display() -> str:
    """Render the Mythos availability matrix + env config as plain text."""
    import json as _json
    if not _MYTHOS_OK:
        return f"❌ Mythos package failed to import: {_MYTHOS_IMPORT_ERR}"
    try:
        matrix = mythos_availability_matrix()
    except Exception as e:  # noqa: BLE001
        return f"❌ Mythos status error: {e}"
    enabled = "ON" if mythos_enabled() else "OFF (set RHODAWK_MYTHOS=1)"
    api_on  = "ON" if os.getenv("MYTHOS_API", "0").lower() in ("1","true","yes","on") else "OFF"
    lines = [
        f"Mythos version       : {MYTHOS_VERSION}",
        f"Multi-agent loop     : {enabled}",
        f"Productization API   : {api_on}  (uvicorn mythos.api.fastapi_server:app)",
        f"Tier-1 primary model : {os.getenv('MYTHOS_TIER1_PRIMARY', 'deepseek/deepseek-v2-chat')}",
        f"Tier-2 primary model : {os.getenv('MYTHOS_TIER2_PRIMARY', 'qwen/qwen-2.5-coder-72b-instruct')}",
        "",
        "Capability matrix (✓ = available, ✗ = optional native dep missing):",
    ]
    for k, v in sorted(matrix.items()):
        ok = v.get("available") if isinstance(v, dict) else False
        err = (" — " + v.get("error")) if isinstance(v, dict) and v.get("error") else ""
        lines.append(f"  {'✓' if ok else '✗'} {k:28s}{err}")
    lines.append("")
    lines.append("Reference: mythos/MYTHOS_PLAN.md   |   ARCHITECTURE_ANALYSIS.md")
    return "\n".join(lines)


def run_mythos_sample_campaign() -> str:
    """Kick off a 1-iteration sample campaign against /data/repo (or cwd)."""
    import json as _json
    if not _MYTHOS_OK:
        return f"❌ Mythos unavailable: {_MYTHOS_IMPORT_ERR}"
    try:
        target = {
            "repo": "sample/local",
            "repo_path": os.getenv("MYTHOS_SAMPLE_REPO", os.getcwd()),
            "languages": ["python"],
            "frameworks": [],
            "dependencies": [],
            "harness_dir": "/tmp/mythos-sample",
        }
        os.makedirs(target["harness_dir"], exist_ok=True)
        orch = build_default_orchestrator(max_iterations=1)
        dossier = orch.run_campaign(target)
        return _json.dumps(dossier, indent=2, default=str)[:20000]
    except Exception as e:  # noqa: BLE001
        return f"❌ Sample campaign error: {type(e).__name__}: {e}"


def _start_mythos_api_server_thread() -> None:
    """Boot the FastAPI productization plane in-process when MYTHOS_API=1."""
    if os.getenv("MYTHOS_API", "0").lower() not in ("1", "true", "yes", "on"):
        return
    if not _MYTHOS_OK:
        ui_log(f"Mythos API requested but package unavailable: {_MYTHOS_IMPORT_ERR}", "MYTHOS")
        return
    try:
        import uvicorn  # type: ignore
        from mythos.api.fastapi_server import app as _mythos_app
        if _mythos_app is None:
            ui_log("Mythos API requested but FastAPI not installed", "MYTHOS")
            return
        port = int(os.getenv("MYTHOS_API_PORT", "7862"))

        def _serve():
            try:
                uvicorn.run(_mythos_app, host="0.0.0.0", port=port, log_level="warning")
            except Exception as exc:  # noqa: BLE001
                ui_log(f"Mythos API thread crashed: {exc}", "MYTHOS")

        threading.Thread(target=_serve, daemon=True, name="mythos-api").start()
        ui_log(f"Mythos productization API listening on :{port}", "MYTHOS")
    except Exception as exc:  # noqa: BLE001
        ui_log(f"Mythos API boot skipped: {exc}", "MYTHOS")


if __name__ == "__main__":
    ui_log(f"Rhodawk AI v3.0 starting — Tenant: {TENANT_ID} | Model: {MODEL}")
    ui_log(f"Mythos: {'enabled' if _MYTHOS_OK else 'unavailable: ' + _MYTHOS_IMPORT_ERR} "
           f"| Multi-agent loop: {'ON' if mythos_enabled() else 'OFF'}", "MYTHOS")

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

    # Boot Mythos productization API (no-op unless MYTHOS_API=1).
    _start_mythos_api_server_thread()
    port = int(os.environ.get("PORT", 7860))
    # ── ARCHITECT autonomous night-mode (opt-in via ARCHITECT_NIGHTMODE=1) ──
    try:
        from architect import nightmode as _arch_nm
        _arch_nm.start_in_background()
    except Exception as _e:  # noqa: BLE001
        print(f"[ARCHITECT] night-mode scheduler not started: {_e}")

    demo.launch(server_name="0.0.0.0", server_port=port, share=False, show_error=True)

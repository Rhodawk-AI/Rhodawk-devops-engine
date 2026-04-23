# Rhodawk-devops-engine — Full Repository Analysis Report

> This report is a line-grounded, programmatically generated walk-through of every file in the [`Rhodawk-AI/Rhodawk-devops-engine`](https://github.com/Rhodawk-AI/Rhodawk-devops-engine) repository at the time of cloning. For every Python file, the abstract syntax tree was parsed and every class, method, function signature, top-level constant, import, and module docstring was extracted directly from the source — no contents were inferred or summarized from outside the file. Markdown files have their full heading hierarchy and opening text extracted. TypeScript/JavaScript files have their imports, exports, and PascalCase identifiers enumerated. Configuration files (JSON/YAML) have their top-level keys listed. Binary assets (images, PDFs, the `.pptx` deck, lockfiles) are noted with their byte size. Vendored third-party code under `vendor/` and the built `pitch-deck/` bundle are catalogued separately at the end with size/line metadata.

## Repository Snapshot

- **Total files** (excluding `.git/`): **2604**
- **Core (non-vendored) files:** **270**
- **Vendored / built-artifact files:** **2334**
- **Total lines across all files:** **647,749**
- **Total bytes:** **26,746,531** (~26.7 MB)

**File-type breakdown:**

- `.ts`: 1600
- `.tsx`: 573
- `.md`: 187
- `.py`: 163
- `.js`: 33
- `(none)`: 11
- `.json`: 8
- `.txt`: 7
- `.yaml`: 4
- `.sh`: 3
- `.svg`: 2
- `.png`: 2
- `.mjs`: 2
- `.ipynb`: 2
- `.css`: 1
- `.html`: 1
- `.pdf`: 1
- `.pptx`: 1
- `.example`: 1
- `.lock`: 1
- `.proto`: 1

## Top-Level Layout

- `.gitattributes` — file, 1793 bytes, 39 lines
- `.gitignore_extra` — file, 32 bytes, 1 lines
- `CAMOFOX_INTEGRATION.md` — file, 5329 bytes, 94 lines
- `Dockerfile` — file, 6388 bytes, 135 lines
- `EXTERNAL_INTEGRATIONS.md` — file, 4841 bytes, 85 lines
- `Makefile` — file, 776 bytes, 25 lines
- `README.md` — file, 27481 bytes, 657 lines
- `adversarial_reviewer.py` — file, 10870 bytes, 293 lines
- `app.py` — file, 134669 bytes, 2760 lines
- `architect/` — directory, 125 files
- `audit_logger.py` — file, 6521 bytes, 196 lines
- `bounty_gateway.py` — file, 14695 bytes, 398 lines
- `bugbounty_checklist.py` — file, 11671 bytes, 352 lines
- `camofox_client.py` — file, 14178 bytes, 392 lines
- `chain_analyzer.py` — file, 9592 bytes, 285 lines
- `clientside_resources.py` — file, 6282 bytes, 199 lines
- `commit_watcher.py` — file, 12431 bytes, 339 lines
- `conviction_engine.py` — file, 5242 bytes, 142 lines
- `cve_intel.py` — file, 13830 bytes, 333 lines
- `disclosure_vault.py` — file, 11411 bytes, 365 lines
- `embedding_memory.py` — file, 15275 bytes, 380 lines
- `entrypoint.sh` — file, 4193 bytes, 93 lines
- `exploit_primitives.py` — file, 11372 bytes, 310 lines
- `formal_verifier.py` — file, 6214 bytes, 191 lines
- `fuzzing_engine.py` — file, 14380 bytes, 414 lines
- `github_app.py` — file, 5979 bytes, 188 lines
- `harness_factory.py` — file, 7418 bytes, 220 lines
- `hermes_orchestrator.py` — file, 38655 bytes, 885 lines
- `job_queue.py` — file, 8150 bytes, 226 lines
- `knowledge_rag.py` — file, 7393 bytes, 200 lines
- `language_runtime.py` — file, 69987 bytes, 1598 lines
- `lora_scheduler.py` — file, 9089 bytes, 258 lines
- `mcp_config.ARCHIVE.json` — file, 16558 bytes, 509 lines
- `memory_engine.py` — file, 5026 bytes, 134 lines
- `mythos/` — directory, 66 files
- `night_hunt_lock.py` — file, 2998 bytes, 95 lines
- `night_hunt_orchestrator.py` — file, 22875 bytes, 567 lines
- `notifier.py` — file, 3779 bytes, 109 lines
- `openclaude_grpc/` — directory, 2 files
- `openclaw_gateway.py` — file, 14554 bytes, 375 lines
- `openclaw_schedule.yaml` — file, 775 bytes, 30 lines
- `oss_guardian.py` — file, 8420 bytes, 208 lines
- `oss_target_scorer.py` — file, 3538 bytes, 111 lines
- `paper2code_engine.py` — file, 14916 bytes, 399 lines
- `pitch-deck/` — directory, 7 files
- `pitch_deck/` — directory, 2 files
- `public_leaderboard.py` — file, 6430 bytes, 190 lines
- `red_team_fuzzer.py` — file, 62456 bytes, 1560 lines
- `repo_harvester.py` — file, 10819 bytes, 333 lines
- `requirements.txt` — file, 1998 bytes, 56 lines
- `sast_gate.py` — file, 8273 bytes, 204 lines
- `scripts/` — directory, 1 files
- `semantic_extractor.py` — file, 6993 bytes, 212 lines
- `skills/` — directory, 7 files
- `supply_chain.py` — file, 10205 bytes, 265 lines
- `swebench_harness.py` — file, 10645 bytes, 293 lines
- `symbolic_engine.py` — file, 12660 bytes, 350 lines
- `taint_analyzer.py` — file, 11544 bytes, 304 lines
- `tests/` — directory, 11 files
- `training_store.py` — file, 15660 bytes, 389 lines
- `vendor/` — directory, 2327 files
- `verification_loop.py` — file, 5041 bytes, 145 lines
- `vuln_classifier.py` — file, 14370 bytes, 360 lines
- `webhook_server.py` — file, 10402 bytes, 266 lines
- `worker_pool.py` — file, 6882 bytes, 210 lines

---

# Part I — Core Source Tree (file-by-file)

Every file under the project root that is **not** inside `vendor/` or `pitch-deck/` (the built deck bundle) is documented in this section.


## Root-level files


### `.gitattributes`

- Lines: 39  Bytes: 1793

```
*.7z filter=lfs diff=lfs merge=lfs -text
*.arrow filter=lfs diff=lfs merge=lfs -text
*.bin filter=lfs diff=lfs merge=lfs -text
*.bz2 filter=lfs diff=lfs merge=lfs -text
*.ckpt filter=lfs diff=lfs merge=lfs -text
*.ftz filter=lfs diff=lfs merge=lfs -text
*.gz filter=lfs diff=lfs merge=lfs -text
*.h5 filter=lfs diff=lfs merge=lfs -text
*.joblib filter=lfs diff=lfs merge=lfs -text
*.lfs.* filter=lfs diff=lfs merge=lfs -text
*.mlmodel filter=lfs diff=lfs merge=lfs -text
*.model filter=lfs diff=lfs merge=lfs -text
*.msgpack filter=lfs diff=lfs merge=lfs -text
*.npy filter=lfs diff=lfs merge=lfs -text
*.npz filter=lfs diff=lfs merge=lfs -text
*.onnx filter=lfs diff=lfs merge=lfs -text
*.ot filter=lfs diff=lfs merge=lfs -text
*.parquet filter=lfs diff=lfs merge=lfs -text
*.pb filter=lfs diff=lfs merge=lfs -text
*.pickle filter=lfs diff=lfs merge=lfs -text
*.pkl filter=lfs diff=lfs merge=lfs -text
*.pt filter=lfs diff=lfs merge=lfs -text
*.pth filter=lfs diff=lfs merge=lfs -text
*.rar filter=lfs diff=lfs merge=lfs -text
*.safetensors filter=lfs diff=lfs merge=lfs -text
saved_model/**/* filter=lfs diff=lfs merge=lfs -text
*.tar.* filter=lfs diff=lfs merge=lfs -text
*.tar filter=lfs diff=lfs merge=lfs -text
*.tflite filter=lfs diff=lfs merge=lfs -text
*.tgz filter=lfs diff=lfs merge=lfs -text
*.wasm filter=lfs diff=lfs merge=lfs -text
*.xz filter=lfs diff=lfs merge=lfs -text
*.zip filter=lfs diff=lfs merge=lfs -text
*.zst filter=lfs diff=lfs merge=lfs -text
*tfevents* filter=lfs diff=lfs merge=lfs -text
Rhodawk_AI_Pitch_Deck_2026.pptx filter=lfs diff=lfs merge=lfs -text
pitch-deck/hero-cover.png filter=lfs diff=lfs merge=lfs -text
pitch-deck/hero-solution.png filter=lfs diff=lfs merge=lfs -text
pitch_deck/Rhodawk_AI_Pitch_Deck_2026.pptx filter=lfs diff=lfs merge=lfs -text

```

### `.gitignore_extra`

- Lines: 1  Bytes: 32

```
vendor/openclaude/node_modules/

```

### `CAMOFOX_INTEGRATION.md`

- Lines: 94  Bytes: 5329

**Headings (8):**

- L1 `# Camofox-Browser Integration`
  - L9 `## Why`
  - L26 `## Architecture`
  - L46 `## Quick Start (Python)`
- L51 `# One-shot: fetch a snapshot of a URL with element refs.`
- L59 `# Long-running session:`
  - L74 `## Environment Variables`
  - L87 `## Files Added`

**Opening text:**

> Rhodawk now ships with an embedded [camofox-browser](https://github.com/jo-inc/camofox-browser) anti-detection browser server so the orchestrator and analysis engines can browse the live web without being fingerprinted, blocked by Cloudflare, or flagged by

### `Dockerfile`

- Lines: 135  Bytes: 6388

```dockerfile
ARG BUN_VERSION=latest

# ─── Stage 1: build the vendored OpenClaude bundle ──────────────────────
FROM oven/bun:${BUN_VERSION} AS openclaude-builder
WORKDIR /openclaude
# FIX: Ignored bun.lock and removed --frozen-lockfile to prevent version mismatch crashes
COPY vendor/openclaude/package.json ./
RUN bun install --no-progress
COPY vendor/openclaude/ ./
RUN bun run build && \
    test -s dist/cli.mjs && \
    echo "[builder] OpenClaude bundle: $(wc -c < dist/cli.mjs) bytes"

# ─── Stage 2: base python+node+bun runtime ──────────────────────────────
FROM python:3.12-slim AS base

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

RUN apt-get update && apt-get install -y --no-install-recommends \
        git curl ca-certificates build-essential unzip xz-utils \
        nodejs npm \
        # ─── camofox-browser runtime deps ────────────────────────────
        # Camoufox is a Firefox fork; it needs the standard X/GTK
        # display libraries even when running headless, plus xvfb so
        # we can attach a virtual display when --headless=virtual.
        xvfb libgtk-3-0 libdbus-glib-1-2 libxt6 libasound2 \
        libx11-xcb1 libxcomposite1 libxcursor1 libxdamage1 libxfixes3 \
        libxi6 libxrandr2 libxss1 libxtst6 libnss3 libpango-1.0-0 \
        libatk1.0-0 libatk-bridge2.0-0 libcups2 libdrm2 libgbm1 \
    && rm -rf /var/lib/apt/lists/*

# uv (fast Python installer used by sandboxed test runs)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Bun (needed at runtime to launch the daemon: `bun run dev:grpc`)
# FIX: Updated to pull from latest to match Stage 1
COPY --from=oven/bun:latest /usr/local/bin/bun /usr/local/bin/bun
COPY --from=oven/bun:latest /usr/local/bin/bunx /usr/local/bin/bunx

WORKDIR /build
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
                mcp-server-fetch mcp-server-git mcp-server-sqlite \
                grpcio==1.66.* grpcio-tools==1.66.* protobuf==5.*

# MCP servers used by the runtime — installed globally so `npx -y …` is
# instantaneous instead of resolving on every audit.
# NOTE: `@modelcontextprotocol/server-git` and `@modelcontextprotocol/server-sqlite`
# were removed from the npm registry (404) — they are now provided via the
# Python packages `mcp-server-git` and `mcp-server-sqlite` installed above.
RUN npm install -g --quiet \
        @modelcontextprotocol/server-github \
        @modelcontextprotocol/server-filesystem \
        @modelcontextprotocol/server-memory \
        @modelcontextprotocol/server-sequential-thinking \
        @modelcontextprotocol/server-brave-search

...
```

### `EXTERNAL_INTEGRATIONS.md`

- Lines: 85  Bytes: 4841

**Headings (7):**

- L1 `# External Knowledge & Tool Integrations`
  - L14 `## Where they plug into the existing engines`
    - L16 `### `bugbounty_checklist.py``
    - L31 `### `clientside_resources.py``
    - L41 `### `paper2code_engine.py``
  - L56 `## Quick programmatic checks`
  - L75 `## Vendoring policy`

**Opening text:**

> Rhodawk now embeds three external knowledge / capability sources directly into the runtime so the orchestrator and analysis engines can use them offline, without round-tripping to the public web on every audit.

### `Makefile`

- Lines: 25  Bytes: 776

```makefile
# Rhodawk AI — Local Developer Makefile
# Resolves W-001: provides a one-shot target to generate gRPC stubs locally
# so the Python brain can run without requiring a full Docker build.

.PHONY: help stubs install dev clean

help:
	@echo "Rhodawk AI — local developer targets"
	@echo "  make stubs    Generate openclaude_pb2*.py gRPC stubs (W-001)"
	@echo "  make install  pip install -r requirements.txt + grpcio-tools"
	@echo "  make dev      Run app.py locally (requires stubs + env vars)"
	@echo "  make clean    Remove generated gRPC stubs"

stubs:
	bash scripts/generate_stubs.sh

install:
	pip install -r requirements.txt
	pip install grpcio-tools

dev: stubs
	python -u app.py

clean:
	rm -f openclaude_grpc/openclaude_pb2.py openclaude_grpc/openclaude_pb2_grpc.py

```

### `README.md`

- Lines: 657  Bytes: 27481

**Headings (24):**

  - L46 `## 🚀 Mythos-Level Upgrade`
  - L69 `## What Rhodawk Actually Is`
  - L81 `## The Full Autonomous Loop`
  - L125 `## Architecture at a Glance`
  - L182 `## Five Custom Algorithms — Built From Scratch`
  - L213 `## The Security Research Pipeline (Hermes)`
  - L249 `## Supported Languages`
  - L273 `## The MCP Server Suite — 25 Integrated Tools`
  - L316 `## The Data Flywheel`
  - L344 `## Required API Keys`
  - L405 `## Running Locally`
    - L409 `### Step 1 — Clone`
    - L416 `### Step 2 — Install Python dependencies`
    - L424 `### Step 3 — Install MCP servers`
    - L436 `### Step 4 — Configure environment`
    - L445 `### Step 5 — Run`
  - L458 `## Docker`
- L463 `# Build`
- L466 `# Run`
  - L481 `## HuggingFace Spaces Deployment`
  - L498 `## Event-Driven Mode — GitHub Webhook`
  - L529 `## Repository Structure`
  - L608 `## Security by Design`
  - L626 `## Default LLM Models`

**Opening text:**

> --- title: Rhodawk AI DevSecOps Engine emoji: 🦅 colorFrom: indigo

### `adversarial_reviewer.py`

- Lines: 293  Bytes: 10870

**Module docstring:**

> Rhodawk AI — Adversarial Reviewer (Consensus Edition)
> =====================================================
> Upgraded from sequential model-chain to concurrent 3-model consensus.
> Requires 2/3 majority to APPROVE or REJECT a diff.
> This eliminates single-model veto false-positives and false-negatives.
> 
> Architecture:
>   Before: Qwen → Gemma → Mistral (sequential, first success wins)
>   After:  Qwen ∥ Gemma ∥ Mistral (concurrent) → majority vote threshold=0.67

**Imports (7):**

- `import concurrent.futures`
- `import hashlib`
- `import json`
- `import os`
- `import time`
- `import requests`
- `from requests.exceptions import HTTPError`

**Top-level constants (8):**

- `OPENROUTER_API_KEY` = `os.getenv('OPENROUTER_API_KEY')`
- `ADVERSARY_MODEL_PRIMARY` = `os.getenv('RHODAWK_ADVERSARY_MODEL', 'deepseek/deepseek-r1:free')`
- `ADVERSARY_MODEL_SECONDARY` = `'meta-llama/llama-3.3-70b-instruct:free'`
- `ADVERSARY_MODEL_TERTIARY` = `'google/gemma-3-27b-it:free'`
- `_MODEL_CHAIN` = `[ADVERSARY_MODEL_PRIMARY, ADVERSARY_MODEL_SECONDARY, ADVERSARY_MODEL_TERTIARY]`
- `CONSENSUS_THRESHOLD` = `float(os.getenv('RHODAWK_CONSENSUS_THRESHOLD', '0.67'))`
- `_RATE_LIMIT_WAIT` = `20`
- `ADVERSARY_SYSTEM_PROMPT` = `'You are a hostile senior security engineer and code quality enforcer.\nYour ONLY job is to find problems in AI-gener...`

**Top-level functions (5):**

- `def _call_openrouter(model: str, system: str, user: str, timeout: int=60) -> dict` (L70)
- `def _call_single_model(model: str, user_prompt: str) -> tuple[dict | None, str]` (L99)
  - _Call one model; return (result_dict, model_name) or (None, model_name) on failure._
- `def _call_concurrent_consensus(user_prompt: str) -> tuple[dict, str]` (L113)
  - _Run all models concurrently and compute majority verdict._
- `def _call_with_model_chain(user_prompt: str) -> tuple[dict, str]` (L189)
  - _Legacy sequential fallback — used only if concurrent call is explicitly disabled._
- `def run_adversarial_review(diff_text: str, test_path: str, original_failure: str, repo: str) -> dict` (L211)
  - _Run the concurrent adversarial consensus review on an AI-generated diff._

### `app.py`

- Lines: 2760  Bytes: 134669

**Module docstring:**

> Rhodawk AI — Autonomous DevSecOps Control Plane v4.0
> =====================================================
> Full loop:
>   1. Clone repo → discover tests → run pytest
>   2. FAIL → retrieve similar fixes from memory (data flywheel)
>   3. Dispatch Aider with failure + memory context via MCP tools
>   4. Re-run tests on the patched code (verification — CLOSES THE LOOP)
>   5. If still failing → retry with new failure context (up to MAX_RETRIES)
>   6. SAST gate: bandit + 16-pattern secret scanner
>   7. Supply chain gate: pip-audit + typosquatting detection
>   8. Adversarial LLM review: 3-model concurrent consensus (Qwen∥Gemma∥Mistral)
>   9. Z3 formal verification gate (bounded integer/bounds checking)
>   10. If adversary REJECTs → loop back with critique as context
>   11. Conviction engine: auto-merge if all trust criteria met
>   12. All clear → open PR, record to training store, update memory
>   13. LoRA scheduler: export training data when threshold reached
>   14. Repo harvester: autonomous target selection (antagonist mode)
>   15. Webhook server runs in parallel for event-driven triggers

**Imports (36):**

- `import hashlib`
- `import json`
- `import os`
- `import signal`
- `import shutil`
- `import subprocess`
- `import tempfile`
- `import threading`
- `import time`
- `from typing import Optional`
- `import gradio as gr`
- `import requests`
- `from git import Repo`
- `from tenacity import retry, stop_after_attempt, wait_exponential`
- `from adversarial_reviewer import run_adversarial_review`
- `from hermes_orchestrator import run_hermes_research, get_hermes_logs, get_session_summary, compute_ves, build_tvg`
- `from bounty_gateway import get_pipeline, get_pipeline_summary, human_approve, human_reject, submit_to_hackerone, submit_github_advisory, add_to_pipeline`
- `from vuln_classifier import classify_vulnerability, get_all_cwes`
- `from audit_logger import export_compliance_report, log_audit_event, read_audit_trail, verify_chain_integrity`
- `from conviction_engine import evaluate_conviction, auto_merge_pr`
- `from formal_verifier import run_formal_verification`
- `from github_app import get_github_token`
- `from job_queue import JobStatus, get_job_status_enum, get_metrics, list_all_jobs, upsert_job`
- `from lora_scheduler import maybe_trigger_training, get_scheduler_status`
- `from memory_engine import get_memory_stats, record_fix_outcome, retrieve_similar_fixes`
- `from embedding_memory import retrieve_similar_fixes_v2`
- `from notifier import notify, notify_audit_complete, notify_audit_start, notify_chain_integrity, notify_patch_failed, notify_pr_created, notify_sast_blocked, notify_test_failed`
- `from sast_gate import run_sast_gate`
- `from red_team_fuzzer import get_red_team_logs, get_red_team_stats, run_red_team_cegis`
- `from supply_chain import run_supply_chain_gate`
- `from training_store import export_training_data, get_statistics, initialize_store, record_attempt, update_test_result`
- `from verification_loop import MAX_RETRIES, ADVERSARIAL_REJECTION_MULTIPLIER, VerificationAttempt, VerificationResult, build_initial_prompt, build_retry_prompt`
- `from webhook_server import set_job_dispatcher, start_webhook_server`
- `from worker_pool import MAX_WORKERS, run_parallel_audit`
- `from language_runtime import RuntimeFactory, LanguageRuntime, EnvConfig, kill_runtime_processes`
- `from openclaude_grpc import run_openclaude as _run_openclaude_bridge`

**Top-level constants (21):**

- `GITHUB_TOKEN` = `os.getenv('GITHUB_TOKEN')`
- `GITHUB_REPO` = `os.getenv('GITHUB_REPO', '')`
- `OPENROUTER_API_KEY` = `os.getenv('OPENROUTER_API_KEY')`
- `DO_INFERENCE_API_KEY` = `os.getenv('DO_INFERENCE_API_KEY') or os.getenv('DIGITALOCEAN_INFERENCE_KEY')`
- `DO_INFERENCE_BASE_URL` = `os.getenv('DO_INFERENCE_BASE_URL', 'https://inference.do-ai.run/v1').rstrip('/')`
- `DO_INFERENCE_MODEL` = `os.getenv('DO_INFERENCE_MODEL', 'llama3.3-70b-instruct')`
- `TENANT_ID` = `os.getenv('RHODAWK_TENANT_ID', 'default')`
- `_DEFAULT_AIDER_MODEL` = `f'openai/{DO_INFERENCE_MODEL}' if DO_INFERENCE_API_KEY else 'openrouter/qwen/qwen-2.5-coder-32b-instruct:free'`
- `MODEL` = `os.getenv('RHODAWK_MODEL', _DEFAULT_AIDER_MODEL)`
- `FALLBACK_MODEL` = `os.getenv('RHODAWK_FALLBACK_MODEL', 'openrouter/qwen/qwen-2.5-coder-32b-instruct:free')`
- `RED_TEAM_ENABLED` = `os.getenv('RHODAWK_RED_TEAM_ENABLED', 'true').lower() != 'false'`
- `PAID_API_KEY_WARNING` = `'Please use a PAID API KEY without rate limits. Free-tier API keys usually hit 8 to 9 requests per minute, but this s...`
- `PERSISTENT_DIR` = `'/data'`
- `REPO_DIR` = `f'{PERSISTENT_DIR}/repo'`
- `VENV_DIR` = `f'{PERSISTENT_DIR}/target_venv'`
- `MCP_RUNTIME_CONFIG` = `'/tmp/mcp_runtime.json'`
- `_OPENCLAUDE_PRIMARY_PORT` = `int(os.getenv('OPENCLAUDE_GRPC_PORT_DO', '50051')) if DO_INFERENCE_API_KEY else 0`
- `_OPENCLAUDE_FALLBACK_PORT` = `int(os.getenv('OPENCLAUDE_GRPC_PORT_OR', '50052')) if OPENROUTER_API_KEY else 0`
- `_OPENCLAUDE_PRIMARY_MODEL` = `DO_INFERENCE_MODEL if DO_INFERENCE_API_KEY else ''`
- `_OPENCLAUDE_FALLBACK_MODEL` = `os.getenv('OPENROUTER_MODEL', 'qwen/qwen-2.5-coder-32b-instruct:free')`
- `THEME` = `gr.themes.Base(primary_hue='violet', secondary_hue='slate', neutral_hue='slate', font=[gr.themes.GoogleFont('Inter'),...`

**Top-level functions (62):**

- `def ui_log(message: str, level: str='INFO')` (L191)
- `def run_subprocess_safe(cmd: list, cwd: str=REPO_DIR, timeout: int=300, env_overrides: dict=None, raise_on_error: bool=True) -> tuple[str, int]` (L207)
- `def _kill_active_processes() -> int` (L251)
- `def configure_git_credentials()` (L274)
  - _Set up git credential storage._
- `def write_mcp_config() -> str` (L306)
  - _Write the full 25-server cybersecurity MCP config to /tmp/mcp_runtime.json._
- `def safe_git_pull()` (L494)
- `def cleanup_stale_branch(branch_name: str)` (L502)
- `def create_fix_branch(branch_name: str) -> bool` (L507)
- `def ensure_fix_committed(test_path: str) -> None` (L515)
- `def push_fix_branch(branch_name: str) -> bool` (L524)
- `def create_github_pr(repo: str, branch: str, test_path: str, token: str) -> str` (L529)
- `def get_current_diff() -> str` (L560)
- `def get_changed_files() -> list[str]` (L572)
- `def setup_target_venv() -> str` (L580)
- `def run_aider(mcp_config_path: str, prompt: str, context_files: list[str]) -> tuple[str, int]` (L648)
  - _Backwards-compatible alias kept so existing call sites and tests do_
- `def run_openclaude(mcp_config_path: str, prompt: str, context_files: list[str]) -> tuple[str, int]` (L654)
  - _Issue one healing turn against the OpenClaude gRPC daemons._
- `def process_failing_test(test_path: str, initial_failure: str, env_config: EnvConfig, mcp_config_path: str, job_id: str, branch_name: str, target_repo: str='') -> VerificationResult` (L692)
  - _Core autonomous healing loop:_
- `def process_audit_test(test_path: str, env_config: EnvConfig, mcp_config_path: str, tenant_id: str, target_repo: str) -> dict` (L930)
- `def enterprise_audit_loop(repo_override: str=None, branch: str='main', specific_test: str=None)` (L1061)
- `def _normalize_repo(raw: str) -> str` (L1233)
  - _Return 'owner/repo' from any common GitHub URL format, or '' if invalid._
- `def terminate_audit() -> str` (L1250)
  - _Force-stop a running audit._
- `def submit_repo_audit(repo_input: str, chat_history: list) -> tuple[list, str]` (L1270)
  - _Called when user submits a repo via the chat inbox._
- `def get_inbox_history() -> list` (L1330)
  - _Pull any background-posted messages (e.g. audit-complete) into the chat._
- `def trigger_audit_fn(repo_input: str='')` (L1338)
  - _Legacy button handler — uses typed repo first, then GITHUB_REPO env var._
- `def _webhook_dispatch(**kwargs)` (L1362)
- `def get_live_logs() -> str` (L1383)
- `def get_metrics_row()` (L1388)
- `def get_combined_refresh()` (L1394)
  - _FIX (Timer Bug): Collapse 3 concurrent SSE streams into a single tick._
- `def get_job_table() -> list[list]` (L1408)
- `def get_audit_display() -> str` (L1419)
- `def get_chain_integrity_display() -> str` (L1432)
- `def get_training_stats_display() -> str` (L1437)
- `def get_training_export() -> str` (L1455)
- `def get_webhook_log_display() -> str` (L1466)
- `def get_red_team_display() -> str` (L1483)
- `def trigger_swebench_eval(max_instances: int=25) -> str` (L1493)
- `def get_swebench_display() -> str` (L1523)
- `def export_compliance_display() -> str` (L1531)
- `def reset_queue()` (L1538)
- `def _research_clone(repo: str) -> str` (L1569)
  - _Clone repo to a local research directory (read-only analysis)._
- `def run_semantic_analysis(repo_input: str) -> tuple[str, str]` (L1582)
  - _Pure static analysis — no code executed._
- `def generate_harness_for_review(gap_json: str, repo_input: str) -> str` (L1607)
  - _Generate PoC harness for operator review — NOT executed here._
- `def execute_approved_harness(harness_code: str, repo_input: str, venv_path: str) -> str` (L1626)
  - _Sandbox execution — only after operator reads and approves harness._
- `def store_primitive_finding(repo_input: str, gap_id: str, severity: str, description: str, triggered_str: str, sandbox_output: str) -> str` (L1657)
- `def run_chain_analysis(repo_input: str) -> str` (L1675)
- `def get_vault_display() -> str` (L1696)
- `def read_dossier_fn(disclosure_id: str) -> str` (L1715)
- `def compile_dossier_fn(repo_input: str, gap_json: str, harness_result: str, bug_bounty: str) -> str` (L1723)
- `def approve_and_prepare_msg(disclosure_id: str, approver: str) -> str` (L1741)
- `def reject_disclosure_fn(disclosure_id: str) -> str` (L1751)
- `def _hermes_run_background(target_repo: str, repo_dir: str, focus_area: str, max_iterations: int) -> None` (L1769)
- `def hermes_start_research(target_repo: str, local_path: str, focus_area: str, max_iter: str) -> str` (L1826)
- `def hermes_get_live_logs() -> str` (L1852)
- `def hermes_get_session_summary() -> str` (L1859)
- `def hermes_get_pipeline_display() -> str` (L1888)
- `def hermes_approve_finding(record_id: str, notes: str) -> str` (L1892)
- `def hermes_reject_finding(record_id: str, notes: str) -> str` (L1899)
- `def hermes_submit_hackerone(record_id: str) -> str` (L1906)
- `def hermes_submit_github(record_id: str, owner_repo: str) -> str` (L1915)
- `def get_mythos_status_display() -> str` (L2626)
  - _Render the Mythos availability matrix + env config as plain text._
- `def run_mythos_sample_campaign() -> str` (L2655)
  - _Kick off a 1-iteration sample campaign against /data/repo (or cwd)._
- `def _start_mythos_api_server_thread() -> None` (L2677)
  - _Boot the FastAPI productization plane in-process when MYTHOS_API=1._

### `audit_logger.py`

- Lines: 196  Bytes: 6521

**Module docstring:**

> Rhodawk AI — Immutable Audit Trail Engine
> ==========================================
> Every AI action is appended to an append-only JSONL file with SHA-256 chaining.
> Each entry references the hash of the previous entry, creating a tamper-evident
> chain of custody for every line of AI-generated code. Required for SOC 2 / ISO 27001.

**Imports (6):**

- `import hashlib`
- `import json`
- `import os`
- `import threading`
- `import time`
- `from typing import Optional`

**Top-level constants (1):**

- `AUDIT_LOG_PATH` = `'/data/audit_trail.jsonl'`

**Top-level functions (6):**

- `def _compute_hash(entry: dict) -> str` (L22)
- `def _get_last_hash() -> str` (L27)
- `def log_audit_event(event_type: str, job_id: str, repo: str, model: str, details: dict, outcome: str='PENDING') -> str` (L48)
  - _Append an audit event to the immutable JSONL chain._
- `def read_audit_trail(limit: int=50) -> list[dict]` (L89)
  - _Return the last N audit events for dashboard display._
- `def verify_chain_integrity() -> tuple[bool, str]` (L108)
  - _Walk the ENTIRE audit chain and verify each entry's hash._
- `def export_compliance_report(output_path: str='/data/rhodawk_soc2_audit_summary.md') -> str` (L153)

### `bounty_gateway.py`

- Lines: 398  Bytes: 14695

**Module docstring:**

> Rhodawk AI — Bug Bounty Gateway (Human-Approval Required)
> ==========================================================
> Manages the responsible disclosure pipeline to:
>   - HackerOne (REST API v1)
>   - Bugcrowd (JSON API)
>   - GitHub Security Advisories (GHSA)
>   - Direct maintainer email (coordinated disclosure)
> 
> CRITICAL DESIGN PRINCIPLE:
>   NOTHING is submitted without explicit human approval.
>   All findings sit in PENDING_HUMAN_APPROVAL state until a human clicks
>   the "Approve & Submit" button in the Gradio UI. The approval gate is
>   enforced at the API call level, not just the UI level.
> 
> Disclosure timeline follows Google Project Zero standard (90 days).

**Imports (10):**

- `from __future__ import annotations`
- `import hashlib`
- `import json`
- `import os`
- `import sqlite3`
- `import time`
- `from dataclasses import dataclass, field, asdict`
- `from enum import Enum`
- `from typing import Optional`
- `import requests`

**Top-level constants (8):**

- `HACKERONE_API_KEY` = `os.getenv('HACKERONE_API_KEY', '')`
- `HACKERONE_USERNAME` = `os.getenv('HACKERONE_USERNAME', '')`
- `HACKERONE_PROGRAM` = `os.getenv('HACKERONE_PROGRAM', '')`
- `BUGCROWD_API_KEY` = `os.getenv('BUGCROWD_API_KEY', '')`
- `BUGCROWD_PROGRAM_URL` = `os.getenv('BUGCROWD_PROGRAM_URL', '')`
- `GITHUB_TOKEN` = `os.getenv('GITHUB_TOKEN', '')`
- `DISCLOSURE_DB` = `os.getenv('RHODAWK_DISCLOSURE_DB', '/data/disclosure_pipeline.db')`
- `DISCLOSURE_WINDOW_DAYS` = `int(os.getenv('RHODAWK_DISCLOSURE_DAYS', '90'))`

**Classes (2):**

- `class DisclosureStatus(str, Enum)` — line 43
- `class DisclosureRecord` — line 57

**Top-level functions (9):**

- `def _init_db()` (L81)
- `def add_to_pipeline(finding_id: str, title: str, description: str, proof_of_concept: str, target_repo: str, cwe_id: str, severity: str, estimated_cvss: float, bounty_tier: str, exploit_class: str, cve_draft: dict=None) -> DisclosureRecord` (L116)
  - _Add a new finding to the disclosure pipeline. Status = PENDING_HUMAN_APPROVAL._
- `def _save_record(record: DisclosureRecord)` (L155)
- `def get_pipeline(status_filter: str=None) -> list[dict]` (L174)
  - _Get all records in the pipeline, optionally filtered by status._
- `def human_approve(record_id: str, notes: str='') -> dict` (L197)
  - _Human approval gate — must be called before any submission attempt._
- `def human_reject(record_id: str, notes: str='') -> dict` (L214)
  - _Human rejection — finding is closed without disclosure._
- `def submit_to_hackerone(record_id: str) -> dict` (L227)
  - _Submit an APPROVED finding to HackerOne._
- `def submit_github_advisory(record_id: str, repo_owner: str, repo_name: str) -> dict` (L304)
  - _Submit an APPROVED finding as a GitHub Security Advisory (GHSA)._
- `def get_pipeline_summary() -> str` (L366)
  - _Human-readable pipeline summary for the Gradio dashboard._

### `bugbounty_checklist.py`

- Lines: 352  Bytes: 11671

**Module docstring:**

> bugbounty_checklist.py
> ──────────────────────
> In-process loader for the vendored Galaxy-Bugbounty-Checklist
> (https://github.com/0xmaximus/Galaxy-Bugbounty-Checklist).
> 
> The repo is a hand-curated bug bounty methodology library — one folder per
> vulnerability class (XSS, SSRF, SQLi, OAuth, IDOR, CSRF bypass, …),
> each containing a long-form checklist plus, where applicable, a payload
> file (e.g. ``sql_injection/SQL.txt``, ``xss_payloads/README.md``).
> 
> This module loads it from ``vendor/galaxy_bugbounty/`` at import time so
> that the rest of the system can:
> 
>   * Look up a checklist by category or by CWE / vulnerability tag
>     (``vuln_classifier.py``, ``red_team_fuzzer.py``).
>   * Pull payload corpora for a category (used by the fuzzer + harness
>     factory to seed boundary-value inputs).
>   * Surface "what should I check next" hints to the orchestrator while
>     triaging a candidate finding.
>   * Expose the same data through a tiny REST adapter so other engines
>     (and the OpenClaude tool layer) can consume it without re-parsing
>     markdown on every call.
> 
> Design rules
> ────────────
> 1. Pure Python stdlib — no heavy dependencies, no I/O at import time
>    beyond a single directory scan.
> 2. Zero hard dependency: if the vendor directory is missing the module
>    degrades to empty-result helpers and logs a warning instead of
>    raising, so the orchestrator keeps working.
> 3. Read-only — never mutate the vendored content.

**Imports (8):**

- `from __future__ import annotations`
- `import logging`
- `import os`
- `import re`
- `from dataclasses import dataclass, field`
- `from functools import lru_cache`
- `from pathlib import Path`
- `from typing import Dict, Iterable, List, Optional`

**Top-level constants (2):**

- `_HERE` = `Path(__file__).resolve().parent`
- `VENDOR_DIR` = `Path(os.environ.get('RHODAWK_GALAXY_DIR', str(_HERE / 'vendor' / 'galaxy_bugbounty')))`

**Classes (1):**

- `class Checklist` — line 129
  - _A single vulnerability-class checklist as vendored from Galaxy._
    - `def summary(self, max_chars: int=600) -> str` (L138)
    - `def to_dict(self) -> Dict[str, object]` (L142)

**Top-level functions (11):**

- `def _read(path: Path) -> str` (L154)
- `def _extract_title(markdown: str, fallback: str) -> str` (L162)
- `def _split_payloads(text: str) -> List[str]` (L170)
  - _Split a payload file into individual non-empty payload lines._
- `def load_all() -> Dict[str, Checklist]` (L186)
  - _Return ``{category_slug: Checklist}`` for every vendored category._
- `def list_categories() -> List[str]` (L222)
- `def get_checklist(category: str) -> Optional[Checklist]` (L226)
  - _Look up by exact category slug (e.g. ``"ssrf"``)._
- `def _normalize_tag(tag: str) -> str` (L231)
- `def match_for_tag(tag: str) -> Optional[Checklist]` (L235)
  - _Map an arbitrary tag (CWE id, vuln label, classifier output, …)_
- `def payloads_for(tag_or_category: str, limit: int=200) -> List[str]` (L263)
  - _Return up to ``limit`` payload strings for a category/tag._
- `def hints_for_finding(*, cwe: str='', *, label: str='', *, description: str='', *, max_bullets: int=8) -> List[str]` (L291)
  - _Return short bullet-point reminders extracted from the matching_
- `def stats() -> Dict[str, object]` (L331)

### `camofox_client.py`

- Lines: 392  Bytes: 14178

**Module docstring:**

> camofox_client.py
> ─────────────────
> Python client for the embedded camofox-browser anti-detection browser server
> (https://github.com/jo-inc/camofox-browser).
> 
> camofox-browser wraps the Camoufox engine — a Firefox fork with fingerprint
> spoofing patched at the C++ implementation level — behind a small REST API
> designed for AI agents:
> 
>   * accessibility snapshots with stable element refs (e1, e2, e3 …)
>   * session isolation per userId / sessionKey
>   * Netscape-format cookie import for authenticated browsing
>   * residential-proxy + GeoIP routing
>   * search macros (@google_search, @youtube_search, …)
>   * download capture, DOM image extraction, screenshot snapshots
> 
> Inside the Rhodawk container the camofox node server is launched by
> `entrypoint.sh` on 127.0.0.1:9377.  This module is the thin Python
> adapter the orchestrator and other engines (repo_harvester, cve_intel,
> red_team_fuzzer, knowledge_rag, …) use to drive it.
> 
> Design goals
> ────────────
> 1. Zero hard dependency — if the camofox server is not running the
>    client raises ``CamofoxUnavailable`` and the caller can degrade
>    gracefully (e.g. fall back to plain ``requests.get``).
> 2. No ``console.print``-style side effects — pure return values + the
>    structured ``audit_logger`` for production observability.
> 3. Safe defaults — every browsing call carries a ``userId`` and an
>    optional ``sessionKey`` so different research jobs cannot leak
>    cookies into each other.

**Imports (8):**

- `from __future__ import annotations`
- `import json`
- `import logging`
- `import os`
- `import time`
- `from dataclasses import dataclass, field`
- `from typing import Any, Dict, List, Optional`
- `import requests`

**Top-level constants (4):**

- `CAMOFOX_BASE_URL` = `os.environ.get('CAMOFOX_BASE_URL', 'http://127.0.0.1:9377').rstrip('/')`
- `CAMOFOX_API_KEY` = `os.environ.get('CAMOFOX_API_KEY', '')`
- `CAMOFOX_DEFAULT_TIMEOUT` = `float(os.environ.get('CAMOFOX_TIMEOUT', '60'))`
- `CAMOFOX_HEALTH_TIMEOUT` = `float(os.environ.get('CAMOFOX_HEALTH_TIMEOUT', '3'))`

**Classes (5):**

- `class CamofoxError(RuntimeError)` — line 56
  - _Base class for any camofox-browser interaction failure._
- `class CamofoxUnavailable(CamofoxError)` — line 60
  - _Raised when the camofox server is not reachable._
- `class CamofoxAPIError(CamofoxError)` — line 68
  - _Raised when the server is reachable but returns a non-2xx response._
    - `def __init__(self, status: int, body: str, *, endpoint: str='')` (L71)
- `class CamofoxTab` — line 80
  - _Lightweight handle to a single tab inside the camofox server._
- `class CamofoxClient` — line 96
  - _Thin REST wrapper around the local camofox-browser server._
    - `def __init__(self, base_url: str=CAMOFOX_BASE_URL, api_key: str=CAMOFOX_API_KEY, timeout: float=CAMOFOX_DEFAULT_TIMEOUT) -> None` (L99)
    - `def _headers(self) -> Dict[str, str]` (L111)
    - `def _request(self, method: str, path: str, *, json_body: Optional[Dict[str, Any]]=None, *, params: Optional[Dict[str, Any]]=None, *, timeout: Optional[float]=None) -> Dict[str, Any]` (L117)
    - `def is_available(self) -> bool` (L157)
      - _Return True if the camofox server is up.  Never raises._
    - `def wait_ready(self, max_wait: float=30.0, poll_interval: float=0.5) -> bool` (L165)
      - _Block until the server responds to /health or ``max_wait`` elapses._
    - `def create_tab(self, user_id: str, url: str, *, session_key: str='default', *, wait_until: str='domcontentloaded') -> CamofoxTab` (L175)
    - `def list_tabs(self, user_id: str) -> List[Dict[str, Any]]` (L201)
    - `def close_tab(self, tab: CamofoxTab) -> None` (L205)
    - `def snapshot(self, tab: CamofoxTab, *, include_screenshot: bool=False, *, offset: int=0, *, limit: Optional[int]=None) -> Dict[str, Any]` (L213)
      - _Accessibility snapshot — ~90% smaller than raw HTML,_
    - `def click(self, tab: CamofoxTab, ref: str) -> Dict[str, Any]` (L232)
    - `def type_text(self, tab: CamofoxTab, ref: str, text: str, *, press_enter: bool=False) -> Dict[str, Any]` (L239)
    - `def navigate(self, tab: CamofoxTab, url: str, *, wait_until: str='domcontentloaded') -> Dict[str, Any]` (L258)
    - `def scroll(self, tab: CamofoxTab, *, direction: str='down', *, amount: int=1) -> Dict[str, Any]` (L275)
    - `def screenshot(self, tab: CamofoxTab, *, full_page: bool=False) -> bytes` (L292)
      - _Return raw PNG bytes for ``tab``._
    - `def import_cookies(self, user_id: str, cookies: List[Dict[str, Any]]) -> Dict[str, Any]` (L314)
      - _Inject pre-exported cookies into a session._
    - `def youtube_transcript(self, video_url: str) -> Dict[str, Any]` (L335)

**Top-level functions (2):**

- `def get_client() -> CamofoxClient` (L347)
  - _Lazy module-wide singleton — most callers just want this._
- `def fetch_snapshot(url: str, *, user_id: str='rhodawk', *, session_key: str='default', *, include_screenshot: bool=False, *, close_when_done: bool=True) -> Dict[str, Any]` (L355)
  - _One-shot helper: open ``url`` in a fresh tab, return its snapshot,_

### `chain_analyzer.py`

- Lines: 285  Bytes: 9592

**Module docstring:**

> Rhodawk AI — Vulnerability Chain Analyzer
> ==========================================
> Documents how primitive findings (individual assumption gaps + PoC results)
> might combine into higher-severity chains.
> 
> ETHICAL CONSTRAINTS:
>   - Chains are THEORETICAL proposals documented for human review
>   - No chain is automatically executed
>   - All chain proposals are stored with status PENDING_HUMAN_REVIEW
>   - Human operator must approve or reject every chain before any further action
> 
> Orchestrated by Nous Hermes 3 via OpenRouter.

**Imports (9):**

- `from __future__ import annotations`
- `import hashlib`
- `import json`
- `import os`
- `import re`
- `import sqlite3`
- `import time`
- `from typing import Optional`
- `import requests`

**Top-level constants (3):**

- `OPENROUTER_API_KEY` = `os.getenv('OPENROUTER_API_KEY', '')`
- `HERMES_MODEL` = `os.getenv('RHODAWK_RESEARCH_MODEL', 'nousresearch/hermes-3-llama-3.1-405b:free')`
- `CHAIN_DB` = `os.getenv('RHODAWK_CHAIN_DB', '/data/chain_memory.sqlite')`

**Top-level functions (7):**

- `def _init_db() -> None` (L36)
- `def store_primitive(repo: str, gap_id: str, severity: str, description: str, triggered: bool, confidence: str='UNKNOWN', harness_result: Optional[dict]=None) -> str` (L72)
  - _Persist a primitive finding from the harness execution._
- `def analyze_chains(repo: str) -> list[dict]` (L102)
  - _Ask Hermes to propose vulnerability chains from stored primitives._
- `def get_pending_chains(repo: Optional[str]=None) -> list[dict]` (L212)
- `def get_all_primitives(repo: Optional[str]=None) -> list[dict]` (L238)
- `def approve_chain(chain_id: str, reviewer: str) -> bool` (L263)
- `def reject_chain(chain_id: str, reviewer: str) -> bool` (L276)

### `clientside_resources.py`

- Lines: 199  Bytes: 6282

**Module docstring:**

> clientside_resources.py
> ───────────────────────
> Programmatic access to the vendored
> ``zomasec/client-side-bugs-resources`` knowledge pack
> (``vendor/clientside_bugs/RESOURCES.md``).
> 
> The upstream repo is a single, lovingly-curated README of links + reading
> material for client-side bug hunting (XSS, postMessage, CSP, CORS,
> prototype pollution, DOM internals, …).  Inside Rhodawk we want to:
> 
>   * Surface the resources as structured records the orchestrator can
>     quote when triaging client-side findings.
>   * Feed seed URLs into ``knowledge_rag.py`` so the embedding store gets
>     real-world write-ups rather than only Rhodawk's own runs.
>   * Provide a category → links lookup for ``red_team_fuzzer.py`` when it
>     needs a quick reminder of what tradecraft exists for a given
>     sub-class (e.g. ``"prototype_pollution"`` → 3 reference links).
> 
> Pure stdlib, zero side effects at import time apart from an `lru_cache`d
> markdown parse.

**Imports (8):**

- `from __future__ import annotations`
- `import logging`
- `import os`
- `import re`
- `from dataclasses import dataclass`
- `from functools import lru_cache`
- `from pathlib import Path`
- `from typing import Dict, List, Optional`

**Top-level constants (3):**

- `_HERE` = `Path(__file__).resolve().parent`
- `RESOURCES_PATH` = `Path(os.environ.get('RHODAWK_CLIENTSIDE_RESOURCES', str(_HERE / 'vendor' / 'clientside_bugs' / 'RESOURCES.md')))`
- `_LINK_RE` = `re.compile('\\[([^\\]]+)\\]\\((https?://[^\\s)]+)\\)')`

**Classes (1):**

- `class Resource` — line 47
    - `def to_dict(self) -> Dict[str, str]` (L52)

**Top-level functions (10):**

- `def _read() -> str` (L60)
- `def _slug(s: str) -> str` (L68)
- `def load() -> Dict[str, List[Resource]]` (L73)
  - _Return ``{section_slug: [Resource, ...]}`` parsed from the README._
- `def list_sections() -> List[str]` (L100)
- `def get_section(section: str) -> List[Resource]` (L104)
- `def all_resources() -> List[Resource]` (L108)
- `def search(query: str, limit: int=25) -> List[Resource]` (L115)
  - _Naive substring search across title + section._
- `def for_tag(tag: str, limit: int=10) -> List[Resource]` (L147)
- `def stats() -> Dict[str, object]` (L162)
- `def seed_urls(limit: int=50) -> List[str]` (L173)
  - _Flat list of unique URLs — handy as input to knowledge_rag.py's_

### `commit_watcher.py`

- Lines: 339  Bytes: 12431

**Module docstring:**

> Rhodawk AI — Commit Watcher + CAD Algorithm
> ============================================
> Monitors GitHub repository commit streams for:
>   1. Silent security patches (fixes without CVE mention)
>   2. Regression introductions (commits that break previously safe invariants)
>   3. Dependency bumps that change security-relevant code
> 
> Custom Algorithm: CAD (Commit Anomaly Detection)
>   Uses statistical analysis of commit metadata + diff content to score
>   how "suspicious" a commit is from a security perspective.
>   High CAD score = likely silent security fix = potential unpatched vuln in older versions.
> 
> CAD Score Components:
>   - keyword_score: security-related words in commit message (without CVE/advisory mention)
>   - diff_complexity: unusual churn patterns (small message + large diff = suspicious)
>   - sink_delta: did the commit add/remove dangerous sinks?
>   - author_entropy: is this from an unusual author for this file?
>   - timing: late-night commits, weekend commits (higher anomaly weight)

**Imports (9):**

- `from __future__ import annotations`
- `import hashlib`
- `import math`
- `import os`
- `import re`
- `import subprocess`
- `import time`
- `from dataclasses import dataclass, field`
- `from typing import Optional`

**Top-level constants (5):**

- `_SECURITY_KEYWORDS` = `{'overflow', 'injection', 'traversal', 'escape', 'sanitize', 'sanitise', 'validate', 'validation', 'bypass', 'privile...`
- `_CVE_PATTERN` = `re.compile('\\bCVE-\\d{4}-\\d+\\b', re.IGNORECASE)`
- `_ADVISORY_PATTERN` = `re.compile('\\bGHSA-[A-Z0-9-]+\\b|\\bSA-\\d+\\b|\\bVU#\\d+\\b', re.IGNORECASE)`
- `_DANGEROUS_SINK_PATTERNS` = `re.compile('\\beval\\b|\\bexec\\b|\\bos\\.system\\b|\\bsubprocess\\b|\\bpickle\\b|\\byaml\\.load\\b|\\bchild_process\...`
- `CAD_THRESHOLD` = `float(os.getenv('RHODAWK_CAD_THRESHOLD', '5.0'))`

**Classes (1):**

- `class CommitAnalysis` — line 35

**Top-level functions (5):**

- `def _git_log(repo_dir: str, n: int=50) -> list[dict]` (L78)
  - _Get recent commits with stats._
- `def _get_commit_diff(repo_dir: str, sha: str) -> str` (L125)
  - _Get the diff for a specific commit._
- `def _compute_cad_score(commit: dict, diff: str) -> tuple[float, list[str], list[str]]` (L137)
  - _CAD (Commit Anomaly Detection) algorithm._
- `def analyze_recent_commits(repo_dir: str, lookback: int=50) -> dict` (L212)
  - _Main entry point. Analyze recent commits using CAD algorithm._
- `def watch_repo_stream(owner: str, repo: str, github_token: str, callback, poll_interval_s: int=300) -> None` (L277)
  - _Continuously poll a GitHub repo for new commits and run CAD on each batch._

### `conviction_engine.py`

- Lines: 142  Bytes: 5242

**Module docstring:**

> Rhodawk AI — Conviction Engine (Auto-Merge Gate)
> ================================================
> Evaluates whether a successfully verified fix meets the conviction threshold
> for autonomous merge without human review.
> 
> Conviction criteria (all must be met):
>   1. adversarial_confidence >= CONVICTION_CONFIDENCE_MIN (default 0.92)
>   2. adversarial_verdict == "APPROVE" (no conditional)
>   3. consensus_fraction >= CONVICTION_CONSENSUS_MIN (default 0.85 — 3/3 models agree)
>   4. Memory engine found a semantically identical past fix that was human-merged
>      (similarity >= CONVICTION_MEMORY_MIN, default 0.85)
>   5. test_attempts == 1 (fixed on first try — indicates clean, well-understood fix)
>   6. SAST findings == 0 (zero informational findings on the diff)
>   7. No new packages introduced in the diff
> 
> When all criteria pass, auto_merge() is called which uses the GitHub API to
> merge the PR directly (no human required).
> 
> Enable with: RHODAWK_AUTO_MERGE=true

**Imports (3):**

- `import os`
- `import time`
- `import requests`

**Top-level constants (4):**

- `CONVICTION_CONFIDENCE_MIN` = `float(os.getenv('RHODAWK_CONVICTION_CONFIDENCE', '0.92'))`
- `CONVICTION_CONSENSUS_MIN` = `float(os.getenv('RHODAWK_CONVICTION_CONSENSUS', '0.85'))`
- `CONVICTION_MEMORY_MIN` = `float(os.getenv('RHODAWK_CONVICTION_MEMORY_SIM', '0.85'))`
- `AUTO_MERGE_ENABLED` = `os.getenv('RHODAWK_AUTO_MERGE', 'false').lower() == 'true'`

**Top-level functions (2):**

- `def evaluate_conviction(adversarial_review: dict, similar_fixes: list[dict], test_attempts: int, sast_findings_count: int, new_packages: list[str]) -> tuple[bool, str]` (L33)
  - _Returns (should_auto_merge, reason_string)._
- `def auto_merge_pr(repo: str, pr_url: str, token: str, merge_method: str='squash') -> tuple[bool, str]` (L93)
  - _Merge a PR via GitHub API._

### `cve_intel.py`

- Lines: 333  Bytes: 13830

**Module docstring:**

> Rhodawk AI — CVE Intelligence Layer
> =====================================
> Queries NVD/CVE databases and implements SSEC (Semantic Similarity Exploit Chain)
> to find code patterns similar to historically exploited vulnerabilities.
> 
> Custom Algorithms:
>   SSEC — Semantic Similarity Exploit Chain
>     Embeds known exploit patterns and compares them to repo code using cosine
>     similarity. Finds "looks like CWE-X" candidates even without a test failure.

**Imports (11):**

- `from __future__ import annotations`
- `import json`
- `import math`
- `import os`
- `import re`
- `import time`
- `import glob`
- `import hashlib`
- `import requests`
- `from dataclasses import dataclass, field`
- `from typing import Optional`

**Top-level constants (4):**

- `NVD_API_KEY` = `os.getenv('NVD_API_KEY', '')`
- `NVD_BASE` = `'https://services.nvd.nist.gov/rest/json/cves/2.0'`
- `CACHE_DIR` = `'/data/cve_cache'`
- `_EXPLOIT_PATTERNS` = `[('buffer_overflow_c', 'CWE-119', 'strcpy|strcat|sprintf|gets\\s*\\(|scanf\\s*\\(', 'CRITICAL'), ('integer_overflow',...`

**Classes (1):**

- `class CVERecord` — line 34

**Top-level functions (6):**

- `def _scan_file_for_patterns(file_path: str, source: str) -> list[dict]` (L84)
  - _Scan a single file against all SSEC exploit patterns._
- `def _compute_ssec_confidence(line: str, cwe: str) -> float` (L110)
  - _SSEC confidence scoring — custom algorithm._
- `def run_ssec_scan(repo_dir: str, focus_files: list[str]=None) -> dict` (L136)
  - _SSEC (Semantic Similarity Exploit Chain) scan._
- `def query_cve_intel(description: str, cwe_hint: str=None) -> dict` (L197)
  - _Query NVD for CVEs similar to the given description._
- `def _query_nvd_api(description: str, cwe_hint: str=None) -> dict` (L226)
  - _Query NVD 2.0 API._
- `def _local_cve_lookup(description: str, cwe_hint: str=None) -> dict` (L276)
  - _Local CVE pattern database — offline fallback._

### `disclosure_vault.py`

- Lines: 365  Bytes: 11411

**Module docstring:**

> Rhodawk AI — Responsible Disclosure Vault
> ==========================================
> Manages the complete responsible disclosure lifecycle with a mandatory
> human approval gate at every stage.
> 
> DISCLOSURE POLICY (non-negotiable):
>   1. ALL findings start as DRAFT — nothing is shared externally
>   2. Human operator must read the full dossier and click Approve
>   3. After approval, the system generates a disclosure message —
>      the operator sends it via the maintainer's own security channel
>   4. Standard 90-day responsible disclosure timeline is tracked
>   5. Bug bounty submissions are prepared for human submission —
>      never automated
>   6. No GitHub API writes in AVR mode

**Imports (8):**

- `from __future__ import annotations`
- `import hashlib`
- `import json`
- `import os`
- `import sqlite3`
- `import time`
- `from pathlib import Path`
- `from typing import Optional`

**Top-level constants (3):**

- `VAULT_DB` = `os.getenv('RHODAWK_VAULT_DB', '/data/disclosure_vault.sqlite')`
- `VAULT_DIR` = `os.getenv('RHODAWK_VAULT_DIR', '/data/vault')`
- `DISCLOSURE_DAYS` = `int(os.getenv('RHODAWK_DISCLOSURE_DAYS', '90'))`

**Top-level functions (8):**

- `def _init_db() -> None` (L33)
- `def compile_dossier(repo: str, semantic_graph: dict, assumption_gap: dict, harness_result: dict, chain_analysis: Optional[list]=None, bug_bounty_program: str='', maintainer_contact: str='') -> str` (L59)
  - _Compile a structured responsible disclosure dossier._
- `def get_pending_disclosures() -> list[dict]` (L223)
- `def get_all_disclosures() -> list[dict]` (L244)
- `def read_dossier(disclosure_id: str) -> str` (L264)
- `def approve_disclosure(disclosure_id: str, approved_by: str) -> bool` (L279)
  - _Human operator explicitly approves a finding for disclosure._
- `def reject_disclosure(disclosure_id: str, reason: str='') -> bool` (L293)
  - _Human operator rejects / archives a finding._
- `def prepare_disclosure_message(disclosure_id: str) -> str` (L306)
  - _After human approval, generate the message for the operator to send_

### `embedding_memory.py`

- Lines: 380  Bytes: 15275

**Module docstring:**

> Rhodawk AI — Embedding-Based Memory Engine v3
> ==============================================
> Dual-backend semantic retrieval:
>   - Default (v2 SQLite): sentence-transformers all-MiniLM-L6-v2 + cosine similarity
>   - Enhanced (v3 Qdrant+CodeBERT): microsoft/codebert-base embeddings stored in
>     an in-process Qdrant vector database for ANN retrieval with HNSW indexing
> 
> CodeBERT understands programming language syntax at the token level, giving
> significantly better semantic similarity for code-related failure traces than
> generic sentence-transformer models.
> 
> Backend selection:
>   RHODAWK_EMBEDDING_BACKEND=sqlite   # default — no extra deps, works everywhere
>   RHODAWK_EMBEDDING_BACKEND=qdrant   # requires: qdrant-client, transformers, torch
> 
> The public API (retrieve_similar_fixes_v2, rebuild_embedding_index,
> record_fix_outcome) is unchanged — all callers continue to work.

**Imports (8):**

- `import hashlib`
- `import os`
- `import re`
- `import sqlite3`
- `import threading`
- `from typing import Optional`
- `import numpy as np`
- `from training_store import DB_PATH`

**Top-level constants (10):**

- `EMBEDDING_DB_PATH` = `os.getenv('RHODAWK_EMBEDDING_DB', '/data/embedding_memory.db')`
- `MODEL_NAME` = `os.getenv('RHODAWK_EMBEDDING_MODEL', 'all-MiniLM-L6-v2')`
- `CODEBERT_MODEL` = `os.getenv('RHODAWK_CODEBERT_MODEL', 'microsoft/codebert-base')`
- `BACKEND` = `os.getenv('RHODAWK_EMBEDDING_BACKEND', 'sqlite').lower()`
- `QDRANT_COLLECTION` = `'rhodawk_fixes'`
- `QDRANT_DIM` = `768`
- `_MINILM_MODEL` = `None`
- `_CODEBERT_TOKENIZER` = `None`
- `_CODEBERT_MODEL` = `None`
- `_QDRANT_CLIENT` = `None`

**Top-level functions (17):**

- `def _get_minilm()` (L51)
- `def _get_codebert()` (L64)
- `def _embed_codebert(text: str) -> np.ndarray` (L75)
- `def _get_qdrant()` (L93)
- `def _normalize_failure(failure_output: str) -> str` (L115)
- `def embed_failure(failure_output: str) -> np.ndarray` (L122)
  - _Embed a failure string using the configured backend model._
- `def pre_warm_model() -> bool` (L133)
  - _Pre-warm the embedding model at startup. Returns True on success._
- `def _ensure_schema() -> None` (L146)
- `def _rebuild_sqlite(limit: int) -> int` (L161)
- `def _retrieve_sqlite(failure_output: str, top_k: int, min_similarity: float) -> list[dict]` (L196)
- `def _point_id(failure_signature: str) -> int` (L238)
  - _Stable integer ID from signature hash — Qdrant requires int or UUID._
- `def _rebuild_qdrant(limit: int) -> int` (L244)
- `def _retrieve_qdrant(failure_output: str, top_k: int, min_similarity: float) -> list[dict]` (L289)
- `def rebuild_embedding_index(limit: int=1000) -> int` (L316)
  - _Rebuild the embedding index from training_store._
- `def retrieve_similar_fixes_v2(failure_output: str, top_k: int=5, min_similarity: float=0.55) -> list[dict]` (L330)
  - _Retrieve semantically similar past fixes for a given failure output._
- `def record_fix_outcome(failure_output: str, test_path: str, diff_text: str, success: bool) -> None` (L354)
  - _Persist a fix outcome to the training store and update the embedding index._
- `def get_memory_stats() -> dict` (L372)
  - _Return basic stats about the embedding index._

### `entrypoint.sh`

- Lines: 93  Bytes: 4193

```bash
#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────
# Rhodawk runtime bootstrap.
#
# 1. Launch the camofox-browser anti-detection browser server on
#    127.0.0.1:9377 (used by the orchestrator via camofox_client.py).
# 2. Launch the OpenClaude headless gRPC daemon for the DigitalOcean
#    Inference provider on :50051 (PRIMARY).
# 3. Launch the OpenClaude headless gRPC daemon for OpenRouter on
#    :50052 (FALLBACK) — only if OPENROUTER_API_KEY is present.
# 4. Wait briefly for everything to bind, then hand control to app.py
#    which talks to them over gRPC + HTTP.
# ─────────────────────────────────────────────────────────────────────
set -eo pipefail

OC_DIR=/opt/openclaude
CAMOFOX_DIR=/opt/camofox
LOG_DIR="${LOG_DIR:-/tmp}"
mkdir -p "${LOG_DIR}"

# ─── camofox-browser ─────────────────────────────────────────────────
# Anti-detection Firefox-fork browser server.  Lazily downloads the
# Camoufox engine (~300MB) on first launch into the user's home dir,
# so the first start may take a minute.  Subsequent starts are fast.
start_camofox() {
    local entry="${CAMOFOX_DIR}/node_modules/@askjo/camofox-browser/server.js"
    [[ -f "${entry}" ]] || entry="${CAMOFOX_DIR}/node_modules/camofox-browser/server.js"
    if [[ ! -f "${entry}" ]]; then
        echo "[entrypoint] camofox-browser not installed — skipping"
        return 0
    fi
    echo "[entrypoint] starting camofox-browser on ${CAMOFOX_HOST:-127.0.0.1}:${CAMOFOX_PORT:-9377}"
    (
        cd "${CAMOFOX_DIR}"
        PORT="${CAMOFOX_PORT:-9377}" \
        HOST="${CAMOFOX_HOST:-127.0.0.1}" \
        CAMOFOX_HEADLESS="${CAMOFOX_HEADLESS:-virtual}" \
        CAMOFOX_PROFILE_DIR="${CAMOFOX_PROFILE_DIR:-/data/camofox/profiles}" \
        CAMOFOX_COOKIES_DIR="${CAMOFOX_COOKIES_DIR:-/data/camofox/cookies}" \
        CAMOFOX_API_KEY="${CAMOFOX_API_KEY:-}" \
        PROXY_HOST="${PROXY_HOST:-}" \
        PROXY_PORT="${PROXY_PORT:-}" \
        PROXY_USERNAME="${PROXY_USERNAME:-}" \
        PROXY_PASSWORD="${PROXY_PASSWORD:-}" \
            node "${entry}" \
                > "${LOG_DIR}/camofox.log" 2>&1 &
        echo $! > "${LOG_DIR}/camofox.pid"
    )
}

start_daemon() {
    local label=$1 port=$2 base_url=$3 api_key=$4 model=$5
    if [[ -z "${api_key}" ]]; then
        echo "[entrypoint] skipping ${label} daemon — no API key"
        return 0
    fi
    echo "[entrypoint] starting OpenClaude ${label} daemon on :${port}"
    (
        cd "${OC_DIR}"
        CLAUDE_CODE_USE_OPENAI=1 \
...
```

### `exploit_primitives.py`

- Lines: 310  Bytes: 11372

**Module docstring:**

> Rhodawk AI — Exploit Primitive Reasoner
> =========================================
> Given a crash or vulnerability candidate, reasons about:
>   1. Exploitability class (overflow, UAF, injection, race, crypto, logic)
>   2. Control flow impact (can attacker redirect execution?)
>   3. Data flow impact (can attacker read/write arbitrary memory?)
>   4. Proof-of-Concept generation (minimal triggerable input)
>   5. Severity and bounty tier estimate
> 
> Uses DeepSeek-R1 (reasoning model) for deep exploit chain analysis.
> Never auto-submits — all output goes to the disclosure pipeline for human review.

**Imports (8):**

- `from __future__ import annotations`
- `import hashlib`
- `import json`
- `import os`
- `import time`
- `import requests`
- `from dataclasses import dataclass, field`
- `from typing import Optional`

**Top-level constants (5):**

- `OPENROUTER_API_KEY` = `os.getenv('OPENROUTER_API_KEY', '')`
- `EXPLOIT_MODEL` = `os.getenv('HERMES_MODEL', 'deepseek/deepseek-r1:free')`
- `OPENROUTER_BASE` = `'https://openrouter.ai/api/v1'`
- `_EXPLOIT_SYSTEM` = `'You are a world-class exploit developer and vulnerability researcher.\nGiven a crash, vulnerability description, or ...`
- `_CVSS_TO_TIER` = `{(9.0, 10.0): 'P1', (7.0, 8.9): 'P2', (4.0, 6.9): 'P3', (0.0, 3.9): 'P4'}`

**Classes (1):**

- `class ExploitAnalysis` — line 32

**Top-level functions (4):**

- `def _estimate_bounty_tier(cvss: float) -> str` (L89)
- `def _call_exploit_reasoner(prompt: str) -> dict` (L96)
- `def reason_exploitability(crash_input: str, crash_output: str, file_path: str, vuln_type: str, source_context: str='') -> dict` (L156)
  - _Main entry point for exploit primitive reasoning._
- `def generate_cve_draft(finding_title: str, finding_description: str, exploit_analysis: dict, affected_repo: str, affected_versions: str='unspecified') -> dict` (L226)
  - _Generate a CVE draft report ready for human review and submission._

### `formal_verifier.py`

- Lines: 191  Bytes: 6214

**Module docstring:**

> Rhodawk AI — Lightweight Formal Verification Gate
> =================================================
> Uses Z3 (SMT solver) to perform bounded symbolic verification of
> simple integer arithmetic, array bounds, and null-safety properties
> extracted from Python diffs.
> 
> This is NOT a full program verifier. It covers:
>   1. Array/list index bounds — catches IndexError when indices are computable
>   2. Integer arithmetic — overflow / divide-by-zero on constant expressions
>   3. Assert statement reachability — checks user asserts are satisfiable
> 
> For complex code (loops, recursion, string ops) it returns SKIP, which does
> NOT block the diff — Z3 gate is advisory, not blocking, unless a definitive
> UNSAFE result is obtained.
> 
> Install: z3-solver  (pip install z3-solver)
> Enable:  RHODAWK_Z3_ENABLED=true

**Imports (3):**

- `import os`
- `import re`
- `import sys as _sys`

**Top-level constants (2):**

- `Z3_ENABLED` = `os.getenv('RHODAWK_Z3_ENABLED', 'true').lower() == 'true'`
- `_IMPORT_OK` = `False`

**Top-level functions (5):**

- `def _extract_added_lines(diff_text: str) -> list[str]` (L54)
- `def _check_divide_by_zero(lines: list[str]) -> list[str]` (L62)
  - _Detect literal divide-by-zero: x / 0 or x % 0._
- `def _check_index_bounds(lines: list[str]) -> list[str]` (L75)
  - _Detect patterns like arr[N] where N is a literal integer and can use Z3_
- `def _check_assert_satisfiability(lines: list[str]) -> list[str]` (L100)
  - _Check assert statements with simple integer inequalities using Z3._
- `def run_formal_verification(diff_text: str) -> dict` (L142)
  - _Run Z3-backed formal verification on the diff._

### `fuzzing_engine.py`

- Lines: 414  Bytes: 14380

**Module docstring:**

> Rhodawk AI — Autonomous Fuzzing Engine
> =======================================
> Generates language-aware fuzzing harnesses using LLM then executes them.
> Integrates with AFL++, libFuzzer (via atheris for Python), and Hypothesis.
> 
> Pipeline per target:
>   1. LLM generates a harness tailored to the target function/API
>   2. Harness is written to /tmp and compiled/instrumented
>   3. Fuzzer runs for duration_s seconds with coverage feedback
>   4. Crashes are triaged: unique crashes extracted, deduped by stack hash
>   5. Results returned for exploit_primitives reasoning
> 
> Supported modes:
>   - Python   → atheris (libFuzzer bindings for Python)
>   - C/C++    → AFL++ subprocess (if installed)
>   - JS/TS    → jsfuzz / fast-check property testing
>   - Generic  → Hypothesis with AI-generated strategies

**Imports (10):**

- `from __future__ import annotations`
- `import hashlib`
- `import json`
- `import os`
- `import subprocess`
- `import tempfile`
- `import time`
- `from dataclasses import dataclass, field`
- `from typing import Optional`
- `import requests`

**Top-level constants (5):**

- `OPENROUTER_API_KEY` = `os.getenv('OPENROUTER_API_KEY', '')`
- `FUZZ_MODEL` = `os.getenv('HERMES_FAST_MODEL', 'deepseek/deepseek-v3:free')`
- `OPENROUTER_BASE` = `'https://openrouter.ai/api/v1'`
- `MAX_FUZZ_DURATION` = `int(os.getenv('RHODAWK_MAX_FUZZ_DURATION', '120'))`
- `FUZZ_CORPUS_DIR` = `os.getenv('RHODAWK_FUZZ_CORPUS', '/data/fuzz_corpus')`

**Classes (2):**

- `class CrashRecord` — line 43
- `class FuzzResult` — line 56

**Top-level functions (7):**

- `def _llm_generate_harness(target: str, language: str, repo_dir: str, source_context: str) -> str` (L67)
  - _Use LLM to generate a fuzzing harness for the target function._
- `def _extract_code_block(text: str) -> str` (L142)
  - _Extract first code block from markdown._
- `def _fallback_harness(target: str, language: str) -> str` (L152)
  - _Generic fallback harness when LLM is unavailable._
- `def _get_source_context(repo_dir: str, target: str, language: str) -> str` (L200)
  - _Extract relevant source code context around the target function._
- `def _run_python_atheris(harness_code: str, duration_s: int) -> list[CrashRecord]` (L224)
  - _Run atheris fuzzer on a Python harness._
- `def _run_hypothesis(repo_dir: str, target: str, harness_code: str, duration_s: int) -> list[CrashRecord]` (L299)
  - _Run Hypothesis property-based testing as a fuzzing fallback._
- `def run_fuzzing_campaign(repo_dir: str, target: str, language: str='python', duration_s: int=60) -> dict` (L343)
  - _Main entry point. Generate harness + run fuzzer + return triage results._

### `github_app.py`

- Lines: 188  Bytes: 5979

**Module docstring:**

> Rhodawk AI — GitHub App Authentication + Fork-and-PR Mode
> ==========================================================
> Handles authentication for:
>   1. GitHub App (short-lived installation tokens) — enterprise mode
>   2. Personal Access Token (PAT) — simple mode
>   3. Fork-and-PR mode (antagonist) — forks any public repo, applies fix, opens cross-repo PR
> 
> Fork-and-PR mode enables Rhodawk to fix ANY public GitHub repository:
>   - Fork target repo under the authenticated user account
>   - Apply fix to the fork
>   - Open a cross-repository PR to upstream
> 
> Enable fork mode: RHODAWK_FORK_MODE=true
> Fork org/user:   RHODAWK_FORK_OWNER (defaults to authenticated user)

**Imports (4):**

- `import os`
- `import time`
- `import jwt`
- `import requests`

**Top-level functions (6):**

- `def get_installation_token(repo: str) -> str` (L25)
- `def get_github_token(repo: str) -> str` (L58)
- `def get_authenticated_user(token: str) -> str` (L67)
  - _Return the login of the authenticated GitHub user._
- `def fork_repo(upstream_repo: str, token: str) -> str` (L81)
  - _Fork upstream_repo to the authenticated user's account (or RHODAWK_FORK_OWNER org)._
- `def create_cross_repo_pr(upstream_repo: str, fork_full_name: str, branch: str, test_path: str, token: str) -> str` (L124)
  - _Open a cross-repository PR from fork:branch → upstream:main._
- `def open_pr_for_repo(upstream_repo: str, branch: str, test_path: str, token: str, fork_mode: bool=False) -> str` (L169)
  - _Unified PR creation:_

### `harness_factory.py`

- Lines: 220  Bytes: 7418

**Module docstring:**

> Rhodawk AI — Ethical PoC Harness Factory
> =========================================
> Generates minimal proof-of-concept test harnesses that exercise identified
> assumption gaps LOCALLY in an isolated sandbox.
> 
> ETHICAL CONSTRAINTS (hard-coded, not configurable):
>   - Generated harnesses target only locally cloned source code
>   - No network calls from within generated harnesses
>   - Execution is time-limited (default 30 s)
>   - All secrets stripped from sandbox environment
>   - Harness code is shown to operator BEFORE execution — never auto-run
>   - Output is PoC-grade only: demonstrates behaviour, not weaponised
> 
> Orchestrated by Nous Hermes 3 via OpenRouter.

**Imports (9):**

- `from __future__ import annotations`
- `import os`
- `import re`
- `import subprocess`
- `import tempfile`
- `import time`
- `from pathlib import Path`
- `from typing import Optional`
- `import requests`

**Top-level constants (5):**

- `OPENROUTER_API_KEY` = `os.getenv('OPENROUTER_API_KEY', '')`
- `HERMES_MODEL` = `os.getenv('RHODAWK_RESEARCH_MODEL', 'nousresearch/hermes-3-llama-3.1-405b:free')`
- `HARNESS_TIMEOUT` = `int(os.getenv('RHODAWK_HARNESS_TIMEOUT', '30'))`
- `_SECRETS` = `['OPENROUTER_API_KEY', 'GITHUB_TOKEN', 'GITHUB_PERSONAL_ACCESS_TOKEN', 'TELEGRAM_BOT_TOKEN', 'SLACK_WEBHOOK_URL', 'RH...`
- `_HARNESS_PREAMBLE` = `'# ETHICAL POC — FOR RESPONSIBLE DISCLOSURE ONLY\n# Generated by Rhodawk AI Ethical Security Research Platform\n# Thi...`

**Top-level functions (3):**

- `def _hermes(system: str, user: str) -> str` (L50)
- `def generate_poc_harness(assumption_gap: dict, repo_dir: str) -> dict` (L73)
  - _Ask Hermes to generate a minimal PoC harness for a specific assumption gap._
- `def run_harness_in_sandbox(harness_code: str, repo_dir: str, venv_dir: str='/data/target_venv') -> dict` (L151)
  - _Execute a HUMAN-REVIEWED harness in an isolated local sandbox._

### `hermes_orchestrator.py`

- Lines: 885  Bytes: 38655

**Module docstring:**

> Rhodawk AI — Hermes Master Orchestrator
> ========================================
> Hermes is the intelligent agent that coordinates all security research components.
> It acts as the "brain" — deciding which tools to deploy, in what order, and how
> to synthesize findings into a coherent vulnerability report.
> 
> Architecture:
>   Hermes receives a target (repo + optional focus area) and executes a dynamic
>   multi-phase research plan using tool calls. It maintains state across phases,
>   routes findings between components, and escalates confidence incrementally.
> 
> Phases:
>   1. RECON       — clone, fingerprint, map attack surface
>   2. STATIC      — taint analysis, symbolic execution planning, CWE pattern match
>   3. DYNAMIC     — fuzzing harness generation + execution
>   4. EXPLOIT     — exploit primitive reasoning on confirmed crashes
>   5. CONSENSUS   — multi-model adversarial verdict on findings
>   6. DISCLOSURE  — package report, hold for human approval
> 
> Custom Algorithms:
>   VES  — Vulnerability Entropy Score: how surprising/dangerous a code path is
>   TVG  — Temporal Vulnerability Graph: how bugs propagate across commits
>   ACTS — Adversarial Consensus Trust Score: Bayesian multi-model confidence
>   CAD  — Commit Anomaly Detection: statistical detection of silent security patches
>   SSEC — Semantic Similarity Exploit Chain: embedding distance to known exploit patterns

**Imports (11):**

- `from __future__ import annotations`
- `import hashlib`
- `import json`
- `import os`
- `import threading`
- `import time`
- `from dataclasses import dataclass, field, asdict`
- `from enum import Enum`
- `from typing import Any, Callable, Optional`
- `import requests`
- `import collections as _collections`

**Top-level constants (12):**

- `OPENROUTER_API_KEY` = `os.getenv('OPENROUTER_API_KEY', '')`
- `HERMES_MODEL` = `os.getenv('HERMES_MODEL', 'deepseek/deepseek-r1:free')`
- `HERMES_FAST_MODEL` = `os.getenv('HERMES_FAST_MODEL', 'deepseek/deepseek-v3:free')`
- `OPENROUTER_BASE` = `'https://openrouter.ai/api/v1'`
- `HERMES_PROVIDER` = `os.getenv('HERMES_PROVIDER', 'auto').lower().strip()`
- `DO_INFERENCE_API_KEY` = `os.getenv('DO_INFERENCE_API_KEY', '') or os.getenv('DIGITALOCEAN_INFERENCE_KEY', '')`
- `DO_INFERENCE_BASE` = `os.getenv('DO_INFERENCE_BASE_URL', 'https://inference.do-ai.run/v1').rstrip('/')`
- `DO_HERMES_MODEL` = `os.getenv('HERMES_DO_MODEL', 'llama3.3-70b-instruct')`
- `_HERMES_LOG_CAP` = `int(os.getenv('HERMES_LOG_CAP', '10000'))`
- `_HERMES_SESSION_DIR` = `os.getenv('HERMES_SESSION_DIR', '/data/hermes')`
- `_HERMES_SYSTEM` = `'You are Hermes, a world-class autonomous security research agent.\nYour goal is to find real, exploitable vulnerabil...`
- `_RATE_LIMIT_BACKOFF_DELAYS` = `[15, 30, 60]`

**Classes (13):**

- `class ResearchPhase(str, Enum)` — line 132
- `class VulnerabilityFinding` — line 143
- `class HermesSession` — line 163
- `class HermesTool` — line 180
  - _Base class for all Hermes-dispatchable tools._
    - `def run(self, **kwargs) -> dict` (L185)
- `class ReconTool(HermesTool)` — line 189
    - `def run(self, repo_dir: str, **kwargs) -> dict` (L193)
- `class TaintTool(HermesTool)` — line 199
    - `def run(self, repo_dir: str, focus_files: list[str]=None, **kwargs) -> dict` (L203)
- `class SymbolicTool(HermesTool)` — line 209
    - `def run(self, repo_dir: str, target_function: str=None, **kwargs) -> dict` (L213)
- `class FuzzTool(HermesTool)` — line 219
    - `def run(self, repo_dir: str, target: str, language: str='python', duration_s: int=60, **kwargs) -> dict` (L223)
- `class ExploitTool(HermesTool)` — line 229
    - `def run(self, crash_input: str, crash_output: str, file_path: str, vuln_type: str, **kwargs) -> dict` (L233)
- `class CVETool(HermesTool)` — line 239
    - `def run(self, description: str, cwe_hint: str=None, **kwargs) -> dict` (L243)
- `class CommitWatchTool(HermesTool)` — line 249
    - `def run(self, repo_dir: str, lookback_commits: int=50, **kwargs) -> dict` (L253)
- `class SSECTool(HermesTool)` — line 259
    - `def run(self, repo_dir: str, focus_files: list[str]=None, **kwargs) -> dict` (L263)
- `class ChainAnalyzerTool(HermesTool)` — line 269
    - `def run(self, repo_dir: str, repo: str='', **kwargs) -> dict` (L277)

**Top-level functions (13):**

- `def hermes_log(msg: str, level: str='HERMES')` (L79)
- `def get_hermes_logs() -> list[str]` (L93)
- `def persist_hermes_session(session) -> str | None` (L102)
  - _Atomically persist a HermesSession dataclass to disk after each phase._
- `def _dispatch_tool(tool_name: str, args: dict, session: HermesSession) -> dict` (L297)
- `def compute_ves(reachability: float, severity_class: str, novelty: float, exploit_complexity: str, auth_required: bool) -> float` (L319)
  - _VES (Vulnerability Entropy Score) — custom algorithm._
- `def compute_acts(model_verdicts: list[dict]) -> float` (L354)
  - _ACTS (Adversarial Consensus Trust Score) — Bayesian multi-model confidence._
- `def _strip_provider_prefix(model: str) -> str` (L435)
  - _Strip OpenRouter / OpenAI provider prefixes so we can re-target a_
- `def _post_chat_completion(base_url: str, api_key: str, model: str, messages: list[dict], timeout: int, extra_headers: dict | None=None) -> dict` (L444)
  - _Single OpenAI-compatible POST. Raises on non-2xx; returns parsed JSON_
- `def _hermes_llm_call(messages: list[dict], model: str=None, timeout: int=120) -> dict` (L472)
  - _Call the Hermes LLM with DigitalOcean Serverless Inference as the_
- `def run_hermes_research(target_repo: str, repo_dir: str, focus_area: str='', max_iterations: int=20, progress_callback: Optional[Callable[[str], None]]=None) -> HermesSession` (L584)
  - _Main Hermes research loop. Runs until max_iterations or completion._
- `def _run_acts_consensus(session: HermesSession)` (L746)
  - _Run multi-model adversarial consensus on each finding to compute ACTS score._
- `def build_tvg(repo_dir: str, findings: list[VulnerabilityFinding]) -> dict` (L822)
  - _TVG (Temporal Vulnerability Graph) — tracks how vulnerability patterns_
- `def get_session_summary(session: HermesSession) -> dict` (L861)
  - _Produce a human-readable summary of a research session._

### `job_queue.py`

- Lines: 226  Bytes: 8150

**Module docstring:**

> Rhodawk AI — Namespaced Job Queue (SQLite backed, v2 — Apr 2026)
> ================================================================
> Replaces the original per-file JSON store with a single SQLite database so
> that concurrent writers (web UI + nightmode + OSS-Guardian) never race on
> ``open(...).replace(...)``.  All previous JSON files in ``/data/jobs/``
> are imported on first start, then ignored.
> 
> The public API is intentionally identical to the v1 module so callers
> do not need to change.

**Imports (11):**

- `from __future__ import annotations`
- `import hashlib`
- `import json`
- `import logging`
- `import os`
- `import sqlite3`
- `import threading`
- `import time`
- `from enum import Enum`
- `from pathlib import Path`
- `from typing import Optional`

**Top-level constants (5):**

- `LOG` = `logging.getLogger('job_queue')`
- `QUEUE_DIR` = `'/data/jobs'`
- `DB_PATH` = `os.getenv('JOB_QUEUE_DB', '/data/jobs.sqlite')`
- `_LOCK` = `threading.Lock()`
- `_MIGRATED` = `False`

**Classes (1):**

- `class JobStatus(Enum)` — line 33

**Top-level functions (10):**

- `def _job_id(tenant_id: str, repo: str, test_path: str) -> str` (L41)
- `def _connect() -> sqlite3.Connection` (L46)
- `def _migrate_legacy_json() -> int` (L72)
  - _One-shot import of any leftover ``/data/jobs/*.json`` files._
- `def _ensure_migrated() -> None` (L117)
- `def upsert_job(tenant_id: str, repo: str, test_path: str, status: JobStatus, detail: str='', pr_url: Optional[str]=None, sast_findings: Optional[list]=None, model_version: Optional[str]=None, prompt_hash: Optional[str]=None) -> str` (L128)
- `def get_job(tenant_id: str, repo: str, test_path: str) -> Optional[dict]` (L166)
- `def get_job_status_enum(tenant_id: str, repo: str, test_path: str) -> Optional[JobStatus]` (L175)
- `def list_all_jobs() -> list[dict]` (L185)
- `def get_metrics() -> dict` (L195)
- `def prune_done_jobs(max_age_hours: int=72) -> int` (L215)
  - _Remove DONE/FAILED jobs older than ``max_age_hours``._

### `knowledge_rag.py`

- Lines: 200  Bytes: 7393

**Module docstring:**

> knowledge_rag.py — security-knowledge RAG store (Masterplan §1.4).
> 
> A small, dependency-light vector store of security writeups, CVE detail
> pages, disclosed bug-bounty reports, and research papers.  The store reuses
> the embedder from ``embedding_memory.py`` if available, otherwise falls
> back to a deterministic hash-bag baseline so unit tests pass with zero
> extra dependencies.
> 
> The store is a single SQLite file under ``/data/knowledge_rag.sqlite`` so
> it survives Space restarts and can be snapshotted to GitHub like the rest
> of the Hermes memory.

**Imports (11):**

- `from __future__ import annotations`
- `import hashlib`
- `import json`
- `import logging`
- `import math`
- `import os`
- `import sqlite3`
- `import time`
- `from dataclasses import dataclass, field`
- `from pathlib import Path`
- `from typing import Any, Iterable`

**Top-level constants (3):**

- `LOG` = `logging.getLogger('knowledge_rag')`
- `DB_PATH` = `Path(os.getenv('KNOWLEDGE_RAG_DB', '/data/knowledge_rag.sqlite'))`
- `EMBED_DIM` = `256`

**Classes (2):**

- `class Document` — line 47
- `class KnowledgeRAG` — line 103
  - _Vector store of security knowledge documents._
    - `def __init__(self, db_path: Path | None=None)` (L108)
    - `def add(self, *, source: str, *, title: str, *, text: str, *, tags: Iterable[str] | None=None) -> str` (L114)
    - `def add_many(self, items: list[dict[str, Any]]) -> int` (L130)
    - `def ingest_text_file(self, path: str | Path, source: str) -> int` (L145)
      - _Ingest a markdown / text file as one document per top-level heading._
    - `def query(self, query_text: str, *, top_k: int=5, *, source_prefix: str | None=None) -> list[Document]` (L170)
    - `def stats(self) -> dict[str, Any]` (L194)

**Top-level functions (4):**

- `def _hash_embed(text: str, dim: int=EMBED_DIM) -> list[float]` (L57)
  - _Deterministic hash-bag embedder — no external deps, good enough for_
- `def _embed(text: str) -> list[float]` (L68)
- `def _cosine(a: list[float], b: list[float]) -> float` (L79)
- `def _connect() -> sqlite3.Connection` (L86)

### `language_runtime.py`

- Lines: 1598  Bytes: 69987

**Module docstring:**

> Rhodawk AI — Universal Language Runtime Abstraction
> =====================================================
> Replaces all Python-specific hardcoding in app.py with a pluggable runtime
> system. Each LanguageRuntime implementation handles:
> 
>   1. detect()           — fingerprint a cloned repo to identify its language
>   2. setup_env()        — install deps, return an EnvConfig (replaces setup_target_venv)
>   3. discover_tests()   — find test files matching language conventions
>   4. run_tests()        — execute one test file, return (output, exit_code)
>   5. run_sast()         — language-specific static analysis on a diff
>   6. run_supply_chain() — language-specific dep audit on a diff
>   7. get_mcp_domains()  — docs domains the MCP fetch tool is allowed to hit
>   8. get_fix_prompt_instructions() — language-aware instructions appended to Aider prompts
> 
> RuntimeFactory.for_repo(repo_dir) auto-detects and returns the right runtime.
> Fall-through: if detection is ambiguous, PythonRuntime is used as default.
> 
> Supported languages
> -------------------
>   Python     pytest / uv / pip-audit / bandit
>   JavaScript jest|mocha|vitest / npm / npm-audit / eslint-security
>   TypeScript same as JS + tsc type-check step
>   Java       Maven|Gradle / JUnit|TestNG / OWASP dep-check / semgrep-java
>   Go         go test / govulncheck / gosec
>   Rust       cargo test / cargo-audit / clippy
>   Ruby       RSpec|Minitest / bundler / bundle-audit / brakeman
> 
> Adding a new language
> ---------------------
>   1. Subclass LanguageRuntime.
>   2. Implement all abstract methods.
>   3. Append instance to RuntimeFactory._REGISTRY (order matters — first match wins).

**Imports (15):**

- `from __future__ import annotations`
- `import glob`
- `import json`
- `import os`
- `import re`
- `import signal`
- `import shutil`
- `import subprocess`
- `import tempfile`
- `import threading`
- `import time`
- `from abc import ABC, abstractmethod`
- `from dataclasses import dataclass, field`
- `from pathlib import Path`
- `from typing import Optional`

**Classes (13):**

- `class EnvConfig` — line 85
  - _Opaque handle returned by setup_env(); passed back into run_tests()._
- `class RuntimeSastFinding` — line 95
- `class RuntimeSastReport` — line 104
    - `def summary(self) -> str` (L111)
- `class RuntimeSupplyChainReport` — line 118
    - `def summary(self) -> str` (L127)
- `class LanguageRuntime(ABC)` — line 137
  - _Abstract base — one concrete subclass per supported language._
    - `def detect(cls, repo_dir: str) -> bool` (L146)
      - _Return True if this runtime should handle the given repo._
    - `def setup_env(self, repo_dir: str, persistent_dir: str='/data') -> EnvConfig` (L155)
      - _Install dependencies; return an EnvConfig._
    - `def discover_tests(self, repo_dir: str) -> list[str]` (L164)
      - _Return a list of test file paths RELATIVE to repo_dir._
    - `def run_tests(self, test_path: str, repo_dir: str, env_config: EnvConfig, timeout: int=120) -> tuple[str, int]` (L173)
      - _Run a single test file. Return (combined_output, exit_code)._
    - `def run_sast(self, diff_text: str, changed_files: list[str], repo_dir: str) -> RuntimeSastReport` (L188)
      - _Run static analysis on the AI-generated diff._
    - `def run_supply_chain(self, diff_text: str, repo_dir: str) -> RuntimeSupplyChainReport` (L197)
      - _Audit dependencies added/changed by the AI diff._
    - `def get_mcp_domains(self) -> list[str]` (L207)
      - _Return allowed documentation domains for the MCP fetch tool._
    - `def get_fix_prompt_instructions(self, test_path: str, branch_name: str, src_hint: str='') -> str` (L211)
      - _Language-specific instruction block appended to Aider prompts._
    - `def _run(cmd: list[str], cwd: str, timeout: int=300, extra_env: dict | None=None, raise_on_error: bool=False) -> tuple[str, int]` (L225)
      - _Thin safe subprocess wrapper (shell=False enforced)._
- `class PythonRuntime(LanguageRuntime)` — line 285
    - `def detect(cls, repo_dir: str) -> bool` (L289)
    - `def setup_env(self, repo_dir: str, persistent_dir: str='/data') -> EnvConfig` (L296)
    - `def discover_tests(self, repo_dir: str) -> list[str]` (L392)
    - `def run_tests(self, test_path: str, repo_dir: str, env_config: EnvConfig, timeout: int=120) -> tuple[str, int]` (L407)
    - `def run_sast(self, diff_text: str, changed_files: list[str], repo_dir: str) -> RuntimeSastReport` (L414)
    - `def run_supply_chain(self, diff_text: str, repo_dir: str) -> RuntimeSupplyChainReport` (L433)
    - `def get_mcp_domains(self) -> list[str]` (L449)
    - `def get_fix_prompt_instructions(self, test_path: str, branch_name: str, src_hint: str='') -> str` (L455)
- `class NodeRuntime(LanguageRuntime)` — line 471
    - `def detect(cls, repo_dir: str) -> bool` (L486)
    - `def _is_typescript(cls, repo_dir: str, pkg_data: dict) -> bool` (L498)
    - `def _detect_runner(self, repo_dir: str) -> tuple[str, list[str]]` (L504)
    - `def setup_env(self, repo_dir: str, persistent_dir: str='/data') -> EnvConfig` (L524)
    - `def discover_tests(self, repo_dir: str) -> list[str]` (L547)
    - `def run_tests(self, test_path: str, repo_dir: str, env_config: EnvConfig, timeout: int=120) -> tuple[str, int]` (L562)
    - `def run_sast(self, diff_text: str, changed_files: list[str], repo_dir: str) -> RuntimeSastReport` (L578)
    - `def _scan_secrets(self, diff_text: str) -> list[RuntimeSastFinding]` (L603)
      - _Reuse the universal secret patterns from sast_gate._
    - `def _scan_js_patterns(self, diff_text: str) -> list[RuntimeSastFinding]` (L627)
    - `def _run_semgrep(self, changed_files: list[str], repo_dir: str) -> str` (L641)
    - `def run_supply_chain(self, diff_text: str, repo_dir: str) -> RuntimeSupplyChainReport` (L656)
    - `def _extract_new_npm_packages(self, diff_text: str) -> list[str]` (L692)
    - `def _check_npm_typosquat(self, package_name: str) -> Optional[str]` (L706)
    - `def _levenshtein(s1: str, s2: str) -> int` (L719)
    - `def _run_npm_audit(self, repo_dir: str) -> list[dict]` (L732)
    - `def get_mcp_domains(self) -> list[str]` (L751)
    - `def get_fix_prompt_instructions(self, test_path: str, branch_name: str, src_hint: str='') -> str` (L758)
- `class TypeScriptRuntime(NodeRuntime)` — line 775
    - `def detect(cls, repo_dir: str) -> bool` (L779)
    - `def discover_tests(self, repo_dir: str) -> list[str]` (L791)
    - `def setup_env(self, repo_dir: str, persistent_dir: str='/data') -> EnvConfig` (L806)
    - `def run_sast(self, diff_text: str, changed_files: list[str], repo_dir: str) -> RuntimeSastReport` (L811)
    - `def _run_tsc(self, repo_dir: str) -> str` (L820)
    - `def _run_semgrep(self, changed_files: list[str], repo_dir: str) -> str` (L830)
    - `def get_mcp_domains(self) -> list[str]` (L845)
    - `def get_fix_prompt_instructions(self, test_path: str, branch_name: str, src_hint: str='') -> str` (L850)
- `class JavaRuntime(LanguageRuntime)` — line 866
    - `def detect(cls, repo_dir: str) -> bool` (L870)
    - `def _has_maven(self, repo_dir: str) -> bool` (L874)
    - `def setup_env(self, repo_dir: str, persistent_dir: str='/data') -> EnvConfig` (L877)
    - `def discover_tests(self, repo_dir: str) -> list[str]` (L898)
    - `def run_tests(self, test_path: str, repo_dir: str, env_config: EnvConfig, timeout: int=300) -> tuple[str, int]` (L911)
    - `def run_sast(self, diff_text: str, changed_files: list[str], repo_dir: str) -> RuntimeSastReport` (L928)
    - `def _scan_secrets(self, diff_text: str) -> list[RuntimeSastFinding]` (L950)
    - `def _scan_java_patterns(self, diff_text: str) -> list[RuntimeSastFinding]` (L971)
    - `def _run_semgrep_java(self, changed_files: list[str], repo_dir: str) -> str` (L985)
    - `def run_supply_chain(self, diff_text: str, repo_dir: str) -> RuntimeSupplyChainReport` (L1000)
    - `def _extract_new_maven_deps(self, diff_text: str) -> list[str]` (L1016)
    - `def _run_owasp_check(self, repo_dir: str) -> tuple[str, int]` (L1033)
    - `def _parse_owasp_output(self, raw: str) -> list[dict]` (L1042)
    - `def get_mcp_domains(self) -> list[str]` (L1058)
    - `def get_fix_prompt_instructions(self, test_path: str, branch_name: str, src_hint: str='') -> str` (L1064)
- `class GoRuntime(LanguageRuntime)` — line 1080
    - `def detect(cls, repo_dir: str) -> bool` (L1084)
    - `def setup_env(self, repo_dir: str, persistent_dir: str='/data') -> EnvConfig` (L1087)
    - `def discover_tests(self, repo_dir: str) -> list[str]` (L1095)
    - `def run_tests(self, test_path: str, repo_dir: str, env_config: EnvConfig, timeout: int=120) -> tuple[str, int]` (L1101)
    - `def run_sast(self, diff_text: str, changed_files: list[str], repo_dir: str) -> RuntimeSastReport` (L1110)
    - `def _scan_secrets(self, diff_text: str) -> list[RuntimeSastFinding]` (L1126)
    - `def _scan_go_patterns(self, diff_text: str) -> list[RuntimeSastFinding]` (L1146)
    - `def _run_gosec(self, changed_files: list[str], repo_dir: str) -> str` (L1160)
    - `def run_supply_chain(self, diff_text: str, repo_dir: str) -> RuntimeSupplyChainReport` (L1170)
    - `def _extract_new_go_modules(self, diff_text: str) -> list[str]` (L1189)
    - `def _parse_govulncheck(self, raw: str) -> list[dict]` (L1200)
    - `def get_mcp_domains(self) -> list[str]` (L1208)
    - `def get_fix_prompt_instructions(self, test_path: str, branch_name: str, src_hint: str='') -> str` (L1214)
- `class RustRuntime(LanguageRuntime)` — line 1231
    - `def detect(cls, repo_dir: str) -> bool` (L1235)
    - `def setup_env(self, repo_dir: str, persistent_dir: str='/data') -> EnvConfig` (L1238)
    - `def discover_tests(self, repo_dir: str) -> list[str]` (L1246)
    - `def run_tests(self, test_path: str, repo_dir: str, env_config: EnvConfig, timeout: int=180) -> tuple[str, int]` (L1259)
    - `def run_sast(self, diff_text: str, changed_files: list[str], repo_dir: str) -> RuntimeSastReport` (L1274)
    - `def _scan_secrets(self, diff_text: str) -> list[RuntimeSastFinding]` (L1288)
    - `def _scan_rust_patterns(self, diff_text: str) -> list[RuntimeSastFinding]` (L1307)
    - `def _run_clippy(self, repo_dir: str) -> str` (L1321)
    - `def run_supply_chain(self, diff_text: str, repo_dir: str) -> RuntimeSupplyChainReport` (L1328)
    - `def _extract_new_crates(self, diff_text: str) -> list[str]` (L1344)
    - `def _parse_cargo_audit(self, raw: str) -> list[dict]` (L1356)
    - `def get_mcp_domains(self) -> list[str]` (L1371)
    - `def get_fix_prompt_instructions(self, test_path: str, branch_name: str, src_hint: str='') -> str` (L1374)
- `class RubyRuntime(LanguageRuntime)` — line 1390
    - `def detect(cls, repo_dir: str) -> bool` (L1394)
    - `def _detect_runner(self, repo_dir: str) -> str` (L1400)
    - `def setup_env(self, repo_dir: str, persistent_dir: str='/data') -> EnvConfig` (L1409)
    - `def discover_tests(self, repo_dir: str) -> list[str]` (L1424)
    - `def run_tests(self, test_path: str, repo_dir: str, env_config: EnvConfig, timeout: int=120) -> tuple[str, int]` (L1436)
    - `def run_sast(self, diff_text: str, changed_files: list[str], repo_dir: str) -> RuntimeSastReport` (L1444)
    - `def _scan_secrets(self, diff_text: str) -> list[RuntimeSastFinding]` (L1458)
    - `def _scan_ruby_patterns(self, diff_text: str) -> list[RuntimeSastFinding]` (L1479)
    - `def _run_brakeman(self, repo_dir: str) -> str` (L1493)
    - `def run_supply_chain(self, diff_text: str, repo_dir: str) -> RuntimeSupplyChainReport` (L1503)
    - `def _extract_new_gems(self, diff_text: str) -> list[str]` (L1522)
    - `def _parse_bundle_audit(self, raw: str) -> list[dict]` (L1533)
    - `def get_mcp_domains(self) -> list[str]` (L1541)
    - `def get_fix_prompt_instructions(self, test_path: str, branch_name: str, src_hint: str='') -> str` (L1547)
- `class RuntimeFactory` — line 1563
  - _Detects and returns the correct LanguageRuntime for a cloned repo._
    - `def for_repo(cls, repo_dir: str) -> LanguageRuntime` (L1581)
      - _Auto-detect and instantiate the correct runtime._
    - `def language_of(cls, repo_dir: str) -> str` (L1592)
      - _Lightweight language label without instantiation._
    - `def supported_languages(cls) -> list[str]` (L1597)

**Top-level functions (1):**

- `def kill_runtime_processes() -> int` (L58)

### `lora_scheduler.py`

- Lines: 258  Bytes: 9089

**Module docstring:**

> Rhodawk AI — LoRA Fine-Tune Scheduler
> ======================================
> Schedules periodic LoRA adapter fine-tuning runs using accumulated
> (failure, fix) pairs from the training store.
> 
> This is NOT a training pipeline — it exports the training data in JSONL
> format ready for consumption by:
>   - Hugging Face PEFT + TRL (local SFT)
>   - Hugging Face AutoTrain API
>   - OpenRouter/Together batch fine-tune API (when available)
> 
> The scheduler monitors fix_success_rate and triggers a training export
> when enough new high-quality data has accumulated since the last run.
> 
> Trigger conditions (any one sufficient):
>   - NEW_GOOD_FIXES >= LORA_MIN_SAMPLES (default 50) since last run
>   - Time since last run >= LORA_MAX_AGE_HOURS (default 168 = 1 week)
> 
> Output artifact: /data/lora_training_data_{timestamp}.jsonl
> Format: standard chat-format instruction tuning JSONL:
>   {"messages": [{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}]}
> 
> Enable: RHODAWK_LORA_ENABLED=true

**Imports (5):**

- `import json`
- `import os`
- `import sqlite3`
- `import time`
- `from training_store import DB_PATH`

**Top-level constants (6):**

- `LORA_ENABLED` = `os.getenv('RHODAWK_LORA_ENABLED', 'false').lower() == 'true'`
- `LORA_MIN_SAMPLES` = `int(os.getenv('RHODAWK_LORA_MIN_SAMPLES', '50'))`
- `LORA_MAX_AGE_H` = `int(os.getenv('RHODAWK_LORA_MAX_AGE_HOURS', '168'))`
- `LORA_OUTPUT_DIR` = `os.getenv('RHODAWK_LORA_OUTPUT_DIR', '/data/lora_exports')`
- `LORA_STATE_PATH` = `'/data/lora_scheduler_state.json'`
- `SYSTEM_PROMPT` = `'You are Rhodawk, an expert AI software engineer specializing in debugging and fixing failing automated tests. You pr...`

**Top-level functions (8):**

- `def _load_state() -> dict` (L47)
- `def _save_state(state: dict) -> None` (L57)
- `def _count_good_fixes_since(since_count: int) -> int` (L62)
  - _Count successful fix attempts added since the last export._
- `def _export_training_data(min_success: int=1, limit: int=2000) -> list[dict]` (L74)
  - _Export (failure, fix) pairs as chat-format messages._
- `def should_trigger_training() -> tuple[bool, str]` (L120)
  - _Check whether training conditions are met._
- `def run_training_export() -> dict` (L145)
  - _Export training data to a JSONL file._
- `def maybe_trigger_training() -> str` (L216)
  - _Call this after each audit cycle. Triggers export if conditions are met._
- `def get_scheduler_status() -> str` (L234)
  - _Human-readable scheduler status for the dashboard._

### `mcp_config.ARCHIVE.json`

- Lines: 509  Bytes: 16558

**Top-level keys (3):** `_W003_ARCHIVE_NOTICE`, `_comment`, `mcpServers`

### `memory_engine.py`

- Lines: 134  Bytes: 5026

**Module docstring:**

> Rhodawk AI — Fix Memory Engine (Data Flywheel)
> ===============================================
> Retrieves semantically similar past successful fixes and injects them as
> few-shot examples into the prompt for new failures.
> 
> This is the compounding advantage: the more repos Rhodawk heals, the better
> it gets at healing new repos. After 500 examples, fix accuracy on similar
> failures improves measurably. After 5,000 — you fine-tune the model on it.
> 
> Implementation: TF-IDF based similarity on failure signatures.
> No external embedding API required. Runs entirely on-device.
> Designed to be swapped out for a vector database (Pinecone/Qdrant) at scale.

**Imports (6):**

- `import hashlib`
- `import re`
- `import sqlite3`
- `from collections import Counter`
- `from typing import Optional`
- `from training_store import DB_PATH`

**Top-level functions (5):**

- `def _tokenize(text: str) -> list[str]` (L25)
- `def _tf_idf_similarity(query_tokens: list[str], doc_tokens: list[str], corpus_df: dict, corpus_size: int) -> float` (L35)
- `def retrieve_similar_fixes(failure_output: str, top_k: int=3, min_similarity: float=0.15) -> list[dict]` (L62)
  - _Retrieve the most similar successful past fixes for a given failure output._
- `def record_fix_outcome(failure_output: str, context: str, fix_diff: str, success: bool)` (L119)
  - _Called after each fix attempt to update the memory store._
- `def get_memory_stats() -> dict` (L126)

### `night_hunt_lock.py`

- Lines: 95  Bytes: 2998

**Module docstring:**

> Rhodawk AI — Night Hunt Mutual Exclusion Lock
> ==============================================
> Resolves W-009 (MEDIUM): two entirely separate autonomous bug-bounty hunting
> systems exist (`night_hunt_orchestrator.py` and `architect/nightmode.py`). Both
> can be enabled simultaneously and both scan the same bounty platform scope
> (HackerOne, Bugcrowd, Intigriti) with no deduplication or coordination.
> 
> This module exposes a single in-process re-entrant lock that BOTH orchestrators
> must acquire before running a hunt cycle. Whichever loop wakes up first holds
> the lock for the duration of its cycle; the other simply skips this round and
> sleeps until its next scheduled wake.
> 
> Cross-process protection (multi-container deployments) should layer a
> SQLite/Postgres advisory lock on top of this, but for the single-container HF
> Spaces deployment the in-process lock is sufficient.
> 
> Usage:
> 
>     from night_hunt_lock import try_acquire_night_hunt, release_night_hunt
> 
>     if not try_acquire_night_hunt("architect-nightmode"):
>         LOG.info("another night-hunt loop is already running; skipping cycle")
>         return
>     try:
>         run_one_cycle()
>     finally:
>         release_night_hunt("architect-nightmode")
> 
> Or as a context manager:
> 
>     from night_hunt_lock import night_hunt_guard
>     with night_hunt_guard("night-hunt-orchestrator") as acquired:
>         if not acquired:
>             return
>         run_night_cycle()

**Imports (5):**

- `from __future__ import annotations`
- `import os`
- `import threading`
- `import time`
- `from contextlib import contextmanager`

**Top-level constants (2):**

- `_ENABLED` = `os.getenv('RHODAWK_NIGHT_HUNT_LOCK', 'true').lower() == 'true'`
- `_LOCK` = `threading.Lock()`

**Top-level functions (4):**

- `def is_locked() -> tuple[bool, str | None, float]` (L55)
  - _Return (locked, holder_name, seconds_held)._
- `def try_acquire_night_hunt(holder: str) -> bool` (L63)
  - _Non-blocking acquire. Returns True if this caller now owns the lock._
- `def release_night_hunt(holder: str) -> None` (L76)
  - _Release the lock. Only the current holder may release._
- `def night_hunt_guard(holder: str)` (L88)
  - _Context manager that yields True if the lock was acquired._

### `night_hunt_orchestrator.py`

- Lines: 567  Bytes: 22875

**Module docstring:**

> Rhodawk AI — Night Hunter orchestrator (Masterplan §3, §9 Week 2).
> 
> End-to-end loop for autonomous bug-bounty hunting:
> 
>     SCOPE INGEST   → scope_parser_mcp / bounty_gateway
>     TARGET SELECT  → score by recency, breadth, tech-match, competition
>     RECON          → subdomain_enum + httpx + wayback + shodan
>     HUNT           → nuclei + zap + sqlmap + jwt-analyzer + cors-analyzer
>                      + (optional) browser-agent for authenticated flows
>     VALIDATE       → adversarial 3-model consensus + reproducibility filter
>     REPORT         → per-platform draft submission + Telegram briefing
> 
> Designed to **never auto-submit** in the first 50 cycles — the operator
> reviews and approves every finding via the Gradio Night Hunter tab or
> the OpenClaw ``approve-finding`` skill.
> 
> This module is heavy on graceful degradation: every external dependency
> (MCP server, scanner binary, LLM endpoint) is wrapped in try/except so a
> missing tool downgrades the cycle quality but never crashes it.
> 
> Public surface:
> 
>     run_night_cycle(...)        → NightCycleReport
>     schedule_loop(start_hour=23) → blocking heartbeat scheduler
>     start_in_background()        → daemon thread for app.py

**Imports (11):**

- `from __future__ import annotations`
- `import json`
- `import logging`
- `import os`
- `import threading`
- `import time`
- `import uuid`
- `from dataclasses import asdict, dataclass, field`
- `from datetime import datetime, timezone`
- `from pathlib import Path`
- `from typing import Any, Iterable`

**Top-level constants (9):**

- `LOG` = `logging.getLogger('rhodawk.night_hunter')`
- `REPORT_DIR` = `Path(os.getenv('NIGHT_HUNTER_REPORTS', '/data/night_reports'))`
- `DEFAULT_PLATFORMS` = `os.getenv('NIGHT_HUNTER_PLATFORMS', 'hackerone,bugcrowd,intigriti').lower().split(',')`
- `DEFAULT_HOUR` = `int(os.getenv('NIGHT_HUNTER_HOUR', '23'))`
- `MORNING_HOUR` = `int(os.getenv('NIGHT_HUNTER_MORNING_HOUR', '6'))`
- `P1_FLOOR` = `int(os.getenv('NIGHT_HUNTER_P1_FLOOR', '5000'))`
- `P2_FLOOR` = `int(os.getenv('NIGHT_HUNTER_P2_FLOOR', '1000'))`
- `MAX_TARGETS` = `int(os.getenv('NIGHT_HUNTER_MAX_TARGETS', '3'))`
- `_DETECTORS` = `('nuclei', 'zap-active', 'sqlmap', 'jwt-analyzer', 'cors-analyzer', 'openapi-analyzer', 'prototype-pollution')`

**Classes (3):**

- `class TargetProfile` — line 61
- `class HuntFinding` — line 74
    - `def to_dict(self) -> dict[str, Any]` (L90)
- `class NightCycleReport` — line 95
    - `def to_dict(self) -> dict[str, Any]` (L105)
    - `def summary(self) -> dict[str, Any]` (L118)

**Top-level functions (17):**

- `def _ingest_scope(platforms: Iterable[str]) -> list[TargetProfile]` (L131)
  - _Try every available scope source. Falls back to a static demo list when_
- `def _filter_by_floor(profiles: list[TargetProfile]) -> list[TargetProfile]` (L193)
- `def _score_targets(profiles: list[TargetProfile]) -> list[TargetProfile]` (L197)
- `def _safe_call(label: str, fn, *args, **kwargs) -> Any` (L208)
- `def _recon(target: TargetProfile) -> dict[str, Any]` (L216)
- `def _hunt(target: TargetProfile, recon: dict[str, Any]) -> list[HuntFinding]` (L257)
- `def _run_detector(detector: str, host: str) -> list[dict[str, Any]]` (L289)
  - _Thin dispatcher. Each block tries to import the matching MCP/scanner and_
- `def _validate(findings: list[HuntFinding]) -> list[HuntFinding]` (L342)
- `def _draft_submission(f: HuntFinding) -> str` (L389)
- `def _persist(report: NightCycleReport) -> Path` (L405)
- `def _briefing(report: NightCycleReport) -> str` (L416)
- `def _notify(report: NightCycleReport) -> None` (L432)
- `def run_night_cycle(*, platforms: Iterable[str] | None=None, *, max_targets: int=MAX_TARGETS) -> NightCycleReport` (L449)
  - _Execute one full hunting cycle and return the report._
- `def _finalise(report: NightCycleReport) -> NightCycleReport` (L515)
- `def _seconds_until(hour: int) -> float` (L523)
- `def schedule_loop(start_hour: int=DEFAULT_HOUR) -> None` (L531)
  - _Blocking scheduler. Runs forever; safe to launch in a daemon thread._
- `def start_in_background(start_hour: int | None=None) -> threading.Thread` (L548)
  - _Idempotent — only one scheduler thread is ever started._

### `notifier.py`

- Lines: 109  Bytes: 3779

**Module docstring:**

> Rhodawk AI — Multi-Channel Notification Engine
> ================================================
> Fire-and-forget notifications across Telegram (and extensible to Slack/PagerDuty).
> All dispatches use tenacity retry logic and never block the audit loop.
> 
> MINOR BUG FIX: Telegram/Slack URLs are no longer captured at module load time.
> They are resolved dynamically at dispatch time, so rotating credentials at runtime
> (without a process restart) takes effect immediately.

**Imports (4):**

- `import os`
- `import threading`
- `import requests`
- `from tenacity import retry, stop_after_attempt, wait_exponential`

**Top-level functions (13):**

- `def _get_telegram_creds() -> tuple[str, str]` (L18)
  - _Resolve Telegram credentials at dispatch time, not module load time._
- `def _get_slack_url() -> str` (L23)
  - _Resolve Slack webhook URL at dispatch time, not module load time._
- `def _post_telegram(payload: dict)` (L29)
- `def _post_slack(payload: dict)` (L37)
- `def _dispatch(message: str, level: str='INFO')` (L43)
- `def notify(message: str, level: str='INFO')` (L71)
  - _Non-blocking dispatch. Spawns a daemon thread — never blocks audit loop._
- `def notify_audit_start(repo: str)` (L76)
- `def notify_test_failed(test_path: str)` (L80)
- `def notify_sast_blocked(test_path: str, reason: str)` (L84)
- `def notify_pr_created(test_path: str, pr_url: str)` (L88)
- `def notify_patch_failed(test_path: str)` (L92)
- `def notify_audit_complete(metrics: dict)` (L96)
- `def notify_chain_integrity(valid: bool, summary: str)` (L105)

### `openclaw_gateway.py`

- Lines: 375  Bytes: 14554

**Module docstring:**

> Rhodawk AI — OpenClaw / Telegram gateway (Masterplan §6 EmbodiedOS).
> 
> A small, self-contained HTTP + Telegram bridge that lets the operator talk
> to Rhodawk in natural language from anywhere:
> 
>     Telegram message      ──┐
>     Slack /command        ──┤
>     OpenClaw skill call   ──┴──►  parse intent  ──►  dispatch to:
>                                                       • OSSGuardian.run(repo)
>                                                       • night_hunt_orchestrator
>                                                       • status / pause / resume
>                                                       • approve / reject finding
>                                                       • explain finding
> 
> Public surface:
> 
>     handle_command(text, *, user="operator") -> dict
>         Pure function. Parses ``text`` into an intent and executes it.
>         Returns {"ok": bool, "intent": str, "reply": str, "data": ...}.
> 
>     create_app() -> flask.Flask
>         FastAPI/Flask-compatible app exposing:
>             POST /openclaw/command   {"text": "..."}        → handle_command
>             POST /telegram/webhook   Telegram Update payload → handle_command
>             GET  /openclaw/status                            → liveness JSON
> 
>     start_in_background(host="0.0.0.0", port=8765) -> Thread
>         Convenience: starts the Flask server in a daemon thread.
> 
> The module degrades gracefully when neither Flask nor python-telegram-bot
> is installed: ``handle_command`` always works (no IO), and ``create_app``
> returns ``None`` with a logged warning.

**Imports (8):**

- `from __future__ import annotations`
- `import json`
- `import logging`
- `import os`
- `import re`
- `import threading`
- `from dataclasses import dataclass`
- `from typing import Any, Callable`

**Top-level constants (4):**

- `LOG` = `logging.getLogger('rhodawk.openclaw_gateway')`
- `TELEGRAM_BOT_TOKEN` = `os.getenv('TELEGRAM_BOT_TOKEN', '')`
- `TELEGRAM_CHAT_ID` = `os.getenv('TELEGRAM_CHAT_ID', '')`
- `OPENCLAW_SHARED_SECRET` = `os.getenv('OPENCLAW_SHARED_SECRET', '')`

**Classes (1):**

- `class Intent` — line 54

**Top-level functions (15):**

- `def register(name: str, pattern: str, *, help: str='') -> Callable[[Callable], Callable]` (L64)
- `def _scan_repo(m: re.Match[str]) -> dict[str, Any]` (L78)
- `def _night_now(_: re.Match[str]) -> dict[str, Any]` (L102)
- `def _pause_night(_: re.Match[str]) -> dict[str, Any]` (L121)
- `def _resume_night(_: re.Match[str]) -> dict[str, Any]` (L133)
- `def _status(_: re.Match[str]) -> dict[str, Any]` (L145)
- `def _format_status(info: dict[str, Any]) -> str` (L163)
- `def _approve_finding(m: re.Match[str]) -> dict[str, Any]` (L182)
- `def _reject_finding(m: re.Match[str]) -> dict[str, Any]` (L205)
- `def _explain_finding(m: re.Match[str]) -> dict[str, Any]` (L223)
- `def _help(_: re.Match[str]) -> dict[str, Any]` (L255)
- `def handle_command(text: str, *, user: str='operator') -> dict[str, Any]` (L263)
  - _Match a freeform command to an intent and execute its handler._
- `def telegram_send(text: str, *, chat_id: str | None=None) -> bool` (L285)
- `def create_app()` (L307)
  - _Returns a Flask app or ``None`` if Flask is not available._
- `def start_in_background(host: str='0.0.0.0', port: int=8765) -> threading.Thread | None` (L353)

### `openclaw_schedule.yaml`

- Lines: 30  Bytes: 775

**Top-level keys:** `heartbeat`, `channels`, `intents`

```yaml
# Rhodawk EmbodiedOS — heartbeat schedule (Masterplan §6).
# All cron expressions are UTC unless noted.
heartbeat:
  health_check:        every: 15min
  harvester_run:       cron: "0 */6 * * *"   # every 6 hours
  night_hunt_start:    cron: "0 23 * * *"    # 11 PM daily
  morning_report:      cron: "0 6 * * *"     # 6 AM daily
  lora_export_check:   cron: "0 2 * * 0"     # Sunday 2 AM
  training_digest:     cron: "0 9 * * 1"     # Monday 9 AM

channels:
  telegram:
    enabled: true
    chat_id_env: TELEGRAM_CHAT_ID
    bot_token_env: TELEGRAM_BOT_TOKEN
  discord:
    enabled: false
  slack:
    enabled: false

intents:
  - scan_repo
  - night_run_now
  - pause_night
  - resume_night
  - status
  - approve_finding
  - reject_finding
  - explain_finding
  - help
```

### `oss_guardian.py`

- Lines: 208  Bytes: 8420

**Module docstring:**

> oss_guardian.py — OSS Zero-Day Pipeline (Masterplan §2.5).
> 
> Glues the existing primitives together end-to-end:
> 
>     repo_harvester  →  oss_target_scorer  →  architect.sandbox  →
>     language_runtime  →  hermes_orchestrator  →  disclosure_vault  →
>     embodied_bridge
> 
> The module is designed so each stage can be stubbed for tests.  The
> production entry point is ``OSSGuardian().run(repo_url)``.
> 
> Run as a module:
> 
>     python -m oss_guardian --repo https://github.com/nodejs/node

**Imports (8):**

- `from __future__ import annotations`
- `import argparse`
- `import dataclasses`
- `import logging`
- `import os`
- `from dataclasses import dataclass, field`
- `from pathlib import Path`
- `from typing import Any`

**Top-level constants (1):**

- `LOG` = `logging.getLogger('oss_guardian')`

**Classes (2):**

- `class OSSCampaign` — line 32
    - `def to_json(self) -> dict[str, Any]` (L40)
- `class OSSGuardian` — line 75
  - _Autonomous open-source vulnerability research runner._
    - `def __init__(self, *, attack_only: bool=False, *, fix_only: bool=False)` (L78)
    - `def run(self, repo_url: str) -> OSSCampaign` (L83)
    - `def _safe_run_tests(self, runtime) -> dict[str, Any]` (L117)
    - `def _fix_mode(self, repo_path: str, runtime, test_result: dict) -> str | None` (L127)
    - `def _extract_findings(self, session) -> list[dict]` (L140)
    - `def _route_findings(self, findings: list[dict], camp: OSSCampaign) -> None` (L151)

**Top-level functions (5):**

- `def _open_sandbox(repo_url: str)` (L45)
- `def _detect_runtime(repo_path: str)` (L50)
- `def _hermes_attack(repo_path: str, language: str)` (L55)
- `def _route_disclosure(finding: dict) -> dict` (L62)
  - _Route a finding to the right submission lane._
- `def main(argv: list[str] | None=None) -> int` (L189)

### `oss_target_scorer.py`

- Lines: 111  Bytes: 3538

**Module docstring:**

> oss_target_scorer.py — prioritise open-source repositories for the
> OSS-Guardian pipeline (Masterplan §2.2).
> 
> The scorer takes the GitHub repo metadata that ``repo_harvester.py`` already
> fetches and produces a single deterministic float in ``[0.0, 1.0+]``.
> Higher scores rank ahead in the OSS-Guardian queue.
> 
> Inputs are a plain dict so the scorer stays unit-testable without a network.

**Imports (5):**

- `from __future__ import annotations`
- `import math`
- `import time`
- `from dataclasses import dataclass`
- `from typing import Any`

**Classes (1):**

- `class TargetScore` — line 43

**Top-level functions (4):**

- `def _safe_log10(x: float) -> float` (L50)
- `def _days_since(iso_str: str | None) -> float` (L54)
- `def score_repo(repo: dict[str, Any], *, cve_history_count: int=0, *, last_security_advisory_iso: str | None=None) -> TargetScore` (L65)
  - _Score one repository for vulnerability-research priority._
- `def rank(repos: list[dict[str, Any]], *, top_k: int=25) -> list[TargetScore]` (L107)
  - _Return the top-K repos ordered by descending score._

### `paper2code_engine.py`

- Lines: 399  Bytes: 14916

**Module docstring:**

> paper2code_engine.py
> ────────────────────
> Rhodawk-native re-implementation of the
> ``PrathamLearnsToCode/paper2code`` skill, vendored under
> ``vendor/paper2code/``.
> 
> The upstream skill converts an arXiv paper into a citation-anchored,
> ambiguity-audited Python implementation.  Inside Rhodawk we want the
> same capability available to the orchestrator so the autonomous loop
> can:
> 
>   * Convert a freshly-discovered research paper (CVE write-up, novel
>     fuzzing technique, new symbolic-execution heuristic, …) into a
>     runnable scaffold under ``training_store.py``'s data flywheel.
>   * Feed the generated ``REPRODUCTION_NOTES.md`` ambiguity audit into
>     ``knowledge_rag.py`` so the embedding memory tracks *what is and
>     isn't specified* in a paper, not just the paper's text.
>   * Drive the ``hermes_orchestrator`` Night-Hunt mode: when a new
>     primitive is discovered in the wild, fetch the paper, scaffold a
>     reproduction, hand the scaffold to OpenClaude for completion,
>     test-run it through ``language_runtime.py``.
> 
> The implementation is faithful to the upstream skill's six-stage
> pipeline (``vendor/paper2code/SKILL.md`` + ``pipeline/01..05``) but
> lives in pure Python so the orchestrator can call it without spawning
> a separate skill-runner subprocess.
> 
> LLM access is intentionally pluggable — by default we route through
> the existing OpenClaude gRPC bridge (``openclaude_grpc``) used
> elsewhere in Rhodawk, but tests / dry runs can pass any callable with
> the signature ``(prompt: str, *, system: str = "") -> str``.

**Imports (10):**

- `from __future__ import annotations`
- `import json`
- `import logging`
- `import os`
- `import re`
- `import urllib.error`
- `import urllib.request`
- `from dataclasses import dataclass, field`
- `from pathlib import Path`
- `from typing import Callable, Dict, List, Optional`

**Top-level constants (5):**

- `_HERE` = `Path(__file__).resolve().parent`
- `VENDOR_DIR` = `Path(os.environ.get('RHODAWK_PAPER2CODE_DIR', str(_HERE / 'vendor' / 'paper2code')))`
- `DEFAULT_OUTPUT_ROOT` = `Path(os.environ.get('RHODAWK_PAPER2CODE_OUT', '/data/paper2code'))`
- `ARXIV_ID_RE` = `re.compile('(\\d{4}\\.\\d{4,5}(?:v\\d+)?)')`
- `SCAFFOLD_FILES` = `{'README.md': 'readme_template.md', 'REPRODUCTION_NOTES.md': 'reproduction_notes_template.md', 'configs/base.yaml': '...`

**Classes (3):**

- `class PaperMetadata` — line 64
    - `def slug(self) -> str` (L72)
- `class AmbiguityFinding` — line 80
    - `def to_dict(self) -> Dict[str, str]` (L86)
- `class Paper2CodeResult` — line 91
    - `def to_dict(self) -> Dict[str, object]` (L98)

**Top-level functions (10):**

- `def parse_arxiv_id(value: str) -> str` (L117)
  - _Accepts a bare id, an abs/pdf URL, or a versioned id._
- `def fetch_metadata(arxiv_id: str, *, timeout: float=20.0) -> PaperMetadata` (L125)
  - _Pull title / abstract / authors via the arXiv Atom API._
- `def identify_contribution(meta: PaperMetadata, *, llm: Optional[LLMFn]=None) -> str` (L157)
- `def audit_ambiguity(meta: PaperMetadata, *, llm: Optional[LLMFn]=None, *, dimensions: Optional[List[str]]=None) -> List[AmbiguityFinding]` (L192)
- `def _load_scaffold(template_name: str) -> str` (L255)
- `def _render(template: str, *, meta: PaperMetadata, *, contribution: str) -> str` (L262)
  - _Lightweight token substitution.  The upstream scaffolds use_
- `def generate_scaffold(meta: PaperMetadata, contribution: str, ambiguity: List[AmbiguityFinding], output_root: Path=DEFAULT_OUTPUT_ROOT) -> Paper2CodeResult` (L280)
- `def run(paper_input: str, *, llm: Optional[LLMFn]=None, *, output_root: Path=DEFAULT_OUTPUT_ROOT) -> Paper2CodeResult` (L316)
  - _Full pipeline: arxiv id/url → scaffolded implementation directory._
- `def _default_llm() -> Optional[LLMFn]` (L346)
  - _Return a callable wrapping the existing OpenClaude gRPC bridge,_
- `def stats() -> Dict[str, object]` (L378)

### `public_leaderboard.py`

- Lines: 190  Bytes: 6430

**Module docstring:**

> Rhodawk AI — Public Leaderboard & Open Source Health Dashboard
> ==============================================================
> Gradio Space interface showing live stats on repos touched, PRs submitted,
> patterns learned, and zero-days discovered.
> 
> This is the antagonist version's marketing engine — real numbers, real PRs,
> publicly verifiable. No fake metrics.
> 
> Runs as a standalone Gradio Space OR embedded in the main app.

**Imports (4):**

- `import json`
- `import os`
- `import time`
- `import gradio as gr`

**Top-level constants (3):**

- `STATS_PATH` = `'/data/public_stats.json'`
- `RED_TEAM_DIR` = `'/data/red_team'`
- `AUDIT_LOG_PATH` = `'/data/audit_trail.jsonl'`

**Top-level functions (5):**

- `def _load_stats() -> dict` (L25)
- `def _compute_live_stats() -> dict` (L35)
- `def get_leaderboard_markdown() -> str` (L93)
- `def get_top_repos_display() -> str` (L131)
- `def build_leaderboard_interface() -> gr.Blocks` (L167)

### `red_team_fuzzer.py`

- Lines: 1560  Bytes: 62456

**Module docstring:**

> Rhodawk AI — Autonomous Red Team Fuzzing Engine (CEGIS)
> ========================================================
> The Zero-Day Discovery Machine. No competitor has this.
> 
> What this does:
>   When the Blue Team audit loop encounters a "Green" repository (all tests passing),
>   this engine takes over. It autonomously ATTACKS the codebase — discovering
>   mathematical invariants, synthesizing Property-Based Tests, and fuzzing them
>   to exhaustion to find the minimal crashing counter-example (the zero-day payload).
>   The crash is then handed to the Blue Team verification_loop.py for autonomous patching.
> 
> Architecture — CEGIS (Counter-Example Guided Inductive Synthesis):
>   ┌─────────────────────────────────────────────────────────────────┐
>   │                    RED TEAM ENGINE (This File)                  │
>   │                                                                 │
>   │  1. MCP Universal Analyzer                                      │
>   │     └── Parse AST → score complexity → rank attack targets      │
>   │                                                                 │
>   │  2. Red Team LLM (The Attacker)                                 │
>   │     └── Adversarial prompt → generate Hypothesis PBT           │
>   │         targeting: overflows, race conditions, invariant breaks  │
>   │                                                                 │
>   │  3. Deterministic Fuzzing Loop                                  │
>   │     └── Execute PBT via subprocess → aggressive randomization   │
>   │         → extract minimal falsifying counter-example            │
>   │                                                                 │
>   │  4. CEGIS Re-attack (if no crash found)                        │
>   │     └── Inject "survived inputs" back to LLM → demand harder   │
>   │         invariant → repeat up to MAX_CEGIS_ROUNDS              │
>   │                                                                 │
>   │  5. Handoff to Blue Team                                        │
>   │     └── Package crash payload → inject into verification_loop   │
>   │         as a synthetic failing pytest → Blue Team patches it    │
>   └─────────────────────────────────────────────────────────────────┘
> 
> Invariant classes targeted:
>   - Mathematical: commutativity, associativity, idempotency, monotonicity
>   - Boundary: integer overflow (sys.maxsize, 2^63-1, -1, 0), empty sequences
>   - Roundtrip: encode→decode, serialize→deserialize, compress→decompress
>   - Concurrency: race conditions via threading + shared state mutation
>   - Type coercion: implicit conversions that cause precision loss or exceptions
>   - State machine: functions that should be pure but carry hidden mutable state

**Imports (18):**

- `import ast`
- `import hashlib`
- `import json`
- `import os`
- `import re`
- `import shutil`
- `import signal`
- `import subprocess`
- `import sys`
- `import tempfile`
- `import textwrap`
- `import threading`
- `import time`
- `from dataclasses import dataclass, field`
- `from pathlib import Path`
- `from typing import Callable, Optional, TYPE_CHECKING`
- `import requests`
- `from tenacity import retry, stop_after_attempt, wait_exponential`

**Top-level constants (12):**

- `OPENROUTER_API_KEY` = `os.getenv('OPENROUTER_API_KEY')`
- `RED_TEAM_MODEL` = `os.getenv('RHODAWK_RED_TEAM_MODEL', 'openrouter/qwen/qwen-2.5-coder-32b-instruct:free')`
- `RED_TEAM_MODEL_STRONG` = `os.getenv('RHODAWK_RED_TEAM_MODEL_STRONG', 'openrouter/anthropic/claude-3-5-sonnet')`
- `PERSISTENT_DIR` = `'/data'`
- `RED_TEAM_DIR` = `f'{PERSISTENT_DIR}/red_team'`
- `FUZZ_VENV_DIR` = `f'{PERSISTENT_DIR}/fuzz_venv'`
- `MAX_CEGIS_ROUNDS` = `int(os.getenv('RHODAWK_CEGIS_ROUNDS', '4'))`
- `FUZZ_MAX_EXAMPLES` = `int(os.getenv('RHODAWK_FUZZ_EXAMPLES', '50000'))`
- `FUZZ_TIMEOUT_SECONDS` = `int(os.getenv('RHODAWK_FUZZ_TIMEOUT', '180'))`
- `MAX_TARGETS_PER_RUN` = `int(os.getenv('RHODAWK_MAX_TARGETS', '8'))`
- `MIN_COMPLEXITY_SCORE` = `float(os.getenv('RHODAWK_MIN_COMPLEXITY', '2.0'))`
- `_RED_TEAM_SYSTEM_PROMPT` = `'You are an elite adversarial security researcher specializing in automated vulnerability discovery through Property-...`

**Classes (5):**

- `class ASTFunctionProfile` — line 188
  - _Rich profile of a function extracted from its AST node._
- `class FuzzTarget` — line 209
  - _A ranked attack target selected by the MCP Universal Analyzer._
- `class GeneratedPBT` — line 218
  - _A Property-Based Test synthesized by the Red Team LLM._
- `class CrashPayload` — line 229
  - _The zero-day package handed to the Blue Team._
- `class RedTeamResult` — line 247
  - _Final result of a full CEGIS red-team run on a repository._

**Top-level functions (30):**

- `def rte_log(message: str, level: str='INFO') -> None` (L99)
- `def get_red_team_logs(n: int=100) -> str` (L121)
- `def _get_runner_bin(env_config: 'EnvConfig') -> str` (L132)
  - _Resolve the pytest-compatible test runner binary from an EnvConfig._
- `def _get_python_bin(env_config: 'EnvConfig') -> str` (L149)
  - _Resolve the Python interpreter binary from an EnvConfig._
- `def _get_pip_bin(env_config: 'EnvConfig') -> str` (L166)
  - _Resolve the pip binary from an EnvConfig._
- `def _compute_cyclomatic_complexity(source: str) -> float` (L264)
  - _Compute cyclomatic complexity using radon if available,_
- `def _extract_arg_types(func_node: ast.FunctionDef) -> dict[str, str]` (L293)
  - _Extract argument names and their type annotations as strings._
- `def _extract_return_type(func_node: ast.FunctionDef) -> str` (L308)
- `def _has_numeric_operations(func_node: ast.FunctionDef) -> bool` (L317)
- `def _has_recursion(func_node: ast.FunctionDef) -> bool` (L329)
- `def _has_state_mutation(func_node: ast.FunctionDef) -> bool` (L340)
- `def _extract_calls(func_node: ast.FunctionDef) -> list[str]` (L357)
- `def _build_ast_summary(profile: 'ASTFunctionProfile') -> str` (L368)
  - _Compact JSON representation of the function for the LLM._
- `def _score_attack_priority(p: ASTFunctionProfile) -> tuple[float, list[str], str]` (L389)
  - _Compute composite attack priority and determine which invariant_
- `def analyze_repository_ast(repo_dir: str) -> list[FuzzTarget]` (L458)
  - _Walk all Python source files in the repo, extract function-level AST_
- `def _build_red_team_prompt(target: FuzzTarget, cegis_round: int, survived_inputs: Optional[list[str]]=None) -> str` (L626)
  - _Build the adversarial LLM prompt. Each CEGIS round gets harder:_
- `def _call_red_team_llm(system: str, user: str, model: str) -> str` (L680)
  - _Call OpenRouter API — returns raw text response (the test code)._
- `def _clean_llm_test_output(raw: str) -> str` (L711)
  - _Strip markdown fences and extract raw Python from LLM response._
- `def synthesize_pbt(target: FuzzTarget, cegis_round: int, survived_inputs: Optional[list[str]]=None, use_strong_model: bool=False) -> Optional[GeneratedPBT]` (L734)
  - _Dispatch the Red Team LLM to synthesize a Property-Based Test._
- `def _install_hypothesis_if_needed(env_config: 'EnvConfig', repo_dir: str) -> bool` (L813)
  - _Ensure hypothesis is installed in the target environment._
- `def _write_pbt_to_file(pbt: GeneratedPBT, target: FuzzTarget, repo_dir: str) -> str` (L842)
  - _Write the generated PBT to the red_team/ directory._
- `def _extract_falsifying_example(output: str) -> str` (L877)
  - _Parse hypothesis output to extract the minimal falsifying example._
- `def _extract_crash_type(output: str) -> str` (L903)
  - _Classify the type of crash from hypothesis output._
- `def _extract_survived_inputs(output: str) -> list[str]` (L926)
  - _If the fuzz run succeeded (no crash), try to extract some of the_
- `def run_fuzzing_loop(pbt: GeneratedPBT, target: FuzzTarget, repo_dir: str, env_config: 'EnvConfig') -> tuple[bool, str, str]` (L939)
  - _Execute the generated PBT via subprocess with hypothesis aggressive settings._
- `def _build_synthetic_failing_test(crash: CrashPayload, repo_dir: str) -> str` (L1046)
  - _Rewrite the PBT crash as a DETERMINISTIC pytest that always reproduces_
- `def package_crash_for_blue_team(target: FuzzTarget, pbt: GeneratedPBT, crash_output: str, falsifying_example: str, cegis_rounds: int, repo_dir: str) -> CrashPayload` (L1138)
  - _Package all crash data into a CrashPayload and write the synthetic_
- `def handoff_to_blue_team(crash: CrashPayload, repo_dir: str, env_config: 'EnvConfig', mcp_config_path: str, job_id: str, branch_name: str, blue_team_fn: Callable) -> dict` (L1186)
  - _Execute the CEGIS Handoff — pass the synthetic failing test to the_
- `def run_red_team_cegis(repo_dir: str, env_config: 'EnvConfig', mcp_config_path: str, blue_team_fn: Callable, tenant_id: str='default', log_audit_fn: Optional[Callable]=None, notify_fn: Optional[Callable]=None) -> RedTeamResult` (L1317)
  - _Full CEGIS Red Team orchestration loop._
- `def get_red_team_stats() -> dict` (L1535)
  - _Return summary statistics for the dashboard._

### `repo_harvester.py`

- Lines: 333  Bytes: 10819

**Module docstring:**

> Rhodawk AI — Autonomous Repository Harvester
> ============================================
> Autonomous target selection engine for the Antagonist operating mode.
> 
> Instead of waiting for a user to supply a repo, the harvester continuously
> scans public GitHub repositories for:
>   - Failing CI checks (check_runs with conclusion=failure)
>   - Active maintenance (last commit < 30 days)
>   - Good test coverage (test files exist)
>   - High star count (community trust signal)
> 
> Outputs a ranked feed of (repo, failing_test_hint) tuples for the
> enterprise_audit_loop to consume continuously.
> 
> Enable continuous harvest mode with: RHODAWK_HARVESTER_ENABLED=true
> Configure poll interval:             RHODAWK_HARVESTER_POLL_SECONDS=21600 (6h)

**Imports (8):**

- `import json`
- `import os`
- `import threading`
- `import time`
- `from dataclasses import dataclass, field, asdict`
- `from datetime import datetime, timedelta, timezone`
- `from typing import Optional`
- `import requests`

**Top-level constants (8):**

- `HARVESTER_PUSHED_WINDOW_DAYS` = `int(os.getenv('RHODAWK_HARVESTER_PUSHED_WINDOW_DAYS', '30'))`
- `GITHUB_TOKEN` = `os.getenv('GITHUB_TOKEN', '')`
- `HARVESTER_ENABLED` = `os.getenv('RHODAWK_HARVESTER_ENABLED', 'false').lower() == 'true'`
- `HARVESTER_POLL_S` = `int(os.getenv('RHODAWK_HARVESTER_POLL_SECONDS', '21600'))`
- `HARVESTER_MIN_STARS` = `int(os.getenv('RHODAWK_HARVESTER_MIN_STARS', '100'))`
- `HARVESTER_MAX_REPOS` = `int(os.getenv('RHODAWK_HARVESTER_MAX_REPOS', '20'))`
- `HARVESTER_PERSIST` = `os.getenv('RHODAWK_HARVESTER_STATE', '/data/harvester_feed.json')`
- `_LANGUAGES` = `['python', 'javascript', 'typescript', 'go', 'java', 'ruby', 'rust']`

**Classes (1):**

- `class HarvestTarget` — line 49

**Top-level functions (13):**

- `def _gh_headers() -> dict` (L62)
- `def _search_repos_with_failing_ci(language: str, page: int=1) -> list[dict]` (L72)
  - _Search GitHub for repos in a given language with recent activity._
- `def _get_failing_check_runs(repo_full_name: str) -> list[str]` (L100)
  - _Return names of failing CI check runs for the default branch._
- `def _has_test_files(repo_full_name: str, language: str) -> bool` (L133)
  - _Quick heuristic: search for test files via GitHub search API._
- `def _last_commit_days(repo: dict) -> int` (L159)
- `def _score_target(stars: int, last_commit_days: int, failing_checks: int) -> float` (L170)
  - _Composite score — higher is better candidate for Rhodawk to fix._
- `def run_harvest_cycle() -> list[HarvestTarget]` (L184)
  - _Perform one harvest pass across all tracked languages._
- `def persist_feed(targets: list[HarvestTarget]) -> None` (L234)
- `def load_feed() -> list[dict]` (L240)
- `def get_next_target() -> Optional[dict]` (L250)
  - _Pop the highest-priority unprocessed target from the feed._
- `def _harvest_loop(dispatch_fn) -> None` (L266)
  - _Background thread: runs harvest cycles and dispatches audits._
- `def start_harvester(dispatch_fn=None) -> Optional[threading.Thread]` (L295)
  - _Start the harvester in a background daemon thread._
- `def get_feed_summary() -> str` (L317)
  - _Human-readable summary of current harvest feed for dashboard display._

### `requirements.txt`

- Lines: 56  Bytes: 1998

```
requests
pytest
uv>=0.7.0
gitpython==3.1.46
gradio>=5.49.0,<6
jinja2==3.1.6

# ─── Code-generation layer ───────────────────────────────────────────────
# Aider-chat has been removed and replaced by the vendored OpenClaude
# headless gRPC daemon (see vendor/openclaude/ + openclaude_grpc/).
# The Dockerfile installs grpcio + grpcio-tools at build time so that
# protobuf stub generation runs inside the build, not in this lock file.

# ─── Static analysis / SAST ──────────────────────────────────────────────
ruff
tenacity
bandit[toml]
pip-audit
radon
hypothesis[cli]>=6.100.0
semgrep>=1.45.0

# ─── ML / embeddings / vector store ──────────────────────────────────────
sentence-transformers>=2.7.0
sqlite-vec>=0.1.1
pygithub>=2.3.0
PyJWT>=2.8.0
datasets>=2.19.0
numpy>=1.26.0
psycopg2-binary>=2.9.9
rapidfuzz>=3.0.0
z3-solver>=4.12.0
qdrant-client>=1.9.0
transformers>=4.40.0
torch>=2.2.0

# atheris removed: requires Clang + libFuzzer at compile time which is
# unavailable on HuggingFace Space Docker images. Fuzzing falls back to
# Hypothesis automatically.
angr>=9.2.0
networkx>=3.0
defusedxml>=0.7.1

# ─── Mythos-level upgrade (see mythos/MYTHOS_PLAN.md) ────────────────────
fastapi>=0.110.0
uvicorn[standard]>=0.27.0
pydantic>=2.6.0

# ─── ARCHITECT masterplan dependencies (see ARCHITECT_MASTERPLAN.md) ─────
dnspython>=2.6.0

# ─── gRPC bridge to the OpenClaude daemon ────────────────────────────────
# (Pinned again here as a safety net for editable installs / `pip install -r`
#  in environments that bypass the Dockerfile.)
grpcio>=1.66.0,<2.0.0
protobuf>=5.0.0,<6.0.0

```

### `sast_gate.py`

- Lines: 204  Bytes: 8273

**Module docstring:**

> Rhodawk AI — Pre-PR SAST + Secret Detection Gate
> ==================================================
> Every AI-generated diff passes through this gate BEFORE a PR is opened.
> The gate runs:
>   1. Bandit — Python SAST for known vulnerability patterns (SQLi, exec, pickle, etc.)
>   2. Secret pattern scanning — detects hardcoded credentials, API keys, tokens
>   3. Dangerous import detection — flags os.system, eval, __import__, pickle.loads
> 
> This is the control plane that stops a hallucinating LLM from shipping a vulnerability.

**Imports (6):**

- `import os`
- `import re`
- `import subprocess`
- `import tempfile`
- `from dataclasses import dataclass, field`
- `from typing import Optional`

**Top-level constants (3):**

- `_SECRET_PATTERNS` = `[(re.compile('(?i)(api[_\\-]?key|apikey|secret[_\\-]?key|access[_\\-]?token|auth[_\\-]?token)\\s*=\\s*["\\\'][a-z0-9\...`
- `_DANGEROUS_PATTERNS` = `[(re.compile('\\bos\\.system\\s*\\('), 'os.system() call — use subprocess with shell=False'), (re.compile('\\beval\\s...`
- `_INJECTION_PATTERNS` = `[(re.compile('f["\\\'].*SELECT.*\\{.*\\}.*FROM', re.IGNORECASE), 'SQL injection via f-string'), (re.compile('["\\\']....`

**Classes (2):**

- `class SastFinding` — line 54
- `class SastReport` — line 63
    - `def summary(self) -> str` (L70)

**Top-level functions (4):**

- `def _scan_diff_for_secrets(diff_text: str) -> list[SastFinding]` (L76)
- `def _run_bandit_on_file(file_path: str) -> str` (L114)
- `def _run_semgrep_on_file(file_path: str) -> str` (L132)
- `def run_sast_gate(diff_text: str, changed_files: list[str], repo_dir: str) -> SastReport` (L150)
  - _Run the full SAST gate on an AI-generated diff._

### `semantic_extractor.py`

- Lines: 212  Bytes: 6993

**Module docstring:**

> Rhodawk AI — Semantic Logic Extractor (Ethical Research Mode)
> =============================================================
> STATIC ANALYSIS ONLY — no code is executed by this module.
> 
> Maps the application's trust state machine across files to identify
> "Assumption Gaps" — points where developer intent diverges from actual
> code behaviour. All output is JSON for human review.
> 
> Orchestrated by Nous Hermes 3 via OpenRouter.

**Imports (9):**

- `from __future__ import annotations`
- `import glob`
- `import json`
- `import os`
- `import re`
- `import time`
- `from pathlib import Path`
- `from typing import Optional`
- `import requests`

**Top-level constants (4):**

- `OPENROUTER_API_KEY` = `os.getenv('OPENROUTER_API_KEY', '')`
- `HERMES_MODEL` = `os.getenv('RHODAWK_RESEARCH_MODEL', 'nousresearch/hermes-3-llama-3.1-405b:free')`
- `_PRIORITY_KEYWORDS` = `['auth', 'token', 'session', 'permission', 'privilege', 'trust', 'validate', 'sanitize', 'parse', 'decode', 'deserial...`
- `_SKIP_DIRS` = `{'.git', 'vendor', 'node_modules', '__pycache__', '.tox', 'dist', 'build'}`

**Top-level functions (6):**

- `def _hermes(system: str, user: str, max_tokens: int=4096) -> str` (L41)
  - _Call Nous Hermes 3 via OpenRouter._
- `def _find_relevant_files(repo_dir: str, language: str) -> list[str]` (L66)
- `def _read_file_head(repo_dir: str, rel_path: str, max_lines: int=200) -> str` (L93)
- `def _extract_json(text: str) -> dict` (L103)
- `def extract_trust_boundaries(repo_dir: str, file_paths: list[str]) -> dict` (L113)
  - _Static analysis pass: asks Hermes to map trust states and find assumption gaps._
- `def run_semantic_extraction(repo_dir: str, language: str='python') -> dict` (L182)
  - _Main entry point for the semantic analysis pipeline._

### `supply_chain.py`

- Lines: 265  Bytes: 10205

**Module docstring:**

> Rhodawk AI — Supply Chain Security Gate
> ========================================
> Every AI-generated diff that touches requirements.txt or any import statement
> passes through this gate before a PR is opened.
> 
> Capabilities:
>   1. pip-audit — CVE scanning against OSV/PyPA advisory database
>   2. Typosquatting detection — 50+ known typosquatting patterns vs PyPI top packages
>   3. New dependency analysis — flags packages added by the AI that weren't in original
>   4. Package metadata validation — checks for packages with no public source repo (red flag)
> 
> This catches supply chain attacks where an LLM hallucinates a plausible-sounding
> package name that happens to be a malicious clone.

**Imports (6):**

- `import re`
- `import requests`
- `import subprocess`
- `from dataclasses import dataclass, field`
- `from datetime import datetime, timezone`
- `from typing import Optional`

**Top-level constants (2):**

- `_KNOWN_PACKAGES` = `{'requests', 'numpy', 'pandas', 'flask', 'django', 'fastapi', 'sqlalchemy', 'boto3', 'pytest', 'setuptools', 'pip', '...`
- `_TYPO_THRESHOLD` = `2`

**Classes (1):**

- `class SupplyChainReport` — line 178
    - `def summary(self) -> str` (L187)

**Top-level functions (6):**

- `def _extract_new_packages(diff_text: str, original_requirements: str='') -> list[str]` (L63)
  - _Extract package names added by the AI diff to requirements.txt_
- `def _check_typosquatting(package_name: str) -> Optional[str]` (L81)
  - _Check if a package name looks like a typosquat of a known package._
- `def _run_pip_audit(packages: list[str]) -> list[dict]` (L96)
  - _Run pip-audit against a list of package names to check for CVEs._
- `def _check_import_additions(diff_text: str) -> list[str]` (L132)
  - _Detect new import statements added by the AI._
- `def _check_package_metadata(package_name: str) -> Optional[str]` (L146)
- `def run_supply_chain_gate(diff_text: str, repo_dir: str='') -> SupplyChainReport` (L193)
  - _Run the full supply chain gate on an AI-generated diff._

### `swebench_harness.py`

- Lines: 293  Bytes: 10645

**Module docstring:**

> Rhodawk AI — SWE-bench Verified Evaluation Harness
> ===================================================
> Runs Rhodawk-compatible evaluations against SWE-bench Verified and writes
> machine-readable plus investor-ready reports.
> 
> BUG-009 / GAP-F FIX:
>   The previous implementation called an arbitrary external command via
>   RHODAWK_SWEBENCH_COMMAND, which bypassed the Rhodawk healing loop entirely.
>   pass@1 metrics produced that way were invalid.
> 
>   This version routes each SWE-bench instance through Rhodawk's own
>   process_failing_test() so the same SAST gate, adversarial review, supply
>   chain scan, and verification loop that runs on real repos is used for
>   benchmark evaluation. Results are now legitimately comparable to external
>   SWE-bench leaderboards.
> 
>   Usage:
>     - Call run_swebench_eval(process_fn=process_failing_test, ...) from app.py
>     - Or run standalone (python swebench_harness.py) with:
>         RHODAWK_SWEBENCH_COMMAND=/path/to/runner  (legacy external mode)
> 
>   Environment variables:
>     RHODAWK_SWEBENCH_COMMAND   — (optional) path to external evaluator binary.
>                                   If not set, Rhodawk's own loop is used.
>     RHODAWK_SWEBENCH_TIMEOUT   — per-instance timeout in seconds (default 1800)
>     RHODAWK_SWEBENCH_SPLIT     — dataset split to evaluate (default "test")
>     RHODAWK_SWEBENCH_MAX       — max instances to evaluate (default 100)

**Imports (8):**

- `import argparse`
- `import json`
- `import os`
- `import subprocess`
- `import tempfile`
- `import time`
- `from dataclasses import dataclass, asdict, field`
- `from typing import Any, Callable, Optional`

**Top-level constants (3):**

- `SWEBENCH_DATASET` = `'princeton-nlp/SWE-bench_Verified'`
- `RESULTS_PATH` = `'/data/swebench_results.json'`
- `REPORT_PATH` = `'/data/swebench_report.md'`

**Classes (1):**

- `class SwebenchOutcome` — line 47

**Top-level functions (6):**

- `def _run_via_rhodawk(instance: dict[str, Any], process_fn: Callable, env_config: Any, mcp_config_path: str, repo_dir: str) -> SwebenchOutcome` (L57)
  - _Route a SWE-bench instance through Rhodawk's own healing loop._
- `def _run_via_external_command(instance: dict[str, Any]) -> SwebenchOutcome` (L135)
  - _Legacy mode: delegate to an external evaluator binary._
- `def evaluate_single_instance(instance: dict[str, Any], process_fn: Optional[Callable]=None, env_config: Any=None, mcp_config_path: str='', repo_dir: str='/data/repo') -> SwebenchOutcome` (L169)
  - _Evaluate one SWE-bench instance._
- `def run_swebench_eval(max_instances: int=100, split: str='test', process_fn: Optional[Callable]=None, env_config: Any=None, mcp_config_path: str='', repo_dir: str='/data/repo') -> dict` (L204)
  - _Run SWE-bench evaluation._
- `def write_reports(result: dict) -> None` (L248)
- `def main() -> None` (L281)

### `symbolic_engine.py`

- Lines: 350  Bytes: 12660

**Module docstring:**

> Rhodawk AI — Symbolic Execution Engine
> ========================================
> Uses angr (Python binary analysis framework) to perform symbolic execution
> on compiled binaries, and AST-based path analysis for interpreted languages.
> 
> For Python/JS repos where angr isn't applicable, performs:
>   - Control flow graph analysis
>   - Constraint collection on input-touching branches
>   - Path condition enumeration to find unreachable/unchecked branches
> 
> Findings fed back to Hermes for exploit_primitives reasoning.

**Imports (8):**

- `from __future__ import annotations`
- `import ast`
- `import os`
- `import json`
- `import tempfile`
- `import subprocess`
- `from dataclasses import dataclass, field`
- `from typing import Optional`

**Classes (2):**

- `class SymbolicPath` — line 27
- `class SymbolicResult` — line 40

**Top-level functions (6):**

- `def _try_import_angr()` (L50)
- `def _find_binary(repo_dir: str) -> Optional[str]` (L58)
  - _Find a compiled binary in the repo._
- `def _angr_analysis(binary_path: str, target_function: str) -> SymbolicResult` (L76)
  - _Run angr symbolic execution on a compiled binary._
- `def _ast_analysis(repo_dir: str, target_function: str) -> SymbolicResult` (L143)
  - _AST-based symbolic path analysis for Python code._
- `def _semgrep_symbolic(repo_dir: str) -> dict` (L290)
  - _Run semgrep with security-focused rules for additional coverage._
- `def run_symbolic_analysis(repo_dir: str, target_function: str=None) -> dict` (L310)
  - _Main entry point. Chooses the best available analysis method._

### `taint_analyzer.py`

- Lines: 304  Bytes: 11544

**Module docstring:**

> Rhodawk AI — Taint Analysis Engine
> =====================================
> Tracks untrusted input as it flows through source code to dangerous sinks.
> Language-agnostic: Python (AST), JS/TS (regex+AST heuristics), Go (grep patterns).
> 
> Also exposes map_attack_surface() used by Hermes recon phase.

**Imports (9):**

- `from __future__ import annotations`
- `import ast`
- `import glob`
- `import json`
- `import os`
- `import re`
- `import subprocess`
- `from dataclasses import dataclass, field`
- `from typing import Optional`

**Top-level constants (4):**

- `_PYTHON_SOURCES` = `{'input', 'sys.argv', 'os.environ.get', 'os.getenv', 'request.args.get', 'request.form.get', 'request.json', 'request...`
- `_PYTHON_SINKS` = `{'eval': 'CWE-95', 'exec': 'CWE-95', 'compile': 'CWE-95', 'os.system': 'CWE-78', 'os.popen': 'CWE-78', 'subprocess.ca...`
- `_JS_SINKS` = `{'eval\\s*\\(': 'CWE-95', 'new\\s+Function\\s*\\(': 'CWE-95', 'child_process\\.exec\\s*\\(': 'CWE-78', 'execSync\\s*\...`
- `_SECURITY_FILE_PATTERNS` = `['auth', 'login', 'password', 'token', 'session', 'crypto', 'cipher', 'ssl', 'tls', 'secret', 'key', 'permission', 'a...`

**Classes (2):**

- `class TaintFlow` — line 23
- `class AttackSurface` — line 35

**Top-level functions (3):**

- `def map_attack_surface(repo_dir: str) -> dict` (L108)
  - _Comprehensive attack surface mapping — used by Hermes recon phase._
- `def run_taint_analysis(repo_dir: str, focus_files: list[str]=None) -> dict` (L214)
  - _Full taint analysis: find flows from sources to sinks._
- `def _node_to_str(node) -> str` (L296)

### `training_store.py`

- Lines: 389  Bytes: 15660

**Module docstring:**

> Rhodawk AI — Training Data Pipeline
> =====================================
> Every fix attempt is recorded in SQLite. This is the data flywheel.
> 
> Schema captures the complete chain:
>   failure → model → prompt → diff → SAST → adversarial verdict → test result → human outcome
> 
> After N examples, this becomes a proprietary fine-tuning dataset that no
> competitor can replicate — because it's trained on YOUR codebase's failure patterns.
> 
> Export API produces HuggingFace-compatible JSONL for direct model fine-tuning.

**Imports (7):**

- `import hashlib`
- `import json`
- `import os`
- `import sqlite3`
- `import time`
- `from contextlib import contextmanager`
- `from typing import Optional`

**Top-level constants (3):**

- `DB_PATH` = `'/data/training_store.db'`
- `DB_BACKEND` = `os.getenv('DB_BACKEND', 'sqlite').lower()`
- `DATABASE_URL` = `os.getenv('DATABASE_URL', '')`

**Top-level functions (11):**

- `def _get_conn()` (L29)
- `def initialize_store()` (L112)
- `def initialize_postgres_store()` (L165)
- `def record_attempt(tenant_id: str, repo: str, test_path: str, failure_output: str, model_version: str, prompt_hash: str, attempt_number: int=1, diff_produced: str='', sast_passed: Optional[bool]=None, sast_findings_count: int=0, adversarial_verdict: Optional[str]=None, adversarial_issues: Optional[list]=None, adversarial_summary: str='', adversary_model: str='', test_passed_after: Optional[bool]=None, pr_url: str='') -> int` (L212)
- `def update_test_result(attempt_id: int, test_passed: bool, pr_url: str='')` (L259)
- `def mark_human_merged(repo: str, test_path: str)` (L267)
- `def record_pattern(failure_output: str, context_hash: str, fix_diff: str, success: bool)` (L277)
- `def get_statistics() -> dict` (L297)
- `def export_training_data(limit: int=1000) -> str` (L325)
  - _Export successful fixes as JSONL for fine-tuning._
- `def export_hf_dataset(repo_id: str, limit: int=1000, private: bool=True) -> str` (L369)
- `def _make_failure_signature(failure_output: str) -> str` (L379)

### `verification_loop.py`

- Lines: 145  Bytes: 5041

**Module docstring:**

> Rhodawk AI — Closed Verification Loop Engine
> =============================================
> This is the core capability that separates Rhodawk from every other AI CI tool.
> 
> Standard tools: AI generates fix → open PR (no idea if fix works)
> Rhodawk:        AI generates fix → re-run tests → if still failing, retry with
>                 new failure context + what was tried → up to MAX_RETRIES rounds
> 
> The loop:
>   1. Run tests → get failure output
>   2. Dispatch Aider with failure context + memory-retrieved similar fixes
>   3. Re-run tests on the modified code
>   4. If GREEN → gate through adversarial review → open PR
>   5. If STILL RED → append new failure + what was tried → goto 2
>   6. After MAX_RETRIES → mark as FAILED, escalate
> 
> BUG-002 FIX: Removed hardcoded os.getenv("RHODAWK_REPO_DIR") — repo_dir is now
>              passed as a parameter to build_initial_prompt() and build_retry_prompt().
> BUG-003 FIX: ADVERSARIAL_REJECTION_MULTIPLIER defaults to 2 (not 0) so adversarial
>              rejections get extra retry budget beyond MAX_RETRIES.

**Imports (5):**

- `import os`
- `import time`
- `from dataclasses import dataclass, field`
- `from typing import Optional`
- `from language_runtime import RuntimeFactory`

**Top-level constants (3):**

- `MAX_RETRIES` = `int(os.getenv('RHODAWK_MAX_RETRIES', '5'))`
- `ADVERSARIAL_REJECTION_MULTIPLIER` = `int(os.getenv('RHODAWK_ADVERSARIAL_REJECTION_MULTIPLIER', '2'))`
- `RETRY_BACKOFF_SECONDS` = `5`

**Classes (2):**

- `class VerificationAttempt` — line 36
- `class VerificationResult` — line 47

**Top-level functions (2):**

- `def build_retry_prompt(test_path: str, src_file: str, branch_name: str, original_failure: str, attempt_history: list[VerificationAttempt], similar_fixes: list[dict], repo_dir: str='/data/repo') -> str` (L56)
  - _Build an increasingly rich prompt for each retry attempt._
- `def build_initial_prompt(test_path: str, src_file: str, branch_name: str, failure_output: str, similar_fixes: list[dict], repo_dir: str='/data/repo') -> str` (L115)

### `vuln_classifier.py`

- Lines: 360  Bytes: 14370

**Module docstring:**

> Rhodawk AI — Vulnerability Classifier
> ========================================
> CWE taxonomy-based classification of raw findings.
> Maps evidence → CWE → CVSS vector → severity tier.
> 
> Also computes the final composite security score used in dashboards.

**Imports (4):**

- `from __future__ import annotations`
- `import re`
- `from dataclasses import dataclass`
- `from typing import Optional`

**Top-level constants (1):**

- `_CWE_DATABASE` = `{'CWE-89': {'name': 'SQL Injection', 'category': 'Injection', 'owasp': 'A03:2021-Injection', 'severity': 'CRITICAL', ...`

**Classes (1):**

- `class ClassificationResult` — line 18

**Top-level functions (3):**

- `def classify_vulnerability(cwe_hint: str, description: str='', exploit_class: str='') -> ClassificationResult` (L274)
  - _Classify a vulnerability by CWE ID, returning full taxonomy information._
- `def _infer_cwe(description: str, exploit_class: str) -> tuple[str, Optional[dict]]` (L311)
  - _Infer CWE from description keywords when CWE ID is not provided._
- `def get_all_cwes() -> list[dict]` (L348)
  - _Return the full CWE database as a list for the UI._

### `webhook_server.py`

- Lines: 266  Bytes: 10402

**Module docstring:**

> Rhodawk AI — Event-Driven Webhook Server
> ==========================================
> Accepts GitHub push events, CI failure webhooks, and manual triggers.
> Runs alongside Gradio in a separate thread on port 7861.
> 
> Supported events:
>   POST /webhook/github       — GitHub push/status/check_run webhooks (HMAC-SHA256 validated)
>   POST /webhook/ci           — Generic CI failure payload (any CI system)
>   POST /webhook/trigger      — Manual trigger with repo + test path
>   GET  /webhook/health       — Health check
>   GET  /webhook/queue        — Current job queue status
> 
> This makes Rhodawk a first-class CI/CD participant — not a side tool you run manually.

**Imports (9):**

- `import hashlib`
- `import hmac`
- `import json`
- `import os`
- `import threading`
- `import time`
- `from http.server import BaseHTTPRequestHandler, HTTPServer`
- `from typing import Callable`
- `from urllib.parse import urlparse`

**Top-level constants (4):**

- `WEBHOOK_SECRET` = `os.getenv('RHODAWK_WEBHOOK_SECRET', '')`
- `WEBHOOK_PORT` = `int(os.getenv('RHODAWK_WEBHOOK_PORT', '7861'))`
- `_RATE_LIMIT_MAX_EVENTS` = `int(os.getenv('RHODAWK_WEBHOOK_RATE_LIMIT', '10'))`
- `_RATE_LIMIT_WINDOW_SECONDS` = `60`

**Classes (1):**

- `class WebhookHandler(BaseHTTPRequestHandler)` — line 136
    - `def log_message(self, format, *args)` (L137)
    - `def _send_json(self, status_code: int, data: dict)` (L140)
    - `def do_GET(self)` (L148)
    - `def do_POST(self)` (L172)

**Top-level functions (8):**

- `def set_job_dispatcher(fn: Callable)` (L38)
  - _Register the function that app.py uses to spawn audit jobs._
- `def _log_webhook(event_type: str, payload: dict, status: str, detail: str='')` (L44)
- `def get_webhook_log(limit: int=50) -> list[dict]` (L57)
- `def clear_webhook_log() -> None` (L62)
- `def _verify_github_signature(body: bytes, signature_header: str) -> bool` (L68)
- `def _rate_limit_allows(ip: str) -> bool` (L90)
- `def _parse_github_event(event_type: str, payload: dict) -> dict` (L102)
  - _Extract repo, branch, and context from a GitHub webhook payload._
- `def start_webhook_server()` (L261)
  - _Start the webhook server in a daemon thread._

### `worker_pool.py`

- Lines: 210  Bytes: 6882

**Module docstring:**

> Rhodawk AI — Concurrent Worker Pool (Process-Isolated Edition)
> ==============================================================
> ThreadPoolExecutor-based audit orchestration with optional process isolation.
> 
> Process isolation mode (RHODAWK_PROCESS_ISOLATE=true):
>   Each test repair runs in its own subprocess via multiprocessing.Process.
>   This prevents:
>     - A crashing fix attempt from killing the orchestrator
>     - Memory leaks accumulating across many test repairs
>     - Global state corruption from aggressive Aider subprocess calls
>     - One tenant's runaway fix from starving others
> 
>   Isolation overhead: ~200ms per test (fork cost). Acceptable given tests
>   typically take seconds. Not recommended for < 5-second test suites.
> 
> Default (RHODAWK_PROCESS_ISOLATE=false):
>   Original ThreadPoolExecutor behavior — shared memory, low overhead.
> 
> BUG-001 FIX: Updated signature to accept env_config: EnvConfig instead of
>              pytest_bin: str to match app.py's call site.
> BUG-011 FIX: Tests returning already_green=True are no longer counted as
>              "healed" — they are counted under a separate "already_green" key.

**Imports (6):**

- `import concurrent.futures`
- `import multiprocessing`
- `import os`
- `import threading`
- `import traceback`
- `from typing import Callable`

**Top-level constants (3):**

- `MAX_WORKERS` = `int(os.getenv('RHODAWK_WORKERS', '8'))`
- `PROCESS_ISOLATE` = `os.getenv('RHODAWK_PROCESS_ISOLATE', 'false').lower() == 'true'`
- `ISOLATION_TIMEOUT` = `int(os.getenv('RHODAWK_ISOLATE_TIMEOUT', '600'))`

**Top-level functions (4):**

- `def _isolated_worker(result_queue: multiprocessing.Queue, test_path: str, process_fn_module: str, process_fn_name: str, env_config, mcp_config_path: str, tenant_id: str, repo: str) -> None` (L40)
  - _Runs inside a child process. Imports the module fresh, calls process_fn,_
- `def _run_isolated(test_path: str, process_fn: Callable, env_config, mcp_config_path: str, tenant_id: str, repo: str) -> dict` (L70)
  - _Run process_fn in a subprocess. Falls back to in-process on spawn failure._
- `def run_parallel_audit(test_files: list[str], process_fn: Callable, env_config, mcp_config_path: str, tenant_id: str, target_repo: str, should_stop: Callable[[], bool] | None=None) -> dict` (L113)
- `def _process_one_test(test_path: str, process_fn: Callable, env_config, mcp_config_path: str, tenant_id: str, repo: str) -> dict` (L196)

## `architect/`


### `architect/__init__.py`

- Lines: 29  Bytes: 1030

**Module docstring:**

> ARCHITECT — superhuman autonomous security agent runtime.
> 
> This package is the *control plane* for the ARCHITECT masterplan.  It sits on
> top of the existing Rhodawk + Mythos engines and adds:
> 
>   * A typed model-tier router (DeepSeek V3.2 / MiniMax M2.5 / Qwen3 / Claude / local).
>   * A pluggable skill registry that matches SKILL.md files to a target profile.
>   * An EmbodiedOS bridge that forwards findings to Telegram / OpenClaw / Hermes Agent.
>   * The autonomous "night-mode" scheduler (the 18:00 → 08:00 bug-bounty loop).
>   * An isolated sandbox manager for safe OSS-Guardian repo cloning.
> 
> Everything in this package is import-safe even when optional binaries
> (playwright, subfinder, dnsx, pwntools, …) are missing — heavy bridges are
> loaded lazily and degrade to ``available()=False`` rather than raising.

**Imports (1):**

- `from __future__ import annotations`

**Top-level constants (1):**

- `ARCHITECT_VERSION` = `'1.0.0'`

### `architect/embodied_bridge.py`

- Lines: 204  Bytes: 6801

**Module docstring:**

> ARCHITECT — EmbodiedOS bridge (§6 of the Masterplan).
> 
> Forwards every confirmed finding from Hermes / Mythos to:
> 
>   * Telegram (operator notifications)
>   * OpenClaw webhook (multi-channel gateway)
>   * Hermes Agent skill-extraction endpoint
>   * Discord (optional, mirror channel)
> 
> All emitters are best-effort; a downstream outage never blocks the audit
> pipeline.
> 
> Environment:
>     TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
>     OPENCLAW_WEBHOOK_URL
>     HERMES_AGENT_URL  (e.g. http://localhost:8080)
>     DISCORD_WEBHOOK_URL

**Imports (8):**

- `from __future__ import annotations`
- `import json`
- `import logging`
- `import os`
- `import time`
- `from dataclasses import asdict, dataclass, field`
- `from typing import Any`
- `import requests`

**Top-level constants (1):**

- `LOG` = `logging.getLogger('architect.embodied_bridge')`

**Classes (1):**

- `class FindingPayload` — line 36

**Top-level functions (9):**

- `def _post(url: str, payload: dict[str, Any], *, timeout: int=8) -> bool` (L50)
- `def _telegram(msg: str) -> bool` (L62)
- `def _discord(msg: str) -> bool` (L71)
- `def _format_for_humans(f: FindingPayload) -> str` (L78)
- `def emit_finding(f: FindingPayload) -> dict[str, bool]` (L88)
  - _Fan-out a finding to every wired channel. Returns per-channel success._
- `def emit_status(message: str, level: str='info') -> bool` (L113)
  - _Fire a free-form operator notice (start of nightly run, errors, etc.)._
- `def dispatch_to_openclaw(job_type: str, payload: dict[str, Any], *, timeout: int=15) -> dict[str, Any]` (L122)
  - _Send a long-running compute job to the OpenClaw GPU fleet._
- `def receive_openclaw_result(payload: dict[str, Any]) -> dict[str, Any]` (L167)
  - _Webhook handler for results pushed back from the OpenClaw fleet._
- `def channels() -> dict[str, bool]` (L198)

### `architect/godmode_consensus.py`

- Lines: 201  Bytes: 8372

**Module docstring:**

> GODMODE Consensus — multi-model parallel racing (G0DM0D3-inspired).
> 
> Fires the same prompt across 3-N model+style combos in parallel, scores
> each response on a composite metric, and returns the winner along with
> the full leaderboard.  Re-uses the existing model router so every call
> honours the hard budget cap and falls back to T5-local when needed.
> 
> Composite score (0-100):
>     correctness   × 0.30
>     specificity   × 0.20
>     repro_clarity × 0.20
>     cvss_uplift   × 0.20
>     novelty       × 0.10
> 
> The scorer is a deterministic feature-based heuristic so we never need an
> extra model call to judge — but a custom scorer can be passed in.
> 
> Public API:
>     race(prompt, *, profile, combos=None, scorer=None) -> RaceResult

**Imports (8):**

- `from __future__ import annotations`
- `import concurrent.futures as _cf`
- `import logging`
- `import re`
- `import time`
- `from dataclasses import dataclass, field`
- `from typing import Any, Callable`
- `from . import master_redteam_prompt, model_router`

**Top-level constants (5):**

- `LOG` = `logging.getLogger('architect.godmode_consensus')`
- `_RE_CWE` = `re.compile('\\bCWE-\\d+\\b', re.IGNORECASE)`
- `_RE_CVSS` = `re.compile('CVSS[: ]+\\d', re.IGNORECASE)`
- `_RE_REPRO` = `re.compile('^\\s*(?:\\d+\\.|step\\s*\\d|repro)', re.IGNORECASE | re.MULTILINE)`
- `_RE_CODE` = `re.compile('```|^\\s{4}\\S', re.MULTILINE)`

**Classes (2):**

- `class CandidateResult` — line 47
- `class RaceResult` — line 59
    - `def to_dict(self) -> dict[str, Any]` (L66)

**Top-level functions (3):**

- `def default_scorer(response: str) -> tuple[float, dict[str, float]]` (L89)
  - _Pure-text heuristic — never calls an LLM._
- `def _default_llm_call(model: str, messages: list[dict]) -> str` (L135)
  - _Call the production Hermes LLM helper.  Returns the assistant text._
- `def race(user_prompt: str, *, profile: dict[str, Any] | None=None, *, combos: list[dict[str, str]] | None=None, *, scorer: Callable[[str], tuple[float, dict[str, float]]] | None=None, *, llm_call: Callable[[str, list[dict]], str] | None=None, *, timeout_s: float=90.0) -> RaceResult` (L151)
  - _Fan out ``user_prompt`` across ``combos`` (default 5), score each, return_

### `architect/master_redteam_prompt.py`

- Lines: 220  Bytes: 10142

**Module docstring:**

> Master Red-Team Operator — system-prompt builder for every LLM call.
> 
> Inspired by:
>   * elder-plinius/G0DM0D3   — multi-prompt parallel racing, AutoTune,
>                               Parseltongue input perturbation, ULTRAPLINIAN
>                               composite scoring.
>   * Gen-Verse/OpenClaw-RL    — async 4-component RL loop, language-feedback
>                               policy improvement, hybrid binary-RL judge.
>   * "20 things that will get your VIBE-CODED app hacked in 24 hours".
> 
> The goal is to give the agent the **maximum operator control surface**
> while keeping the legal / ethical guard rails intact (the agent operates
> inside an approved disclosure pipeline, never against unauthorised assets).
> 
> Public API:
>     build_master_prompt(profile, *, mode="hunt") -> str
>     OPERATOR_DIRECTIVE                          -> str (the persona)
>     VIBE_CODED_HIT_LIST                         -> list[str] (always-loaded)

**Imports (5):**

- `from __future__ import annotations`
- `import json`
- `import os`
- `import textwrap`
- `from typing import Any`

**Top-level constants (1):**

- `OPERATOR_DIRECTIVE` = `textwrap.dedent('\n    You are RHODAWK — a senior red-team operator embedded inside a\n    coordinated, legally autho...`

**Top-level functions (4):**

- `def build_master_prompt(profile: dict[str, Any] | None=None, *, mode: str='hunt', *, extra_skill_pack: str | None=None, *, include_hit_list: bool=True) -> str` (L135)
  - _Compose the master red-team system prompt for one LLM call._
- `def _operator_notes() -> str` (L180)
- `def as_messages(user_prompt: str, profile: dict[str, Any] | None=None, *, mode: str='hunt') -> list[dict[str, str]]` (L192)
  - _Convenience: produce a `messages` list ready for an OpenAI-style call._
- `def diagnostic() -> dict[str, Any]` (L203)
  - _Return the current static metadata (used by /healthz endpoints)._

### `architect/model_router.py`

- Lines: 281  Bytes: 10646

**Module docstring:**

> ARCHITECT — typed model-tier router (§8 of the Masterplan, v2 — Apr 2026).
> 
> Routes every LLM call to the cheapest model that can do the job, while
> keeping a per-task fallback chain.  All calls go through OpenRouter unless
> the task is mapped to the local ``vLLM`` endpoint.
> 
> Tier table (Masterplan §1.1, confirmed April 2026):
> 
>     T1-fast  MiniMax M2.5-highspeed   — recon, triage, bulk scan
>     T1-deep  DeepSeek V3              — static analysis, patch generation
>     T2       Qwen3-235B-A22B          — exploit reasoning, attack graphs
>     T3       MiniMax M2.5             — long-context repo analysis
>     T4       Claude Sonnet 4.6        — P1/P2 final report polish
>     T5       DeepSeek-R1-32B-AWQ      — local Kaggle GPU bulk triage
> 
> Environment:
> 
>     OPENROUTER_API_KEY              — required for tiers 1-4
>     OPENROUTER_BASE_URL             — defaults to https://openrouter.ai/api/v1
>     LOCAL_VLLM_BASE_URL             — defaults to http://localhost:8000/v1
>     ARCHITECT_DEFAULT_MAX_TOKENS    — default 4096
>     ARCHITECT_HARD_BUDGET_USD       — abort the day if this is exceeded
>     TIER1_PRIMARY_MODEL / TIER1_DEEP_MODEL / TIER2_PRIMARY_MODEL
>     TIER3_PRIMARY_MODEL / TIER4_PRIMARY_MODEL — env overrides

**Imports (7):**

- `from __future__ import annotations`
- `import json`
- `import logging`
- `import os`
- `import time`
- `from dataclasses import dataclass, field`
- `from typing import Any`

**Top-level constants (8):**

- `LOG` = `logging.getLogger('architect.model_router')`
- `TIER1_PRIMARY` = `os.getenv('TIER1_PRIMARY_MODEL', 'minimax/minimax-m2.5-highspeed')`
- `TIER1_DEEP` = `os.getenv('TIER1_DEEP_MODEL', 'deepseek/deepseek-chat-v3')`
- `TIER2_PRIMARY` = `os.getenv('TIER2_PRIMARY_MODEL', 'qwen/qwen3-235b-a22b')`
- `TIER3_PRIMARY` = `os.getenv('TIER3_PRIMARY_MODEL', 'minimax/minimax-m2.5')`
- `TIER4_PRIMARY` = `os.getenv('TIER4_PRIMARY_MODEL', 'anthropic/claude-sonnet-4-6')`
- `TIER5_LOCAL` = `os.getenv('TIER5_LOCAL_MODEL', 'local/deepseek-r1-32b-awq')`
- `_BUDGET` = `_BudgetState()`

**Classes (2):**

- `class RouteDecision` — line 82
    - `def to_json(self) -> str` (L89)
- `class _BudgetState` — line 94

**Top-level functions (8):**

- `def reset_budget(hard_cap_usd: float | None=None) -> None` (L103)
- `def budget_status() -> dict[str, Any]` (L108)
- `def _tier_of(model: str) -> int` (L117)
- `def route(task: str, *, prefer: str | None=None) -> RouteDecision` (L125)
  - _Pick the right model for a task. Honors the hard budget cap._
- `def record_usage(model: str, tokens: int) -> float` (L143)
- `def all_routes() -> dict[str, list[str]]` (L149)
- `def build_skill_system_prompt(profile: dict[str, Any], *, max_skills: int=3, *, base_directive: str | None=None, *, pin_skills: list[str] | None=None) -> str` (L154)
  - _Materialise the matched skill bodies into a single system prompt that_
- `def call_with_skills(task: str, user_prompt: str, profile: dict[str, Any], *, max_skills: int=4, *, extra_system: str | None=None, *, llm_call: 'callable | None'=None, *, mode: str='hunt', *, use_master_prompt: bool=True, *, record_rl: bool=True, *, pin_skills: list[str] | None=None) -> dict[str, Any]` (L198)
  - _Convenience wrapper:_

### `architect/nightmode.py`

- Lines: 226  Bytes: 8202

**Module docstring:**

> ARCHITECT — autonomous "night-mode" loop (§5.2 of the Masterplan).
> 
> Phase schedule (operator-local time):
>     18:00 → scope ingestion (HackerOne / Bugcrowd / Intigriti)
>     18:30 → reconnaissance fan-out per top target
>     20:00 → vulnerability hunt — 5 specialist agents in parallel
>     04:00 → report drafting
>     08:00 → operator review handoff (Telegram nudge)
> 
> The scheduler is opt-in (``ARCHITECT_NIGHTMODE=1``).  It never executes any
> submission action; the operator remains the final gate on every report.

**Imports (9):**

- `from __future__ import annotations`
- `import datetime as _dt`
- `import logging`
- `import os`
- `import threading`
- `import time`
- `from dataclasses import dataclass, field`
- `from typing import Any, Callable`
- `from . import embodied_bridge`

**Top-level constants (1):**

- `LOG` = `logging.getLogger('architect.nightmode')`

**Classes (2):**

- `class PhaseResult` — line 31
- `class NightRun` — line 118

**Top-level functions (10):**

- `def _now() -> str` (L40)
- `def _phase_scope_ingest() -> list[str]` (L46)
  - _Pull active programs from every linked bounty platform._
- `def _phase_recon(target: str) -> dict[str, Any]` (L60)
- `def _phase_hunt(target: str, recon: dict[str, Any]) -> list[dict]` (L80)
  - _Run the 5 specialist agents (auth, server-side, logic, infra, api)._
- `def _phase_report(findings: list[dict]) -> list[dict]` (L101)
  - _Filter to ACTS ≥ 0.72 and format for human review._
- `def run_one_cycle() -> NightRun` (L125)
- `def _run_one_cycle_inner() -> NightRun` (L154)
- `def _next_run_time(hour: int) -> float` (L199)
- `def schedule_loop(start_hour: int | None=None) -> None` (L207)
  - _Daemon loop: runs ``run_one_cycle`` once per day at start_hour:00 local._
- `def start_in_background() -> None` (L225)

### `architect/parseltongue.py`

- Lines: 193  Bytes: 6856

**Module docstring:**

> Parseltongue — input perturbation engine (G0DM0D3-inspired).
> 
> Used to red-team LLM endpoints, content-filter classifiers, and any text
> decision boundary.  Detects trigger tokens and applies one or more
> obfuscation techniques across three intensity tiers.
> 
> Pure-Python, no dependencies, deterministic.
> 
> Public API:
>     perturb(text, *, technique=None, intensity="medium") -> str
>     perturb_all(text, *, intensity="medium") -> dict[str, str]
>     DEFAULT_TRIGGERS  — 33 default trigger words (red-team probes).

**Imports (4):**

- `from __future__ import annotations`
- `import random`
- `import re`
- `from typing import Iterable`

**Top-level constants (8):**

- `TIER_SIZE` = `{'light': 11, 'medium': 22, 'heavy': 33}`
- `_LEET` = `str.maketrans({'a': '4', 'A': '4', 'e': '3', 'E': '3', 'i': '1', 'I': '1', 'o': '0', 'O': '0', 's': '5', 'S': '5', 't...`
- `_BRAILLE` = `{'a': '⠁', 'b': '⠃', 'c': '⠉', 'd': '⠙', 'e': '⠑', 'f': '⠋', 'g': '⠛', 'h': '⠓', 'i': '⠊', 'j': '⠚', 'k': '⠅', 'l': '...`
- `_MORSE` = `{'a': '.-', 'b': '-...', 'c': '-.-.', 'd': '-..', 'e': '.', 'f': '..-.', 'g': '--.', 'h': '....', 'i': '..', 'j': '.-...`
- `_UNICODE_LOOKALIKE` = `{'a': 'а', 'e': 'е', 'o': 'о', 'p': 'р', 'c': 'с', 'y': 'у', 'x': 'х', 'i': 'і', 's': 'ѕ', 'h': 'һ'}`
- `_PHONETIC` = `{'a': 'ay', 'b': 'bee', 'c': 'see', 'd': 'dee', 'e': 'ee', 'f': 'eff', 'g': 'gee', 'h': 'aitch', 'i': 'eye', 'j': 'ja...`
- `_ZW` = `'\u200b'`
- `TECHNIQUES` = `{'leet': _leet, 'bubble': _bubble, 'braille': _braille, 'morse': _morse, 'unicode': _unicode_sub, 'phonetic': _phonet...`

**Top-level functions (11):**

- `def _leet(s: str) -> str` (L47)
- `def _bubble(s: str) -> str` (L52)
- `def _braille(s: str) -> str` (L78)
- `def _morse(s: str) -> str` (L95)
- `def _unicode_sub(s: str, *, density: float=0.6) -> str` (L106)
- `def _phonetic(s: str) -> str` (L128)
- `def _zwj(s: str, *, density: float=0.5) -> str` (L136)
- `def _triggers_for_tier(intensity: str) -> list[str]` (L156)
- `def perturb(text: str, *, technique: str | None=None, *, intensity: str='medium', *, triggers: Iterable[str] | None=None, *, seed: int | None=None) -> str` (L161)
  - _Apply one technique to every trigger in ``text`` (case-insensitive)._
- `def perturb_all(text: str, *, intensity: str='medium', *, seed: int | None=None) -> dict[str, str]` (L182)
  - _Run every technique against ``text`` and return one variant per technique._
- `def list_techniques() -> list[str]` (L192)

### `architect/rl_feedback_loop.py`

- Lines: 187  Bytes: 6631

**Module docstring:**

> RL Feedback Loop — OpenClaw-RL inspired async 4-component policy improver.
> 
> Adapted from Gen-Verse/OpenClaw-RL (Apache-2.0).  We don't run real GPU
> training inside the Space — that lives on the OpenClaw fleet.  This
> module is the *local* half: it captures every (prompt, response, reward)
> trace, scores it via a binary judge + composite scorer, and periodically
> ships a batch to the OpenClaw webhook so the LoRA adapter for the Tier-5
> local model improves over time.
> 
> Components:
> 
>     1. Rollout collector   — every call_with_skills() emits a Trace.
>     2. PRM / judge         — scores the trace (binary RL + composite RL).
>     3. Trace store         — append-only JSONL on disk.
>     4. Trainer dispatcher  — flush in batches via embodied_bridge.

**Imports (10):**

- `from __future__ import annotations`
- `import dataclasses`
- `import json`
- `import logging`
- `import os`
- `import threading`
- `import time`
- `from dataclasses import dataclass, field`
- `from pathlib import Path`
- `from typing import Any`

**Top-level constants (4):**

- `LOG` = `logging.getLogger('architect.rl_feedback_loop')`
- `TRACE_PATH` = `Path(os.getenv('RHODAWK_RL_TRACE', '/data/rl_traces.jsonl'))`
- `BATCH_SIZE` = `int(os.getenv('RHODAWK_RL_BATCH', '50'))`
- `LOCK` = `threading.Lock()`

**Classes (1):**

- `class Trace` — line 39
    - `def to_dict(self) -> dict[str, Any]` (L50)

**Top-level functions (7):**

- `def _judge(prompt: str, response: str) -> tuple[int, float, str]` (L55)
  - _Cheap heuristic judge — same composite as godmode_consensus, plus_
- `def record(*, task: str, *, model: str, *, prompt: str, *, response: str, *, profile: dict[str, Any] | None=None, *, extra_judge: tuple[int, float, str] | None=None) -> Trace` (L76)
- `def _append(tr: Trace) -> None` (L106)
- `def _count_traces() -> int` (L112)
- `def flush(*, max_lines: int | None=None) -> dict[str, Any]` (L121)
  - _Ship all currently-stored traces to the OpenClaw fleet for LoRA_
- `def stats() -> dict[str, Any]` (L152)
- `def submit_language_feedback(*, trace_id: str | int, *, feedback: str, *, polarity: int) -> dict[str, Any]` (L173)
  - _Push a free-form natural-language operator feedback onto the queue_

### `architect/sandbox.py`

- Lines: 95  Bytes: 3114

**Module docstring:**

> ARCHITECT — isolated sandbox manager (§4.2 / §10.2 of the Masterplan).
> 
> Provides the OSS-Guardian sandbox primitive: a per-target, ephemeral, network-
> restricted directory where the agent may safely clone and analyse arbitrary
> open-source code.
> 
> When ``docker`` is available we build a one-shot container with:
>   * read-only bind of the host workspace
>   * iptables drop-all egress after the initial git clone
>   * 4-hour wallclock cap, 10 GB disk cap, 8 GB memory cap
> 
> When docker is not available (HF Space) we fall back to a process-level
> sandbox: shutil-based ephemeral directory, ``rlimit`` walltime cap, no network
> ops outside the initial git clone.

**Imports (12):**

- `from __future__ import annotations`
- `import logging`
- `import os`
- `import shutil`
- `import signal`
- `import subprocess`
- `import tempfile`
- `import time`
- `from contextlib import contextmanager`
- `from dataclasses import dataclass`
- `from pathlib import Path`
- `from typing import Iterator`

**Top-level constants (4):**

- `LOG` = `logging.getLogger('architect.sandbox')`
- `DEFAULT_TIMEOUT_S` = `int(os.getenv('ARCHITECT_SANDBOX_TIMEOUT_S', '14400'))`
- `DEFAULT_DISK_GB` = `int(os.getenv('ARCHITECT_SANDBOX_DISK_GB', '10'))`
- `DEFAULT_MEM_GB` = `int(os.getenv('ARCHITECT_SANDBOX_MEM_GB', '8'))`

**Classes (1):**

- `class SandboxHandle` — line 40
    - `def elapsed_s(self) -> float` (L47)

**Top-level functions (4):**

- `def _docker_available() -> bool` (L51)
- `def _git_clone(target_url: str, dest: Path, depth: int=1) -> None` (L55)
- `def open_sandbox(target_url: str) -> Iterator[SandboxHandle]` (L63)
  - _Context-managed sandbox.  Cleans up the workdir on exit._
- `def _on_timeout(signum, frame)` (L94)

### `architect/skill_registry.py`

- Lines: 142  Bytes: 4987

**Module docstring:**

> ARCHITECT — skill registry (§7 of the Masterplan).
> 
> Loads ``SKILL.md`` files from ``architect/skills/`` and ``/data/skills/``
> (if present), parses their YAML front-matter, and exposes a ``match(profile)``
> selector that returns the relevant skills for a given target profile.
> 
> The agentskills.io front-matter we expect:
> 
>     ---
>     name: web-security-advanced
>     domain: web
>     triggers:
>       languages:    [python, javascript, typescript, php]
>       frameworks:   [flask, fastapi, django, express, rails]
>       asset_types:  [http, web]
>     tools:          [burp, ffuf, nuclei, sqlmap]
>     severity_focus: [P1, P2]
>     ---

**Imports (7):**

- `from __future__ import annotations`
- `import logging`
- `import os`
- `import re`
- `from dataclasses import dataclass, field`
- `from pathlib import Path`
- `from typing import Any`

**Top-level constants (3):**

- `LOG` = `logging.getLogger('architect.skill_registry')`
- `DEFAULT_SKILLS_DIR` = `Path(__file__).resolve().parent / 'skills'`
- `RUNTIME_SKILLS_DIR` = `Path(os.getenv('ARCHITECT_SKILLS_DIR', '/data/skills'))`

**Classes (1):**

- `class Skill` — line 38
    - `def matches(self, profile: dict[str, Any]) -> int` (L47)
      - _Return a positive match score; 0 means 'do not load'._

**Top-level functions (5):**

- `def _parse(path: Path) -> Skill | None` (L60)
- `def load_all() -> list[Skill]` (L101)
- `def match(profile: dict[str, Any], top_k: int=6) -> list[Skill]` (L114)
- `def render_skill_pack(profile: dict[str, Any], top_k: int=6) -> str` (L120)
  - _Materialise the matched skills as a single markdown pack ready to paste_
- `def stats() -> dict[str, Any]` (L134)

### `architect/skill_selector.py`

- Lines: 320  Bytes: 11847

**Module docstring:**

> ARCHITECT — semantic skill selector (Masterplan §5).
> 
> Upgrades the keyword-based ``architect/skill_registry`` with **semantic
> similarity ranking** so the right domain skills are loaded into the LLM
> context regardless of how the task is phrased.
> 
> Tier-5 design (Masterplan §7):
>     * Embeddings:  sentence-transformers / MiniLM-L6-v2  (CPU, $0)
>     * Fallback:    deterministic keyword-overlap scorer  (no model needed)
>     * Cache:       skill embeddings hashed on disk (JSON) so the model loads
>                    *once* per process and *never* recomputes between calls.
> 
> Public surface:
> 
>     select_for_task(task_description, repo_languages, repo_tech_stack,
>                     attack_phase, top_k=5) -> str
>         Returns a single XML-flavoured ``<skills>...</skills>`` block ready
>         to be prepended to any system prompt.
> 
>     pack(task_description, ...) -> list[Skill]
>         Same logic but returns the matched Skill objects (for callers who
>         want to render their own context format).
> 
> The module is designed to **never raise** in production: every external
> dependency (sentence-transformers, numpy, sklearn) is optional and falls
> back to a pure-Python implementation.

**Imports (12):**

- `from __future__ import annotations`
- `import hashlib`
- `import json`
- `import logging`
- `import math`
- `import os`
- `import re`
- `import threading`
- `from dataclasses import dataclass`
- `from pathlib import Path`
- `from typing import Any, Iterable`
- `from . import skill_registry`

**Top-level constants (3):**

- `LOG` = `logging.getLogger('architect.skill_selector')`
- `CACHE_DIR` = `Path(os.getenv('ARCHITECT_SKILL_CACHE', '/tmp/architect_skill_cache'))`
- `_LOCK` = `threading.Lock()`

**Classes (1):**

- `class Match` — line 186
    - `def to_dict(self) -> dict[str, Any]` (L191)

**Top-level functions (13):**

- `def _try_load_model() -> Any` (L67)
  - _Best-effort load of MiniLM. Returns None on any failure._
- `def _skill_hash(skill: skill_registry.Skill) -> str` (L85)
- `def _cache_path_for(model_name: str) -> Path` (L92)
- `def _load_disk_cache(model_name: str) -> dict[str, list[float]]` (L97)
- `def _save_disk_cache(model_name: str, data: dict[str, list[float]]) -> None` (L108)
- `def _ensure_skill_embeddings() -> dict[str, list[float]]` (L116)
  - _Return ``{skill_name: vector}`` for the entire registry. Computes only_
- `def _cosine(a: list[float], b: list[float]) -> float` (L156)
- `def _keyword_score(skill: skill_registry.Skill, tokens: set[str]) -> float` (L167)
  - _Pure-Python fallback ranker. Counts shared whitespace tokens._
- `def _phase_boost(skill: skill_registry.Skill, phase: str) -> float` (L176)
- `def pack(task_description: str, *, repo_languages: Iterable[str] | None=None, *, repo_tech_stack: Iterable[str] | None=None, *, attack_phase: str='static', *, top_k: int=5, *, pin: Iterable[str] | None=None) -> list[Match]` (L201)
  - _Return up to ``top_k`` matched skills (highest score first)._
- `def select_for_task(task_description: str, repo_languages: Iterable[str] | None=None, repo_tech_stack: Iterable[str] | None=None, attack_phase: str='static', top_k: int=5, pin: Iterable[str] | None=None) -> str` (L265)
  - _Render the matched skills into a context block ready to be prepended to_
- `def explain(task_description: str, **kwargs) -> dict[str, Any]` (L302)
  - _Diagnostic: returns the ranked match list as JSON-able dicts._
- `def stats() -> dict[str, Any]` (L312)

### `architect/skills/ai-ml-security.md`

- Lines: 57  Bytes: 2856

**Headings (4):**

- L12 `# AI / ML Security`
  - L14 `## When to load`
  - L19 `## Bug classes that pay`
  - L44 `## Methodology`

**Opening text:**

> --- name: ai-ml-security domain: ai triggers:

### `architect/skills/ai-systems/agent-tool-abuse.md`

- Lines: 27  Bytes: 606

**Headings (4):**

- L9 `# agent-tool-abuse`
  - L13 `## Detection checklist`
  - L19 `## Exploitation primitives`
  - L24 `## Reporting fingerprint`

**Opening text:**

> --- name: agent-tool-abuse domain: ai-systems triggers:

### `architect/skills/ai-systems/ai-api-authentication-bypass.md`

- Lines: 27  Bytes: 623

**Headings (4):**

- L9 `# ai-api-authentication-bypass`
  - L13 `## Detection checklist`
  - L19 `## Exploitation primitives`
  - L24 `## Reporting fingerprint`

**Opening text:**

> --- name: ai-api-authentication-bypass domain: ai-systems triggers:

### `architect/skills/ai-systems/llm-system-prompt-extraction.md`

- Lines: 27  Bytes: 630

**Headings (4):**

- L9 `# llm-system-prompt-extraction`
  - L13 `## Detection checklist`
  - L19 `## Exploitation primitives`
  - L24 `## Reporting fingerprint`

**Opening text:**

> --- name: llm-system-prompt-extraction domain: ai-systems triggers:

### `architect/skills/ai-systems/model-inversion-attacks.md`

- Lines: 27  Bytes: 576

**Headings (4):**

- L9 `# model-inversion-attacks`
  - L13 `## Detection checklist`
  - L19 `## Exploitation primitives`
  - L24 `## Reporting fingerprint`

**Opening text:**

> --- name: model-inversion-attacks domain: ai-systems triggers:

### `architect/skills/ai-systems/prompt-injection-direct.md`

- Lines: 27  Bytes: 660

**Headings (4):**

- L9 `# prompt-injection-direct`
  - L13 `## Detection checklist`
  - L19 `## Exploitation primitives`
  - L24 `## Reporting fingerprint`

**Opening text:**

> --- name: prompt-injection-direct domain: ai-systems triggers:

### `architect/skills/ai-systems/prompt-injection-indirect.md`

- Lines: 27  Bytes: 626

**Headings (4):**

- L9 `# prompt-injection-indirect`
  - L13 `## Detection checklist`
  - L19 `## Exploitation primitives`
  - L24 `## Reporting fingerprint`

**Opening text:**

> --- name: prompt-injection-indirect domain: ai-systems triggers:

### `architect/skills/ai-systems/rag-poisoning.md`

- Lines: 27  Bytes: 578

**Headings (4):**

- L9 `# rag-poisoning`
  - L13 `## Detection checklist`
  - L19 `## Exploitation primitives`
  - L24 `## Reporting fingerprint`

**Opening text:**

> --- name: rag-poisoning domain: ai-systems triggers:

### `architect/skills/api-security.md`

- Lines: 46  Bytes: 2093

**Headings (5):**

- L11 `# API Security`
  - L13 `## When to load`
  - L17 `## OWASP API Top-10 (2023) checklist`
  - L36 `## Procedure`
  - L44 `## Reporting`

**Opening text:**

> --- name: api-security domain: api triggers:

### `architect/skills/automotive-security.md`

- Lines: 37  Bytes: 1413

**Headings (5):**

- L10 `# Automotive Security`
  - L12 `## When to load`
  - L16 `## Stack`
  - L22 `## Procedure`
  - L35 `## Reporting`

**Opening text:**

> --- name: automotive-security domain: automotive triggers:

### `architect/skills/automotive/autosar-architecture-security.md`

- Lines: 27  Bytes: 613

**Headings (4):**

- L9 `# autosar-architecture-security`
  - L13 `## Detection checklist`
  - L19 `## Exploitation primitives`
  - L24 `## Reporting fingerprint`

**Opening text:**

> --- name: autosar-architecture-security domain: automotive triggers:

### `architect/skills/automotive/can-bus-attacks.md`

- Lines: 27  Bytes: 585

**Headings (4):**

- L9 `# can-bus-attacks`
  - L13 `## Detection checklist`
  - L19 `## Exploitation primitives`
  - L24 `## Reporting fingerprint`

**Opening text:**

> --- name: can-bus-attacks domain: automotive triggers:

### `architect/skills/automotive/uds-iso14229-security.md`

- Lines: 27  Bytes: 611

**Headings (4):**

- L9 `# uds-iso14229-security`
  - L13 `## Detection checklist`
  - L19 `## Exploitation primitives`
  - L24 `## Reporting fingerprint`

**Opening text:**

> --- name: uds-iso14229-security domain: automotive triggers:

### `architect/skills/automotive/v2x-communication-security.md`

- Lines: 27  Bytes: 603

**Headings (4):**

- L9 `# v2x-communication-security`
  - L13 `## Detection checklist`
  - L19 `## Exploitation primitives`
  - L24 `## Reporting fingerprint`

**Opening text:**

> --- name: v2x-communication-security domain: automotive triggers:

### `architect/skills/aviation-aerospace.md`

- Lines: 38  Bytes: 1575

**Headings (5):**

- L10 `# Aviation & Aerospace`
  - L12 `## When to load`
  - L16 `## Surface`
  - L28 `## Procedure`
  - L36 `## Ethics`

**Opening text:**

> --- name: aviation-aerospace domain: aviation triggers:

### `architect/skills/aviation/arinc429-security.md`

- Lines: 27  Bytes: 590

**Headings (4):**

- L9 `# arinc429-security`
  - L13 `## Detection checklist`
  - L19 `## Exploitation primitives`
  - L24 `## Reporting fingerprint`

**Opening text:**

> --- name: arinc429-security domain: aviation triggers:

### `architect/skills/aviation/avionics-software-patterns.md`

- Lines: 27  Bytes: 599

**Headings (4):**

- L9 `# avionics-software-patterns`
  - L13 `## Detection checklist`
  - L19 `## Exploitation primitives`
  - L24 `## Reporting fingerprint`

**Opening text:**

> --- name: avionics-software-patterns domain: aviation triggers:

### `architect/skills/aviation/do178c-verification-gaps.md`

- Lines: 27  Bytes: 605

**Headings (4):**

- L9 `# do178c-verification-gaps`
  - L13 `## Detection checklist`
  - L19 `## Exploitation primitives`
  - L24 `## Reporting fingerprint`

**Opening text:**

> --- name: do178c-verification-gaps domain: aviation triggers:

### `architect/skills/bb-methodology-claude.md`

- Lines: 73  Bytes: 2911

**Headings (7):**

- L12 `# Bug-Bounty Methodology (imported from claude-bug-bounty)`
  - L20 `## Phase 1 — Scope & passive recon`
  - L30 `## Phase 2 — Surface mapping`
  - L37 `## Phase 3 — Triage by bug class`
  - L55 `## Phase 4 — Validation gate`
  - L65 `## Phase 5 — Report`
  - L70 `## Tone`

**Opening text:**

> --- name: bb-methodology-claude domain: web triggers:

### `architect/skills/binary-analysis.md`

- Lines: 47  Bytes: 1993

**Headings (5):**

- L11 `# Binary Analysis`
  - L13 `## When to load`
  - L17 `## Procedure`
  - L37 `## Known-bad patterns`
  - L43 `## Tool calls (MCP)`

**Opening text:**

> --- name: binary-analysis domain: binary triggers:

### `architect/skills/binary/buffer-overflow-stack.md`

- Lines: 27  Bytes: 644

**Headings (4):**

- L9 `# buffer-overflow-stack`
  - L13 `## Detection checklist`
  - L19 `## Exploitation primitives`
  - L24 `## Reporting fingerprint`

**Opening text:**

> --- name: buffer-overflow-stack domain: binary triggers:

### `architect/skills/binary/format-string-exploitation.md`

- Lines: 27  Bytes: 609

**Headings (4):**

- L9 `# format-string-exploitation`
  - L13 `## Detection checklist`
  - L19 `## Exploitation primitives`
  - L24 `## Reporting fingerprint`

**Opening text:**

> --- name: format-string-exploitation domain: binary triggers:

### `architect/skills/binary/heap-exploitation-glibc.md`

- Lines: 27  Bytes: 625

**Headings (4):**

- L9 `# heap-exploitation-glibc`
  - L13 `## Detection checklist`
  - L19 `## Exploitation primitives`
  - L24 `## Reporting fingerprint`

**Opening text:**

> --- name: heap-exploitation-glibc domain: binary triggers:

### `architect/skills/binary/integer-overflow-underflow.md`

- Lines: 27  Bytes: 636

**Headings (4):**

- L9 `# integer-overflow-underflow`
  - L13 `## Detection checklist`
  - L19 `## Exploitation primitives`
  - L24 `## Reporting fingerprint`

**Opening text:**

> --- name: integer-overflow-underflow domain: binary triggers:

### `architect/skills/binary/kernel-exploitation-linux.md`

- Lines: 27  Bytes: 640

**Headings (4):**

- L9 `# kernel-exploitation-linux`
  - L13 `## Detection checklist`
  - L19 `## Exploitation primitives`
  - L24 `## Reporting fingerprint`

**Opening text:**

> --- name: kernel-exploitation-linux domain: binary triggers:

### `architect/skills/binary/race-conditions-toctou.md`

- Lines: 27  Bytes: 591

**Headings (4):**

- L9 `# race-conditions-toctou`
  - L13 `## Detection checklist`
  - L19 `## Exploitation primitives`
  - L24 `## Reporting fingerprint`

**Opening text:**

> --- name: race-conditions-toctou domain: binary triggers:

### `architect/skills/binary/rop-chain-construction.md`

- Lines: 27  Bytes: 619

**Headings (4):**

- L9 `# rop-chain-construction`
  - L13 `## Detection checklist`
  - L19 `## Exploitation primitives`
  - L24 `## Reporting fingerprint`

**Opening text:**

> --- name: rop-chain-construction domain: binary triggers:

### `architect/skills/binary/type-confusion.md`

- Lines: 27  Bytes: 582

**Headings (4):**

- L9 `# type-confusion`
  - L13 `## Detection checklist`
  - L19 `## Exploitation primitives`
  - L24 `## Reporting fingerprint`

**Opening text:**

> --- name: type-confusion domain: binary triggers:

### `architect/skills/binary/use-after-free.md`

- Lines: 27  Bytes: 638

**Headings (4):**

- L9 `# use-after-free`
  - L13 `## Detection checklist`
  - L19 `## Exploitation primitives`
  - L24 `## Reporting fingerprint`

**Opening text:**

> --- name: use-after-free domain: binary triggers:

### `architect/skills/browser-engine-security.md`

- Lines: 60  Bytes: 2800

**Headings (6):**

- L12 `# Browser Engine Security`
  - L14 `## When to load`
  - L18 `## Bug classes that pay (Pwn2Own / Chrome VRP / TCC tier)`
  - L35 `## Methodology`
  - L49 `## Exploitation pattern (modern V8)`
  - L57 `## Reporting`

**Opening text:**

> --- name: browser-engine-security domain: browser triggers:

### `architect/skills/bug-bounty-reference-index.md`

- Lines: 97  Bytes: 3499

**Headings (15):**

- L12 `# Bug-Bounty Reference Index`
  - L21 `## XSS (cross-site scripting)`
  - L28 `## SQLi / NoSQLi`
  - L33 `## SSRF (server-side request forgery)`
  - L39 `## RCE`
  - L45 `## CSRF`
  - L49 `## IDOR / BOLA`
  - L54 `## Authentication / OAuth bypass`
  - L60 `## Race conditions`
  - L65 `## Business-logic flaws`
  - L70 `## Email / header injection`
  - L74 `## Money-stealing`
  - L78 `## Miscellaneous`
  - L83 `## How to use this skill`
  - L92 `## Source`

**Opening text:**

> --- name: bug-bounty-reference-index domain: knowledge triggers:

### `architect/skills/ci-cd-pipeline-attack.md`

- Lines: 56  Bytes: 2715

**Headings (5):**

- L12 `# CI / CD Pipeline Attack`
  - L14 `## When to load`
  - L19 `## High-impact bug classes`
  - L44 `## Recon checklist`
  - L52 `## Reporting`

**Opening text:**

> --- name: ci-cd-pipeline-attack domain: supply-chain triggers:

### `architect/skills/cloud-security.md`

- Lines: 38  Bytes: 1548

**Headings (5):**

- L10 `# Cloud Security`
  - L12 `## When to load`
  - L16 `## Key vulnerability classes`
  - L27 `## Procedure`
  - L36 `## Reporting`

**Opening text:**

> --- name: cloud-security domain: cloud triggers:

### `architect/skills/container-escape.md`

- Lines: 40  Bytes: 1545

**Headings (5):**

- L10 `# Container Escape & Isolation Bypass`
  - L12 `## When to load`
  - L15 `## Escape primitives`
  - L28 `## Procedure`
  - L37 `## Reporting`

**Opening text:**

> --- name: container-escape domain: container triggers:

### `architect/skills/cryptographic-implementation.md`

- Lines: 59  Bytes: 2744

**Headings (6):**

- L12 `# Cryptographic Implementation Bugs`
  - L14 `## When to load`
  - L18 `## Patterns that have produced real CVEs`
  - L44 `## Test harness`
  - L49 `## Cost-of-bug heuristic`
  - L56 `## Reporting`

**Opening text:**

> --- name: cryptographic-implementation domain: crypto triggers:

### `architect/skills/cryptography-attacks.md`

- Lines: 43  Bytes: 1859

**Headings (5):**

- L11 `# Cryptography Attacks`
  - L13 `## When to load`
  - L17 `## Common findings`
  - L31 `## Procedure`
  - L41 `## Reporting`

**Opening text:**

> --- name: cryptography-attacks domain: crypto triggers:

### `architect/skills/cryptography/crypto-implementation-flaws.md`

- Lines: 27  Bytes: 651

**Headings (4):**

- L9 `# crypto-implementation-flaws`
  - L13 `## Detection checklist`
  - L19 `## Exploitation primitives`
  - L24 `## Reporting fingerprint`

**Opening text:**

> --- name: crypto-implementation-flaws domain: cryptography triggers:

### `architect/skills/cryptography/key-management-flaws.md`

- Lines: 27  Bytes: 616

**Headings (4):**

- L9 `# key-management-flaws`
  - L13 `## Detection checklist`
  - L19 `## Exploitation primitives`
  - L24 `## Reporting fingerprint`

**Opening text:**

> --- name: key-management-flaws domain: cryptography triggers:

### `architect/skills/cryptography/post-quantum-migration-risks.md`

- Lines: 27  Bytes: 630

**Headings (4):**

- L9 `# post-quantum-migration-risks`
  - L13 `## Detection checklist`
  - L19 `## Exploitation primitives`
  - L24 `## Reporting fingerprint`

**Opening text:**

> --- name: post-quantum-migration-risks domain: cryptography triggers:

### `architect/skills/cryptography/rng-weakness-patterns.md`

- Lines: 27  Bytes: 615

**Headings (4):**

- L9 `# rng-weakness-patterns`
  - L13 `## Detection checklist`
  - L19 `## Exploitation primitives`
  - L24 `## Reporting fingerprint`

**Opening text:**

> --- name: rng-weakness-patterns domain: cryptography triggers:

### `architect/skills/cryptography/timing-side-channels.md`

- Lines: 27  Bytes: 604

**Headings (4):**

- L9 `# timing-side-channels`
  - L13 `## Detection checklist`
  - L19 `## Exploitation primitives`
  - L24 `## Reporting fingerprint`

**Opening text:**

> --- name: timing-side-channels domain: cryptography triggers:

### `architect/skills/cryptography/tls-ssl-attacks.md`

- Lines: 27  Bytes: 612

**Headings (4):**

- L9 `# tls-ssl-attacks`
  - L13 `## Detection checklist`
  - L19 `## Exploitation primitives`
  - L24 `## Reporting fingerprint`

**Opening text:**

> --- name: tls-ssl-attacks domain: cryptography triggers:

### `architect/skills/embedded-iot/arm-cortex-m-exploitation.md`

- Lines: 27  Bytes: 611

**Headings (4):**

- L9 `# arm-cortex-m-exploitation`
  - L13 `## Detection checklist`
  - L19 `## Exploitation primitives`
  - L24 `## Reporting fingerprint`

**Opening text:**

> --- name: arm-cortex-m-exploitation domain: embedded-iot triggers:

### `architect/skills/embedded-iot/firmware-extraction-analysis.md`

- Lines: 27  Bytes: 632

**Headings (4):**

- L9 `# firmware-extraction-analysis`
  - L13 `## Detection checklist`
  - L19 `## Exploitation primitives`
  - L24 `## Reporting fingerprint`

**Opening text:**

> --- name: firmware-extraction-analysis domain: embedded-iot triggers:

### `architect/skills/embedded-iot/iot-cloud-api-attacks.md`

- Lines: 27  Bytes: 586

**Headings (4):**

- L9 `# iot-cloud-api-attacks`
  - L13 `## Detection checklist`
  - L19 `## Exploitation primitives`
  - L24 `## Reporting fingerprint`

**Opening text:**

> --- name: iot-cloud-api-attacks domain: embedded-iot triggers:

### `architect/skills/embedded-iot/rtos-security-freertos.md`

- Lines: 27  Bytes: 612

**Headings (4):**

- L9 `# rtos-security-freertos`
  - L13 `## Detection checklist`
  - L19 `## Exploitation primitives`
  - L24 `## Reporting fingerprint`

**Opening text:**

> --- name: rtos-security-freertos domain: embedded-iot triggers:

### `architect/skills/embedded-iot/uart-jtag-debug-interfaces.md`

- Lines: 27  Bytes: 612

**Headings (4):**

- L9 `# uart-jtag-debug-interfaces`
  - L13 `## Detection checklist`
  - L19 `## Exploitation primitives`
  - L24 `## Reporting fingerprint`

**Opening text:**

> --- name: uart-jtag-debug-interfaces domain: embedded-iot triggers:

### `architect/skills/firmware-analysis.md`

- Lines: 32  Bytes: 1236

**Headings (4):**

- L10 `# Firmware Analysis`
  - L12 `## When to load`
  - L16 `## Procedure`
  - L29 `## Reporting`

**Opening text:**

> --- name: firmware-analysis domain: firmware triggers:

### `architect/skills/hardware-protocols.md`

- Lines: 37  Bytes: 1434

**Headings (5):**

- L10 `# Hardware Protocols (UART / JTAG / I2C / SPI)`
  - L12 `## When to load`
  - L16 `## Procedure`
  - L28 `## Findings`
  - L34 `## Reporting`

**Opening text:**

> --- name: hardware-protocols domain: hardware triggers:

### `architect/skills/ics-scada.md`

- Lines: 39  Bytes: 1595

**Headings (5):**

- L10 `# Industrial Control Systems (SCADA / PLC)`
  - L12 `## When to load`
  - L16 `## Protocols and known weaknesses`
  - L27 `## Procedure`
  - L35 `## Reporting`

**Opening text:**

> --- name: ics-scada domain: ics triggers:

### `architect/skills/infrastructure/aws-iam-escalation.md`

- Lines: 27  Bytes: 627

**Headings (4):**

- L9 `# aws-iam-escalation`
  - L13 `## Detection checklist`
  - L19 `## Exploitation primitives`
  - L24 `## Reporting fingerprint`

**Opening text:**

> --- name: aws-iam-escalation domain: infrastructure triggers:

### `architect/skills/infrastructure/ci-cd-pipeline-attacks.md`

- Lines: 27  Bytes: 658

**Headings (4):**

- L9 `# ci-cd-pipeline-attacks`
  - L13 `## Detection checklist`
  - L19 `## Exploitation primitives`
  - L24 `## Reporting fingerprint`

**Opening text:**

> --- name: ci-cd-pipeline-attacks domain: infrastructure triggers:

### `architect/skills/infrastructure/docker-container-escape.md`

- Lines: 27  Bytes: 655

**Headings (4):**

- L9 `# docker-container-escape`
  - L13 `## Detection checklist`
  - L19 `## Exploitation primitives`
  - L24 `## Reporting fingerprint`

**Opening text:**

> --- name: docker-container-escape domain: infrastructure triggers:

### `architect/skills/infrastructure/kubernetes-rbac-misconfig.md`

- Lines: 27  Bytes: 656

**Headings (4):**

- L9 `# kubernetes-rbac-misconfig`
  - L13 `## Detection checklist`
  - L19 `## Exploitation primitives`
  - L24 `## Reporting fingerprint`

**Opening text:**

> --- name: kubernetes-rbac-misconfig domain: infrastructure triggers:

### `architect/skills/infrastructure/secrets-in-code.md`

- Lines: 27  Bytes: 609

**Headings (4):**

- L9 `# secrets-in-code`
  - L13 `## Detection checklist`
  - L19 `## Exploitation primitives`
  - L24 `## Reporting fingerprint`

**Opening text:**

> --- name: secrets-in-code domain: infrastructure triggers:

### `architect/skills/infrastructure/supply-chain-attacks.md`

- Lines: 27  Bytes: 612

**Headings (4):**

- L9 `# supply-chain-attacks`
  - L13 `## Detection checklist`
  - L19 `## Exploitation primitives`
  - L24 `## Reporting fingerprint`

**Opening text:**

> --- name: supply-chain-attacks domain: infrastructure triggers:

### `architect/skills/languages/c-cpp-memory-safety.md`

- Lines: 27  Bytes: 637

**Headings (4):**

- L9 `# c-cpp-memory-safety`
  - L13 `## Detection checklist`
  - L19 `## Exploitation primitives`
  - L24 `## Reporting fingerprint`

**Opening text:**

> --- name: c-cpp-memory-safety domain: languages triggers:

### `architect/skills/languages/go-concurrency-races.md`

- Lines: 27  Bytes: 619

**Headings (4):**

- L9 `# go-concurrency-races`
  - L13 `## Detection checklist`
  - L19 `## Exploitation primitives`
  - L24 `## Reporting fingerprint`

**Opening text:**

> --- name: go-concurrency-races domain: languages triggers:

### `architect/skills/languages/java-security-patterns.md`

- Lines: 27  Bytes: 612

**Headings (4):**

- L9 `# java-security-patterns`
  - L13 `## Detection checklist`
  - L19 `## Exploitation primitives`
  - L24 `## Reporting fingerprint`

**Opening text:**

> --- name: java-security-patterns domain: languages triggers:

### `architect/skills/languages/javascript-node-security.md`

- Lines: 27  Bytes: 655

**Headings (4):**

- L9 `# javascript-node-security`
  - L13 `## Detection checklist`
  - L19 `## Exploitation primitives`
  - L24 `## Reporting fingerprint`

**Opening text:**

> --- name: javascript-node-security domain: languages triggers:

### `architect/skills/languages/php-security-legacy.md`

- Lines: 27  Bytes: 626

**Headings (4):**

- L9 `# php-security-legacy`
  - L13 `## Detection checklist`
  - L19 `## Exploitation primitives`
  - L24 `## Reporting fingerprint`

**Opening text:**

> --- name: php-security-legacy domain: languages triggers:

### `architect/skills/languages/python-injection-patterns.md`

- Lines: 27  Bytes: 612

**Headings (4):**

- L9 `# python-injection-patterns`
  - L13 `## Detection checklist`
  - L19 `## Exploitation primitives`
  - L24 `## Reporting fingerprint`

**Opening text:**

> --- name: python-injection-patterns domain: languages triggers:

### `architect/skills/languages/rust-unsafe-patterns.md`

- Lines: 27  Bytes: 638

**Headings (4):**

- L9 `# rust-unsafe-patterns`
  - L13 `## Detection checklist`
  - L19 `## Exploitation primitives`
  - L24 `## Reporting fingerprint`

**Opening text:**

> --- name: rust-unsafe-patterns domain: languages triggers:

### `architect/skills/languages/solidity-smart-contract.md`

- Lines: 27  Bytes: 637

**Headings (4):**

- L9 `# solidity-smart-contract`
  - L13 `## Detection checklist`
  - L19 `## Exploitation primitives`
  - L24 `## Reporting fingerprint`

**Opening text:**

> --- name: solidity-smart-contract domain: languages triggers:

### `architect/skills/linux-kernel-exploitation.md`

- Lines: 63  Bytes: 2673

**Headings (7):**

- L12 `# Linux Kernel Exploitation`
  - L14 `## When to load`
  - L18 `## Bug classes (with payout tiers)`
  - L36 `## Recon`
  - L42 `## Building the exploit`
  - L55 `## Sanitisers`
  - L60 `## Reporting (kernel.org coordinated disclosure)`

**Opening text:**

> --- name: linux-kernel-exploitation domain: kernel triggers:

### `architect/skills/llm-system-prompt-injection.md`

- Lines: 68  Bytes: 2605

**Headings (7):**

- L12 `# LLM System-Prompt & Indirect Prompt Injection`
  - L14 `## When to load`
  - L18 `## Direct prompt injection — patterns that still work`
  - L29 `## Indirect prompt injection (highest payout)`
  - L45 `## Confirmation harness (Hypothesis-style)`
  - L55 `## Exploitation impact ladder`
  - L64 `## Reporting`

**Opening text:**

> --- name: llm-system-prompt-injection domain: ai triggers:

### `architect/skills/memory-safety.md`

- Lines: 47  Bytes: 1847

**Headings (5):**

- L11 `# Memory Safety`
  - L13 `## When to load`
  - L17 `## Vulnerability classes`
  - L30 `## Procedure`
  - L45 `## Reporting`

**Opening text:**

> --- name: memory-safety domain: binary triggers:

### `architect/skills/mobile-android.md`

- Lines: 35  Bytes: 1415

**Headings (4):**

- L11 `# Android Application Security`
  - L13 `## When to load`
  - L16 `## Procedure`
  - L32 `## Reporting`

**Opening text:**

> --- name: mobile-android domain: mobile triggers:

### `architect/skills/mobile-ios.md`

- Lines: 34  Bytes: 1275

**Headings (4):**

- L11 `# iOS Application Security`
  - L13 `## When to load`
  - L16 `## Procedure`
  - L31 `## Reporting`

**Opening text:**

> --- name: mobile-ios domain: mobile triggers:

### `architect/skills/mobile/android-apk-analysis.md`

- Lines: 27  Bytes: 629

**Headings (4):**

- L9 `# android-apk-analysis`
  - L13 `## Detection checklist`
  - L19 `## Exploitation primitives`
  - L24 `## Reporting fingerprint`

**Opening text:**

> --- name: android-apk-analysis domain: mobile triggers:

### `architect/skills/mobile/ios-ipa-analysis.md`

- Lines: 27  Bytes: 605

**Headings (4):**

- L9 `# ios-ipa-analysis`
  - L13 `## Detection checklist`
  - L19 `## Exploitation primitives`
  - L24 `## Reporting fingerprint`

**Opening text:**

> --- name: ios-ipa-analysis domain: mobile triggers:

### `architect/skills/mobile/mobile-api-security.md`

- Lines: 27  Bytes: 599

**Headings (4):**

- L9 `# mobile-api-security`
  - L13 `## Detection checklist`
  - L19 `## Exploitation primitives`
  - L24 `## Reporting fingerprint`

**Opening text:**

> --- name: mobile-api-security domain: mobile triggers:

### `architect/skills/mobile/mobile-certificate-pinning-bypass.md`

- Lines: 27  Bytes: 622

**Headings (4):**

- L9 `# mobile-certificate-pinning-bypass`
  - L13 `## Detection checklist`
  - L19 `## Exploitation primitives`
  - L24 `## Reporting fingerprint`

**Opening text:**

> --- name: mobile-certificate-pinning-bypass domain: mobile triggers:

### `architect/skills/network-protocol.md`

- Lines: 38  Bytes: 1419

**Headings (5):**

- L10 `# Network-Protocol Implementation Bugs`
  - L12 `## When to load`
  - L16 `## Vulnerability classes`
  - L27 `## Procedure`
  - L36 `## Reporting`

**Opening text:**

> --- name: network-protocol domain: network triggers:

### `architect/skills/protocols/bluetooth-ble-security.md`

- Lines: 27  Bytes: 608

**Headings (4):**

- L9 `# bluetooth-ble-security`
  - L13 `## Detection checklist`
  - L19 `## Exploitation primitives`
  - L24 `## Reporting fingerprint`

**Opening text:**

> --- name: bluetooth-ble-security domain: protocols triggers:

### `architect/skills/protocols/dns-attacks-rebinding-takeover.md`

- Lines: 27  Bytes: 614

**Headings (4):**

- L9 `# dns-attacks-rebinding-takeover`
  - L13 `## Detection checklist`
  - L19 `## Exploitation primitives`
  - L24 `## Reporting fingerprint`

**Opening text:**

> --- name: dns-attacks-rebinding-takeover domain: protocols triggers:

### `architect/skills/protocols/grpc-security.md`

- Lines: 27  Bytes: 581

**Headings (4):**

- L9 `# grpc-security`
  - L13 `## Detection checklist`
  - L19 `## Exploitation primitives`
  - L24 `## Reporting fingerprint`

**Opening text:**

> --- name: grpc-security domain: protocols triggers:

### `architect/skills/protocols/http2-http3-quic-security.md`

- Lines: 27  Bytes: 577

**Headings (4):**

- L9 `# http2-http3-quic-security`
  - L13 `## Detection checklist`
  - L19 `## Exploitation primitives`
  - L24 `## Reporting fingerprint`

**Opening text:**

> --- name: http2-http3-quic-security domain: protocols triggers:

### `architect/skills/protocols/mqtt-iot-protocol.md`

- Lines: 27  Bytes: 584

**Headings (4):**

- L9 `# mqtt-iot-protocol`
  - L13 `## Detection checklist`
  - L19 `## Exploitation primitives`
  - L24 `## Reporting fingerprint`

**Opening text:**

> --- name: mqtt-iot-protocol domain: protocols triggers:

### `architect/skills/protocols/websocket-ws-wss.md`

- Lines: 27  Bytes: 569

**Headings (4):**

- L9 `# websocket-ws-wss`
  - L13 `## Detection checklist`
  - L19 `## Exploitation primitives`
  - L24 `## Reporting fingerprint`

**Opening text:**

> --- name: websocket-ws-wss domain: protocols triggers:

### `architect/skills/report-quality/cvss-scoring-guide.md`

- Lines: 27  Bytes: 641

**Headings (4):**

- L9 `# cvss-scoring-guide`
  - L13 `## Detection checklist`
  - L19 `## Exploitation primitives`
  - L24 `## Reporting fingerprint`

**Opening text:**

> --- name: cvss-scoring-guide domain: report-quality triggers:

### `architect/skills/report-quality/impact-statement-writing.md`

- Lines: 27  Bytes: 655

**Headings (4):**

- L9 `# impact-statement-writing`
  - L13 `## Detection checklist`
  - L19 `## Exploitation primitives`
  - L24 `## Reporting fingerprint`

**Opening text:**

> --- name: impact-statement-writing domain: report-quality triggers:

### `architect/skills/report-quality/p1-critical-template.md`

- Lines: 27  Bytes: 646

**Headings (4):**

- L9 `# p1-critical-template`
  - L13 `## Detection checklist`
  - L19 `## Exploitation primitives`
  - L24 `## Reporting fingerprint`

**Opening text:**

> --- name: p1-critical-template domain: report-quality triggers:

### `architect/skills/report-quality/p2-high-template.md`

- Lines: 27  Bytes: 614

**Headings (4):**

- L9 `# p2-high-template`
  - L13 `## Detection checklist`
  - L19 `## Exploitation primitives`
  - L24 `## Reporting fingerprint`

**Opening text:**

> --- name: p2-high-template domain: report-quality triggers:

### `architect/skills/report-quality/platform-specific-guides/bugcrowd-submission.md`

- Lines: 27  Bytes: 574

**Headings (4):**

- L9 `# bugcrowd-submission`
  - L13 `## Detection checklist`
  - L19 `## Exploitation primitives`
  - L24 `## Reporting fingerprint`

**Opening text:**

> --- name: bugcrowd-submission domain: report-quality triggers:

### `architect/skills/report-quality/platform-specific-guides/hackerone-submission.md`

- Lines: 27  Bytes: 635

**Headings (4):**

- L9 `# hackerone-submission`
  - L13 `## Detection checklist`
  - L19 `## Exploitation primitives`
  - L24 `## Reporting fingerprint`

**Opening text:**

> --- name: hackerone-submission domain: report-quality triggers:

### `architect/skills/report-quality/platform-specific-guides/immunefi-web3.md`

- Lines: 27  Bytes: 596

**Headings (4):**

- L9 `# immunefi-web3`
  - L13 `## Detection checklist`
  - L19 `## Exploitation primitives`
  - L24 `## Reporting fingerprint`

**Opening text:**

> --- name: immunefi-web3 domain: report-quality triggers:

### `architect/skills/report-quality/platform-specific-guides/intigriti-submission.md`

- Lines: 27  Bytes: 571

**Headings (4):**

- L9 `# intigriti-submission`
  - L13 `## Detection checklist`
  - L19 `## Exploitation primitives`
  - L24 `## Reporting fingerprint`

**Opening text:**

> --- name: intigriti-submission domain: report-quality triggers:

### `architect/skills/reverse-engineering.md`

- Lines: 31  Bytes: 1115

**Headings (4):**

- L11 `# Reverse Engineering`
  - L13 `## When to load`
  - L17 `## Procedure`
  - L28 `## Outputs`

**Opening text:**

> --- name: reverse-engineering domain: binary triggers:

### `architect/skills/reverse-engineering/binary-diffing-patch-analysis.md`

- Lines: 27  Bytes: 651

**Headings (4):**

- L9 `# binary-diffing-patch-analysis`
  - L13 `## Detection checklist`
  - L19 `## Exploitation primitives`
  - L24 `## Reporting fingerprint`

**Opening text:**

> --- name: binary-diffing-patch-analysis domain: reverse-engineering triggers:

### `architect/skills/reverse-engineering/frida-dynamic-instrumentation.md`

- Lines: 27  Bytes: 649

**Headings (4):**

- L9 `# frida-dynamic-instrumentation`
  - L13 `## Detection checklist`
  - L19 `## Exploitation primitives`
  - L24 `## Reporting fingerprint`

**Opening text:**

> --- name: frida-dynamic-instrumentation domain: reverse-engineering triggers:

### `architect/skills/reverse-engineering/ghidra-workflow.md`

- Lines: 27  Bytes: 616

**Headings (4):**

- L9 `# ghidra-workflow`
  - L13 `## Detection checklist`
  - L19 `## Exploitation primitives`
  - L24 `## Reporting fingerprint`

**Opening text:**

> --- name: ghidra-workflow domain: reverse-engineering triggers:

### `architect/skills/reverse-engineering/ida-pro-patterns.md`

- Lines: 27  Bytes: 583

**Headings (4):**

- L9 `# ida-pro-patterns`
  - L13 `## Detection checklist`
  - L19 `## Exploitation primitives`
  - L24 `## Reporting fingerprint`

**Opening text:**

> --- name: ida-pro-patterns domain: reverse-engineering triggers:

### `architect/skills/reverse-engineering/radare2-workflow.md`

- Lines: 27  Bytes: 596

**Headings (4):**

- L9 `# radare2-workflow`
  - L13 `## Detection checklist`
  - L19 `## Exploitation primitives`
  - L24 `## Reporting fingerprint`

**Opening text:**

> --- name: radare2-workflow domain: reverse-engineering triggers:

### `architect/skills/rf-radio-security.md`

- Lines: 34  Bytes: 1338

**Headings (5):**

- L10 `# RF / Radio Security`
  - L12 `## When to load`
  - L16 `## Surface`
  - L26 `## Procedure`
  - L32 `## Reporting`

**Opening text:**

> --- name: rf-radio-security domain: rf triggers:

### `architect/skills/satellite-comms.md`

- Lines: 37  Bytes: 1461

**Headings (5):**

- L10 `# Satellite Communications`
  - L12 `## When to load`
  - L17 `## Surface`
  - L27 `## Procedure`
  - L34 `## Ethics`

**Opening text:**

> --- name: satellite-comms domain: satellite triggers:

### `architect/skills/smart-contract-audit.md`

- Lines: 54  Bytes: 2691

**Headings (5):**

- L12 `# Smart-Contract Audit (EVM-first)`
  - L14 `## When to load`
  - L19 `## High-payout bug classes`
  - L41 `## Methodology`
  - L52 `## Reporting tone`

**Opening text:**

> --- name: smart-contract-audit domain: web3 triggers:

### `architect/skills/supply-chain.md`

- Lines: 43  Bytes: 1668

**Headings (5):**

- L11 `# Supply-Chain Security`
  - L13 `## When to load`
  - L17 `## Findings to hunt`
  - L33 `## Procedure`
  - L41 `## Reporting`

**Opening text:**

> --- name: supply-chain domain: supply-chain triggers:

### `architect/skills/vibe-coded-app-hunter.md`

- Lines: 137  Bytes: 6856

**Headings (11):**

- L13 `# Vibe-Coded App Hunter — The 24-Hour Hit-List`
  - L15 `## Why this skill is loaded first`
  - L26 `## The 20 Hit-List (run **every** check on **every** target, in this order)`
    - L28 `### Tier 0 — Public-surface secrets (5 minutes)`
    - L40 `### Tier 1 — Authentication primitives (15 minutes)`
    - L56 `### Tier 2 — Authorisation / IDOR (20 minutes)`
    - L69 `### Tier 3 — Injection (20 minutes)`
    - L83 `### Tier 4 — Crypto & infra (15 minutes)`
  - L106 `## Reporting template (paste into HackerOne)`
  - L120 `## How the Rhodawk pipeline uses this skill`
  - L131 `## Ethical constraints (non-negotiable)`

**Opening text:**

> --- name: vibe-coded-app-hunter domain: web priority: critical

### `architect/skills/web-security-advanced.md`

- Lines: 52  Bytes: 2412

**Headings (5):**

- L12 `# Advanced Web Security`
  - L14 `## When to load`
  - L18 `## Attack surface checklist`
  - L38 `## Procedure`
  - L50 `## Reporting`

**Opening text:**

> --- name: web-security-advanced domain: web triggers:

### `architect/skills/web/api-security-rest-graphql-grpc.md`

- Lines: 27  Bytes: 670

**Headings (4):**

- L9 `# api-security-rest-graphql-grpc`
  - L13 `## Detection checklist`
  - L19 `## Exploitation primitives`
  - L24 `## Reporting fingerprint`

**Opening text:**

> --- name: api-security-rest-graphql-grpc domain: web triggers:

### `architect/skills/web/deserialization-java.md`

- Lines: 27  Bytes: 653

**Headings (4):**

- L9 `# deserialization-java`
  - L13 `## Detection checklist`
  - L19 `## Exploitation primitives`
  - L24 `## Reporting fingerprint`

**Opening text:**

> --- name: deserialization-java domain: web triggers:

### `architect/skills/web/deserialization-python.md`

- Lines: 27  Bytes: 635

**Headings (4):**

- L9 `# deserialization-python`
  - L13 `## Detection checklist`
  - L19 `## Exploitation primitives`
  - L24 `## Reporting fingerprint`

**Opening text:**

> --- name: deserialization-python domain: web triggers:

### `architect/skills/web/graphql-security.md`

- Lines: 27  Bytes: 710

**Headings (4):**

- L9 `# graphql-security`
  - L13 `## Detection checklist`
  - L19 `## Exploitation primitives`
  - L24 `## Reporting fingerprint`

**Opening text:**

> --- name: graphql-security domain: web triggers:

### `architect/skills/web/http-request-smuggling.md`

- Lines: 27  Bytes: 633

**Headings (4):**

- L9 `# http-request-smuggling`
  - L13 `## Detection checklist`
  - L19 `## Exploitation primitives`
  - L24 `## Reporting fingerprint`

**Opening text:**

> --- name: http-request-smuggling domain: web triggers:

### `architect/skills/web/oauth2-jwt-attacks.md`

- Lines: 27  Bytes: 701

**Headings (4):**

- L9 `# oauth2-jwt-attacks`
  - L13 `## Detection checklist`
  - L19 `## Exploitation primitives`
  - L24 `## Reporting fingerprint`

**Opening text:**

> --- name: oauth2-jwt-attacks domain: web triggers:

### `architect/skills/web/owasp-top10.md`

- Lines: 27  Bytes: 719

**Headings (4):**

- L9 `# owasp-top10`
  - L13 `## Detection checklist`
  - L19 `## Exploitation primitives`
  - L24 `## Reporting fingerprint`

**Opening text:**

> --- name: owasp-top10 domain: web triggers:

### `architect/skills/web/prototype-pollution-js.md`

- Lines: 27  Bytes: 676

**Headings (4):**

- L9 `# prototype-pollution-js`
  - L13 `## Detection checklist`
  - L19 `## Exploitation primitives`
  - L24 `## Reporting fingerprint`

**Opening text:**

> --- name: prototype-pollution-js domain: web triggers:

### `architect/skills/web/ssrf-advanced.md`

- Lines: 27  Bytes: 638

**Headings (4):**

- L9 `# ssrf-advanced`
  - L13 `## Detection checklist`
  - L19 `## Exploitation primitives`
  - L24 `## Reporting fingerprint`

**Opening text:**

> --- name: ssrf-advanced domain: web triggers:

### `architect/skills/web/template-injection.md`

- Lines: 27  Bytes: 626

**Headings (4):**

- L9 `# template-injection`
  - L13 `## Detection checklist`
  - L19 `## Exploitation primitives`
  - L24 `## Reporting fingerprint`

**Opening text:**

> --- name: template-injection domain: web triggers:

### `architect/skills/web/web-cache-poisoning.md`

- Lines: 27  Bytes: 632

**Headings (4):**

- L9 `# web-cache-poisoning`
  - L13 `## Detection checklist`
  - L19 `## Exploitation primitives`
  - L24 `## Reporting fingerprint`

**Opening text:**

> --- name: web-cache-poisoning domain: web triggers:

### `architect/skills/web/websocket-security.md`

- Lines: 27  Bytes: 700

**Headings (4):**

- L9 `# websocket-security`
  - L13 `## Detection checklist`
  - L19 `## Exploitation primitives`
  - L24 `## Reporting fingerprint`

**Opening text:**

> --- name: websocket-security domain: web triggers:

### `architect/skills/web/xxe-injection.md`

- Lines: 27  Bytes: 610

**Headings (4):**

- L9 `# xxe-injection`
  - L13 `## Detection checklist`
  - L19 `## Exploitation primitives`
  - L24 `## Reporting fingerprint`

**Opening text:**

> --- name: xxe-injection domain: web triggers:

### `architect/skills/zero-day-research.md`

- Lines: 65  Bytes: 2586

**Headings (11):**

- L12 `# Zero-Day Research Methodology`
  - L14 `## When to load`
  - L18 `## Repeatable methodology`
    - L20 `### 1. CVE archaeology (cheap, high-yield)`
    - L27 `### 2. Variant hunting (the actual exploit)`
    - L35 `### 3. Differential fuzzing`
    - L41 `### 4. State-machine review`
    - L47 `### 5. Build & sanitiser farm`
    - L52 `### 6. The "what would the patch look like?" test`
  - L57 `## Scoring (decides effort)`
  - L63 `## Disclosure`

**Opening text:**

> --- name: zero-day-research domain: methodology triggers:

## `mythos/`


### `mythos/__init__.py`

- Lines: 50  Bytes: 2018

**Module docstring:**

> Rhodawk Mythos-Level Upgrade Package
> =====================================
> 
> This package implements the "Ascending to Mythos-Level" blueprint
> (see ``mythos/MYTHOS_PLAN.md``) on top of the existing Rhodawk
> EmbodiedOS / Hermes orchestration core.
> 
> Layout
> ------
> 
> mythos/
> ├── MYTHOS_PLAN.md                  – the living plan (source of truth)
> ├── agents/                         – Planner / Explorer / Executor + orchestrator
> ├── reasoning/                      – probabilistic hypothesis engine + attack graphs
> ├── static/                         – Tree-sitter, Joern, CodeQL, Semgrep bridges
> ├── dynamic/                        – AFL++, KLEE, QEMU, Frida, GDB automation
> ├── exploit/                        – Pwntools / ROPGadget / heap / privesc kits
> ├── learning/                       – RL planner, MLflow tracker, LoRA, curriculum, episodic memory
> ├── mcp/                            – static / dynamic / exploit / vuln-db / web-security MCP servers
> ├── api/                            – FastAPI productization layer
> └── skills/                         – agentskills.io standardised skill registry
> 
> Every concrete module degrades gracefully when its optional native
> dependency (Joern, KLEE, AFL++, Frida, Pyro, …) is missing — Mythos
> modules detect the absence and either fall back to a pure-Python heuristic
> or raise a clean ``MythosToolUnavailable`` so the orchestrator can route
> around the missing capability.

**Imports (1):**

- `from __future__ import annotations`

**Top-level constants (1):**

- `MYTHOS_VERSION` = `'1.0.0'`

**Classes (1):**

- `class MythosToolUnavailable(RuntimeError)` — line 42
  - _Raised when an optional native tool (Joern, KLEE, AFL++, ...) is missing._

**Top-level functions (1):**

- `def build_default_orchestrator(**kwargs)` (L46)
  - _Convenience constructor — defers heavy imports until first call._

### `mythos/__main__.py`

- Lines: 82  Bytes: 2590

**Module docstring:**

> End-to-end self-test for the Mythos package.
> 
> Run with::
> 
>     python -m mythos               # full diagnostic + sample campaign
>     python -m mythos status        # availability matrix only
>     python -m mythos campaign /path/to/repo
> 
> Exits with non-zero status if any *required* component fails to import.
> Optional native tools (Joern, AFL++, KLEE, Frida, …) are reported as
> "unavailable" but never fail the self-test.

**Imports (6):**

- `from __future__ import annotations`
- `import json`
- `import os`
- `import sys`
- `import traceback`
- `from mythos.diagnostics import availability_matrix, reasoning_check, learning_check, api_check, mcp_check`

**Top-level functions (3):**

- `def _safe(label, fn)` (L28)
- `def sample_campaign(target_repo: str | None=None) -> dict` (L35)
- `def main(argv: list[str] | None=None) -> int` (L51)

### `mythos/agents/__init__.py`

- Lines: 5  Bytes: 287

**Module docstring:**

> Mythos multi-agent framework: Planner, Explorer, Executor + Orchestrator.

**Imports (4):**

- `from .planner import PlannerAgent`
- `from .explorer import ExplorerAgent`
- `from .executor import ExecutorAgent`
- `from .orchestrator import MythosOrchestrator`

### `mythos/agents/base.py`

- Lines: 122  Bytes: 4652

**Module docstring:**

> Base agent class for the Mythos multi-agent framework.
> 
> All Mythos agents share:
>   * a ``name`` used in routing / logging
>   * a ``model_tier`` (``"tier1"`` strategy / ``"tier2"`` execution / ``"tier3"`` consensus)
>   * a tool-calling client that maps to OpenRouter / vLLM / TGI etc.
>   * a structured ``act(context)`` entry point returning a typed message

**Imports (8):**

- `from __future__ import annotations`
- `import json`
- `import logging`
- `import os`
- `import time`
- `from dataclasses import dataclass, field`
- `from typing import Any, Iterable`
- `import requests`

**Top-level constants (2):**

- `LOG` = `logging.getLogger('mythos.agent')`
- `_DEFAULT_MODELS` = `{'tier1': [os.getenv('MYTHOS_TIER1_PRIMARY', 'deepseek/deepseek-v2-chat'), os.getenv('MYTHOS_TIER1_FALLBACK', 'qwen/q...`

**Classes (2):**

- `class AgentMessage` — line 52
    - `def to_json(self) -> str` (L59)
- `class MythosAgent` — line 63
  - _Concrete agents subclass this and implement ``act()``._
    - `def __init__(self, openrouter_key: str | None=None, base_url: str | None=None)` (L69)
    - `def _call_llm(self, prompt: str, system: str='', tools: Iterable[dict] | None=None, temperature: float=0.2, max_tokens: int=2048) -> str` (L77)
      - _Tier-aware LLM invocation with automatic model fall-through._
    - `def default_system(self) -> str` (L115)
    - `def act(self, context: dict[str, Any]) -> AgentMessage` (L121)

**Top-level functions (1):**

- `def models_for_tier(tier: str) -> list[str]` (L47)

### `mythos/agents/executor.py`

- Lines: 79  Bytes: 3193

**Module docstring:**

> Executor Agent — dynamic execution, instrumentation, exploit synthesis.
> 
> Drives :mod:`mythos.dynamic` and :mod:`mythos.exploit`.  Provides crash /
> trace feedback to the Planner so the CEGIS loop can refine hypotheses.

**Imports (13):**

- `from __future__ import annotations`
- `import json`
- `from typing import Any`
- `from .base import AgentMessage, MythosAgent`
- `from ..dynamic.aflpp_runner import AFLPlusPlusRunner`
- `from ..dynamic.klee_runner import KLEERunner`
- `from ..dynamic.qemu_harness import QEMUHarness`
- `from ..dynamic.frida_instr import FridaInstrumenter`
- `from ..dynamic.gdb_automation import GDBAutomation`
- `from ..exploit.pwntools_synth import PwntoolsSynth`
- `from ..exploit.rop_chain import ROPChainBuilder`
- `from ..exploit.heap_exploit import HeapExploitKit`
- `from ..exploit.privesc_kb import PrivEscKB`

**Classes (1):**

- `class ExecutorAgent(MythosAgent)` — line 25
    - `def __init__(self, **kwargs)` (L29)
    - `def execute(self, harness_dir: str, hypotheses: list[dict[str, Any]]) -> dict[str, Any]` (L41)
    - `def act(self, context: dict[str, Any]) -> AgentMessage` (L64)

### `mythos/agents/explorer.py`

- Lines: 61  Bytes: 2486

**Module docstring:**

> Explorer Agent — deep static & semantic code analysis.
> 
> Drives the bridges in :mod:`mythos.static` (Tree-sitter, Joern, CodeQL,
> Semgrep) and feeds enriched code understanding back to the Planner.

**Imports (8):**

- `from __future__ import annotations`
- `import json`
- `from typing import Any`
- `from .base import AgentMessage, MythosAgent`
- `from ..static.treesitter_cpg import TreeSitterCPG`
- `from ..static.joern_bridge import JoernBridge`
- `from ..static.codeql_bridge import CodeQLBridge`
- `from ..static.semgrep_bridge import SemgrepBridge`

**Classes (1):**

- `class ExplorerAgent(MythosAgent)` — line 20
    - `def __init__(self, **kwargs)` (L24)
    - `def analyse(self, repo_path: str, hypotheses: list[dict[str, Any]]) -> dict[str, Any]` (L31)
    - `def act(self, context: dict[str, Any]) -> AgentMessage` (L54)

### `mythos/agents/orchestrator.py`

- Lines: 119  Bytes: 4491

**Module docstring:**

> Mythos Orchestrator — the enhanced Hermes coordinating Planner/Explorer/Executor.
> 
> Implements §5.5 of the plan.  Models the closed-loop CEGIS cycle:
> 
>     Planner → (Explorer + Executor in parallel) → Refinement → Loop
> 
> If AutoGen / CrewAI are installed they are auto-detected and used to drive
> inter-agent conversation; otherwise the orchestrator falls back to the
> deterministic in-process loop below — both produce identical dossiers so
> downstream Bounty Gateway code is unaffected.

**Imports (10):**

- `from __future__ import annotations`
- `import logging`
- `import time`
- `from typing import Any`
- `from .base import AgentMessage`
- `from .planner import PlannerAgent`
- `from .explorer import ExplorerAgent`
- `from .executor import ExecutorAgent`
- `from ..learning.episodic_memory import EpisodicMemory`
- `from ..learning.mlflow_tracker import MLflowTracker`

**Top-level constants (1):**

- `LOG` = `logging.getLogger('mythos.orchestrator')`

**Classes (1):**

- `class MythosOrchestrator` — line 30
    - `def __init__(self, planner: PlannerAgent | None=None, explorer: ExplorerAgent | None=None, executor: ExecutorAgent | None=None, max_iterations: int=3)` (L31)
    - `def _send(self, msg: AgentMessage) -> None` (L48)
    - `def run_campaign(self, target: dict[str, Any]) -> dict[str, Any]` (L54)
    - `def _refine(ctx: dict[str, Any]) -> dict[str, Any]` (L108)
    - `def _converged(iteration: dict[str, Any]) -> bool` (L117)

### `mythos/agents/planner.py`

- Lines: 86  Bytes: 3386

**Module docstring:**

> Planner Agent — strategic reasoning and hypothesis generation.
> 
> Implements §5.1 of the Mythos plan:
>   * Problem decomposition.
>   * Probabilistic hypothesis generation (delegates to
>     :mod:`mythos.reasoning.probabilistic`).
>   * Attack-graph construction.
>   * Resource allocation between Explorer and Executor.

**Imports (6):**

- `from __future__ import annotations`
- `import json`
- `from typing import Any`
- `from .base import AgentMessage, MythosAgent`
- `from ..reasoning.probabilistic import HypothesisEngine`
- `from ..reasoning.attack_graph import AttackGraph`

**Classes (1):**

- `class PlannerAgent(MythosAgent)` — line 22
    - `def __init__(self, **kwargs)` (L26)
    - `def decompose(self, target: dict[str, Any]) -> list[str]` (L31)
      - _Split a high-level engagement into ordered sub-tasks._
    - `def generate_hypotheses(self, recon: dict[str, Any]) -> list[dict[str, Any]]` (L51)
      - _Produce ranked vulnerability hypotheses with probabilistic priors._
    - `def build_attack_graph(self, hypotheses: list[dict[str, Any]]) -> AttackGraph` (L55)
    - `def allocate(self, hypotheses: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]` (L61)
      - _Decide which hypothesis goes to Explorer (static) vs Executor (dynamic)._
    - `def act(self, context: dict[str, Any]) -> AgentMessage` (L71)

### `mythos/api/__init__.py`

- Lines: 2  Bytes: 128

**Module docstring:**

> FastAPI productization layer for Mythos.

**Imports (1):**

- `from .schemas import AnalyseRequest, AnalyseResponse, WebhookEvent`

### `mythos/api/auth.py`

- Lines: 44  Bytes: 1679

**Module docstring:**

> Lightweight API-key + OAuth2 bearer authentication for the Mythos API.
> 
> Backed by an env-defined static API key (``MYTHOS_API_KEYS=key1,key2``) plus
> optional JWT validation when ``MYTHOS_JWT_PUBKEY`` is set.

**Imports (3):**

- `from __future__ import annotations`
- `import os`
- `from typing import Any`

**Top-level functions (2):**

- `def _allowed_keys() -> set[str]` (L25)
- `def require_api_key(authorization: str | None=Header(default=None)) -> dict[str, Any]` (L29)

### `mythos/api/fastapi_server.py`

- Lines: 92  Bytes: 3202

**Module docstring:**

> Mythos productization API.
> 
> Run with::
> 
>     uvicorn mythos.api.fastapi_server:app --host 0.0.0.0 --port 8000
> 
> If ``fastapi`` isn't installed (e.g. minimal HF Space build) importing this
> module is still safe — ``app`` is set to ``None`` so a deployment guard can
> detect the gap.

**Imports (9):**

- `from __future__ import annotations`
- `import logging`
- `import threading`
- `import uuid`
- `from typing import Any`
- `from .auth import require_api_key`
- `from .schemas import AnalyseRequest, AnalyseResponse, WebhookEvent`
- `from .webhooks import deliver`
- `from ..agents.orchestrator import MythosOrchestrator`

**Top-level constants (1):**

- `LOG` = `logging.getLogger('mythos.api')`

### `mythos/api/schemas.py`

- Lines: 45  Bytes: 1263

**Module docstring:**

> Pydantic schemas for the Mythos API surface.

**Imports (2):**

- `from __future__ import annotations`
- `from typing import Any`

**Classes (4):**

- `class AnalyseRequest(BaseModel)` — line 15
- `class CrashReport(BaseModel)` — line 27
- `class AnalyseResponse(BaseModel)` — line 35
- `class WebhookEvent(BaseModel)` — line 42

### `mythos/api/webhooks.py`

- Lines: 36  Bytes: 978

**Module docstring:**

> HMAC-signed webhook delivery.

**Imports (8):**

- `from __future__ import annotations`
- `import hashlib`
- `import hmac`
- `import json`
- `import os`
- `import time`
- `from typing import Any`
- `import requests`

**Top-level constants (1):**

- `_SECRET` = `os.getenv('MYTHOS_WEBHOOK_SECRET', '')`

**Top-level functions (2):**

- `def sign(payload: bytes) -> str` (L17)
- `def deliver(url: str, event: str, payload: dict[str, Any]) -> dict[str, Any]` (L24)

### `mythos/diagnostics.py`

- Lines: 97  Bytes: 4169

**Module docstring:**

> Mythos diagnostics — capability availability matrix + lightweight self-checks.
> 
> Importable from anywhere (no heavy side-effects). Used by:
>   * ``mythos.__main__`` (the ``python -m mythos`` self-test CLI)
>   * ``app.py`` (the Gradio "🜲 Mythos" tab status box)
>   * ``mythos.api.fastapi_server`` health endpoint hooks

**Imports (2):**

- `from __future__ import annotations`
- `from typing import Any`

**Top-level functions (6):**

- `def _probe(modpath: str, attr: str) -> dict[str, Any]` (L15)
- `def availability_matrix() -> dict[str, dict[str, Any]]` (L26)
  - _Return ``{component_name: {available: bool, error?: str}}``._
- `def reasoning_check() -> dict[str, Any]` (L45)
- `def learning_check() -> dict[str, Any]` (L63)
- `def api_check() -> dict[str, Any]` (L73)
- `def mcp_check() -> dict[str, Any]` (L81)

### `mythos/dynamic/__init__.py`

- Lines: 6  Bytes: 324

**Module docstring:**

> Dynamic execution + instrumentation bridges.

**Imports (5):**

- `from .aflpp_runner import AFLPlusPlusRunner`
- `from .klee_runner import KLEERunner`
- `from .qemu_harness import QEMUHarness`
- `from .frida_instr import FridaInstrumenter`
- `from .gdb_automation import GDBAutomation`

### `mythos/dynamic/aflpp_runner.py`

- Lines: 80  Bytes: 2925

**Module docstring:**

> AFL++ runner.
> 
> If ``afl-fuzz`` is on ``$PATH`` we drive a short, time-boxed campaign over
> each harness directory.  Otherwise we route through the existing
> ``fuzzing_engine`` (Hypothesis-based) so the orchestrator still produces
> crash candidates.

**Imports (8):**

- `from __future__ import annotations`
- `import glob`
- `import json`
- `import os`
- `import shutil`
- `import subprocess`
- `import time`
- `from typing import Any`

**Classes (1):**

- `class AFLPlusPlusRunner` — line 21
    - `def __init__(self, time_budget_s: int=60)` (L22)
    - `def available(self) -> bool` (L26)
    - `def run(self, harness_dir: str) -> list[dict[str, Any]]` (L29)
    - `def _signature(path: str) -> str` (L64)
    - `def _hypothesis_fallback(harness_dir: str) -> list[dict[str, Any]]` (L72)
      - _Surface a marker that the legacy fuzzing_engine will consume._

### `mythos/dynamic/frida_instr.py`

- Lines: 53  Bytes: 1623

**Module docstring:**

> Frida dynamic instrumentation — attaches a generic syscall/cred tracer.

**Imports (3):**

- `from __future__ import annotations`
- `import os`
- `from typing import Any`

**Top-level constants (1):**

- `_DEFAULT_SCRIPT` = `"\nconst interesting = ['open', 'execve', 'connect', 'recvfrom', 'mmap'];\ninteresting.forEach((name) => {\n  try {\n...`

**Classes (1):**

- `class FridaInstrumenter` — line 29
    - `def available(self) -> bool` (L30)
    - `def attach_all(self, harness_dir: str) -> list[dict[str, Any]]` (L33)

### `mythos/dynamic/gdb_automation.py`

- Lines: 55  Bytes: 1784

**Module docstring:**

> GDB-Python automation — replays a crash through GDB and captures
> backtrace, registers, and a small chunk of memory around the crash site.
> 
> When GDB is missing the function returns a structured marker so the
> orchestrator can record the gap.

**Imports (6):**

- `from __future__ import annotations`
- `import os`
- `import shutil`
- `import subprocess`
- `import tempfile`
- `from typing import Any`

**Top-level constants (1):**

- `_GDB_SCRIPT` = `'set pagination off\nset logging file {logfile}\nset logging on\nrun < {input}\nbt\ninfo registers\nx/64x $sp\nquit\n'`

**Classes (1):**

- `class GDBAutomation` — line 29
    - `def __init__(self)` (L30)
    - `def available(self) -> bool` (L33)
    - `def replay(self, crash: dict[str, Any]) -> dict[str, Any]` (L36)

### `mythos/dynamic/klee_runner.py`

- Lines: 37  Bytes: 1278

**Module docstring:**

> KLEE symbolic execution runner — emits per-path execution traces.

**Imports (6):**

- `from __future__ import annotations`
- `import glob`
- `import os`
- `import shutil`
- `import subprocess`
- `from typing import Any`

**Classes (1):**

- `class KLEERunner` — line 12
    - `def __init__(self, time_budget_s: int=120)` (L13)
    - `def available(self) -> bool` (L17)
    - `def run(self, harness_dir: str) -> list[dict[str, Any]]` (L20)

### `mythos/dynamic/qemu_harness.py`

- Lines: 38  Bytes: 1398

**Module docstring:**

> QEMU full-system emulation harness for kernel-level fuzzing experiments.

**Imports (5):**

- `from __future__ import annotations`
- `import os`
- `import shutil`
- `import subprocess`
- `from typing import Any`

**Classes (1):**

- `class QEMUHarness` — line 11
    - `def __init__(self)` (L12)
    - `def available(self) -> bool` (L15)
    - `def run(self, harness_dir: str) -> list[dict[str, Any]]` (L18)

### `mythos/exploit/__init__.py`

- Lines: 5  Bytes: 248

**Module docstring:**

> Exploit synthesis primitives.

**Imports (4):**

- `from .pwntools_synth import PwntoolsSynth`
- `from .rop_chain import ROPChainBuilder`
- `from .heap_exploit import HeapExploitKit`
- `from .privesc_kb import PrivEscKB`

### `mythos/exploit/heap_exploit.py`

- Lines: 53  Bytes: 1803

**Module docstring:**

> Heap exploitation kit — produces target-allocator-aware spray templates.
> 
> Supports glibc ptmalloc2 (default), tcache, jemalloc, and a generic
> fallback.  The Executor uses the resulting template as a starting point for
> GDB+GEF-driven manual confirmation.

**Imports (2):**

- `from __future__ import annotations`
- `from typing import Any`

**Top-level constants (1):**

- `_TEMPLATES` = `{'ptmalloc2': '# tcache poisoning skeleton\nfor i in range(7):\n    free(allocate({size}))\nfree(target_chunk)\noverw...`

**Classes (1):**

- `class HeapExploitKit` — line 43
    - `def spray_template(self, crash: dict[str, Any]) -> dict[str, Any]` (L44)

### `mythos/exploit/privesc_kb.py`

- Lines: 38  Bytes: 1837

**Module docstring:**

> Privilege-escalation knowledge base — codifies LinPEAS / WinPEAS heuristics
> into structured suggestions the Executor can verify automatically.

**Imports (2):**

- `from __future__ import annotations`
- `from typing import Any`

**Top-level constants (2):**

- `_LINUX_VECTORS` = `[{'id': 'suid-binaries', 'cmd': 'find / -perm -4000 -type f 2>/dev/null'}, {'id': 'writable-passwd', 'cmd': 'ls -la /...`
- `_WINDOWS_VECTORS` = `[{'id': 'service-perms', 'cmd': 'accesschk.exe -uwcqv "Authenticated Users" *'}, {'id': 'unquoted-paths', 'cmd': 'wmi...`

**Classes (1):**

- `class PrivEscKB` — line 29
    - `def suggest(self, hypotheses: list[dict[str, Any]]) -> list[dict[str, Any]]` (L30)

### `mythos/exploit/pwntools_synth.py`

- Lines: 58  Bytes: 2191

**Module docstring:**

> Pwntools-based PoC assembler.
> 
> Produces a runnable Python script for every confirmed crash that a human
> researcher (or downstream Bounty Gateway) can review and submit.  When
> ``pwntools`` isn't installed the assembler still emits a self-contained
> Python file using the standard library that demonstrates the input.

**Imports (4):**

- `from __future__ import annotations`
- `import os`
- `import textwrap`
- `from typing import Any`

**Classes (1):**

- `class PwntoolsSynth` — line 23
    - `def assemble(self, crash: dict[str, Any], rop_chain: list[str]) -> dict[str, Any]` (L24)

### `mythos/exploit/rop_chain.py`

- Lines: 56  Bytes: 1754

**Module docstring:**

> ROP chain builder — wraps ``angrop`` and ``ROPgadget`` when available, with
> an in-memory deterministic gadget registry so unit tests can exercise the
> chain logic without binary inputs.

**Imports (4):**

- `from __future__ import annotations`
- `import shutil`
- `import subprocess`
- `from typing import Any`

**Classes (1):**

- `class ROPChainBuilder` — line 21
    - `def __init__(self)` (L22)
    - `def build(self, crash: dict[str, Any]) -> list[str]` (L25)
    - `def _with_angrop(binary: str) -> list[str]` (L36)
    - `def _with_ropgadget(self, binary: str) -> list[str]` (L46)

### `mythos/integration.py`

- Lines: 27  Bytes: 843

**Module docstring:**

> Integration shim between the legacy ``hermes_orchestrator`` six-phase
> pipeline and the new Mythos multi-agent framework.
> 
> The shim is *additive*: existing Rhodawk code paths keep working unchanged.
> Callers that opt in to Mythos by setting ``RHODAWK_MYTHOS=1`` get the
> Planner/Explorer/Executor pipeline transparently.

**Imports (3):**

- `from __future__ import annotations`
- `import os`
- `from typing import Any`

**Top-level functions (2):**

- `def mythos_enabled() -> bool` (L16)
- `def maybe_run_mythos(target: dict[str, Any]) -> dict[str, Any] | None` (L20)
  - _If Mythos is enabled, run the multi-agent pipeline and return its dossier._

### `mythos/learning/__init__.py`

- Lines: 6  Bytes: 376

**Module docstring:**

> Self-improvement: RL planner, MLflow tracker, LoRA adapters, curriculum, episodic memory.

**Imports (5):**

- `from .rl_planner import RLPlanner`
- `from .mlflow_tracker import MLflowTracker`
- `from .lora_adapters import LoRAAdapterManager`
- `from .curriculum import CurriculumScheduler`
- `from .episodic_memory import EpisodicMemory`

### `mythos/learning/curriculum.py`

- Lines: 48  Bytes: 1348

**Module docstring:**

> Curriculum scheduler — orders training targets from easy → hard.
> 
> Difficulty is a weighted blend of:
>   * lines of code,
>   * dependency surface,
>   * historical success rate of similar repos.
> 
> Used by the data-flywheel to feed RL / LoRA fine-tuning with progressively
> harder workloads.

**Imports (4):**

- `from __future__ import annotations`
- `import math`
- `from dataclasses import dataclass`
- `from typing import Any`

**Classes (2):**

- `class CurriculumItem` — line 21
    - `def difficulty(self) -> float` (L28)
- `class CurriculumScheduler` — line 36
    - `def __init__(self, items: list[CurriculumItem] | None=None)` (L37)
    - `def add(self, repo: str, loc: int, dep_count: int, success: float=0.0) -> None` (L40)
    - `def next_batch(self, batch_size: int=4) -> list[CurriculumItem]` (L43)
    - `def to_dict(self) -> dict[str, Any]` (L47)

### `mythos/learning/episodic_memory.py`

- Lines: 62  Bytes: 2236

**Module docstring:**

> Episodic memory — stores complete campaign trajectories on disk so the
> Planner can retrieve "what worked last time on a similar repo".
> 
> Backed by SQLite for portability (no extra deps).  Schema mirrors the
> ``memory_engine`` patterns already in the repo.

**Imports (6):**

- `from __future__ import annotations`
- `import json`
- `import os`
- `import sqlite3`
- `import time`
- `from typing import Any`

**Top-level constants (1):**

- `_DB` = `os.getenv('MYTHOS_EPISODIC_DB', '/data/mythos/episodic.sqlite')`

**Classes (1):**

- `class EpisodicMemory` — line 20
    - `def __init__(self, path: str=_DB)` (L21)
    - `def record(self, target: dict[str, Any], iteration: dict[str, Any]) -> int` (L41)
    - `def recall(self, repo: str, limit: int=10) -> list[dict[str, Any]]` (L54)

### `mythos/learning/lora_adapters.py`

- Lines: 67  Bytes: 2186

**Module docstring:**

> LoRA / QLoRA adapter manager.
> 
> Wraps the existing ``lora_scheduler`` module and adds Mythos-specific
> versioning + A/B testing semantics.  Adapters are pinned per (cwe, target
> language) so the orchestrator can ship a specialised Tier-2 weight set per
> campaign class.

**Imports (5):**

- `from __future__ import annotations`
- `import json`
- `import os`
- `import time`
- `from typing import Any`

**Top-level constants (1):**

- `_ADAPTERS_INDEX` = `os.getenv('MYTHOS_ADAPTER_INDEX', '/data/mythos/adapters/index.json')`

**Classes (1):**

- `class LoRAAdapterManager` — line 21
    - `def __init__(self)` (L22)
    - `def register(self, name: str, *, cwe: str, *, language: str, *, base_model: str, *, weight_path: str, *, metrics: dict[str, float] | None=None) -> str` (L26)
    - `def select(self, *, cwe: str, *, language: str) -> dict[str, Any] | None` (L38)
    - `def rollback(self, name: str) -> dict[str, Any] | None` (L45)
    - `def _load(self) -> None` (L54)
    - `def _save(self) -> None` (L61)

### `mythos/learning/mlflow_tracker.py`

- Lines: 69  Bytes: 2358

**Module docstring:**

> Thin MLflow tracker — falls back to a JSONL log when MLflow is absent.

**Imports (6):**

- `from __future__ import annotations`
- `import json`
- `import os`
- `import time`
- `import uuid`
- `from typing import Any`

**Top-level constants (1):**

- `_FALLBACK_LOG` = `os.getenv('MYTHOS_MLFLOW_FALLBACK', '/data/mythos/mlflow_fallback.jsonl')`

**Classes (1):**

- `class MLflowTracker` — line 21
    - `def __init__(self, experiment: str='mythos')` (L22)
    - `def start_run(self, tags: dict[str, str] | None=None) -> str` (L30)
    - `def log_iteration(self, run_id: str, iteration: dict[str, Any]) -> None` (L42)
    - `def end_run(self, run_id: str) -> None` (L55)
    - `def _jsonl(self, payload: dict[str, Any]) -> None` (L63)

### `mythos/learning/rl_planner.py`

- Lines: 96  Bytes: 2967

**Module docstring:**

> Reinforcement-learning controller for the Planner.
> 
> Wraps Ray RLlib / Stable Baselines3 when available; otherwise exposes a
> contextual-bandit baseline that updates per-CWE arm preferences from
> campaign rewards.  This is enough to deliver measurable improvement in the
> Planner's choice of CWE focus across hundreds of campaigns.

**Imports (6):**

- `from __future__ import annotations`
- `import json`
- `import math`
- `import os`
- `import random`
- `from typing import Any`

**Top-level constants (1):**

- `_STATE_FILE` = `os.getenv('MYTHOS_RL_STATE', '/data/mythos/rl_state.json')`

**Classes (1):**

- `class RLPlanner` — line 35
  - _Contextual UCB1 over CWE arms (with PPO upgrade path)._
    - `def __init__(self)` (L38)
    - `def backend(self) -> str` (L45)
    - `def select(self, candidate_cwes: list[str]) -> str` (L52)
    - `def reward(self, cwe: str, signal: float) -> None` (L66)
    - `def explore(self, candidates: list[str], epsilon: float=0.1) -> str` (L73)
    - `def _load(self) -> None` (L80)
    - `def _save(self) -> None` (L90)

### `mythos/mcp/__init__.py`

- Lines: 1  Bytes: 57

**Module docstring:**

> Mythos-specialised Model Context Protocol servers.

### `mythos/mcp/_mcp_runtime.py`

- Lines: 71  Bytes: 2676

**Module docstring:**

> Tiny in-process MCP-compatible runtime used by every Mythos MCP server.
> 
> Real production deployments will swap this for the official ``mcp`` Python
> SDK.  Keeping a local shim means the Mythos servers can be exercised
> end-to-end inside the existing HuggingFace Space without pulling extra
> binary deps.
> 
> Wire protocol on stdio:
> 
>     >>> {"id": 1, "method": "tools/list"}
>     <<< {"id": 1, "result": [{"name": "...", "schema": {...}}]}
>     >>> {"id": 2, "method": "tools/call", "params": {"name": "...", "args": {...}}}
>     <<< {"id": 2, "result": {...}}

**Imports (5):**

- `from __future__ import annotations`
- `import json`
- `import logging`
- `import sys`
- `from typing import Any, Callable`

**Top-level constants (1):**

- `LOG` = `logging.getLogger('mythos.mcp')`

**Classes (1):**

- `class MCPServer` — line 27
    - `def __init__(self, name: str)` (L28)
    - `def tool(self, name: str, schema: dict[str, Any] | None=None)` (L32)
    - `def list_tools(self) -> list[dict[str, Any]]` (L40)
    - `def call(self, name: str, args: dict[str, Any]) -> Any` (L43)
    - `def serve_stdio(self) -> None` (L50)

### `mythos/mcp/browser_agent_mcp.py`

- Lines: 125  Bytes: 4346

**Module docstring:**

> browser-agent-mcp — Playwright-driven live browser for web app testing (§9.3).
> 
> Tools
> -----
> * ``navigate(url)``                       → headers, status, title, dom_snippet
> * ``click(selector)``                     → result
> * ``fill_form(selector, value)``          → result
> * ``intercept_requests()``                → HAR-like list of recent requests
> * ``inject_payload(selector, payload)``   → response analysis
> * ``screenshot()``                        → base64 PNG (vision-model ready)
> 
> If Playwright is unavailable we fall back to a ``requests``-based stub so the
> tool surface stays callable for unit tests and operator smoke runs.

**Imports (6):**

- `from __future__ import annotations`
- `import base64`
- `import json`
- `import os`
- `from typing import Any`
- `from ._mcp_runtime import MCPServer`

**Top-level functions (7):**

- `def _ensure_browser()` (L37)
- `def navigate(url: str) -> dict[str, Any]` (L63)
- `def click(selector: str) -> dict[str, Any]` (L82)
- `def fill_form(selector: str, value: str) -> dict[str, Any]` (L91)
- `def intercept_requests() -> dict[str, Any]` (L100)
- `def inject_payload(selector: str, payload: str) -> dict[str, Any]` (L105)
- `def screenshot() -> dict[str, Any]` (L116)

### `mythos/mcp/can_bus_mcp.py`

- Lines: 76  Bytes: 2676

**Module docstring:**

> can-bus-mcp — automotive CAN-bus + UDS (ISO 14229) wrapper (§9.2 / §7 frontier).
> 
> Uses the optional ``python-can`` package.  Without it every tool returns
> ``available=False`` so the agent can route around cleanly.

**Imports (3):**

- `from __future__ import annotations`
- `from typing import Any`
- `from ._mcp_runtime import MCPServer`

**Top-level functions (4):**

- `def _gate() -> dict[str, Any] | None` (L23)
- `def send_frame(interface: str, channel: str, arb_id: int, data_hex: str) -> dict[str, Any]` (L32)
- `def listen(interface: str, channel: str, seconds: int=5) -> dict[str, Any]` (L42)
- `def uds_request(interface: str, channel: str, arb_id: int, service_id: int, sub_function: int=-1) -> dict[str, Any]` (L60)

### `mythos/mcp/cors_analyzer_mcp.py`

- Lines: 105  Bytes: 3972

**Module docstring:**

> Mythos MCP — CORS misconfiguration analyzer.
> 
> Probes a host for the canonical CORS failure modes:
> 
>     * Origin reflection (``Access-Control-Allow-Origin: <attacker>``)
>     * ``null`` origin acceptance
>     * Wildcard with credentials (``ACAO: *`` + ``ACAC: true``)
>     * Subdomain wildcard misconfig (``*.target.com`` accepting attacker)
>     * Trailing-dot / suffix bypass (``target.com.attacker.com``)

**Imports (3):**

- `from __future__ import annotations`
- `import logging`
- `from typing import Any`

**Top-level constants (2):**

- `LOG` = `logging.getLogger('mythos.mcp.cors_analyzer')`
- `PROBE_ORIGINS` = `['https://evil.example.com', 'null', 'https://target.com.evil.example.com', 'https://eviltarget.com']`

**Top-level functions (2):**

- `def _request(host: str, origin: str) -> dict[str, str]` (L28)
- `def scan_host(host: str) -> list[dict[str, Any]]` (L42)

### `mythos/mcp/dep_confusion_mcp.py`

- Lines: 97  Bytes: 3604

**Module docstring:**

> Mythos MCP — dependency-confusion vector detector.
> 
> For every internal-looking dependency in a manifest (no ``@scope``,
> no public namespace prefix, no published version on the registry), emit a
> finding describing the registry the attacker would race against.
> 
> Supported manifests:  package.json, requirements.txt, pyproject.toml.

**Imports (6):**

- `from __future__ import annotations`
- `import json`
- `import logging`
- `import re`
- `from pathlib import Path`
- `from typing import Any`

**Top-level constants (2):**

- `LOG` = `logging.getLogger('mythos.mcp.dep_confusion')`
- `PUBLIC_HINTS` = `('@', '/')`

**Top-level functions (4):**

- `def _exists_on_pypi(name: str) -> bool` (L24)
- `def _exists_on_npm(name: str) -> bool` (L33)
- `def scan_repo(repo_path: str) -> list[dict[str, Any]]` (L42)
- `def scan_host(host: str) -> list[dict[str, Any]]` (L91)

### `mythos/mcp/dynamic_analysis_mcp.py`

- Lines: 33  Bytes: 1209

**Module docstring:**

> ``dynamic-analysis-mcp`` — AFL++, KLEE, QEMU, Frida, GDB.

**Imports (7):**

- `from __future__ import annotations`
- `from ._mcp_runtime import MCPServer`
- `from ..dynamic.aflpp_runner import AFLPlusPlusRunner`
- `from ..dynamic.klee_runner import KLEERunner`
- `from ..dynamic.qemu_harness import QEMUHarness`
- `from ..dynamic.frida_instr import FridaInstrumenter`
- `from ..dynamic.gdb_automation import GDBAutomation`

**Top-level functions (5):**

- `def afl_run(harness_dir: str)` (L21)
- `def klee_run(harness_dir: str)` (L23)
- `def qemu_run(harness_dir: str)` (L25)
- `def frida_attach(harness_dir: str)` (L27)
- `def gdb_replay(crash: dict)` (L29)

### `mythos/mcp/exploit_generation_mcp.py`

- Lines: 39  Bytes: 1090

**Module docstring:**

> ``exploit-generation-mcp`` — Pwntools + ROPGadget + heap + privesc.

**Imports (6):**

- `from __future__ import annotations`
- `from ._mcp_runtime import MCPServer`
- `from ..exploit.pwntools_synth import PwntoolsSynth`
- `from ..exploit.rop_chain import ROPChainBuilder`
- `from ..exploit.heap_exploit import HeapExploitKit`
- `from ..exploit.privesc_kb import PrivEscKB`

**Top-level functions (4):**

- `def rop_chain(crash: dict)` (L19)
- `def pwntools_assemble(crash: dict, rop_chain: list)` (L24)
- `def heap_template(crash: dict)` (L29)
- `def privesc_suggest(hypotheses: list)` (L34)

### `mythos/mcp/frida_runtime_mcp.py`

- Lines: 60  Bytes: 1814

**Module docstring:**

> frida-runtime-mcp — live Frida instrumentation sessions (§9.2).
> 
> Wraps the existing ``mythos.dynamic.frida_instr.FridaInstrumenter`` so the
> Planner can spawn → attach → run-script → detach via the standard MCP tool
> protocol.

**Imports (3):**

- `from __future__ import annotations`
- `from typing import Any`
- `from ._mcp_runtime import MCPServer`

**Top-level functions (4):**

- `def _gate() -> dict[str, Any] | None` (L26)
- `def attach(target: str, spawn: bool=False) -> dict[str, Any]` (L35)
- `def run_script(session_id: str, script: str) -> dict[str, Any]` (L43)
- `def detach(session_id: str) -> dict[str, Any]` (L52)

### `mythos/mcp/ghidra_bridge_mcp.py`

- Lines: 76  Bytes: 2910

**Module docstring:**

> ghidra-bridge-mcp — headless Ghidra analysis via subprocess (§9.2).
> 
> Uses ``analyzeHeadless`` so a GUI is never required.  Falls back to ``r2``
> (radare2) if Ghidra is unavailable, and to ``readelf`` / ``objdump`` if
> neither is present.

**Imports (8):**

- `from __future__ import annotations`
- `import json`
- `import os`
- `import shutil`
- `import subprocess`
- `import tempfile`
- `from typing import Any`
- `from ._mcp_runtime import MCPServer`

**Top-level functions (3):**

- `def _have(b: str) -> bool` (L23)
- `def analyse_binary(binary_path: str, script: str='') -> dict[str, Any]` (L28)
- `def strings(binary_path: str, min_len: int=6) -> dict[str, Any]` (L66)

### `mythos/mcp/httpx_probe_mcp.py`

- Lines: 99  Bytes: 3412

**Module docstring:**

> httpx-probe-mcp — concurrent HTTP(S) probing + tech fingerprinting (§9.2).
> 
> Native ``httpx`` (projectdiscovery) is preferred; otherwise we fall back to
> ``requests`` + a tiny header / body fingerprint.

**Imports (7):**

- `from __future__ import annotations`
- `import concurrent.futures as cf`
- `import shutil`
- `import subprocess`
- `from typing import Any`
- `import requests`
- `from ._mcp_runtime import MCPServer`

**Top-level functions (4):**

- `def _fingerprint(headers: dict[str, str], body: str) -> list[str]` (L22)
- `def _probe_one(host: str) -> dict[str, Any]` (L51)
- `def _title(body: str) -> str` (L64)
- `def probe(hosts: list[str], concurrency: int=16) -> dict[str, Any]` (L71)

### `mythos/mcp/jwt_analyzer_mcp.py`

- Lines: 177  Bytes: 5857

**Module docstring:**

> Mythos MCP — JWT analyzer.
> 
> Detects the canonical JWT failure modes against any host or token:
> 
>     * ``alg:none`` acceptance
>     * Weak HMAC secret (top-N wordlist brute force)
>     * Algorithm confusion (RS256 → HS256 with public key)
>     * Missing ``exp`` / ``nbf`` claims
>     * Sensitive claim leakage in the payload
> 
> The module is import-safe everywhere: every external dependency
> (``requests``, ``PyJWT``, ``cryptography``) is wrapped so the absence of
> any one of them downgrades coverage but never crashes the loop.

**Imports (6):**

- `from __future__ import annotations`
- `import base64`
- `import json`
- `import logging`
- `import re`
- `from typing import Any, Iterable`

**Top-level constants (3):**

- `LOG` = `logging.getLogger('mythos.mcp.jwt_analyzer')`
- `JWT_RE` = `re.compile('eyJ[a-zA-Z0-9_-]+?\\.[a-zA-Z0-9_-]+?\\.[a-zA-Z0-9_-]*')`
- `COMMON_SECRETS` = `('secret', 'password', '123456', 'changeme', 'jwt_secret', 'supersecret', 'your-256-bit-secret', 'test', 'qwerty', 'a...`

**Top-level functions (6):**

- `def _b64url_decode(part: str) -> bytes` (L34)
- `def _decode_payload(token: str) -> dict[str, Any]` (L42)
- `def _decode_header(token: str) -> dict[str, Any]` (L50)
- `def analyze_token(token: str) -> dict[str, Any]` (L58)
  - _Pure, no-IO analysis of a single JWT string._
- `def _try_weak_secret(token: str) -> str | None` (L128)
- `def scan_host(host: str) -> list[dict[str, Any]]` (L142)
  - _Hit ``host`` and look for JWTs in cookies, Authorization headers, and the body._

### `mythos/mcp/openapi_analyzer_mcp.py`

- Lines: 123  Bytes: 4271

**Module docstring:**

> Mythos MCP — OpenAPI / Swagger surface enumerator.
> 
> Given a host, find the spec, parse it, and emit:
>     * Each route + method as an attack-surface candidate
>     * Routes flagged as authenticated / unauthenticated
>     * Routes that accept arbitrary file uploads
>     * Routes with parameters that look like SQL / NoSQL / SSRF sinks

**Imports (5):**

- `from __future__ import annotations`
- `import json`
- `import logging`
- `import re`
- `from typing import Any`

**Top-level constants (3):**

- `LOG` = `logging.getLogger('mythos.mcp.openapi_analyzer')`
- `WELL_KNOWN_PATHS` = `('/openapi.json', '/openapi.yaml', '/openapi.yml', '/swagger.json', '/swagger.yaml', '/swagger.yml', '/v1/openapi.jso...`
- `SUSPICIOUS_PARAMS` = `(('url', 'ssrf'), ('redirect', 'open-redirect'), ('callback', 'open-redirect'), ('file', 'lfi'), ('path', 'lfi'), ('t...`

**Top-level functions (3):**

- `def _fetch_spec(base: str) -> tuple[str, dict[str, Any]] | None` (L40)
- `def analyze_spec(spec: dict[str, Any]) -> list[dict[str, Any]]` (L66)
- `def scan_host(host: str) -> list[dict[str, Any]]` (L108)

### `mythos/mcp/prototype_pollution_mcp.py`

- Lines: 69  Bytes: 2556

**Module docstring:**

> Mythos MCP — JS prototype-pollution surface scan.
> 
> Static AST-style detection: greps a repo for the canonical sinks:
> 
>     * Object.assign(target, untrustedUserInput)
>     * Lodash _.merge / _.set / _.defaultsDeep with user input
>     * jQuery $.extend(true, target, untrusted)
>     * Recursive ``for..in`` copy without ``hasOwnProperty`` guard
> 
> Output is a list of "candidate" sinks for the LLM to triage; the noise rate
> is high, so callers downstream apply consensus before filing.

**Imports (5):**

- `from __future__ import annotations`
- `import logging`
- `import re`
- `from pathlib import Path`
- `from typing import Any`

**Top-level constants (1):**

- `LOG` = `logging.getLogger('mythos.mcp.prototype_pollution')`

**Top-level functions (2):**

- `def scan_repo(repo_path: str) -> list[dict[str, Any]]` (L32)
- `def scan_host(host: str) -> list[dict[str, Any]]` (L63)

### `mythos/mcp/reconnaissance_mcp.py`

- Lines: 195  Bytes: 7158

**Module docstring:**

> reconnaissance-mcp — Mythos recon MCP server (§4.6 of MYTHOS_PLAN.md).
> 
> Exposes language / framework / dependency / attack-surface fingerprinting as
> MCP tools so the Planner agent can call them via the standard tool bus
> instead of importing the helpers directly.
> 
> Tools
> -----
> 
> * ``fingerprint_repo``       — language + framework + build-system summary
> * ``enumerate_dependencies`` — manifest parsers (pyproject, package.json, go.mod, Cargo.toml)
> * ``map_attack_surface``     — heuristic surface (HTTP routes, CLI entry-points, deserialisers)
> 
> The server boots cleanly even when no recon target is on disk; every tool
> returns ``{"available": False, "reason": "..."}`` instead of raising.

**Imports (7):**

- `from __future__ import annotations`
- `import json`
- `import os`
- `import re`
- `from pathlib import Path`
- `from typing import Any`
- `from ._mcp_runtime import MCPServer`

**Top-level constants (2):**

- `_LANG_HINTS` = `{'python': ['.py', 'pyproject.toml', 'requirements.txt', 'setup.py', 'Pipfile'], 'javascript': ['.js', '.mjs', '.cjs'...`
- `_FRAMEWORK_HINTS` = `{'django': ['manage.py', 'settings.py'], 'flask': ['from flask import', 'Flask('], 'fastapi': ['from fastapi import',...`

**Top-level functions (5):**

- `def _scan(root: Path) -> dict[str, Any]` (L59)
- `def fingerprint_repo(path: str) -> dict[str, Any]` (L74)
- `def enumerate_dependencies(path: str) -> dict[str, Any]` (L108)
- `def map_attack_surface(path: str) -> dict[str, Any]` (L161)
- `def main() -> None` (L190)

### `mythos/mcp/scope_parser_mcp.py`

- Lines: 160  Bytes: 5951

**Module docstring:**

> scope-parser-mcp — HackerOne / Bugcrowd / Intigriti scope ingestion (§5.2).
> 
> Pulls active programs from each platform, applies the operator's hard filters
> (P1/P2 only, ≥ $1k cash bounty, no everything-out-of-scope programs), and
> returns a normalised list ready for the night-mode scheduler to consume.
> 
> Environment:
>     HACKERONE_USERNAME, HACKERONE_API_TOKEN
>     BUGCROWD_API_TOKEN
>     INTIGRITI_API_TOKEN
>     YESWEHACK_API_TOKEN
>     ARCHITECT_MIN_BOUNTY_USD  (default 1000)

**Imports (7):**

- `from __future__ import annotations`
- `import json`
- `import logging`
- `import os`
- `from typing import Any`
- `import requests`
- `from ._mcp_runtime import MCPServer`

**Top-level constants (1):**

- `LOG` = `logging.getLogger('mythos.mcp.scope_parser')`

**Top-level functions (9):**

- `def _min_bounty() -> int` (L31)
- `def _h1_programs() -> list[dict[str, Any]]` (L36)
- `def _h1_normalise(p: dict[str, Any]) -> dict[str, Any] | None` (L54)
- `def _bc_programs() -> list[dict[str, Any]]` (L74)
- `def _bc_normalise(p: dict[str, Any]) -> dict[str, Any] | None` (L92)
- `def _intigriti_programs() -> list[dict[str, Any]]` (L104)
- `def _intigriti_normalise(p: dict[str, Any]) -> dict[str, Any]` (L121)
- `def list_active_programs(platforms: list[str] | None=None) -> dict[str, Any]` (L132)
- `def parse_scope_text(raw_text: str, platform: str='manual') -> dict[str, Any]` (L147)
  - _Extract URLs / domains / IPs from a pasted policy / scope page._

### `mythos/mcp/sdr_analysis_mcp.py`

- Lines: 74  Bytes: 2913

**Module docstring:**

> sdr-analysis-mcp — GNU Radio scripted RF analysis (§9.2 / §7 frontier).
> 
> Drives ``gr-fosphor`` / ``rtl_sdr`` / ``hackrf_transfer`` style binaries via
> subprocess.  Without any SDR tooling on PATH every tool returns
> ``available=False``.

**Imports (6):**

- `from __future__ import annotations`
- `import shutil`
- `import subprocess`
- `import tempfile`
- `from typing import Any`
- `from ._mcp_runtime import MCPServer`

**Top-level functions (3):**

- `def _have(b: str) -> bool` (L21)
- `def capture_iq(freq_hz: int, sample_rate_hz: int=2400000, duration_s: int=5) -> dict[str, Any]` (L27)
  - _Capture an IQ sample to a temp file. Returns metadata + path._
- `def run_grc_flowgraph(flowgraph_py: str) -> dict[str, Any]` (L56)
  - _Execute a generated GNU Radio flowgraph. Caller is responsible for_

### `mythos/mcp/shodan_mcp.py`

- Lines: 55  Bytes: 1435

**Module docstring:**

> shodan-mcp — passive recon via the Shodan REST API (§9.2).
> 
> Tools: ``host_info(ip)``, ``search(query)``, ``count(query)``.
> Falls back to ``{"available": False}`` when ``SHODAN_API_KEY`` is unset.

**Imports (5):**

- `from __future__ import annotations`
- `import os`
- `from typing import Any`
- `import requests`
- `from ._mcp_runtime import MCPServer`

**Top-level constants (1):**

- `BASE` = `'https://api.shodan.io'`

**Top-level functions (5):**

- `def _key() -> str` (L21)
- `def _get(path: str, **params) -> dict[str, Any]` (L25)
- `def host_info(ip: str) -> dict[str, Any]` (L40)
- `def search(query: str, page: int=1) -> dict[str, Any]` (L45)
- `def count(query: str) -> dict[str, Any]` (L50)

### `mythos/mcp/skill_selector_mcp.py`

- Lines: 64  Bytes: 2083

**Module docstring:**

> Mythos MCP — semantic skill selector exposed as an MCP-compatible service.
> 
> Wraps :mod:`architect.skill_selector` so any LLM tool-call can ask:
> 
>     selector.select(task=..., languages=[...], phase=...) -> str
> 
> The MCP runtime lazy-loads this module via ``python -m
> mythos.mcp.skill_selector_mcp``; when invoked from the CLI it reads JSON
> from stdin and writes JSON to stdout, making it trivially scriptable from
> shell / orchestrator code.

**Imports (5):**

- `from __future__ import annotations`
- `import json`
- `import logging`
- `import sys`
- `from typing import Any`

**Top-level constants (1):**

- `LOG` = `logging.getLogger('mythos.mcp.skill_selector')`

**Top-level functions (2):**

- `def select(task: str, *, languages: list[str] | None=None, *, tech: list[str] | None=None, *, phase: str='static', *, top_k: int=5, *, pin: list[str] | None=None) -> dict[str, Any]` (L24)
- `def main() -> int` (L43)
  - _JSON-in / JSON-out CLI for orchestrator integration._

### `mythos/mcp/static_analysis_mcp.py`

- Lines: 39  Bytes: 1215

**Module docstring:**

> ``static-analysis-mcp`` — Joern + CodeQL + Semgrep + Tree-sitter.

**Imports (6):**

- `from __future__ import annotations`
- `from ._mcp_runtime import MCPServer`
- `from ..static.joern_bridge import JoernBridge`
- `from ..static.codeql_bridge import CodeQLBridge`
- `from ..static.semgrep_bridge import SemgrepBridge`
- `from ..static.treesitter_cpg import TreeSitterCPG`

**Top-level functions (4):**

- `def cpg_summary(repo_path: str)` (L19)
- `def joern_query(repo_path: str, hypotheses: list)` (L24)
- `def codeql_query(repo_path: str, hypotheses: list)` (L29)
- `def semgrep_scan(repo_path: str, hypotheses: list)` (L34)

### `mythos/mcp/subdomain_enum_mcp.py`

- Lines: 74  Bytes: 2322

**Module docstring:**

> subdomain-enum-mcp — subfinder + amass + dnsx + crt.sh enumeration (§9.2).
> 
> When the native binaries are not available we fall back to certificate
> transparency (crt.sh JSON) which gives a respectable subdomain list with
> zero local tooling.

**Imports (7):**

- `from __future__ import annotations`
- `import json`
- `import shutil`
- `import subprocess`
- `from typing import Any`
- `import requests`
- `from ._mcp_runtime import MCPServer`

**Top-level functions (3):**

- `def _native(tool: str, target: str) -> list[str]` (L23)
- `def _crtsh(target: str) -> list[str]` (L42)
- `def enumerate(target: str, passive_only: bool=True) -> dict[str, Any]` (L59)

### `mythos/mcp/vulnerability_database_mcp.py`

- Lines: 58  Bytes: 1777

**Module docstring:**

> ``vulnerability-database-mcp`` — NVD / OSV / Exploit-DB lookup.
> 
> Uses the existing ``cve_intel`` module when available, plus public OSV
> JSON for unauthenticated queries.

**Imports (4):**

- `from __future__ import annotations`
- `from typing import Any`
- `import requests`
- `from ._mcp_runtime import MCPServer`

**Top-level functions (3):**

- `def osv_query(package: str, ecosystem: str='PyPI', version: str='') -> dict[str, Any]` (L20)
- `def nvd_cve(cve_id: str) -> dict[str, Any]` (L33)
- `def exploit_db_search(q: str) -> dict[str, Any]` (L45)

### `mythos/mcp/wayback_mcp.py`

- Lines: 48  Bytes: 1531

**Module docstring:**

> wayback-mcp — Wayback Machine + URLScan historical-URL miner (§9.2).

**Imports (5):**

- `from __future__ import annotations`
- `import os`
- `from typing import Any`
- `import requests`
- `from ._mcp_runtime import MCPServer`

**Top-level functions (2):**

- `def snapshots(domain: str, limit: int=5000) -> dict[str, Any]` (L18)
- `def urlscan_search(query: str) -> dict[str, Any]` (L32)

### `mythos/mcp/web_security_mcp.py`

- Lines: 53  Bytes: 1666

**Module docstring:**

> ``web-security-mcp`` — bridges OWASP ZAP / sqlmap / nuclei.
> 
> When the binary isn't on ``$PATH`` we return a structured "unavailable"
> result so the agent can fall back to the existing ``web-security-mcp``
> heuristics in ``mcp_config.json``.

**Imports (5):**

- `from __future__ import annotations`
- `import shutil`
- `import subprocess`
- `from typing import Any`
- `from ._mcp_runtime import MCPServer`

**Top-level functions (4):**

- `def _runtool(cmd: list[str], timeout: int=120) -> dict[str, Any]` (L20)
- `def zap_baseline(target: str)` (L34)
- `def nuclei_scan(target: str, templates: str='')` (L39)
- `def sqlmap_quick(target: str)` (L47)

### `mythos/reasoning/__init__.py`

- Lines: 3  Bytes: 166

**Module docstring:**

> Probabilistic reasoning + attack-graph utilities.

**Imports (2):**

- `from .probabilistic import HypothesisEngine`
- `from .attack_graph import AttackGraph`

### `mythos/reasoning/attack_graph.py`

- Lines: 80  Bytes: 3169

**Module docstring:**

> Attack-graph construction for the Planner.
> 
> Nodes  = hypotheses or intermediate states (e.g. "leaked-pointer", "RCE").
> Edges  = exploitation transitions weighted by the joint probability of the
>          pair occurring in the same code-base + the cost of the chain.
> 
> Falls back to a tiny pure-Python adjacency-list when ``networkx`` is absent
> so the orchestrator works in minimal images.

**Imports (2):**

- `from __future__ import annotations`
- `from typing import Any`

**Classes (1):**

- `class AttackGraph` — line 36
    - `def __init__(self)` (L37)
    - `def add_hypothesis(self, h: dict[str, Any]) -> None` (L42)
    - `def connect(self) -> None` (L48)
    - `def critical_paths(self, top: int=3) -> list[list[str]]` (L56)
    - `def to_dict(self) -> dict[str, Any]` (L75)

### `mythos/reasoning/probabilistic.py`

- Lines: 157  Bytes: 6064

**Module docstring:**

> Hypothesis Engine — probabilistic reasoning over vulnerability hypotheses.
> 
> Implements §4.1 of the Mythos plan.  Uses Pyro / PyMC when available, falls
> back to a transparent NumPy Bayesian update otherwise so the engine is
> always usable inside a HuggingFace Space without GPU acceleration.
> 
> The engine maintains per-CWE prior probabilities and updates them with
> evidence collected by the Explorer/Executor agents — this is the
> ``confidence`` value the Planner uses for resource allocation.

**Imports (5):**

- `from __future__ import annotations`
- `import math`
- `import random`
- `from dataclasses import dataclass, field`
- `from typing import Any`

**Classes (2):**

- `class Hypothesis` — line 68
    - `def to_dict(self) -> dict[str, Any]` (L75)
- `class HypothesisEngine` — line 79
  - _Bayesian-flavoured generator of ranked vulnerability hypotheses._
    - `def __init__(self, seed: int | None=None)` (L82)
    - `def sample(self, recon: dict[str, Any], n: int=8) -> list[dict[str, Any]]` (L88)
      - _Return the top-``n`` hypotheses for a recon snapshot._
    - `def update_with_outcome(self, cwe: str, *, success: bool) -> None` (L103)
      - _Online refinement: bump or decay a prior after a campaign result._
    - `def _bayes_update(prior: float, log_lift: float) -> float` (L114)
      - _Combine a base prior with a log-odds evidence boost._
    - `def _boosts_from_recon(recon: dict[str, Any]) -> dict[str, float]` (L123)
      - _Translate recon hints (languages, deps, frameworks) into log-odds boosts._
    - `def _rationale(cwe: str, recon: dict[str, Any], posterior: float) -> str` (L142)
    - `def backend(self) -> str` (L152)

### `mythos/skills/__init__.py`

- Lines: 2  Bytes: 132

**Module docstring:**

> Standardised skill registry following the ``agentskills.io`` schema.

**Imports (1):**

- `from .registry import SkillRegistry, Skill`

### `mythos/skills/registry.py`

- Lines: 122  Bytes: 4363

**Module docstring:**

> agentskills.io-compatible skill registry.
> 
> Skills are JSON documents persisted to disk and indexed by name; the Hermes
> agent populates this registry from successful campaign trajectories so the
> Mythos orchestrator can compose them at planning time.

**Imports (6):**

- `from __future__ import annotations`
- `import json`
- `import os`
- `import time`
- `from dataclasses import dataclass, field, asdict`
- `from typing import Any`

**Top-level constants (1):**

- `_REGISTRY_DIR` = `os.getenv('MYTHOS_SKILLS_DIR', '/data/mythos/skills')`

**Classes (2):**

- `class Skill` — line 21
- `class SkillRegistry` — line 32
    - `def __init__(self, root: str=_REGISTRY_DIR)` (L33)
    - `def add(self, skill: Skill) -> str` (L38)
    - `def get(self, name: str) -> Skill | None` (L44)
    - `def list(self, tag: str | None=None) -> list[Skill]` (L52)
    - `def _seed_default(self) -> None` (L63)

### `mythos/static/__init__.py`

- Lines: 5  Bytes: 296

**Module docstring:**

> Advanced static analysis bridges (Tree-sitter, Joern, CodeQL, Semgrep).

**Imports (4):**

- `from .treesitter_cpg import TreeSitterCPG`
- `from .joern_bridge import JoernBridge`
- `from .codeql_bridge import CodeQLBridge`
- `from .semgrep_bridge import SemgrepBridge`

### `mythos/static/codeql_bridge.py`

- Lines: 69  Bytes: 2700

**Module docstring:**

> CodeQL bridge — runs the open-source CodeQL CLI against a target repo.
> 
> The bridge:
>   * detects the ``codeql`` binary on ``$PATH``;
>   * creates a database for the repo (auto-detects language);
>   * runs the bundled QL pack matching each hypothesis kind;
>   * returns parsed SARIF results.
> 
> When CodeQL is missing the bridge returns an empty list rather than
> crashing — the Explorer's other backends provide partial coverage.

**Imports (7):**

- `from __future__ import annotations`
- `import json`
- `import os`
- `import shutil`
- `import subprocess`
- `import tempfile`
- `from typing import Any`

**Top-level constants (1):**

- `_PACK_FOR_KIND` = `{'validation': 'codeql/python-queries:Security/CWE-079/ReflectedXss.ql', 'memory': 'codeql/cpp-queries:Security/CWE-1...`

**Classes (1):**

- `class CodeQLBridge` — line 33
    - `def __init__(self)` (L34)
    - `def available(self) -> bool` (L37)
    - `def query(self, repo_path: str, hypotheses: list[dict[str, Any]]) -> list[dict[str, Any]]` (L40)

### `mythos/static/joern_bridge.py`

- Lines: 93  Bytes: 3109

**Module docstring:**

> Joern Code Property Graph bridge.
> 
> Joern ships as a JVM CLI.  This bridge is a thin, robust subprocess wrapper
> that:
> 
>   1. Detects the ``joern`` binary on ``$PATH`` (or ``$JOERN_HOME/bin``).
>   2. Imports a target codebase (``importCode``).
>   3. Runs hypothesis-driven CPG queries (taint, call-chains, dataflow).
>   4. Returns parsed JSON results.
> 
> If Joern is not installed the bridge raises ``MythosToolUnavailable`` so the
> orchestrator transparently routes around it.

**Imports (8):**

- `from __future__ import annotations`
- `import json`
- `import os`
- `import shutil`
- `import subprocess`
- `import tempfile`
- `from typing import Any`
- `from .. import MythosToolUnavailable`

**Classes (1):**

- `class JoernBridge` — line 46
    - `def __init__(self, joern_home: str | None=None)` (L47)
    - `def available(self) -> bool` (L54)
    - `def query(self, repo_path: str, hypotheses: list[dict[str, Any]]) -> list[dict[str, Any]]` (L57)
    - `def _run_query(self, repo_path: str, query: str, kind: str) -> list[dict[str, Any]]` (L69)
    - `def require(self) -> None` (L91)

### `mythos/static/semgrep_bridge.py`

- Lines: 55  Bytes: 1933

**Module docstring:**

> Semgrep bridge — wraps the existing Semgrep dependency declared in
> ``requirements.txt`` and exposes a hypothesis-driven scan API.
> 
> Falls back to ``semgrep --config=auto`` when no kind-specific config is
> matched, and gracefully returns ``[]`` when the binary is unavailable.

**Imports (5):**

- `from __future__ import annotations`
- `import json`
- `import shutil`
- `import subprocess`
- `from typing import Any`

**Top-level constants (1):**

- `_KIND_CONFIG` = `{'validation': 'p/owasp-top-ten', 'memory': 'p/cwe-top-25', 'auth': 'p/security-audit', 'logic': 'p/default'}`

**Classes (1):**

- `class SemgrepBridge` — line 24
    - `def __init__(self)` (L25)
    - `def available(self) -> bool` (L28)
    - `def scan(self, repo_path: str, hypotheses: list[dict[str, Any]]) -> list[dict[str, Any]]` (L31)

### `mythos/static/treesitter_cpg.py`

- Lines: 80  Bytes: 3268

**Module docstring:**

> Tree-sitter based Concrete Syntax Tree → lightweight CPG summary.
> 
> When ``tree_sitter_languages`` is installed we walk the CST per file and
> emit per-language stats (function count, max nesting depth, dangerous-call
> hits).  Otherwise we degrade to a regex-based scanner that is good enough
> for the planner's first-cut prioritisation.

**Imports (5):**

- `from __future__ import annotations`
- `import os`
- `import re`
- `from collections import defaultdict`
- `from typing import Any`

**Top-level constants (2):**

- `EXT_LANG` = `{'.py': 'python', '.js': 'javascript', '.ts': 'typescript', '.c': 'c', '.h': 'c', '.cc': 'cpp', '.cpp': 'cpp', '.hpp'...`
- `DANGEROUS_PATTERNS` = `{'python': ['\\beval\\(', '\\bexec\\(', 'pickle\\.loads\\(', 'yaml\\.load\\(', 'subprocess\\..*shell\\s*=\\s*True'], ...`

**Classes (1):**

- `class TreeSitterCPG` — line 42
    - `def __init__(self)` (L43)
    - `def summary(self, repo_path: str) -> dict[str, Any]` (L46)

## `openclaude_grpc/`


### `openclaude_grpc/__init__.py`

- Lines: 21  Bytes: 550

**Module docstring:**

> openclaude_grpc — Python bridge to the vendored OpenClaude headless gRPC daemon.
> 
> Public surface:
>     OpenClaudeClient       — low-level bidi-streaming client
>     run_openclaude         — drop-in replacement for the legacy ``run_aider``
>                               function (returns ``(combined_output, exit_code)``)

**Imports (1):**

- `from .client import OpenClaudeClient, OpenClaudeError, OpenClaudeResult, run_openclaude`

### `openclaude_grpc/client.py`

- Lines: 348  Bytes: 13474

**Module docstring:**

> OpenClaude gRPC client — replaces the legacy aider subprocess shell-out.
> 
> Design contract
> ---------------
> Every callable in this module returns an :class:`OpenClaudeResult` (or the
> ``(combined_output, exit_code)`` tuple that legacy callers expect) so that the
> existing validation, SAST gate, conviction engine, and red-team loops keep
> plugging in unchanged.
> 
> Streaming events from the daemon (text chunks, tool start/result, action
> required) are accumulated into a single transcript so that downstream code
> that previously parsed aider stdout still sees a useful blob.
> 
> Operational guarantees
> ----------------------
> * Connection drops, ``StatusCode.UNAVAILABLE`` and stream-level RPC errors
>   are converted into a non-zero exit code with the error message embedded in
>   the combined output (mirrors aider's crash semantics).
> * Per-call wall-clock timeout (defaults to 600 s) — same as the legacy
>   aider invocation.
> * Bidi stream auto-answers any ``ActionRequired`` prompt with ``"y"`` so that
>   headless mode never deadlocks waiting for human input. The daemon also
>   honours ``OPENCLAUDE_AUTO_APPROVE=1`` server-side as a belt-and-braces.
> * Each call produces a fresh stream — sessions are not shared across calls
>   to keep failures isolated.

**Imports (11):**

- `from __future__ import annotations`
- `import logging`
- `import os`
- `import queue`
- `import threading`
- `import time`
- `from dataclasses import dataclass, field`
- `from typing import Iterable, Optional`
- `import grpc`
- `from . import openclaude_pb2 as pb`
- `from . import openclaude_pb2_grpc as pb_grpc`

**Top-level constants (4):**

- `DEFAULT_HOST` = `os.getenv('OPENCLAUDE_GRPC_HOST', '127.0.0.1')`
- `DEFAULT_PORT_DO` = `int(os.getenv('OPENCLAUDE_GRPC_PORT_DO', '50051'))`
- `DEFAULT_PORT_OR` = `int(os.getenv('OPENCLAUDE_GRPC_PORT_OR', '50052'))`
- `DEFAULT_TIMEOUT` = `int(os.getenv('OPENCLAUDE_TIMEOUT', '600'))`

**Classes (3):**

- `class OpenClaudeError(RuntimeError)` — line 51
  - _Raised for unrecoverable client-side errors (connect, decode, etc)._
- `class OpenClaudeResult` — line 56
  - _Mirror of the legacy aider return contract._
    - `def combined_output(self) -> str` (L74)
    - `def as_legacy_tuple(self) -> tuple[str, int]` (L79)
- `class OpenClaudeClient` — line 83
  - _Bidirectional-streaming client for one OpenClaude daemon._
    - `def __init__(self, host: str=DEFAULT_HOST, port: int=DEFAULT_PORT_DO, timeout: int=DEFAULT_TIMEOUT, max_message_mb: int=64) -> None` (L86)
    - `def wait_ready(self, deadline_s: float=60.0) -> bool` (L109)
      - _Block until the daemon's gRPC channel is READY or the deadline_
    - `def chat(self, message: str, working_directory: str, model: str='', session_id: str='', timeout: Optional[int]=None) -> OpenClaudeResult` (L127)
      - _Send one prompt, drain the bidi stream, return an aggregated_
    - `def close(self) -> None` (L237)
    - `def __enter__(self) -> 'OpenClaudeClient'` (L243)
    - `def __exit__(self, *exc) -> None` (L246)

**Top-level functions (2):**

- `def _format_prompt(prompt: str, context_files: list[str]) -> str` (L253)
  - _Aider received context files as CLI args; OpenClaude gets them_
- `def run_openclaude(mcp_config_path: str, prompt: str, context_files: list[str], *, repo_dir: str, *, primary_port: int=DEFAULT_PORT_DO, *, fallback_port: int=DEFAULT_PORT_OR, *, primary_label: str='DigitalOcean', *, fallback_label: str='OpenRouter', *, primary_model: str='', *, fallback_model: str='', *, timeout: int=DEFAULT_TIMEOUT, *, log_fn=None) -> tuple[str, int]` (L267)
  - _Drop-in replacement for ``run_aider`` — preserves the_

## `pitch_deck/`


### `pitch_deck/Rhodawk_AI_Pitch_Deck_2026.pdf`

- **Binary asset.** Size: 13264 bytes.

### `pitch_deck/Rhodawk_AI_Pitch_Deck_2026.pptx`

- **Binary asset.** Size: 1394267 bytes.

## `scripts/`


### `scripts/generate_stubs.sh`

- Lines: 52  Bytes: 1971

```bash
#!/usr/bin/env bash
# ============================================================================
# Rhodawk AI — Local gRPC Stub Generator
# ----------------------------------------------------------------------------
# Resolves W-001 (CRITICAL): the openclaude_grpc/openclaude_pb2.py and
# openclaude_grpc/openclaude_pb2_grpc.py files are NOT committed to source
# (they are generated at Docker build time). This script generates them
# locally so app.py can be imported and run without a full Docker build.
#
# Usage:
#   bash scripts/generate_stubs.sh
#
# Requirements:
#   pip install grpcio-tools
# ============================================================================
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PROTO_DIR="${REPO_ROOT}/vendor/openclaude/src/proto"
OUT_DIR="${REPO_ROOT}/openclaude_grpc"

if [ ! -f "${PROTO_DIR}/openclaude.proto" ]; then
    echo "[generate_stubs] ERROR: ${PROTO_DIR}/openclaude.proto not found." >&2
    echo "[generate_stubs] The vendor/openclaude submodule may be missing." >&2
    exit 1
fi

if ! python -c "import grpc_tools" 2>/dev/null; then
    echo "[generate_stubs] ERROR: grpcio-tools not installed." >&2
    echo "[generate_stubs] Run: pip install grpcio-tools" >&2
    exit 1
fi

mkdir -p "${OUT_DIR}"

echo "[generate_stubs] Generating Python gRPC stubs..."
python -m grpc_tools.protoc \
    -I "${PROTO_DIR}" \
    --python_out="${OUT_DIR}" \
    --grpc_python_out="${OUT_DIR}" \
    "${PROTO_DIR}/openclaude.proto"

# Patch the generated _grpc.py to use a relative import so it works as a
# package module (the protoc default emits an absolute import).
GRPC_FILE="${OUT_DIR}/openclaude_pb2_grpc.py"
if [ -f "${GRPC_FILE}" ]; then
    sed -i.bak 's/^import openclaude_pb2 as openclaude__pb2$/from . import openclaude_pb2 as openclaude__pb2/' "${GRPC_FILE}"
    rm -f "${GRPC_FILE}.bak"
fi

echo "[generate_stubs] Done. Generated:"
ls -la "${OUT_DIR}"/openclaude_pb2*.py

```

## `skills/`


### `skills/rhodawk/add-target.md`

- Lines: 12  Bytes: 299

**Headings (3):**

- L1 `# add-target`
  - L7 `## Trigger phrases`
  - L10 `## Output contract`

**Opening text:**

> **Summary:** Add a bounty target to tonight's queue

### `skills/rhodawk/approve-finding.md`

- Lines: 12  Bytes: 301

**Headings (3):**

- L1 `# approve-finding`
  - L7 `## Trigger phrases`
  - L10 `## Output contract`

**Opening text:**

> **Summary:** Approve and submit a finding

### `skills/rhodawk/explain-finding.md`

- Lines: 12  Bytes: 299

**Headings (3):**

- L1 `# explain-finding`
  - L7 `## Trigger phrases`
  - L10 `## Output contract`

**Opening text:**

> **Summary:** Plain-English description

### `skills/rhodawk/night-report.md`

- Lines: 12  Bytes: 342

**Headings (3):**

- L1 `# night-report`
  - L7 `## Trigger phrases`
  - L10 `## Output contract`

**Opening text:**

> **Summary:** Morning briefing template

### `skills/rhodawk/pause-hunting.md`

- Lines: 12  Bytes: 268

**Headings (3):**

- L1 `# pause-hunting`
  - L7 `## Trigger phrases`
  - L10 `## Output contract`

**Opening text:**

> **Summary:** Pause Night Hunter

### `skills/rhodawk/scan-repo.md`

- Lines: 12  Bytes: 321

**Headings (3):**

- L1 `# scan-repo`
  - L7 `## Trigger phrases`
  - L10 `## Output contract`

**Opening text:**

> **Summary:** Scan a repository

### `skills/rhodawk/status.md`

- Lines: 12  Bytes: 278

**Headings (3):**

- L1 `# status`
  - L7 `## Trigger phrases`
  - L10 `## Output contract`

**Opening text:**

> **Summary:** System status

## `tests/`


### `tests/__init__.py`

- Lines: 0  Bytes: 0

### `tests/conftest.py`

- Lines: 33  Bytes: 945

**Module docstring:**

> Shared pytest fixtures for the ARCHITECT / Rhodawk test suite.

**Imports (6):**

- `from __future__ import annotations`
- `import os`
- `import sys`
- `import tempfile`
- `from pathlib import Path`
- `import pytest`

**Top-level constants (1):**

- `ROOT` = `Path(__file__).resolve().parent.parent`

**Top-level functions (2):**

- `def tmp_data_dir(monkeypatch)` (L19)
  - _Redirect /data writes into an isolated temp dir for the test._
- `def fresh_budget(monkeypatch)` (L29)
  - _Reset the model-router budget between tests._

### `tests/test_audit_chain.py`

- Lines: 47  Bytes: 1590

**Module docstring:**

> Audit-chain integrity smoke tests.

**Imports (5):**

- `from __future__ import annotations`
- `import json`
- `import os`
- `import tempfile`
- `import pytest`

**Top-level functions (1):**

- `def test_audit_logger_chains_hashes(tmp_data_dir, monkeypatch)` (L12)
  - _Every appended event must reference the previous event's SHA-256._

### `tests/test_job_queue.py`

- Lines: 30  Bytes: 1036

**Module docstring:**

> Job-queue smoke test — enqueue → status → done.

**Imports (3):**

- `from __future__ import annotations`
- `import importlib`
- `import pytest`

**Top-level functions (1):**

- `def test_enqueue_and_status(tmp_data_dir, monkeypatch)` (L10)

### `tests/test_mcp_servers_load.py`

- Lines: 37  Bytes: 1100

**Module docstring:**

> All ARCHITECT / Mythos MCP servers must import cleanly and expose tools.

**Imports (3):**

- `from __future__ import annotations`
- `import importlib`
- `import pytest`

**Top-level constants (1):**

- `MCP_MODULES` = `['mythos.mcp.static_analysis_mcp', 'mythos.mcp.dynamic_analysis_mcp', 'mythos.mcp.exploit_generation_mcp', 'mythos.mc...`

**Top-level functions (1):**

- `def test_mcp_module_imports_and_exposes_tools(mod)` (L30)

### `tests/test_model_router.py`

- Lines: 31  Bytes: 1166

**Module docstring:**

> ARCHITECT model-router unit tests.

**Imports (1):**

- `from __future__ import annotations`

**Top-level functions (4):**

- `def test_default_routes_present(fresh_budget)` (L6)
- `def test_route_returns_known_model(fresh_budget)` (L14)
- `def test_budget_caps_force_local_fallback(fresh_budget)` (L20)
- `def test_caller_preferred_overrides(fresh_budget)` (L28)

### `tests/test_mythos_diagnostics.py`

- Lines: 35  Bytes: 1147

**Module docstring:**

> Mythos diagnostics smoke tests.

**Imports (1):**

- `from __future__ import annotations`

**Top-level functions (4):**

- `def test_availability_matrix_has_all_components()` (L6)
- `def test_mcp_check_lists_all_servers()` (L14)
- `def test_reasoning_check_returns_graph()` (L20)
- `def test_embodied_bridge_channels_default_off()` (L27)
  - _With no env vars set every channel must report unwired (no exceptions)._

### `tests/test_nightmode_smoke.py`

- Lines: 25  Bytes: 931

**Module docstring:**

> Night-mode scheduler — smoke runs the report phase only.

**Imports (1):**

- `from __future__ import annotations`

**Top-level functions (2):**

- `def test_phase_report_filters_by_acts_gate(monkeypatch)` (L6)
- `def test_run_one_cycle_with_no_targets_does_not_crash(monkeypatch)` (L19)

### `tests/test_scope_parser.py`

- Lines: 32  Bytes: 1088

**Module docstring:**

> Scope-parser MCP tests — text parsing path (no network).

**Imports (1):**

- `from __future__ import annotations`

**Top-level functions (2):**

- `def test_parse_scope_text_extracts_assets()` (L6)
- `def test_list_active_programs_no_creds_returns_empty()` (L23)
  - _With no credentials the tool must return empty programs gracefully._

### `tests/test_skill_registry.py`

- Lines: 36  Bytes: 1239

**Module docstring:**

> ARCHITECT skill-registry tests.

**Imports (1):**

- `from __future__ import annotations`

**Top-level functions (4):**

- `def test_load_all_returns_phase1_minimum()` (L6)
- `def test_match_picks_web_for_python_flask_target()` (L16)
- `def test_render_skill_pack_yields_markdown()` (L25)
- `def test_stats_reports_total()` (L33)

### `tests/test_webhook_hmac.py`

- Lines: 56  Bytes: 1618

**Module docstring:**

> Webhook HMAC verification smoke test.

**Imports (6):**

- `from __future__ import annotations`
- `import hashlib`
- `import hmac`
- `import json`
- `import os`
- `import pytest`

**Top-level functions (3):**

- `def _signature(secret: str, body: bytes) -> str` (L13)
- `def test_hmac_verify_accepts_valid(monkeypatch)` (L17)
- `def test_hmac_verify_rejects_bogus(monkeypatch)` (L39)

---

# Part II — Vendored & Built-Artifact Files (catalog)

The `vendor/` tree contains third-party / forked codebases bundled into the repo. The `pitch-deck/` directory is the **built** output of a Vite/React deck (the source lives elsewhere; only the production bundle is committed). For these, every file is listed below with size and line count, so the inventory is complete; per-line documentation of third-party code is not duplicated here.


### `pitch-deck/` (5 files)

| File | Bytes | Lines |
|---|---:|---:|
| `README.md` | 207 | 12 |
| `favicon.svg` | 163 | 3 |
| `hero-cover.png` | 1713901 | 6620 |
| `hero-solution.png` | 1320406 | 4862 |
| `index.html` | 1355 | 32 |

### `pitch-deck/assets/` (2 files)

| File | Bytes | Lines |
|---|---:|---:|
| `index-DLD4Ktjk.js` | 314460 | 11 |
| `index-NAq_mMiz.css` | 23658 | 1 |

### `vendor/clientside_bugs/` (2 files)

| File | Bytes | Lines |
|---|---:|---:|
| `LICENSE` | 1071 | 21 |
| `RESOURCES.md` | 6191 | 84 |

### `vendor/galaxy_bugbounty/` (1 files)

| File | Bytes | Lines |
|---|---:|---:|
| `README.md` | 604 | 16 |

### `vendor/galaxy_bugbounty/2fa_bypass/` (1 files)

| File | Bytes | Lines |
|---|---:|---:|
| `README.md` | 2738 | 98 |

### `vendor/galaxy_bugbounty/account_takeover/` (1 files)

| File | Bytes | Lines |
|---|---:|---:|
| `README.md` | 373 | 18 |

### `vendor/galaxy_bugbounty/api_security/` (1 files)

| File | Bytes | Lines |
|---|---:|---:|
| `README.md` | 2643 | 58 |

### `vendor/galaxy_bugbounty/broken_access_control/` (1 files)

| File | Bytes | Lines |
|---|---:|---:|
| `README.md` | 6879 | 146 |

### `vendor/galaxy_bugbounty/crlf_injection/` (1 files)

| File | Bytes | Lines |
|---|---:|---:|
| `README.md` | 5537 | 153 |

### `vendor/galaxy_bugbounty/csrf_bypass/` (1 files)

| File | Bytes | Lines |
|---|---:|---:|
| `README.md` | 545 | 12 |

### `vendor/galaxy_bugbounty/dos/` (1 files)

| File | Bytes | Lines |
|---|---:|---:|
| `README.md` | 13276 | 183 |

### `vendor/galaxy_bugbounty/file_upload/` (1 files)

| File | Bytes | Lines |
|---|---:|---:|
| `README.md` | 14302 | 277 |

### `vendor/galaxy_bugbounty/http_request_smuggling/` (1 files)

| File | Bytes | Lines |
|---|---:|---:|
| `README.md` | 4389 | 95 |

### `vendor/galaxy_bugbounty/internet_information_services_iis/` (1 files)

| File | Bytes | Lines |
|---|---:|---:|
| `README.md` | 8107 | 181 |

### `vendor/galaxy_bugbounty/log4shell/` (1 files)

| File | Bytes | Lines |
|---|---:|---:|
| `README.md` | 14326 | 377 |

### `vendor/galaxy_bugbounty/oauth/` (1 files)

| File | Bytes | Lines |
|---|---:|---:|
| `README.md` | 156 | 2 |

### `vendor/galaxy_bugbounty/open_redirect/` (1 files)

| File | Bytes | Lines |
|---|---:|---:|
| `README.md` | 6610 | 113 |

### `vendor/galaxy_bugbounty/osint/` (1 files)

| File | Bytes | Lines |
|---|---:|---:|
| `README.md` | 1 | 1 |

### `vendor/galaxy_bugbounty/parameter_pollution/` (1 files)

| File | Bytes | Lines |
|---|---:|---:|
| `README.md` | 4876 | 161 |

### `vendor/galaxy_bugbounty/rate_limit_bypass/` (1 files)

| File | Bytes | Lines |
|---|---:|---:|
| `README.md` | 2644 | 66 |

### `vendor/galaxy_bugbounty/reset_password_vulnerabilities/` (1 files)

| File | Bytes | Lines |
|---|---:|---:|
| `README.md` | 12130 | 253 |

### `vendor/galaxy_bugbounty/sensitive_data_exposure/` (2 files)

| File | Bytes | Lines |
|---|---:|---:|
| `README.MD` | 2005 | 29 |
| `cyspadSniper.txt` | 84108 | 6038 |

### `vendor/galaxy_bugbounty/sql_injection/` (2 files)

| File | Bytes | Lines |
|---|---:|---:|
| `README.md` | 2280 | 60 |
| `SQL.txt` | 8404 | 377 |

### `vendor/galaxy_bugbounty/ssrf/` (1 files)

| File | Bytes | Lines |
|---|---:|---:|
| `README.md` | 20130 | 324 |

### `vendor/galaxy_bugbounty/web_cache_deception/` (1 files)

| File | Bytes | Lines |
|---|---:|---:|
| `README.md` | 2077 | 44 |

### `vendor/galaxy_bugbounty/wordpress/` (1 files)

| File | Bytes | Lines |
|---|---:|---:|
| `README.md` | 15830 | 351 |

### `vendor/galaxy_bugbounty/xss_payloads/` (1 files)

| File | Bytes | Lines |
|---|---:|---:|
| `README.md` | 5735 | 166 |

### `vendor/openclaude/` (17 files)

| File | Bytes | Lines |
|---|---:|---:|
| `.dockerignore` | 143 | 16 |
| `.env.example` | 15071 | 374 |
| `.gitignore` | 161 | 14 |
| `.release-please-manifest.json` | 19 | 3 |
| `ANDROID_INSTALL.md` | 4011 | 162 |
| `CHANGELOG.md` | 22391 | 176 |
| `CODE_OF_CONDUCT.md` | 5289 | 126 |
| `CONTRIBUTING.md` | 2904 | 119 |
| `Dockerfile` | 1086 | 46 |
| `LICENSE` | 1228 | 29 |
| `PLAYBOOK.md` | 6642 | 322 |
| `README.md` | 12025 | 345 |
| `SECURITY.md` | 1991 | 69 |
| `bun.lock` | 189238 | 1602 |
| `package.json` | 5812 | 162 |
| `release-please-config.json` | 284 | 11 |
| `tsconfig.json` | 498 | 22 |

### `vendor/openclaude/bin/` (3 files)

| File | Bytes | Lines |
|---|---:|---:|
| `import-specifier.mjs` | 410 | 13 |
| `import-specifier.test.mjs` | 338 | 13 |
| `openclaude` | 705 | 32 |

### `vendor/openclaude/docs/` (6 files)

| File | Bytes | Lines |
|---|---:|---:|
| `advanced-setup.md` | 7986 | 273 |
| `hook-chains.md` | 10141 | 333 |
| `litellm-setup.md` | 4879 | 144 |
| `non-technical-setup.md` | 2204 | 116 |
| `quick-start-mac-linux.md` | 2585 | 143 |
| `quick-start-windows.md` | 2621 | 143 |

### `vendor/openclaude/python/` (5 files)

| File | Bytes | Lines |
|---|---:|---:|
| `__init__.py` | 64 | 1 |
| `atomic_chat_provider.py` | 5294 | 146 |
| `ollama_provider.py` | 6635 | 173 |
| `requirements.txt` | 52 | 3 |
| `smart_router.py` | 15028 | 387 |

### `vendor/openclaude/python/tests/` (5 files)

| File | Bytes | Lines |
|---|---:|---:|
| `__init__.py` | 58 | 1 |
| `conftest.py` | 177 | 5 |
| `test_atomic_chat_provider.py` | 4658 | 130 |
| `test_ollama_provider.py` | 6428 | 192 |
| `test_smart_router.py` | 7978 | 231 |

### `vendor/openclaude/scripts/` (16 files)

| File | Bytes | Lines |
|---|---:|---:|
| `build.ts` | 21247 | 492 |
| `grpc-cli.ts` | 3732 | 121 |
| `no-telemetry-growthbook-stub.test.ts` | 7419 | 163 |
| `no-telemetry-plugin.ts` | 23881 | 459 |
| `pr-intent-scan.test.ts` | 4245 | 136 |
| `pr-intent-scan.ts` | 11317 | 453 |
| `provider-bootstrap.ts` | 5951 | 195 |
| `provider-discovery.ts` | 321 | 13 |
| `provider-launch.ts` | 8027 | 255 |
| `provider-recommend.ts` | 6699 | 265 |
| `render-coverage-heatmap.ts` | 10880 | 393 |
| `start-grpc.ts` | 2786 | 83 |
| `system-check.test.ts` | 1867 | 59 |
| `system-check.ts` | 21555 | 691 |
| `verify-no-phone-home.sh` | 967 | 50 |
| `verify-no-phone-home.ts` | 1150 | 47 |

### `vendor/openclaude/src/` (21 files)

| File | Bytes | Lines |
|---|---:|---:|
| `QueryEngine.ts` | 47181 | 1309 |
| `Task.ts` | 3119 | 124 |
| `Tool.ts` | 30130 | 807 |
| `commands.test.ts` | 768 | 30 |
| `commands.ts` | 25650 | 767 |
| `context.ts` | 6456 | 189 |
| `cost-tracker.ts` | 10817 | 327 |
| `costHook.ts` | 617 | 22 |
| `dialogLaunchers.tsx` | 6248 | 132 |
| `history.ts` | 14081 | 464 |
| `ink.ts` | 3887 | 85 |
| `interactiveHelpers.tsx` | 17168 | 374 |
| `main.tsx` | 232728 | 4668 |
| `projectOnboardingState.test.ts` | 2149 | 62 |
| `projectOnboardingState.ts` | 1411 | 47 |
| `projectOnboardingSteps.ts` | 1263 | 44 |
| `query.ts` | 74322 | 1838 |
| `replLauncher.tsx` | 813 | 22 |
| `setup.ts` | 18722 | 438 |
| `tasks.ts` | 1355 | 39 |
| `tools.ts` | 16712 | 376 |

### `vendor/openclaude/src/__tests__/` (3 files)

| File | Bytes | Lines |
|---|---:|---:|
| `bugfixes.test.ts` | 11453 | 290 |
| `providerCounts.test.ts` | 1499 | 55 |
| `security-hardening.test.ts` | 8170 | 191 |

### `vendor/openclaude/src/assistant/` (2 files)

| File | Bytes | Lines |
|---|---:|---:|
| `AssistantSessionChooser.tsx` | 244 | 10 |
| `sessionHistory.ts` | 2503 | 87 |

### `vendor/openclaude/src/bootstrap/` (1 files)

| File | Bytes | Lines |
|---|---:|---:|
| `state.ts` | 54749 | 1731 |

### `vendor/openclaude/src/bridge/` (33 files)

| File | Bytes | Lines |
|---|---:|---:|
| `bridgeApi.ts` | 18066 | 539 |
| `bridgeConfig.ts` | 1579 | 41 |
| `bridgeDebug.ts` | 4926 | 135 |
| `bridgeEnabled.ts` | 8447 | 202 |
| `bridgeMain.ts` | 115304 | 2992 |
| `bridgeMessaging.ts` | 15703 | 461 |
| `bridgePermissionCallbacks.ts` | 1411 | 43 |
| `bridgePointer.ts` | 7611 | 210 |
| `bridgeStatusUtil.ts` | 5143 | 163 |
| `bridgeUI.ts` | 16780 | 530 |
| `capacityWake.ts` | 1841 | 56 |
| `codeSessionApi.ts` | 4840 | 168 |
| `createSession.ts` | 12810 | 398 |
| `debugUtils.ts` | 4240 | 141 |
| `envLessBridgeConfig.ts` | 7250 | 165 |
| `flushGate.ts` | 1981 | 71 |
| `inboundAttachments.ts` | 6267 | 175 |
| `inboundMessages.ts` | 2727 | 80 |
| `initReplBridge.ts` | 23756 | 566 |
| `jwtUtils.ts` | 9444 | 256 |
| `pollConfig.ts` | 4562 | 110 |
| `pollConfigDefaults.ts` | 4018 | 82 |
| `remoteBridgeCore.ts` | 39439 | 1008 |
| `replBridge.ts` | 100542 | 2406 |
| `replBridgeHandle.ts` | 1473 | 36 |
| `replBridgeTransport.ts` | 15523 | 370 |
| `sessionIdCompat.ts` | 2536 | 57 |
| `sessionRunner.test.ts` | 2809 | 85 |
| `sessionRunner.ts` | 19254 | 601 |
| `trustedDevice.ts` | 7781 | 210 |
| `types.ts` | 10161 | 262 |
| `workSecret.test.ts` | 1330 | 36 |
| `workSecret.ts` | 4700 | 127 |

### `vendor/openclaude/src/buddy/` (8 files)

| File | Bytes | Lines |
|---|---:|---:|
| `CompanionSprite.tsx` | 12191 | 370 |
| `companion.ts` | 3715 | 133 |
| `feature.ts` | 60 | 3 |
| `observer.ts` | 1657 | 65 |
| `prompt.ts` | 1460 | 36 |
| `sprites.ts` | 9797 | 514 |
| `types.ts` | 3805 | 148 |
| `useBuddyNotification.tsx` | 2684 | 97 |

### `vendor/openclaude/src/cli/` (6 files)

| File | Bytes | Lines |
|---|---:|---:|
| `exit.ts` | 1310 | 31 |
| `ndjsonSafeStringify.ts` | 1408 | 32 |
| `print.ts` | 212604 | 5584 |
| `remoteIO.ts` | 9946 | 255 |
| `structuredIO.ts` | 28719 | 859 |
| `update.ts` | 15128 | 436 |

### `vendor/openclaude/src/cli/handlers/` (6 files)

| File | Bytes | Lines |
|---|---:|---:|
| `agents.ts` | 2089 | 70 |
| `auth.ts` | 10756 | 330 |
| `autoMode.ts` | 5706 | 169 |
| `mcp.tsx` | 18565 | 459 |
| `plugins.ts` | 31073 | 878 |
| `util.tsx` | 3849 | 109 |

### `vendor/openclaude/src/cli/transports/` (7 files)

| File | Bytes | Lines |
|---|---:|---:|
| `HybridTransport.ts` | 10883 | 282 |
| `SSETransport.ts` | 23758 | 711 |
| `SerialBatchEventUploader.ts` | 9089 | 275 |
| `WebSocketTransport.ts` | 28195 | 800 |
| `WorkerStateUploader.ts` | 3879 | 131 |
| `ccrClient.ts` | 33775 | 998 |
| `transportUtils.ts` | 1767 | 45 |

### `vendor/openclaude/src/commands/` (19 files)

| File | Bytes | Lines |
|---|---:|---:|
| `advisor.ts` | 3182 | 109 |
| `auto-fix.ts` | 1016 | 25 |
| `benchmark.ts` | 1554 | 56 |
| `bridge-kick.ts` | 6703 | 200 |
| `brief.ts` | 5173 | 130 |
| `commit-push-pr.ts` | 6322 | 158 |
| `commit.ts` | 3492 | 92 |
| `createMovedToPluginCommand.ts` | 1789 | 65 |
| `init-verifiers.ts` | 10315 | 262 |
| `init.test.ts` | 1300 | 43 |
| `init.ts` | 21024 | 250 |
| `initMode.ts` | 298 | 13 |
| `insights.ts` | 106808 | 2932 |
| `install.tsx` | 10535 | 299 |
| `review.ts` | 2188 | 57 |
| `security-review.ts` | 12531 | 243 |
| `statusline.tsx` | 904 | 23 |
| `ultraplan.tsx` | 20042 | 470 |
| `version.ts` | 577 | 22 |

### `vendor/openclaude/src/commands/add-dir/` (3 files)

| File | Bytes | Lines |
|---|---:|---:|
| `add-dir.tsx` | 4825 | 125 |
| `index.ts` | 260 | 11 |
| `validation.ts` | 3207 | 110 |

### `vendor/openclaude/src/commands/agents/` (2 files)

| File | Bytes | Lines |
|---|---:|---:|
| `agents.tsx` | 580 | 11 |
| `index.ts` | 232 | 10 |

### `vendor/openclaude/src/commands/agents-platform/` (1 files)

| File | Bytes | Lines |
|---|---:|---:|
| `index.ts` | 28 | 2 |

### `vendor/openclaude/src/commands/ant-trace/` (1 files)

| File | Bytes | Lines |
|---|---:|---:|
| `index.js` | 73 | 1 |

### `vendor/openclaude/src/commands/assistant/` (2 files)

| File | Bytes | Lines |
|---|---:|---:|
| `AssistantSessionChooser.ts` | 28 | 2 |
| `assistant.ts` | 82 | 2 |

### `vendor/openclaude/src/commands/autofix-pr/` (1 files)

| File | Bytes | Lines |
|---|---:|---:|
| `index.js` | 73 | 1 |

### `vendor/openclaude/src/commands/backfill-sessions/` (1 files)

| File | Bytes | Lines |
|---|---:|---:|
| `index.js` | 73 | 1 |

### `vendor/openclaude/src/commands/branch/` (2 files)

| File | Bytes | Lines |
|---|---:|---:|
| `branch.ts` | 9580 | 296 |
| `index.ts` | 445 | 14 |

### `vendor/openclaude/src/commands/break-cache/` (1 files)

| File | Bytes | Lines |
|---|---:|---:|
| `index.js` | 73 | 1 |

### `vendor/openclaude/src/commands/bridge/` (2 files)

| File | Bytes | Lines |
|---|---:|---:|
| `bridge.tsx` | 13927 | 508 |
| `index.ts` | 604 | 26 |

### `vendor/openclaude/src/commands/btw/` (2 files)

| File | Bytes | Lines |
|---|---:|---:|
| `btw.tsx` | 8298 | 242 |
| `index.ts` | 314 | 13 |

### `vendor/openclaude/src/commands/buddy/` (2 files)

| File | Bytes | Lines |
|---|---:|---:|
| `buddy.tsx` | 4629 | 185 |
| `index.ts` | 314 | 12 |

### `vendor/openclaude/src/commands/bughunter/` (1 files)

| File | Bytes | Lines |
|---|---:|---:|
| `index.js` | 73 | 1 |

### `vendor/openclaude/src/commands/cache-probe/` (2 files)

| File | Bytes | Lines |
|---|---:|---:|
| `cache-probe.ts` | 13584 | 413 |
| `index.ts` | 535 | 17 |

### `vendor/openclaude/src/commands/chrome/` (2 files)

| File | Bytes | Lines |
|---|---:|---:|
| `chrome.tsx` | 9302 | 284 |
| `index.ts` | 381 | 13 |

### `vendor/openclaude/src/commands/clear/` (4 files)

| File | Bytes | Lines |
|---|---:|---:|
| `caches.ts` | 6370 | 144 |
| `clear.ts` | 254 | 7 |
| `conversation.ts` | 9325 | 251 |
| `index.ts` | 603 | 19 |

### `vendor/openclaude/src/commands/color/` (2 files)

| File | Bytes | Lines |
|---|---:|---:|
| `color.ts` | 2712 | 93 |
| `index.ts` | 417 | 16 |

### `vendor/openclaude/src/commands/compact/` (2 files)

| File | Bytes | Lines |
|---|---:|---:|
| `compact.ts` | 10079 | 287 |
| `index.ts` | 530 | 15 |

### `vendor/openclaude/src/commands/config/` (2 files)

| File | Bytes | Lines |
|---|---:|---:|
| `config.tsx` | 316 | 6 |
| `index.ts` | 247 | 11 |

### `vendor/openclaude/src/commands/context/` (3 files)

| File | Bytes | Lines |
|---|---:|---:|
| `context-noninteractive.ts` | 10796 | 325 |
| `context.tsx` | 2659 | 63 |
| `index.ts` | 695 | 24 |

### `vendor/openclaude/src/commands/copy/` (2 files)

| File | Bytes | Lines |
|---|---:|---:|
| `copy.tsx` | 11596 | 370 |
| `index.ts` | 393 | 15 |

### `vendor/openclaude/src/commands/cost/` (2 files)

| File | Bytes | Lines |
|---|---:|---:|
| `cost.ts` | 914 | 24 |
| `index.ts` | 668 | 23 |

### `vendor/openclaude/src/commands/ctx_viz/` (1 files)

| File | Bytes | Lines |
|---|---:|---:|
| `index.js` | 73 | 1 |

### `vendor/openclaude/src/commands/debug-tool-call/` (1 files)

| File | Bytes | Lines |
|---|---:|---:|
| `index.js` | 73 | 1 |

### `vendor/openclaude/src/commands/desktop/` (2 files)

| File | Bytes | Lines |
|---|---:|---:|
| `desktop.tsx` | 345 | 8 |
| `index.ts` | 601 | 26 |

### `vendor/openclaude/src/commands/diff/` (2 files)

| File | Bytes | Lines |
|---|---:|---:|
| `diff.tsx` | 325 | 8 |
| `index.ts` | 221 | 8 |

### `vendor/openclaude/src/commands/doctor/` (2 files)

| File | Bytes | Lines |
|---|---:|---:|
| `doctor.tsx` | 273 | 6 |
| `index.ts` | 381 | 12 |

### `vendor/openclaude/src/commands/dream/` (2 files)

| File | Bytes | Lines |
|---|---:|---:|
| `dream.ts` | 2101 | 68 |
| `index.ts` | 37 | 1 |

### `vendor/openclaude/src/commands/effort/` (2 files)

| File | Bytes | Lines |
|---|---:|---:|
| `effort.tsx` | 7635 | 220 |
| `index.ts` | 428 | 13 |

### `vendor/openclaude/src/commands/env/` (1 files)

| File | Bytes | Lines |
|---|---:|---:|
| `index.js` | 73 | 1 |

### `vendor/openclaude/src/commands/exit/` (2 files)

| File | Bytes | Lines |
|---|---:|---:|
| `exit.tsx` | 1404 | 32 |
| `index.ts` | 250 | 12 |

### `vendor/openclaude/src/commands/export/` (2 files)

| File | Bytes | Lines |
|---|---:|---:|
| `export.tsx` | 3724 | 90 |
| `index.ts` | 303 | 11 |

### `vendor/openclaude/src/commands/extra-usage/` (4 files)

| File | Bytes | Lines |
|---|---:|---:|
| `extra-usage-core.ts` | 4000 | 118 |
| `extra-usage-noninteractive.ts` | 466 | 16 |
| `extra-usage.tsx` | 754 | 16 |
| `index.ts` | 1101 | 31 |

### `vendor/openclaude/src/commands/fast/` (2 files)

| File | Bytes | Lines |
|---|---:|---:|
| `fast.tsx` | 9575 | 268 |
| `index.ts` | 693 | 26 |

### `vendor/openclaude/src/commands/feedback/` (2 files)

| File | Bytes | Lines |
|---|---:|---:|
| `feedback.tsx` | 1171 | 24 |
| `index.ts` | 931 | 26 |

### `vendor/openclaude/src/commands/files/` (2 files)

| File | Bytes | Lines |
|---|---:|---:|
| `files.ts` | 688 | 19 |
| `index.ts` | 316 | 12 |

### `vendor/openclaude/src/commands/good-claude/` (1 files)

| File | Bytes | Lines |
|---|---:|---:|
| `index.js` | 73 | 1 |

### `vendor/openclaude/src/commands/heapdump/` (2 files)

| File | Bytes | Lines |
|---|---:|---:|
| `heapdump.ts` | 398 | 17 |
| `index.ts` | 288 | 12 |

### `vendor/openclaude/src/commands/help/` (2 files)

| File | Bytes | Lines |
|---|---:|---:|
| `help.tsx` | 316 | 10 |
| `index.ts` | 229 | 10 |

### `vendor/openclaude/src/commands/hooks/` (2 files)

| File | Bytes | Lines |
|---|---:|---:|
| `hooks.tsx` | 635 | 12 |
| `index.ts` | 260 | 11 |

### `vendor/openclaude/src/commands/ide/` (2 files)

| File | Bytes | Lines |
|---|---:|---:|
| `ide.tsx` | 21018 | 645 |
| `index.ts` | 258 | 11 |

### `vendor/openclaude/src/commands/install-github-app/` (16 files)

| File | Bytes | Lines |
|---|---:|---:|
| `ApiKeyStep.tsx` | 7002 | 230 |
| `CheckExistingSecretStep.tsx` | 5323 | 189 |
| `CheckGitHubStep.tsx` | 356 | 14 |
| `ChooseRepoStep.tsx` | 6155 | 210 |
| `CreatingStep.tsx` | 2550 | 64 |
| `ErrorStep.tsx` | 2326 | 84 |
| `ExistingWorkflowStep.tsx` | 2853 | 102 |
| `InstallAppStep.tsx` | 2801 | 93 |
| `OAuthFlowStep.tsx` | 10499 | 275 |
| `SuccessStep.tsx` | 2914 | 95 |
| `WarningsStep.tsx` | 2368 | 72 |
| `index.ts` | 471 | 13 |
| `install-github-app.tsx` | 24483 | 586 |
| `repoSlug.test.ts` | 1477 | 48 |
| `repoSlug.ts` | 1518 | 54 |
| `setupGitHubActions.ts` | 10168 | 325 |

### `vendor/openclaude/src/commands/install-slack-app/` (2 files)

| File | Bytes | Lines |
|---|---:|---:|
| `index.ts` | 333 | 12 |
| `install-slack-app.ts` | 877 | 30 |

### `vendor/openclaude/src/commands/issue/` (1 files)

| File | Bytes | Lines |
|---|---:|---:|
| `index.js` | 73 | 1 |

### `vendor/openclaude/src/commands/keybindings/` (2 files)

| File | Bytes | Lines |
|---|---:|---:|
| `index.ts` | 448 | 13 |
| `keybindings.ts` | 1645 | 53 |

### `vendor/openclaude/src/commands/login/` (2 files)

| File | Bytes | Lines |
|---|---:|---:|
| `index.ts` | 489 | 14 |
| `login.tsx` | 4109 | 132 |

### `vendor/openclaude/src/commands/logout/` (2 files)

| File | Bytes | Lines |
|---|---:|---:|
| `index.ts` | 341 | 10 |
| `logout.tsx` | 3004 | 81 |

### `vendor/openclaude/src/commands/mcp/` (6 files)

| File | Bytes | Lines |
|---|---:|---:|
| `addCommand.ts` | 9848 | 280 |
| `doctorCommand.test.ts` | 633 | 19 |
| `doctorCommand.ts` | 1041 | 25 |
| `index.ts` | 280 | 12 |
| `mcp.tsx` | 3182 | 84 |
| `xaaIdpCommand.ts` | 10290 | 266 |

### `vendor/openclaude/src/commands/memory/` (2 files)

| File | Bytes | Lines |
|---|---:|---:|
| `index.ts` | 220 | 10 |
| `memory.tsx` | 3444 | 89 |

### `vendor/openclaude/src/commands/mobile/` (2 files)

| File | Bytes | Lines |
|---|---:|---:|
| `index.ts` | 282 | 11 |
| `mobile.tsx` | 6209 | 273 |

### `vendor/openclaude/src/commands/mock-limits/` (1 files)

| File | Bytes | Lines |
|---|---:|---:|
| `index.js` | 73 | 1 |

### `vendor/openclaude/src/commands/model/` (3 files)

| File | Bytes | Lines |
|---|---:|---:|
| `index.ts` | 559 | 16 |
| `model.test.tsx` | 2776 | 68 |
| `model.tsx` | 12255 | 332 |

### `vendor/openclaude/src/commands/oauth-refresh/` (1 files)

| File | Bytes | Lines |
|---|---:|---:|
| `index.js` | 73 | 1 |

### `vendor/openclaude/src/commands/onboard-github/` (3 files)

| File | Bytes | Lines |
|---|---:|---:|
| `index.ts` | 382 | 12 |
| `onboard-github.test.ts` | 4820 | 148 |
| `onboard-github.tsx` | 10755 | 364 |

### `vendor/openclaude/src/commands/onboarding/` (1 files)

| File | Bytes | Lines |
|---|---:|---:|
| `index.js` | 73 | 1 |

### `vendor/openclaude/src/commands/output-style/` (2 files)

| File | Bytes | Lines |
|---|---:|---:|
| `index.ts` | 291 | 11 |
| `output-style.tsx` | 343 | 6 |

### `vendor/openclaude/src/commands/passes/` (2 files)

| File | Bytes | Lines |
|---|---:|---:|
| `index.ts` | 632 | 22 |
| `passes.tsx` | 979 | 23 |

### `vendor/openclaude/src/commands/perf-issue/` (1 files)

| File | Bytes | Lines |
|---|---:|---:|
| `index.js` | 73 | 1 |

### `vendor/openclaude/src/commands/permissions/` (2 files)

| File | Bytes | Lines |
|---|---:|---:|
| `index.ts` | 296 | 11 |
| `permissions.tsx` | 507 | 9 |

### `vendor/openclaude/src/commands/plan/` (2 files)

| File | Bytes | Lines |
|---|---:|---:|
| `index.ts` | 286 | 11 |
| `plan.tsx` | 3756 | 121 |

### `vendor/openclaude/src/commands/plugin/` (17 files)

| File | Bytes | Lines |
|---|---:|---:|
| `AddMarketplace.tsx` | 5713 | 161 |
| `BrowseMarketplace.tsx` | 31878 | 801 |
| `DiscoverPlugins.tsx` | 28450 | 780 |
| `ManageMarketplaces.tsx` | 31724 | 837 |
| `ManagePlugins.tsx` | 88819 | 2214 |
| `PluginErrors.tsx` | 6900 | 123 |
| `PluginOptionsDialog.tsx` | 10149 | 356 |
| `PluginOptionsFlow.tsx` | 5194 | 134 |
| `PluginSettings.tsx` | 34440 | 1071 |
| `PluginTrustWarning.tsx` | 1187 | 31 |
| `UnifiedInstalledCell.tsx` | 14113 | 564 |
| `ValidatePlugin.tsx` | 3513 | 97 |
| `index.tsx` | 289 | 10 |
| `parseArgs.ts` | 2818 | 103 |
| `plugin.tsx` | 338 | 6 |
| `pluginDetailsHelpers.tsx` | 3340 | 116 |
| `usePagination.ts` | 4990 | 171 |

### `vendor/openclaude/src/commands/pr_comments/` (1 files)

| File | Bytes | Lines |
|---|---:|---:|
| `index.ts` | 1848 | 50 |

### `vendor/openclaude/src/commands/privacy-settings/` (2 files)

| File | Bytes | Lines |
|---|---:|---:|
| `index.ts` | 399 | 14 |
| `privacy-settings.tsx` | 2667 | 57 |

### `vendor/openclaude/src/commands/provider/` (3 files)

| File | Bytes | Lines |
|---|---:|---:|
| `index.ts` | 241 | 10 |
| `provider.test.tsx` | 16993 | 560 |
| `provider.tsx` | 50814 | 1716 |

### `vendor/openclaude/src/commands/rate-limit-options/` (2 files)

| File | Bytes | Lines |
|---|---:|---:|
| `index.ts` | 511 | 19 |
| `rate-limit-options.tsx` | 6889 | 209 |

### `vendor/openclaude/src/commands/release-notes/` (2 files)

| File | Bytes | Lines |
|---|---:|---:|
| `index.ts` | 268 | 11 |
| `release-notes.ts` | 1524 | 50 |

### `vendor/openclaude/src/commands/reload-plugins/` (2 files)

| File | Bytes | Lines |
|---|---:|---:|
| `index.ts` | 653 | 18 |
| `reload-plugins.ts` | 2598 | 61 |

### `vendor/openclaude/src/commands/remote-env/` (2 files)

| File | Bytes | Lines |
|---|---:|---:|
| `index.ts` | 577 | 15 |
| `remote-env.tsx` | 330 | 6 |

### `vendor/openclaude/src/commands/remote-setup/` (3 files)

| File | Bytes | Lines |
|---|---:|---:|
| `api.ts` | 5519 | 182 |
| `index.ts` | 693 | 20 |
| `remote-setup.tsx` | 6090 | 186 |

### `vendor/openclaude/src/commands/rename/` (3 files)

| File | Bytes | Lines |
|---|---:|---:|
| `generateSessionName.ts` | 2297 | 67 |
| `index.ts` | 281 | 12 |
| `rename.ts` | 2759 | 87 |

### `vendor/openclaude/src/commands/reset-limits/` (1 files)

| File | Bytes | Lines |
|---|---:|---:|
| `index.js` | 172 | 4 |

### `vendor/openclaude/src/commands/resume/` (2 files)

| File | Bytes | Lines |
|---|---:|---:|
| `index.ts` | 303 | 12 |
| `resume.tsx` | 9598 | 274 |

### `vendor/openclaude/src/commands/review/` (4 files)

| File | Bytes | Lines |
|---|---:|---:|
| `UltrareviewOverageDialog.tsx` | 2547 | 95 |
| `reviewRemote.ts` | 11926 | 316 |
| `ultrareviewCommand.tsx` | 2675 | 57 |
| `ultrareviewEnabled.ts` | 526 | 14 |

### `vendor/openclaude/src/commands/rewind/` (2 files)

| File | Bytes | Lines |
|---|---:|---:|
| `index.ts` | 337 | 13 |
| `rewind.ts` | 376 | 13 |

### `vendor/openclaude/src/commands/sandbox-toggle/` (2 files)

| File | Bytes | Lines |
|---|---:|---:|
| `index.ts` | 1520 | 50 |
| `sandbox-toggle.tsx` | 3633 | 82 |

### `vendor/openclaude/src/commands/session/` (2 files)

| File | Bytes | Lines |
|---|---:|---:|
| `index.ts` | 418 | 16 |
| `session.tsx` | 3605 | 139 |

### `vendor/openclaude/src/commands/share/` (1 files)

| File | Bytes | Lines |
|---|---:|---:|
| `index.js` | 73 | 1 |

### `vendor/openclaude/src/commands/skills/` (2 files)

| File | Bytes | Lines |
|---|---:|---:|
| `index.ts` | 226 | 10 |
| `skills.tsx` | 432 | 7 |

### `vendor/openclaude/src/commands/stats/` (2 files)

| File | Bytes | Lines |
|---|---:|---:|
| `index.ts` | 252 | 10 |
| `stats.tsx` | 249 | 6 |

### `vendor/openclaude/src/commands/status/` (2 files)

| File | Bytes | Lines |
|---|---:|---:|
| `index.ts` | 322 | 12 |
| `status.tsx` | 431 | 7 |

### `vendor/openclaude/src/commands/stickers/` (2 files)

| File | Bytes | Lines |
|---|---:|---:|
| `index.ts` | 268 | 11 |
| `stickers.ts` | 476 | 16 |

### `vendor/openclaude/src/commands/summary/` (1 files)

| File | Bytes | Lines |
|---|---:|---:|
| `index.js` | 73 | 1 |

### `vendor/openclaude/src/commands/tag/` (2 files)

| File | Bytes | Lines |
|---|---:|---:|
| `index.ts` | 321 | 12 |
| `tag.tsx` | 5983 | 214 |

### `vendor/openclaude/src/commands/tasks/` (2 files)

| File | Bytes | Lines |
|---|---:|---:|
| `index.ts` | 256 | 11 |
| `tasks.tsx` | 453 | 7 |

### `vendor/openclaude/src/commands/teleport/` (1 files)

| File | Bytes | Lines |
|---|---:|---:|
| `index.js` | 73 | 1 |

### `vendor/openclaude/src/commands/terminalSetup/` (2 files)

| File | Bytes | Lines |
|---|---:|---:|
| `index.ts` | 725 | 23 |
| `terminalSetup.tsx` | 21862 | 530 |

### `vendor/openclaude/src/commands/theme/` (2 files)

| File | Bytes | Lines |
|---|---:|---:|
| `index.ts` | 217 | 10 |
| `theme.tsx` | 1416 | 56 |

### `vendor/openclaude/src/commands/thinkback/` (2 files)

| File | Bytes | Lines |
|---|---:|---:|
| `index.ts` | 442 | 13 |
| `thinkback.tsx` | 17721 | 553 |

### `vendor/openclaude/src/commands/thinkback-play/` (2 files)

| File | Bytes | Lines |
|---|---:|---:|
| `index.ts` | 608 | 17 |
| `thinkback-play.ts` | 1430 | 43 |

### `vendor/openclaude/src/commands/upgrade/` (2 files)

| File | Bytes | Lines |
|---|---:|---:|
| `index.ts` | 523 | 16 |
| `upgrade.tsx` | 1962 | 37 |

### `vendor/openclaude/src/commands/usage/` (2 files)

| File | Bytes | Lines |
|---|---:|---:|
| `index.ts` | 233 | 9 |
| `usage.tsx` | 315 | 6 |

### `vendor/openclaude/src/commands/vim/` (2 files)

| File | Bytes | Lines |
|---|---:|---:|
| `index.ts` | 273 | 11 |
| `vim.ts` | 1139 | 38 |

### `vendor/openclaude/src/commands/voice/` (2 files)

| File | Bytes | Lines |
|---|---:|---:|
| `index.ts` | 482 | 20 |
| `voice.ts` | 5264 | 150 |

### `vendor/openclaude/src/commands/wiki/` (2 files)

| File | Bytes | Lines |
|---|---:|---:|
| `index.ts` | 299 | 12 |
| `wiki.tsx` | 3454 | 123 |

### `vendor/openclaude/src/components/` (123 files)

| File | Bytes | Lines |
|---|---:|---:|
| `AgentProgressLine.tsx` | 3881 | 134 |
| `App.tsx` | 1526 | 55 |
| `ApproveApiKey.tsx` | 3137 | 121 |
| `AutoModeOptInDialog.tsx` | 4208 | 141 |
| `AutoUpdater.tsx` | 8832 | 197 |
| `AutoUpdaterWrapper.tsx` | 3552 | 90 |
| `AwsAuthStatusBox.tsx` | 2303 | 81 |
| `BaseTextInput.tsx` | 4346 | 137 |
| `BashModeProgress.tsx` | 1487 | 55 |
| `BridgeDialog.tsx` | 10210 | 400 |
| `BypassPermissionsModeDialog.tsx` | 2710 | 86 |
| `ChannelDowngradeDialog.tsx` | 2529 | 100 |
| `ClaudeInChromeOnboarding.tsx` | 3535 | 120 |
| `ClaudeMdExternalIncludesDialog.tsx` | 3935 | 136 |
| `ClickableImageRef.tsx` | 2142 | 71 |
| `CompactSummary.tsx` | 3817 | 117 |
| `ConfigurableShortcutHint.tsx` | 1648 | 56 |
| `ConsoleOAuthFlow.test.tsx` | 3126 | 121 |
| `ConsoleOAuthFlow.tsx` | 18887 | 562 |
| `ContextSuggestions.tsx` | 1458 | 45 |
| `ContextVisualization.tsx` | 18337 | 488 |
| `CoordinatorAgentStatus.tsx` | 9414 | 272 |
| `CostThresholdDialog.tsx` | 1307 | 53 |
| `CtrlOToExpand.tsx` | 1698 | 50 |
| `DesktopHandoff.tsx` | 5575 | 192 |
| `DevBar.tsx` | 1256 | 48 |
| `DevChannelsDialog.tsx` | 2591 | 103 |
| `DiagnosticsDisplay.tsx` | 3216 | 94 |
| `EffortCallout.tsx` | 7142 | 264 |
| `EffortIndicator.ts` | 1128 | 42 |
| `EffortPicker.tsx` | 4733 | 147 |
| `ExitFlow.tsx` | 1212 | 47 |
| `ExportDialog.tsx` | 4945 | 127 |
| `FallbackToolUseErrorMessage.tsx` | 3379 | 115 |
| `FallbackToolUseRejectedMessage.tsx` | 442 | 14 |
| `FastIcon.tsx` | 1242 | 44 |
| `Feedback.test.ts` | 700 | 23 |
| `Feedback.tsx` | 25198 | 607 |
| `FileEditToolDiff.tsx` | 5824 | 180 |
| `FileEditToolUpdatedMessage.tsx` | 3269 | 123 |
| `FileEditToolUseRejectedMessage.tsx` | 4354 | 169 |
| `FilePathLink.tsx` | 954 | 42 |
| `FullscreenLayout.tsx` | 25045 | 636 |
| `GlobalSearchDialog.tsx` | 10757 | 342 |
| `HighlightedCode.tsx` | 4687 | 189 |
| `HistorySearchDialog.tsx` | 4539 | 117 |
| `IdeAutoConnectDialog.tsx` | 3755 | 153 |
| `IdeOnboardingDialog.tsx` | 4695 | 166 |
| `IdeStatusIndicator.tsx` | 1774 | 57 |
| `IdleReturnDialog.tsx` | 2825 | 117 |
| `InterruptedByUser.tsx` | 474 | 13 |
| `InvalidConfigDialog.tsx` | 4308 | 155 |
| `InvalidSettingsDialog.tsx` | 2159 | 88 |
| `KeybindingWarnings.tsx` | 2314 | 54 |
| `LanguagePicker.tsx` | 2404 | 85 |
| `LogSelector.tsx` | 55519 | 1574 |
| `MCPServerApprovalDialog.tsx` | 3315 | 114 |
| `MCPServerDesktopImportDialog.tsx` | 5952 | 202 |
| `MCPServerDialogCopy.tsx` | 486 | 13 |
| `MCPServerMultiselectDialog.tsx` | 4433 | 132 |
| `Markdown.tsx` | 8316 | 235 |
| `MarkdownTable.tsx` | 13019 | 321 |
| `MemoryUsageIndicator.tsx` | 1257 | 36 |
| `Message.tsx` | 24601 | 626 |
| `MessageModel.tsx` | 1074 | 42 |
| `MessageResponse.tsx` | 1957 | 77 |
| `MessageRow.tsx` | 14230 | 382 |
| `MessageSelector.tsx` | 30854 | 830 |
| `MessageTimestamp.tsx` | 1512 | 62 |
| `Messages.tsx` | 42847 | 833 |
| `ModelPicker.tsx` | 15198 | 447 |
| `NativeAutoUpdater.tsx` | 7358 | 192 |
| `NotebookEditToolUseRejectedMessage.tsx` | 2367 | 91 |
| `OffscreenFreeze.tsx` | 1800 | 43 |
| `Onboarding.tsx` | 8369 | 243 |
| `OutputStylePicker.tsx` | 3565 | 111 |
| `PackageManagerAutoUpdater.tsx` | 3623 | 103 |
| `PrBadge.tsx` | 2195 | 96 |
| `PressEnterToContinue.tsx` | 366 | 13 |
| `ProviderManager.test.tsx` | 27892 | 965 |
| `ProviderManager.tsx` | 57043 | 1813 |
| `QuickOpenDialog.tsx` | 7328 | 243 |
| `RemoteCallout.tsx` | 2622 | 75 |
| `RemoteEnvironmentDialog.tsx` | 9831 | 339 |
| `ResumeTask.tsx` | 9902 | 267 |
| `SandboxViolationExpandedView.tsx` | 3098 | 104 |
| `ScrollKeybindingHandler.tsx` | 47594 | 1011 |
| `SearchBox.tsx` | 2329 | 71 |
| `SentryErrorBoundary.ts` | 487 | 28 |
| `SessionBackgroundHint.tsx` | 3486 | 107 |
| `SessionPreview.tsx` | 5403 | 193 |
| `ShowInIDEPrompt.tsx` | 4754 | 169 |
| `SkillImprovementSurvey.tsx` | 4128 | 151 |
| `Spinner.tsx` | 24206 | 561 |
| `StartupScreen.ts` | 11667 | 230 |
| `Stats.tsx` | 38879 | 1227 |
| `StatusLine.tsx` | 13653 | 323 |
| `StatusNotices.tsx` | 2279 | 79 |
| `StructuredDiff.tsx` | 7127 | 189 |
| `StructuredDiffList.tsx` | 936 | 29 |
| `TagTabs.tsx` | 5465 | 138 |
| `TaskListV2.tsx` | 13109 | 378 |
| `TeammateViewHeader.tsx` | 2195 | 81 |
| `TeleportError.tsx` | 5372 | 188 |
| `TeleportProgress.tsx` | 4122 | 139 |
| `TeleportRepoMismatchDialog.tsx` | 3466 | 103 |
| `TeleportResumeWrapper.tsx` | 4437 | 166 |
| `TeleportStash.tsx` | 3834 | 115 |
| `TextInput.test.tsx` | 6232 | 239 |
| `TextInput.tsx` | 5539 | 123 |
| `ThemePicker.test.tsx` | 3853 | 161 |
| `ThemePicker.tsx` | 8161 | 261 |
| `ThinkingToggle.tsx` | 5177 | 152 |
| `TokenWarning.tsx` | 5733 | 178 |
| `ToolUseLoader.tsx` | 1083 | 41 |
| `ValidationErrorsList.tsx` | 4655 | 147 |
| `VimTextInput.tsx` | 4866 | 139 |
| `VirtualMessageList.tsx` | 44400 | 1081 |
| `WorkflowMultiselectDialog.tsx` | 3948 | 127 |
| `WorktreeExitDialog.tsx` | 9676 | 230 |
| `messageActions.tsx` | 13964 | 449 |
| `useCodexOAuthFlow.test.tsx` | 5877 | 220 |
| `useCodexOAuthFlow.ts` | 3500 | 134 |

### `vendor/openclaude/src/components/ClaudeCodeHint/` (1 files)

| File | Bytes | Lines |
|---|---:|---:|
| `PluginHintMenu.tsx` | 2221 | 77 |

### `vendor/openclaude/src/components/CustomSelect/` (10 files)

| File | Bytes | Lines |
|---|---:|---:|
| `SelectMulti.tsx` | 8088 | 212 |
| `index.ts` | 118 | 3 |
| `option-map.ts` | 1189 | 50 |
| `select-input-option.tsx` | 16064 | 487 |
| `select-option.tsx` | 1781 | 67 |
| `select.tsx` | 29936 | 689 |
| `use-multi-select-state.ts` | 10980 | 414 |
| `use-select-input.ts` | 8770 | 287 |
| `use-select-navigation.ts` | 17116 | 676 |
| `use-select-state.ts` | 2980 | 163 |

### `vendor/openclaude/src/components/DesktopUpsell/` (1 files)

| File | Bytes | Lines |
|---|---:|---:|
| `DesktopUpsellStartup.tsx` | 4464 | 170 |

### `vendor/openclaude/src/components/FeedbackSurvey/` (9 files)

| File | Bytes | Lines |
|---|---:|---:|
| `FeedbackSurvey.tsx` | 5577 | 173 |
| `FeedbackSurveyView.tsx` | 2892 | 107 |
| `TranscriptSharePrompt.tsx` | 2685 | 87 |
| `submitTranscriptShare.ts` | 3251 | 112 |
| `useDebouncedDigitInput.ts` | 2722 | 82 |
| `useFeedbackSurvey.tsx` | 13527 | 295 |
| `useMemorySurvey.tsx` | 8466 | 212 |
| `usePostCompactSurvey.tsx` | 6499 | 205 |
| `useSurveyState.tsx` | 3800 | 99 |

### `vendor/openclaude/src/components/HelpV2/` (3 files)

| File | Bytes | Lines |
|---|---:|---:|
| `Commands.tsx` | 2474 | 81 |
| `General.tsx` | 809 | 21 |
| `HelpV2.tsx` | 5847 | 183 |

### `vendor/openclaude/src/components/HighlightedCode/` (1 files)

| File | Bytes | Lines |
|---|---:|---:|
| `Fallback.tsx` | 4763 | 192 |

### `vendor/openclaude/src/components/LogoV2/` (15 files)

| File | Bytes | Lines |
|---|---:|---:|
| `AnimatedAsterisk.tsx` | 2103 | 51 |
| `AnimatedClawd.tsx` | 3826 | 122 |
| `ChannelsNotice.tsx` | 8167 | 265 |
| `Clawd.tsx` | 5289 | 239 |
| `CondensedLogo.tsx` | 5798 | 161 |
| `EmergencyTip.tsx` | 1723 | 57 |
| `Feed.tsx` | 3376 | 111 |
| `FeedColumn.tsx` | 1459 | 58 |
| `GuestPassesUpsell.tsx` | 2390 | 68 |
| `LogoV2.tsx` | 20650 | 544 |
| `Opus1mMergeNotice.tsx` | 1584 | 53 |
| `OverageCreditUpsell.tsx` | 5355 | 165 |
| `VoiceModeNotice.tsx` | 1916 | 66 |
| `WelcomeV2.tsx` | 19108 | 432 |
| `feedConfigs.tsx` | 3072 | 91 |

### `vendor/openclaude/src/components/LspRecommendation/` (1 files)

| File | Bytes | Lines |
|---|---:|---:|
| `LspRecommendationMenu.tsx` | 2511 | 87 |

### `vendor/openclaude/src/components/ManagedSettingsSecurityDialog/` (2 files)

| File | Bytes | Lines |
|---|---:|---:|
| `ManagedSettingsSecurityDialog.tsx` | 4196 | 148 |
| `utils.ts` | 3979 | 144 |

### `vendor/openclaude/src/components/Passes/` (1 files)

| File | Bytes | Lines |
|---|---:|---:|
| `Passes.tsx` | 7104 | 183 |

### `vendor/openclaude/src/components/PromptInput/` (23 files)

| File | Bytes | Lines |
|---|---:|---:|
| `HistorySearchInput.tsx` | 1285 | 50 |
| `IssueFlagBanner.tsx` | 216 | 7 |
| `Notifications.tsx` | 13364 | 331 |
| `PromptInput.tsx` | 101347 | 2376 |
| `PromptInputFooter.tsx` | 8712 | 190 |
| `PromptInputFooterLeftSide.tsx` | 24561 | 516 |
| `PromptInputFooterSuggestions.test.tsx` | 926 | 35 |
| `PromptInputFooterSuggestions.tsx` | 5868 | 212 |
| `PromptInputHelpMenu.tsx` | 9715 | 357 |
| `PromptInputModeIndicator.tsx` | 2987 | 92 |
| `PromptInputQueuedCommands.test.tsx` | 1099 | 35 |
| `PromptInputQueuedCommands.tsx` | 6061 | 130 |
| `PromptInputStashNotice.tsx` | 583 | 24 |
| `SandboxPromptFooterHint.tsx` | 2195 | 63 |
| `ShimmeredInput.tsx` | 3904 | 142 |
| `VoiceIndicator.tsx` | 3270 | 136 |
| `inputModes.ts` | 731 | 33 |
| `inputPaste.ts` | 2693 | 90 |
| `useMaybeTruncateInput.ts` | 1468 | 58 |
| `usePromptInputPlaceholder.ts` | 2391 | 76 |
| `useShowFastIconHint.ts` | 696 | 31 |
| `useSwarmBanner.ts` | 5344 | 155 |
| `utils.ts` | 1744 | 60 |

### `vendor/openclaude/src/components/Settings/` (5 files)

| File | Bytes | Lines |
|---|---:|---:|
| `CodexUsage.tsx` | 5317 | 211 |
| `Config.tsx` | 75854 | 1861 |
| `Settings.tsx` | 4422 | 136 |
| `Status.tsx` | 6568 | 240 |
| `Usage.tsx` | 10928 | 384 |

### `vendor/openclaude/src/components/Spinner/` (12 files)

| File | Bytes | Lines |
|---|---:|---:|
| `FlashingChar.tsx` | 1766 | 60 |
| `GlimmerMessage.tsx` | 8419 | 327 |
| `ShimmerChar.tsx` | 865 | 35 |
| `SpinnerAnimationRow.tsx` | 11704 | 267 |
| `SpinnerGlyph.tsx` | 2591 | 79 |
| `TeammateSpinnerLine.tsx` | 10363 | 232 |
| `TeammateSpinnerTree.tsx` | 8572 | 271 |
| `index.ts` | 602 | 10 |
| `teammateSelectHint.ts` | 64 | 1 |
| `useShimmerAnimation.ts` | 1236 | 31 |
| `useStalledAnimation.ts` | 2500 | 75 |
| `utils.ts` | 2261 | 84 |

### `vendor/openclaude/src/components/StructuredDiff/` (2 files)

| File | Bytes | Lines |
|---|---:|---:|
| `Fallback.tsx` | 15687 | 486 |
| `colorDiff.ts` | 1157 | 37 |

### `vendor/openclaude/src/components/TrustDialog/` (2 files)

| File | Bytes | Lines |
|---|---:|---:|
| `TrustDialog.tsx` | 8825 | 289 |
| `utils.ts` | 7005 | 245 |

### `vendor/openclaude/src/components/agents/` (14 files)

| File | Bytes | Lines |
|---|---:|---:|
| `AgentDetail.tsx` | 6366 | 219 |
| `AgentEditor.tsx` | 6445 | 177 |
| `AgentNavigationFooter.tsx` | 811 | 25 |
| `AgentsList.tsx` | 14981 | 439 |
| `AgentsMenu.tsx` | 23522 | 799 |
| `ColorPicker.tsx` | 3668 | 111 |
| `ModelSelector.tsx` | 1855 | 67 |
| `SnapshotUpdateDialog.tsx` | 104 | 3 |
| `ToolSelector.tsx` | 17827 | 561 |
| `agentFileUtils.ts` | 7487 | 272 |
| `generateAgent.ts` | 10143 | 197 |
| `types.ts` | 915 | 27 |
| `utils.ts` | 528 | 18 |
| `validateAgent.ts` | 3150 | 109 |

### `vendor/openclaude/src/components/agents/new-agent-creation/` (1 files)

| File | Bytes | Lines |
|---|---:|---:|
| `CreateAgentWizard.tsx` | 2955 | 96 |

### `vendor/openclaude/src/components/agents/new-agent-creation/wizard-steps/` (12 files)

| File | Bytes | Lines |
|---|---:|---:|
| `ColorStep.tsx` | 3046 | 83 |
| `ConfirmStep.tsx` | 10306 | 377 |
| `ConfirmStepWrapper.tsx` | 3594 | 73 |
| `DescriptionStep.tsx` | 3991 | 122 |
| `GenerateStep.tsx` | 5761 | 142 |
| `LocationStep.tsx` | 2392 | 79 |
| `MemoryStep.tsx` | 3876 | 112 |
| `MethodStep.tsx` | 2344 | 79 |
| `ModelStep.tsx` | 1805 | 51 |
| `PromptStep.tsx` | 4159 | 127 |
| `ToolsStep.tsx` | 1992 | 60 |
| `TypeStep.tsx` | 3418 | 102 |

### `vendor/openclaude/src/components/design-system/` (17 files)

| File | Bytes | Lines |
|---|---:|---:|
| `Byline.tsx` | 2009 | 76 |
| `Dialog.tsx` | 4143 | 138 |
| `Divider.tsx` | 3366 | 148 |
| `FullWidthRow.tsx` | 302 | 15 |
| `FuzzyPicker.tsx` | 11158 | 311 |
| `KeyboardShortcutHint.tsx` | 2247 | 80 |
| `ListItem.tsx` | 6147 | 243 |
| `LoadingState.tsx` | 1940 | 93 |
| `Pane.tsx` | 1915 | 76 |
| `ProgressBar.tsx` | 2042 | 85 |
| `Ratchet.tsx` | 1906 | 79 |
| `StatusIcon.tsx` | 2180 | 94 |
| `Tabs.tsx` | 10812 | 339 |
| `ThemeProvider.tsx` | 5384 | 169 |
| `ThemedBox.tsx` | 5787 | 152 |
| `ThemedText.tsx` | 4105 | 123 |
| `color.ts` | 853 | 30 |

### `vendor/openclaude/src/components/diff/` (3 files)

| File | Bytes | Lines |
|---|---:|---:|
| `DiffDetailView.tsx` | 6787 | 280 |
| `DiffDialog.tsx` | 11523 | 382 |
| `DiffFileList.tsx` | 7326 | 291 |

### `vendor/openclaude/src/components/grove/` (1 files)

| File | Bytes | Lines |
|---|---:|---:|
| `Grove.tsx` | 14633 | 462 |

### `vendor/openclaude/src/components/hooks/` (6 files)

| File | Bytes | Lines |
|---|---:|---:|
| `HooksConfigMenu.tsx` | 16857 | 577 |
| `PromptDialog.tsx` | 2110 | 89 |
| `SelectEventMode.tsx` | 3823 | 126 |
| `SelectHookMode.tsx` | 3703 | 111 |
| `SelectMatcherMode.tsx` | 4245 | 143 |
| `ViewHookMode.tsx` | 5237 | 198 |

### `vendor/openclaude/src/components/mcp/` (12 files)

| File | Bytes | Lines |
|---|---:|---:|
| `CapabilitiesSection.tsx` | 1473 | 60 |
| `ElicitationDialog.tsx` | 47183 | 1168 |
| `MCPAgentServerMenu.tsx` | 6726 | 182 |
| `MCPListPanel.tsx` | 15855 | 503 |
| `MCPReconnect.tsx` | 4667 | 166 |
| `MCPRemoteServerMenu.tsx` | 27057 | 648 |
| `MCPSettings.tsx` | 12658 | 397 |
| `MCPStdioServerMenu.tsx` | 6982 | 176 |
| `MCPToolDetailView.tsx` | 6155 | 211 |
| `MCPToolListView.tsx` | 4472 | 140 |
| `McpParsingWarnings.tsx` | 5723 | 212 |
| `index.ts` | 523 | 9 |

### `vendor/openclaude/src/components/mcp/utils/` (1 files)

| File | Bytes | Lines |
|---|---:|---:|
| `reconnectHelpers.tsx` | 1404 | 48 |

### `vendor/openclaude/src/components/memory/` (4 files)

| File | Bytes | Lines |
|---|---:|---:|
| `MemoryFileSelector.tsx` | 13264 | 440 |
| `MemoryUpdateNotification.tsx` | 1340 | 44 |
| `memoryFileSelectorPaths.test.ts` | 2125 | 72 |
| `memoryFileSelectorPaths.ts` | 932 | 34 |

### `vendor/openclaude/src/components/messages/` (33 files)

| File | Bytes | Lines |
|---|---:|---:|
| `AdvisorMessage.tsx` | 4355 | 157 |
| `AssistantRedactedThinkingMessage.tsx` | 683 | 30 |
| `AssistantTextMessage.tsx` | 9287 | 269 |
| `AssistantThinkingMessage.tsx` | 2286 | 85 |
| `AssistantToolUseMessage.tsx` | 12477 | 367 |
| `AttachmentMessage.tsx` | 19745 | 536 |
| `CollapsedReadSearchContent.tsx` | 20018 | 483 |
| `CompactBoundaryMessage.tsx` | 575 | 16 |
| `GroupedToolUseContent.tsx` | 1969 | 57 |
| `HighlightedThinkingText.tsx` | 4206 | 161 |
| `HookProgressMessage.tsx` | 3045 | 115 |
| `PlanApprovalMessage.tsx` | 6927 | 221 |
| `RateLimitMessage.tsx` | 4958 | 160 |
| `ShutdownMessage.tsx` | 3897 | 131 |
| `SystemAPIErrorMessage.tsx` | 3461 | 140 |
| `SystemTextMessage.tsx` | 22216 | 826 |
| `TaskAssignmentMessage.tsx` | 2218 | 75 |
| `UserAgentNotificationMessage.tsx` | 1723 | 82 |
| `UserBashInputMessage.tsx` | 1247 | 57 |
| `UserBashOutputMessage.tsx` | 1156 | 53 |
| `UserChannelMessage.tsx` | 3381 | 136 |
| `UserCommandMessage.tsx` | 2602 | 107 |
| `UserImageMessage.tsx` | 1657 | 58 |
| `UserLocalCommandOutputMessage.tsx` | 4155 | 167 |
| `UserMemoryInputMessage.tsx` | 1800 | 74 |
| `UserPlanMessage.tsx` | 995 | 41 |
| `UserPromptMessage.tsx` | 4384 | 79 |
| `UserResourceUpdateMessage.tsx` | 3315 | 120 |
| `UserTeammateMessage.tsx` | 6506 | 205 |
| `UserTextMessage.tsx` | 8375 | 274 |
| `nullRenderingAttachments.ts` | 2257 | 70 |
| `teamMemCollapsed.tsx` | 4207 | 139 |
| `teamMemSaved.ts` | 711 | 19 |

### `vendor/openclaude/src/components/messages/UserToolResultMessage/` (8 files)

| File | Bytes | Lines |
|---|---:|---:|
| `RejectedPlanMessage.tsx` | 861 | 30 |
| `RejectedToolUseMessage.tsx` | 443 | 14 |
| `UserToolCanceledMessage.tsx` | 461 | 14 |
| `UserToolErrorMessage.tsx` | 3598 | 102 |
| `UserToolRejectMessage.tsx` | 2638 | 94 |
| `UserToolResultMessage.tsx` | 4074 | 105 |
| `UserToolSuccessMessage.tsx` | 6815 | 146 |
| `utils.tsx` | 1142 | 43 |

### `vendor/openclaude/src/components/permissions/` (15 files)

| File | Bytes | Lines |
|---|---:|---:|
| `FallbackPermissionRequest.tsx` | 9213 | 332 |
| `PermissionDecisionDebugInfo.tsx` | 14409 | 459 |
| `PermissionDialog.tsx` | 2029 | 71 |
| `PermissionExplanation.tsx` | 6704 | 271 |
| `PermissionPrompt.tsx` | 10775 | 335 |
| `PermissionRequest.tsx` | 10203 | 216 |
| `PermissionRequestTitle.tsx` | 1545 | 65 |
| `PermissionRuleExplanation.tsx` | 4093 | 120 |
| `SandboxPermissionRequest.tsx` | 3904 | 162 |
| `WorkerBadge.tsx` | 1082 | 48 |
| `WorkerPendingPermission.tsx` | 2717 | 104 |
| `hooks.ts` | 8458 | 209 |
| `shellPermissionHelpers.tsx` | 5797 | 163 |
| `useShellPermissionFeedback.ts` | 4605 | 148 |
| `utils.ts` | 660 | 25 |

### `vendor/openclaude/src/components/permissions/AskUserQuestionPermissionRequest/` (7 files)

| File | Bytes | Lines |
|---|---:|---:|
| `AskUserQuestionPermissionRequest.tsx` | 22893 | 644 |
| `PreviewBox.tsx` | 6995 | 228 |
| `PreviewQuestionView.tsx` | 13575 | 327 |
| `QuestionNavigationBar.tsx` | 6239 | 177 |
| `QuestionView.tsx` | 16019 | 459 |
| `SubmitQuestionsView.tsx` | 4521 | 143 |
| `use-multiple-choice-state.ts` | 4142 | 179 |

### `vendor/openclaude/src/components/permissions/BashPermissionRequest/` (2 files)

| File | Bytes | Lines |
|---|---:|---:|
| `BashPermissionRequest.tsx` | 21453 | 481 |
| `bashToolUseOptions.tsx` | 6126 | 146 |

### `vendor/openclaude/src/components/permissions/ComputerUseApproval/` (1 files)

| File | Bytes | Lines |
|---|---:|---:|
| `ComputerUseApproval.tsx` | 12409 | 440 |

### `vendor/openclaude/src/components/permissions/EnterPlanModePermissionRequest/` (1 files)

| File | Bytes | Lines |
|---|---:|---:|
| `EnterPlanModePermissionRequest.tsx` | 3920 | 121 |

### `vendor/openclaude/src/components/permissions/ExitPlanModePermissionRequest/` (1 files)

| File | Bytes | Lines |
|---|---:|---:|
| `ExitPlanModePermissionRequest.tsx` | 34447 | 767 |

### `vendor/openclaude/src/components/permissions/FileEditPermissionRequest/` (1 files)

| File | Bytes | Lines |
|---|---:|---:|
| `FileEditPermissionRequest.tsx` | 4781 | 181 |

### `vendor/openclaude/src/components/permissions/FilePermissionDialog/` (5 files)

| File | Bytes | Lines |
|---|---:|---:|
| `FilePermissionDialog.tsx` | 7933 | 203 |
| `ideDiffConfig.ts` | 858 | 42 |
| `permissionOptions.tsx` | 6339 | 176 |
| `useFilePermissionDialog.ts` | 6809 | 212 |
| `usePermissionHandler.ts` | 5105 | 185 |

### `vendor/openclaude/src/components/permissions/FileWritePermissionRequest/` (2 files)

| File | Bytes | Lines |
|---|---:|---:|
| `FileWritePermissionRequest.tsx` | 4674 | 160 |
| `FileWriteToolDiff.tsx` | 2492 | 88 |

### `vendor/openclaude/src/components/permissions/FilesystemPermissionRequest/` (1 files)

| File | Bytes | Lines |
|---|---:|---:|
| `FilesystemPermissionRequest.tsx` | 3773 | 114 |

### `vendor/openclaude/src/components/permissions/MonitorPermissionRequest/` (1 files)

| File | Bytes | Lines |
|---|---:|---:|
| `MonitorPermissionRequest.tsx` | 5040 | 173 |

### `vendor/openclaude/src/components/permissions/NotebookEditPermissionRequest/` (2 files)

| File | Bytes | Lines |
|---|---:|---:|
| `NotebookEditPermissionRequest.tsx` | 4766 | 165 |
| `NotebookEditToolDiff.tsx` | 6720 | 234 |

### `vendor/openclaude/src/components/permissions/PowerShellPermissionRequest/` (2 files)

| File | Bytes | Lines |
|---|---:|---:|
| `PowerShellPermissionRequest.tsx` | 10548 | 234 |
| `powershellToolUseOptions.tsx` | 3311 | 90 |

### `vendor/openclaude/src/components/permissions/SedEditPermissionRequest/` (1 files)

| File | Bytes | Lines |
|---|---:|---:|
| `SedEditPermissionRequest.tsx` | 5818 | 229 |

### `vendor/openclaude/src/components/permissions/SkillPermissionRequest/` (1 files)

| File | Bytes | Lines |
|---|---:|---:|
| `SkillPermissionRequest.tsx` | 10655 | 368 |

### `vendor/openclaude/src/components/permissions/WebFetchPermissionRequest/` (1 files)

| File | Bytes | Lines |
|---|---:|---:|
| `WebFetchPermissionRequest.tsx` | 6672 | 257 |

### `vendor/openclaude/src/components/permissions/rules/` (8 files)

| File | Bytes | Lines |
|---|---:|---:|
| `AddPermissionRules.tsx` | 6189 | 179 |
| `AddWorkspaceDirectory.tsx` | 10437 | 339 |
| `PermissionRuleDescription.tsx` | 2232 | 75 |
| `PermissionRuleInput.tsx` | 4559 | 137 |
| `PermissionRuleList.tsx` | 34406 | 1178 |
| `RecentDenialsTab.tsx` | 5449 | 206 |
| `RemoveWorkspaceDirectory.tsx` | 2881 | 109 |
| `WorkspaceTab.tsx` | 4284 | 149 |

### `vendor/openclaude/src/components/sandbox/` (5 files)

| File | Bytes | Lines |
|---|---:|---:|
| `SandboxConfigTab.tsx` | 3823 | 44 |
| `SandboxDependenciesTab.tsx` | 4302 | 119 |
| `SandboxDoctorSection.tsx` | 1586 | 45 |
| `SandboxOverridesTab.tsx` | 6073 | 192 |
| `SandboxSettings.tsx` | 8684 | 295 |

### `vendor/openclaude/src/components/shell/` (4 files)

| File | Bytes | Lines |
|---|---:|---:|
| `ExpandShellOutputContext.tsx` | 1080 | 35 |
| `OutputLine.tsx` | 4088 | 117 |
| `ShellProgressMessage.tsx` | 3873 | 149 |
| `ShellTimeDisplay.tsx` | 1513 | 73 |

### `vendor/openclaude/src/components/skills/` (1 files)

| File | Bytes | Lines |
|---|---:|---:|
| `SkillsMenu.tsx` | 7722 | 241 |

### `vendor/openclaude/src/components/tasks/` (12 files)

| File | Bytes | Lines |
|---|---:|---:|
| `AsyncAgentDetailDialog.tsx` | 7609 | 228 |
| `BackgroundTask.tsx` | 10188 | 344 |
| `BackgroundTaskStatus.tsx` | 11527 | 428 |
| `BackgroundTasksDialog.tsx` | 29552 | 652 |
| `DreamDetailDialog.tsx` | 7197 | 250 |
| `InProcessTeammateDetailDialog.tsx` | 8498 | 265 |
| `RemoteSessionDetailDialog.tsx` | 26905 | 903 |
| `RemoteSessionProgress.tsx` | 7363 | 242 |
| `ShellDetailDialog.tsx` | 10763 | 403 |
| `ShellProgress.tsx` | 2188 | 86 |
| `renderToolActivity.tsx` | 1046 | 32 |
| `taskStatusUtils.tsx` | 3756 | 106 |

### `vendor/openclaude/src/components/teams/` (2 files)

| File | Bytes | Lines |
|---|---:|---:|
| `TeamStatus.tsx` | 1905 | 79 |
| `TeamsDialog.tsx` | 25908 | 714 |

### `vendor/openclaude/src/components/ui/` (3 files)

| File | Bytes | Lines |
|---|---:|---:|
| `OrderedList.tsx` | 2050 | 70 |
| `OrderedListItem.tsx` | 925 | 44 |
| `TreeSelect.tsx` | 10712 | 396 |

### `vendor/openclaude/src/components/wizard/` (5 files)

| File | Bytes | Lines |
|---|---:|---:|
| `WizardDialogLayout.tsx` | 1711 | 64 |
| `WizardNavigationFooter.tsx` | 1026 | 23 |
| `WizardProvider.tsx` | 5441 | 212 |
| `index.ts` | 328 | 9 |
| `useWizard.ts` | 447 | 13 |

### `vendor/openclaude/src/constants/` (22 files)

| File | Bytes | Lines |
|---|---:|---:|
| `apiLimits.ts` | 3443 | 94 |
| `betas.ts` | 2218 | 52 |
| `common.ts` | 1521 | 33 |
| `cyberRiskInstruction.ts` | 1525 | 24 |
| `errorIds.ts` | 476 | 15 |
| `figures.ts` | 2063 | 45 |
| `files.ts` | 2625 | 156 |
| `github-app.ts` | 5347 | 144 |
| `keys.ts` | 102 | 3 |
| `messages.ts` | 49 | 1 |
| `oauth.ts` | 8970 | 234 |
| `outputStyles.ts` | 9886 | 216 |
| `product.ts` | 2563 | 76 |
| `promptIdentity.test.ts` | 3908 | 95 |
| `prompts.ts` | 54319 | 919 |
| `spinnerVerbs.ts` | 3453 | 204 |
| `system.ts` | 3850 | 98 |
| `systemPromptSections.ts` | 1794 | 68 |
| `toolLimits.ts` | 2169 | 56 |
| `tools.ts` | 4512 | 110 |
| `turnCompletionVerbs.ts` | 269 | 12 |
| `xml.ts` | 3325 | 86 |

### `vendor/openclaude/src/context/` (9 files)

| File | Bytes | Lines |
|---|---:|---:|
| `QueuedMessageContext.tsx` | 1458 | 62 |
| `fpsMetrics.tsx` | 842 | 29 |
| `mailbox.tsx` | 928 | 37 |
| `modalContext.tsx` | 1970 | 57 |
| `notifications.tsx` | 9009 | 252 |
| `overlayContext.tsx` | 4283 | 150 |
| `promptOverlayContext.tsx` | 4074 | 158 |
| `stats.tsx` | 5402 | 219 |
| `voice.tsx` | 2404 | 87 |

### `vendor/openclaude/src/coordinator/` (2 files)

| File | Bytes | Lines |
|---|---:|---:|
| `coordinatorMode.ts` | 19038 | 369 |
| `workerAgent.ts` | 921 | 18 |

### `vendor/openclaude/src/entrypoints/` (6 files)

| File | Bytes | Lines |
|---|---:|---:|
| `agentSdkTypes.ts` | 13186 | 448 |
| `cli.tsx` | 15633 | 401 |
| `init.ts` | 13780 | 340 |
| `mcp.test.ts` | 2823 | 75 |
| `mcp.ts` | 9062 | 267 |
| `sandboxTypes.ts` | 5691 | 156 |

### `vendor/openclaude/src/entrypoints/sdk/` (6 files)

| File | Bytes | Lines |
|---|---:|---:|
| `controlSchemas.ts` | 19559 | 663 |
| `coreSchemas.ts` | 56493 | 1889 |
| `coreTypes.generated.ts` | 75 | 2 |
| `coreTypes.ts` | 1466 | 62 |
| `runtimeTypes.ts` | 60 | 1 |
| `toolTypes.ts` | 74 | 2 |

### `vendor/openclaude/src/grpc/` (1 files)

| File | Bytes | Lines |
|---|---:|---:|
| `server.ts` | 10882 | 333 |

### `vendor/openclaude/src/hooks/` (86 files)

| File | Bytes | Lines |
|---|---:|---:|
| `fileSuggestions.ts` | 27152 | 811 |
| `renderPlaceholder.ts` | 1280 | 51 |
| `unifiedSuggestions.ts` | 5837 | 202 |
| `useAfterFirstRender.ts` | 485 | 17 |
| `useApiKeyVerification.test.tsx` | 3002 | 123 |
| `useApiKeyVerification.ts` | 3176 | 103 |
| `useArrowKeyHistory.tsx` | 9559 | 228 |
| `useAssistantHistory.ts` | 9228 | 250 |
| `useAwaySummary.ts` | 3835 | 125 |
| `useBackgroundTaskNavigation.ts` | 8553 | 251 |
| `useBlink.ts` | 1279 | 34 |
| `useCanUseTool.tsx` | 9658 | 203 |
| `useCancelRequest.ts` | 10127 | 276 |
| `useChromeExtensionNotification.tsx` | 1567 | 49 |
| `useClaudeCodeHintRecommendation.tsx` | 4420 | 128 |
| `useClipboardImageHint.ts` | 2458 | 77 |
| `useCommandKeybindings.tsx` | 3267 | 107 |
| `useCommandQueue.ts` | 543 | 15 |
| `useCopyOnSelect.ts` | 4287 | 98 |
| `useDeferredHookMessages.ts` | 1499 | 46 |
| `useDiffData.ts` | 2839 | 110 |
| `useDiffInIDE.ts` | 9867 | 379 |
| `useDirectConnect.ts` | 7504 | 229 |
| `useDoublePress.ts` | 1651 | 62 |
| `useDynamicConfig.ts` | 703 | 22 |
| `useEffectEventCompat.ts` | 428 | 16 |
| `useElapsedTime.ts` | 1226 | 37 |
| `useExitOnCtrlCD.ts` | 3226 | 95 |
| `useExitOnCtrlCDWithKeybindings.ts` | 948 | 24 |
| `useFileHistorySnapshotInit.ts` | 767 | 25 |
| `useGlobalKeybindings.tsx` | 9397 | 248 |
| `useHistorySearch.ts` | 9488 | 303 |
| `useIDEIntegration.tsx` | 2793 | 69 |
| `useIdeAtMentioned.ts` | 2217 | 76 |
| `useIdeConnectionStatus.ts` | 981 | 33 |
| `useIdeLogging.ts` | 1201 | 41 |
| `useIdeSelection.ts` | 4349 | 150 |
| `useInboxPoller.ts` | 34375 | 969 |
| `useInputBuffer.ts` | 3386 | 132 |
| `useIssueFlagBanner.ts` | 3828 | 133 |
| `useLogMessages.ts` | 5710 | 119 |
| `useLspPluginRecommendation.tsx` | 6192 | 193 |
| `useMailboxBridge.ts` | 716 | 21 |
| `useMainLoopModel.ts` | 1509 | 34 |
| `useManagePlugins.ts` | 12420 | 324 |
| `useMemoryUsage.ts` | 1293 | 39 |
| `useMergedClients.ts` | 745 | 23 |
| `useMergedCommands.ts` | 423 | 15 |
| `useMergedTools.ts` | 1650 | 44 |
| `useMinDisplayTime.ts` | 1010 | 35 |
| `useNotifyAfterTimeout.ts` | 2471 | 65 |
| `useOfficialMarketplaceNotification.tsx` | 1815 | 47 |
| `usePasteHandler.test.ts` | 1854 | 64 |
| `usePasteHandler.ts` | 11169 | 327 |
| `usePluginRecommendationBase.tsx` | 3198 | 104 |
| `usePrStatus.ts` | 3202 | 106 |
| `usePromptSuggestion.ts` | 5315 | 177 |
| `usePromptsFromClaudeInChrome.tsx` | 2495 | 70 |
| `useQueueProcessor.ts` | 2547 | 68 |
| `useRemoteSession.ts` | 23010 | 605 |
| `useReplBridge.tsx` | 35751 | 722 |
| `useSSHSession.ts` | 8316 | 241 |
| `useScheduledTasks.ts` | 5975 | 139 |
| `useSearchInput.ts` | 10327 | 364 |
| `useSessionBackgrounding.ts` | 4944 | 158 |
| `useSettings.ts` | 618 | 17 |
| `useSettingsChange.ts` | 946 | 25 |
| `useSkillImprovementSurvey.ts` | 3528 | 105 |
| `useSkillsChange.ts` | 2084 | 62 |
| `useSwarmInitialization.ts` | 3151 | 81 |
| `useSwarmPermissionPoller.ts` | 6919 | 222 |
| `useTaskListWatcher.ts` | 6822 | 221 |
| `useTasksV2.ts` | 8808 | 250 |
| `useTeammateViewAutoExit.ts` | 2189 | 63 |
| `useTeleportResume.tsx` | 2676 | 84 |
| `useTerminalSize.ts` | 354 | 15 |
| `useTextInput.ts` | 19707 | 610 |
| `useTimeout.ts` | 362 | 14 |
| `useTurnDiffs.ts` | 6686 | 213 |
| `useTypeahead.tsx` | 61494 | 1392 |
| `useUpdateNotification.ts` | 982 | 34 |
| `useVimInput.ts` | 9772 | 323 |
| `useVirtualScroll.ts` | 35122 | 721 |
| `useVoice.ts` | 45802 | 1144 |
| `useVoiceEnabled.ts` | 1134 | 25 |
| `useVoiceIntegration.tsx` | 31628 | 676 |

### `vendor/openclaude/src/hooks/notifs/` (16 files)

| File | Bytes | Lines |
|---|---:|---:|
| `useAutoModeUnavailableNotification.ts` | 1965 | 56 |
| `useCanSwitchToExistingSubscription.tsx` | 1946 | 59 |
| `useDeprecationWarningNotification.tsx` | 1261 | 43 |
| `useFastModeNotification.tsx` | 4441 | 161 |
| `useIDEStatusIndicator.tsx` | 6016 | 185 |
| `useInstallMessages.tsx` | 736 | 25 |
| `useLspInitializationNotification.tsx` | 4125 | 142 |
| `useMcpConnectivityStatus.tsx` | 3802 | 92 |
| `useModelMigrationNotifications.tsx` | 1856 | 51 |
| `useNpmDeprecationNotification.tsx` | 954 | 24 |
| `usePluginAutoupdateNotification.tsx` | 2507 | 82 |
| `usePluginInstallationStatus.tsx` | 3800 | 127 |
| `useRateLimitWarningNotification.tsx` | 3554 | 113 |
| `useSettingsErrors.tsx` | 1988 | 68 |
| `useStartupNotification.ts` | 1278 | 41 |
| `useTeammateShutdownNotification.ts` | 2296 | 78 |

### `vendor/openclaude/src/hooks/toolPermission/` (2 files)

| File | Bytes | Lines |
|---|---:|---:|
| `PermissionContext.ts` | 12768 | 388 |
| `permissionLogging.ts` | 7286 | 238 |

### `vendor/openclaude/src/hooks/toolPermission/handlers/` (3 files)

| File | Bytes | Lines |
|---|---:|---:|
| `coordinatorHandler.ts` | 2374 | 65 |
| `interactiveHandler.ts` | 20194 | 536 |
| `swarmWorkerHandler.ts` | 5537 | 159 |

### `vendor/openclaude/src/ink/` (48 files)

| File | Bytes | Lines |
|---|---:|---:|
| `Ansi.tsx` | 8592 | 291 |
| `bidi.ts` | 4290 | 139 |
| `clearTerminal.ts` | 1901 | 74 |
| `colorize.ts` | 7647 | 231 |
| `constants.ts` | 107 | 2 |
| `devtools.ts` | 71 | 2 |
| `dom.ts` | 15328 | 487 |
| `focus.ts` | 5142 | 181 |
| `frame.ts` | 4209 | 124 |
| `get-max-width.ts` | 1149 | 27 |
| `global.d.ts` | 271 | 9 |
| `hit-test.ts` | 4228 | 130 |
| `ink.tsx` | 78537 | 1752 |
| `instances.ts` | 410 | 10 |
| `line-width-cache.ts` | 734 | 24 |
| `log-update.test.ts` | 3466 | 125 |
| `log-update.ts` | 29297 | 857 |
| `measure-element.ts` | 419 | 23 |
| `measure-text.ts` | 1138 | 47 |
| `node-cache.ts` | 1654 | 54 |
| `optimizer.ts` | 2588 | 93 |
| `output.ts` | 26183 | 797 |
| `parse-keypress.test.ts` | 1364 | 49 |
| `parse-keypress.ts` | 24418 | 827 |
| `reconciler.test.ts` | 8399 | 369 |
| `reconciler.ts` | 15747 | 548 |
| `render-border.ts` | 6642 | 231 |
| `render-node-to-output.ts` | 64268 | 1495 |
| `render-to-screen.ts` | 8570 | 231 |
| `renderer.ts` | 7665 | 178 |
| `root.ts` | 4600 | 184 |
| `screen.ts` | 49323 | 1486 |
| `searchHighlight.ts` | 3325 | 93 |
| `selection.ts` | 34933 | 917 |
| `squash-text-nodes.ts` | 2293 | 92 |
| `stringWidth.ts` | 7156 | 222 |
| `styles.ts` | 20889 | 771 |
| `supports-hyperlinks.ts` | 1596 | 57 |
| `tabstops.ts` | 1113 | 46 |
| `terminal-focus-state.ts` | 1305 | 47 |
| `terminal-querier.ts` | 7843 | 212 |
| `terminal.ts` | 9402 | 275 |
| `termio.ts` | 1036 | 42 |
| `useTerminalNotification.ts` | 3857 | 126 |
| `warn.ts` | 295 | 9 |
| `widest-line.ts` | 434 | 19 |
| `wrap-text.ts` | 1806 | 74 |
| `wrapAnsi.ts` | 383 | 20 |

### `vendor/openclaude/src/ink/components/` (18 files)

| File | Bytes | Lines |
|---|---:|---:|
| `AlternateScreen.tsx` | 2869 | 79 |
| `App.tsx` | 31789 | 689 |
| `AppContext.ts` | 523 | 21 |
| `Box.tsx` | 6830 | 209 |
| `Button.tsx` | 4863 | 191 |
| `ClockContext.tsx` | 3327 | 111 |
| `CursorDeclarationContext.ts` | 1119 | 32 |
| `ErrorOverview.tsx` | 733 | 27 |
| `Link.tsx` | 904 | 41 |
| `Newline.tsx` | 692 | 38 |
| `NoSelect.tsx` | 2011 | 67 |
| `RawAnsi.tsx` | 1737 | 56 |
| `ScrollBox.tsx` | 9486 | 236 |
| `Spacer.tsx` | 491 | 19 |
| `StdinContext.ts` | 1678 | 49 |
| `TerminalFocusContext.tsx` | 1751 | 51 |
| `TerminalSizeContext.tsx` | 183 | 6 |
| `Text.tsx` | 5079 | 253 |

### `vendor/openclaude/src/ink/events/` (10 files)

| File | Bytes | Lines |
|---|---:|---:|
| `click-event.ts` | 1332 | 38 |
| `dispatcher.ts` | 5991 | 234 |
| `emitter.ts` | 1125 | 39 |
| `event-handlers.ts` | 2202 | 73 |
| `event.ts` | 250 | 11 |
| `focus-event.ts` | 687 | 21 |
| `input-event.ts` | 7306 | 205 |
| `keyboard-event.ts` | 1765 | 51 |
| `terminal-event.ts` | 2526 | 107 |
| `terminal-focus-event.ts` | 512 | 19 |

### `vendor/openclaude/src/ink/hooks/` (12 files)

| File | Bytes | Lines |
|---|---:|---:|
| `use-animation-frame.ts` | 1933 | 57 |
| `use-app.ts` | 251 | 8 |
| `use-declared-cursor.ts` | 2996 | 73 |
| `use-input.ts` | 3107 | 92 |
| `use-interval.ts` | 1796 | 67 |
| `use-search-highlight.ts` | 2158 | 53 |
| `use-selection.ts` | 4421 | 104 |
| `use-stdin.ts` | 232 | 8 |
| `use-tab-status.ts` | 2175 | 72 |
| `use-terminal-focus.ts` | 556 | 16 |
| `use-terminal-title.ts` | 1020 | 31 |
| `use-terminal-viewport.ts` | 3977 | 96 |

### `vendor/openclaude/src/ink/layout/` (4 files)

| File | Bytes | Lines |
|---|---:|---:|
| `engine.ts` | 177 | 6 |
| `geometry.ts` | 2471 | 97 |
| `node.ts` | 4346 | 152 |
| `yoga.ts` | 7400 | 308 |

### `vendor/openclaude/src/ink/termio/` (10 files)

| File | Bytes | Lines |
|---|---:|---:|
| `ansi.ts` | 1490 | 75 |
| `csi.ts` | 8677 | 319 |
| `dec.ts` | 1935 | 60 |
| `esc.ts` | 1444 | 67 |
| `osc.test.ts` | 4730 | 150 |
| `osc.ts` | 17763 | 518 |
| `parser.ts` | 11546 | 394 |
| `sgr.ts` | 6400 | 308 |
| `tokenize.ts` | 9284 | 319 |
| `types.ts` | 7076 | 236 |

### `vendor/openclaude/src/keybindings/` (14 files)

| File | Bytes | Lines |
|---|---:|---:|
| `KeybindingContext.tsx` | 7580 | 242 |
| `KeybindingProviderSetup.tsx` | 11384 | 307 |
| `defaultBindings.ts` | 11640 | 340 |
| `loadUserBindings.ts` | 14536 | 472 |
| `match.ts` | 3797 | 120 |
| `parser.ts` | 4972 | 203 |
| `reservedShortcuts.ts` | 3610 | 127 |
| `resolver.ts` | 7087 | 244 |
| `schema.ts` | 6274 | 236 |
| `shortcutFormat.ts` | 2575 | 63 |
| `template.ts` | 1721 | 52 |
| `useKeybinding.ts` | 6862 | 196 |
| `useShortcutDisplay.ts` | 2510 | 59 |
| `validate.ts` | 13667 | 498 |

### `vendor/openclaude/src/memdir/` (9 files)

| File | Bytes | Lines |
|---|---:|---:|
| `findRelevantMemories.ts` | 5269 | 140 |
| `memdir.ts` | 21174 | 507 |
| `memoryAge.ts` | 1931 | 53 |
| `memoryScan.test.ts` | 2205 | 59 |
| `memoryScan.ts` | 3401 | 101 |
| `memoryTypes.ts` | 22866 | 271 |
| `paths.ts` | 10668 | 278 |
| `teamMemPaths.ts` | 11690 | 292 |
| `teamMemPrompts.ts` | 5998 | 100 |

### `vendor/openclaude/src/migrations/` (11 files)

| File | Bytes | Lines |
|---|---:|---:|
| `migrateAutoUpdatesToSettings.ts` | 1953 | 61 |
| `migrateBypassPermissionsAcceptedToSettings.ts` | 1262 | 40 |
| `migrateEnableAllProjectMcpServersToSettings.ts` | 3977 | 118 |
| `migrateFennecToOpus.ts` | 1372 | 45 |
| `migrateLegacyOpusToCurrent.ts` | 1974 | 57 |
| `migrateOpusToOpus1m.ts` | 1347 | 43 |
| `migrateReplBridgeEnabledToRemoteControlAtStartup.ts` | 1000 | 22 |
| `migrateSonnet1mToSonnet45.ts` | 1702 | 53 |
| `migrateSonnet45ToSonnet46.ts` | 2055 | 67 |
| `resetAutoModeOptInForDefaultOffer.ts` | 2110 | 51 |
| `resetProToOpusDefault.ts` | 1550 | 51 |

### `vendor/openclaude/src/moreright/` (1 files)

| File | Bytes | Lines |
|---|---:|---:|
| `useMoreRight.tsx` | 855 | 25 |

### `vendor/openclaude/src/native-ts/color-diff/` (1 files)

| File | Bytes | Lines |
|---|---:|---:|
| `index.ts` | 30042 | 999 |

### `vendor/openclaude/src/native-ts/file-index/` (1 files)

| File | Bytes | Lines |
|---|---:|---:|
| `index.ts` | 12006 | 370 |

### `vendor/openclaude/src/native-ts/yoga-layout/` (2 files)

| File | Bytes | Lines |
|---|---:|---:|
| `enums.ts` | 2823 | 134 |
| `index.ts` | 83377 | 2578 |

### `vendor/openclaude/src/outputStyles/` (1 files)

| File | Bytes | Lines |
|---|---:|---:|
| `loadOutputStylesDir.ts` | 3438 | 98 |

### `vendor/openclaude/src/plugins/` (1 files)

| File | Bytes | Lines |
|---|---:|---:|
| `builtinPlugins.ts` | 4980 | 159 |

### `vendor/openclaude/src/plugins/bundled/` (1 files)

| File | Bytes | Lines |
|---|---:|---:|
| `index.ts` | 843 | 23 |

### `vendor/openclaude/src/proto/` (1 files)

| File | Bytes | Lines |
|---|---:|---:|
| `openclaude.proto` | 3166 | 101 |

### `vendor/openclaude/src/query/` (4 files)

| File | Bytes | Lines |
|---|---:|---:|
| `config.ts` | 1782 | 46 |
| `deps.ts` | 1445 | 40 |
| `stopHooks.ts` | 17290 | 473 |
| `tokenBudget.ts` | 2320 | 93 |

### `vendor/openclaude/src/remote/` (4 files)

| File | Bytes | Lines |
|---|---:|---:|
| `RemoteSessionManager.ts` | 9320 | 343 |
| `SessionsWebSocket.ts` | 12505 | 404 |
| `remotePermissionBridge.ts` | 2378 | 78 |
| `sdkMessageAdapter.ts` | 9060 | 302 |

### `vendor/openclaude/src/schemas/` (1 files)

| File | Bytes | Lines |
|---|---:|---:|
| `hooks.ts` | 7884 | 222 |

### `vendor/openclaude/src/screens/` (7 files)

| File | Bytes | Lines |
|---|---:|---:|
| `Doctor.tsx` | 19217 | 574 |
| `REPL.tsx` | 259948 | 5030 |
| `ResumeConversation.tsx` | 16500 | 410 |
| `replInputSuppression.test.ts` | 685 | 18 |
| `replInputSuppression.ts` | 179 | 6 |
| `replStartupGates.test.ts` | 1467 | 53 |
| `replStartupGates.ts` | 1462 | 35 |

### `vendor/openclaude/src/server/` (3 files)

| File | Bytes | Lines |
|---|---:|---:|
| `createDirectConnectSession.ts` | 2193 | 88 |
| `directConnectManager.ts` | 5898 | 213 |
| `types.ts` | 1466 | 57 |

### `vendor/openclaude/src/services/` (18 files)

| File | Bytes | Lines |
|---|---:|---:|
| `awaySummary.ts` | 2671 | 74 |
| `claudeAiLimits.ts` | 16923 | 520 |
| `claudeAiLimitsHook.ts` | 515 | 23 |
| `diagnosticTracking.test.ts` | 5287 | 152 |
| `diagnosticTracking.ts` | 13403 | 439 |
| `internalLogging.ts` | 224 | 9 |
| `mcpServerApproval.tsx` | 1668 | 40 |
| `mockRateLimits.ts` | 6104 | 205 |
| `notifier.ts` | 4256 | 156 |
| `preventSleep.ts` | 4586 | 165 |
| `rateLimitMessages.ts` | 10858 | 344 |
| `rateLimitMocking.ts` | 4420 | 144 |
| `tokenEstimation.ts` | 21284 | 638 |
| `tokenModelCompression.test.ts` | 3346 | 100 |
| `vcr.ts` | 12166 | 406 |
| `voice.ts` | 17116 | 525 |
| `voiceKeyterms.ts` | 3462 | 106 |
| `voiceStreamSTT.ts` | 21375 | 544 |

### `vendor/openclaude/src/services/AgentSummary/` (1 files)

| File | Bytes | Lines |
|---|---:|---:|
| `agentSummary.ts` | 6407 | 179 |

### `vendor/openclaude/src/services/MagicDocs/` (2 files)

| File | Bytes | Lines |
|---|---:|---:|
| `magicDocs.ts` | 7683 | 254 |
| `prompts.ts` | 5595 | 127 |

### `vendor/openclaude/src/services/PromptSuggestion/` (2 files)

| File | Bytes | Lines |
|---|---:|---:|
| `promptSuggestion.ts` | 17065 | 523 |
| `speculation.ts` | 30685 | 991 |

### `vendor/openclaude/src/services/SessionMemory/` (3 files)

| File | Bytes | Lines |
|---|---:|---:|
| `prompts.ts` | 12629 | 324 |
| `sessionMemory.ts` | 16571 | 495 |
| `sessionMemoryUtils.ts` | 6110 | 207 |

### `vendor/openclaude/src/services/analytics/` (9 files)

| File | Bytes | Lines |
|---|---:|---:|
| `config.ts` | 1054 | 33 |
| `datadog.ts` | 9102 | 307 |
| `firstPartyEventLogger.ts` | 14600 | 449 |
| `firstPartyEventLoggingExporter.ts` | 26367 | 806 |
| `growthbook.ts` | 40535 | 1155 |
| `index.ts` | 5542 | 173 |
| `metadata.ts` | 32637 | 973 |
| `sink.ts` | 3547 | 114 |
| `sinkKillswitch.ts` | 1063 | 25 |

### `vendor/openclaude/src/services/api/` (55 files)

| File | Bytes | Lines |
|---|---:|---:|
| `adminRequests.ts` | 3208 | 119 |
| `agentRouting.test.ts` | 4728 | 125 |
| `agentRouting.ts` | 2293 | 75 |
| `bootstrap.ts` | 7099 | 217 |
| `claude.ts` | 127463 | 3445 |
| `client.test.ts` | 8441 | 270 |
| `client.ts` | 18548 | 452 |
| `codexOAuth.test.ts` | 4745 | 166 |
| `codexOAuth.ts` | 9050 | 307 |
| `codexOAuthShared.ts` | 4105 | 139 |
| `codexShim.test.ts` | 29107 | 885 |
| `codexShim.ts` | 27519 | 977 |
| `codexUsage.test.ts` | 4817 | 204 |
| `codexUsage.ts` | 11989 | 455 |
| `compressToolHistory.test.ts` | 18287 | 572 |
| `compressToolHistory.ts` | 9423 | 255 |
| `dumpPrompts.ts` | 607 | 26 |
| `emptyUsage.ts` | 712 | 22 |
| `errorUtils.ts` | 8405 | 260 |
| `errors.openaiCompatibility.test.ts` | 1488 | 44 |
| `errors.ts` | 48090 | 1361 |
| `fetchWithProxyRetry.test.ts` | 2443 | 86 |
| `fetchWithProxyRetry.ts` | 1267 | 44 |
| `filesApi.ts` | 21494 | 748 |
| `firstTokenDate.ts` | 1765 | 60 |
| `grove.ts` | 11543 | 357 |
| `logging.ts` | 24191 | 788 |
| `metricsOptOut.ts` | 5355 | 159 |
| `openaiErrorClassification.test.ts` | 3134 | 97 |
| `openaiErrorClassification.ts` | 9383 | 352 |
| `openaiSchemaSanitizer.ts` | 79 | 1 |
| `openaiShim.compression.test.ts` | 10737 | 317 |
| `openaiShim.diagnostics.test.ts` | 8007 | 286 |
| `openaiShim.test.ts` | 102153 | 3731 |
| `openaiShim.ts` | 73474 | 2163 |
| `overageCreditGrant.ts` | 4913 | 137 |
| `promptCacheBreakDetection.ts` | 26288 | 727 |
| `providerConfig.codexSecureStorage.test.ts` | 7851 | 225 |
| `providerConfig.envDiagnostics.test.ts` | 3637 | 107 |
| `providerConfig.github.test.ts` | 2159 | 58 |
| `providerConfig.local.test.ts` | 4342 | 126 |
| `providerConfig.runtimeCodexCredentials.test.ts` | 3357 | 107 |
| `providerConfig.ts` | 25949 | 903 |
| `referral.ts` | 7985 | 281 |
| `sessionIngress.ts` | 17055 | 514 |
| `smartModelRouting.test.ts` | 5673 | 191 |
| `smartModelRouting.ts` | 5833 | 215 |
| `thinkTagSanitizer.test.ts` | 6240 | 183 |
| `thinkTagSanitizer.ts` | 4761 | 162 |
| `toolArgumentNormalization.test.ts` | 5654 | 180 |
| `toolArgumentNormalization.ts` | 2231 | 69 |
| `ultrareviewQuota.ts` | 1219 | 38 |
| `usage.ts` | 1685 | 63 |
| `withRetry.test.ts` | 6480 | 192 |
| `withRetry.ts` | 30365 | 879 |

### `vendor/openclaude/src/services/autoDream/` (4 files)

| File | Bytes | Lines |
|---|---:|---:|
| `autoDream.ts` | 11264 | 324 |
| `config.ts` | 892 | 21 |
| `consolidationLock.ts` | 4548 | 140 |
| `consolidationPrompt.ts` | 3225 | 65 |

### `vendor/openclaude/src/services/autoFix/` (7 files)

| File | Bytes | Lines |
|---|---:|---:|
| `autoFixConfig.test.ts` | 3391 | 106 |
| `autoFixConfig.ts` | 1327 | 52 |
| `autoFixHook.test.ts` | 2165 | 63 |
| `autoFixHook.ts` | 782 | 25 |
| `autoFixIntegration.test.ts` | 1402 | 48 |
| `autoFixRunner.test.ts` | 2847 | 103 |
| `autoFixRunner.ts` | 4775 | 186 |

### `vendor/openclaude/src/services/compact/` (15 files)

| File | Bytes | Lines |
|---|---:|---:|
| `apiMicrocompact.ts` | 5001 | 153 |
| `autoCompact.test.ts` | 2300 | 55 |
| `autoCompact.ts` | 13665 | 361 |
| `cachedMicrocompact.ts` | 301 | 12 |
| `compact.ts` | 60953 | 1712 |
| `compactWarningHook.ts` | 568 | 16 |
| `compactWarningState.ts` | 693 | 18 |
| `grouping.ts` | 2794 | 63 |
| `microCompact.test.ts` | 4812 | 127 |
| `microCompact.ts` | 19764 | 536 |
| `postCompactCleanup.ts` | 3778 | 77 |
| `prompt.ts` | 16278 | 374 |
| `sessionMemoryCompact.ts` | 21063 | 630 |
| `snipCompact.ts` | 104 | 4 |
| `timeBasedMCConfig.ts` | 1766 | 43 |

### `vendor/openclaude/src/services/contextCollapse/` (1 files)

| File | Bytes | Lines |
|---|---:|---:|
| `index.ts` | 207 | 7 |

### `vendor/openclaude/src/services/extractMemories/` (2 files)

| File | Bytes | Lines |
|---|---:|---:|
| `extractMemories.ts` | 21684 | 615 |
| `prompts.ts` | 7673 | 154 |

### `vendor/openclaude/src/services/github/` (2 files)

| File | Bytes | Lines |
|---|---:|---:|
| `deviceFlow.test.ts` | 6306 | 229 |
| `deviceFlow.ts` | 7878 | 263 |

### `vendor/openclaude/src/services/lsp/` (7 files)

| File | Bytes | Lines |
|---|---:|---:|
| `LSPClient.ts` | 14361 | 447 |
| `LSPDiagnosticRegistry.ts` | 11957 | 386 |
| `LSPServerInstance.ts` | 16864 | 511 |
| `LSPServerManager.ts` | 13394 | 420 |
| `config.ts` | 2857 | 79 |
| `manager.ts` | 10067 | 289 |
| `passiveFeedback.ts` | 11190 | 328 |

### `vendor/openclaude/src/services/mcp/` (28 files)

| File | Bytes | Lines |
|---|---:|---:|
| `InProcessTransport.ts` | 1772 | 63 |
| `MCPConnectionManager.tsx` | 2254 | 72 |
| `SdkControlTransport.ts` | 4503 | 136 |
| `auth.test.ts` | 1529 | 61 |
| `auth.ts` | 90545 | 2531 |
| `channelAllowlist.ts` | 2838 | 76 |
| `channelNotification.ts` | 12540 | 316 |
| `channelPermissions.ts` | 8981 | 240 |
| `claudeai.ts` | 6521 | 174 |
| `client.test.ts` | 1100 | 48 |
| `client.ts` | 120912 | 3398 |
| `config.ts` | 51130 | 1578 |
| `doctor.test.ts` | 17665 | 540 |
| `doctor.ts` | 21350 | 695 |
| `elicitationHandler.ts` | 10166 | 313 |
| `envExpansion.ts` | 1047 | 38 |
| `headersHelper.ts` | 4718 | 138 |
| `mcpStringUtils.ts` | 3968 | 106 |
| `normalization.ts` | 879 | 23 |
| `oauthPort.ts` | 2325 | 78 |
| `officialRegistry.test.ts` | 2208 | 72 |
| `officialRegistry.ts` | 2218 | 78 |
| `types.ts` | 6962 | 258 |
| `useManageMCPConnections.ts` | 44866 | 1141 |
| `utils.ts` | 17931 | 575 |
| `vscodeSdkMcp.ts` | 3703 | 112 |
| `xaa.ts` | 18286 | 511 |
| `xaaIdpLogin.ts` | 16271 | 487 |

### `vendor/openclaude/src/services/oauth/` (8 files)

| File | Bytes | Lines |
|---|---:|---:|
| `auth-code-listener.analytics.test.ts` | 3957 | 155 |
| `auth-code-listener.test.ts` | 726 | 31 |
| `auth-code-listener.ts` | 8283 | 274 |
| `client.ts` | 18254 | 566 |
| `crypto.test.ts` | 796 | 27 |
| `crypto.ts` | 646 | 23 |
| `getOauthProfile.ts` | 1611 | 53 |
| `index.ts` | 6560 | 198 |

### `vendor/openclaude/src/services/plugins/` (3 files)

| File | Bytes | Lines |
|---|---:|---:|
| `PluginInstallationManager.ts` | 6017 | 184 |
| `pluginCliCommands.ts` | 10894 | 344 |
| `pluginOperations.ts` | 35619 | 1088 |

### `vendor/openclaude/src/services/policyLimits/` (2 files)

| File | Bytes | Lines |
|---|---:|---:|
| `index.ts` | 18064 | 663 |
| `types.ts` | 792 | 27 |

### `vendor/openclaude/src/services/remoteManagedSettings/` (5 files)

| File | Bytes | Lines |
|---|---:|---:|
| `index.ts` | 20911 | 638 |
| `securityCheck.tsx` | 3101 | 73 |
| `syncCache.ts` | 4229 | 112 |
| `syncCacheState.ts` | 4004 | 96 |
| `types.ts` | 1060 | 31 |

### `vendor/openclaude/src/services/settingsSync/` (2 files)

| File | Bytes | Lines |
|---|---:|---:|
| `index.ts` | 17924 | 581 |
| `types.ts` | 1668 | 67 |

### `vendor/openclaude/src/services/teamMemorySync/` (5 files)

| File | Bytes | Lines |
|---|---:|---:|
| `index.ts` | 44153 | 1256 |
| `secretScanner.ts` | 9458 | 324 |
| `teamMemSecretGuard.ts` | 1552 | 44 |
| `types.ts` | 4906 | 156 |
| `watcher.ts` | 13405 | 387 |

### `vendor/openclaude/src/services/tips/` (3 files)

| File | Bytes | Lines |
|---|---:|---:|
| `tipHistory.ts` | 601 | 17 |
| `tipRegistry.ts` | 22259 | 661 |
| `tipScheduler.ts` | 1664 | 58 |

### `vendor/openclaude/src/services/toolUseSummary/` (1 files)

| File | Bytes | Lines |
|---|---:|---:|
| `toolUseSummaryGenerator.ts` | 3376 | 112 |

### `vendor/openclaude/src/services/tools/` (5 files)

| File | Bytes | Lines |
|---|---:|---:|
| `StreamingToolExecutor.ts` | 17196 | 530 |
| `toolExecution.test.ts` | 1269 | 33 |
| `toolExecution.ts` | 61696 | 1788 |
| `toolHooks.ts` | 25190 | 717 |
| `toolOrchestration.ts` | 5501 | 188 |

### `vendor/openclaude/src/services/wiki/` (10 files)

| File | Bytes | Lines |
|---|---:|---:|
| `indexBuilder.ts` | 1942 | 68 |
| `ingest.test.ts` | 1666 | 48 |
| `ingest.ts` | 2398 | 93 |
| `init.test.ts` | 1695 | 54 |
| `init.ts` | 3522 | 140 |
| `paths.ts` | 488 | 18 |
| `status.test.ts` | 1675 | 55 |
| `status.ts` | 1922 | 82 |
| `types.ts` | 585 | 33 |
| `utils.ts` | 825 | 36 |

### `vendor/openclaude/src/skills/` (4 files)

| File | Bytes | Lines |
|---|---:|---:|
| `bundledSkills.ts` | 7497 | 220 |
| `loadSkillsDir.test.ts` | 2109 | 64 |
| `loadSkillsDir.ts` | 36519 | 1171 |
| `mcpSkillBuilders.ts` | 1627 | 44 |

### `vendor/openclaude/src/skills/bundled/` (15 files)

| File | Bytes | Lines |
|---|---:|---:|
| `batch.ts` | 7177 | 124 |
| `claudeApi.ts` | 6323 | 196 |
| `claudeApiContent.ts` | 4280 | 75 |
| `claudeInChrome.ts` | 1760 | 34 |
| `debug.ts` | 4219 | 103 |
| `index.ts` | 2663 | 65 |
| `keybindings.ts` | 10412 | 339 |
| `loop.test.ts` | 4876 | 125 |
| `loop.ts` | 7476 | 223 |
| `scheduleRemoteAgents.ts` | 19048 | 447 |
| `simplify.ts` | 4466 | 69 |
| `stuck.ts` | 46 | 1 |
| `updateConfig.test.ts` | 786 | 23 |
| `updateConfig.ts` | 17453 | 475 |
| `verifyContent.ts` | 414 | 13 |

### `vendor/openclaude/src/state/` (7 files)

| File | Bytes | Lines |
|---|---:|---:|
| `AppState.tsx` | 6733 | 191 |
| `AppStateStore.ts` | 21847 | 569 |
| `onChangeAppState.ts` | 6623 | 179 |
| `pluginCommandsStore.ts` | 425 | 13 |
| `selectors.ts` | 2240 | 76 |
| `store.ts` | 836 | 34 |
| `teammateViewHelpers.ts` | 4399 | 141 |

### `vendor/openclaude/src/tasks/` (4 files)

| File | Bytes | Lines |
|---|---:|---:|
| `LocalMainSessionTask.ts` | 15103 | 478 |
| `pillLabel.ts` | 2898 | 82 |
| `stopTask.ts` | 2894 | 100 |
| `types.ts` | 1691 | 46 |

### `vendor/openclaude/src/tasks/DreamTask/` (1 files)

| File | Bytes | Lines |
|---|---:|---:|
| `DreamTask.ts` | 4988 | 157 |

### `vendor/openclaude/src/tasks/InProcessTeammateTask/` (2 files)

| File | Bytes | Lines |
|---|---:|---:|
| `InProcessTeammateTask.tsx` | 4737 | 125 |
| `types.ts` | 4322 | 121 |

### `vendor/openclaude/src/tasks/LocalAgentTask/` (1 files)

| File | Bytes | Lines |
|---|---:|---:|
| `LocalAgentTask.tsx` | 23398 | 682 |

### `vendor/openclaude/src/tasks/LocalShellTask/` (3 files)

| File | Bytes | Lines |
|---|---:|---:|
| `LocalShellTask.tsx` | 18650 | 522 |
| `guards.ts` | 1552 | 41 |
| `killShellTasks.ts` | 2565 | 76 |

### `vendor/openclaude/src/tasks/MonitorMcpTask/` (1 files)

| File | Bytes | Lines |
|---|---:|---:|
| `MonitorMcpTask.ts` | 3448 | 102 |

### `vendor/openclaude/src/tasks/RemoteAgentTask/` (1 files)

| File | Bytes | Lines |
|---|---:|---:|
| `RemoteAgentTask.tsx` | 36929 | 855 |

### `vendor/openclaude/src/tools/` (2 files)

| File | Bytes | Lines |
|---|---:|---:|
| `shellToolResultMappers.test.ts` | 1626 | 71 |
| `utils.ts` | 1105 | 40 |

### `vendor/openclaude/src/tools/AgentTool/` (14 files)

| File | Bytes | Lines |
|---|---:|---:|
| `AgentTool.tsx` | 69891 | 1412 |
| `UI.tsx` | 32736 | 871 |
| `agentColorManager.ts` | 1499 | 66 |
| `agentDisplay.ts` | 3269 | 104 |
| `agentMemory.ts` | 5853 | 177 |
| `agentMemorySnapshot.ts` | 5633 | 197 |
| `agentToolUtils.ts` | 22739 | 686 |
| `builtInAgents.ts` | 2756 | 72 |
| `constants.ts` | 547 | 12 |
| `forkSubagent.ts` | 8678 | 210 |
| `loadAgentsDir.ts` | 26230 | 755 |
| `prompt.ts` | 16406 | 277 |
| `resumeAgent.ts` | 9339 | 265 |
| `runAgent.ts` | 36330 | 987 |

### `vendor/openclaude/src/tools/AgentTool/built-in/` (6 files)

| File | Bytes | Lines |
|---|---:|---:|
| `claudeCodeGuideAgent.ts` | 8965 | 205 |
| `exploreAgent.ts` | 4493 | 82 |
| `generalPurposeAgent.ts` | 2184 | 34 |
| `planAgent.ts` | 4317 | 92 |
| `statuslineSetup.ts` | 7793 | 148 |
| `verificationAgent.ts` | 11410 | 152 |

### `vendor/openclaude/src/tools/AskUserQuestionTool/` (2 files)

| File | Bytes | Lines |
|---|---:|---:|
| `AskUserQuestionTool.tsx` | 10787 | 265 |
| `prompt.ts` | 2903 | 44 |

### `vendor/openclaude/src/tools/BashTool/` (22 files)

| File | Bytes | Lines |
|---|---:|---:|
| `BashTool.tsx` | 47242 | 1152 |
| `BashToolResultMessage.tsx` | 5906 | 191 |
| `UI.tsx` | 6453 | 184 |
| `bashCommandHelpers.ts` | 8589 | 265 |
| `bashPermissions.test.ts` | 1957 | 59 |
| `bashPermissions.ts` | 97754 | 2601 |
| `bashSecurity.ts` | 102561 | 2592 |
| `commandSemantics.ts` | 3658 | 140 |
| `commentLabel.ts` | 637 | 13 |
| `destructiveCommandWarning.ts` | 2935 | 102 |
| `modeValidation.test.ts` | 1216 | 44 |
| `modeValidation.ts` | 6246 | 213 |
| `pathValidation.ts` | 43686 | 1303 |
| `prompt.ts` | 19339 | 337 |
| `readOnlyValidation.ts` | 66418 | 1924 |
| `sedEditParser.test.ts` | 976 | 40 |
| `sedEditParser.ts` | 8525 | 323 |
| `sedValidation.ts` | 21518 | 684 |
| `shouldUseSandbox.test.ts` | 2297 | 74 |
| `shouldUseSandbox.ts` | 5619 | 167 |
| `toolName.ts` | 89 | 2 |
| `utils.ts` | 7207 | 223 |

### `vendor/openclaude/src/tools/BriefTool/` (5 files)

| File | Bytes | Lines |
|---|---:|---:|
| `BriefTool.ts` | 7677 | 204 |
| `UI.tsx` | 3827 | 100 |
| `attachments.ts` | 3889 | 110 |
| `prompt.ts` | 1933 | 22 |
| `upload.ts` | 5815 | 174 |

### `vendor/openclaude/src/tools/ConfigTool/` (5 files)

| File | Bytes | Lines |
|---|---:|---:|
| `ConfigTool.ts` | 13478 | 467 |
| `UI.tsx` | 1317 | 37 |
| `constants.ts` | 41 | 1 |
| `prompt.ts` | 2885 | 93 |
| `supportedSettings.ts` | 6374 | 211 |

### `vendor/openclaude/src/tools/EnterPlanModeTool/` (4 files)

| File | Bytes | Lines |
|---|---:|---:|
| `EnterPlanModeTool.ts` | 4101 | 126 |
| `UI.tsx` | 1303 | 32 |
| `constants.ts` | 57 | 1 |
| `prompt.ts` | 4683 | 103 |

### `vendor/openclaude/src/tools/EnterWorktreeTool/` (4 files)

| File | Bytes | Lines |
|---|---:|---:|
| `EnterWorktreeTool.ts` | 4364 | 127 |
| `UI.tsx` | 780 | 19 |
| `constants.ts` | 56 | 1 |
| `prompt.ts` | 1412 | 30 |

### `vendor/openclaude/src/tools/ExitPlanModeTool/` (4 files)

| File | Bytes | Lines |
|---|---:|---:|
| `ExitPlanModeV2Tool.ts` | 17006 | 493 |
| `UI.tsx` | 2910 | 81 |
| `constants.ts` | 113 | 2 |
| `prompt.ts` | 2139 | 29 |

### `vendor/openclaude/src/tools/ExitWorktreeTool/` (4 files)

| File | Bytes | Lines |
|---|---:|---:|
| `ExitWorktreeTool.ts` | 11649 | 329 |
| `UI.tsx` | 956 | 24 |
| `constants.ts` | 54 | 1 |
| `prompt.ts` | 2021 | 32 |

### `vendor/openclaude/src/tools/FileEditTool/` (6 files)

| File | Bytes | Lines |
|---|---:|---:|
| `FileEditTool.ts` | 20574 | 628 |
| `UI.tsx` | 9276 | 288 |
| `constants.ts` | 538 | 11 |
| `prompt.ts` | 1897 | 28 |
| `types.ts` | 2612 | 85 |
| `utils.ts` | 22516 | 775 |

### `vendor/openclaude/src/tools/FileReadTool/` (5 files)

| File | Bytes | Lines |
|---|---:|---:|
| `FileReadTool.ts` | 39162 | 1186 |
| `UI.tsx` | 5960 | 184 |
| `imageProcessor.ts` | 3735 | 117 |
| `limits.ts` | 3219 | 92 |
| `prompt.ts` | 2868 | 49 |

### `vendor/openclaude/src/tools/FileWriteTool/` (3 files)

| File | Bytes | Lines |
|---|---:|---:|
| `FileWriteTool.ts` | 15019 | 437 |
| `UI.tsx` | 12044 | 404 |
| `prompt.ts` | 969 | 18 |

### `vendor/openclaude/src/tools/GlobTool/` (3 files)

| File | Bytes | Lines |
|---|---:|---:|
| `GlobTool.ts` | 6064 | 198 |
| `UI.tsx` | 2052 | 62 |
| `prompt.ts` | 439 | 7 |

### `vendor/openclaude/src/tools/GrepTool/` (3 files)

| File | Bytes | Lines |
|---|---:|---:|
| `GrepTool.ts` | 20087 | 577 |
| `UI.tsx` | 5740 | 200 |
| `prompt.ts` | 1150 | 18 |

### `vendor/openclaude/src/tools/LSPTool/` (6 files)

| File | Bytes | Lines |
|---|---:|---:|
| `LSPTool.ts` | 25710 | 860 |
| `UI.tsx` | 6834 | 227 |
| `formatters.ts` | 17399 | 592 |
| `prompt.ts` | 1114 | 21 |
| `schemas.ts` | 6064 | 215 |
| `symbolContext.ts` | 3392 | 90 |

### `vendor/openclaude/src/tools/ListMcpResourcesTool/` (3 files)

| File | Bytes | Lines |
|---|---:|---:|
| `ListMcpResourcesTool.ts` | 3907 | 123 |
| `UI.tsx` | 1205 | 28 |
| `prompt.ts` | 776 | 20 |

### `vendor/openclaude/src/tools/MCPTool/` (4 files)

| File | Bytes | Lines |
|---|---:|---:|
| `MCPTool.ts` | 3593 | 127 |
| `UI.tsx` | 13802 | 402 |
| `classifyForCollapse.ts` | 15178 | 604 |
| `prompt.ts` | 119 | 3 |

### `vendor/openclaude/src/tools/McpAuthTool/` (1 files)

| File | Bytes | Lines |
|---|---:|---:|
| `McpAuthTool.ts` | 7873 | 215 |

### `vendor/openclaude/src/tools/MonitorTool/` (1 files)

| File | Bytes | Lines |
|---|---:|---:|
| `MonitorTool.ts` | 5678 | 195 |

### `vendor/openclaude/src/tools/NotebookEditTool/` (4 files)

| File | Bytes | Lines |
|---|---:|---:|
| `NotebookEditTool.ts` | 15271 | 490 |
| `UI.tsx` | 3344 | 92 |
| `constants.ts` | 104 | 2 |
| `prompt.ts` | 632 | 3 |

### `vendor/openclaude/src/tools/PowerShellTool/` (14 files)

| File | Bytes | Lines |
|---|---:|---:|
| `PowerShellTool.tsx` | 43611 | 1013 |
| `UI.tsx` | 4872 | 130 |
| `clmTypes.ts` | 7229 | 211 |
| `commandSemantics.ts` | 5459 | 142 |
| `commonParameters.ts` | 894 | 30 |
| `destructiveCommandWarning.ts` | 3402 | 109 |
| `gitSafety.ts` | 7695 | 176 |
| `modeValidation.ts` | 17399 | 404 |
| `pathValidation.ts` | 73059 | 2049 |
| `powershellPermissions.ts` | 67606 | 1648 |
| `powershellSecurity.ts` | 37651 | 1090 |
| `prompt.ts` | 9826 | 145 |
| `readOnlyValidation.ts` | 67327 | 1823 |
| `toolName.ts` | 110 | 2 |

### `vendor/openclaude/src/tools/REPLTool/` (3 files)

| File | Bytes | Lines |
|---|---:|---:|
| `REPLTool.ts` | 57 | 3 |
| `constants.ts` | 1799 | 46 |
| `primitiveTools.ts` | 1532 | 39 |

### `vendor/openclaude/src/tools/ReadMcpResourceTool/` (3 files)

| File | Bytes | Lines |
|---|---:|---:|
| `ReadMcpResourceTool.ts` | 4654 | 158 |
| `UI.tsx` | 1529 | 36 |
| `prompt.ts` | 544 | 16 |

### `vendor/openclaude/src/tools/RemoteTriggerTool/` (3 files)

| File | Bytes | Lines |
|---|---:|---:|
| `RemoteTriggerTool.ts` | 4715 | 161 |
| `UI.tsx` | 704 | 16 |
| `prompt.ts` | 697 | 15 |

### `vendor/openclaude/src/tools/ScheduleCronTool/` (5 files)

| File | Bytes | Lines |
|---|---:|---:|
| `CronCreateTool.ts` | 5710 | 157 |
| `CronDeleteTool.ts` | 2616 | 95 |
| `CronListTool.ts` | 2888 | 97 |
| `UI.tsx` | 1987 | 59 |
| `prompt.ts` | 7053 | 131 |

### `vendor/openclaude/src/tools/SendMessageTool/` (4 files)

| File | Bytes | Lines |
|---|---:|---:|
| `SendMessageTool.ts` | 28405 | 935 |
| `UI.tsx` | 1127 | 30 |
| `constants.ts` | 52 | 1 |
| `prompt.ts` | 2356 | 49 |

### `vendor/openclaude/src/tools/SkillTool/` (5 files)

| File | Bytes | Lines |
|---|---:|---:|
| `SkillTool.test.ts` | 2597 | 98 |
| `SkillTool.ts` | 38498 | 1118 |
| `UI.tsx` | 4933 | 130 |
| `constants.ts` | 39 | 1 |
| `prompt.ts` | 8221 | 241 |

### `vendor/openclaude/src/tools/SleepTool/` (1 files)

| File | Bytes | Lines |
|---|---:|---:|
| `prompt.ts` | 774 | 17 |

### `vendor/openclaude/src/tools/SuggestBackgroundPRTool/` (1 files)

| File | Bytes | Lines |
|---|---:|---:|
| `SuggestBackgroundPRTool.ts` | 72 | 3 |

### `vendor/openclaude/src/tools/SyntheticOutputTool/` (1 files)

| File | Bytes | Lines |
|---|---:|---:|
| `SyntheticOutputTool.ts` | 5468 | 163 |

### `vendor/openclaude/src/tools/TaskCreateTool/` (3 files)

| File | Bytes | Lines |
|---|---:|---:|
| `TaskCreateTool.ts` | 3441 | 138 |
| `constants.ts` | 50 | 1 |
| `prompt.ts` | 2760 | 56 |

### `vendor/openclaude/src/tools/TaskGetTool/` (3 files)

| File | Bytes | Lines |
|---|---:|---:|
| `TaskGetTool.ts` | 2881 | 128 |
| `constants.ts` | 44 | 1 |
| `prompt.ts` | 823 | 24 |

### `vendor/openclaude/src/tools/TaskListTool/` (3 files)

| File | Bytes | Lines |
|---|---:|---:|
| `TaskListTool.ts` | 2803 | 116 |
| `constants.ts` | 46 | 1 |
| `prompt.ts` | 2066 | 49 |

### `vendor/openclaude/src/tools/TaskOutputTool/` (2 files)

| File | Bytes | Lines |
|---|---:|---:|
| `TaskOutputTool.tsx` | 18324 | 583 |
| `constants.ts` | 50 | 1 |

### `vendor/openclaude/src/tools/TaskStopTool/` (3 files)

| File | Bytes | Lines |
|---|---:|---:|
| `TaskStopTool.ts` | 3935 | 131 |
| `UI.tsx` | 1380 | 40 |
| `prompt.ts` | 280 | 8 |

### `vendor/openclaude/src/tools/TaskUpdateTool/` (3 files)

| File | Bytes | Lines |
|---|---:|---:|
| `TaskUpdateTool.ts` | 12161 | 406 |
| `constants.ts` | 50 | 1 |
| `prompt.ts` | 2375 | 77 |

### `vendor/openclaude/src/tools/TeamCreateTool/` (4 files)

| File | Bytes | Lines |
|---|---:|---:|
| `TeamCreateTool.ts` | 7665 | 240 |
| `UI.tsx` | 202 | 5 |
| `constants.ts` | 50 | 1 |
| `prompt.ts` | 6900 | 113 |

### `vendor/openclaude/src/tools/TeamDeleteTool/` (4 files)

| File | Bytes | Lines |
|---|---:|---:|
| `TeamDeleteTool.ts` | 4221 | 139 |
| `UI.tsx` | 698 | 19 |
| `constants.ts` | 50 | 1 |
| `prompt.ts` | 684 | 16 |

### `vendor/openclaude/src/tools/TodoWriteTool/` (3 files)

| File | Bytes | Lines |
|---|---:|---:|
| `TodoWriteTool.ts` | 3881 | 115 |
| `constants.ts` | 48 | 1 |
| `prompt.ts` | 9527 | 184 |

### `vendor/openclaude/src/tools/ToolSearchTool/` (3 files)

| File | Bytes | Lines |
|---|---:|---:|
| `ToolSearchTool.ts` | 14275 | 471 |
| `constants.ts` | 50 | 1 |
| `prompt.ts` | 5227 | 121 |

### `vendor/openclaude/src/tools/TungstenTool/` (2 files)

| File | Bytes | Lines |
|---|---:|---:|
| `TungstenLiveMonitor.ts` | 113 | 2 |
| `TungstenTool.ts` | 41 | 2 |

### `vendor/openclaude/src/tools/VerifyPlanExecutionTool/` (1 files)

| File | Bytes | Lines |
|---|---:|---:|
| `VerifyPlanExecutionTool.ts` | 72 | 3 |

### `vendor/openclaude/src/tools/WebFetchTool/` (7 files)

| File | Bytes | Lines |
|---|---:|---:|
| `UI.tsx` | 1923 | 71 |
| `WebFetchTool.ts` | 10336 | 351 |
| `applyPromptFallback.test.ts` | 3011 | 87 |
| `domainCheck.test.ts` | 2690 | 83 |
| `preapproved.ts` | 5248 | 166 |
| `prompt.ts` | 2200 | 46 |
| `utils.ts` | 21355 | 663 |

### `vendor/openclaude/src/tools/WebSearchTool/` (4 files)

| File | Bytes | Lines |
|---|---:|---:|
| `README_SEARCH_PROVIDERS.md` | 10968 | 518 |
| `UI.tsx` | 2988 | 100 |
| `WebSearchTool.ts` | 27647 | 873 |
| `prompt.ts` | 1545 | 34 |

### `vendor/openclaude/src/tools/WebSearchTool/providers/` (16 files)

| File | Bytes | Lines |
|---|---:|---:|
| `bing.ts` | 1317 | 47 |
| `custom.test.ts` | 10085 | 268 |
| `custom.ts` | 20073 | 596 |
| `duckduckgo.test.ts` | 549 | 15 |
| `duckduckgo.ts` | 3479 | 100 |
| `exa.ts` | 1603 | 58 |
| `firecrawl.ts` | 1359 | 41 |
| `index.test.ts` | 5550 | 160 |
| `index.ts` | 6353 | 192 |
| `jina.ts` | 1385 | 50 |
| `linkup.ts` | 1446 | 52 |
| `mojeek.ts` | 1573 | 54 |
| `tavily.ts` | 1420 | 53 |
| `types.test.ts` | 7495 | 229 |
| `types.ts` | 4059 | 119 |
| `you.ts` | 1494 | 52 |

### `vendor/openclaude/src/tools/WorkflowTool/` (1 files)

| File | Bytes | Lines |
|---|---:|---:|
| `constants.ts` | 106 | 2 |

### `vendor/openclaude/src/tools/shared/` (2 files)

| File | Bytes | Lines |
|---|---:|---:|
| `gitOperationTracking.ts` | 9485 | 277 |
| `spawnMultiAgent.ts` | 37275 | 1151 |

### `vendor/openclaude/src/tools/testing/` (1 files)

| File | Bytes | Lines |
|---|---:|---:|
| `TestingPermissionTool.tsx` | 1808 | 73 |

### `vendor/openclaude/src/types/` (8 files)

| File | Bytes | Lines |
|---|---:|---:|
| `command.ts` | 7736 | 216 |
| `connectorText.ts` | 497 | 22 |
| `hooks.ts` | 9143 | 290 |
| `ids.ts` | 1295 | 44 |
| `logs.ts` | 11291 | 330 |
| `permissions.ts` | 13145 | 441 |
| `plugin.ts` | 11308 | 363 |
| `textInputTypes.ts` | 11697 | 389 |

### `vendor/openclaude/src/types/generated/events_mono/claude_code/v1/` (1 files)

| File | Bytes | Lines |
|---|---:|---:|
| `claude_code_internal_event.ts` | 3399 | 108 |

### `vendor/openclaude/src/types/generated/events_mono/common/v1/` (1 files)

| File | Bytes | Lines |
|---|---:|---:|
| `auth.ts` | 533 | 25 |

### `vendor/openclaude/src/types/generated/events_mono/growthbook/v1/` (1 files)

| File | Bytes | Lines |
|---|---:|---:|
| `growthbook_experiment_event.ts` | 1032 | 40 |

### `vendor/openclaude/src/types/generated/google/protobuf/` (1 files)

| File | Bytes | Lines |
|---|---:|---:|
| `timestamp.ts` | 287 | 19 |

### `vendor/openclaude/src/upstreamproxy/` (3 files)

| File | Bytes | Lines |
|---|---:|---:|
| `relay.ts` | 14937 | 455 |
| `upstreamproxy.test.ts` | 1677 | 42 |
| `upstreamproxy.ts` | 10464 | 304 |

### `vendor/openclaude/src/utils/` (370 files)

| File | Bytes | Lines |
|---|---:|---:|
| `CircularBuffer.ts` | 1888 | 84 |
| `Cursor.ts` | 46757 | 1554 |
| `QueryGuard.ts` | 3597 | 121 |
| `Shell.ts` | 16929 | 474 |
| `ShellCommand.ts` | 14138 | 465 |
| `abortController.ts` | 3364 | 99 |
| `activityManager.ts` | 4973 | 164 |
| `advisor.ts` | 5585 | 145 |
| `agentContext.ts` | 6660 | 178 |
| `agentId.ts` | 2805 | 99 |
| `agentSwarmsEnabled.ts` | 1417 | 44 |
| `agenticSessionSearch.ts` | 10067 | 307 |
| `analyzeContext.ts` | 42936 | 1382 |
| `ansiToPng.ts` | 214955 | 334 |
| `ansiToSvg.ts` | 8212 | 272 |
| `api.test.ts` | 2883 | 105 |
| `api.ts` | 27283 | 763 |
| `apiPreconnect.test.ts` | 2729 | 83 |
| `apiPreconnect.ts` | 3026 | 77 |
| `appleTerminalBackup.ts` | 2798 | 124 |
| `argumentSubstitution.ts` | 5079 | 145 |
| `array.ts` | 364 | 13 |
| `asciicast.ts` | 520 | 18 |
| `attachments.extractors.test.ts` | 3553 | 85 |
| `attachments.ts` | 128410 | 4017 |
| `attribution.ts` | 13685 | 399 |
| `auth.ts` | 66076 | 2012 |
| `authFileDescriptor.ts` | 6787 | 196 |
| `authPortable.ts` | 674 | 19 |
| `autoModeDenials.ts` | 720 | 26 |
| `autoRunIssue.tsx` | 3084 | 121 |
| `autoUpdater.ts` | 18271 | 568 |
| `aws.ts` | 2305 | 74 |
| `awsAuthStatusManager.ts` | 2043 | 81 |
| `backgroundHousekeeping.ts` | 3213 | 94 |
| `betas.ts` | 15682 | 434 |
| `billing.ts` | 2413 | 78 |
| `binaryCheck.ts` | 1466 | 53 |
| `browser.ts` | 1867 | 68 |
| `bufferedWriter.ts` | 2584 | 100 |
| `buildConfig.test.ts` | 789 | 20 |
| `buildConfig.ts` | 654 | 18 |
| `bundledMode.ts` | 618 | 22 |
| `caCerts.ts` | 4401 | 115 |
| `caCertsConfig.ts` | 3616 | 88 |
| `cachePaths.ts` | 1411 | 38 |
| `classifierApprovals.ts` | 2448 | 88 |
| `classifierApprovalsHook.ts` | 531 | 17 |
| `claudeCodeHints.ts` | 6472 | 193 |
| `claudeDesktop.ts` | 4063 | 152 |
| `claudemd.ts` | 47030 | 1502 |
| `cleanup.ts` | 17770 | 602 |
| `cleanupRegistry.ts` | 900 | 25 |
| `cliArgs.ts` | 2067 | 60 |
| `cliHighlight.ts` | 2140 | 54 |
| `codeIndexing.ts` | 6110 | 206 |
| `codexCredentials.test.ts` | 18138 | 607 |
| `codexCredentials.ts` | 10034 | 375 |
| `collapseBackgroundBashNotifications.ts` | 2750 | 84 |
| `collapseHookSummaries.ts` | 1714 | 59 |
| `collapseReadSearch.ts` | 37902 | 1109 |
| `collapseTeammateShutdowns.ts` | 1322 | 55 |
| `combinedAbortSignal.ts` | 1714 | 47 |
| `commandLifecycle.ts` | 440 | 21 |
| `commitAttribution.ts` | 29594 | 961 |
| `completionCache.ts` | 5654 | 166 |
| `concurrentSessions.ts` | 6808 | 204 |
| `config.ts` | 65223 | 1861 |
| `configConstants.ts` | 813 | 23 |
| `contentArray.ts` | 1621 | 51 |
| `context.test.ts` | 8919 | 256 |
| `context.ts` | 8692 | 261 |
| `contextAnalysis.ts` | 7733 | 272 |
| `contextSuggestions.ts` | 7258 | 235 |
| `controlMessageCompat.ts` | 1216 | 32 |
| `conversationRecovery.hooks.test.ts` | 5200 | 161 |
| `conversationRecovery.test.ts` | 2280 | 79 |
| `conversationRecovery.ts` | 23719 | 663 |
| `cron.ts` | 9462 | 308 |
| `cronJitterConfig.ts` | 3414 | 75 |
| `cronScheduler.ts` | 21478 | 565 |
| `cronTasks.ts` | 17301 | 458 |
| `cronTasksLock.ts` | 6259 | 195 |
| `crossProjectResume.ts` | 2104 | 75 |
| `crypto.ts` | 763 | 13 |
| `cwd.ts` | 985 | 32 |
| `debug.ts` | 7862 | 260 |
| `debugFilter.ts` | 5089 | 157 |
| `desktopDeepLink.ts` | 7130 | 236 |
| `detectRepository.ts` | 6063 | 178 |
| `diagLogs.ts` | 2784 | 94 |
| `diff.ts` | 4855 | 177 |
| `directMemberMessage.ts` | 1715 | 69 |
| `displayTags.ts` | 2256 | 51 |
| `doctorContextWarnings.ts` | 8071 | 265 |
| `doctorDiagnostic.ts` | 21050 | 647 |
| `dragDropPaths.test.ts` | 4470 | 110 |
| `dragDropPaths.ts` | 1917 | 55 |
| `earlyInput.ts` | 5398 | 191 |
| `editor.ts` | 6634 | 183 |
| `effort.codex.test.ts` | 1878 | 65 |
| `effort.ts` | 13265 | 386 |
| `embeddedTools.ts` | 1043 | 29 |
| `env.test.ts` | 2249 | 62 |
| `env.ts` | 11487 | 360 |
| `envDynamic.ts` | 5278 | 151 |
| `envUtils.ts` | 7126 | 209 |
| `envValidation.ts` | 1045 | 38 |
| `errorLogSink.ts` | 6557 | 235 |
| `errors.ts` | 7655 | 238 |
| `exampleCommands.ts` | 6200 | 184 |
| `execFileNoThrow.test.ts` | 2269 | 65 |
| `execFileNoThrow.ts` | 8286 | 332 |
| `execFileNoThrowPortable.ts` | 2685 | 89 |
| `execSyncWrapper.ts` | 1203 | 38 |
| `exportRenderer.tsx` | 4527 | 97 |
| `extraUsage.ts` | 635 | 23 |
| `fastMode.test.ts` | 4615 | 162 |
| `fastMode.ts` | 17466 | 529 |
| `file.test.ts` | 1532 | 51 |
| `file.ts` | 18258 | 584 |
| `fileHistory.ts` | 34660 | 1115 |
| `fileOperationAnalytics.ts` | 2287 | 71 |
| `fileRead.ts` | 3168 | 102 |
| `fileReadCache.ts` | 2432 | 96 |
| `fileStateCache.ts` | 4175 | 142 |
| `findExecutable.ts` | 553 | 17 |
| `fingerprint.ts` | 2582 | 82 |
| `forkedAgent.ts` | 24635 | 689 |
| `format.ts` | 9375 | 308 |
| `formatBriefTimestamp.ts` | 2223 | 81 |
| `fpsTracker.ts` | 1299 | 47 |
| `frontmatterParser.ts` | 12404 | 370 |
| `fsOperations.ts` | 24230 | 770 |
| `fullscreen.ts` | 9252 | 214 |
| `geminiAuth.test.ts` | 5605 | 186 |
| `geminiAuth.ts` | 5789 | 216 |
| `geminiCredentials.test.ts` | 1741 | 64 |
| `geminiCredentials.ts` | 2085 | 76 |
| `generatedFiles.ts` | 3481 | 136 |
| `generators.ts` | 2156 | 88 |
| `genericProcessUtils.ts` | 6403 | 184 |
| `getWorktreePaths.ts` | 2048 | 70 |
| `getWorktreePathsPortable.ts` | 847 | 27 |
| `ghPrStatus.ts` | 2823 | 106 |
| `git.ts` | 30270 | 926 |
| `gitDiff.ts` | 16039 | 532 |
| `gitSettings.ts` | 838 | 18 |
| `githubModelsCredentials.hydrate.test.ts` | 2379 | 71 |
| `githubModelsCredentials.refresh.test.ts` | 3715 | 118 |
| `githubModelsCredentials.test.ts` | 1592 | 53 |
| `githubModelsCredentials.ts` | 6038 | 198 |
| `githubRepoPathMapping.ts` | 5131 | 162 |
| `glob.ts` | 4518 | 130 |
| `gracefulShutdown.ts` | 20820 | 539 |
| `groupToolUses.ts` | 5537 | 182 |
| `handlePromptSubmit.test.ts` | 2549 | 89 |
| `handlePromptSubmit.ts` | 21829 | 611 |
| `hash.ts` | 1683 | 46 |
| `headlessProfiler.ts` | 6058 | 178 |
| `heapDumpService.ts` | 9890 | 303 |
| `heatmap.ts` | 5305 | 198 |
| `highlightMatch.tsx` | 931 | 27 |
| `hookChains.integration.test.ts` | 11030 | 357 |
| `hookChains.test.ts` | 13946 | 476 |
| `hookChains.ts` | 41405 | 1518 |
| `hooks.ts` | 164405 | 5210 |
| `horizontalScroll.ts` | 4302 | 137 |
| `http.ts` | 5128 | 141 |
| `hyperlink.ts` | 1465 | 39 |
| `iTermBackup.ts` | 1608 | 73 |
| `ide.ts` | 46740 | 1496 |
| `idePathConversion.ts` | 2602 | 90 |
| `idleTimeout.ts` | 1574 | 53 |
| `imagePaste.ts` | 14930 | 440 |
| `imageResizer.ts` | 26699 | 880 |
| `imageStore.ts` | 4320 | 167 |
| `imageValidation.ts` | 3619 | 104 |
| `immediateCommand.ts` | 547 | 15 |
| `inProcessTeammateHelpers.ts` | 2988 | 102 |
| `ink.ts` | 921 | 26 |
| `intl.ts` | 2824 | 94 |
| `jetbrains.ts` | 5805 | 191 |
| `json.ts` | 9148 | 277 |
| `jsonRead.ts` | 657 | 16 |
| `keyboardShortcuts.ts` | 568 | 14 |
| `lazySchema.ts` | 295 | 8 |
| `listSessionsImpl.ts` | 15071 | 454 |
| `localInstaller.ts` | 6299 | 212 |
| `lockfile.ts` | 1330 | 43 |
| `log.ts` | 11661 | 362 |
| `logoV2Utils.ts` | 9869 | 350 |
| `mailbox.ts` | 1596 | 73 |
| `managedEnv.ts` | 8372 | 208 |
| `managedEnvConstants.ts` | 6838 | 192 |
| `markdown.ts` | 11853 | 381 |
| `markdownConfigLoader.ts` | 21312 | 600 |
| `mcpInstructionsDelta.ts` | 4751 | 130 |
| `mcpOutputStorage.ts` | 7086 | 189 |
| `mcpValidation.ts` | 6300 | 208 |
| `mcpWebSocketTransport.ts` | 6052 | 200 |
| `memoize.ts` | 8612 | 269 |
| `memoryFileDetection.ts` | 10212 | 289 |
| `messagePredicates.ts` | 427 | 8 |
| `messageQueueManager.ts` | 16563 | 547 |
| `messages.ts` | 193949 | 5524 |
| `modelCost.ts` | 7520 | 231 |
| `modifiers.ts` | 752 | 22 |
| `mtls.ts` | 4655 | 179 |
| `notebook.ts` | 6368 | 224 |
| `objectGroupBy.ts` | 511 | 18 |
| `openclaudeInstallSurfaces.test.ts` | 2269 | 75 |
| `openclaudePaths.test.ts` | 4643 | 146 |
| `openclaudeUiSurfaces.test.ts` | 2143 | 65 |
| `pasteStore.ts` | 2950 | 104 |
| `path.ts` | 5700 | 155 |
| `pdf.ts` | 8148 | 300 |
| `pdfUtils.ts` | 2190 | 70 |
| `peerAddress.ts` | 981 | 21 |
| `planModeV2.ts` | 2951 | 92 |
| `plans.ts` | 12390 | 397 |
| `platform.ts` | 3801 | 150 |
| `preflightChecks.tsx` | 5027 | 151 |
| `privacyLevel.ts` | 1886 | 55 |
| `process.ts` | 2333 | 68 |
| `profilerBase.ts` | 1572 | 46 |
| `projectInstructions.test.ts` | 3343 | 105 |
| `projectInstructions.ts` | 1442 | 55 |
| `promptCategory.ts` | 1502 | 49 |
| `promptEditor.ts` | 5664 | 188 |
| `promptShellExecution.test.ts` | 2090 | 77 |
| `promptShellExecution.ts` | 7574 | 197 |
| `protectedNamespace.ts` | 133 | 3 |
| `providerAutoDetect.test.ts` | 8564 | 299 |
| `providerAutoDetect.ts` | 8167 | 283 |
| `providerDiscovery.test.ts` | 10605 | 363 |
| `providerDiscovery.ts` | 11446 | 459 |
| `providerFlag.test.ts` | 6434 | 211 |
| `providerFlag.ts` | 4305 | 154 |
| `providerModels.test.ts` | 3437 | 108 |
| `providerModels.ts` | 1005 | 33 |
| `providerProfile.test.ts` | 25709 | 811 |
| `providerProfile.ts` | 26871 | 926 |
| `providerProfiles.test.ts` | 29207 | 853 |
| `providerProfiles.ts` | 31403 | 1067 |
| `providerRecommendation.test.ts` | 4778 | 194 |
| `providerRecommendation.ts` | 8186 | 317 |
| `providerSecrets.ts` | 2253 | 99 |
| `providerValidation.test.ts` | 4579 | 140 |
| `providerValidation.ts` | 6895 | 212 |
| `proxy.ts` | 13584 | 428 |
| `queryContext.ts` | 5937 | 179 |
| `queryHelpers.ts` | 19734 | 552 |
| `queryProfiler.ts` | 8894 | 301 |
| `queueProcessor.ts` | 3174 | 95 |
| `readEditContext.ts` | 7224 | 227 |
| `readFileInRange.ts` | 12259 | 383 |
| `releaseNotes.ts` | 11813 | 360 |
| `renderOptions.ts` | 2278 | 77 |
| `requestLogging.test.ts` | 2143 | 86 |
| `requestLogging.ts` | 1793 | 89 |
| `ripgrep.test.ts` | 2082 | 68 |
| `ripgrep.ts` | 23926 | 772 |
| `sanitization.ts` | 4003 | 91 |
| `schemaSanitizer.test.ts` | 2062 | 68 |
| `schemaSanitizer.ts` | 6519 | 258 |
| `screenshotClipboard.ts` | 3709 | 121 |
| `sdkEventQueue.ts` | 4077 | 134 |
| `semanticBoolean.ts` | 1167 | 29 |
| `semanticNumber.ts` | 1486 | 36 |
| `semver.ts` | 1713 | 59 |
| `sequential.ts` | 1641 | 56 |
| `sessionActivity.ts` | 4081 | 133 |
| `sessionEnvVars.ts` | 590 | 22 |
| `sessionEnvironment.ts` | 5053 | 166 |
| `sessionFileAccessHooks.ts` | 8138 | 250 |
| `sessionIngressAuth.ts` | 4737 | 140 |
| `sessionRestore.ts` | 20411 | 551 |
| `sessionStart.ts` | 8151 | 232 |
| `sessionState.ts` | 5309 | 150 |
| `sessionStorage.test.ts` | 7590 | 261 |
| `sessionStorage.ts` | 187729 | 5361 |
| `sessionStoragePortable.ts` | 25448 | 793 |
| `sessionTitle.ts` | 4878 | 133 |
| `sessionUrl.ts` | 1672 | 64 |
| `set.ts` | 1036 | 53 |
| `shellConfig.ts` | 4737 | 167 |
| `sideQuery.ts` | 8292 | 222 |
| `sideQuestion.ts` | 6133 | 155 |
| `signal.ts` | 1447 | 43 |
| `sinks.ts` | 608 | 16 |
| `slashCommandParsing.ts` | 1437 | 60 |
| `sleep.ts` | 2882 | 84 |
| `sliceAnsi.ts` | 3343 | 91 |
| `slowOperations.ts` | 9055 | 286 |
| `standaloneAgent.ts` | 803 | 23 |
| `startupProfiler.ts` | 6079 | 194 |
| `staticRender.tsx` | 3729 | 119 |
| `stats.ts` | 33800 | 1061 |
| `statsCache.ts` | 13896 | 434 |
| `status.tsx` | 15981 | 452 |
| `statusNoticeDefinitions.tsx` | 8115 | 197 |
| `statusNoticeHelpers.ts` | 673 | 20 |
| `stream.ts` | 1926 | 76 |
| `streamJsonStdoutGuard.ts` | 3987 | 123 |
| `streamingOptimizer.test.ts` | 1766 | 61 |
| `streamingOptimizer.ts` | 1118 | 51 |
| `streamlinedTransform.ts` | 5941 | 201 |
| `stringUtils.ts` | 6595 | 235 |
| `subprocessEnv.ts` | 3975 | 99 |
| `systemDirectories.ts` | 2125 | 74 |
| `systemPrompt.ts` | 4867 | 123 |
| `systemPromptType.ts` | 382 | 14 |
| `systemTheme.ts` | 4231 | 119 |
| `taggedId.ts` | 1573 | 54 |
| `tasks.ts` | 26359 | 862 |
| `teamDiscovery.ts` | 2323 | 81 |
| `teamMemoryOps.ts` | 2471 | 88 |
| `teammate.ts` | 9206 | 292 |
| `teammateContext.ts` | 3161 | 96 |
| `teammateMailbox.ts` | 33420 | 1183 |
| `telemetryAttributes.ts` | 2095 | 71 |
| `teleport.tsx` | 52119 | 1225 |
| `tempfile.ts` | 1170 | 31 |
| `terminal.ts` | 4372 | 131 |
| `terminalPanel.ts` | 6014 | 191 |
| `textHighlighting.ts` | 4540 | 166 |
| `theme.ts` | 26830 | 639 |
| `thinking.ts` | 5519 | 162 |
| `thinkingTokenExtractor.test.ts` | 3015 | 106 |
| `thinkingTokenExtractor.ts` | 5528 | 192 |
| `thinkingTokens.test.ts` | 1793 | 69 |
| `timeouts.ts` | 1410 | 39 |
| `tmuxSocket.ts` | 13693 | 427 |
| `tokenAnalytics.test.ts` | 2480 | 84 |
| `tokenAnalytics.ts` | 5402 | 211 |
| `tokenBudget.ts` | 2675 | 73 |
| `tokens.ts` | 14662 | 453 |
| `toolErrors.ts` | 4012 | 132 |
| `toolPool.ts` | 3136 | 79 |
| `toolResultStorage.test.ts` | 1739 | 59 |
| `toolResultStorage.ts` | 39502 | 1068 |
| `toolSchemaCache.ts` | 1061 | 26 |
| `toolSearch.ts` | 26606 | 756 |
| `transcriptSearch.ts` | 8039 | 202 |
| `treeify.ts` | 5033 | 170 |
| `truncate.test.ts` | 509 | 15 |
| `truncate.ts` | 6036 | 186 |
| `unaryLogging.ts` | 1254 | 39 |
| `undercover.ts` | 206 | 11 |
| `urlRedaction.test.ts` | 1188 | 38 |
| `urlRedaction.ts` | 1121 | 48 |
| `user.test.ts` | 2438 | 90 |
| `user.ts` | 5322 | 176 |
| `userAgent.ts` | 281 | 10 |
| `userPromptKeywords.ts` | 929 | 27 |
| `uuid.ts` | 888 | 27 |
| `warningHandler.ts` | 4486 | 121 |
| `which.ts` | 2392 | 82 |
| `windowsPaths.ts` | 6008 | 173 |
| `withResolvers.ts` | 444 | 13 |
| `words.ts` | 10850 | 797 |
| `workloadContext.ts` | 2337 | 57 |
| `worktree.test.ts` | 1672 | 69 |
| `worktree.ts` | 51455 | 1563 |
| `worktreeModeEnabled.ts` | 415 | 11 |
| `xdg.ts` | 1876 | 65 |
| `xml.ts` | 622 | 16 |
| `yaml.ts` | 525 | 15 |
| `zodToJsonSchema.ts` | 761 | 23 |

### `vendor/openclaude/src/utils/background/remote/` (2 files)

| File | Bytes | Lines |
|---|---:|---:|
| `preconditions.ts` | 7336 | 235 |
| `remoteSession.ts` | 3050 | 98 |

### `vendor/openclaude/src/utils/bash/` (15 files)

| File | Bytes | Lines |
|---|---:|---:|
| `ParsedCommand.ts` | 9221 | 318 |
| `ShellSnapshot.ts` | 21780 | 582 |
| `ast.ts` | 112054 | 2679 |
| `bashParser.ts` | 130810 | 4436 |
| `bashPipeCommand.ts` | 10708 | 294 |
| `commands.ts` | 51078 | 1339 |
| `heredoc.ts` | 31458 | 733 |
| `parser.ts` | 6657 | 230 |
| `prefix.ts` | 6222 | 204 |
| `registry.ts` | 1433 | 53 |
| `shellCompletion.ts` | 7874 | 259 |
| `shellPrefix.ts` | 1028 | 28 |
| `shellQuote.ts` | 10824 | 304 |
| `shellQuoting.ts` | 4718 | 128 |
| `treeSitterAnalysis.ts` | 17594 | 506 |

### `vendor/openclaude/src/utils/bash/specs/` (8 files)

| File | Bytes | Lines |
|---|---:|---:|
| `alias.ts` | 313 | 14 |
| `index.ts` | 380 | 18 |
| `nohup.ts` | 274 | 13 |
| `pyright.ts` | 2670 | 91 |
| `sleep.ts` | 315 | 13 |
| `srun.ts` | 654 | 31 |
| `time.ts` | 244 | 13 |
| `timeout.ts` | 426 | 20 |

### `vendor/openclaude/src/utils/claudeInChrome/` (7 files)

| File | Bytes | Lines |
|---|---:|---:|
| `chromeNativeHost.ts` | 13876 | 527 |
| `common.ts` | 14489 | 540 |
| `mcpServer.ts` | 10918 | 290 |
| `prompt.ts` | 5605 | 83 |
| `setup.ts` | 13015 | 400 |
| `setupPortable.ts` | 6767 | 233 |
| `toolRendering.tsx` | 9278 | 261 |

### `vendor/openclaude/src/utils/computerUse/` (15 files)

| File | Bytes | Lines |
|---|---:|---:|
| `appNames.ts` | 6575 | 196 |
| `cleanup.ts` | 3298 | 86 |
| `common.ts` | 2617 | 61 |
| `computerUseLock.ts` | 7135 | 215 |
| `drainRunLoop.ts` | 2821 | 79 |
| `escHotkey.ts` | 1965 | 54 |
| `executor.ts` | 23812 | 658 |
| `gates.ts` | 2563 | 72 |
| `hostAdapter.ts` | 2771 | 69 |
| `inputLoader.ts` | 1190 | 30 |
| `mcpServer.ts` | 4123 | 106 |
| `setup.ts` | 2020 | 53 |
| `swiftLoader.ts` | 925 | 23 |
| `toolRendering.tsx` | 4498 | 124 |
| `wrapper.tsx` | 14344 | 335 |

### `vendor/openclaude/src/utils/deepLink/` (6 files)

| File | Bytes | Lines |
|---|---:|---:|
| `banner.ts` | 4694 | 123 |
| `parseDeepLink.ts` | 5715 | 170 |
| `protocolHandler.ts` | 4943 | 136 |
| `registerProtocol.ts` | 11866 | 348 |
| `terminalLauncher.ts` | 17786 | 557 |
| `terminalPreference.ts` | 1897 | 54 |

### `vendor/openclaude/src/utils/dxt/` (2 files)

| File | Bytes | Lines |
|---|---:|---:|
| `helpers.ts` | 2599 | 88 |
| `zip.ts` | 7704 | 226 |

### `vendor/openclaude/src/utils/filePersistence/` (3 files)

| File | Bytes | Lines |
|---|---:|---:|
| `filePersistence.ts` | 7763 | 287 |
| `outputsScanner.ts` | 3682 | 126 |
| `types.ts` | 398 | 21 |

### `vendor/openclaude/src/utils/git/` (3 files)

| File | Bytes | Lines |
|---|---:|---:|
| `gitConfigParser.ts` | 6645 | 277 |
| `gitFilesystem.ts` | 22340 | 699 |
| `gitignore.ts` | 3200 | 99 |

### `vendor/openclaude/src/utils/github/` (1 files)

| File | Bytes | Lines |
|---|---:|---:|
| `ghAuthStatus.ts` | 942 | 29 |

### `vendor/openclaude/src/utils/hooks/` (17 files)

| File | Bytes | Lines |
|---|---:|---:|
| `AsyncHookRegistry.ts` | 8913 | 309 |
| `apiQueryHookHelper.ts` | 4383 | 141 |
| `execAgentHook.ts` | 12485 | 339 |
| `execHttpHook.ts` | 8871 | 242 |
| `execPromptHook.ts` | 6822 | 211 |
| `fileChangedWatcher.ts` | 5309 | 191 |
| `hookEvents.ts` | 4492 | 192 |
| `hookHelpers.ts` | 2521 | 83 |
| `hooksConfigManager.ts` | 17502 | 400 |
| `hooksConfigSnapshot.ts` | 5064 | 133 |
| `hooksSettings.ts` | 8506 | 271 |
| `postSamplingHooks.ts` | 1993 | 70 |
| `registerFrontmatterHooks.ts` | 2277 | 67 |
| `registerSkillHooks.ts` | 2059 | 64 |
| `sessionHooks.ts` | 12132 | 447 |
| `skillImprovement.ts` | 8362 | 267 |
| `ssrfGuard.ts` | 8732 | 294 |

### `vendor/openclaude/src/utils/mcp/` (2 files)

| File | Bytes | Lines |
|---|---:|---:|
| `dateTimeParser.ts` | 4322 | 121 |
| `elicitationValidation.ts` | 9384 | 336 |

### `vendor/openclaude/src/utils/memory/` (2 files)

| File | Bytes | Lines |
|---|---:|---:|
| `types.ts` | 264 | 12 |
| `versions.ts` | 307 | 8 |

### `vendor/openclaude/src/utils/messages/` (2 files)

| File | Bytes | Lines |
|---|---:|---:|
| `mappers.ts` | 9031 | 290 |
| `systemInit.ts` | 3752 | 96 |

### `vendor/openclaude/src/utils/model/` (30 files)

| File | Bytes | Lines |
|---|---:|---:|
| `agent.ts` | 5578 | 157 |
| `aliases.ts` | 793 | 25 |
| `antModels.ts` | 1803 | 64 |
| `bedrock.ts` | 9196 | 265 |
| `benchmark.ts` | 5588 | 205 |
| `check1mAccess.ts` | 2215 | 72 |
| `configs.ts` | 7325 | 206 |
| `contextWindowUpgradeCheck.ts` | 1284 | 47 |
| `copilotModels.ts` | 9491 | 351 |
| `deprecation.ts` | 2534 | 101 |
| `minimaxModels.ts` | 2094 | 46 |
| `model.github.test.ts` | 2117 | 57 |
| `model.openai-shim-providers.test.ts` | 7506 | 199 |
| `model.ts` | 29730 | 842 |
| `modelAllowlist.ts` | 6030 | 170 |
| `modelCache.test.ts` | 952 | 30 |
| `modelCache.ts` | 4647 | 165 |
| `modelCapabilities.ts` | 426 | 16 |
| `modelOptions.github.test.ts` | 3377 | 84 |
| `modelOptions.ts` | 24795 | 738 |
| `modelStrings.github.test.ts` | 2031 | 54 |
| `modelStrings.ts` | 5484 | 169 |
| `modelSupportOverrides.ts` | 1537 | 50 |
| `nvidiaNimModels.ts` | 12449 | 161 |
| `ollamaModels.ts` | 2890 | 104 |
| `openaiContextWindows.ts` | 18526 | 458 |
| `openaiModelDiscovery.ts` | 4681 | 189 |
| `providers.test.ts` | 6398 | 166 |
| `providers.ts` | 3635 | 102 |
| `validateModel.ts` | 7236 | 215 |

### `vendor/openclaude/src/utils/nativeInstaller/` (5 files)

| File | Bytes | Lines |
|---|---:|---:|
| `download.ts` | 15418 | 529 |
| `index.ts` | 456 | 18 |
| `installer.ts` | 54956 | 1712 |
| `packageManagers.ts` | 8963 | 336 |
| `pidLock.ts` | 11934 | 433 |

### `vendor/openclaude/src/utils/permissions/` (25 files)

| File | Bytes | Lines |
|---|---:|---:|
| `PermissionMode.ts` | 3494 | 141 |
| `PermissionPromptToolResultSchema.ts` | 4108 | 127 |
| `PermissionResult.ts` | 874 | 35 |
| `PermissionRule.ts` | 1176 | 40 |
| `PermissionUpdate.ts` | 11912 | 389 |
| `PermissionUpdateSchema.ts` | 2402 | 78 |
| `autoModeState.ts` | 1095 | 39 |
| `bashClassifier.ts` | 1449 | 61 |
| `bypassPermissionsKillswitch.ts` | 4839 | 155 |
| `classifierDecision.ts` | 4585 | 98 |
| `classifierShared.ts` | 1174 | 39 |
| `dangerousPatterns.ts` | 2548 | 81 |
| `denialTracking.ts` | 1101 | 45 |
| `filesystem.ts` | 62813 | 1787 |
| `getNextPermissionMode.ts` | 3301 | 101 |
| `pathValidation.ts` | 16249 | 485 |
| `permissionExplainer.ts` | 7606 | 250 |
| `permissionRuleParser.ts` | 7279 | 198 |
| `permissionSetup.ts` | 53514 | 1533 |
| `permissions.ts` | 52195 | 1486 |
| `permissionsLoader.ts` | 8743 | 296 |
| `shadowedRuleDetection.ts` | 8050 | 234 |
| `shellRuleMatching.ts` | 6409 | 228 |
| `yoloClassifier.test.ts` | 1803 | 79 |
| `yoloClassifier.ts` | 55014 | 1603 |

### `vendor/openclaude/src/utils/plugins/` (45 files)

| File | Bytes | Lines |
|---|---:|---:|
| `addDirPluginSettings.ts` | 2320 | 71 |
| `cacheUtils.ts` | 6652 | 196 |
| `dependencyResolver.ts` | 11673 | 305 |
| `fetchTelemetry.ts` | 4922 | 135 |
| `gitAvailability.ts` | 2273 | 69 |
| `headlessPluginInstall.ts` | 6775 | 174 |
| `hintRecommendation.ts` | 5431 | 164 |
| `installCounts.ts` | 8315 | 292 |
| `installedPluginsManager.ts` | 41410 | 1268 |
| `loadPluginAgents.ts` | 12485 | 348 |
| `loadPluginCommands.ts` | 30541 | 946 |
| `loadPluginHooks.ts` | 10066 | 287 |
| `loadPluginOutputStyles.ts` | 5672 | 178 |
| `lspPluginIntegration.ts` | 12414 | 387 |
| `lspRecommendation.ts` | 10695 | 374 |
| `managedPlugins.ts` | 877 | 27 |
| `marketplaceHelpers.ts` | 18217 | 592 |
| `marketplaceManager.ts` | 93468 | 2648 |
| `mcpPluginIntegration.ts` | 20113 | 634 |
| `mcpbHandler.ts` | 31289 | 968 |
| `officialMarketplace.ts` | 836 | 25 |
| `officialMarketplaceGcs.ts` | 9338 | 216 |
| `officialMarketplaceStartupCheck.ts` | 15192 | 439 |
| `orphanedPluginFilter.ts` | 3980 | 114 |
| `parseMarketplaceInput.ts` | 6075 | 162 |
| `performStartupChecks.tsx` | 3177 | 69 |
| `pluginAutoupdate.ts` | 9473 | 284 |
| `pluginBlocklist.ts` | 4361 | 127 |
| `pluginDirectories.ts` | 6669 | 178 |
| `pluginFlagging.ts` | 5621 | 208 |
| `pluginIdentifier.ts` | 3928 | 123 |
| `pluginInstallationHelpers.ts` | 20629 | 595 |
| `pluginLoader.test.ts` | 1784 | 71 |
| `pluginLoader.ts` | 111537 | 3341 |
| `pluginOptionsStorage.ts` | 15302 | 400 |
| `pluginPolicy.ts` | 827 | 20 |
| `pluginStartupCheck.ts` | 11096 | 341 |
| `pluginVersioning.ts` | 5340 | 157 |
| `reconciler.ts` | 8273 | 265 |
| `refresh.ts` | 8642 | 217 |
| `schemas.ts` | 58914 | 1681 |
| `validatePlugin.ts` | 28366 | 903 |
| `walkPluginMarkdown.ts` | 2222 | 69 |
| `zipCache.ts` | 13163 | 406 |
| `zipCacheAdapters.ts` | 5310 | 164 |

### `vendor/openclaude/src/utils/powershell/` (3 files)

| File | Bytes | Lines |
|---|---:|---:|
| `dangerousCmdlets.ts` | 6155 | 185 |
| `parser.ts` | 66647 | 1804 |
| `staticPrefix.ts` | 12277 | 316 |

### `vendor/openclaude/src/utils/processUserInput/` (4 files)

| File | Bytes | Lines |
|---|---:|---:|
| `processBashCommand.tsx` | 6451 | 142 |
| `processSlashCommand.tsx` | 42387 | 921 |
| `processTextPrompt.ts` | 3272 | 100 |
| `processUserInput.ts` | 19507 | 605 |

### `vendor/openclaude/src/utils/sandbox/` (2 files)

| File | Bytes | Lines |
|---|---:|---:|
| `sandbox-adapter.ts` | 36094 | 994 |
| `sandbox-ui-utils.ts` | 389 | 12 |

### `vendor/openclaude/src/utils/secureStorage/` (9 files)

| File | Bytes | Lines |
|---|---:|---:|
| `fallbackStorage.ts` | 2362 | 70 |
| `index.ts` | 2615 | 89 |
| `keychainPrefetch.ts` | 4755 | 116 |
| `linuxSecretStorage.ts` | 2481 | 86 |
| `macOsKeychainHelpers.ts` | 5070 | 121 |
| `macOsKeychainStorage.ts` | 8271 | 231 |
| `plainTextStorage.ts` | 2430 | 84 |
| `platformStorage.test.ts` | 6563 | 188 |
| `windowsCredentialStorage.ts` | 6495 | 225 |

### `vendor/openclaude/src/utils/settings/` (17 files)

| File | Bytes | Lines |
|---|---:|---:|
| `allErrors.ts` | 1257 | 32 |
| `allowBypassPermissionsMode.test.ts` | 962 | 27 |
| `applySettingsChange.ts` | 3656 | 92 |
| `changeDetector.ts` | 16384 | 488 |
| `constants.ts` | 5627 | 202 |
| `internalWrites.ts` | 1380 | 37 |
| `managedPath.ts` | 1095 | 34 |
| `permissionValidation.ts` | 8657 | 262 |
| `pluginOnlyPolicy.ts` | 2405 | 60 |
| `schemaOutput.ts` | 317 | 8 |
| `settings.ts` | 32887 | 1034 |
| `settingsCache.ts` | 2416 | 80 |
| `toolValidationConfig.ts` | 3100 | 103 |
| `types.ts` | 44085 | 1178 |
| `validateEditTool.ts` | 1695 | 45 |
| `validation.ts` | 7951 | 265 |
| `validationTips.ts` | 4985 | 154 |

### `vendor/openclaude/src/utils/settings/mdm/` (3 files)

| File | Bytes | Lines |
|---|---:|---:|
| `constants.ts` | 2627 | 81 |
| `rawRead.ts` | 4183 | 130 |
| `settings.ts` | 10716 | 316 |

### `vendor/openclaude/src/utils/shell/` (10 files)

| File | Bytes | Lines |
|---|---:|---:|
| `bashProvider.ts` | 11002 | 255 |
| `outputLimits.ts` | 416 | 14 |
| `powershellDetection.ts` | 3714 | 107 |
| `powershellProvider.ts` | 5771 | 123 |
| `prefix.ts` | 11216 | 367 |
| `readOnlyCommandValidation.ts` | 68309 | 1893 |
| `resolveDefaultShell.ts` | 496 | 14 |
| `shellProvider.ts` | 955 | 33 |
| `shellToolUtils.ts` | 1036 | 22 |
| `specPrefix.ts` | 7905 | 241 |

### `vendor/openclaude/src/utils/skills/` (1 files)

| File | Bytes | Lines |
|---|---:|---:|
| `skillChangeDetector.ts` | 10033 | 311 |

### `vendor/openclaude/src/utils/suggestions/` (5 files)

| File | Bytes | Lines |
|---|---:|---:|
| `commandSuggestions.ts` | 19174 | 589 |
| `directoryCompletion.ts` | 7098 | 263 |
| `shellHistoryCompletion.ts` | 3456 | 119 |
| `skillUsageTracking.ts` | 1948 | 55 |
| `slackChannelSuggestions.ts` | 6391 | 209 |

### `vendor/openclaude/src/utils/swarm/` (14 files)

| File | Bytes | Lines |
|---|---:|---:|
| `It2SetupPrompt.tsx` | 12061 | 379 |
| `constants.ts` | 1334 | 33 |
| `inProcessRunner.ts` | 53565 | 1552 |
| `leaderPermissionBridge.ts` | 1732 | 54 |
| `permissionSync.ts` | 27919 | 955 |
| `reconnection.ts` | 3401 | 119 |
| `spawnInProcess.ts` | 10241 | 328 |
| `spawnUtils.test.ts` | 899 | 33 |
| `spawnUtils.ts` | 5925 | 171 |
| `teamHelpers.ts` | 21385 | 683 |
| `teammateInit.ts` | 4280 | 129 |
| `teammateLayoutManager.ts` | 3261 | 107 |
| `teammateModel.ts` | 467 | 10 |
| `teammatePromptAddendum.ts` | 771 | 18 |

### `vendor/openclaude/src/utils/swarm/backends/` (9 files)

| File | Bytes | Lines |
|---|---:|---:|
| `ITermBackend.ts` | 12927 | 370 |
| `InProcessBackend.ts` | 10468 | 339 |
| `PaneBackendExecutor.ts` | 10914 | 354 |
| `TmuxBackend.ts` | 21491 | 764 |
| `detection.ts` | 4495 | 128 |
| `it2Setup.ts` | 6921 | 245 |
| `registry.ts` | 14791 | 464 |
| `teammateModeSnapshot.ts` | 2863 | 87 |
| `types.ts` | 9906 | 311 |

### `vendor/openclaude/src/utils/task/` (5 files)

| File | Bytes | Lines |
|---|---:|---:|
| `TaskOutput.ts` | 12474 | 390 |
| `diskOutput.ts` | 13568 | 451 |
| `framework.ts` | 9869 | 308 |
| `outputFormatting.ts` | 1188 | 38 |
| `sdkProgress.ts` | 1153 | 36 |

### `vendor/openclaude/src/utils/telemetry/` (9 files)

| File | Bytes | Lines |
|---|---:|---:|
| `betaSessionTracing.ts` | 15848 | 491 |
| `bigqueryExporter.ts` | 7806 | 252 |
| `events.ts` | 2287 | 75 |
| `instrumentation.ts` | 26741 | 825 |
| `logger.ts` | 742 | 26 |
| `perfettoTracing.ts` | 29797 | 1120 |
| `pluginTelemetry.ts` | 10491 | 289 |
| `sessionTracing.ts` | 27991 | 927 |
| `skillLoadedEvent.ts` | 1425 | 39 |

### `vendor/openclaude/src/utils/teleport/` (4 files)

| File | Bytes | Lines |
|---|---:|---:|
| `api.ts` | 13327 | 466 |
| `environmentSelection.ts` | 2695 | 77 |
| `environments.ts` | 3471 | 120 |
| `gitBundle.ts` | 9820 | 292 |

### `vendor/openclaude/src/utils/todo/` (1 files)

| File | Bytes | Lines |
|---|---:|---:|
| `types.ts` | 602 | 18 |

### `vendor/openclaude/src/utils/ultraplan/` (3 files)

| File | Bytes | Lines |
|---|---:|---:|
| `ccrSession.ts` | 12987 | 349 |
| `keyword.ts` | 4691 | 127 |
| `prompt.txt` | 32 | 1 |

### `vendor/openclaude/src/vim/` (5 files)

| File | Bytes | Lines |
|---|---:|---:|
| `motions.ts` | 1902 | 82 |
| `operators.ts` | 15966 | 556 |
| `textObjects.ts` | 5029 | 186 |
| `transitions.ts` | 12381 | 490 |
| `types.ts` | 6332 | 199 |

### `vendor/openclaude/src/voice/` (1 files)

| File | Bytes | Lines |
|---|---:|---:|
| `voiceModeEnabled.ts` | 2332 | 54 |

### `vendor/openclaude/vscode-extension/openclaude-vscode/` (2 files)

| File | Bytes | Lines |
|---|---:|---:|
| `README.md` | 2322 | 70 |
| `package.json` | 5049 | 179 |

### `vendor/openclaude/vscode-extension/openclaude-vscode/.vscode/` (1 files)

| File | Bytes | Lines |
|---|---:|---:|
| `launch.json` | 313 | 13 |

### `vendor/openclaude/vscode-extension/openclaude-vscode/media/` (1 files)

| File | Bytes | Lines |
|---|---:|---:|
| `openclaude.svg` | 434 | 6 |

### `vendor/openclaude/vscode-extension/openclaude-vscode/scripts/` (1 files)

| File | Bytes | Lines |
|---|---:|---:|
| `lint.js` | 493 | 17 |

### `vendor/openclaude/vscode-extension/openclaude-vscode/src/` (6 files)

| File | Bytes | Lines |
|---|---:|---:|
| `extension.js` | 38397 | 1235 |
| `extension.test.js` | 10359 | 254 |
| `presentation.js` | 5865 | 202 |
| `presentation.test.js` | 8632 | 291 |
| `state.js` | 10779 | 412 |
| `state.test.js` | 6086 | 246 |

### `vendor/openclaude/vscode-extension/openclaude-vscode/src/chat/` (7 files)

| File | Bytes | Lines |
|---|---:|---:|
| `chatProvider.js` | 21773 | 676 |
| `chatRenderer.js` | 46939 | 1354 |
| `diffController.js` | 2633 | 90 |
| `messageParser.js` | 4428 | 177 |
| `processManager.js` | 5641 | 194 |
| `protocol.js` | 4564 | 186 |
| `sessionManager.js` | 8537 | 282 |

### `vendor/openclaude/vscode-extension/openclaude-vscode/themes/` (1 files)

| File | Bytes | Lines |
|---|---:|---:|
| `OpenClaude-Terminal-Black.json` | 2744 | 78 |

### `vendor/paper2code/` (3 files)

| File | Bytes | Lines |
|---|---:|---:|
| `LICENSE` | 1080 | 21 |
| `SKILL.md` | 5341 | 112 |
| `UPSTREAM_README.md` | 9717 | 219 |

### `vendor/paper2code/guardrails/` (3 files)

| File | Bytes | Lines |
|---|---:|---:|
| `badly_written_papers.md` | 9054 | 215 |
| `hallucination_prevention.md` | 8309 | 194 |
| `scope_enforcement.md` | 8064 | 186 |

### `vendor/paper2code/knowledge/` (4 files)

| File | Bytes | Lines |
|---|---:|---:|
| `loss_functions.md` | 10023 | 280 |
| `paper_to_code_mistakes.md` | 10569 | 332 |
| `training_recipes.md` | 9304 | 253 |
| `transformer_components.md` | 14296 | 362 |

### `vendor/paper2code/pipeline/` (5 files)

| File | Bytes | Lines |
|---|---:|---:|
| `01_paper_acquisition.md` | 7123 | 152 |
| `02_contribution_identification.md` | 8621 | 176 |
| `03_ambiguity_audit.md` | 10763 | 212 |
| `04_code_generation.md` | 11415 | 314 |
| `05_walkthrough_notebook.md` | 6962 | 192 |

### `vendor/paper2code/scaffolds/` (8 files)

| File | Bytes | Lines |
|---|---:|---:|
| `config_template.yaml` | 2690 | 62 |
| `data_template.py` | 3263 | 113 |
| `evaluate_template.py` | 1736 | 62 |
| `loss_template.py` | 1431 | 53 |
| `model_template.py` | 4236 | 139 |
| `readme_template.md` | 1798 | 62 |
| `reproduction_notes_template.md` | 3595 | 109 |
| `train_template.py` | 5795 | 183 |

### `vendor/paper2code/scripts/` (2 files)

| File | Bytes | Lines |
|---|---:|---:|
| `extract_structure.py` | 11222 | 335 |
| `fetch_paper.py` | 15812 | 436 |

### `vendor/paper2code/worked/attention_is_all_you_need/` (4 files)

| File | Bytes | Lines |
|---|---:|---:|
| `README.md` | 2662 | 69 |
| `REPRODUCTION_NOTES.md` | 6015 | 118 |
| `requirements.txt` | 39 | 3 |
| `review.md` | 5238 | 89 |

### `vendor/paper2code/worked/attention_is_all_you_need/configs/` (1 files)

| File | Bytes | Lines |
|---|---:|---:|
| `base.yaml` | 3490 | 59 |

### `vendor/paper2code/worked/attention_is_all_you_need/notebooks/` (1 files)

| File | Bytes | Lines |
|---|---:|---:|
| `walkthrough.ipynb` | 27573 | 658 |

### `vendor/paper2code/worked/attention_is_all_you_need/src/` (6 files)

| File | Bytes | Lines |
|---|---:|---:|
| `data.py` | 6089 | 156 |
| `evaluate.py` | 2214 | 73 |
| `loss.py` | 2983 | 78 |
| `model.py` | 23099 | 569 |
| `train.py` | 3449 | 97 |
| `utils.py` | 3125 | 96 |

### `vendor/paper2code/worked/ddpm/` (4 files)

| File | Bytes | Lines |
|---|---:|---:|
| `README.md` | 2845 | 73 |
| `REPRODUCTION_NOTES.md` | 6241 | 120 |
| `requirements.txt` | 39 | 3 |
| `review.md` | 4515 | 100 |

### `vendor/paper2code/worked/ddpm/configs/` (1 files)

| File | Bytes | Lines |
|---|---:|---:|
| `base.yaml` | 3936 | 69 |

### `vendor/paper2code/worked/ddpm/notebooks/` (1 files)

| File | Bytes | Lines |
|---|---:|---:|
| `walkthrough.ipynb` | 13987 | 435 |

### `vendor/paper2code/worked/ddpm/src/` (6 files)

| File | Bytes | Lines |
|---|---:|---:|
| `data.py` | 3246 | 111 |
| `evaluate.py` | 8148 | 246 |
| `loss.py` | 1921 | 60 |
| `model.py` | 14869 | 382 |
| `train.py` | 6634 | 195 |
| `utils.py` | 8171 | 243 |

---

# Generation Notes

- This report was generated by a deterministic Python script that walks every file, parses Python sources via `ast`, and extracts Markdown headings / TS exports via regular expressions. Nothing in the per-file analysis is paraphrased opinion — every signature, docstring first-line, heading, import, and constant came directly from the file.
- Files larger than 200 KB that are not source code are listed by size only.
- The `.git/` directory was excluded because it is version-control metadata, not project source.

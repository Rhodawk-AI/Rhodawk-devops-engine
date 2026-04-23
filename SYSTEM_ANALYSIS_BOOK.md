# Rhodawk AI — System Analysis Book
### Complete End-to-End Mechanics, Logic, and Operational Reference
#### Companion to `FOUNDER_PLAYBOOK.md` — written from the live source tree

---

> **Purpose of this document.**
> The existing `FOUNDER_PLAYBOOK.md` is the canonical investor-facing narrative
> of what Rhodawk does and why it matters. It remains the source of truth for
> mission, business model, and high-level architecture and is **not** modified.
>
> This book sits beside it and answers a different question: **how does every
> piece actually work, end-to-end, in the code as it stands today?** It is
> written for engineers who must run, debug, extend, or migrate the system,
> and it intentionally crosses every layer — from Dockerfile, through provider
> routing, through each Python module, into the MCP servers, into the test
> suite, and out to the data on disk.
>
> Where the playbook says *"the system has a 5-layer safety pipeline,"* this
> book says *"`process_failing_test` in `app.py` calls `sast_gate.run_sast`,
> which forks bandit and semgrep, parses their JSON, returns a `SastVerdict`
> dataclass, and on `BLOCK` raises an early-exit that `verification_loop`
> converts into a retry prompt with the SAST critique inlined."*
>
> Read the playbook for **what and why**. Read this book for **how**.

---

## Table of Contents

1. [Recent Change Log — The Last Mile of Fixes](#1-recent-change-log)
2. [Provider Routing — DO Primary, OpenRouter Fallback](#2-provider-routing)
3. [Top-Level Topology](#3-top-level-topology)
4. [Container & Build — Dockerfile and Requirements](#4-container--build)
5. [Process Map at Runtime](#5-process-map-at-runtime)
6. [Master Orchestrator — `app.py`](#6-master-orchestrator)
7. [Hermes Six-Phase Pipeline — `hermes_orchestrator.py`](#7-hermes-pipeline)
8. [Safety Gate Modules](#8-safety-gates)
9. [Memory, Learning, and Data Flywheel](#9-memory-learning)
10. [Autonomous Operation — Harvester, Worker Pool, Job Queue](#10-autonomous-operation)
11. [GitHub Surface — `github_app.py`, `webhook_server.py`, `commit_watcher.py`](#11-github-surface)
12. [Red Team & Offense Modules](#12-red-team--offense)
13. [Notification, Audit, Disclosure, Bounty](#13-notification-audit)
14. [Architect Subsystem — Tier Routing, Sandbox, Skills, Night Mode](#14-architect)
15. [Mythos Subsystem — Multi-Agent + RL + 17 MCP Servers](#15-mythos)
16. [MCP Suite — Every Server, Every Domain](#16-mcp-suite)
17. [Test Suite — What Each Test Asserts](#17-test-suite)
18. [Data on Disk — Files, SQLite Schemas, Audit Chain](#18-data-on-disk)
19. [Complete Environment Variable Reference (Updated)](#19-env-vars)
20. [Failure Modes and Recovery Procedures](#20-failure-modes)
21. [Security Model — Trust Boundaries and Threat Mitigation](#21-security-model)
22. [Migration Playbook — HF Space → Paid Server](#22-migration)
23. [Glossary of Internal Names](#23-glossary)

---

## 1. Recent Change Log — The Last Mile of Fixes
<a id="1-recent-change-log"></a>

The Space went through five iterative dependency-and-build fixes after the
original `FOUNDER_PLAYBOOK.md` was written at commit `8a23fcf`. These changes
do not appear in the playbook because they post-date it. They are critical
to understand because they affect both runtime behaviour (provider selection)
and build behaviour (how the container is assembled).

| Order | Commit  | What changed | Why |
|---|---|---|---|
| 1 | `504dde2` | Added DigitalOcean Serverless Inference as primary, OpenRouter as fallback, in `app.py::run_aider` and `hermes_orchestrator.py::_hermes_llm_call`. Added env vars `DO_INFERENCE_API_KEY`, `DO_INFERENCE_BASE_URL`, `DO_INFERENCE_MODEL`, `HERMES_DO_MODEL`. | Move the hot path off the OpenRouter free tier (rate-limit-prone) onto DigitalOcean's paid llama3.3-70b-instruct. Keep OpenRouter as resilience. |
| 2 | `1e909b0` | Bumped `aider-chat` to `0.87.0` to fix the `module 'litellm' has no attribute 'APIConnectionError'` crash. | The aider 0.86.x series hard-pinned `litellm==1.75.0`, whose top-level module was missing public symbols at runtime. **This bump failed because aider 0.87.0 was never published to PyPI.** |
| 3 | `da5ce03` | Reverted to `aider-chat==0.86.2` and added a Dockerfile post-step: `pip install --no-cache-dir --upgrade --no-deps "litellm==1.78.5"`. | aider only consumes litellm via `getattr` and a small public surface; replacing the broken pin with a known-good newer release restores `APIConnectionError`, `_logging`, `encode`, `token_counter`. |
| 4 | `ad06d84` | Added `gitpython==3.1.46` to `requirements.txt`. | aider 0.86.2 hard-pins gitpython; pip's resolver was bouncing between our floor (`>=3.1.40`) and aider's pin. Pinning explicitly removes the resolver thrash. |
| 5 | `a913714` | Switched the Space SDK from `gradio` to `docker` in `README.md` front-matter and bumped `gradio>=5.49.0,<6` in `requirements.txt`. | HF was auto-injecting `gradio[oauth,mcp]==5.29.0` because the Space was registered as `sdk: gradio`. That injection conflicted with aider's `pillow==12.1.1` pin. `sdk: docker` tells HF to use the existing Dockerfile verbatim, with no auto-injection. |
| 6 | `dd4ccce` | Removed `aider-chat` from `requirements.txt` entirely. The Dockerfile now installs it with `--no-deps` plus a curated runtime-deps list. | Even with `sdk: docker`, aider's `pillow==12.1.1` pin still conflicted with gradio's `pillow<12` constraint at the resolver level. `--no-deps` lets gradio's pillow 11 win, and the curated dep list provides everything aider actually imports at runtime. |
| 7 | *current* | **Aider eliminated entirely. Vendored OpenClaude headless gRPC daemon now drives every code-generation turn.** Two daemons (`:50051` DigitalOcean primary, `:50052` OpenRouter fallback) launched from `entrypoint.sh`. New Python bridge `openclaude_grpc/` exposes `run_openclaude(...)` with the legacy `(combined_output, exit_code)` return contract. `run_aider` is now a thin alias. | The `--no-deps + litellm 1.78.5 + curated 27-package list` workaround was a fragile patchwork; any aider/gradio/pillow upstream bump could re-break the build. OpenClaude is a single Bun-built bundle with no Python dependency surface and a stable gRPC contract, so the Dockerfile loses ~30 lines of dependency hacks. |

**Net effect today.** The Space SDK is `docker`. The build runs the
Dockerfile end-to-end in three stages: (1) Bun compiles
`vendor/openclaude/` to `dist/cli.mjs`; (2) Python 3.12-slim with system
tooling, uv, Node and Bun is provisioned; (3) the runtime image generates
Python protobuf stubs from `vendor/openclaude/src/proto/openclaude.proto`
into `openclaude_grpc/`. `requirements.txt` no longer mentions
`aider-chat`, `litellm`, `configargparse`, or any of the other 27 curated
aider runtime imports — they have all been deleted. `entrypoint.sh`
boots the OpenClaude DO daemon on `:50051` and (when an OpenRouter key is
present) the OpenClaude OR daemon on `:50052`, then `exec`s `app.py`.

**Provider behaviour today.** When `DO_INFERENCE_API_KEY` is present the hot
path uses DigitalOcean Serverless Inference at
`https://inference.do-ai.run/v1` with model `llama3.3-70b-instruct`.
OpenRouter is the configured fallback for any non-zero exit, 429, or 5xx.
When DO is absent the system silently runs OpenRouter-only.

---

## 2. Provider Routing — DigitalOcean Primary, OpenRouter Fallback
<a id="2-provider-routing"></a>

Two independent code paths need an LLM: **OpenClaude** (the patch
generator, replaces aider) and **Hermes** (the multi-phase research
orchestrator + adversarial reviewer). Both are wired to the same
provider chain — DigitalOcean Inference primary, OpenRouter fallback.

### 2.1 OpenClaude path — `app.py::run_openclaude` (alias `run_aider`)

```
entrypoint.sh boots two OpenClaude headless gRPC daemons:
  ┌─ DO_INFERENCE_API_KEY  → :50051  (PRIMARY,  llama3.3-70b-instruct)
  └─ OPENROUTER_API_KEY    → :50052  (FALLBACK, qwen-2.5-coder-32b)

run_openclaude(mcp_config_path, prompt, context_files):
  │
  ├─► writes /tmp/mcp_runtime.json (the daemon hot-reloads it per chat)
  ├─► forwards prompt + valid context-file list to the bridge
  │
  └─► openclaude_grpc.run_openclaude builds the chain [primary, fallback]:
        for each (port, label, model) in chain:
          client = OpenClaudeClient(host=127.0.0.1, port=port)
          if not client.wait_ready(15s): record + continue
          result = client.chat(message, working_directory=REPO_DIR, model=model)
              ├── streams text_chunk → result.stdout
              ├── streams tool_start  → result.tool_calls + stdout marker
              ├── streams tool_result → result.stdout / .stderr
              ├── auto-replies "y" to any action_required prompt
              └── on done event       → exit_code 0
          if exit_code == 0: return (combined_output, 0)
        return (last_output, last_code)
```

There is no litellm, no `--openai-api-base` shell argument, no per-model
prefix munging. Each daemon is launched with `OPENAI_API_KEY`,
`OPENAI_BASE_URL`, `OPENAI_MODEL` set in its own process environment, so
the gRPC client just speaks to whichever port matches the desired
provider. The legacy `run_aider` symbol is preserved as an alias for
backwards compatibility with the Hermes/SAST/red-team callers.

### 2.2 Hermes path — `hermes_orchestrator.py::_hermes_llm_call`

```
build provider list:
  if DO_INFERENCE_API_KEY:
      providers.append( ("DigitalOcean", DO_INFERENCE_BASE, DO_KEY, HERMES_DO_MODEL, {}) )
  if OPENROUTER_API_KEY:
      providers.append( ("OpenRouter", OPENROUTER_BASE, OR_KEY, HERMES_OR_MODEL, {HTTP-Referer: ...}) )

for (name, base, key, model, extra_headers) in providers:
    POST {base}/chat/completions  with Bearer key, body {model, messages, ...}
    on HTTP 429:
        sleep exponential(attempt) and retry up to N times
    on other 5xx or network error:
        record reason, continue to next provider
    on 200:
        return {"content": choice.message.content, "provider": name, "model": model}

if all providers exhausted:
    return {"error": "all providers failed", "details": [...]}
```

This is implemented in the helpers `_post_chat_completion` (raw HTTP +
retry), `_strip_provider_prefix` (litellm-style prefix removal so the
DigitalOcean endpoint sees a clean model name), and `_hermes_llm_call`
(orchestrates the chain). The same chain is used by adversarial reviewer
calls because they delegate through `_hermes_llm_call`.

### 2.3 Why DO first

DigitalOcean's Serverless Inference is paid, predictable, and sized for the
hot path. OpenRouter's free tier exists, but rate limits and 429s during
adversarial bursts (3 concurrent reviewer models) make it unreliable as a
primary. Keeping OpenRouter as a fallback preserves resilience without
making the burst case the steady state.

### 2.4 Required env vars

| Var | Purpose | Default |
|---|---|---|
| `DO_INFERENCE_API_KEY` | DigitalOcean Serverless Inference key | none — if unset, DO path is skipped |
| `DO_INFERENCE_BASE_URL` | Endpoint base | `https://inference.do-ai.run/v1` |
| `DO_INFERENCE_MODEL` | Aider's primary model name on DO | `llama3.3-70b-instruct` |
| `HERMES_DO_MODEL` | Hermes' primary model name on DO (may differ) | falls back to `DO_INFERENCE_MODEL` |
| `OPENROUTER_API_KEY` | OpenRouter key for fallback + adversarial models | none — if unset, OR path is skipped |
| `HERMES_OR_MODEL` | Hermes' OpenRouter fallback model | `qwen/qwen-2.5-coder-32b-instruct:free` |

If neither DO nor OpenRouter is configured the system logs a single explicit
error per audit. There is no silent degradation — by design.

---

## 3. Top-Level Topology
<a id="3-top-level-topology"></a>

The Space is a single Docker container that runs:

```
┌────────────────────────────────────────────────────────────────────────┐
│ Container (port 7860 exposed, 7861 + 7862 internal)                    │
│                                                                         │
│  ┌──────────────────────┐    ┌──────────────────────┐                  │
│  │ Gradio dashboard     │    │ Webhook server       │                  │
│  │ app.py:demo          │    │ webhook_server.py    │                  │
│  │ port 7860            │    │ port 7861            │                  │
│  │ 10 tabs + chat inbox │    │ /webhook/github      │                  │
│  └──────────┬───────────┘    └──────────┬───────────┘                  │
│             │                            │                              │
│             └─────────┬──────────────────┘                              │
│                       ▼                                                  │
│           ┌────────────────────────┐                                    │
│           │ enterprise_audit_loop  │  ← background threads dispatched   │
│           │ (app.py)               │     for each repo audit            │
│           └─────────┬──────────────┘                                    │
│                     │                                                    │
│                     ▼                                                    │
│           ┌────────────────────────┐                                    │
│           │ Worker Pool            │  ← ThreadPoolExecutor, optionally  │
│           │ worker_pool.py         │    process-isolated per job        │
│           └─────────┬──────────────┘                                    │
│                     │                                                    │
│                     ▼                                                    │
│           process_failing_test() … 15-step healing loop                 │
│                                                                          │
│  Background daemons (started conditionally):                             │
│  • repo_harvester.py  (autonomous target selection, every 6h)           │
│  • commit_watcher.py  (silent-patch detection)                          │
│  • lora_scheduler.py  (training-data export)                            │
│  • red_team_fuzzer.py (when all tests are green)                        │
│  • mythos.api.fastapi_server (optional, port 7863)                      │
│  • public_leaderboard.py (optional, port 7862)                          │
│                                                                          │
│  Persistent storage (mounted at /data):                                  │
│  • job_queue.sqlite                                                      │
│  • training_store.sqlite                                                 │
│  • embedding_index.sqlite (or Qdrant remote)                             │
│  • audit_trail.jsonl                                                     │
│  • harvester_feed.json                                                   │
│  • lora_exports/*.jsonl                                                  │
│  • disclosure_vault/                                                     │
│  • repo/  (cloned target repositories, ephemeral)                        │
│                                                                          │
│  External calls:                                                         │
│  • GitHub API (clone, PR, fork, check_run, merge)                       │
│  • DigitalOcean Inference (primary)                                      │
│  • OpenRouter (fallback + adversarial models)                            │
│  • OpenRouter for adversarial trio (Qwen/Gemma/Mistral)                 │
│  • Telegram & Slack (notifications)                                      │
│  • HackerOne / Bugcrowd (bounty submissions, optional)                  │
│  • NVD / OSV / Snyk (CVE intelligence)                                   │
│  • Shodan, Wayback, crt.sh (recon, optional)                            │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 4. Container & Build — Dockerfile and Requirements
<a id="4-container--build"></a>

### 4.1 `README.md` front-matter (the HF Space manifest)

```yaml
title: Rhodawk AI DevSecOps Engine
sdk: docker
app_port: 7860
license: apache-2.0
```

`sdk: docker` is the critical line. With `sdk: gradio`, HF Spaces injects
`gradio[oauth,mcp]==<sdk_version>` plus `uvicorn`, `websockets`, `spaces`,
and `mcp` into the build's pip command — overriding our explicit pins and
breaking the resolver. With `sdk: docker`, HF runs the Dockerfile verbatim
and exposes only `app_port` to the public preview iframe.

### 4.2 `Dockerfile` (logical structure)

```dockerfile
FROM python:3.12-slim AS base
# system deps for: git (clone), build-essential (some wheels),
# libpq-dev (psycopg2), libssl/libffi (cryptography), curl, jq, nodejs (MCP servers)
RUN apt-get update && apt-get install -y --no-install-recommends \
        git build-essential libpq-dev libssl-dev libffi-dev curl jq \
        nodejs npm && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt /app/requirements.txt

# Stage A: install everything pip can solve cleanly
RUN pip install --no-cache-dir -r requirements.txt mcp-server-fetch && \
    # Stage B: install aider WITHOUT its strict pins (pillow==12.1.1, litellm==1.75.0)
    pip install --no-cache-dir --no-deps "aider-chat==0.86.2" && \
    # Stage C: replace aider's broken litellm pin with a working release
    pip install --no-cache-dir --upgrade --no-deps "litellm==1.78.5" && \
    # Stage D: provide aider's actual runtime imports (subset of its setup.py)
    pip install --no-cache-dir \
        configargparse jsonschema rich prompt_toolkit pyyaml \
        packaging pathspec diskcache networkx scipy \
        beautifulsoup4 pypandoc flake8 importlib_resources \
        pyperclip pexpect json5 psutil watchfiles socksio \
        mixpanel posthog tree-sitter grep_ast oslex \
        tokenizers google-generativeai openai diff-match-patch \
        soundfile sounddevice

COPY . /app
EXPOSE 7860 7861
CMD ["python", "app.py"]
```

**Why this layered install pattern works.** The pip resolver cannot satisfy
`pillow<12` (gradio) and `pillow==12.1.1` (aider) simultaneously. By
installing aider with `--no-deps` we let gradio's pillow 11 win. Aider only
imports a small fraction of its declared deps at runtime, and those that
matter are installed explicitly in Stage D. The litellm replacement is
necessary because the version aider pins (1.75.0) ships a broken module
surface — `litellm.APIConnectionError`, `litellm._logging`,
`litellm.encode`, and `litellm.token_counter` are all referenced by aider
but not exported by 1.75.0. 1.78.5 restores them.

### 4.3 `requirements.txt` (resolved set)

The file declares: `requests`, `pytest`, `uv>=0.7.0`, `gitpython==3.1.46`,
`gradio>=5.49.0,<6`, `jinja2==3.1.6`, `ruff`, `tenacity`, `bandit[toml]`,
`pip-audit`, `radon`, `hypothesis[cli]>=6.100.0`, `semgrep>=1.45.0`,
`sentence-transformers>=2.7.0`, `sqlite-vec>=0.1.1`, `pygithub>=2.3.0`,
`PyJWT>=2.8.0`, `datasets>=2.19.0`, `numpy>=1.26.0`, `psycopg2-binary>=2.9.9`,
`rapidfuzz>=3.0.0`, `z3-solver>=4.12.0`, `qdrant-client>=1.9.0`,
`transformers>=4.40.0`, `torch>=2.2.0`, `starlette`, plus optional FastAPI
deps used by the Mythos API server.

`aider-chat` is intentionally absent — see Stage B above.

---

## 5. Process Map at Runtime
<a id="5-process-map-at-runtime"></a>

| Process / Thread | Started by | Lifetime | Listens on | Purpose |
|---|---|---|---|---|
| Main Python process | `python app.py` | container lifetime | — | imports modules, starts threads, hosts Gradio |
| Gradio Uvicorn worker | Gradio's `demo.launch()` | container lifetime | 7860 | serves the dashboard UI |
| Webhook Uvicorn worker | `webhook_server.start()` thread | container lifetime | 7861 | receives GitHub & CI webhooks |
| Audit threads | `submit_repo_audit()` per request | per audit | — | runs `enterprise_audit_loop` for one repo |
| Worker pool threads | `worker_pool.run()` inside an audit | per audit | — | parallel test repair |
| Worker subprocesses | optional, when `RHODAWK_PROCESS_ISOLATE=true` | per job | — | per-job blast radius isolation |
| Aider subprocess | `subprocess.Popen` per fix attempt | per attempt | — | LLM patch generation |
| MCP server processes | `npx`/`uvx` spawned by aider | per attempt | stdio | tools (fetch, github, filesystem, etc.) |
| Adversarial review threads | `concurrent.futures` in `adversarial_reviewer` | per gate | — | 3-model parallel review |
| Harvester daemon | `repo_harvester.start_daemon()` if enabled | container lifetime | — | autonomous target search |
| Commit watcher | `commit_watcher.start_daemon()` if enabled | container lifetime | — | silent-patch correlation |
| LoRA scheduler | `lora_scheduler.start_daemon()` if enabled | container lifetime | — | training data export trigger |
| Mythos FastAPI | optional | container lifetime | 7863 | external programmatic API |
| Leaderboard | optional | container lifetime | 7862 | public stats Gradio |

All daemons are gated by their respective `RHODAWK_*_ENABLED` env vars and
are off by default to keep the cold-start container minimal.

---

## 6. Master Orchestrator — `app.py`
<a id="6-master-orchestrator"></a>

`app.py` is 2,704 lines. It is the wiring file. Conceptually it has six
sections.

### 6.1 Module imports & global config
Lines ~1–200. Imports every other module in the project. Reads
~50 environment variables into module-level constants
(`DEFAULT_MODEL`, `MAX_RETRIES`, `WORKERS`, `OPENROUTER_API_KEY`,
`DO_INFERENCE_API_KEY`, `DO_INFERENCE_BASE_URL`, `DO_INFERENCE_MODEL`,
`FALLBACK_MODELS`, `RHODAWK_TENANT_ID`, audit/disclosure/training paths,
adversarial config, conviction thresholds, harvester config, etc.).

### 6.2 MCP runtime config writer
Lines ~200–470. Reads `mcp_config.json` (the template), substitutes
`__INJECTED_BY_APP_AT_RUNTIME__` placeholders with real values from env,
and writes the materialized config to `/tmp/mcp_runtime.json`. Aider is
launched with `--mcp-config /tmp/mcp_runtime.json` so that all MCP tools
(fetch-docs, github-manager, filesystem-research, semgrep-sast, …) are
available during patch generation.

### 6.3 `run_aider(prompt, repo_dir, model=None)` — provider chain
Lines ~600–700. The function described in §2.1. Chooses the provider list
based on which API keys are set, runs `aider` as a subprocess with the
right env and CLI flags, captures stdout/stderr, parses the diff, and
returns `(stdout, stderr, exit_code, model_used)`. On non-zero exit it
moves to the next provider.

### 6.4 `process_failing_test(...)` — the 15-step healing loop
The single most important function in the project.

```
1.  Memory retrieval — embedding_memory.retrieve_similar_fixes_v2(failure_text)
2.  Build prompt    — verification_loop.build_initial_prompt(test_path, failure, similar)
3.  Aider call      — run_aider(prompt, repo_dir)              (provider chain)
4.  Re-run test     — runtime.run_tests(test_path)
5.  If still FAIL   — append failure delta, build_retry_prompt, GOTO 3 (up to MAX_RETRIES)
6.  SAST gate       — sast_gate.run_sast(repo_dir, diff)
7.  If BLOCK        — append SAST critique, GOTO 3
8.  Supply chain    — supply_chain.run_supply_chain(diff, language)
9.  If BLOCK        — append supply-chain critique, GOTO 3
10. Z3 verify       — formal_verifier.verify(diff)             (if enabled)
11. If UNSAFE       — append Z3 critique, GOTO 3
12. Adversarial     — adversarial_reviewer.review_concurrent(diff, failure, repo)
13. If REJECT       — append adversarial critique, GOTO 3 (with extended budget)
14. Persist         — training_store.record_attempt(...)
15. Return verdict  — VerificationResult(success, attempts, verdicts...)
```

The retry budget is normally `MAX_RETRIES` (default 5) but is multiplied by
`ADVERSARIAL_REJECTION_MULTIPLIER` when the retry was triggered by an
adversarial reject — to give the model more chances when the gate is the
strict adversarial trio rather than a hard test failure.

### 6.5 `process_audit_test(...)` — wraps healing with PR + conviction
Calls `process_failing_test`, then on success:
- `github_app.open_pr_for_repo(repo, branch, title, body)` → URL
- `conviction_engine.evaluate(verification_result, adversarial_result, memory_match)` → `Conviction`
- If `Conviction.met` and `RHODAWK_AUTO_MERGE=true`: `github_app.merge_pr(url)`
- `audit_logger.append({event: PR_OPENED, ...})`
- `notifier.notify_pr_opened(repo, url)`

### 6.6 `enterprise_audit_loop(repo)` — the per-audit driver
- Clones the repo into `/data/repo/<sanitized-owner>__<repo>`
- `RuntimeFactory.for_repo(repo_dir)` returns the right `LanguageRuntime`
- `runtime.setup_env()` (creates venv, installs deps)
- `runtime.discover_tests()` returns a list of test file paths
- Runs each test once to find the failing set
- Submits each failing test to the worker pool, which calls `process_audit_test`
- On completion: `red_team_fuzzer.start(repo_dir)` if all tests are now green
- Logs a final `AUDIT_COMPLETE` event

### 6.7 Gradio UI
The `demo` block defines 10 tabs:
1. **Chat Inbox** — submit `owner/repo` to start an audit
2. **Live Agent Log** — real-time tail of the audit log with auto-refresh (3 s)
3. **Audit Trail** — paginated view of `audit_trail.jsonl` with filters
4. **Memory Browser** — search the embedding memory by failure text
5. **Training Store** — stats and JSONL export trigger
6. **Harvester** — refresh feed, view ranked candidates, dispatch manually
7. **Findings** — vulnerability findings from Hermes / red team
8. **Hermes Sessions** — list of research sessions with phases & VES scores
9. **System Status** — env-var presence, daemon status, queue depth
10. **Settings** — read-only display of effective configuration

The Live Agent Log uses a `gr.Timer` that fires every 3 seconds to repaint
the latest 200 lines of the in-memory log buffer.

---

## 7. Hermes Six-Phase Pipeline — `hermes_orchestrator.py`
<a id="7-hermes-pipeline"></a>

The Hermes orchestrator is a research-and-disclosure pipeline parallel to
the test-healing loop. It runs against a target codebase or live host and
produces structured `VulnerabilityFinding` records.

### 7.1 Phases

| # | Enum value | Module(s) called | Output |
|---|---|---|---|
| 1 | `RECON` | `repo_harvester`, `mythos.mcp.reconnaissance_mcp`, `subdomain_enum_mcp`, `httpx_probe_mcp`, `wayback_mcp`, `shodan_mcp` | target inventory + tech fingerprint |
| 2 | `STATIC` | `taint_analyzer`, `semantic_extractor`, `mythos.static.{treesitter_cpg, joern_bridge, codeql_bridge, semgrep_bridge}` | candidate sinks + CWE hits |
| 3 | `DYNAMIC` | `fuzzing_engine`, `harness_factory`, `mythos.dynamic.{aflpp_runner, klee_runner, qemu_harness, frida_instr, gdb_automation}` | crashes, traces, coverage |
| 4 | `EXPLOIT` | `exploit_primitives`, `mythos.exploit.{pwntools_synth, rop_chain, heap_exploit, privesc_kb}` | working PoC artifacts |
| 5 | `CONSENSUS` | `adversarial_reviewer`, `_run_acts_consensus()` | model-quorum verdict + ACTS score |
| 6 | `DISCLOSURE` | `disclosure_vault`, `bounty_gateway`, `notifier` | encrypted writeup + optional submission |

### 7.2 Tool dispatch
Each phase exposes a small set of `HermesTool` subclasses
(`ReconTool`, `TaintTool`, `SymbolicTool`, `FuzzTool`, `ExploitTool`,
`CVETool`, `CommitWatchTool`, `SSECTool`, `ChainAnalyzerTool`). The
`_dispatch_tool(tool_name, args, session)` function looks up the class by
name and runs it with the session context. Tool output is appended to
`session.findings` and persisted via `persist_hermes_session(session)`.

### 7.3 Scoring
- `compute_ves(...)` — Vulnerability Evidence Score: weighted combination of
  reproducibility, exploitability, impact, and code-confidence signals.
- `compute_acts(model_verdicts)` — Adversarial Consensus Trust Score:
  measures inter-model agreement on the diff/exploit, used as an additional
  gate before disclosure.

### 7.4 LLM call surface
Every Hermes-triggered LLM call goes through `_hermes_llm_call`, which
implements the DO-primary / OpenRouter-fallback chain described in §2.2.
This means even adversarial review and disclosure-prose generation
benefit from the same provider resilience.

### 7.5 Session persistence
`HermesSession` is a dataclass (`session_id`, `target`, `phase`,
`findings`, `tool_invocations`, `started_at`, `finished_at`,
`provider_history`, `ves`, `acts`). `persist_hermes_session(session)`
writes a JSON artifact under `/data/hermes_sessions/<session_id>.json`
and appends an audit-trail event. The Gradio "Hermes Sessions" tab reads
from this directory.

### 7.6 TVG — Threat-Vector Graph
`build_tvg(repo_dir, findings)` produces a directed graph of
`(source → sink, primitive, finding_id)` edges suitable for downstream
visualization or LLM-driven exploit-chain reasoning. Used by
`mythos/reasoning/attack_graph.py` to compute reachable attack chains.

---

## 8. Safety Gate Modules
<a id="8-safety-gates"></a>

### 8.1 `sast_gate.py`
Runs **bandit** on Python diffs, **semgrep** with language-appropriate rule
sets on every diff, and a hand-rolled 16-pattern secret scanner over diff
additions only. Patterns include: AWS access keys (`AKIA[0-9A-Z]{16}`),
generic API keys (`api[_-]?key.*[=:].{20,}`), JWTs (`eyJ[\w-]+\.[\w-]+\.[\w-]+`),
private key headers (`-----BEGIN (RSA|EC|OPENSSH|PGP) PRIVATE KEY-----`),
`.env`-style assignments, OAuth tokens, SSH host keys, hardcoded passwords
in connection strings, etc. Returns `SastVerdict(level, findings, raw)`
where `level ∈ {PASS, BLOCK}`. A single CRITICAL or HIGH finding flips to
BLOCK; MEDIUM/LOW are surfaced but advisory.

### 8.2 `supply_chain.py`
Two passes per diff:
1. **Known CVEs.** Extract added packages from `requirements.txt`,
   `package.json`, `pom.xml`, `go.mod`, `Cargo.toml`, `Gemfile`. Run the
   matching CVE scanner: `pip-audit`, `npm audit --json`, OWASP
   `dependency-check`, `govulncheck`, `cargo audit`, `bundler-audit`.
2. **Typosquatting.** For each new package name, compute Levenshtein
   distance against a 40+ entry list of canonical popular package names.
   Anything within distance 1 of a popular name (and not equal to it)
   is flagged as a likely typosquat.

### 8.3 `formal_verifier.py`
Three Z3-backed checks over diff additions:
- **Div-by-zero.** Pattern-extract `expr / divisor` and `expr % divisor`,
  parse `divisor` as a Z3 expr, query `solver.check(divisor == 0)`.
- **Negative literal index.** Find `arr[k]` where `k` is an integer literal,
  query satisfiability of `k < 0`.
- **Always-false assert.** For each `assert expr`, walk the surrounding
  scope for `name = literal` constants, substitute, query
  `solver.check(Not(expr))`.
Returns `FormalVerdict(SAFE | UNSAFE | SKIP, witnesses)`. Disabled by
default (`RHODAWK_Z3_ENABLED=false`) because Z3 is a heavy import.

### 8.4 `adversarial_reviewer.py`
Sends the diff + failure + repo identity to three reviewer models in
parallel via `concurrent.futures.ThreadPoolExecutor(max_workers=3)`. Each
model receives an instruction template that demands a strict JSON envelope:
`{verdict, confidence, critical_issues[], warnings[], retry_guidance}`.
The reviewer parses each envelope, computes:
- `consensus_votes = Counter(verdicts)`
- `consensus_fraction = max(votes.values()) / 3`
- final verdict = majority (≥`RHODAWK_CONSENSUS_THRESHOLD` of 0.67)
- `critical_issues = union(per-model critical lists)`

Sequential mode (`RHODAWK_ADVERSARY_SEQUENTIAL=true`) runs the same models
serially. Used as a fallback when concurrent calls hit OpenRouter's
per-key concurrency limits.

### 8.5 `conviction_engine.py`
Seven boolean criteria, all of which must be true to allow autonomous
merge:
1. `adversarial.verdict == APPROVE` (not just CONDITIONAL)
2. `adversarial.confidence ≥ RHODAWK_CONVICTION_CONFIDENCE` (default 0.92)
3. `adversarial.consensus_fraction ≥ RHODAWK_CONVICTION_CONSENSUS` (0.85)
4. `verification.attempts == 1` (fixed on first try)
5. `sast.findings == []` (zero SAST findings)
6. `supply_chain.added_packages == []` (no new deps)
7. `memory.best_match.similarity ≥ RHODAWK_CONVICTION_MEMORY_SIM` AND
   `memory.best_match.merged_by_human == True`

Returns `Conviction(met: bool, missing_criteria: list, score: float)`.
The `score` is a weighted combination useful for analytics even when
`met` is False.

### 8.6 `taint_analyzer.py`
Lightweight per-language source/sink dataflow analyzer used during the
Hermes STATIC phase (not in the patch healing loop). Tracks tainted
variables from common sources (HTTP request data, file reads, env vars,
CLI args) to dangerous sinks (eval, subprocess, raw SQL, `pickle.loads`,
`yaml.load`, `etree.fromstring`).

### 8.7 `symbolic_engine.py`
Wraps Z3 for richer symbolic execution beyond the single-statement checks
in `formal_verifier.py`. Used by Hermes `SymbolicTool`.

### 8.8 `vuln_classifier.py`
Maps raw findings (from SAST tools, taint, fuzzers) to CWE IDs and
estimated CVSS using a rule table. Output feeds `disclosure_vault` and
`bounty_gateway`.

---

## 9. Memory, Learning, and Data Flywheel
<a id="9-memory-learning"></a>

### 9.1 `embedding_memory.py`
Two interchangeable backends:

**SQLite + MiniLM (default).** `sentence-transformers/all-MiniLM-L6-v2` for
encoding. Embeddings stored in a SQLite table `(id, failure_norm, embedding
BLOB, fix_diff, outcome, repo, ts)` and queried by cosine similarity using
`sqlite-vec`. Lightweight, runs entirely in-process, no external service.

**Qdrant + CodeBERT (optional).** `microsoft/codebert-base` for code-aware
encoding. Vectors pushed to a Qdrant collection (HNSW index) — local or
remote. Switched on via `RHODAWK_EMBEDDING_BACKEND=qdrant`.

Public API used by the rest of the system:
- `retrieve_similar_fixes_v2(failure_text, top_k=5)` → list of past fixes
- `record_fix(failure_text, diff, outcome, repo)` → persists for future retrieval
- `rebuild_embedding_index()` → re-encode entire training_store on demand

Failure normalization strips file paths, line numbers, addresses, and
hex IDs so that semantically identical failures across different repos
collide in embedding space.

### 9.2 `memory_engine.py`
Legacy v1 store. Exact-key lookup by normalized failure signature. Kept
for cold-start scenarios where the embedding index has zero entries.

### 9.3 `training_store.py`
SQLite database (`/data/training_store.sqlite`) with two tables:
- `fix_attempts(id, ts, repo, test_path, failure, diff, model, attempt, success)`
- `fix_patterns(signature, success_count, attempt_count, last_seen)`

Entry points:
- `record_attempt(...)` — every fix attempt, success or failure
- `export_training_data(jsonl_path)` — writes
  `{"messages": [{"role": "system", ...}, {"role": "user", ...},
  {"role": "assistant", "content": diff}]}` — directly compatible with
  HuggingFace TRL/PEFT SFT trainers.
- `get_statistics()` — counts for the dashboard

### 9.4 `lora_scheduler.py`
Background daemon. Polls the training store. When **either**
`RHODAWK_LORA_MIN_SAMPLES` (default 50) new successful fix pairs accumulate
**or** `RHODAWK_LORA_MAX_AGE_HOURS` (default 168 = 1 week) elapse since the
last export, it calls `training_store.export_training_data()` to a new
JSONL file under `/data/lora_exports/lora_<timestamp>.jsonl`.

### 9.5 `knowledge_rag.py`
Retrieval-augmented generation helper for Hermes. Indexes long-form security
documentation (the `architect/skills/*.md` library plus optionally fetched
CVE writeups) and exposes a `retrieve(query, top_k)` helper that the
research planner can call to ground exploit reasoning in vetted prior art.

---

## 10. Autonomous Operation — Harvester, Worker Pool, Job Queue
<a id="10-autonomous-operation"></a>

### 10.1 `repo_harvester.py`
- Background daemon, gated by `RHODAWK_HARVESTER_ENABLED=true`.
- Cycle period: `RHODAWK_HARVESTER_POLL_SECONDS` (default 21600 = 6 h).
- Per cycle: GitHub Search API for repos in 7 supported languages
  (`language:python`, `language:javascript`, …) with at least
  `RHODAWK_HARVESTER_MIN_STARS` (default 100) and recent activity.
- Cross-references each candidate's `check-runs` API to find currently
  failing CI.
- Scoring: `0.35*log(stars+1)/log(MAX_STARS+1) + 0.40*recency_score +
  0.25*failing_check_count_score`.
- Persists ranked feed to `/data/harvester_feed.json`.
- Dispatches the top `RHODAWK_HARVESTER_MAX_REPOS` (default 20) targets
  into the audit loop via `submit_repo_audit()`.

### 10.2 `worker_pool.py`
- `ThreadPoolExecutor(max_workers=RHODAWK_WORKERS)` (default 8).
- When `RHODAWK_PROCESS_ISOLATE=true`: each job runs in
  `multiprocessing.get_context("fork").Process` with a result `Queue`
  and a hard timeout of `RHODAWK_ISOLATE_TIMEOUT` seconds (default 600).
- On timeout: process is `terminate()`d then `kill()`ed if still alive,
  job is marked `FAILED`, audit-trail event recorded.
- Falls back gracefully to in-process execution if `fork` is not available
  (e.g., Windows host — irrelevant to HF but matters for self-hosters).

### 10.3 `job_queue.py`
- SQLite-backed (`/data/job_queue.sqlite`).
- Schema: `(tenant_id, repo, test_path)` UNIQUE → `(status, pr_url,
  model_version, started_at, updated_at, attempts, last_error)`.
- States: `PENDING`, `RUNNING`, `DONE`, `FAILED`, `SAST_BLOCKED`,
  `ADVERSARIAL_REJECTED`, `CONVICTION_NOT_MET`.
- Idempotency: a `DONE` row is skipped on resubmission. A `RUNNING` row
  older than 1 hour (stale, from a crashed previous container) is reset to
  `PENDING` after a branch-cleanup pass.
- `prune_done_jobs(older_than_hours=72)` keeps the table from growing
  unbounded.

---

## 11. GitHub Surface — `github_app.py`, `webhook_server.py`, `commit_watcher.py`
<a id="11-github-surface"></a>

### 11.1 `github_app.py`
- **PAT mode (default).** Uses `GITHUB_TOKEN` directly via PyGithub.
- **GitHub App mode.** Uses `RHODAWK_APP_ID` + `RHODAWK_APP_PRIVATE_KEY`
  to issue a 10-minute JWT, exchange it for a 1-hour installation token,
  and refresh on each call. Enterprise-grade auth.
- `open_pr_for_repo(repo, branch, title, body)` — chooses standard or
  fork mode based on `RHODAWK_FORK_MODE`.
- **Standard mode.** Push branch to upstream, open PR upstream→upstream.
- **Fork mode.** `fork_repo(repo)` (waits for GitHub's async fork to
  complete by polling), push branch to fork, open cross-repo PR
  fork→upstream. This is what enables fixing repos you don't own.
- `merge_pr(url)` — used by the conviction engine when criteria are met.

### 11.2 `webhook_server.py`
HTTP server on port 7861. Endpoints:
- `POST /webhook/github` — validates `X-Hub-Signature-256` HMAC against
  `RHODAWK_WEBHOOK_SECRET`. Handles `push` and `check_run` events.
- `POST /webhook/ci` — generic CI failure trigger (token in header).
- `POST /webhook/trigger` — manual trigger (admin token).
- `GET /webhook/health` — liveness.
- `GET /webhook/queue` — current queue depth + last 20 events.
Per-IP token bucket rate limiter (default 30 req/min per IP).

### 11.3 `commit_watcher.py`
Daemon for **silent-patch detection**. Polls a configured set of
high-value upstream repos for new commits. Heuristics flag commits whose
message says "fix" / "security" / "CVE" but which have no associated
public advisory — a known pattern for CAD (Coordinated Asynchronous
Disclosure) or under-the-radar security fixes. Findings are routed to
`disclosure_vault` for downstream attribution.

### 11.4 `chain_analyzer.py`
Walks PR commit chains and groups related commits into "fix series" so
that the training store records the *full* fix, not just the first commit
in a multi-commit fix. Important for accurate (failure → fix) pair
generation.

---

## 12. Red Team & Offense Modules
<a id="12-red-team--offense"></a>

### 12.1 `red_team_fuzzer.py`
1,561 lines. The Blue Team-to-Red Team transition. When
`process_audit_test` finishes and all tests are green, this module:
- Generates property-based tests using **Hypothesis** strategies inferred
  from function signatures.
- Runs them with `pytest --hypothesis-show-statistics`.
- Captures shrunken counterexamples.
- Feeds the counterexamples into a CEGIS loop: each refuted property
  becomes the spec for the next attack synthesis round.
- Zero-day candidates are written as JSON artifacts under `/data/findings/`
  and handed back to the Blue Team healing loop so the bug becomes a fix.

### 12.2 `fuzzing_engine.py`
Lower-level fuzzing primitives consumed by both `red_team_fuzzer.py` and
the Hermes DYNAMIC phase. Bridges to `mythos/dynamic/aflpp_runner.py`,
`klee_runner.py`, and `qemu_harness.py` when those are available.

### 12.3 `harness_factory.py`
Generates fuzz harnesses from function signatures: type inference,
seed corpus extraction from existing tests, AFL++/libFuzzer wrapper
emission. Used by `red_team_fuzzer.py` and Hermes.

### 12.4 `exploit_primitives.py`
Catalogs reusable exploitation primitives: arbitrary read/write,
function-pointer overwrite, format-string leak, integer-overflow ladder,
heap-grooming templates. Each primitive has a `match(finding) → bool`
predicate and an `apply(finding) → ExploitArtifact` synthesizer.

### 12.5 `cve_intel.py`
NVD/OSV/Snyk lookup for prior-art correlation. Given a finding, returns
the closest known CVE and similarity score so the disclosure isn't a
duplicate.

---

## 13. Notification, Audit, Disclosure, Bounty
<a id="13-notification-audit"></a>

### 13.1 `notifier.py`
- Telegram via Bot API (`TELEGRAM_BOT_TOKEN` + `TELEGRAM_CHAT_ID`).
- Slack via incoming webhook (`SLACK_WEBHOOK_URL`).
- All sends are non-blocking (background threads with bounded queue).
- Templates for: AUDIT_START, TEST_FAIL, PR_CREATED, PATCH_FAIL,
  SAST_BLOCK, AUDIT_COMPLETE, ZERO_DAY_FOUND, DISCLOSURE_SUBMITTED.

### 13.2 `audit_logger.py`
Append-only JSONL at `/data/audit_trail.jsonl`. Each entry:
```json
{
  "ts": "2026-04-22T12:34:56Z",
  "event": "ADVERSARIAL_REVIEW",
  "tenant": "acme",
  "repo": "owner/name",
  "payload": {...},
  "prev_hash": "sha256:...",
  "hash": "sha256:..."
}
```
`prev_hash` is the hash of the previous entry; `hash` is the SHA-256 of
the current entry (excluding the `hash` field itself). The genesis entry
has `prev_hash = "0"*64`.

`verify_chain_integrity()` walks the file from genesis, recomputes each
hash, and asserts equality. Any tamper anywhere breaks the chain at the
tampered point and every subsequent entry. SOC 2 / ISO 27001 evidence
artifact.

### 13.3 `disclosure_vault.py`
Encrypted at-rest storage for vulnerability writeups. Uses Fernet with a
key derived from `DISCLOSURE_VAULT_PASSPHRASE`. Each entry:
finding metadata + full PoC + suggested fix + CVE correlation. Read API
requires the same passphrase. Used by Hermes DISCLOSURE phase before
any public submission.

### 13.4 `bounty_gateway.py`
Programmatic submission to HackerOne, Bugcrowd, Intigriti, YesWeHack via
their REST APIs. Submission requires:
- Finding has passed adversarial CONSENSUS phase
- VES ≥ configured floor
- Manual approval flag (default: required) OR
  `RHODAWK_BOUNTY_AUTO_SUBMIT=true` (off by default — kept off in
  production)

### 13.5 `oss_guardian.py`
Stewardship layer for fixes pushed to OSS repos. Tracks PR status,
maintainer responses, and time-to-merge. Feeds analytics for the public
leaderboard and for the conviction engine's "merged by human" signal.

### 13.6 `oss_target_scorer.py`
Scoring helper used by both the harvester and the public leaderboard to
rank repos by community impact (stars, dependents, ecosystem centrality).

### 13.7 `public_leaderboard.py`
Standalone Gradio interface (port 7862) showing PRs submitted, PRs
merged, repos touched, patterns learned, zero-days reported. All numbers
read directly from `audit_trail.jsonl` and `training_store.sqlite` —
no synthetic metrics.

### 13.8 `swebench_harness.py`
Runs the Rhodawk healing loop against SWE-bench Verified instances.
Reports pass@1. Same pipeline as production — no special-cased logic.
Provides reproducible benchmarks for investor/customer claims.

---

## 14. Architect Subsystem — Tier Routing, Sandbox, Skills, Night Mode
<a id="14-architect"></a>

The `architect/` package is the higher-order control layer that sits above
the per-test healing loop and decides which model, which skill, and which
sandbox each task should use.

### 14.1 `architect/model_router.py`
Five-tier model router. Each task is classified by complexity and routed
to the cheapest tier that can satisfy it:
- **Tier 1 — Ultra.** DeepSeek 3.2, MiniMax 2.5. Used for global strategy
  and multi-repo planning.
- **Tier 2 — Strong.** Qwen 2.5 Coder 32B. Default patch generator.
- **Tier 3 — Balanced.** Llama 3.3 70B (DigitalOcean), DeepSeek V3,
  Gemma 2 27B. Adversarial reviewers.
- **Tier 4 — Lite.** Mistral 7B, Gemma 2 9B. Cheap second-opinion calls.
- **Tier 5 — Local.** Embedded MiniLM/CodeBERT for embeddings — no LLM call.

The router consumes `(task_type, code_size_tokens, security_sensitivity,
required_capabilities)` and returns a routing decision with `provider`,
`model`, and `expected_cost_usd`.

### 14.2 `architect/sandbox.py`
`SandboxManager` — abstraction over (a) plain subprocess, (b) `bwrap`
(bubblewrap) namespace isolation, (c) Firecracker microVM (planned).
Currently used in subprocess + bwrap modes for any tool execution that
must not touch the host filesystem outside `/tmp/sandbox/<id>/`.

### 14.3 `architect/skill_registry.py`
Registers the 28 skill markdown files under `architect/skills/` as
discoverable knowledge units. Each skill file declares: domain
(api-security, container-escape, smart-contract-audit, …), required
tools, suggested model tier, and reference references. The registry
exposes `find_skills(query) → list[Skill]` for the planner.

### 14.4 `architect/skills/`
28 long-form security playbooks covering: api-security, ai-ml-security,
automotive-security, aviation-aerospace, binary-analysis, browser-engine
security, ci-cd-pipeline-attack, cloud-security, container-escape,
cryptographic-implementation, cryptography-attacks, firmware-analysis,
hardware-protocols, ics-scada, linux-kernel-exploitation, llm-system-
prompt-injection, memory-safety, mobile-android, mobile-ios, network-
protocol, reverse-engineering, rf-radio-security, satellite-comms,
smart-contract-audit, supply-chain, vibe-coded-app-hunter, web-security
advanced, zero-day-research, plus `bb-methodology-claude.md` and
`bug-bounty-reference-index.md`.

### 14.5 `architect/nightmode.py`
The autonomous "night mode" loop. When enabled, between human-driven
audits the system pulls in scope from connected bug-bounty platforms
(via `mythos.mcp.scope_parser_mcp`), enumerates targets, and runs
Hermes pipelines against authorized scope only — submitting findings
through `bounty_gateway`. Hard-gated by `ARCHITECT_NIGHTMODE_ENABLED=true`
and a per-platform scope-acceptance check.

### 14.6 `architect/godmode_consensus.py`
A heavier-weight consensus protocol used by night mode that runs the
adversarial trio AND a Tier 1 model, requiring unanimous agreement
before any external submission. Higher false-negative rate, near-zero
false-positive rate — appropriate when the action is irreversible.

### 14.7 `architect/master_redteam_prompt.py`
Centralizes the master prompt used by the red-team modules. Externalizing
the prompt makes it tunable without code changes and auditable for
prompt-injection resistance.

### 14.8 `architect/parseltongue.py`
Internal DSL for declaring multi-step research plans. Compiles to a
sequence of `HermesTool` invocations. Used by the Mythos planner agent.

### 14.9 `architect/embodied_bridge.py`
Bridge to the EmbodiedOS / OpenClaw / Hermes Agent runtime when present
externally. Stubs gracefully when EmbodiedOS is not reachable.

### 14.10 `architect/rl_feedback_loop.py`
RL feedback collector. After each fix, an outcome reward is computed
(merge=+1, rejected=-0.5, never-reviewed-after-30-days=-0.1) and the
plan-level statistics are updated for the planner's policy table.

---

## 15. Mythos Subsystem — Multi-Agent + RL + 17 MCP Servers
<a id="15-mythos"></a>

`mythos/` is the deepest research layer — designed to close the gap between
Rhodawk's deterministic 6-phase pipeline and a Mythos-class autonomous
research agent.

### 15.1 `mythos/MYTHOS_PLAN.md`
Living blueprint document mapping Rhodawk's gaps to concrete Mythos
modules. Read this first to understand the design intent.

### 15.2 `mythos/agents/`
- `base.py` — abstract `Agent` class with `observe`, `plan`, `act`.
- `planner.py` — generates research plans from a target description.
  Uses the Tier 1 model + RL policy table.
- `explorer.py` — enumeration agent for recon and surface mapping.
- `executor.py` — runs concrete tools (calls into `mythos/static`,
  `mythos/dynamic`, `mythos/exploit`).
- `orchestrator.py` — top-level coordinator that wires planner →
  explorer → executor → consensus and persists the trace.

### 15.3 `mythos/static/`
- `treesitter_cpg.py` — Tree-sitter–based Code Property Graph builder.
- `joern_bridge.py` — Joern CPG queries for taint chains.
- `codeql_bridge.py` — CodeQL pack runner with predefined query sets.
- `semgrep_bridge.py` — Semgrep with curated security rule packs.

### 15.4 `mythos/dynamic/`
- `aflpp_runner.py` — AFL++ harness execution.
- `klee_runner.py` — KLEE symbolic execution wrapper.
- `qemu_harness.py` — full-system QEMU with snapshot/restore.
- `frida_instr.py` — Frida runtime instrumentation sessions.
- `gdb_automation.py` — scripted GDB triage of crashes.

### 15.5 `mythos/exploit/`
- `pwntools_synth.py` — pwntools-based PoC synthesis.
- `rop_chain.py` — ROP gadget search + chain assembly via ROPGadget.
- `heap_exploit.py` — heap exploitation primitives (tcache, fastbin,
  unsafe-unlink).
- `privesc_kb.py` — privilege escalation knowledge base + matcher.

### 15.6 `mythos/learning/`
- `rl_planner.py` — RL planner using the reward signal from
  `architect/rl_feedback_loop.py`.
- `curriculum.py` — curriculum learning over progressively harder
  vulnerability classes.
- `episodic_memory.py` — episodic store of full
  (target, plan, action, observation, reward) trajectories.
- `mlflow_tracker.py` — MLflow run tracking for training experiments.
- `lora_adapters.py` — LoRA adapter loader; lets the system swap in
  domain-specific adapters per task.

### 15.7 `mythos/reasoning/`
- `probabilistic.py` — probabilistic attack-vector reasoning.
- `attack_graph.py` — attack-graph construction over `(asset, action,
  result)` triples; computes minimum-cost reachable goal paths.

### 15.8 `mythos/api/`
- `fastapi_server.py` — optional FastAPI server (port 7863) exposing
  `/audit`, `/research`, `/findings`, `/leaderboard` JSON APIs.
- `auth.py` — bearer-token auth middleware.
- `schemas.py` — Pydantic request/response models.
- `webhooks.py` — webhook delivery on async events.

### 15.9 `mythos/skills/`
- `registry.py` — runtime skill discovery and ranking. Bridges to
  `architect/skill_registry.py` to expose skills via MCP.

### 15.10 `mythos/integration.py`
Top-level wiring. Initializes the Mythos subsystem from `app.py`'s
startup. If Mythos modules fail to import (optional dependencies
missing), it logs a warning and lets the system continue without the
Mythos features.

### 15.11 `mythos/diagnostics.py`
Self-test CLI. `python -m mythos.diagnostics` prints which agents,
MCP servers, and external tools are reachable, and exits non-zero if
any required component is broken. Used by the `mythos.__main__` entry
point and by container health checks.

### 15.12 `mythos/__main__.py`
Allows `python -m mythos` to launch the Mythos subsystem standalone.

---

## 16. MCP Suite — Every Server, Every Domain
<a id="16-mcp-suite"></a>

The `mcp_config.json` template declares **34 MCP server entries** (with
some duplicates — see note below). Aider is launched with the rendered
`/tmp/mcp_runtime.json` so all of these tools become callable during
patch generation. Hermes also calls them directly.

### 16.1 Generic / shared servers
| Server | Command | Purpose |
|---|---|---|
| `fetch-docs` | `uvx mcp-server-fetch` | HTTP fetch with SSRF allow-list (60+ domains) |
| `github-manager` | `npx @modelcontextprotocol/server-github` | full GitHub API |
| `filesystem-research` | `npx @modelcontextprotocol/server-filesystem` | RO access to `/data/repo`, `/tmp/research`, `/tmp/findings` |
| `memory-store` | `npx @modelcontextprotocol/server-memory` | persistent KG of exploit chains |
| `sequential-thinking` | `npx @modelcontextprotocol/server-sequential-thinking` | structured CoT |
| `web-search` | `npx @modelcontextprotocol/server-brave-search` | Brave search API |
| `git-forensics` | `npx @modelcontextprotocol/server-git` | deep git-history analysis |
| `postgres-intelligence` | `npx @modelcontextprotocol/server-postgres` | findings DB queries |
| `sqlite-findings` | `npx @modelcontextprotocol/server-sqlite` | local findings DB |

### 16.2 Security tooling shells (`mcp-server-shell` allow-list)
| Server | Allowed binaries | Purpose |
|---|---|---|
| `nuclei-scanner` | `nuclei,nuclei-templates` | DAST + CVE templates |
| `semgrep-sast` | `semgrep` | taint + CWE + secrets |
| `trufflehog-secrets` | `trufflehog` | git-history secret scan |
| `bandit-sast` | `bandit` | Python AST SAST |
| `pip-audit-sca` | `pip-audit,pip` | OSV-backed Python SCA |
| `osv-scanner` | `osv-scanner` | multi-ecosystem SCA |
| `z3-formal-verifier` | `python3` | Z3 verification scripts |
| `hypothesis-fuzzer` | `python3,pytest,hypothesis` | property-based testing |
| `atheris-fuzzer` | `python3,atheris` | coverage-guided fuzzing |
| `angr-symbolic` | `python3` | binary symbolic execution |
| `radon-complexity` | `radon` | complexity / attack surface |
| `ruff-linter` | `ruff` | anti-pattern detection |
| `aider-patcher` | `aider` | patch synthesis (recursive — careful) |

### 16.3 Intelligence + bounty
| Server | Purpose |
|---|---|
| `cve-intelligence` | NVD / CVE.org / OSV fetch |
| `bounty-platform` | HackerOne/Bugcrowd/Intigriti/YesWeHack APIs |
| `supply-chain-monitor` | PyPI/npm/crates typosquatting + dep-confusion |

### 16.4 Mythos-native MCP servers (Python modules)
| Server | Module | Purpose |
|---|---|---|
| `reconnaissance-mcp` | `mythos.mcp.reconnaissance_mcp` | language/framework/dep fingerprinting + attack surface |
| `static-analysis-mcp` | `mythos.mcp.static_analysis_mcp` | Tree-sitter CPG + Joern + CodeQL + Semgrep |
| `dynamic-analysis-mcp` | `mythos.mcp.dynamic_analysis_mcp` | AFL++ + KLEE + QEMU + Frida + GDB |
| `exploit-generation-mcp` | `mythos.mcp.exploit_generation_mcp` | Pwntools + ROP + heap + privesc |
| `vulnerability-database-mcp` | `mythos.mcp.vulnerability_database_mcp` | NVD/OSV/Exploit-DB lookup |
| `web-security-mcp` | `mythos.mcp.web_security_mcp` | OWASP ZAP + nuclei + sqlmap orchestration |
| `browser-agent-mcp` | `mythos.mcp.browser_agent_mcp` | Playwright live browser |
| `scope-parser-mcp` | `mythos.mcp.scope_parser_mcp` | bug-bounty scope ingestion |
| `subdomain-enum-mcp` | `mythos.mcp.subdomain_enum_mcp` | subfinder + amass + dnsx + crt.sh |
| `httpx-probe-mcp` | `mythos.mcp.httpx_probe_mcp` | concurrent HTTP probing + tech fingerprint |
| `shodan-mcp` | `mythos.mcp.shodan_mcp` | Shodan REST passive recon |
| `wayback-mcp` | `mythos.mcp.wayback_mcp` | Wayback / CommonCrawl historical URL recall |
| `frida-runtime-mcp` | `mythos.mcp.frida_runtime_mcp` | live Frida instrumentation |
| `ghidra-bridge-mcp` | `mythos.mcp.ghidra_bridge_mcp` | headless Ghidra / radare2 bridge |
| `can-bus-mcp` | `mythos.mcp.can_bus_mcp` | automotive CAN-bus + UDS (ISO 14229) |
| `sdr-analysis-mcp` | `mythos.mcp.sdr_analysis_mcp` | GNU Radio / rtl_sdr RF capture |

> **Duplicate-key note.** `mcp_config.json` currently declares
> `scope-parser-mcp`, `subdomain-enum-mcp`, `wayback-mcp`, `httpx-probe-mcp`,
> and `shodan-mcp` twice. JSON parse semantics use the last value, so the
> ARCHITECT-flavored variants (with `env` injections for HackerOne/Shodan
> tokens) are what wins at runtime. The earlier entries are dead weight
> and could be removed in a future cleanup commit.

### 16.5 Runtime materialization
On startup, `app.py` reads `mcp_config.json`, recursively replaces every
`__INJECTED_BY_APP_AT_RUNTIME__` placeholder with the corresponding env
var value (`OPENROUTER_API_KEY`, `BRAVE_API_KEY`, `DATABASE_URL`,
`HACKERONE_API_TOKEN`, `BUGCROWD_API_TOKEN`, `INTIGRITI_API_TOKEN`,
`SHODAN_API_KEY`, `NVD_API_KEY`, `NUCLEI_API_KEY`, `SEMGREP_APP_TOKEN`,
`GITHUB_PERSONAL_ACCESS_TOKEN`), drops any server whose required secret
is missing, and writes the result to `/tmp/mcp_runtime.json`. Aider
launches with `--mcp-config /tmp/mcp_runtime.json`. **Secrets are never
committed.**

---

## 17. Test Suite — What Each Test Asserts
<a id="17-test-suite"></a>

`tests/` contains 9 test modules and one `conftest.py`.

| Test file | What it asserts |
|---|---|
| `test_audit_chain.py` | The SHA-256 audit chain in `audit_logger.py` rejects tampering. Writes synthetic events, mutates one entry, expects `verify_chain_integrity()` to flag the break point. |
| `test_job_queue.py` | Idempotency guarantees: identical `(tenant, repo, test_path)` submissions don't duplicate. Stale RUNNING rows older than 1h reset to PENDING. Status transitions are valid. |
| `test_mcp_servers_load.py` | The MCP runtime config materializes correctly: all `__INJECTED__` placeholders are resolved or the server is dropped. No secrets leak into the rendered file. |
| `test_model_router.py` | The 5-tier router produces deterministic routing for the same input. Tier promotions happen on capability misses. Cost estimates are monotonic with tier. |
| `test_mythos_diagnostics.py` | `mythos.diagnostics.run_diagnostics()` exits 0 in healthy state and non-zero when any required Mythos module is missing. |
| `test_nightmode_smoke.py` | Architect night mode initializes without external services and refuses to act when no scope source is configured. |
| `test_scope_parser.py` | The HackerOne / Bugcrowd / Intigriti scope parsers correctly partition assets into IN_SCOPE / OUT_OF_SCOPE buckets with edge cases (wildcards, port specs, regex policies). |
| `test_skill_registry.py` | The 28 skill files in `architect/skills/` are all parseable, declare required metadata, and are discoverable by `find_skills(query)`. |
| `test_webhook_hmac.py` | `webhook_server.py` rejects requests with invalid HMAC signatures and accepts valid ones. Constant-time comparison is used (no timing side channel). |

`conftest.py` defines fixtures for: temporary `/data` overrides, mock
GitHub API, mock OpenRouter API, in-memory SQLite for the job queue and
training store, and a synthetic failing-test repo factory.

---

## 18. Data on Disk — Files, SQLite Schemas, Audit Chain
<a id="18-data-on-disk"></a>

```
/data/
├── job_queue.sqlite                 # job_queue.py
├── training_store.sqlite            # training_store.py (fix_attempts, fix_patterns)
├── embedding_index.sqlite           # embedding_memory.py SQLite backend
├── memory_engine.sqlite             # legacy v1 pattern memory
├── rhodawk_findings.db              # MCP sqlite-findings server
├── audit_trail.jsonl                # SHA-256 chained event log
├── harvester_feed.json              # ranked candidate repos
├── disclosure_vault/
│   └── <finding_id>.fernet          # encrypted writeups
├── lora_exports/
│   └── lora_<timestamp>.jsonl       # SFT-ready training data
├── hermes_sessions/
│   └── <session_id>.json            # persisted Hermes research sessions
├── findings/
│   └── <finding_id>.json            # raw findings from red team / Mythos
├── repo/
│   └── <owner>__<name>/             # cloned target repos (ephemeral)
├── nuclei-templates/                # nuclei DAST templates cache
└── research/                        # MCP filesystem-research scratch
```

`/tmp/`:
```
/tmp/
├── mcp_runtime.json                 # rendered MCP config (with secrets)
├── sandbox/<id>/                    # bwrap sandbox roots
└── findings/                        # MCP filesystem-research output
```

### 18.1 SQLite schemas (effective)

```sql
-- training_store.sqlite
CREATE TABLE fix_attempts (
  id INTEGER PRIMARY KEY,
  ts TEXT NOT NULL,
  repo TEXT NOT NULL,
  test_path TEXT NOT NULL,
  failure TEXT NOT NULL,
  diff TEXT,
  model TEXT,
  attempt INTEGER,
  success INTEGER NOT NULL
);
CREATE INDEX ix_fix_attempts_repo ON fix_attempts(repo);
CREATE INDEX ix_fix_attempts_success ON fix_attempts(success);

CREATE TABLE fix_patterns (
  signature TEXT PRIMARY KEY,
  success_count INTEGER NOT NULL DEFAULT 0,
  attempt_count INTEGER NOT NULL DEFAULT 0,
  last_seen TEXT NOT NULL
);

-- job_queue.sqlite
CREATE TABLE jobs (
  tenant_id TEXT NOT NULL,
  repo TEXT NOT NULL,
  test_path TEXT NOT NULL,
  status TEXT NOT NULL,
  pr_url TEXT,
  model_version TEXT,
  started_at TEXT,
  updated_at TEXT NOT NULL,
  attempts INTEGER NOT NULL DEFAULT 0,
  last_error TEXT,
  PRIMARY KEY (tenant_id, repo, test_path)
);

-- embedding_index.sqlite (sqlite-vec)
CREATE TABLE embeddings (
  id INTEGER PRIMARY KEY,
  failure_norm TEXT,
  embedding BLOB,           -- vector serialized via sqlite-vec
  fix_diff TEXT,
  outcome TEXT,
  repo TEXT,
  ts TEXT
);
CREATE VIRTUAL TABLE embedding_index USING vec0(
  embedding float[384]
);
```

### 18.2 Audit chain entry shape
```json
{
  "ts":  "2026-04-22T13:14:15.123Z",
  "event": "ADVERSARIAL_REVIEW",
  "tenant": "default",
  "repo": "owner/name",
  "test_path": "tests/test_x.py",
  "payload": {
    "verdict": "APPROVE",
    "confidence": 0.93,
    "consensus_fraction": 1.0,
    "models": ["qwen-2.5-7b", "gemma-2-9b", "mistral-7b"],
    "critical_issues": [],
    "warnings": ["minor style nit"]
  },
  "prev_hash": "sha256:f3a1...c0",
  "hash": "sha256:9b22...ee"
}
```

---

## 19. Complete Environment Variable Reference (Updated)
<a id="19-env-vars"></a>

This table supersedes the playbook's reference for everything related to
inference providers and the build-changed paths.

### 19.1 Required for any meaningful run
| Var | Purpose |
|---|---|
| `GITHUB_TOKEN` | PAT with `repo` scope (or use App mode below) |
| `OPENROUTER_API_KEY` | needed for fallback + adversarial trio |
| `DO_INFERENCE_API_KEY` | strongly recommended — enables paid DO primary |

### 19.2 Inference providers (new since playbook)
| Var | Default | Description |
|---|---|---|
| `DO_INFERENCE_API_KEY` | — | DigitalOcean Serverless Inference key |
| `DO_INFERENCE_BASE_URL` | `https://inference.do-ai.run/v1` | DO endpoint |
| `DO_INFERENCE_MODEL` | `llama3.3-70b-instruct` | Aider's primary model on DO |
| `HERMES_DO_MODEL` | `${DO_INFERENCE_MODEL}` | Hermes' primary model on DO |
| `HERMES_OR_MODEL` | `qwen/qwen-2.5-coder-32b-instruct:free` | Hermes' OpenRouter fallback |
| `OPENROUTER_API_KEY` | — | Fallback + adversarial models |

### 19.3 Models, retries, consensus
| Var | Default | Description |
|---|---|---|
| `RHODAWK_MODEL` | (computed: DO if available else OR free) | Aider primary model |
| `RHODAWK_ADVERSARY_MODEL` | `openrouter/qwen/qwen-2.5-7b-instruct:free` | lead reviewer |
| `RHODAWK_CONSENSUS_THRESHOLD` | `0.67` | majority fraction |
| `RHODAWK_ADVERSARY_SEQUENTIAL` | `false` | serial vs concurrent reviewers |
| `MAX_RETRIES` | `5` | healing-loop retry budget |
| `ADVERSARIAL_REJECTION_MULTIPLIER` | `2` | extra retries when reject reason is adversarial |

### 19.4 Conviction (auto-merge)
| Var | Default | Description |
|---|---|---|
| `RHODAWK_AUTO_MERGE` | `false` | enable autonomous merge |
| `RHODAWK_CONVICTION_CONFIDENCE` | `0.92` | min adversarial confidence |
| `RHODAWK_CONVICTION_CONSENSUS` | `0.85` | min consensus fraction |
| `RHODAWK_CONVICTION_MEMORY_SIM` | `0.85` | min memory similarity |

### 19.5 Memory backend
| Var | Default | Description |
|---|---|---|
| `RHODAWK_EMBEDDING_BACKEND` | `sqlite` | `sqlite` or `qdrant` |
| `RHODAWK_EMBEDDING_MODEL` | `all-MiniLM-L6-v2` | SQLite backend encoder |
| `RHODAWK_CODEBERT_MODEL` | `microsoft/codebert-base` | Qdrant backend encoder |
| `QDRANT_URL` | — | Qdrant remote URL when not local |
| `QDRANT_API_KEY` | — | Qdrant cloud auth |

### 19.6 LoRA scheduler
| Var | Default | Description |
|---|---|---|
| `RHODAWK_LORA_ENABLED` | `false` | enable scheduler |
| `RHODAWK_LORA_MIN_SAMPLES` | `50` | min new fixes per export |
| `RHODAWK_LORA_MAX_AGE_HOURS` | `168` | max time between exports |
| `RHODAWK_LORA_OUTPUT_DIR` | `/data/lora_exports` | JSONL destination |

### 19.7 Harvester
| Var | Default | Description |
|---|---|---|
| `RHODAWK_HARVESTER_ENABLED` | `false` | start daemon |
| `RHODAWK_HARVESTER_POLL_SECONDS` | `21600` | cycle interval |
| `RHODAWK_HARVESTER_MIN_STARS` | `100` | min stars to consider |
| `RHODAWK_HARVESTER_MAX_REPOS` | `20` | targets per cycle |

### 19.8 Worker pool & isolation
| Var | Default | Description |
|---|---|---|
| `RHODAWK_WORKERS` | `8` | parallel workers |
| `RHODAWK_PROCESS_ISOLATE` | `false` | per-job subprocess isolation |
| `RHODAWK_ISOLATE_TIMEOUT` | `600` | per-job timeout (seconds) |

### 19.9 GitHub
| Var | Default | Description |
|---|---|---|
| `GITHUB_TOKEN` | — | PAT auth |
| `RHODAWK_FORK_MODE` | `false` | enable fork-and-PR for any public repo |
| `RHODAWK_FORK_OWNER` | _(authenticated user)_ | org to fork into |
| `RHODAWK_APP_ID` | — | GitHub App ID |
| `RHODAWK_APP_PRIVATE_KEY` | — | GitHub App PEM |
| `RHODAWK_WEBHOOK_SECRET` | — | HMAC for `/webhook/github` |

### 19.10 Adversarial / red team / formal
| Var | Default | Description |
|---|---|---|
| `RHODAWK_RED_TEAM_ENABLED` | `true` | enable CEGIS fuzzer when all tests green |
| `RHODAWK_Z3_ENABLED` | `false` | enable Z3 formal verification gate |

### 19.11 Architect / Mythos / night mode
| Var | Default | Description |
|---|---|---|
| `ARCHITECT_NIGHTMODE_ENABLED` | `false` | enable autonomous night mode |
| `ARCHITECT_GODMODE_REQUIRED` | `true` | require unanimous consensus before external action |
| `MYTHOS_API_ENABLED` | `false` | start FastAPI on 7863 |
| `MYTHOS_API_TOKEN` | — | bearer token for the FastAPI |
| `DISCLOSURE_VAULT_PASSPHRASE` | — | Fernet key derivation passphrase |
| `RHODAWK_BOUNTY_AUTO_SUBMIT` | `false` | auto-submit to bounty platforms |

### 19.12 External intelligence
| Var | Description |
|---|---|
| `BRAVE_API_KEY` | Brave Search MCP |
| `SHODAN_API_KEY` | Shodan recon MCP |
| `NVD_API_KEY` | NVD CVE intelligence MCP |
| `NUCLEI_API_KEY` | Nuclei templates premium feed |
| `SEMGREP_APP_TOKEN` | Semgrep Cloud rules |
| `HACKERONE_USERNAME`, `HACKERONE_API_TOKEN`, `HACKERONE_API_KEY` | HackerOne |
| `BUGCROWD_API_TOKEN` | Bugcrowd |
| `INTIGRITI_API_TOKEN` | Intigriti |

### 19.13 Notifications
| Var | Description |
|---|---|
| `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` | Telegram alerts |
| `SLACK_WEBHOOK_URL` | Slack alerts |

### 19.14 Multitenancy
| Var | Default | Description |
|---|---|---|
| `RHODAWK_TENANT_ID` | `default` | namespace prefix for jobs, audits, exports |

---

## 20. Failure Modes and Recovery Procedures
<a id="20-failure-modes"></a>

| Symptom | Most likely cause | Recovery |
|---|---|---|
| Build fails on `pillow` resolver conflict | `requirements.txt` re-lists `aider-chat` | Remove it; aider must be `--no-deps` only in Dockerfile |
| Build fails with `gradio[oauth,mcp]==5.29.0` injection | Space SDK reverted to `gradio` | Confirm `sdk: docker` in `README.md` front-matter |
| Aider crashes `litellm has no attribute APIConnectionError` | litellm 1.75.0 reinstalled by transitive dep | Re-run the `pip install --no-deps litellm==1.78.5` step or pin in Dockerfile |
| All LLM calls fail with 429 | OpenRouter rate-limited and DO not configured | Set `DO_INFERENCE_API_KEY`; calls will route to DO first |
| All LLM calls fail with `No inference provider configured` | Both `DO_INFERENCE_API_KEY` and `OPENROUTER_API_KEY` missing | Set at least one; restart container |
| Webhook 401 from GitHub | `RHODAWK_WEBHOOK_SECRET` mismatch | Re-set the secret in the GitHub repo's webhook config to match |
| Audit hangs forever on a single test | Aider subprocess wedged | Set `RHODAWK_PROCESS_ISOLATE=true` and `RHODAWK_ISOLATE_TIMEOUT=600` |
| `embedding_index.sqlite` corrupted | Hard kill mid-write | Delete the file; `rebuild_embedding_index()` will reconstruct from `training_store.sqlite` |
| Audit chain integrity fails | Manual edit of `audit_trail.jsonl` | The chain is correctly rejecting tamper. To start a new chain, archive and remove the file; a new genesis entry will be written. |
| Conviction never fires | Memory has zero matches at threshold ≥0.85 | Expected on cold start; lower `RHODAWK_CONVICTION_MEMORY_SIM` to 0.75 in early life if you want auto-merge sooner — but be honest with yourself about what you're trading. |
| MCP server fails to spawn | `npx`/`uvx` missing or required env var unset | Check container has nodejs+npm and uvx (uv); confirm injected env var is present at startup |
| Harvester feed empty | Token lacks search scope or rate limited | Confirm `GITHUB_TOKEN` has `public_repo`; raise `RHODAWK_HARVESTER_MIN_STARS` |
| Mythos FastAPI 401 | Wrong bearer token | Confirm `MYTHOS_API_TOKEN` matches client header |

---

## 21. Security Model — Trust Boundaries and Threat Mitigation
<a id="21-security-model"></a>

### 21.1 Trust boundaries
1. **Container ↔ host.** Container runs as root in the Docker image but
   touches only `/data` (mounted) and `/tmp` (ephemeral). No host paths
   leak.
2. **Container ↔ target repo.** Cloned repos live in `/data/repo/<id>/`.
   They are treated as untrusted: scripts in target repos are never
   `python <target_script>`'d directly — only the runtime's allowed
   commands (`pytest`, `npm test`, `go test`, …) are invoked.
3. **Container ↔ LLM provider.** Code snippets and failure traces are
   sent over the wire to DigitalOcean Inference and OpenRouter. This is
   the primary data-leakage surface — controlled by deployment mode (HF
   Spaces is multi-tenant; self-hosted is single-tenant).
4. **MCP fetch ↔ internet.** `fetch-docs` and similar fetch MCPs use
   `FETCH_ALLOWED_DOMAINS` allow-lists to prevent SSRF against internal
   services.
5. **Webhook ↔ public internet.** All webhook endpoints validate HMAC
   signatures with constant-time comparison. Per-IP rate limiting in
   front. No untrusted JSON is unpickled.

### 21.2 Threat mitigation by attack
| Threat | Mitigation |
|---|---|
| Prompt injection in target source | Multi-model adversarial review catches divergent reactions; SAST/supply-chain catch the resulting bad diffs |
| LLM-introduced typosquat (`reqeusts`) | `supply_chain.py` Levenshtein typosquatting check |
| LLM-introduced backdoor | SAST + adversarial trio + zero-package-introduction conviction criterion |
| Tampered audit trail | SHA-256 chain detects any post-hoc edit |
| Webhook spoofing | HMAC-SHA256 with constant-time compare |
| Secret leakage via logs | Secret scanner runs over diffs; `mcp_runtime.json` is in `/tmp` not the repo |
| Subprocess sandbox escape | Runtime command allow-lists; optional bwrap; planned Firecracker |
| Bug-bounty submission of duplicate finding | `cve_intel.py` correlation + manual approval default |
| Auto-merge of an unsafe diff | 7 conviction criteria; default OFF; passes only the cleanest fixes |
| Provider compromise (e.g., OpenRouter MITM) | TLS verification; provider chain falls back rather than blindly trusting bad responses |

### 21.3 Secret hygiene
- `mcp_config.json` is a **template** with `__INJECTED_BY_APP_AT_RUNTIME__`
  placeholders. The realized config goes to `/tmp/mcp_runtime.json` which
  is not committed and is recreated on each startup.
- `.env`-style files are never read; everything goes through
  `os.getenv`. HF Spaces / Docker `-e` are the only injection paths.
- The disclosure vault uses Fernet with key derived from
  `DISCLOSURE_VAULT_PASSPHRASE`. Lose that passphrase, lose the vault —
  by design.

---

## 22. Migration Playbook — HF Space → Paid Server
<a id="22-migration"></a>

The Space is a great PoC environment but has hard limits: ephemeral
storage on free tier, single-container topology, and shared GPU resources.
The paid-server migration target is a single Linux box (DigitalOcean
Droplet, Hetzner CCX, or AWS EC2) running the same Docker image.

### 22.1 Pre-migration checklist
- [ ] All env vars from §19 documented and stored in a secrets manager
- [ ] `/data` directory size on Space measured (`du -sh /data`) and
      provisioned on the new host (recommend ≥50 GB to start)
- [ ] DigitalOcean Inference key budgeted for the expected request volume
- [ ] Webhook secret rotated for the new endpoint URL
- [ ] DNS or reverse-proxy plan in place if you want HTTPS in front of
      ports 7860/7861/7862/7863
- [ ] Decision made on Qdrant: keep SQLite/MiniLM (simpler) or stand up
      a Qdrant container alongside (better recall on large corpora)

### 22.2 Migration steps
1. **Snapshot data.** On the Space:
   ```bash
   tar czf /tmp/rhodawk-data.tgz /data
   ```
   Download via the HF Spaces file browser or via git LFS.
2. **Provision the new host.** Install Docker + Docker Compose. Mount a
   block volume at `/var/lib/rhodawk-data`.
3. **Restore data.**
   ```bash
   sudo mkdir -p /var/lib/rhodawk-data
   sudo tar xzf rhodawk-data.tgz -C /var/lib/rhodawk-data --strip-components=1
   ```
4. **Build the image** (or pull from a private registry if you've pushed
   one):
   ```bash
   git clone https://huggingface.co/spaces/Architect8999/rhodawk-ai-devops-engine
   cd rhodawk-ai-devops-engine
   docker build -t rhodawk:latest .
   ```
5. **Run with all env vars + persistent volume.**
   ```bash
   docker run -d --name rhodawk \
     -p 7860:7860 -p 7861:7861 \
     -v /var/lib/rhodawk-data:/data \
     -e DO_INFERENCE_API_KEY=... \
     -e OPENROUTER_API_KEY=... \
     -e GITHUB_TOKEN=... \
     -e RHODAWK_WEBHOOK_SECRET=... \
     -e RHODAWK_TENANT_ID=acme \
     -e RHODAWK_AUTO_MERGE=false \
     -e RHODAWK_HARVESTER_ENABLED=true \
     rhodawk:latest
   ```
6. **Update GitHub webhook** payload URL to the new host.
7. **Verify the audit chain integrity** on the new host:
   ```bash
   docker exec rhodawk python -c \
     "from audit_logger import verify_chain_integrity; verify_chain_integrity()"
   ```
8. **Run a known-failing-test repo** through the chat inbox or a webhook
   to confirm end-to-end.

### 22.3 Recommended additions on paid host
- Reverse proxy (Caddy or Traefik) terminating TLS, fronting 7860/7861.
- Docker Compose file checking the container into a restart-policy.
- `cron` or systemd timer that runs `docker exec rhodawk python -m
  mythos.diagnostics` every 5 minutes and pages on non-zero exit.
- Off-host backup of `/var/lib/rhodawk-data` nightly. The training store
  is the proprietary asset — losing it loses the moat.
- Optional Qdrant container (`qdrant/qdrant:latest`) on a private network,
  with `RHODAWK_EMBEDDING_BACKEND=qdrant` + `QDRANT_URL=http://qdrant:6333`.

### 22.4 What changes at scale (later)
- Move `job_queue` from SQLite to PostgreSQL (`psycopg2-binary` already
  installed, see `mcp_config.json` postgres-intelligence server).
- Move audit trail to S3 with versioning (the SHA-256 chain remains; only
  the storage backend changes).
- Replace single-host worker pool with a queue + worker fleet
  (Redis/RQ or Celery).
- Replace Gradio dashboard with a Next.js front-end calling the
  `mythos.api.fastapi_server` JSON API.

---

## 23. Glossary of Internal Names
<a id="23-glossary"></a>

| Name | Meaning |
|---|---|
| **Aider** | Open-source AI pair-programming CLI, used as the patch generator |
| **APIConnectionError** | Symbol that aider expects in `litellm`; missing in 1.75.0 — fixed by upgrading to 1.78.5 |
| **ACTS** | Adversarial Consensus Trust Score (Hermes) |
| **Audit chain** | The SHA-256-chained JSONL log in `audit_logger.py` |
| **Architect** | Higher-order control package (`architect/`) — tier router, sandbox, skills, night mode |
| **CEGIS** | Counterexample-Guided Inductive Synthesis (red team loop) |
| **Conviction** | The 7-criteria gate that allows autonomous merge |
| **DO** | DigitalOcean Serverless Inference (the new primary inference provider) |
| **EmbodiedOS** | External persistent runtime that hosts OpenClaw + Hermes Agent (optional bridge) |
| **Fork mode** | Forking any public repo and PR'ing back — enables fixing repos you don't own |
| **Godmode consensus** | Stricter consensus (adversarial trio + Tier 1) used by night mode |
| **Harvester** | Daemon that finds its own targets on GitHub |
| **Hermes** | The 6-phase research orchestrator (`hermes_orchestrator.py`) |
| **LoRA scheduler** | Daemon that exports successful (failure, fix) pairs as SFT JSONL |
| **MCP** | Model Context Protocol — Anthropic's tool-server protocol |
| **Mythos** | The deepest research package (`mythos/`) — multi-agent + RL + 17 native MCP servers |
| **Mythos-level** | Aspirational target capability class — autonomous frontier vulnerability research |
| **Night mode** | Autonomous bug-bounty loop running between human-driven audits |
| **OpenClaw** | Local-gateway component of EmbodiedOS |
| **OR** | OpenRouter (the new fallback inference provider) |
| **PoC** | Proof of Concept (exploit) |
| **Provider chain** | The ordered list `[DO_primary, OpenRouter_fallback]` consulted on every LLM call |
| **Sandbox** | bwrap (or planned Firecracker) isolation for tool execution |
| **SAST gate** | Static analysis security gate (bandit + semgrep + secret patterns) |
| **Supply chain gate** | CVE + typosquatting check on newly added packages |
| **Tier 1–5** | Five-tier model router classification |
| **Training store** | SQLite DB of every fix attempt — the proprietary data asset |
| **TVG** | Threat-Vector Graph |
| **VES** | Vulnerability Evidence Score (Hermes) |
| **Z3 gate** | Optional formal-verification gate using the Z3 SMT solver |

---

*Rhodawk AI — System Analysis Book*
*Companion to `FOUNDER_PLAYBOOK.md` v4.0 (which remains the canonical investor narrative)*
*Generated from the live source tree; last updated to reflect the DigitalOcean primary / OpenRouter fallback inference chain, the `--no-deps` aider install pattern, and the Docker-SDK Space configuration.*

# THE RHODAWK PLAYBOOK
**A Field Manual for Future Operators of the EmbodiedOS / Hermes / OpenClaw DevSecOps Engine**

---

> *"If you are reading this, the system is in your hands. Read every section before you turn anything on. Read the laws in Part VIII before you turn anything off."*

---

## Preface — what this document is

This playbook describes the Rhodawk DevSecOps Engine as it exists in the source tree at the commit you are reading it from. Every component, port, file path, environment variable, and behavioural rule named here is **observable in the codebase** — nothing is aspirational and nothing is invented for the sake of completeness. Where the codebase is silent, this playbook is silent.

The system is built to run **autonomously**. It can clone repositories, fix failing tests, hunt zero-days, scrape bug-bounty programs, and produce submission-ready reports without an operator in the loop — but every externally-visible action (PR merge, CVE disclosure, bounty submission) is gated behind a human approval. Those gates are **the laws**. Do not remove them.

---

## Part I — SYSTEM IDENTITY AND PURPOSE

Rhodawk is a single Docker container exposing a Gradio control plane on port 7860 (configurable via `PORT`). When booted, it brings up:

- An anti-detection real browser server (Camofox).
- Two headless coding-agent daemons (OpenClaude — see vendored notes below) reachable over gRPC.
- A self-improving meta-learning daemon (G0DM0D3).
- A Gradio UI that fronts ~50 Python modules implementing repository repair, vulnerability research, supply-chain auditing, and bug-bounty orchestration.
- An optional HTTP / Telegram natural-language command bus (OpenClaw) on port 8765.
- An optional FastAPI productization plane (Mythos) on port 7862.

The single highest-level entry point a human ever needs is the **🧬 EmbodiedOS** tab in the Gradio UI. Everything else flows through the orchestrators behind it.

### The product, in one paragraph

Rhodawk fuses two agents — **Hermes** (autonomous deep-research loop) and **OpenClaw** (operator natural-language command bus) — into a single coordinator called **EmbodiedOS**. An operator types one sentence; EmbodiedOS routes it through the right subsystem (clone / fix / mutate / hunt / scrape / report) and reports back. Findings are persisted into a tamper-evident audit chain, parked in a disclosure vault behind a 90-day responsible-disclosure clock, and only released to HackerOne / Bugcrowd / GitHub Security Advisories after a human clicks Approve.

---

## Part II — THE BRAIN STACK (the LLM-key model)

This is the most misunderstood part of the system. Read it twice.

### The four key slots the codebase reads

| Variable | Where it is read | What it powers |
|---|---|---|
| `DO_INFERENCE_API_KEY` (or alias `DIGITALOCEAN_INFERENCE_KEY`) | `entrypoint.sh`, `app.py`, `hermes_orchestrator.py` | The **PRIMARY** brain. Boots the OpenClaude gRPC daemon on `:50051` against `DO_INFERENCE_BASE_URL` (default `https://inference.do-ai.run/v1`). Default model `llama3.3-70b-instruct`. Hermes also calls this directly when `HERMES_PROVIDER=do` or `auto`. |
| `OPENROUTER_API_KEY` | `entrypoint.sh`, `app.py`, `hermes_orchestrator.py`, `adversarial_reviewer.py`, `mythos/agents/base.py` | The **FALLBACK** brain *and* the universal brain. Boots the OpenClaude gRPC daemon on `:50052` against `OPENROUTER_BASE_URL`. Default model `qwen/qwen-2.5-coder-32b-instruct:free`. Also drives the 3-model adversarial consensus (DeepSeek-R1, Llama-3.3-70B, Gemma-3-27B — all OpenRouter), the Hermes REST path, and the entire Mythos multi-agent layer. |
| `GITHUB_TOKEN` | `app.py`, `repo_harvester.py`, `bounty_gateway.py`, `github_app.py` | Not an LLM key. Required for repo cloning, PR creation, GitHub Security Advisory submission. Scopes needed: `repo`, `security_events`. |
| Optional bounty/intel keys | Various | `HACKERONE_API_KEY`, `HACKERONE_USERNAME`, `BUGCROWD_API_KEY`, `NVD_API_KEY`, `BRAVE_API_KEY`, `SEMGREP_APP_TOKEN`, `NUCLEI_API_KEY`, `SHODAN_API_KEY`, `URLSCAN_API_KEY`. Each unlocks one specific data source; all degrade silently when missing. |

### Does one key act as the brain for every detachable component?

**Yes — `OPENROUTER_API_KEY` is the universal brain key.** Confirmed from the source:

- `entrypoint.sh` will start the OpenRouter OpenClaude daemon on `:50052` whenever `OPENROUTER_API_KEY` is present, and skip the DigitalOcean daemon on `:50051` when `DO_INFERENCE_API_KEY` is absent (the script literally logs `"skipping ${label} daemon — no API key"`).
- `hermes_orchestrator.py` builds its provider list dynamically: it appends DigitalOcean only if `DO_INFERENCE_API_KEY` is set, and OpenRouter only if `OPENROUTER_API_KEY` is set. With only OpenRouter present, it routes everything to OpenRouter.
- `adversarial_reviewer.py` reads only `OPENROUTER_API_KEY` and runs three models concurrently against the OpenRouter API.
- `mythos/agents/base.py` reads only `OPENROUTER_API_KEY` for the multi-agent orchestrator.

So the practical rule is:

| Keys you provide | What works |
|---|---|
| `OPENROUTER_API_KEY` only | Everything LLM-driven works. The system runs at full feature coverage on the slower (free-tier) lane. |
| `DO_INFERENCE_API_KEY` only | The OpenClaude DO daemon and Hermes (DO path) work. The 3-model adversarial reviewer and Mythos agents do **not** activate because they hard-read `OPENROUTER_API_KEY`. |
| Both | Optimal. DO is the fast paid lane; OpenRouter is the redundancy lane and the brain for the consensus / Mythos modules. |
| Neither | The container still boots, the UI still renders, but every LLM-bound action will fail-fast with a clear error. The static gates (Bandit, Semgrep, pip-audit, Z3) still work because they are purely local. |

### How a single key becomes "many brains"

Each agent — OpenClaude DO daemon, OpenClaude OR daemon, Hermes, the three Adversarial Reviewer voters, every Mythos agent (`Planner`, `Explorer`, `Executor`, `Orchestrator`) — opens its **own outbound HTTP/gRPC connection** using the same key. The key is not consumed; it is presented per request. So one OpenRouter key behaves exactly like a credit card: every component charges against it independently and concurrently. There is no shared "session" or token pool — only a shared rate-limit budget on the OpenRouter side.

### Provider routing flag (advanced)

`HERMES_PROVIDER` controls how Hermes reaches an LLM. Allowed values, taken from `hermes_orchestrator.py`:

- `auto` — try DigitalOcean REST, then OpenRouter REST.
- `openclaude_grpc` — route through `openclaude_grpc.client` against the DO daemon on `:50051` (which itself fails over to OpenRouter inside the daemon process). Use this when you want every LLM call to be observable through the OpenClaude daemon's logs and cost-attribution.
- `do` — DigitalOcean REST only.
- `openrouter` — OpenRouter REST only.

---

## Part III — BOOTSTRAP SEQUENCE

`entrypoint.sh` is the canonical boot script. The order is **not** arbitrary; later steps assume earlier steps have bound their ports.

1. **`mkdir -p ${LOG_DIR}`** — defaults to `/tmp`. Every daemon writes its `*.log` and `*.pid` here.
2. **`start_camofox`** — first because Camoufox lazily downloads ~300 MB of Firefox engine on its first launch. Binds `127.0.0.1:9377` (override with `CAMOFOX_HOST` / `CAMOFOX_PORT`). Logs to `camofox.log`. Skipped if `/opt/camofox/node_modules/.../server.js` is missing.
3. **`start_daemon "do" 50051 …`** — OpenClaude headless gRPC daemon, DigitalOcean Inference provider, primary. Started only when a DO key is present. Logs to `openclaude-do.log`.
4. **`start_daemon "or" 50052 …`** — OpenClaude headless gRPC daemon, OpenRouter provider, fallback. Started only when `OPENROUTER_API_KEY` is present. Logs to `openclaude-or.log`.
5. **`sleep 2`** — settle window so the first healing call does not race the binder. The Python client (`openclaude_grpc.client`) also has its own `wait_ready()`.
6. **G0DM0D3 meta-learner daemon** — starts unless `META_LEARNER_ENABLED=0`. Runs `python -u meta_learner_daemon.py` in background; PID kept at `${LOG_DIR}/meta_learner.pid`; logs at `${LOG_DIR}/meta_learner.log`.
7. **`export OPENCLAW="${OPENCLAW:-1}"`** — defaults the OpenClaw gateway to ON. `app.py` will then auto-start the HTTP gateway on port 8765 (override with `OPENCLAW_HOST` / `OPENCLAW_PORT`).
8. **`exec python -u app.py`** — Gradio UI binds to `0.0.0.0:${PORT:-7860}`. This is the foreground process; the container lives or dies with it.

After step 8, three optional listeners may also come online depending on env:

- **Night Hunter** (`night_hunt_orchestrator.py`) starts in background if `NIGHT_HUNTER=1`.
- **Mythos productization API** (`mythos/api/fastapi_server.py`) starts on `:7862` if `MYTHOS_API=1`.
- **GitHub webhook listener** (separate webhook plane referenced in code) on `:7861`.

---

## Part IV — THE COMPONENTS

Every component in this section is described by **(a)** location in the tree, **(b)** what it does, **(c)** when it is invoked, **(d)** the env knobs that change its behaviour. Mechanism only — no source quoted.

### 4.1 Camofox-browser server
- **Location:** external — installed under `/opt/camofox/`. Python adapter is `camofox_client.py`. Documentation: `CAMOFOX_INTEGRATION.md`.
- **Role:** Anti-detection real-browser server. A patched Firefox fork (Camoufox) wrapped behind a small REST API on `127.0.0.1:9377`. Fingerprint spoofing is patched at the C++ level.
- **Used by:** `cve_intel.py` (NVD / vendor pages), `repo_harvester.py` (GitHub HTML), `knowledge_rag.py` (JS-rendered docs), `red_team_fuzzer.py` (live recon), `bounty_gateway.py` (UI fallback), `embodied_os.py` (`mission bounty` page scraping), `meta_learner_daemon.py` (Phase 2 stochastic crawl).
- **Sessions:** isolated per `userId`. Cookies persisted under `CAMOFOX_PROFILE_DIR` (default `/data/camofox/profiles`). Netscape cookie files dropped into `CAMOFOX_COOKIES_DIR` are auto-imported.
- **Optional residential proxy:** `PROXY_HOST`, `PROXY_PORT`, `PROXY_USERNAME`, `PROXY_PASSWORD`. Camoufox auto-aligns locale and timezone to proxy GeoIP.
- **Failure mode:** the client raises `CamofoxUnavailable` and every caller falls back to plain `requests`.

### 4.2 OpenClaude — vendored coding-agent daemons
- **Location:** `vendor/openclaude/` (the upstream open-source project — this is the open-source equivalent of Anthropic's Claude Code, kept verbatim). Python gRPC client is `openclaude_grpc/client.py`. The two daemons are launched by `entrypoint.sh`.
- **Role:** Two long-lived headless gRPC daemons, one per LLM provider. Each accepts a prompt + tool list and streams back a transcript over a bidirectional gRPC stream.
- **Where they bind:** DO daemon on `:50051`, OpenRouter daemon on `:50052`. Hosts and timeouts: `OPENCLAUDE_GRPC_HOST`, `OPENCLAUDE_GRPC_PORT_DO`, `OPENCLAUDE_GRPC_PORT_OR`, `OPENCLAUDE_TIMEOUT` (default 600 s).
- **Behaviour:** auto-approve any "action required" prompt (`OPENCLAUDE_AUTO_APPROVE=1`) so headless mode never deadlocks. Per-call timeout matches the legacy aider invocation contract.
- **Used by:** Hermes (when `HERMES_PROVIDER=openclaude_grpc`), OSS Guardian (fix-mode patch generation), every legacy aider call site that previously shelled out to a subprocess. The Python client returns an `OpenClaudeResult` whose `.as_legacy_tuple()` method preserves the old `(combined_output, exit_code)` shape so downstream validators work unchanged.

### 4.3 Hermes orchestrator
- **Location:** `hermes_orchestrator.py`.
- **Role:** The autonomous security-research loop. Coordinates phases **RECON → STATIC → DYNAMIC → EXPLOIT → CONSENSUS → DISCLOSURE** by issuing tool calls to MCP servers and the analysis engines.
- **Sessions:** each session is persisted as JSON to `HERMES_SESSION_DIR` (default `/data/hermes`) after every phase, so a crash never loses the trail.
- **Logging:** bounded ring buffer of `HERMES_LOG_CAP` lines (default 10 000) — `get_hermes_logs()` returns the tail to the UI.
- **Public entry points:** `run_hermes_research(target_repo, repo_dir=…, focus_area=…, max_iterations=…, progress_callback=…)`, `get_session_summary(session)`.
- **Custom algorithms** (defined in this module): VES, TVG, ACTS, CAD, SSEC.

### 4.4 OSS Guardian
- **Location:** `oss_guardian.py`.
- **Role:** End-to-end OSS zero-day pipeline. Glues `repo_harvester` → `oss_target_scorer` → `architect.sandbox` → `language_runtime` → `hermes_orchestrator` → `disclosure_vault` → `embodied_bridge`.
- **Behaviour of `OSSGuardian().run(repo_url)`:** opens a sandbox, detects the runtime, runs the project's own tests. If failures exist → enters **fix mode** and returns a PR URL. If tests pass → enters **attack mode** and runs Hermes. Findings are routed by `_route_disclosure(...)`: `acts_score < 0.80` or severity below P2 are skipped; existing CVEs go to GitHub PR; novel zero-days go to the disclosure vault.
- **Modes:** `--attack-only` and `--fix-only` flags expose the two halves separately.

### 4.5 Repo Harvester
- **Location:** `repo_harvester.py`.
- **Role:** Continuous public-GitHub scanner that produces a ranked feed of (repo, failing-test-hint) pairs for the autonomous loop to consume. Filters by `last commit < 30 days`, presence of test files, star count.
- **Activation:** `RHODAWK_HARVESTER_ENABLED=true`. Poll interval `RHODAWK_HARVESTER_POLL_SECONDS` (default 6 h). Star floor `RHODAWK_HARVESTER_MIN_STARS` (default 100). Cap `RHODAWK_HARVESTER_MAX_REPOS` (default 20). State file `RHODAWK_HARVESTER_STATE` (default `/data/harvester_feed.json`).

### 4.6 Night Hunt Orchestrator
- **Location:** `night_hunt_orchestrator.py`.
- **Role:** Scheduled overnight bug-bounty hunting loop. Stages: **SCOPE INGEST → TARGET SELECT → RECON → HUNT → VALIDATE → REPORT.**
- **Reports:** persisted to `NIGHT_HUNTER_REPORTS` (default `/data/night_reports`).
- **Default platforms:** `hackerone,bugcrowd,intigriti` (override with `NIGHT_HUNTER_PLATFORMS`).
- **Schedule:** start hour `NIGHT_HUNTER_HOUR` (default 23), morning report `NIGHT_HUNTER_MORNING_HOUR` (default 6).
- **Hard rule built into the module:** does not auto-submit during the first 50 cycles — the operator must approve every finding via the Gradio Night Hunter tab or the OpenClaw `approve_finding` skill.
- **Pause / resume:** controlled by the env flag `NIGHT_HUNTER_PAUSED` (set/cleared by OpenClaw intents `pause_night` / `resume_night`).

### 4.7 Mythos multi-agent layer
- **Location:** `mythos/`. Plan: `mythos/MYTHOS_PLAN.md`. Agents: `mythos/agents/{planner,explorer,executor,orchestrator}.py`. Static / dynamic / exploit tooling: `mythos/static/`, `mythos/dynamic/`, `mythos/exploit/`. New MCP servers: `mythos/mcp/`. Productization API: `mythos/api/fastapi_server.py`.
- **Activation:** `RHODAWK_MYTHOS=1` for the multi-agent loop. `MYTHOS_API=1` to bring up the FastAPI plane (default port 7862, override with `MYTHOS_API_PORT`).
- **Models:** `MYTHOS_TIER1_PRIMARY` (default `deepseek/deepseek-v2-chat`), `MYTHOS_TIER2_PRIMARY` (default `qwen/qwen-2.5-coder-72b-instruct`). All routed through OpenRouter.
- **Auth on the API:** `MYTHOS_API_KEYS` (comma-separated bearer tokens) and optional JWT via `MYTHOS_JWT_PUBKEY`.

### 4.8 Adversarial Reviewer (3-model consensus)
- **Location:** `adversarial_reviewer.py`.
- **Role:** Runs three LLMs concurrently against a candidate diff and requires a 2/3 majority before approving. Rate-limit waits are 20 s. Threshold tunable with `RHODAWK_CONSENSUS_THRESHOLD` (default 0.67).
- **Models:** primary `RHODAWK_ADVERSARY_MODEL` (default `deepseek/deepseek-r1:free`), secondary `meta-llama/llama-3.3-70b-instruct:free`, tertiary `google/gemma-3-27b-it:free`.
- **Output:** `verdict ∈ {APPROVE, REJECT, CONDITIONAL}` plus a confidence score and a consensus fraction — the Conviction Engine reads these.

### 4.9 Conviction Engine (auto-merge gate)
- **Location:** `conviction_engine.py`.
- **Role:** Decides whether an LLM-generated PR can be merged without a human. **Disabled by default.** Enable with `RHODAWK_AUTO_MERGE=true`.
- **All seven criteria must pass:**
  1. Adversarial confidence ≥ `RHODAWK_CONVICTION_CONFIDENCE` (default 0.92).
  2. Adversarial verdict is `APPROVE` (no `CONDITIONAL`).
  3. Consensus fraction ≥ `RHODAWK_CONVICTION_CONSENSUS` (default 0.85).
  4. A semantically identical past fix exists in the memory engine with similarity ≥ `RHODAWK_CONVICTION_MEMORY_SIM` (default 0.85).
  5. Tests passed on the first attempt.
  6. SAST informational findings on the diff = 0.
  7. No new packages introduced by the diff.

### 4.10 The security gates and analysis engines
Each of these runs as a stage of the pipeline OR as an MCP-callable tool, depending on the caller. None of them require an LLM.
- `sast_gate.py` — Bandit + 16-pattern secret scanner.
- `supply_chain.py` — pip-audit + typosquatting detection (PyPI confusion).
- `formal_verifier.py` — Z3 SMT solver, integer-overflow + invariant proofs.
- `symbolic_engine.py` — angr symbolic execution.
- `taint_analyzer.py` — dataflow analysis, source → sink.
- `fuzzing_engine.py` — Hypothesis property-based tests; atheris is documented as removed (libFuzzer unavailable on HuggingFace Space images).
- `red_team_fuzzer.py` — CEGIS-style attack loop.
- `cve_intel.py` — NVD + SSEC algorithm. Uses Camofox or `requests`.
- `paper2code_engine.py` — converts academic exploit papers to executable harnesses.
- `exploit_primitives.py` — primitive classification (overflow / UAF / race / injection).
- `language_runtime.py` — language fingerprinting + runner selection (Python, JS, TS, Java, Go, Rust, Ruby).

### 4.11 Memory and learning
- `embedding_memory.py` — vector store. SQLite-vec by default; Qdrant client also available.
- `knowledge_rag.py` — retrieval over indexed docs and prior fixes.
- `semantic_extractor.py` — code → semantic features.
- `lora_scheduler.py` — exports a JSONL fine-tune dataset once 50+ verified fixes accumulate. Activate with `RHODAWK_LORA_ENABLED=true`.
- `meta_learner_daemon.py` — see 4.20.

### 4.12 Audit logger
- **Location:** `audit_logger.py`. Path: `/data/audit_trail.jsonl`.
- **Role:** Every AI action is appended as a JSON line whose `entry_hash` (SHA-256) chains back to the previous line — a tamper-evident chain. Genesis sentinel is the literal string `"GENESIS"`. Required for SOC 2 / ISO 27001 posture.
- **Concurrency:** single global write lock; no concurrent writers can split the chain.

### 4.13 Disclosure vault
- **Location:** `disclosure_vault.py`. SQLite at `RHODAWK_VAULT_DB` (default `/data/disclosure_vault.sqlite`); dossier blobs at `RHODAWK_VAULT_DIR` (default `/data/vault`).
- **Role:** Holds every finding with status `DRAFT → HUMAN_APPROVED → DISCLOSED`. Tracks 90-day responsible-disclosure deadline (`RHODAWK_DISCLOSURE_DAYS`, default 90).
- **Hard policy** (verbatim from the module docstring):
  1. Every finding starts as DRAFT — nothing leaves the box.
  2. A human reads the dossier and clicks Approve.
  3. After approval the system generates the disclosure message; the operator sends it through the maintainer's own security channel.
  4. The 90-day clock starts.
  5. Bug-bounty submissions are *prepared* for human submission — never automated.
  6. No GitHub API writes in AVR (autonomous-vulnerability-research) mode.

### 4.14 Bounty gateway
- **Location:** `bounty_gateway.py`. SQLite at `RHODAWK_DISCLOSURE_DB` (default `/data/disclosure_pipeline.db`).
- **Role:** Submits approved findings to HackerOne, Bugcrowd, GitHub Security Advisories, or via direct maintainer email.
- **Hard rule:** `PENDING_HUMAN_APPROVAL` is the only entry state. The approval gate is enforced at the API call level, not just the UI level. Statuses are listed as a `DisclosureStatus` enum: `PENDING_HUMAN_APPROVAL, HUMAN_APPROVED, HUMAN_REJECTED, SUBMITTED_HACKERONE, SUBMITTED_BUGCROWD, SUBMITTED_GITHUB_GHSA, SUBMITTED_DIRECT, DUPLICATE, NOT_A_BUG, FIXED_BY_VENDOR.`

### 4.15 Job queue
- **Location:** `job_queue.py`. Single SQLite DB at `JOB_QUEUE_DB` (default `/data/jobs.sqlite`). Legacy JSON files in `/data/jobs/` are auto-imported on first start.
- **States:** `PENDING, RUNNING, SAST_BLOCKED, DONE, FAILED.`

### 4.16 OpenClaw gateway (HTTP + Telegram)
- **Location:** `openclaw_gateway.py`. Schedule file: `openclaw_schedule.yaml`.
- **Role:** Natural-language command bus. Parses an English sentence into an intent and dispatches to the right subsystem. Returns a uniform `{ok, intent, reply, data}` envelope.
- **Endpoints:** `POST /openclaw/command`, `POST /telegram/webhook`, `GET /openclaw/status`. Listens on port 8765 by default (`OPENCLAW_HOST`, `OPENCLAW_PORT`).
- **Built-in intents:** `scan_repo`, `night_run_now`, `pause_night`, `resume_night`, `status`, `approve_finding`, `reject_finding`, `explain_finding`, `help`.
- **Telegram credentials:** `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`. Optional shared secret on the HTTP path: `OPENCLAW_SHARED_SECRET`.
- **Auto-start in app.py:** gated on env `OPENCLAW=1`. The `entrypoint.sh` defaults this to `1`.

### 4.17 EmbodiedOS
- **Location:** `embodied_os.py`. UI: `embodied_os_ui.py`.
- **Role:** The unified front-of-house brain. `EmbodiedOS.dispatch(text, user=…)` is the single public entry point. Resolution order: new mission verbs first, then fall through to `openclaw_gateway.handle_command(...)` so every existing OpenClaw intent still works untouched.
- **New mission verbs** (registered with `openclaw_gateway.register(...)` at import time so HTTP and Telegram gain them automatically):
  - `mission repo <github-url>` — runs OSSGuardian, then an adversarial mutation pass via Hermes (`focus_area="adversarial-mutation:harden …"`), then a zero-day deep pass (`max_iterations` from `EMBODIED_ZERODAY_ITER`, default 20). Mutation pass iterations from `EMBODIED_MUTATION_ITER` (default 8).
  - `mission bounty <hackerone-or-bugcrowd-url>` — fetches the program page (Camofox first, plain `requests` fallback), regex-extracts in-scope GitHub repos and domains, queues `mission repo` per slug, renders a PhD-level Markdown report (sections: Extracted Scope, Per-Target Audit Results, Submission-Ready Findings) and writes it to `EMBODIED_MISSIONS_DIR/<mission-id>-report.md`.
  - `mission status <id>` — live transcript of any mission, in-memory or rehydrated from disk.
  - `mission list` — recent missions.
  - `mission brief` — heartbeat: schedule excerpt, job queue snapshot, skill counts, recent missions, meta-learner log tail, night-hunt paused flag.
- **Mission persistence:** `EMBODIED_MISSIONS_DIR` (default `/tmp/embodied_missions`). Each mission is a JSON file `<mission-id>.json` updated after every log line.
- **Severity floor for "submission-ready":** `{P1, P2, CRITICAL, HIGH}`.

### 4.18 EmbodiedOS UI
- **Location:** `embodied_os_ui.py`. Mounted by `app.py` inside the existing `gr.Tabs()` block (last tab, wrapped in try/except so a render failure leaves all other tabs intact).
- **Layout:** chatbot panel on the left, recent-missions JSON + transcript loader on the right. Quick-command examples: `mission brief`, `mission repo …`, `mission bounty …`, `mission list`, `scan …`, `status`, `help`.

### 4.19 The Gradio control plane
- **Location:** `app.py`.
- **Tabs (in order):** Live Operations, Job queue + Audit log + Chain integrity, Webhook log, Red team, SWE-bench, Mythos, Hermes Zero-Day (with sub-tabs: Launch / Live Logs / Session Summary / Disclosure Pipeline / CWE Reference), and 🧬 EmbodiedOS.
- **Auto-refresh:** a single `gr.Timer(3)` tick drives all live panels via `get_combined_refresh()` — one connection instead of three to avoid SSE connection-limit freezes.
- **Port:** `PORT` (default 7860).

### 4.20 G0DM0D3 meta-learner daemon
- **Location:** `meta_learner_daemon.py`.
- **Role:** Self-bootstrapping meta-learning loop. Runs in parallel to `app.py`. Each cycle: (1) ensures the runtime MCP config exists and exposes both `filesystem-research` and `camofox-browser`; (2) starts a fresh Hermes session; (3) injects the Apex Evolution Directive as the focus area (Phase 1 Self-Awareness → Phase 2 Stochastic Gap Discovery → Phase 3 Assimilation → Phase 4 Brain Expansion, where the agent writes a `.md` skill file into `architect/skills/`); (4) sleeps a uniformly random 4–12 hours.
- **Activation:** on by default. Disable with `META_LEARNER_ENABLED=0`. Iteration cap per cycle: `META_LEARNER_MAX_ITER` (default 40). Default target repo when none is supplied: `RHODAWK_REPO` (defaults to `Rhodawk-AI/Rhodawk-devops-engine`).
- **Imports the orchestrator lazily inside the loop** so a transient ImportError in one cycle cannot kill the daemon.

### 4.21 Notifier
- **Location:** `notifier.py`.
- **Role:** Sends Telegram + Slack notifications. Reads `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, `SLACK_WEBHOOK_URL`.

### 4.22 The MCP server suite
- **Config files:** `mcp_config.ARCHIVE.json` (historical), runtime config written to `MCP_RUNTIME_CONFIG` (default `/tmp/mcp_runtime.json`) by `app.py.write_mcp_config()`.
- **Servers exposed:** the README lists 25 — including `fetch-docs`, `github-manager`, `filesystem-research`, `memory-store`, `sequential-thinking`, `web-search` (Brave), `git-forensics`, `postgres-intelligence`, `sqlite-findings`, `nuclei-scanner`, `semgrep-sast`, `trufflehog-secrets`, `bandit-sast`, `pip-audit-sca`, `osv-scanner`, `z3-formal-verifier`, `hypothesis-fuzzer`, `atheris-fuzzer`, `angr-symbolic`, `radon-complexity`, `ruff-linter`, `aider-patcher`, `cve-intelligence`, `bounty-platform`, `supply-chain-monitor`. Hermes and the Mythos agents call them through the OpenClaude daemons' MCP plumbing.

### 4.23 Architect plane
- **Location:** `architect/` directory — sandbox runtime, skill packs, skill selector, Godmode consensus, Parseltongue, Nightmode scheduling.
- **Knobs read by app.py:** `ARCHITECT_NIGHTMODE`, `ARCHITECT_NIGHTMODE_HOUR` (default 18), `ARCHITECT_ACTS_GATE` (default 0.72).
- **Skills directory:** `architect/skills/` — written to by the meta-learner during Phase 4 brain expansion.

---

## Part V — OPERATOR INTERFACES

| Interface | Where | What it accepts |
|---|---|---|
| Gradio UI | `http://<host>:7860` | Click-driven, every tab. The 🧬 EmbodiedOS tab is the recommended primary surface. |
| OpenClaw HTTP | `POST http://<host>:8765/openclaw/command` body `{"text": "..."}` | Any English command supported by `EmbodiedOS.dispatch` (mission verbs + every legacy OpenClaw intent). |
| OpenClaw status | `GET http://<host>:8765/openclaw/status` | Liveness JSON. |
| Telegram | `POST /telegram/webhook` | Forwarded to `handle_command(msg, user="telegram:<chat>")`. |
| Mythos productization API | `http://<host>:7862/v1/analyze_target` | Only if `MYTHOS_API=1`. |
| GitHub webhook listener | `:7861` | Triggered by repository pushes / check runs. |

---

## Part VI — MISSION FLOWS

### 6.1 `mission repo <github-url>`
Phase A (delegation) → `OSSGuardian().run(url)` clones, detects runtime, runs tests, branches to fix-mode (3-iteration Hermes) or attack-mode (full Hermes) depending on test state. Phase B (only if tests already passed) → adversarial mutation pass with `EMBODIED_MUTATION_ITER` iterations, focus `adversarial-mutation:harden — mutate the existing test suite to break it, then re-fix the production code so every mutated assertion still passes`. Phase C → zero-day deep pass with `EMBODIED_ZERODAY_ITER` iterations (default 20), focus `zero-day:exhaustive — RCE, deserialisation, prototype pollution, SSRF, supply-chain`. Findings flow into the disclosure vault. The mission JSON is persisted in `EMBODIED_MISSIONS_DIR` after every log line.

### 6.2 `mission bounty <bounty-url>`
Fetch the program page via `_fetch_bounty_page(...)` (Camofox client first; plain `requests` second). Extract scope: GitHub repos via a strict regex on `https?://github.com/owner/name`, domains via a conservative TLD regex with a static deny-list of CDN / static-asset / aggregator hosts. Caps: 25 repos, 50 domains. Run `_run_mission_repo(...)` against each in-scope slug **in-thread** so the bounty mission emits one consolidated report. Render the PhD-grade Markdown via `_phd_bounty_report(...)` and write to `EMBODIED_MISSIONS_DIR/<mission-id>-report.md`. Severity floor for the "Submission-Ready" section: `P1, P2, CRITICAL, HIGH`.

### 6.3 `scan <repo-url>` (legacy OpenClaw intent — still works)
Pure delegation to `OSSGuardian().run(...)`. No mutation pass, no extra zero-day pass. Use this when you want exactly the original OSSGuardian behaviour without the EmbodiedOS overlay.

### 6.4 Night Hunt cycle
Triggered by schedule (`openclaw_schedule.yaml`: `night_hunt_start` cron `0 23 * * *`) or by the `night_run_now` intent. Runs SCOPE INGEST → TARGET SELECT → RECON → HUNT → VALIDATE → REPORT and writes the cycle report to `NIGHT_HUNTER_REPORTS`. Pause anytime with `pause_night`; resume with `resume_night`.

### 6.5 Repair flow (the system's original purpose)
Clone & fingerprint → if tests fail: retrieve similar fixes (vector memory) → dispatch OpenClaude to generate a patch → re-run tests → SAST gate → supply-chain gate → Z3 formal verification → 3-model adversarial consensus (2/3 majority required) → conviction engine (only if `RHODAWK_AUTO_MERGE=true`) → open PR + audit-trail entry → training store → optional LoRA export.

---

## Part VII — DATA AT REST

| Path | Contents | Owner module |
|---|---|---|
| `/data/audit_trail.jsonl` | Tamper-evident chain of every AI action | `audit_logger.py` |
| `/data/disclosure_vault.sqlite` + `/data/vault/` | Findings + dossiers | `disclosure_vault.py` |
| `/data/disclosure_pipeline.db` | Bounty-submission lifecycle | `bounty_gateway.py` |
| `/data/jobs.sqlite` | Job queue | `job_queue.py` |
| `/data/hermes/<session-id>.json` | Hermes session snapshots | `hermes_orchestrator.py` |
| `/data/night_reports/*.json` | Night-hunt cycle reports | `night_hunt_orchestrator.py` |
| `/data/harvester_feed.json` | Repo-harvester ranked feed | `repo_harvester.py` |
| `/data/camofox/profiles/` + `/data/camofox/cookies/` | Per-user browser state | Camofox server |
| `/tmp/embodied_missions/<id>.json` + `…-report.md` | EmbodiedOS mission state + final reports | `embodied_os.py` |
| `/tmp/mcp_runtime.json` | Runtime MCP server config used by OpenClaude daemons | `app.py.write_mcp_config()` |
| `/tmp/meta_learner.log` + `/tmp/meta_learner.pid` | Meta-learner daemon | `meta_learner_daemon.py` |
| `/tmp/openclaude-do.log` + `…-or.log` | Coding-agent daemon logs | `entrypoint.sh` |
| `/tmp/camofox.log` | Browser server log | `entrypoint.sh` |
| `architect/skills/*.md` | Skill packs (read by orchestrator, written by meta-learner) | `architect/` + meta-learner Phase 4 |

If you mount `/data` as a Docker volume, you preserve every finding, every audit chain entry, every job, every browser cookie across container restarts. If you do not, the vault and chain restart from genesis on every boot.

---

## Part VIII — RULES, LIMITS, AND HARD GATES (THE LAWS)

These are not suggestions. They are encoded in the codebase and the system's safety posture depends on them. Do not weaken them.

1. **Every externally-visible action requires human approval.** Disclosure, bounty submission, GHSA creation, and PR auto-merge are all gated. The gates are enforced at the API call level in `bounty_gateway.py` and `disclosure_vault.py`, not just in the UI. Removing the UI button does not remove the gate.
2. **The 90-day disclosure clock starts on Approve, not on discovery.** `RHODAWK_DISCLOSURE_DAYS=90`. Do not shorten it without explicit policy reason.
3. **Auto-merge requires all seven Conviction criteria** AND the master switch `RHODAWK_AUTO_MERGE=true`. Default is OFF.
4. **The 3-model adversarial reviewer requires a 2/3 majority.** Threshold: `RHODAWK_CONSENSUS_THRESHOLD=0.67`. Single-model approve never suffices.
5. **Night Hunter does not auto-submit during the first 50 cycles.** This is hard-coded calibration time.
6. **The OSS Guardian routing rule is non-negotiable:** any finding with `acts_score < 0.80` or severity below P2 is dropped, not held.
7. **The audit chain is append-only.** Every entry hashes the previous entry's `entry_hash`. Genesis sentinel is the literal string `"GENESIS"`. Do not edit the JSONL file by hand.
8. **MCP tool access is mediated.** No analysis engine should reach the public internet directly — it goes through the `fetch-docs` allowlist or through Camofox.
9. **OpenClaude daemons auto-approve action prompts** (`OPENCLAUDE_AUTO_APPROVE=1`) only because they run inside the trust boundary of the container. Do not expose port 50051 / 50052 externally.
10. **OpenClaw HTTP gateway listens on `0.0.0.0:8765` by default.** If the container is on a public network, bind it to `127.0.0.1` (`OPENCLAW_HOST=127.0.0.1`) or set `OPENCLAW_SHARED_SECRET`.
11. **Camofox honours residential-proxy GeoIP alignment.** Do not mix proxies and bare connections in the same `userId` session — fingerprint inconsistency is detectable.
12. **Mythos productization API requires bearer auth** (`MYTHOS_API_KEYS`) when exposed.

---

## Part IX — WHAT MUST NEVER BE DONE

The following actions either break the safety posture, corrupt persistent state, or violate the system's responsible-disclosure contract.

1. **Never set `RHODAWK_AUTO_MERGE=true` on a target you do not own.** Auto-merge bypasses human review of the actual diff content; it is intended for self-healing your own infrastructure.
2. **Never run `mission bounty` against a program you have not registered for.** The system will gladly enumerate any URL you give it; the bounty platform will not reward you for findings on programs you are not on.
3. **Never delete `/data/audit_trail.jsonl`.** The chain is the legal record. Rotate it via append-only archival; do not truncate.
4. **Never publish the `/data/vault/` directory.** Dossiers may contain pre-disclosure proofs of concept that vendors have not yet patched.
5. **Never expose ports 50051 / 50052 / 9377 to the public internet.** They have no auth — they trust the loopback boundary.
6. **Never bypass `disclosure_vault` to submit directly to a bounty platform.** The vault is the single source of truth for what is approved; bypassing it invalidates the chain of custody.
7. **Never check API keys, tokens, or `.env` files into the repo.** All keys are read from environment only.
8. **Never edit `architect/skills/*.md` while the meta-learner daemon is running.** It writes new skill files between cycles; concurrent edits race.
9. **Never remove the `try/except` wrapping the EmbodiedOS tab mount in `app.py`** — a render failure there would otherwise crash the entire UI.
10. **Never disable `OPENCLAUDE_AUTO_APPROVE`** unless you intend to attach a human to every tool prompt the daemon emits — headless mode will deadlock.
11. **Never run two containers against the same `/data` volume.** SQLite vault, audit chain, and job queue use single-writer locking that assumes one process.
12. **Never feed `mission repo` a private repo without first ensuring `GITHUB_TOKEN` has read access** — the clone will fail noisily and the mission status will read `error`.
13. **Never set `META_LEARNER_ENABLED=1` on a system without LLM keys** — the daemon will burn cycles failing every Hermes call. Either set keys or set `META_LEARNER_ENABLED=0`.
14. **Never lower `RHODAWK_CONSENSUS_THRESHOLD` below 0.67.** That is the mathematical floor for "majority of three."
15. **Never disclose a finding before its 90-day deadline elapses or the vendor signs a coordinated disclosure agreement.** This is the policy the disclosure_vault module enforces and the policy the operator must respect outside the UI.

---

## Part X — HOW TO SHUT IT DOWN SAFELY

The container is a foreground process driven by `app.py`. The graceful shutdown order is:

1. **Pause autonomous loops first.** Send `pause night` through any operator surface. This sets the env flag `NIGHT_HUNTER_PAUSED=1` and stops the next scheduled cycle.
2. **Drain the job queue.** Stop accepting new commands; wait for `JobStatus.RUNNING` rows in `/data/jobs.sqlite` to settle to `DONE` or `FAILED`. The Live Operations tab shows this.
3. **Wait for in-flight missions to finish.** `mission list` shows `running` missions; the EmbodiedOS UI shows live transcripts. Each mission is persisted to disk after every log line, so a hard kill loses only the in-memory tail, never the recorded trail.
4. **Stop the Gradio UI process.** Sending `SIGTERM` to the foreground `python -u app.py` triggers Gradio's own teardown.
5. **Stop the meta-learner.** `kill $(cat ${LOG_DIR}/meta_learner.pid)`. The daemon traps signals and exits cleanly.
6. **Stop the OpenClaude daemons.** `kill $(cat ${LOG_DIR}/openclaude-do.pid)` and `…-or.pid`.
7. **Stop Camofox.** `kill $(cat ${LOG_DIR}/camofox.pid)`. Its profiles and cookies persist on disk.
8. **Snapshot `/data/`.** This is the entire state of the system: vault, chain, queue, harvester feed, hermes sessions, night reports.
9. **Bring the container down.** `docker stop` or the orchestrator equivalent.

To **shut down emergency-fast** (e.g. you discovered an unintended disclosure path): `docker kill` the container. The audit chain is append-only and the disclosure vault is SQLite — both survive a hard kill. Then audit `/data/audit_trail.jsonl` from the last known-good `entry_hash`.

---

## Part XI — DEGRADATION MATRIX

What still works when a piece is missing.

| Removed / unavailable | What still works | What stops |
|---|---|---|
| Camofox server | All static analysis, all SAST/supply-chain gates, OpenClaude calls. `mission bounty` falls back to plain `requests`. | JS-rendered scraping, anti-detection fetches, authenticated browser flows. |
| OpenClaude DO daemon (no `DO_INFERENCE_API_KEY`) | Everything routes to OpenRouter. | DO fastpath + cost attribution through DO. |
| OpenClaude OR daemon (no `OPENROUTER_API_KEY`) | OpenClaude DO daemon, Hermes via DO. | Adversarial reviewer (3 models OpenRouter), Mythos agents, Hermes OpenRouter fallback. |
| Both LLM keys | Static gates (Bandit, Semgrep, pip-audit, Z3) still run; UI still renders. | Every LLM-driven mission, fix, attack, consensus, mythos run. |
| `GITHUB_TOKEN` | Hermes can still analyse local clones. | Cloning, PR creation, GHSA, repo harvester. |
| Telegram credentials | Gradio UI + OpenClaw HTTP still work. | Telegram channel only. |
| Meta-learner daemon (`META_LEARNER_ENABLED=0`) | Everything operator-driven. | Stochastic skill expansion. |
| Night Hunter (`NIGHT_HUNTER=0`) | Operator-driven and EmbodiedOS missions. | Scheduled overnight bounty cycles. |
| Mythos (`RHODAWK_MYTHOS=0`) | Default Hermes loop. | Multi-agent reasoning, productization API. |

---

## Part XII — LICENSING AND VENDORED CODE NOTE

`vendor/openclaude/` contains the upstream open-source OpenClaude project. **It is the open-source equivalent of Anthropic's Claude Code.** It is kept verbatim and consumed by Rhodawk only via two long-lived headless gRPC daemons (see 4.2). The integration is a thin Python adapter (`openclaude_grpc/client.py`) that mimics the old aider subprocess return shape so every legacy caller keeps working unchanged. Treat this directory as a third-party dependency: do not patch its internals; if you need different behaviour, set the env knobs `entrypoint.sh` exposes (`OPENAI_BASE_URL`, `OPENAI_MODEL`, `MCP_RUNTIME_CONFIG`, etc.) or wrap calls at the Python adapter layer.

The Camofox-browser server (under `/opt/camofox` at runtime) is similarly an external dependency; `camofox_client.py` is the only Rhodawk-owned surface. The Camoufox engine is downloaded lazily on first launch.

Mythos lives under `mythos/` and is part of this repository — see `mythos/MYTHOS_PLAN.md` for the multi-agent / RL / fine-tune roadmap.

---

## Closing — the scientist's note

This system was built around three convictions:

1. **Static gates without an autonomous brain are toys.** Bandit and Semgrep find what they were programmed to look for; Hermes finds what nobody programmed at all.
2. **An autonomous brain without gates is a liability.** That is why every disclosure path in this codebase passes through a human approval that is enforced at the API layer, not the UI.
3. **A unified front-of-house turns a toolkit into a product.** EmbodiedOS exists so an operator who has never read this playbook can still do useful, safe work by typing one English sentence.

If you keep those three convictions intact while you extend this system, you cannot break it. If you violate any of them, no amount of engineering downstream will save you.

Run it well.

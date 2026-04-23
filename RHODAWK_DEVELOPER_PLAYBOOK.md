# Rhodawk AI — Developer & Founder Playbook

*Companion document to* `Rhodawk_Superhuman_Agent_Plan.md`.
*Covers everything in the v6 codebase: architecture, build, run, extend, deploy.*

---

## Table of Contents

1. [What Rhodawk Is](#1-what-rhodawk-is)
2. [System Topology](#2-system-topology)
3. [Repository Map](#3-repository-map)
4. [Boot Sequence](#4-boot-sequence)
5. [Skill Architecture](#5-skill-architecture)
6. [Model Router (5-tier)](#6-model-router-5-tier)
7. [Hermes Reasoning Engine](#7-hermes-reasoning-engine)
8. [Mythos MCP Fleet (37 servers)](#8-mythos-mcp-fleet-37-servers)
9. [Night Hunter — autonomous bug-bounty loop](#9-night-hunter--autonomous-bug-bounty-loop)
10. [EmbodiedOS — OpenClaw + Telegram](#10-embodiedos--openclaw--telegram)
11. [OSS Guardian flow](#11-oss-guardian-flow)
12. [Safety gates & audit trail](#12-safety-gates--audit-trail)
13. [Local development](#13-local-development)
14. [Docker / HuggingFace Space deployment](#14-docker--huggingface-space-deployment)
15. [DigitalOcean migration](#15-digitalocean-migration)
16. [Configuration reference](#16-configuration-reference)
17. [Adding a new skill](#17-adding-a-new-skill)
18. [Adding a new MCP server](#18-adding-a-new-mcp-server)
19. [Testing & validation](#19-testing--validation)
20. [Troubleshooting](#20-troubleshooting)
21. [Founder operating handbook](#21-founder-operating-handbook)

---

## 1. What Rhodawk Is

Rhodawk is an autonomous security agent built around three loops:

* **OSS Guardian** — clones a public repository, runs the project's own
  test suite, then either (a) fixes failing tests via the Hermes reasoning
  loop or (b) launches a six-phase attack run with the Mythos MCP fleet,
  emitting findings as PRs and CVE drafts.
* **Night Hunter** — every night at 23:00 UTC, ingests bug-bounty scope
  from HackerOne / Bugcrowd / Intigriti, scores targets, runs the recon
  → scan → validate → report pipeline, and posts a 06:00 morning briefing.
* **EmbodiedOS** — natural-language interface (Telegram + HTTP gateway)
  built on OpenClaw skills. Ten command intents cover everything an
  operator does: scan, status, pause, approve, reject, explain.

All three loops share the Hermes orchestrator, the semantic skill
selector, the 5-tier model router, the 37-server MCP fleet, and the
training flywheel.

---

## 2. System Topology

```
                       ┌─────────────────────┐
                       │  YOU (Telegram/HTTP) │
                       └──────────┬───────────┘
                                  ▼
                  ┌─────────────────────────────┐
                  │  openclaw_gateway.py         │
                  │  • intent registry           │
                  │  • Telegram webhook          │
                  │  • POST /openclaw/command    │
                  └──────────┬───────────────────┘
            ┌────────────────┼─────────────────────┐
            ▼                ▼                     ▼
   ┌──────────────┐ ┌──────────────────┐ ┌──────────────────┐
   │ oss_guardian │ │ night_hunt_      │ │ status / mgmt    │
   │ .py          │ │ orchestrator.py  │ │ commands         │
   └──────┬───────┘ └────────┬─────────┘ └──────────────────┘
          │                  │
          └────────┬─────────┘
                   ▼
        ┌────────────────────────────┐
        │  hermes_orchestrator.py     │
        │  • 6-phase reasoning loop   │
        │  • call_with_skills()       │
        │  • _hermes_llm_call()       │
        └──────┬───────────┬──────────┘
               │           │
   ┌───────────▼──┐   ┌────▼─────────────────┐
   │ architect/   │   │ architect/           │
   │ model_router │   │ skill_selector.py    │
   │  (T1..T5)    │   │  (MiniLM semantic)   │
   └──────┬───────┘   └──────────┬───────────┘
          ▼                      ▼
   OpenRouter / vLLM        architect/skills/  (114 skill .md files)
                                  │
                                  ▼
                  ┌──────────────────────────────┐
                  │  mythos/mcp/  (37 servers)   │
                  │  static, dynamic, exploit,   │
                  │  jwt, cors, openapi, dep-    │
                  │  confusion, proto-pollution… │
                  └──────────────┬───────────────┘
                                 ▼
                  ┌──────────────────────────────┐
                  │  Safety gates                │
                  │  sast_gate / adversarial /   │
                  │  conviction / scope          │
                  └──────────────┬───────────────┘
                                 ▼
                  ┌──────────────────────────────┐
                  │  Output                      │
                  │  PRs / bounty drafts / CVEs  │
                  │  → embodied_bridge → ops     │
                  └──────────────────────────────┘
```

---

## 3. Repository Map

```
.
├── app.py                           gradio UI + boot orchestration
├── hermes_orchestrator.py           6-phase reasoning loop
├── oss_guardian.py                  OSS attack/fix campaigner
├── night_hunt_orchestrator.py  ★    autonomous bounty hunter (NEW v6)
├── openclaw_gateway.py         ★    Telegram + HTTP intent gateway (NEW v6)
├── openclaw_schedule.yaml      ★    heartbeat schedule (NEW v6)
├── mcp_config.json                  37 MCP servers (12 added in v6)
├── Dockerfile                       HF Space build (PyPI mcp-server-* fix)
│
├── architect/
│   ├── model_router.py              5-tier model routing + budget
│   ├── skill_registry.py            keyword scoring (legacy)
│   ├── skill_selector.py       ★    MiniLM semantic selector (NEW v6)
│   ├── nightmode.py                 v5 stub (kept for backwards compat)
│   ├── embodied_bridge.py           Telegram/Discord/OpenClaw emit
│   ├── godmode_consensus.py         3-model adversarial review
│   ├── master_redteam_prompt.py     prompt templating
│   └── skills/                      114 skill markdown files
│       ├── web/  binary/  languages/  cryptography/
│       ├── infrastructure/  ai-systems/  protocols/
│       ├── embedded-iot/  automotive/  aviation/
│       ├── mobile/  reverse-engineering/
│       └── report-quality/  + platform-specific-guides/
│
├── mythos/mcp/                      Python MCP servers
│   ├── reconnaissance_mcp.py        existing
│   ├── static_analysis_mcp.py       existing (CodeQL/Semgrep/Joern)
│   ├── dynamic_analysis_mcp.py      existing (AFL++/KLEE/Frida)
│   ├── exploit_generation_mcp.py    existing (pwntools/ROP)
│   ├── web_security_mcp.py          existing (ZAP/nuclei/sqlmap)
│   ├── jwt_analyzer_mcp.py     ★    NEW v6
│   ├── cors_analyzer_mcp.py    ★    NEW v6
│   ├── openapi_analyzer_mcp.py ★    NEW v6
│   ├── dep_confusion_mcp.py    ★    NEW v6
│   ├── prototype_pollution_mcp.py ★ NEW v6
│   ├── skill_selector_mcp.py   ★    NEW v6
│   └── …
│
├── skills/rhodawk/             ★    7 OpenClaw interaction skills (NEW v6)
│   ├── scan-repo.md   night-report.md   approve-finding.md
│   ├── pause-hunting.md   add-target.md   status.md   explain-finding.md
│
├── tests/                           pytest suite
└── vendor/openclaude/               vendored OpenClaude (gRPC daemon)
```

`★` = added or rewritten in v6 to fulfil the Masterplan §3, §5, §6, §8.

---

## 4. Boot Sequence

`app.py` → `if __name__ == "__main__"`:

1. `start_webhook_server()` — GitHub-app webhooks (HMAC verified).
2. `_start_mythos_api_server_thread()` — productisation API (opt-in).
3. `architect.nightmode.start_in_background()` — legacy v5 night-mode (no-op
   unless `ARCHITECT_NIGHTMODE=1`).
4. **(NEW)** `night_hunt_orchestrator.start_in_background()` —
   v6 hunter when `NIGHT_HUNTER=1`.
5. **(NEW)** `openclaw_gateway.start_in_background()` —
   Flask gateway on `OPENCLAW_PORT` (default 8765) when `OPENCLAW=1`.
6. `demo.launch(...)` — Gradio dashboard on `PORT` (HF default 7860).

Container entrypoint (`entrypoint.sh`) writes `/tmp/mcp_runtime.json`
from `mcp_config.json` + secret env vars before starting the Python
process — keeping secrets out of the committed config.

---

## 5. Skill Architecture

The core insight (Masterplan §1.2 / §5): **a $0.07/M-token model becomes
a domain expert when the right skill briefing is loaded into its
context**. The selector is what turns the model from a generalist into a
JWT specialist or a Solidity auditor for the duration of one task.

### 5.1 Skill file format

```yaml
---
name: jwt-analyzer
domain: web
triggers:
  languages: [python, javascript, java]
severity_focus: [P1, P2]
tools: [pyjwt, jwt-cli]
---

# jwt-analyzer

Free-form markdown the model can read…
```

`architect/skill_registry.py` parses the YAML front-matter, exposes
`Skill` objects with structured triggers, and provides a keyword `match()`
scorer used as the deterministic fallback.

### 5.2 Semantic selection (`architect/skill_selector.py`)

1. Load every `*.md` from `architect/skills/` and `/data/skills/`.
2. Embed each one with `sentence-transformers/all-MiniLM-L6-v2` (cached
   on disk under `/tmp/architect_skill_cache/skills_<model>.json`).
3. Embed the task description + repo languages + tech stack + attack phase.
4. Cosine-rank, apply phase boosts (e.g. `recon` boosts skills whose name
   contains `subdomain`, `wayback`, `httpx`).
5. Return either:
   * `pack(...)` → list of `Match` objects (for custom rendering)
   * `select_for_task(...)` → ready-to-prepend `<skills>...</skills>` block

**The module never raises in production**: if `sentence-transformers`
isn't installed, it falls back to keyword overlap scoring without
changing the public interface.

### 5.3 Wiring

`hermes_orchestrator.run_hermes_research` calls `select_for_task` once
per session and prepends the skill block to the Hermes system prompt.
`architect.model_router.call_with_skills` does the same for ad-hoc
LLM calls (used by the OSS Guardian fix loop and report drafting).

---

## 6. Model Router (5-tier)

`architect/model_router.py` — every LLM call goes through this:

| Tier | Default model | Cost / M out | Use |
|------|---------------|-------------:|-----|
| T1-fast | `minimax/minimax-m2.5-highspeed` | $0.10 | recon, triage, bulk |
| T1-deep | `deepseek/deepseek-chat-v3` | $0.28 | static analysis, patches |
| T2 | `qwen/qwen3-235b-a22b` | $0.60 | exploit reasoning, chains |
| T3 | `minimax/minimax-m2.5` | $0.55 | long-context whole-repo |
| T4 | `anthropic/claude-sonnet-4-6` | $3.00 | P1/P2 final polish |
| T5 | `local/deepseek-r1-32b-awq` | $0.00 | local Kaggle GPU fallback |

`route(task)` returns a `RouteDecision` (model + fallback chain + tier).
`record_usage(model, tokens)` mutates the day's budget; once
`ARCHITECT_HARD_BUDGET_USD` is exceeded, every call is forced to T5.

### Per-task table

| Task | Primary | Fallbacks |
|------|---------|-----------|
| `recon`, `scope_parse` | T1-fast | T5 |
| `bulk_triage` | T5 | T1-fast |
| `static_analysis`, `patch_generation` | T1-deep | T1-fast, T2 |
| `exploit_reasoning`, `chain_synthesis` | T2 | T1-deep, T4 |
| `long_context_analysis` | T3 | T1-fast |
| `adversarial_review_a/b/c` | T1-fast / T1-deep / T2 | — |
| `report_drafting` | T1-deep | T1-fast |
| `critical_cve_draft` | T4 | T2 |

`call_with_skills(task, prompt, profile)` is the canonical entry point —
it routes, builds the master red-team prompt, injects the skill pack,
calls the LLM, and records the interaction in the RL feedback loop.

---

## 7. Hermes Reasoning Engine

`hermes_orchestrator.py` — six phases tracked on a `HermesSession`:

```
RECON → STATIC → DYNAMIC → EXPLOIT → CHAIN → REPORT
```

`run_hermes_research(target_repo, repo_dir, focus_area, max_iterations)`:

1. Builds a `HermesSession` and skill-augmented system prompt
   (uses `skill_selector.select_for_task` — added in v6).
2. Loops up to `max_iterations` times, each iteration:
   * Calls `_hermes_llm_call(messages)` → JSON tool-call or finding.
   * On `tool_call`, dispatches to one of: `ReconTool`, `TaintTool`,
     `SymbolicTool`, `FuzzTool`, `ExploitTool`, `CVETool`,
     `CommitWatchTool`, `SSECTool`, `ChainAnalyzerTool`.
   * On `finding`, computes **VES** (Vulnerability Exploitability Score:
     reachability × severity_class × novelty / complexity / auth-needed)
     and stores a `VulnerabilityFinding` dataclass.
3. After the loop, runs `_run_acts_consensus` — three different LLMs
   review the same finding; agreement increments **ACTS** (Adversarial
   Consensus Truth Score).
4. `build_tvg(repo_dir, findings)` produces a Target Vulnerability Graph
   (nodes = sinks, edges = data-flow relationships) for cross-finding
   chain reasoning.

Persistence: every session is JSON-serialised to
`/tmp/hermes_sessions/<session_id>.json` via `persist_hermes_session`.

---

## 8. Mythos MCP Fleet (37 servers)

The MCP fleet is described in `mcp_config.json`. Each entry is one of:

* `command: npx -y <pkg>` — community Node MCP server.
* `command: uvx mcp-server-shell --allow-commands <bin>` — shell wrapper
  exposing one or more binaries as tools.
* `command: python -m mythos.mcp.<module>` — Mythos-native Python module.

### v6 additions (12)

| Name | Module / binary | Purpose |
|------|-----------------|---------|
| `skill-selector-mcp` | `mythos.mcp.skill_selector_mcp` | semantic skill ctx |
| `trufflehog-deep-mcp` | `trufflehog` | full git history secrets |
| `gitleaks-mcp` | `gitleaks` | secondary secret scanner |
| `semgrep-pro-patterns-mcp` | `semgrep` w/ p/security-audit | SAST rule sets |
| `jwt-analyzer-mcp` | `mythos.mcp.jwt_analyzer_mcp` | alg:none, weak secret |
| `api-fuzzer-mcp` | `restler/dredd/schemathesis` | stateful API fuzz |
| `solidity-auditor-mcp` | `slither/myth` | smart-contract SAST |
| `dependency-confusion-mcp` | `mythos.mcp.dep_confusion_mcp` | dep-conf scan |
| `git-forensics-deep-mcp` | `git-dumper` | exposed .git dirs |
| `openapi-analyzer-mcp` | `mythos.mcp.openapi_analyzer_mcp` | spec → surface |
| `cors-analyzer-mcp` | `mythos.mcp.cors_analyzer_mcp` | CORS misconfig |
| `prototype-pollution-mcp` | `mythos.mcp.prototype_pollution_mcp` | JS proto sinks |

Each Python MCP exposes either `scan_host(host)` or `scan_repo(path)` (or
both — see `dep_confusion_mcp.scan_host` aliasing) so the night-hunt
detector dispatcher can call them uniformly.

---

## 9. Night Hunter — autonomous bug-bounty loop

`night_hunt_orchestrator.py` (added in v6).

### Pipeline

```
_ingest_scope()       → bounty_gateway.list_active_programs(plat)
                        falls back to scope_parser_mcp, then to demo data
_filter_by_floor()    → keep programs with P1≥$5k or P2≥$1k
                        (NIGHT_HUNTER_P1_FLOOR / _P2_FLOOR env)
_score_targets()      → 0.45*money + 0.35*breadth + 0.20*recency
_recon(target)        → subdomain_enum + httpx_probe + wayback + shodan
_hunt(target, recon)  → for each detector in (nuclei, zap, sqlmap,
                        jwt-analyzer, cors-analyzer, openapi, proto-poll)
                          run via _run_detector(...)
_validate(findings)   → architect.godmode_consensus.review_finding
                        + drop low-conviction noise
_draft_submission(f)  → platform-specific template (h1/bugcrowd/intigriti)
_persist(report)      → /data/night_reports/night_<cycle_id>.json
_notify(report)       → embodied_bridge.emit_status + notifier.notify
```

### Public API

```python
import night_hunt_orchestrator as nh
report = nh.run_night_cycle(platforms=["hackerone"], max_targets=3)
print(report.summary())                # {"targets":3,"findings":7,...}
nh.start_in_background(start_hour=23)  # daemon thread, runs forever
```

### Relevant env vars

```
NIGHT_HUNTER=1                    enable scheduler in app.py
NIGHT_HUNTER_HOUR=23              cycle start (UTC)
NIGHT_HUNTER_MORNING_HOUR=6       morning briefing time
NIGHT_HUNTER_P1_FLOOR=5000        $ minimum to qualify a program
NIGHT_HUNTER_P2_FLOOR=1000
NIGHT_HUNTER_MAX_TARGETS=3        per cycle
NIGHT_HUNTER_REPORTS=/data/night_reports
NIGHT_HUNTER_PLATFORMS=hackerone,bugcrowd,intigriti
NIGHT_HUNTER_PAUSED=1             skip the next cycle (set by openclaw)
```

### Safety policy

The orchestrator **never auto-submits**. `_draft_submission` produces a
markdown body that is queued for operator approval. Only the
`approve_finding` intent (via OpenClaw) calls
`bounty_gateway.submit_finding`. The plan's stated guardrail —
"target < 20% false positives before any submission" — is enforced by
the operator review step, not the code.

---

## 10. EmbodiedOS — OpenClaw + Telegram

`openclaw_gateway.py` (added in v6).

### Intent registry

```python
from openclaw_gateway import handle_command
handle_command("scan github.com/pallets/flask")
# → {"ok": True, "intent": "scan_repo", "reply": "Scan queued..."}
```

| Intent | Trigger pattern | Handler |
|--------|-----------------|---------|
| `scan_repo` | `scan <target>` / `audit <target>` | `OSSGuardian().run` |
| `night_run_now` | `night run` / `hunt now` | `nh.run_night_cycle()` |
| `pause_night` | `pause night` | sets `NIGHT_HUNTER_PAUSED=1` |
| `resume_night` | `resume night` | unsets it |
| `status` | `status` / `what are you doing` | system snapshot |
| `approve_finding` | `approve <id>` | `bounty_gateway.submit_finding` |
| `reject_finding` | `reject <id>` | `training_store.record_negative` |
| `explain_finding` | `explain <id>` | look up in night reports |
| `help` | `help` / `?` | prints intent list |

### HTTP surface (when `OPENCLAW=1`)

```
GET  /openclaw/status                liveness + intents + skill stats
POST /openclaw/command   {"text":...}  → handle_command(text)
POST /telegram/webhook                 Telegram Update payload
```

The HTTP endpoint requires `X-OpenClaw-Token` matching
`OPENCLAW_SHARED_SECRET` if that env var is set.

### Schedule (`openclaw_schedule.yaml`)

```yaml
heartbeat:
  health_check:        every: 15min
  harvester_run:       cron: "0 */6 * * *"
  night_hunt_start:    cron: "0 23 * * *"
  morning_report:      cron: "0 6 * * *"
  lora_export_check:   cron: "0 2 * * 0"
  training_digest:     cron: "0 9 * * 1"
```

Today the cron is implemented in two places:
* `night_hunt_orchestrator.schedule_loop` for the 23:00 cycle.
* The morning report is emitted at the *end* of each cycle (good enough
  for v6); a dedicated 06:00 cron is left for the DigitalOcean migration
  step where systemd timers are easier to reason about than in-app
  threads.

---

## 11. OSS Guardian flow

`oss_guardian.py` (unchanged in v6, documented here for completeness):

1. Open a `_open_sandbox(repo_url)` — pulls into a temp dir.
2. Detect runtime (`language_runtime.detect`).
3. Run the project's own test suite. If failures → `fix_mode`:
   call `run_hermes_research(focus_area="oss-guardian:fix-failing-tests")`,
   open a PR via the GitHub MCP server.
4. If tests pass → `attack_mode`: full Hermes session.
5. `_route_findings(findings, camp)` ships every finding to:
   * `embodied_bridge.emit_finding` (Telegram + OpenClaw + Discord).
   * `disclosure_vault` for SHA-256 hashed audit-trail storage.

---

## 12. Safety gates & audit trail

* `sast_gate.py` — every PR diff must pass Semgrep before submission.
* `architect/godmode_consensus.py` — 3-model ACTS review on every finding.
* `conviction_engine.py` — refuses to submit anything with VES < 0.6 or
  ACTS < 0.66 unless the operator overrides.
* `disclosure_vault.py` — append-only SHA-256 chained log of every
  finding, decision, and submission. Used by `tests/test_audit_chain.py`.

---

## 13. Local development

```
# bootstrap (Linux/WSL/macOS)
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
# optional: install MCP runtimes
pipx install uv && uv tool install nuclei semgrep trufflehog gitleaks

# unit tests
pytest -q

# run the gradio dashboard
PORT=7860 python app.py

# run the night hunter once, ad-hoc
python -m night_hunt_orchestrator

# pipe a command through openclaw without HTTP
python -m openclaw_gateway "scan github.com/pallets/flask"

# ask the skill selector for context
python -c "from architect import skill_selector as s; \
  print(s.select_for_task('jwt rs256 confusion', \
        repo_languages=['python'], attack_phase='static', top_k=3))"
```

---

## 14. Docker / HuggingFace Space deployment

The Space build is driven by the root `Dockerfile`. v6 lessons learned:

* `@modelcontextprotocol/server-git` and `…/server-sqlite` were removed
  from the npm registry in March 2026. Replaced with the PyPI versions
  `mcp-server-git` and `mcp-server-sqlite`, invoked by their console
  scripts. `mcp_config.json` was updated to match (`command:
  "mcp-server-git"` instead of `npx -y …`).
* The fix that unblocked the Space build is commit `6089ff0` on GitHub
  and `4b69257` on HuggingFace (cherry-picked because the histories had
  diverged).

Push flow when working through this repo:

```bash
git remote add origin   https://<gh-token>@github.com/Rhodawk-AI/Rhodawk-devops-engine.git
git remote add hf       https://Architect8999:<hf-token>@huggingface.co/spaces/Architect8999/rhodawk-ai-devops-engine

git push origin main                      # GitHub fast-forward
git fetch hf && git checkout -b hf-sync hf/main
git cherry-pick <commit-from-main>        # HF history is divergent
git push hf hf-sync:main
```

(The Replit / agent environment has destructive git ops blocked at the
shell tool, so we run `git commit` / `git push` through `code_execution`
shelling out to `child_process.execSync`.)

---

## 15. DigitalOcean migration

When the HuggingFace free tier proves too constrained:

1. Provision a DO droplet (4 vCPU / 8 GB / 50 GB block volume).
2. Mount block volume at `/data`. Set `MCP_DATA_ROOT=/data`.
3. Install Docker; clone the repo; `docker build -t rhodawk .`.
4. Persist secrets in `/etc/rhodawk.env` (chmod 600, root only).
5. Systemd unit:

   ```ini
   [Unit]
   Description=Rhodawk AI
   After=docker.service
   Requires=docker.service

   [Service]
   EnvironmentFile=/etc/rhodawk.env
   ExecStart=/usr/bin/docker run --rm --name rhodawk \
     --env-file /etc/rhodawk.env -p 7860:7860 -p 8765:8765 \
     -v /data:/data rhodawk
   Restart=always

   [Install]
   WantedBy=multi-user.target
   ```

6. Add systemd timers for the 23:00 / 06:00 / Sunday-02:00 cron entries
   in `openclaw_schedule.yaml` (preferred over in-app threads on a
   long-lived host).

---

## 16. Configuration reference

All toggles via env vars — no config file changes needed for ops.

| Var | Default | Purpose |
|-----|---------|---------|
| `PORT` | 7860 | gradio listen port |
| `NIGHT_HUNTER` | 0 | start the night-hunt thread |
| `NIGHT_HUNTER_HOUR` | 23 | cycle start (UTC) |
| `NIGHT_HUNTER_PAUSED` | unset | skip next cycle |
| `NIGHT_HUNTER_REPORTS` | /data/night_reports | report dir |
| `OPENCLAW` | 0 | start the gateway |
| `OPENCLAW_HOST` | 0.0.0.0 | bind |
| `OPENCLAW_PORT` | 8765 | bind |
| `OPENCLAW_SHARED_SECRET` | unset | required header on /openclaw/command |
| `TELEGRAM_BOT_TOKEN` | unset | outbound Telegram |
| `TELEGRAM_CHAT_ID` | unset | default chat for status pings |
| `OPENROUTER_API_KEY` | required for T1–T4 | LLM tier 1–4 |
| `OPENROUTER_BASE_URL` | https://openrouter.ai/api/v1 | LLM endpoint |
| `LOCAL_VLLM_BASE_URL` | http://localhost:8000/v1 | T5 endpoint |
| `ARCHITECT_HARD_BUDGET_USD` | 10.0 | day-cap before forced T5 |
| `ARCHITECT_SKILLS_DIR` | /data/skills | additional runtime skills dir |
| `ARCHITECT_EMBED_MODEL` | sentence-transformers/all-MiniLM-L6-v2 | embedder |
| `ARCHITECT_SKILL_CACHE` | /tmp/architect_skill_cache | embedding cache |
| `HACKERONE_API_TOKEN` etc. | unset | platform scope ingestion |
| `GITHUB_PERSONAL_ACCESS_TOKEN` | unset | github MCP + PR submission |
| `BRAVE_API_KEY` | unset | brave-search MCP |
| `SHODAN_API_KEY` | unset | shodan MCP |
| `NVD_API_KEY` | unset | cve-intel MCP |
| `SEMGREP_APP_TOKEN` | unset | semgrep registry |
| `SESSION_SECRET` | required | Flask session signing |

---

## 17. Adding a new skill

```
$ cat > architect/skills/web/my-new-skill.md <<'MD'
---
name: my-new-skill
domain: web
triggers:
  languages: [python]
  asset_types: [http]
severity_focus: [P1, P2]
---

# my-new-skill

Markdown body the model reads when this skill is selected.
MD

# verify it loads + ranks correctly
python -c "
from architect import skill_selector as s
print(s.explain('exploit my-new-skill in flask app',
                repo_languages=['python'], attack_phase='static'))
"
```

The selector picks it up automatically — no registry edit needed. The
embedding cache is keyed on body hash, so adding new skills only embeds
the new files.

---

## 18. Adding a new MCP server

For a Python module (preferred):

```
# mythos/mcp/my_new_mcp.py
def scan_host(host: str) -> list[dict]:
    return [{"title": "...", "severity": "low", "cvss": 3.0,
             "url": host, "description": "...", "evidence": {},
             "confidence": 0.6}]
```

Register it in `mcp_config.json`:

```json
"my-new-mcp": {
  "command": "python",
  "args": ["-m", "mythos.mcp.my_new_mcp"],
  "description": "What it does"
}
```

If you want it called by the night-hunter for every target, add it to
`_DETECTORS` in `night_hunt_orchestrator.py` and add a branch in
`_run_detector(...)` that imports + calls it.

For a binary wrapper, use the `uvx mcp-server-shell --allow-commands
<bin>` pattern that the existing `nuclei-scanner` / `semgrep-sast`
entries use.

---

## 19. Testing & validation

```
pytest tests/                       # 10 existing test files
pytest tests/test_skill_registry.py # skill loader
pytest tests/test_model_router.py   # router decisions + budget
pytest tests/test_nightmode_smoke.py # legacy nightmode
pytest tests/test_mcp_servers_load.py # validates mcp_config.json parses

# manual smoke for v6 additions
python -c "from architect import skill_selector; print(skill_selector.stats())"
python -c "import night_hunt_orchestrator as n; print(n.run_night_cycle().summary())"
python -m openclaw_gateway "status"
python -m openclaw_gateway "help"
python -m mythos.mcp.jwt_analyzer_mcp https://example.com
```

The night-hunt smoke test will fall through to the demo `example.com`
target if no scope tokens are configured, so it's safe to run in dev.

---

## 20. Troubleshooting

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| `npm ERR! 404` building Docker image | npm package removed | already fixed in v6 by switching to PyPI `mcp-server-git/sqlite` |
| Skill selector returns 0 matches | `skill_registry.load_all()` empty | check `architect/skills/` exists in image; check `ARCHITECT_SKILLS_DIR` |
| `sentence-transformers` not installed | OK — falls back to keyword scoring | install if you want semantic ranking: `pip install sentence-transformers` |
| Telegram messages don't arrive | `TELEGRAM_BOT_TOKEN`/`TELEGRAM_CHAT_ID` unset | check env vars; `telegram_send` returns False without erroring |
| Night cycle runs but no findings | no scanner binaries installed | install `nuclei`, `semgrep`, `sqlmap`, etc., or accept that only the Python-native MCPs (jwt/cors/openapi/proto-poll/dep-conf) will fire |
| Hermes loop crashes on first iter | `OPENROUTER_API_KEY` missing | set it; check `_BUDGET.spent_usd` hasn't tripped the hard cap |
| MCP config has duplicate keys | JSON parser keeps last; benign but ugly | dedupe block in `mcp_config.json` (v6 keeps the consolidated single block) |

---

## 21. Founder operating handbook

### Daily routine (5 minutes)

1. Open Telegram. Read the 06:00 morning briefing.
2. For each finding, read the title + severity + target. Tap one of:
   * `approve <id>` — submit to platform
   * `reject <id>` — log negative training signal
   * `explain <id>` — get the plain-English version first
3. `status` — confirm the night-hunt thread is armed for tonight.

### Weekly routine (30 minutes)

* Read `/data/night_reports/*.json` from the past 7 cycles. Sample 3
  findings end-to-end and verify reproducibility yourself.
* Check the LoRA export schedule (Sunday 02:00) — confirm a new training
  digest landed on Monday.
* Review the public leaderboard (`public_leaderboard.py`). If PRs
  merged < target, check `repo_harvester.py` is selecting decent repos.

### When to spend money

* T4 (Claude Sonnet) only on `critical_cve_draft`. Verify `_BUDGET` shows
  >$5 burn/day before adding more T4 calls.
* Hardware: keep one DO droplet running 24/7 (~$24/mo). Add a Kaggle GPU
  for T5 only when local triage volume justifies it.

### When to add a skill

Whenever you find yourself writing the same explanation twice in a
finding triage. Capture the pattern in
`architect/skills/<domain>/<topic>.md`. The selector will start loading
it into Hermes within minutes — no deploy required if you mount
`/data/skills/`.

### When to ship to investors

The Masterplan §10 demo script (Demo A / B / C) is the canonical pitch.
Pre-flight checklist before any live demo:
1. `docker pull` the latest image; smoke-test the gradio UI loads.
2. Run `night_run_now` once to ensure the pipeline doesn't error.
3. Send `status` from your phone over Telegram and confirm the reply.
4. Prepare a known-vuln backup target in case the live repo finds nothing
   in the demo window (e.g. an intentionally vulnerable fork).

---

*Rhodawk AI v6.0 — Developer & Founder Playbook*
*Generated as the closing artefact of the Masterplan §3 build sweep.*
*Always paired with the upstream `Rhodawk_Superhuman_Agent_Plan.md`.*

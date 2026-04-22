# ARCHITECT Masterplan — Implementation vs Deferred

**Commit baseline:** `da9b4c7` (pre-ARCHITECT)
**Spec source:** `ARCHITECT_MASTERPLAN_1776834551686.md`
**Author:** ARCHITECT build agent · 2026-04-22

This document maps every numbered section of the masterplan to its
implementation status in this commit, plus a concrete migration path for
anything deferred to the paid VPS / lab phase.

---

## Legend
* ✅ **DONE** — implemented in this commit, importable + covered by tests.
* 🟡 **STUB** — interface present, falls back gracefully when the heavy
  binary/SDK is missing; ready to "light up" once the dep is installed on
  the VPS.
* ⛔ **DEFERRED** — explicitly out of scope for this commit (see notes).

---

## §1 — Vision & §2 — Capability Targets

| Capability                 | Status | Notes |
|----------------------------|--------|-------|
| Multi-platform agent       | ✅ DONE | `architect/embodied_bridge.py` fans out to Telegram + OpenClaw + Hermes Agent + Discord |
| Tier-routed model brain    | ✅ DONE | `architect/model_router.py` — DeepSeek V3 / MiniMax M2.5 / Qwen3 / Claude / local |
| Skill registry             | ✅ DONE | `architect/skill_registry.py` + 19 SKILL.md files in `architect/skills/` |
| Autonomous night-mode loop | ✅ DONE | `architect/nightmode.py` — `start_in_background()` boots from `app.py` |
| Sandboxed OSS-Guardian     | ✅ DONE | `architect/sandbox.py` (docker preferred, process fallback) |

## §4 — Architecture / §5 — Operating Loops

| Layer                       | Status | Notes |
|-----------------------------|--------|-------|
| Operator dashboard tab      | ✅ DONE | New "🏛 ARCHITECT" tab in `app.py` |
| Embodied bridge             | ✅ DONE | `architect/embodied_bridge.py` |
| Skill loader                | ✅ DONE | `architect/skill_registry.py` |
| Tier router + budget cap    | ✅ DONE | `architect/model_router.py` (`ARCHITECT_HARD_BUDGET_USD`) |
| Sandbox manager             | ✅ DONE | `architect/sandbox.py` |
| Night-mode scheduler        | ✅ DONE | `architect/nightmode.py` (`ARCHITECT_NIGHTMODE=1`, default 18:00 hour) |

## §6 — EmbodiedOS

| Channel        | Status | Notes |
|----------------|--------|-------|
| Telegram       | ✅ DONE | `TELEGRAM_BOT_TOKEN` + `TELEGRAM_CHAT_ID` |
| OpenClaw       | ✅ DONE | `OPENCLAW_WEBHOOK_URL` |
| Hermes Agent   | ✅ DONE | `HERMES_AGENT_URL` (POSTs to `/v1/skill/extract`) |
| Discord mirror | ✅ DONE | `DISCORD_WEBHOOK_URL` |

## §7 — Skill Library (19 skills)

### Phase 1 — foundation (7) — all ✅
* `binary-analysis`, `web-security-advanced`, `api-security`,
  `memory-safety`, `cryptography-attacks`, `network-protocol`, `cloud-security`

### Phase 2 — broader surface (6) — all ✅
* `mobile-android`, `mobile-ios`, `supply-chain`, `reverse-engineering`,
  `hardware-protocols`, `container-escape`

### Phase 3 — frontier (6) — all ✅
* `firmware-analysis`, `automotive-security`, `ics-scada`,
  `rf-radio-security`, `aviation-aerospace`, `satellite-comms`

Each SKILL.md ships with YAML front-matter (`triggers.languages`,
`triggers.frameworks`, `triggers.asset_types`, `tools`, `severity_focus`)
that the registry uses to score against a target profile.

## §8 — Model Tier Strategy

| Tier                 | Status | Notes |
|----------------------|--------|-------|
| Tier 1 — DeepSeek V3 | ✅ DONE | default for static / patch / report tasks |
| Tier 2 — MiniMax M2.5| ✅ DONE | long-context + exploit reasoning |
| Tier 3 — Qwen3 235B  | ✅ DONE | adversarial-review-c |
| Tier 4 — Claude S4.6 | ✅ DONE | critical-CVE drafts |
| Tier 5 — Local vLLM  | ✅ DONE | bulk-triage + budget-exceeded fallback |
| Hard budget cap      | ✅ DONE | `ARCHITECT_HARD_BUDGET_USD` (default $10) |

## §9 — Tooling / MCP servers

| MCP server             | Status | Notes |
|------------------------|--------|-------|
| browser-agent-mcp      | ✅ DONE | Playwright when available, requests fallback |
| scope-parser-mcp       | ✅ DONE | H1 + Bugcrowd + Intigriti + raw-text parser |
| subdomain-enum-mcp     | ✅ DONE | subfinder/amass/dnsx + crt.sh fallback |
| httpx-probe-mcp        | ✅ DONE | native httpx + threaded requests fallback |
| shodan-mcp             | 🟡 STUB | needs `SHODAN_API_KEY` |
| wayback-mcp            | ✅ DONE | Wayback CDX + URLScan |
| frida-runtime-mcp      | 🟡 STUB | wraps `mythos.dynamic.frida_instr`, requires frida on VPS |
| ghidra-bridge-mcp      | ✅ DONE | analyzeHeadless > radare2 > readelf chain |
| can-bus-mcp            | 🟡 STUB | needs `python-can` and a SocketCAN interface |
| sdr-analysis-mcp       | 🟡 STUB | needs `rtl_sdr` / `hackrf_transfer` |

All 10 are registered in `mcp_config.json` (total 41 MCP servers, up from 31).

## §10 — Hardening & Safety

| Item                          | Status | Notes |
|-------------------------------|--------|-------|
| Bounded log ring buffer       | ✅ DONE | `_hermes_logs` is now `deque(maxlen=10_000)` |
| Durable `HermesSession` save  | ✅ DONE | `persist_hermes_session()` after CONSENSUS + DISCLOSURE |
| Operator-gated submission     | ✅ DONE | night-mode never auto-submits — see `_phase_report()` |
| Sandbox wallclock cap         | ✅ DONE | `ARCHITECT_SANDBOX_TIMEOUT_S` (default 4 h) |
| ACTS gate on findings         | ✅ DONE | `ARCHITECT_ACTS_GATE` (default 0.72) |

## §11 — Test Suite

New `tests/` directory with 9 modules + shared `conftest.py`:

* `test_audit_chain.py`        — chained-hash integrity
* `test_webhook_hmac.py`       — GitHub-style HMAC accept/reject
* `test_model_router.py`       — tier routing + budget fallback + caller pref
* `test_scope_parser.py`       — text parser + no-creds graceful path
* `test_mcp_servers_load.py`   — every MCP module imports + exposes tools
* `test_skill_registry.py`     — 19 skills load + `match()` picks correctly
* `test_job_queue.py`          — namespaced enqueue/status round-trip
* `test_mythos_diagnostics.py` — availability / mcp / reasoning matrices
* `test_nightmode_smoke.py`    — phase-report filter + empty-target safety

Run with `pytest -q`.

## §12 — Deferred (explicit, with migration paths)

| Item                                        | Reason | When to enable |
|---------------------------------------------|--------|----------------|
| Real LoRA training on a 4×H100 box          | ⛔ — needs hardware | Provision GPU VPS, then `RHODAWK_LORA=1` |
| Frida live attach to a real device          | ⛔ — needs USB / device farm | Connect device, `pip install frida` |
| `python-can` against a real CAN interface   | ⛔ — needs vehicle bench | Plug PEAK/Vector dongle, `pip install python-can` |
| `pwntools` for real ROP-chain build         | ⛔ — Linux-only heavy dep | `pip install pwntools` on the VPS |
| Replace tiny in-process MCP shim with the   | ⛔ — works today via stdio | `pip install mcp` on the VPS, swap `_mcp_runtime.py` |
| official `mcp` Python SDK                   |        |                |
| Live HackerOne/Bugcrowd auto-submission     | ⛔ — by design (operator gate) | Never; remains operator-gated by design |

---

## Operator runbook (post-merge)

1. `pip install -r requirements.txt` — pulls `dnspython` for the new
   `subdomain-enum-mcp` fallback; everything else lights up automatically
   when present.
2. Optional secrets to wire on the VPS:
   ```
   OPENROUTER_API_KEY              # tiers 1-4
   ARCHITECT_NIGHTMODE=1            # arm the 18:00 daily loop
   ARCHITECT_HARD_BUDGET_USD=20     # daily budget guardrail
   ARCHITECT_ACTS_GATE=0.72         # raise to 0.80 for stricter triage
   TELEGRAM_BOT_TOKEN / _CHAT_ID    # operator notifications
   HACKERONE_USERNAME / _API_TOKEN
   BUGCROWD_API_TOKEN
   INTIGRITI_API_TOKEN
   SHODAN_API_KEY
   URLSCAN_API_KEY
   OPENCLAW_WEBHOOK_URL
   HERMES_AGENT_URL
   DISCORD_WEBHOOK_URL
   ```
3. `pytest -q` should be all-green (or skip-only on env-dependent paths).
4. `python app.py` — the new "🏛 ARCHITECT" tab shows live stats; click
   "🌙 Run Night-Mode Cycle Now" to smoke the full loop on demand.

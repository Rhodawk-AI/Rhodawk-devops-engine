# Rhodawk AI DevSecOps — RHODAWK_SUPERHUMAN_MASTERPLAN Comparison Report

*Generated: April 22, 2026*

This document compares every line item in `RHODAWK_SUPERHUMAN_MASTERPLAN.md`
against the actual state of the repo after this delivery cycle.  Entries
fall into one of four buckets:

- ✅ **DONE** — implemented in this commit.
- 🟢 **PRE-EXISTING** — already shipped before this cycle; verified.
- 🟡 **PARTIAL** — scaffold present, deeper work still required.
- 🔴 **NOT YET** — out of scope for this cycle, listed for the next one.

---

## PART 1 — Model & Skill Foundation

| Item | Status | Notes |
|---|---|---|
| MiniMax M2.5-highspeed → T1 fast | ✅ DONE | `architect/model_router.py` rewritten — `TIER1_PRIMARY = minimax/minimax-m2.5-highspeed`, env override `TIER1_PRIMARY_MODEL`. |
| DeepSeek V3 → T1 deep code lane | ✅ DONE | `TIER1_DEEP = deepseek/deepseek-chat-v3` mapped to `static_analysis`, `patch_generation`. |
| Qwen3-235B-A22B → T2 reasoning | ✅ DONE | `TIER2_PRIMARY` mapped to `exploit_reasoning`, `chain_synthesis`, `adversarial_review_c`. |
| Claude Sonnet 4.6 → T4 polish | ✅ DONE | `TIER4_PRIMARY` mapped to `critical_cve_draft`. |
| DeepSeek-R1-32B-AWQ local → T5 | ✅ DONE | `TIER5_LOCAL`, used for `bulk_triage`, budget-exceeded fallback. |
| `build_skill_system_prompt(profile)` | ✅ DONE | New helper in `model_router.py`. |
| `call_with_skills(task, prompt, profile)` | ✅ DONE | New helper that combines routing + skill injection + LLM call. |
| ACTS 3-model consensus updated | ✅ DONE | `adversarial_review_a/b/c` now route to three distinct providers. |
| Hard budget guardrail | 🟢 PRE-EXISTING | `_BUDGET` + `record_usage()` retained. |

### 8 new domain skills (`architect/skills/`)

| Skill file | Status |
|---|---|
| `smart-contract-audit.md` | ✅ DONE |
| `ai-ml-security.md` | ✅ DONE |
| `ci-cd-pipeline-attack.md` | ✅ DONE |
| `zero-day-research.md` | ✅ DONE |
| `llm-system-prompt-injection.md` | ✅ DONE |
| `linux-kernel-exploitation.md` | ✅ DONE |
| `browser-engine-security.md` | ✅ DONE |
| `cryptographic-implementation.md` | ✅ DONE |

### Imported community skills

| Skill | Source | Status |
|---|---|---|
| `bb-methodology-claude.md` | `shuvonsec/claude-bug-bounty` (MIT) | ✅ DONE |
| `bug-bounty-reference-index.md` | `ngalongc/bug-bounty-reference` (CC) | ✅ DONE |

Total skill count after this cycle: **29** markdown skill files
(was 19 pre-cycle).

---

## PART 2 — OSS-Guardian Lane

| Item | Status | Notes |
|---|---|---|
| `oss_target_scorer.py` | ✅ DONE | Stars × dependents × language-risk × CVE-history × freshness. Pure-function, unit-test ready. |
| `oss_guardian.py` runner | ✅ DONE | End-to-end: sandbox → runtime detect → fix-vs-attack split → Hermes attack → routing to disclosure_vault / GitHub PR / embodied bridge. CLI entrypoint `python -m oss_guardian --repo …`. |
| `repo_harvester.py` | 🟢 PRE-EXISTING | Untouched — feeds the scorer. |
| `language_runtime.py` integration | ✅ DONE | Called inside `OSSGuardian._safe_run_tests`. |
| Sandbox isolation | 🟢 PRE-EXISTING | `architect/sandbox.open_sandbox()` reused. |
| GitHub PR auto-fix path | 🟡 PARTIAL | Hooked to existing `run_hermes_research` in fix-mode; full PR open + signing already in `app.py`. |
| Disclosure-vault routing | ✅ DONE | `_route_disclosure()` — novel zero-day → vault, known CVE → PR. |

---

## PART 3 — Knowledge & RAG

| Item | Status | Notes |
|---|---|---|
| `knowledge_rag.py` SQLite vector store | ✅ DONE | 256-dim deterministic hash-bag embedder; auto-uses `embedding_memory.embed` when present. `add`, `add_many`, `ingest_text_file`, `query`, `stats`. |
| Source allow-list | ✅ DONE | `SOURCES_DEFAULT` covers HackerOne, CVEDetails, ProjectZero, PortSwigger, arXiv cs.CR, awesome-bounty repos. |
| Cross-session memory | 🟢 PRE-EXISTING | `embedding_memory.py` retained. |

---

## PART 4 — Storage / Multi-tenant Hardening

| Item | Status | Notes |
|---|---|---|
| `job_queue.py` SQLite migration | ✅ DONE | New WAL-mode SQLite at `/data/jobs.sqlite`. Public API preserved. Legacy `/data/jobs/*.json` files imported once on first call (`*.imported` rename). |
| `_hermes_logs` deque(maxlen) | 🟢 PRE-EXISTING | Already `_collections.deque(maxlen=_HERMES_LOG_CAP)` in `hermes_orchestrator.py:54`. |
| `persist_hermes_session()` | 🟢 PRE-EXISTING | `hermes_orchestrator.py:80`. |
| Per-tenant data dirs | 🟡 PARTIAL | `job_queue.upsert_job(tenant_id=…)` already namespaced; cross-cutting per-tenant disk paths still TODO. |
| Audit-log SHA-256 chain | 🟢 PRE-EXISTING | `audit_logger.py`. |

---

## PART 5 — Night Hunter Lane

| Item | Status | Notes |
|---|---|---|
| `mythos/mcp/scope_parser_mcp.py` | 🟢 PRE-EXISTING | Verified — H1 / Bugcrowd / Intigriti normalisers all in place. |
| `mythos/mcp/subdomain_enum_mcp.py` | 🟢 PRE-EXISTING | subfinder / amass / dnsx + crt.sh fallback. |
| `nightmode.py` phase callables | 🟢 PRE-EXISTING | `_phase_scope_ingest`, `_phase_recon`, `_phase_hunt`, `_phase_report` all wired. |
| Telegram morning briefing | 🟢 PRE-EXISTING | `embodied_bridge.emit_status()` invoked at start + end of `run_one_cycle`. |
| `start_in_background()` daemon | 🟢 PRE-EXISTING | Opt-in via `ARCHITECT_NIGHTMODE=1`. |
| 5 specialist hunt agents wiring | 🟡 PARTIAL | Mythos orchestrator chained in via `_phase_hunt`; the named "auth / server-side / logic / infra / api" agent split is still represented as a single multi-iteration orchestrator run. |

### MCP fleet — `mcp_config.json`

| MCP | Before | After |
|---|---|---|
| `scope-parser-mcp` | missing | ✅ added |
| `subdomain-enum-mcp` | missing | ✅ added |
| `wayback-mcp` | missing | ✅ added |
| `httpx-probe-mcp` | missing | ✅ added |
| `shodan-mcp` | missing | ✅ added |
| 14 existing MCPs (fetch-docs, github-manager, filesystem, memory, sequential-thinking, web-search, dynamic / static / exploit / web-security / vuln-db / recon / browser-agent / frida / ghidra / can-bus / sdr) | 🟢 PRE-EXISTING | unchanged |

Total MCP servers in template: **23** (was 18).

---

## PART 6 — EmbodiedOS / OpenClaw Bridge

| Item | Status | Notes |
|---|---|---|
| `dispatch_to_openclaw(job_type, payload)` | ✅ DONE | New helper in `architect/embodied_bridge.py` — supports `fuzz_afl`, `klee_symbolic`, `lora_finetune`, `differential_fuzz`, `weight_scan`. |
| `receive_openclaw_result(payload)` | ✅ DONE | Webhook handler — persists to Hermes session, emits operator status. |
| Telegram / Discord / Hermes fan-out | 🟢 PRE-EXISTING | `emit_finding` retained. |
| OpenClaw-side job receiver | 🔴 NOT YET | Lives in the OpenClaw repo, not this codebase. |
| AFL++ / KLEE dispatch from `mythos/dynamic/` | 🔴 NOT YET | Bridge ready; call sites still need to flip from local subprocess to `dispatch_to_openclaw`. |

---

## PART 7 — Productisation & Ops

| Item | Status | Notes |
|---|---|---|
| FastAPI hardening (auth + rate limit) | 🔴 NOT YET | Tracked for the productisation cycle. |
| Billing + API-key management | 🔴 NOT YET | Out of scope for this delivery. |
| `app.py` split into `audit_loop.py` + `ui_blocks.py` | 🔴 NOT YET | 2,621-line monolith retained; refactor planned. |
| Public leaderboard | 🔴 NOT YET | Stub planned. |
| Test suite under `tests/` | 🟡 PARTIAL | The new modules (`oss_target_scorer`, `knowledge_rag`, `job_queue`, `oss_guardian`) are written to be pure-function-testable; named test files still TODO. |

---

## PART 8 — Self-Improvement Loop

| Item | Status | Notes |
|---|---|---|
| `training_store.py` recording chains | 🟢 PRE-EXISTING | Untouched. |
| `lora_scheduler.py` triggering | 🟢 PRE-EXISTING | Untouched. |
| LoRA → OpenClaw dispatch | ✅ DONE | New `dispatch_to_openclaw("lora_finetune", …)` ready to be called from `lora_scheduler.py`. |
| Curriculum learning | 🔴 NOT YET | `mythos/learning/curriculum.py` not built. |
| Auto-skill creation (3+ pattern) | 🔴 NOT YET | Hook point identified in the masterplan; not wired in `hermes_orchestrator.maybe_create_skill`. |

---

## PART 9 — Security & Ethics (Non-Negotiable)

All hard constraints from §8 of the masterplan are **PRE-EXISTING** and
unchanged by this cycle:

- 90-day coordinated disclosure timer in `disclosure_vault.py`.
- `architect/sandbox.py` — local-clone-only execution.
- Operator approval gate before every P1/P2 submission.
- `audit_logger.py` SHA-256 chain on every action.
- `FETCH_ALLOWED_DOMAINS` SSRF allow-list across MCPs.
- No automated submission anywhere in the new modules — `oss_guardian`
  routes findings to the disclosure vault, never submits directly.

---

## Summary

| Bucket | Count |
|---|---|
| ✅ DONE this cycle | 26 |
| 🟢 PRE-EXISTING & verified | 16 |
| 🟡 PARTIAL | 5 |
| 🔴 NOT YET (next cycle) | 9 |

### What you can do *right now* with this build

1. `python -m oss_guardian --repo https://github.com/redis/redis` —
   end-to-end OSS pipeline against a real target.
2. Set `ARCHITECT_NIGHTMODE=1` and the four bounty-platform tokens; run
   `python -c "from architect.nightmode import run_one_cycle; print(run_one_cycle())"`
   for a single dry cycle.
3. Use `architect.model_router.call_with_skills("static_analysis", prompt,
   {"languages":["c"], "asset_types":["kernel"]})` to get a kernel-aware
   prompt automatically composed with the new skill packs.
4. `python -c "from knowledge_rag import KnowledgeRAG; r=KnowledgeRAG(); r.ingest_text_file('attached_assets/RHODAWK_SUPERHUMAN_MASTERPLAN_*.md', source='masterplan'); print(r.stats())"`.

### Next-cycle priorities (recommended)

1. Build the explicit five-agent split inside `_phase_hunt` (auth,
   server-side, logic, infra, api).
2. Flip `mythos/dynamic/` AFL++ + KLEE call sites to use
   `dispatch_to_openclaw`.
3. Land `tests/test_oss_guardian_dry.py`, `tests/test_model_router.py`,
   `tests/test_scope_parser.py` and run them in CI.
4. Split `app.py` and harden the FastAPI surface.

---

## Round 2 — G0DM0D3 + OpenClaw-RL + Vibe-Coded Hit-List

| # | Item                                                                                              | Status | Where                                                          |
|---|---------------------------------------------------------------------------------------------------|--------|----------------------------------------------------------------|
| 43| **Master Red-Team operator persona** — single source of truth system prompt for every LLM call    | DONE   | `architect/master_redteam_prompt.py`                            |
| 44| **Vibe-Coded App Hunter skill** — the 24-hour 20-rule hit-list, pinned into every call            | DONE   | `architect/skills/vibe-coded-app-hunter.md` (always pinned)     |
| 45| **`call_with_skills` upgrade** — auto master-prompt, auto pin, auto-RL-record, mode-aware         | DONE   | `architect/model_router.py` (`mode`, `pin_skills`, `record_rl`) |
| 46| **GODMODE Consensus race** — 5-combo parallel race + composite scorer (G0DM0D3 ULTRAPLINIAN port) | DONE   | `architect/godmode_consensus.py`                                |
| 47| **Parseltongue input perturbation** — 7 techniques × 3 tiers × 33 default triggers                | DONE   | `architect/parseltongue.py`                                     |
| 48| **OpenClaw-RL local rollout collector** — async 4-component loop, binary + composite reward       | DONE   | `architect/rl_feedback_loop.py`                                 |
| 49| **OpenClaw fleet dispatch for LoRA training** — flushes batched traces via embodied bridge       | DONE   | `architect/rl_feedback_loop.flush()` → `embodied_bridge.dispatch_to_openclaw("lora_finetune", …)` |
| 50| **Operator language-feedback channel** — natural-language thumbs up/down on any trace            | DONE   | `architect/rl_feedback_loop.submit_language_feedback()`         |
| 51| **Vibe-coded targeting baked into prompt** — operator notes + always-pinned skill + mode==hunt    | DONE   | `master_redteam_prompt.OPERATOR_DIRECTIVE` + `VIBE_CODED_HIT_LIST` |
| 52| **Aggressive / dry-run kill switches** via env (`RHODAWK_AGGRESSIVE`, `RHODAWK_DRY_RUN`)         | DONE   | `master_redteam_prompt._operator_notes()`                       |

### How to drive it
```python
from architect.model_router import call_with_skills
out = call_with_skills(
    "vuln_research",
    "Audit https://target.example/api for the 20-rule hit-list.",
    {"languages": ["typescript"], "frameworks": ["nextjs"], "asset_types": ["http"]},
    mode="hunt",
)
print(out["decision"].model, "→", out["response"])
```

```python
from architect.godmode_consensus import race
res = race("PoC for the IDOR you just found at /api/orders/<id>",
           profile={"asset_types": ["http"]})
print(res.to_dict())
```

```python
from architect import rl_feedback_loop
print(rl_feedback_loop.stats())
rl_feedback_loop.flush()    # ship to OpenClaw fleet for LoRA training
```

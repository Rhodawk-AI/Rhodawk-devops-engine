# EmbodiedOS V2 — Architecture Specification

> Complete architecture reference for the redesigned system.
> Anti-Vibe Constitution §14 compliance: module-level docstrings on every new file.

---

## System Overview

EmbodiedOS is a unified, state-of-the-art autonomous security researcher
built on top of the Rhodawk DevOps Engine. It fuses Hermes Agent (self-evolution),
OpenClaw (multi-channel gateway), vendor/openclaude (autonomous coding engine),
and 25+ Mythos MCP servers into a single coherent system controlled exclusively
through a Telegram bot.

---

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           OPERATOR LAYER                                    │
│                                                                             │
│   Telegram Bot ──► OpenClaw Gateway (:18789) ──► Unified Intent Router     │
│                                                   (embodied/router/)        │
└────────────────────────────┬────────────────────────────────────────────────┘
                             │ dispatch()
┌────────────────────────────▼────────────────────────────────────────────────┐
│                        ORCHESTRATION LAYER                                  │
│                                                                             │
│   ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────────────┐ │
│   │  Hermes Agent    │  │  OpenClaw MCP    │  │  EmbodiedOS Bridge MCP   │ │
│   │  (:11434)        │  │  Gateway         │  │  (embodied/bridge/)      │ │
│   │  Self-evolution  │  │  Telegram/Slack/ │  │  HTTP + stdio + Python   │ │
│   │  Skill learning  │  │  Discord adapter │  │  Tool registry v2.0      │ │
│   └──────────┬───────┘  └──────────────────┘  └──────────────────────────┘ │
│              │                                                              │
│   ┌──────────▼────────────────────────────────────────────────────────┐    │
│   │              PIPELINE DISPATCHER                                  │    │
│   │   Side 1: Repo Hunter  │  Side 2: Bounty Hunter                  │    │
│   │   (embodied/pipelines/) │  (embodied/pipelines/)                 │    │
│   └──────────┬────────────────────────────┬──────────────────────────┘    │
└──────────────│────────────────────────────│───────────────────────────────┘
               │                            │
┌──────────────▼────────────────────────────▼───────────────────────────────┐
│                        ANALYSIS LAYER                                      │
│                                                                             │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────────┐ │
│  │  SAST    │ │  Taint   │ │Symbolic  │ │  Fuzzing │ │  Chain Analyzer  │ │
│  │ sast_gate│ │ taint_   │ │ symbolic_│ │ red_team │ │  chain_analyzer  │ │
│  │          │ │ analyzer │ │ engine   │ │ _fuzzer  │ │                  │ │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────────────┘ │
│                                                                             │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────────┐ │
│  │ Supply   │ │  CVE     │ │  Vuln    │ │ GODMODE  │ │  Parseltongue    │ │
│  │  Chain   │ │  Intel   │ │Classifier│ │ Consensus│ │  Perturbation    │ │
│  │          │ │ cve_intel│ │          │ │(5-model) │ │  (33 triggers)   │ │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────────────┘ │
└──────────────────────────────────────────────────────────────────────────┬─┘
                                                                           │
┌──────────────────────────────────────────────────────────────────────────▼─┐
│                        DISCLOSURE LAYER                                    │
│                                                                             │
│  ┌─────────────────────┐  ┌─────────────────────┐  ┌────────────────────┐ │
│  │  Disclosure Vault   │  │  Exploit Primitives  │  │  Harness Factory   │ │
│  │  disclosure_vault   │  │  exploit_primitives  │  │  harness_factory   │ │
│  │  PENDING_HUMAN_APPR │  │  reason_exploitabili │  │  generate_poc      │ │
│  └─────────────────────┘  └─────────────────────┘  └────────────────────┘ │
│                                                                             │
│  ┌─────────────────────┐  ┌─────────────────────┐                         │
│  │  Bounty Gateway     │  │  GitHub App          │                         │
│  │  bounty_gateway     │  │  github_app          │                         │
│  │  (submit gated)     │  │  (open_pr_for_repo)  │                         │
│  └─────────────────────┘  └─────────────────────┘                         │
└────────────────────────────────────────────────────────────────────────────┘
```

---

## Memory Architecture (3 Layers)

```
┌───────────────────────────────────────────────────┐
│               LAYER 1: SESSION                    │
│  audit_logger.py — immutable, hash-chained        │
│  In-memory ring buffer (512 events/mission)       │
│  SQLite session_log table (persistent)            │
└───────────────────────┬───────────────────────────┘
                        │
┌───────────────────────▼───────────────────────────┐
│              LAYER 2: EPISODIC                    │
│  embedding_memory.py — vector store               │
│  memory_engine.py — TF-IDF retrieval             │
│  knowledge_rag.py — RAG pipeline                 │
│  unified_memory.py — FTS5 SQLite unified API     │
│  Hermes Agent FTS5 search + LLM summarization    │
└───────────────────────┬───────────────────────────┘
                        │
┌───────────────────────▼───────────────────────────┐
│             LAYER 3: PROCEDURAL                   │
│  embodied/skills/sync_engine.py — skill catalogue │
│  architect/skills/ — 121+ curated Rhodawk skills  │
│  ~/.hermes/skills/ — Hermes auto-created skills   │
│  ~/.openclaw/skills/ — 13,000+ ClawHub skills    │
│  training_store.py — LoRA checkpoint store       │
│  lora_scheduler.py — auto-improvement via GEPA   │
└───────────────────────────────────────────────────┘
```

---

## Skill Store Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                    SKILL SYNC ENGINE                                │
│              embodied/skills/sync_engine.py                         │
│                                                                     │
│  Input pools (walk *.md recursively):                               │
│  ┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐    │
│  │ architect/skills/│ │~/.hermes/skills/ │ │~/.openclaw/skills│    │
│  │ (rhodawk source) │ │ (hermes source)  │ │ (openclaw source)│    │
│  │ precedence: 3    │ │ precedence: 2    │ │ precedence: 1    │    │
│  └────────┬─────────┘ └────────┬─────────┘ └────────┬─────────┘    │
│           └──────────────┬─────┘                    │              │
│                          ▼                           │              │
│              Normalize to agentskills.io format      │              │
│              Deduplicate by (name+domain+body hash)  │              │
│              Precedence: rhodawk > hermes > openclaw │              │
│                          │                                          │
│                          ▼                                          │
│              unified_skills.json + UNIFIED_SKILLS.md               │
│              (written to $EMBODIED_SKILL_CACHE)                     │
│                          │                                          │
│                          ▼                                          │
│              select_for_task() → top-N prompt block                │
│              (keyword overlap + semantic rerank)                    │
└─────────────────────────────────────────────────────────────────────┘
```

---

## G0DM0D3 Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                    GODMODE CLASSIC (5-model race)                   │
│              architect/godmode_consensus.py                          │
│                                                                     │
│  User prompt ──► Parseltongue perturbation (RHODAWK_PARSE_INTENSITY)│
│                          │                                          │
│                          ▼                                          │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │             ThreadPoolExecutor (5 workers)                   │   │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────┐ ┌───────┐ │   │
│  │  │T1-fast   │ │T1-deep   │ │T2-exploit│ │T4-rpt│ │T5-lcl │ │   │
│  │  │qwen3-32b │ │llama3-70b│ │deepseek  │ │claude│ │minimax│ │   │
│  │  │hunt mode │ │hunt mode │ │exploit   │ │report│ │triage │ │   │
│  │  └────┬─────┘ └────┬─────┘ └────┬─────┘ └──┬───┘ └───┬───┘ │   │
│  │       └─────────────┴───────────┴──────────┴─────────┘     │   │
│  │                         ACTS scorer                          │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                          │                                          │
│                          ▼                                          │
│              ACTS 100-point composite (5 dimensions × 20pt each):  │
│                CWE presence | CVSS quality | Reproducibility        │
│                PoC feasibility | Patch suggestion quality           │
│                          │                                          │
│                          ▼                                          │
│              ACTS ≥ 72 → surface to operator                       │
│              ACTS < 72 → episodic memory only                       │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Self-Evolution Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│              GEPA (weekly) — Skill Evolution                         │
│         embodied/evolution/gepa_engine.py                            │
│                                                                      │
│  1. Load SKILL.md files from shared skill store                     │
│  2. Build eval set (campaign traces → synthetic fallback)           │
│  3. Execute skill against eval set (via Hermes Agent)               │
│  4. DSPy + LLM reflection → diagnose failures → propose mutations   │
│  5. Pareto frontier selection (quality × novelty)                   │
│  6. Open GitHub PR → human reviews → human merges                   │
│                                                                      │
│         NEVER AUTO-MERGES (INV-005)                                  │
└──────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────┐
│           Darwin Gödel Machine (monthly) — Code Evolution            │
│         embodied/evolution/code_evolver.py                           │
│                                                                      │
│  1. Identify underperforming analysis engines (episodic metrics)    │
│  2. Generate variant Python source (Hermes Agent code generation)   │
│  3. Compile check (ast.parse) + import check (subprocess)           │
│  4. Run test suite against variant in sandbox                       │
│  5. Reject if score < 0.95 × original (regression threshold)        │
│  6. Open GitHub PR → human reviews → human merges                   │
│                                                                      │
│         NEVER AUTO-MERGES (INV-005)                                  │
└──────────────────────────────────────────────────────────────────────┘
```

---

## Claude Context Integration

```
┌──────────────────────────────────────────────────────────────────────┐
│                  CLAUDE CONTEXT MCP                                  │
│         @zilliz/claude-context-mcp                                   │
│                                                                      │
│  On every target repo clone:                                         │
│  rhodawk.context.index_repo(path) ──► Milvus vector index           │
│                                                                      │
│  During red-team sessions:                                           │
│  rhodawk.context.semantic_search(query) ──► top-N code chunks       │
│                          │                                           │
│                          ▼                                           │
│  Injected into agent system prompt alongside top-N matched skills   │
│                                                                      │
│  Research daemon queries past indexed repos for knowledge distill.  │
│                                                                      │
│  Backend: Zilliz Cloud (Milvus) — configured via:                   │
│    MILVUS_TOKEN, MILVUS_ADDRESS                                      │
└──────────────────────────────────────────────────────────────────────┘
```

---

## Service Start Order (entrypoint.sh)

```
1. camofox browser (port 9377) — slowest, lazy engine download
2. OpenClaude gRPC daemons — do (50051) + or (50052)
3. Hermes Agent gateway (port 11434)
4. OpenClaw gateway (port 18789)
5. EmbodiedOS MCP bridge (port 8600)
6. Research daemon (background, every 6h)
7. Final: python -m embodied run
```

---

## Bounded Contexts

| Domain | Module(s) | Contract |
|--------|-----------|----------|
| Ingress | `embodied/router/unified_gateway.py`, `embodied/router/intent_router.py` | `dispatch(text, user, channel) → dict` |
| Orchestration | `embodied/pipelines/repo_hunter.py`, `bounty_hunter.py`, `campaign_runner.py` | `run_*(**kwargs) → dict` |
| Analysis | `sast_gate`, `taint_analyzer`, `symbolic_engine`, `red_team_fuzzer`, `chain_analyzer`, `vuln_classifier` | per-module typed functions |
| Disclosure | `disclosure_vault`, `exploit_primitives`, `harness_factory`, `bounty_gateway`, `github_app` | `PENDING_HUMAN_APPROVAL` gate |
| Memory | `embodied/memory/unified_memory.py` | `get_memory() → UnifiedMemory` |
| Skills | `embodied/skills/sync_engine.py` | `get_engine() → SkillSyncEngine` |
| Gateway | `embodied/bridge/mcp_server.py`, `embodied/bridge/tool_registry.py` | MCP JSON-line protocol + HTTP |

No module crosses these boundaries without going through the declared contract.

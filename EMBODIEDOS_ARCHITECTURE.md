# EmbodiedOS — Architecture (Sections 3 & 4.1 – 4.8)

EmbodiedOS is the **strictly-additive** integration layer that fuses Nous
Research's *Hermes Agent* and the *OpenClaw* multi-channel gateway into the
existing Rhodawk DevOps engine.  Nothing in the legacy code path is removed
or replaced — every new capability lives under the new `embodied/` Python
package and is wired in via `entrypoint.sh`.

```
                      ┌─────────────────────────────────────────────┐
                      │           Operator (any channel)            │
                      │  Telegram • Discord • Slack • OpenClaw CLI  │
                      └───────────────────────┬─────────────────────┘
                                              │
            ┌─────────────────────────────────▼─────────────────────────────────┐
            │  embodied.router.unified_gateway  (Section 4.1)                   │
            │  ───────────────────────────────────────────────────────────────  │
            │  - Per-channel adapters → canonical (text, user, channel_id).    │
            │  - intent_router classifies → side1.* | side2.* | maintenance.*. │
            │  - Falls back to legacy `openclaw_gateway.handle_command(...)`   │
            │    so the existing intent set keeps working.                     │
            └─────────────────────────────────┬─────────────────────────────────┘
                                              │
                ┌─────────────────────────────┼─────────────────────────────┐
                │                             │                             │
                ▼                             ▼                             ▼
   ┌─────────────────────┐         ┌────────────────────┐        ┌────────────────────┐
   │ Side 1 — Repo Hunter│         │ Side 2 — Bounty    │        │ maintenance.*       │
   │ (Section 4.3)       │         │ Hunter (Sec 4.4)   │        │ (status / pause /   │
   │                     │         │                    │        │ approve / reject)   │
   └──────────┬──────────┘         └─────────┬──────────┘        └────────┬───────────┘
              │                              │                            │
              ▼                              ▼                            ▼
   ┌──────────────────────────────────────────────────────────────────────────────┐
   │  embodied.bridge.mcp_server   (Section 4.2)                                  │
   │  ─────────────────────────────────────────────────────────────────────────  │
   │  Single MCP server, three transports: stdio | HTTP | in-process.            │
   │  Reuses mythos.mcp._mcp_runtime.MCPServer for stdio so it speaks the same   │
   │  wire-format as every existing Mythos MCP server.                            │
   │                                                                              │
   │  Tools registered via embodied.bridge.tool_registry:                          │
   │    - rhodawk.repo.*   (clone, run_tests, write_patch, open_pr, …)            │
   │    - rhodawk.sec.*    (sast, taint, symbolic, fuzz, chain, classifier)       │
   │    - rhodawk.intel.*  (camofox fetch, hackerone, bugcrowd, intigriti)        │
   │    - rhodawk.disclosure.*  (vault, scrape developer emails, draft email)     │
   │    - rhodawk.skill.*  (sync, select_for_task, save_auto_skill)               │
   │    - rhodawk.memory.* (write_session, episodic_query, save_skill)            │
   │    - rhodawk.pipeline.* (run_repo_hunter, run_bounty_hunter, …)              │
   │                                                                              │
   │  Emits two registration files on demand so external agents can discover us: │
   │    - /tmp/mcp_runtime.embodied.json     (Hermes Agent)                       │
   │    - /tmp/openclaw_mcp.embodied.json    (OpenClaw)                           │
   └──────────────────────────────────────────────────────────────────────────────┘
              │
              │  consumed by ↓
              ▼
   ┌──────────────────────────────────────────────────────────────────────────────┐
   │  embodied.bridge.hermes_client   ←→   embodied.bridge.openclaw_client        │
   │  ─────────────────────────────────────────────────────────────────────────  │
   │  Thin HTTP clients used by the pipelines + research daemon to delegate any  │
   │  reasoning / channel-push work to the running Hermes Agent / OpenClaw       │
   │  daemons.  Both return {"ok": bool, ...} dicts and never raise.             │
   └──────────────────────────────────────────────────────────────────────────────┘
```

---

## 4.5 — Skill Sync Engine

`embodied.skills.sync_engine.SkillSyncEngine` walks **three** pools:

* `architect/skills/`         — Rhodawk's curated catalogue.
* `${HERMES_SKILLS_DIR}`      — Hermes Agent's auto-skill outputs.
* `${OPENCLAW_SKILLS_DIR}`    — OpenClaw's ClawHub-installed skills.

`embodied.skills.normalizer` rewrites every variant (Hermes' `capabilities`,
OpenClaw's `inputs/outputs`, Claude.md frontmatter, …) into the canonical
**agentskills.io** schema.  The engine fingerprints by name + domain + body
hash and applies deterministic precedence (`rhodawk > hermes > openclaw`)
when duplicates collide.

Outputs (rewritten on every `sync()`):

* `${EMBODIED_SKILL_CACHE}/UNIFIED_SKILLS.md`      — human index.
* `${EMBODIED_SKILL_CACHE}/unified_skills.json`    — machine index.

`select_for_task(...)` returns an ephemeral `<skill>…</skill>` prompt block
packing the top-K skills relevant to the task — first scored by keyword /
trigger overlap, then re-ranked by the existing `architect.skill_selector`
when it's available.

Auto-created skills (Hermes' auto-skill output, or pipeline-distilled
campaigns) are written to **both** `architect/skills/embodied_auto/` (so
they're git-versioned) and `${HERMES_SKILLS_DIR}/embodied_auto/` (so
Hermes sees them on its next reload).

---

## 4.6 — Unified Memory

`embodied.memory.unified_memory.UnifiedMemory` provides a three-layer
memory:

| Layer       | Backend                                | Lifetime           | Used by                              |
|-------------|----------------------------------------|--------------------|--------------------------------------|
| Session     | In-process ring buffer + SQLite log    | Mission lifetime   | Hermes step-stream, pipeline notes    |
| Episodic    | SQLite (FTS5 if available)             | Forever            | "What happened on mission X?" recall  |
| Procedural  | Skill catalogue + `rhodawk.knowledge`  | Forever            | "What skill should I use for Y?"      |

Failure isolation: every write is wrapped in try/except and falls back to
`/tmp` when `/data` isn't writable (so a fresh dev clone never crashes).

---

## 4.7 — Continuous-Learning Daemon

`embodied.learning.research_daemon.ResearchDaemon` runs forever.  Each tick:

1. Fetches the configured CVE / news / write-up feeds (preferring the
   already-bundled **camofox** stealth browser; falls back to `requests`).
2. Splits the payload into bounded chunks and asks Hermes to either distil
   a generalisable skill via the `teach_skill` tool or skip it as
   non-novel.
3. Re-runs the SkillSyncEngine so the new skill is immediately pickable.
4. Logs the tick to episodic memory.

Toggle with `EMBODIED_LEARNING_ENABLED`; tune cadence with
`EMBODIED_RESEARCH_MIN`.

---

## 4.8 — Bootstrap

`entrypoint.sh` now ends by:

1. Spawning `python -m embodied bootstrap` in the background, which itself
   starts: the MCP bridge (HTTP), the unified gateway (HTTP +1), and the
   research daemon — all as daemon threads inside one Python process.
2. Emitting `/tmp/mcp_runtime.embodied.json` + `/tmp/openclaw_mcp.embodied.json`
   so Hermes Agent and OpenClaw register the bridge automatically.
3. Handing off to the existing `python -u app.py` (Gradio + GitHub webhook
   + every legacy subsystem — completely unchanged).

The whole EmbodiedOS layer is gated by `EMBODIED_OS_ENABLED=1`, so it can
be turned off without touching code.

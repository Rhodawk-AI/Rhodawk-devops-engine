---
title: Rhodawk AI DevSecOps Engine
emoji: 🦅
colorFrom: purple
colorTo: indigo
sdk: docker
pinned: true
license: apache-2.0
---

# 🦅 Rhodawk AI — Autonomous DevSecOps Control Plane v4.0

> **Autonomous CI/CD healing + Zero-Day Discovery. The only DevSecOps engine that attacks its own green repos.**

Rhodawk AI v4.0 is an enterprise-grade autonomous DevSecOps control plane with two modes:
- **Blue Team**: detects failing tests, deploys AI (Aider + Qwen via OpenRouter) to generate a fix, gates through SAST + supply chain + adversarial LLM review, opens a PR.
- **Red Team / CEGIS**: when all tests pass (repo is GREEN), autonomously attacks the codebase — discovering mathematical invariants, synthesizing Property-Based Tests via Hypothesis, fuzzing to exhaustion, and handing the minimal crashing counter-example to the Blue Team for patching.

---

## Architecture

```
GitHub Repo
    │
    ▼
pytest discovery & execution
    │
    ├── FAIL ──► Blue Team Healing Loop
    │               │
    │               ├── Memory Engine (TF-IDF — similar past fixes)
    │               ├── Aider Agent (Qwen 2.5 Coder 32B via OpenRouter + MCP)
    │               ├── SAST Gate (bandit + secret scanner)
    │               ├── Supply Chain Gate (pip-audit + typosquatting)
    │               ├── Adversarial LLM Review (hostile red-team model)
    │               └── Open PR → Immutable Audit Trail (SHA-256 JSONL)
    │
    └── ALL PASS ──► 🆕 Red Team CEGIS Engine
                        │
                        ├── AST Universal Analyzer
                        │     rank functions by complexity, overflow risk, recursion, mutations
                        ├── Red Team LLM (Attacker)
                        │     synthesize Hypothesis property-based test (invariant attack)
                        ├── Deterministic Fuzzing Loop (50,000 examples, aggressive boundaries)
                        │
                        ├── CRASH ──► Package minimal counter-example (zero-day)
                        │              └── CEGIS Handoff → Blue Team patches it → PR
                        │
                        └── NO CRASH ──► Inject survived inputs → harder invariant → retry
                                          (up to 4 CEGIS rounds, escalates to Claude for final round)
```

---

## Required Secrets

Set these in **Settings → Secrets** of your HuggingFace Space:

| Secret | Description |
|--------|-------------|
| `GITHUB_TOKEN` | GitHub PAT with `repo` + `pull_request` scope |
| `GITHUB_REPO` | Target repository in `owner/repo` format |
| `OPENROUTER_API_KEY` | OpenRouter API key (Qwen 2.5 Coder 32B) |

## Optional Secrets

| Secret | Description |
|--------|-------------|
| `TELEGRAM_BOT_TOKEN` | Telegram bot token for notifications |
| `TELEGRAM_CHAT_ID` | Telegram chat ID |
| `SLACK_WEBHOOK_URL` | Slack incoming webhook URL |
| `RHODAWK_TENANT_ID` | Namespace for multi-tenant deployments (default: `default`) |
| `RHODAWK_MODEL` | Override AI model (default: `openrouter/qwen/qwen-2.5-coder-32b-instruct:free`) |
| `RHODAWK_RED_TEAM_ENABLED` | Enable/disable Red Team CEGIS engine (default: `true`) |
| `RHODAWK_RED_TEAM_MODEL` | Red Team attacker model (default: Qwen 2.5 Coder 32B) |
| `RHODAWK_RED_TEAM_MODEL_STRONG` | Escalation model for final CEGIS rounds (default: Claude 3.5 Sonnet) |
| `RHODAWK_CEGIS_ROUNDS` | Max CEGIS re-attack rounds per target (default: `4`) |
| `RHODAWK_FUZZ_EXAMPLES` | Hypothesis max_examples per PBT run (default: `50000`) |
| `RHODAWK_FUZZ_TIMEOUT` | Fuzzing subprocess timeout in seconds (default: `180`) |
| `RHODAWK_MAX_TARGETS` | Max AST attack targets per audit (default: `8`) |

---

## Enterprise Features

### SAST Gate (Pre-PR Security Scanning)
Every AI-generated diff is scanned for:
- Hardcoded secrets, API keys, and tokens
- Dangerous Python patterns (`os.system`, `eval`, `pickle.loads`, `subprocess` with `shell=True`)
- Bandit SAST findings (HIGH+ severity blocks the PR)

**If the SAST gate blocks a PR, it is never opened.** The AI agent cannot bypass this gate.

### Immutable Audit Trail
Every AI action is appended to a SHA-256 chained JSONL file:
- AI model version and prompt hash are logged per job
- Each entry references the previous entry's hash (tamper-evident chain)
- Chain integrity can be verified on-demand from the dashboard
- Suitable as SOC 2 / ISO 27001 evidence

### Namespaced Job Queue
Jobs are keyed by `(tenant_id, repo, test_path)` — the foundation for multi-tenant SaaS. Backed by atomic JSON writes today, designed to swap to PostgreSQL with zero application changes.

### 🆕 Red Team CEGIS Engine (v4.0)
The industry's first autonomous zero-day discovery loop integrated directly into a CI/CD healing platform:

- **AST Universal Analyzer** — scores every Python function by cyclomatic complexity, arithmetic operations, recursion depth, and mutable argument mutation. Ranks targets by attack priority with composite scoring.
- **Red Team LLM (The Attacker)** — dispatches an adversarial LLM with the function's full AST profile. The LLM synthesizes a Hypothesis property-based test targeting: integer overflow, commutativity, associativity, idempotency, roundtrip encoding, monotonicity, aliasing, and exception-swallowing.
- **Deterministic Fuzzing Loop** — executes the generated PBT via subprocess (`shell=False` enforced, secrets stripped) with up to 50,000 randomized examples. Captures the minimal falsifying counter-example with exact input values.
- **CEGIS Re-attack Loop** — if no crash is found, the survived inputs are injected back into the LLM prompt ("these inputs didn't work, try harder") and a new invariant is synthesized. Up to 4 rounds, escalating to a stronger model on the final round.
- **CEGIS Handoff (Red → Blue)** — the crash is packaged as a deterministic pytest with the exact failing input baked in. The Blue Team processes it identically to a human-written failing test: SAST → supply chain → adversarial review → PR.

**Result:** Zero-day vulnerabilities are discovered, reproduced, patched, and PRed autonomously — without any human writing a test.

---

## Roadmap

1. **Firecracker microVMs** — per-job execution isolation replacing subprocess
2. **GitHub App** — fine-grained per-repo OAuth replacing Personal Access Tokens
3. **PostgreSQL job store** — horizontal scaling for concurrent audits
4. **Webhook event triggers** — event-driven audits on push/PR events
5. **Fine-tuned model** — trained on proprietary `(test_failure, fix)` dataset
6. **Data flywheel** — every PR approval/rejection becomes training signal
7. **Concurrency fuzzer** — Hypothesis stateful testing + threading to find race conditions
8. **Multi-language AST** — extend Red Team to JavaScript (Babel AST), Go (go/ast), Rust (syn)

---

*Built by Rhodawk AI — the autonomous DevSecOps control plane.*

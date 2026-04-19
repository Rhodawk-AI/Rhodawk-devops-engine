---
title: Rhodawk AI DevSecOps Engine
emoji: 🦅
colorFrom: indigo
colorTo: blue
sdk: gradio
sdk_version: 6.12.0
python_version: '3.12'
app_file: app.py
pinned: false
license: apache-2.0
---

# Rhodawk AI — Autonomous DevSecOps Engine

**Autonomous DevSecOps Control Plane v4.0**

A self-contained system that autonomously detects failing tests, generates code fixes using LLMs, verifies those fixes through a multi-layered security pipeline, and opens pull requests — without a human in the loop unless explicitly required.

---

## What This System Actually Does

Rhodawk is not a code suggestion tool. It is a complete autonomous repair loop. Here is the exact sequence it runs for every failing test it encounters:

1. Clone a target repository and discover all test files
2. Run the test suite and identify failing tests
3. Retrieve semantically similar past fixes from a vector memory store (the "data flywheel")
4. Dispatch Aider (an AI code editor) via MCP tool calls with the failure context and memory-retrieved examples
5. Re-run the tests on the patched code to confirm the fix works
6. If still failing: retry with the new failure context, up to a configurable maximum number of attempts
7. Run a SAST gate (Bandit + 16-pattern secret scanner) against the generated diff
8. Run a supply chain gate (pip-audit + typosquatting detection against 50+ known patterns)
9. Run a 3-model adversarial review concurrently (DeepSeek-R1 + Llama-3.3-70B + Gemma-3-27B) — requires 2/3 majority to proceed
10. Run Z3 formal verification against bounded integer invariants and overflow checks
11. If the adversarial review rejects: loop back with the critique as additional context
12. If all gates pass and conviction criteria are met: auto-merge the PR (when enabled)
13. Record the full attempt chain to a training store (SQLite or PostgreSQL)
14. Export LoRA fine-tuning data in JSONL format when enough high-quality examples accumulate

For repositories where all tests are already passing, the Red Team CEGIS engine activates: it autonomously attacks the codebase, generates property-based fuzz tests targeting mathematical invariants and boundary conditions, and injects discovered crashes back into the Blue Team repair loop as synthetic failing tests.

---

## Repository Structure

```
.
├── app.py                      Main entry point. Gradio UI + full audit loop orchestration (2,311 lines)
├── hermes_orchestrator.py      Hermes: 6-phase autonomous security research agent (RECON→DISCLOSURE) (715 lines)
├── language_runtime.py         Universal language abstraction: Python, JS/TS, Java, Go, Rust, Ruby (1,540 lines)
├── red_team_fuzzer.py          CEGIS autonomous red team engine — finds zero-days in passing repos (1,561 lines)
├── adversarial_reviewer.py     3-model concurrent consensus adversarial code review (294 lines)
├── verification_loop.py        Retry-with-context fix loop with configurable max attempts
├── conviction_engine.py        Auto-merge gate: 7-criteria trust evaluation before autonomous PR merge
├── embedding_memory.py         Dual-backend semantic memory: SQLite/MiniLM or Qdrant/CodeBERT
├── memory_engine.py            Fix outcome tracking and similarity retrieval API
├── training_store.py           SQLite/Postgres training data pipeline — the data flywheel
├── lora_scheduler.py           LoRA fine-tune export scheduler (triggers at 50+ good fixes)
├── bounty_gateway.py           Bug bounty pipeline: HackerOne, Bugcrowd, GitHub Advisories — human-approval-gated
├── vuln_classifier.py          CWE taxonomy classifier → CVSS scoring → severity tier
├── cve_intel.py                NVD/CVE intelligence + SSEC (semantic exploit chain similarity)
├── supply_chain.py             pip-audit + typosquatting detection supply chain gate
├── sast_gate.py                Bandit SAST + 16-pattern secret scanner gate
├── formal_verifier.py          Z3 SMT solver: integer overflow + invariant formal verification
├── symbolic_engine.py          Angr symbolic execution for binary path exploration
├── taint_analyzer.py           Dataflow taint analysis: source-to-sink tracking
├── fuzzing_engine.py           Hypothesis property-based fuzzing harness generator
├── exploit_primitives.py       Exploit primitive reasoning: overflow, UAF, race, injection classification
├── harness_factory.py          Proof-of-concept harness compiler for operator-reviewed gaps
├── chain_analyzer.py           Multi-primitive vulnerability chain synthesizer
├── commit_watcher.py           Commit anomaly detection (CAD) — silent security patch identification
├── repo_harvester.py           Autonomous target repository selection and prioritization
├── swebench_harness.py         SWE-bench Verified evaluation harness (routes through Rhodawk's own loop)
├── audit_logger.py             Append-only tamper-evident audit trail with SHA-256 chain integrity
├── disclosure_vault.py         Coordinated disclosure document vault with 90-day timeline tracking
├── public_leaderboard.py       Fix success rate leaderboard for tracked repositories
├── semantic_extractor.py       AST-level semantic feature extraction for vulnerability scoring
├── github_app.py               GitHub App JWT authentication handler
├── webhook_server.py           Event-driven webhook server on port 7861 (GitHub push, CI failure, manual trigger)
├── job_queue.py                Job queue with status tracking and metrics
├── worker_pool.py              Parallel audit worker pool
├── notifier.py                 Slack/webhook notification dispatch
├── mcp_config.json             MCP server suite configuration (25 cybersecurity servers, template — no secrets)
├── Dockerfile                  Two-stage Docker build: Python 3.12-slim + Node.js for MCP
├── requirements.txt            Python dependencies
├── FOUNDER_PLAYBOOK.md         Full technical + investor documentation (1,119 lines)
└── SECURITY_RESEARCH_PLAYBOOK.md  Ethical AVR operator guide (200 lines)
```

---

## Required API Keys and Environment Variables

### Mandatory

| Variable | Purpose | Where to Get |
|---|---|---|
| `GITHUB_TOKEN` | Clone repos, open PRs, create GitHub Security Advisories | GitHub Settings → Developer Settings → Personal Access Tokens (needs `repo` + `security_events` scopes) |
| `OPENROUTER_API_KEY` | All LLM calls: fix generation, adversarial review, Hermes orchestrator | [openrouter.ai/keys](https://openrouter.ai/keys) — has a generous free tier |

The system will refuse to start if either of these is missing.

### Optional (enable specific features)

| Variable | Default | Purpose |
|---|---|---|
| `GITHUB_REPO` | `""` | Target repository in `owner/repo` format. Can also be supplied at runtime via the chat UI |
| `RHODAWK_MODEL` | `openrouter/qwen/qwen-2.5-coder-32b-instruct:free` | LLM used for code fix generation |
| `HERMES_MODEL` | `deepseek/deepseek-r1:free` | LLM used for the Hermes security research orchestrator |
| `HERMES_FAST_MODEL` | `deepseek/deepseek-v3:free` | Faster LLM used for lightweight Hermes sub-tasks |
| `RHODAWK_AUTO_MERGE` | `false` | Set to `true` to enable autonomous PR merge when all 7 conviction criteria pass |
| `RHODAWK_RED_TEAM_ENABLED` | `true` | Set to `false` to disable the red team fuzzer on passing repos |
| `RHODAWK_LORA_ENABLED` | `false` | Set to `true` to export LoRA training data when 50+ good fixes accumulate |
| `RHODAWK_EMBEDDING_BACKEND` | `sqlite` | Set to `qdrant` for CodeBERT-based semantic memory (requires GPU, `transformers`, `torch`) |
| `RHODAWK_ADVERSARY_MODEL` | `deepseek/deepseek-r1:free` | Primary adversarial reviewer model |
| `RHODAWK_CONSENSUS_THRESHOLD` | `0.67` | Fraction of models that must agree (default: 2/3) |
| `RHODAWK_CONVICTION_CONFIDENCE` | `0.92` | Minimum adversarial confidence for auto-merge |
| `RHODAWK_WEBHOOK_SECRET` | `""` | HMAC-SHA256 secret for validating GitHub webhook payloads |
| `DB_BACKEND` | `sqlite` | Set to `postgres` and provide `DATABASE_URL` for persistent production storage |
| `DATABASE_URL` | `""` | PostgreSQL connection string (only used when `DB_BACKEND=postgres`) |
| `HACKERONE_API_KEY` | `""` | HackerOne report submission (bug bounty gateway) |
| `HACKERONE_USERNAME` | `""` | HackerOne account username |
| `HACKERONE_PROGRAM` | `""` | HackerOne program handle |
| `NVD_API_KEY` | `""` | NIST NVD CVE API key (higher rate limits — free to request at nvd.nist.gov) |
| `BRAVE_API_KEY` | `""` | Brave Search API for Hermes web search MCP tool |
| `RHODAWK_WEBHOOK_PORT` | `7861` | Port for the webhook server (runs alongside Gradio) |
| `SEMGREP_APP_TOKEN` | `""` | Semgrep Cloud token for enhanced SAST |

---

## How to Run Locally

### Prerequisites

- Python 3.12
- Node.js 18+ and npm (for MCP servers)
- Git

### Step 1 — Clone this repository

```bash
git clone https://github.com/Rhodawk-AI/Rhodawk-devops-engine.git
cd Rhodawk-devops-engine
```

### Step 2 — Install Python dependencies

```bash
pip install -r requirements.txt
```

> **Note on atheris:** The `atheris` coverage-guided fuzzer requires Clang and libFuzzer at compile time and has been intentionally removed from `requirements.txt`. The system automatically falls back to `Hypothesis` for property-based testing.

### Step 3 — Install MCP server dependencies

```bash
npm install -g @modelcontextprotocol/server-github
npm install -g @modelcontextprotocol/server-memory
npm install -g @modelcontextprotocol/server-filesystem
npm install -g @modelcontextprotocol/server-sequential-thinking
npm install -g @modelcontextprotocol/server-brave-search
npm install -g @modelcontextprotocol/server-git
```

### Step 4 — Set environment variables

```bash
export GITHUB_TOKEN="your_github_personal_access_token"
export OPENROUTER_API_KEY="your_openrouter_api_key"
export GITHUB_REPO="owner/your-target-repo"   # optional — can be set in UI
```

### Step 5 — Create the data directory

```bash
mkdir -p /data
```

### Step 6 — Run the application

```bash
python -u app.py
```

The Gradio UI will start on `http://localhost:7860`. The webhook server starts automatically on port 7861.

---

## How to Run with Docker

### Build the image

```bash
docker build -t rhodawk-ai .
```

### Run the container

```bash
docker run -d \
  -p 7860:7860 \
  -p 7861:7861 \
  -v rhodawk_data:/data \
  -e GITHUB_TOKEN="your_github_personal_access_token" \
  -e OPENROUTER_API_KEY="your_openrouter_api_key" \
  -e GITHUB_REPO="owner/your-target-repo" \
  rhodawk-ai
```

Open `http://localhost:7860` in your browser.

---

## Running on HuggingFace Spaces

This repository is designed to deploy directly as a HuggingFace Space.

1. Fork or duplicate the Space at `Architect8999/rhodawk-ai-devops-engine`
2. In your Space's Settings → Repository Secrets, add:
   - `GITHUB_TOKEN`
   - `OPENROUTER_API_KEY`
3. The Dockerfile handles the full build automatically
4. The Space will be available at `https://huggingface.co/spaces/your-username/your-space-name`

---

## Connecting a GitHub Webhook (Event-Driven Mode)

To make Rhodawk trigger automatically on every CI failure or push:

1. In your GitHub repository: Settings → Webhooks → Add webhook
2. Set Payload URL to `https://your-deployment-url/webhook/github`
3. Set Content type to `application/json`
4. Set Secret to the same value you put in `RHODAWK_WEBHOOK_SECRET`
5. Select events: `Push`, `Check runs`, `Status`
6. Click "Add webhook"

Rhodawk will now automatically run the full audit loop every time CI fails on your repository.

---

## The Autonomous Research Pipeline (Hermes)

Beyond fixing failing tests, the Hermes orchestrator can be triggered to run a full autonomous security research sweep on any public repository. It executes six phases:

| Phase | What Happens |
|---|---|
| RECON | Clone, fingerprint, map attack surface, score file complexity |
| STATIC | Taint analysis, CWE pattern matching, symbolic execution planning |
| DYNAMIC | Fuzzing harness generation and execution |
| EXPLOIT | Exploit primitive reasoning on confirmed crashes |
| CONSENSUS | 3-model adversarial verdict on all findings |
| DISCLOSURE | Package report, hold in human-approval queue |

All findings sit in `PENDING_HUMAN_APPROVAL` state. Nothing is submitted to HackerOne, Bugcrowd, or GitHub Security Advisories without a human clicking "Approve & Submit" in the UI.

---

## The Data Flywheel

Every fix attempt — successful or not — is recorded in the training store. The schema captures the full chain:

```
test failure → memory retrieval → prompt → LLM diff → SAST result → adversarial verdict → test outcome
```

When 50 or more high-quality fixes accumulate (`RHODAWK_LORA_ENABLED=true`), the scheduler exports a LoRA fine-tuning dataset in standard JSONL chat format, ready for HuggingFace PEFT/TRL or AutoTrain. Each successive fine-tuning cycle makes the model progressively better at fixing failures in your specific codebase.

---

## Supported Languages

The universal language runtime (`language_runtime.py`) handles 7 languages:

| Language | Test Runner | SAST | Supply Chain Audit |
|---|---|---|---|
| Python | pytest / uv | Bandit + Semgrep | pip-audit |
| JavaScript | Jest / Mocha / Vitest | eslint-security | npm audit |
| TypeScript | Same as JS + tsc | Same as JS | npm audit |
| Java | JUnit / TestNG / Maven / Gradle | Semgrep-Java | OWASP dep-check |
| Go | go test | gosec | govulncheck |
| Rust | cargo test | clippy | cargo-audit |
| Ruby | RSpec / Minitest | brakeman | bundle-audit |

Language detection is automatic. The system fingerprints the cloned repository and selects the correct runtime.

---

## Custom Algorithms

**VES — Vulnerability Entropy Score**
Measures how surprising and dangerous a code path is based on control flow complexity, data flow depth, and deviation from similar code in the corpus.

**TVG — Temporal Vulnerability Graph**
Models how bugs propagate across commit history. Identifies the commit that introduced an assumption gap and traces which later commits relied on that assumption.

**ACTS — Adversarial Consensus Trust Score**
Bayesian aggregation of the 3-model adversarial review. Weights model consistency, argument quality, and historical accuracy of each model's votes.

**CAD — Commit Anomaly Detection**
Statistical detection of silent security patches: commits that fix security issues without mentioning it in the commit message.

**SSEC — Semantic Similarity Exploit Chain**
Embeds known exploit patterns using CodeBERT and compares them to repository code via cosine similarity. Surfaces CWE candidates even when no test failure exists.

---

## Security Design Principles

- All secrets are loaded from environment variables. No secrets are hardcoded or committed.
- The MCP config file is a template only. The runtime version with injected secrets is written to `/tmp/mcp_runtime.json` at startup and never committed.
- The audit logger uses an append-only SHA-256 chain to detect tampered audit records.
- The bug bounty gateway enforces human approval at the API call level, not just the UI.
- Z3 formal verification runs on every AI-generated patch before it can be merged.
- SSRF protection: all MCP fetch tools use `FETCH_ALLOWED_DOMAINS` allowlists.

---

## License

Proprietary. Source visible for due diligence purposes.

---

*Every feature described in this README is implemented in the files above. There are no placeholders, mocks, or stubs in the core pipeline.*

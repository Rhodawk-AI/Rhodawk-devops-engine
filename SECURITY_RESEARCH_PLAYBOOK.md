# Rhodawk AI — Ethical Autonomous Vulnerability Research (AVR)
## Operator & Investor Playbook v1.0

> **"The next generation of security tooling does not find known CVEs.  
> It finds the assumptions that developers got wrong — before attackers do."**

---

## The Problem: Why Existing Security Tools Are Obsolete Against Tier-1 Targets

The global security tooling market ($20B+ and growing) is flooded with scanners that search for patterns they already know about. They find Log4Shell *after* it has been CVE-assigned. They find SQL injection via regex. They find secret keys with keyword matching.

Against Tier-1 targets — Linux kernel, Kubernetes, V8, OpenSSL, gRPC — none of this works. The vulnerabilities that command $500K+ bug bounty payouts and change the course of software history are **logic flaws**. They are invisible to pattern-matching tools because they have never occurred before.

The root cause of every novel critical vulnerability is a single cognitive failure: **a developer made an assumption that was true in their mental model but false at the boundary of another component's execution context.**

---

## The Solution: Rhodawk AVR — Semantic Logic Reversal

Rhodawk's Ethical Autonomous Vulnerability Research (AVR) module reconstructs the developer's mental model from their code, then systematically proves where that model breaks.

This is not fuzzing. This is not SAST. This is a reasoning engine.

---

## Architecture: The Five-Stage Ethical Pipeline

Every stage is designed around a single principle: **the human operator is the final authority at every decision point**. The AI accelerates discovery. The human ensures responsibility.

---

### Stage 1 — Semantic Reversal Engine

**What it does:**  
Ingests the target repository alongside any available RFCs, API documentation, or architecture markdown. Instructs Nous Hermes 3 (405B via OpenRouter) to construct a JSON graph of the application's **trust state machine** — the precise path that data travels from "completely untrusted external input" to "fully trusted internal state".

**What it finds:**  
The "Assumption Gap" — the exact line of code where a developer assumed a variable was safe, but the state machine graph proves an edge case can deliver an untrusted value to that point.

**Ethical constraint:**  
This stage is **pure static analysis**. No code is executed. The repository is cloned locally and read. No network calls are made from within the analysis. Every finding is tagged `requires_human_verification: true`.

**Output:**  
A structured JSON state machine graph with scored assumption gaps, ready for operator review.

---

### Stage 2 — Dynamic Harness Compiler

**What it does:**  
For each operator-reviewed assumption gap, Hermes generates a **minimal Python proof-of-concept harness** that exercises the specific code path identified in Stage 1.

The harness speaks the application's own protocol (correct JSON structure, valid OAuth flows, proper gRPC framing) to reach the deep logic — then introduces precisely the edge-case input that the assumption gap predicts will bypass the validation.

**What it is not:**  
This is not a weaponised exploit. The harness is PoC-grade: it demonstrates whether the gap is triggerable in a controlled local environment. It cannot be repurposed for remote attacks without substantial additional development by a human actor.

**Ethical constraint:**  
The harness is displayed to the operator in full before any execution occurs. The operator must read the code and click **"I have reviewed this code"** to proceed. The harness runs in an isolated local sandbox with:
- All secrets and API keys stripped from the environment
- No outbound network connections permitted
- 30-second hard timeout
- Execution against a locally cloned copy of the codebase only

**Output:**  
`TRIGGERED: True / False` — a boolean result that either validates or falsifies the assumption gap hypothesis.

---

### Stage 3 — Vulnerability Chain Synthesiser

**What it does:**  
Advanced vulnerabilities are rarely a single bug. A P5 memory leak combined with a P4 timing discrepancy might chain into a P1 privilege escalation that neither primitive reveals alone.

Hermes maintains a local SQLite database (`chain_memory.sqlite`) of all primitive findings. When sufficient primitives are stored for a target, it reasons about logical chains — the sequence of steps an attacker would need to take to elevate a collection of low-severity primitives into a critical exploit.

**Ethical constraint:**  
All chain proposals are **theoretical documents** tagged `PENDING_HUMAN_REVIEW`. No chain is executed automatically. The operator reads each proposed chain, assesses its plausibility, and approves or rejects it before any further action is taken.

**Output:**  
A structured chain proposal document with severity rating, required conditions, and human verification checklist.

---

### Stage 4 — Isolated Execution Chamber

**What it does:**  
Executes operator-approved harnesses against locally cloned repository code. Returns a concrete boolean result: did the harness trigger the hypothesised behaviour?

The chamber enforces:
- **Offline execution** — the target codebase runs without network access
- **Secret isolation** — all credentials removed from the subprocess environment
- **Time boxing** — hard 30-second limit per harness
- **No persistence** — harness temp files deleted after execution

**What it does not do:**  
It does not execute against live production systems. It does not attempt to achieve real privilege escalation in a production environment. It does not exfiltrate data. The "detonation" is entirely simulated against local code.

**Ethical constraint:**  
This stage is only reachable after the operator has passed through Stage 2's explicit human approval gate.

**Output:**  
Execution result stored as a primitive finding and surfaced in the Rhodawk dashboard.

---

### Stage 5 — Air-Gapped Disclosure Vault

**What it does:**  
Compiles all findings — semantic graph, assumption gap description, harness PoC, chain analysis, execution result — into a structured responsible disclosure dossier.

The dossier is stored locally in encrypted-at-rest format. Nothing leaves the system until the operator takes explicit action.

**The Disclosure Lifecycle:**

| Stage | Actor | Action |
|---|---|---|
| DRAFT | System | Dossier compiled, stored locally |
| PENDING | **Human Operator** | Reads full dossier, independently verifies |
| APPROVED | **Human Operator** | Clicks Approve, enters their name (audit record) |
| DISCLOSED | **Human Operator** | Sends prepared message via maintainer's security channel |
| COORDINATED | Maintainer | Acknowledges, begins remediation |
| PUBLIC | Both | Coordinated public disclosure after 90-day window |

**Ethical constraint:**  
The system never sends anything to an external party. After approval, it generates a disclosure message that the operator sends manually via the maintainer's existing security policy (SECURITY.md, HackerOne, Bugcrowd, direct email). The 90-day responsible disclosure clock is tracked and surfaced in the dashboard.

**GitHub API lockout:**  
When AVR mode is active, all outbound GitHub API write access is severed. The system is a research instrument, not an autonomous actor.

---

## The Adversarial Reviewer (Multi-Model Validation)

Before any finding advances past Stage 2, the Rhodawk Multi-Model Adversarial Reviewer evaluates the logical soundness of the assumption gap. Three models (Qwen, Gemma, Mistral) independently assess whether the proposed gap is:

- Logically coherent given the state machine graph
- Supported by the actual source code evidence
- Not a hallucination or pattern-match false positive

A 2-of-3 consensus is required to advance. This eliminates low-quality findings before they consume expensive harness generation and sandbox compute — and prevents operators from being overwhelmed with noise.

---

## Market Opportunity

| Segment | TAM | Rhodawk Position |
|---|---|---|
| Application security testing | $8.3B (2025) | AI-native SAST replacement |
| Bug bounty & VDP platforms | $1.2B | Autonomous discovery layer |
| Penetration testing services | $4.5B | Augmented researcher tooling |
| Threat intelligence platforms | $6.7B | Novel zero-day feed |

**The inflection point:** Every major tech company (Google, Meta, Apple, Microsoft) now pays six-figure sums for Tier-1 zero-days through internal and external bug bounty programmes. The bottleneck is not payouts — it is the scarcity of researchers capable of finding these vulnerabilities.

Rhodawk does not replace security researchers. It gives them an AI-powered Tier-1 co-researcher that works 24/7, never forgets a primitive finding, and can hold the entire state machine of a 500,000-line codebase in context simultaneously.

---

## Why Ethical Design Is the Moat

Automated exploitation tooling is a commodity. Nation-state actors have had it for decades. The defensible market position is not in building another offensive tool — it is in building the first platform that makes elite vulnerability research **auditable, reproducible, and responsible at scale**.

Every action in Rhodawk AVR is logged with a SHA-256 JSONL audit trail. Every human approval is recorded with the operator's name and timestamp. Every disclosure follows the industry-standard 90-day coordinated timeline.

This is not a constraint on capability. It is the capability. Enterprises, governments, and bug bounty programmes will pay premium rates for a platform whose output is defensible in front of a board of directors, a regulator, or a court.

---

## Technical Stack

| Component | Technology | Role |
|---|---|---|
| Orchestrator LLM | Nous Hermes 3 405B (OpenRouter) | Semantic reasoning, chain synthesis |
| Adversarial Reviewer | Qwen + Gemma + Mistral (2/3 consensus) | Hallucination elimination |
| Static Analysis | Custom `semantic_extractor.py` | Trust state machine extraction |
| Harness Generation | `harness_factory.py` + Hermes | PoC code synthesis |
| Chain Memory | SQLite (`chain_memory.sqlite`) | Longitudinal primitive storage |
| Disclosure Vault | SQLite + local filesystem | Dossier lifecycle management |
| Sandbox Runtime | subprocess + env isolation | Time-limited local execution |
| Audit Trail | SHA-256 JSONL chain | SOC 2 / ISO 27001 evidence |
| UI | Gradio (HuggingFace Spaces) | Human operator dashboard |

---

## Operational Principles (Non-Negotiable)

1. **No automated disclosure.** The human operator is the final authority.
2. **No live system testing.** All PoC execution is against locally cloned code.
3. **No credential use.** Secrets are stripped from all sandbox environments.
4. **90-day timeline.** All disclosures follow coordinated responsible disclosure.
5. **Open-source targets only.** Only repositories with established security policies.
6. **Full audit log.** Every action, approval, and disclosure is recorded.

---

*Rhodawk AI — Building the infrastructure for responsible AI-native security research*  
*Contact: security-research@rhodawk.ai*

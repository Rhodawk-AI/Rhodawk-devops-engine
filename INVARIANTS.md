# EmbodiedOS — System Invariants

> These constraints are permanently in effect. Violation requires explicit operator override
> with a written justification committed to the audit log. No automated process may bypass them.

---

## INV-001: Zero-Day Non-Disclosure

**NEVER auto-submit zero-day findings.**

Every finding classified as P1 / Critical must be placed in
`disclosure_vault` with status `PENDING_HUMAN_APPROVAL`. The system
generates a PoC harness and dossier for the operator's review, but
no disclosure email is sent and no bug-bounty submission is made
until the operator explicitly runs `approve <finding-id>` via Telegram.

*Enforced in:* `embodied/pipelines/repo_hunter.py::_route_zero_day()`,
`disclosure_vault.py`, `embodied/router/unified_gateway.py`

---

## INV-002: Email Scraping Requires Approval

**NEVER scrape maintainer emails without explicit operator approval.**

`disclosure_vault.scrape_developer_emails()` may be called to *collect*
candidate email addresses into the dossier, but those addresses are
presented to the operator in the morning report only. No email is sent
from inside any pipeline function. The operator uses their own email
client to contact maintainers after reviewing the dossier.

*Enforced in:* `embodied/pipelines/repo_hunter.py::_route_zero_day()`

---

## INV-003: 50-Cycle Review Window

**The first 50 bounty cycles are review-only, regardless of `EMBODIED_AUTOSUBMIT`.**

Even if `EMBODIED_AUTOSUBMIT=1` is set, all reports generated during
the first 50 complete bounty cycles go through the human-approval gate.
This gives the operator confidence in the system's report quality before
any autonomous submission occurs.

*Enforced in:* `embodied/pipelines/bounty_hunter.py::scan_bounty_program()`

---

## INV-004: Sandbox Network Allowlist

**The analysis sandbox is network-isolated to an approved allowlist.**

Outbound connections from the sandbox are restricted to:
- `api.github.com` (GitHub REST API)
- `*.hackerone.com` (H1 API)
- `*.bugcrowd.com` (BC API)
- `*.intigriti.com` (Intigriti API)
- `nvd.nist.gov`, `osv.dev` (CVE/OSV feeds)
- `inference.do-ai.run` (DigitalOcean Inference)
- `openrouter.ai` (OpenRouter)
- `*.milvus.io`, `*.zillizcloud.com` (Claude Context vector DB)
- Camofox proxy endpoints (residential proxy for stealth browser)

Target applications under test are accessed via the camofox browser,
which is itself allowlisted. The sandbox cannot initiate arbitrary
internet connections.

*Enforced in:* `architect/sandbox.py`, Dockerfile network rules

---

## INV-005: No Auto-Merge of Evolved Code

**GEPA-evolved skills and DGM code variants are NEVER auto-merged.**

Every output from `embodied/evolution/gepa_engine.py` and
`embodied/evolution/code_evolver.py` is submitted as a GitHub pull request.
A human operator must review the diff and click "Merge" manually. No
GitHub Actions workflow or bot account has merge permissions for these PRs.

*Enforced in:* `embodied/evolution/gepa_engine.py::_open_skill_pr()`,
`embodied/evolution/code_evolver.py::_open_code_pr()`

---

## INV-006: ACTS Gate

**Findings with ACTS score < 72 are never surfaced to the operator.**

The Adversarial Consensus Trust Score is a 100-point composite across
5 dimensions. Sub-threshold findings are written to episodic memory
for future correlation but are not shown in the morning report and
do not trigger Telegram notifications.

*Enforced in:* `architect/godmode_consensus.py`, `architect/nightmode.py`

---

## INV-007: No shell=True in Subprocesses

**All `subprocess.run()` and `subprocess.check_call()` calls must use `shell=False`.**

This prevents shell injection attacks in paths derived from user input
or repository contents. Any exception requires an inline justification
comment reviewed in code review.

*Enforced in:* ruff rule `S603`, mypy strict mode, CI lint gate

---

## INV-008: No Unapproved Any Types

**`Any` types are prohibited without an explicit justification comment.**

Every use of `typing.Any` must be accompanied by a comment explaining
why the type cannot be narrowed and confirming it is safe.

*Enforced in:* mypy `--strict`, ruff `ANN401`

---

## INV-009: Immutable Audit Log

**`audit_logger.py` sessions are append-only and hash-chained.**

No function in the codebase may delete or overwrite an existing
audit log entry. The hash chain allows operators to detect tampering.

*Enforced in:* `audit_logger.py` write path

---

## INV-010: Telegram-Only Operator Interface

**All operator commands go through the Telegram bot.**

The Gradio UI is disabled by default (`EMBODIED_LEGACY_UI=0`).
HTTP endpoints `/openclaw/command` and `/openclaw/status` are
preserved for internal service-to-service use only and must not
be exposed on the public network interface.

*Enforced in:* `app.py` launch gate, Dockerfile port exposure policy

---

## INV-020: Deterministic Exploit Validator Gates All Findings

**No finding with severity CRITICAL or HIGH may be surfaced to the
operator without `ValidationVerdict.CONFIRMED` from
`exploit_validator.py`.**

LLM adversarial review is *advisory only* for CRITICAL / HIGH severity
findings. The deterministic exploit validator — which never calls an LLM —
is the sole authority for promoting a finding to operator-visible status.
Verdicts of `REFUTED`, `PARTIAL`, or `SANDBOX_ERROR` send the finding
back to the synthesiser for re-attempt.

*Enforced in:* `exploit_validator.ExploitValidator.validate`,
`conviction_engine.evaluate_conviction` (criterion 8)

---

## INV-021: SAST Runs Before Every PR Merge

**`sast_orchestrator.full_scan()` must complete without BLOCK-severity
findings before `conviction_engine` evaluates a fix for auto-merge.**

The CodeQL + Semgrep + QRS pipeline replaces the regex / Bandit-only
SAST path. The orchestrator's `full_scan` runs Semgrep first (no build
required) and then CodeQL (deep cross-file dataflow); QRS then
synthesises new queries / rules from the top high-severity findings to
expand coverage. Auto-merge cannot proceed while any CRITICAL / HIGH
finding remains in the diff.

*Enforced in:* `sast_orchestrator.SASTOrchestrator`,
`hermes_orchestrator.SASTScanTool`,
`conviction_engine.evaluate_conviction` (criterion 6)

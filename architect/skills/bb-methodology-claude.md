---
name: bb-methodology-claude
domain: web
triggers:
  languages:    [python, javascript, typescript, php, ruby, java, go]
  frameworks:   [flask, django, fastapi, express, rails, spring, laravel, nextjs]
  asset_types:  [http, https, web, api]
tools:          [burp, ffuf, nuclei, sqlmap, nmap, amass, subfinder, httpx]
severity_focus: [P1, P2, P3]
---

# Bug-Bounty Methodology (imported from claude-bug-bounty)

Adapted from the open-source Claude Bug Bounty plugin
(https://github.com/shuvonsec/claude-bug-bounty, MIT licence).  The original
project ships nine skill domains around an "AI hunting partner" workflow;
this single file distills the practical methodology so it can be injected
into Rhodawk's skill-augmented prompt.

## Phase 1 — Scope & passive recon
- Pull the program scope; resolve every wildcard (`*.example.com`) into a
  concrete list using ``subdomain_enum_mcp.enumerate``.
- Inventory technologies with ``httpx_probe_mcp`` (titles, status, tech
  stack, hashes).
- Pull historical URLs from Wayback / CommonCrawl (``wayback_mcp``); old
  endpoints often outlive their security review.
- Catalogue every JS bundle; grep for hard-coded keys, internal URLs,
  feature flags, GraphQL schema endpoints.

## Phase 2 — Surface mapping
Build a target tree per domain:
``host → endpoint → method → params → auth-context``.

For every leaf, classify the auth context: pre-auth, user, admin,
service-account, OAuth callback. The "pre-auth" leaves are 80% of P1 hits.

## Phase 3 — Triage by bug class
Walk the OWASP-API top 10 plus the additional Web2 vuln classes from
``architect/skills/web-security-advanced.md``:

1. Broken object-level authorization (BOLA / IDOR).
2. Broken authentication.
3. Excessive data exposure.
4. Lack of resources & rate-limiting.
5. Broken function-level authorization.
6. Mass assignment.
7. Security misconfiguration.
8. Injection (SQLi / NoSQLi / SSTI / SSRF).
9. Improper assets management.
10. Insufficient logging & monitoring.

For each candidate finding capture: **request, response, repro steps,
fix suggestion, impact**.

## Phase 4 — Validation gate
Cross-confirm before submission:

- Confirm reproducibility from a fresh browser profile (no cached creds).
- Capture both the vulnerable and the (proof) fixed-state response.
- Run the vulnerability_database_mcp to make sure it isn't already a
  known issue or a duplicate of a public report.
- Score CVSS v3.1; reject submissions with < 4.0 score unless the program
  explicitly accepts low-severity.

## Phase 5 — Report
Use the HackerOne template in ``bounty_gateway.py``.  Include:
title (≤ 80 chars), summary, steps to reproduce (numbered), impact,
recommendations, references (CWE / CVE), and the PoC harness.

## Tone
Professional, terse, no exaggeration. Triage teams scan dozens of reports
a day; the report that wins the bounty is the one that respects their
time first.

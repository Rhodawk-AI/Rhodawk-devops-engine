---
name: bug-bounty-reference-index
domain: knowledge
triggers:
  languages:    []
  frameworks:   []
  asset_types:  [web, api, oauth, saml, http]
tools:          []
severity_focus: [P1, P2, P3]
---

# Bug-Bounty Reference Index

Curated index of canonical public writeups, mirrored from
``ngalongc/bug-bounty-reference`` (open licence, archive of disclosed
findings).  This skill is loaded by the agent as a "look-up sheet" — when a
candidate finding matches one of the categories below, fetch the original
writeup via ``fetch-docs`` and study the exploitation chain before
submitting.

## XSS (cross-site scripting)
- Sleeping stored XSS — Google ($5,000) — `it-securityguard.com`.
- Self-XSS → good XSS — Uber, AirBnb, Twitter (multiple writeups).
- Stored XSS via PNG / image upload — Facebook (`whitton.io`).
- DOM-XSS via Marketo Forms postMessage — HackerOne.
- Polymorphic image XSS — Google Scholar (`doyensec.com`).

## SQLi / NoSQLi
- Time-based blind SQLi via header — Uber.
- Boolean-based SQLi over GraphQL — multiple.
- MongoDB injection via JSON body — GitHub Security Lab writeups.

## SSRF (server-side request forgery)
- Cloud metadata SSRF — AWS (`169.254.169.254`) — countless writeups.
- Webhook SSRF reaching Redis — Shopify ($25K).
- DNS-rebinding SSRF — modern variants used in 2024 against internal
  staging clusters.

## RCE
- Image-Tragick (ImageMagick).
- Node.js prototype-pollution → RCE.
- Insecure deserialisation in Java (Jackson, FastJson, ysoserial chains).
- Pickle / dill in ML inference endpoints.

## CSRF
- Login CSRF in OAuth callback (state missing).
- POST-based CSRF on state-changing GraphQL mutations.

## IDOR / BOLA
- Sequential UUIDs on internal admin APIs.
- GraphQL `node(id:)` lookup ignoring authorization.
- Mobile-app-only endpoints reachable via standard HTTP.

## Authentication / OAuth bypass
- ``state`` parameter not validated → account takeover.
- ``redirect_uri`` open-redirect with subpath.
- Microsoft / Google OAuth wildcard tenant abuse.
- Magic-link / passwordless flow re-use.

## Race conditions
- Coupon double-spend (1 second window).
- Wallet balance race during withdrawal.
- HTTP/2 single-packet attack (Smith-Hill technique).

## Business-logic flaws
- Negative-amount transfer.
- Skip-step in a multi-step KYC / 2FA flow.
- Coupon-stacking, referral-loop infinite credit.

## Email / header injection
- Host header injection → password-reset poisoning.
- CRLF injection in `Location` header.

## Money-stealing
- Currency rounding abuse.
- Front-running on price updates inside payment flows.

## Miscellaneous
- Subdomain takeover (Heroku, Azure, Fastly, S3).
- Source-map exposure → service tokens.
- Internal Sentry / Grafana panels indexed publicly.

## How to use this skill
1. Match your candidate to a category above.
2. Pull the original writeup with the ``fetch-docs`` MCP for the URL listed
   in ``ngalongc/bug-bounty-reference``.
3. Extract the **primitive** (what made the bug exploitable), not just the
   target.  Replicate the primitive against the current target.
4. If the program already paid for a near-identical bug to another
   researcher, expect "duplicate" — pivot to a variant.

## Source
Ed Foudil / Github user ``ngalongc`` —
https://github.com/ngalongc/bug-bounty-reference (creative-commons style
collection of public writeups).  The full link list is preserved in
``knowledge_rag.py`` after you run ``ingest_text_file()`` on the upstream
README.

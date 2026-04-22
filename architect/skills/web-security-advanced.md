---
name: web-security-advanced
domain: web
triggers:
  languages:    [python, javascript, typescript, php, ruby, java, go]
  frameworks:   [flask, django, fastapi, express, rails, spring, laravel, nextjs]
  asset_types:  [http, https, web]
tools:          [burp, ffuf, nuclei, sqlmap, browser-agent-mcp]
severity_focus: [P1, P2]
---

# Advanced Web Security

## When to load
Any HTTP(S) target, web application, or framework-based service.  Drives 60 %
of real bug-bounty payouts.

## Attack surface checklist
1. **Auth** — login, signup, password-reset, OAuth callback, MFA enrol/disable,
   JWT (`alg=none`, key confusion, kid path traversal), session fixation.
2. **Authorization** — IDOR (sequential ids, predictable UUIDs, GraphQL
   `node(id:)`), missing function-level checks, role tampering via JWT or
   client-side flags.
3. **Server-side** — SSRF (full + blind, DNS rebinding, gopher://), XXE, SSTI
   (Jinja2/Twig/Velocity/Freemarker — confirm with `{{7*7}}` then escalate),
   path traversal, file inclusion, deserialisation (pickle/yaml/jackson/PHP).
4. **Injection** — SQLi (boolean, time-based, OOB DNS), NoSQL injection,
   LDAP injection, command injection (always test `;`, `|`, ``backticks``,
   `$()`, newline-bypass).
5. **Client-side** — DOM-XSS via `innerHTML`, postMessage origin checks,
   prototype pollution, ClickJacking on sensitive endpoints, CSRF on state-
   changing routes lacking CSRF token.
6. **Race / logic** — TOCTOU on balance debit, coupon stacking, parallel
   account-merge, registration of conflicting usernames.
7. **Headers / config** — CORS `*` with credentials, missing CSP, dangerous
   `X-Forwarded-*` trust, open redirects, cache-key confusion.

## Procedure
1. Burp baseline crawl → import HAR.
2. Run `nuclei -severity high,critical -tags cve,rce,xxe,ssrf,exposure`.
3. For every authenticated endpoint, swap session cookies horizontally to test
   IDOR / BFLA.
4. For every input that lands in a server-rendered template, try the SSTI
   primer.
5. For every URL parameter that fetches a remote resource, attempt SSRF to
   `169.254.169.254`, `127.0.0.1:22`, `file://`, `gopher://`.
6. Use `browser-agent-mcp` to drive the live app for any flow that requires
   real session state.

## Reporting
ACTS ≥ 0.72.  Always include: reproduction steps, request/response, impact
narrative, suggested fix.  No active exploitation outside scope.

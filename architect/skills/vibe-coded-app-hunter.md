---
name: vibe-coded-app-hunter
domain: web
priority: critical
triggers:
  languages:    [javascript, typescript, python, go, ruby, php]
  frameworks:   [nextjs, react, vue, svelte, express, fastapi, flask, django, rails, supabase, firebase]
  asset_types:  [http, https, web, api, vibe-coded, ai-generated, cursor, v0, lovable, bolt, replit]
tools:          [burp, ffuf, nuclei, sqlmap, jwt-tool, gitleaks, npm-audit, semgrep]
severity_focus: [P1, P2]
---

# Vibe-Coded App Hunter — The 24-Hour Hit-List

## Why this skill is loaded first
Apps shipped from Cursor / v0 / Lovable / Bolt / Replit / Windsurf inherit a
predictable set of mistakes the AI tooling makes by default. Auditing the
**same 20 patterns** against every freshly launched product gives the
fastest path from "discover target" → "valid P1/P2 report".

The market is enormous — every YC batch, every Indie-Hackers launch,
every Product-Hunt #1 is a candidate. A monthly $10/seat subscription
becomes a no-brainer for any founder who shipped without a security
review.

## The 20 Hit-List (run **every** check on **every** target, in this order)

### Tier 0 — Public-surface secrets (5 minutes)
1. **Hardcoded API keys in frontend bundles**
   - Pull every `*.js` from the JS bundle and grep for `sk_live_`, `pk_`,
     `AIza`, `AKIA`, `ghp_`, `xoxb-`, `eyJ...` (JWT), `Bearer `,
     `firebase`, `supabase.co`, `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`.
   - `gitleaks detect --no-git --source <bundles>` on the dumped assets.
   - Treat every match as P1 until proven otherwise.
8. **`.env` committed to git, even once**
   - For OSS / GitHub-Pages / Vercel-public targets: `git log --all
     --full-history -- .env`, `--source-map` lookups, look for `.env.example`
     that secretly contains real values.

### Tier 1 — Authentication primitives (15 minutes)
2. **No rate-limit on `/login`, `/signup`, `/forgot-password`, `/2fa`**
   - Fire 50 requests in 5 seconds; if 200/302 throughout, file P2.
5. **JWT in `localStorage` or `sessionStorage`**
   - Open devtools → Application → Storage. If you see a JWT, it is
     stealable by any XSS. Combine with #1 to escalate.
6. **Predictable / leaked JWT secret**
   - Decode header: `alg=none` accepted? File P1.
   - Try `jwt-tool -V -hc <token> -d /usr/share/wordlists/jwt.secrets.list`.
     Common leakage: `secret`, `change-me`, `your-256-bit-secret`,
     `supersecret`, project name, repo name.
12. **Tokens with no expiry / no refresh rotation**
    - Decode `exp`. If missing or > 1 year → P2.
18. **Sessions not invalidated on logout**
    - Save token, click logout, replay token. If still 200 → P2.

### Tier 2 — Authorisation / IDOR (20 minutes)
7. **Admin routes guarded only in the React Router / Vue Router**
   - Use the network tab to find admin endpoints, hit them directly with
     a normal user JWT. P1 if 200.
13. **Auth middleware missing on internal routes**
   - Walk every endpoint in `_next/data/`, every Next.js Server Action
     URL, every tRPC endpoint, every Supabase RLS policy. AI-generated
     code consistently forgets the deeper paths.
16. **IDOR on resource endpoints**
   - For every `/api/<resource>/<id>` discovered, swap `id` for an
     adjacent value (`+1`, `-1`, GUID brute, `/me` → `/admin`).
   - Especially aggressive on Supabase `eq.*`, Firestore document IDs.

### Tier 3 — Injection (20 minutes)
3. **String-concat SQL queries**
   - Test every `id`, `q`, `search`, `filter`, `sort`, `order`,
     `userId`, `email` param with `'`, `"`, `; --`, `OR 1=1`, time-based
     `pg_sleep(3)`, `WAITFOR DELAY '0:0:3'`.
   - For Supabase / PostgREST: try `?id=eq.1 OR 1=1`.
10. **File-upload — no MIME validation server-side**
    - Upload `.html` with `Content-Type: image/png`, then load it from
      the public URL. If JS executes → stored XSS. Upload `.svg`, `.htm`,
      `.phtml`, `.aspx`, `.jsp` and watch where they land.
20. **Open redirects in `?next=`, `?return_to=`, `?redirect=`, `?url=`**
    - Try `https://attacker.com`, `//attacker.com`,
      `https://target.com.attacker.com`, `javascript:alert(1)`.

### Tier 4 — Crypto & infra (15 minutes)
11. **Passwords hashed with MD5 / SHA1 / no salt**
    - If a leak / breach surface exists, check `Have-I-Been-Pwned`-style
      hash format. Anything < bcrypt cost 10 / argon2id is P2.
4. **CORS `*` with credentials**
    - `curl -H "Origin: https://evil.com" -I https://target/api/me` → if
      `Access-Control-Allow-Origin: *` AND `Allow-Credentials: true` → P1.
9. **Verbose error responses (stack traces, table names, file paths)**
    - Send malformed JSON, missing required fields, oversized payloads;
      record every leaked internal detail.
17. **No HTTPS enforcement / HSTS missing**
    - `curl -I http://target/`. If 200 (no 308 to https) → P2.
14. **App running as root (when remotely observable)**
    - File-upload + path-traversal → read `/proc/self/status` → check
      `Uid:`. Bonus: `/etc/passwd`, `/root/.bash_history`.
15. **Database port directly internet-exposed**
    - Shodan: `org:"<target-org>" port:5432`, `port:27017`,
      `port:6379`, `port:9200`, `port:8086`. Confirm anonymous read.
19. **`npm audit` criticals on the deployed bundle**
    - Pull `package-lock.json` (often shipped to `/_next/static/`),
      run `npm audit --json` against it, file each critical that lands
      in the runtime path.

## Reporting template (paste into HackerOne)

```
Title:   <vuln class> — <impact in one line> on <subdomain>
Severity: P1|P2 (CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H)
Affected: <url> · <endpoint> · <param>
Reproduction:
  1. <one-line steps>
  2. ...
Impact: <what the attacker gains in money / data / users>
Fix:    <one-paragraph remediation, cite CWE>
PoC:    attached HAR + curl one-liner.
```

## How the Rhodawk pipeline uses this skill
- ``oss_guardian.OSSGuardian`` and ``architect.nightmode._phase_hunt`` load
  this skill first when the target profile contains an HTTP asset; it
  becomes the highest-priority checklist regardless of other matches.
- Each numbered item maps to a Hermes tool call:
  `recon → ScopeParse → JS bundle dump → secret scan → endpoint walk →
  IDOR fuzz → injection fuzz → upload tests → CORS probe → JWT replay →
  Shodan exposure check`.
- A finding from this checklist auto-fills the report template above and
  routes through ``embodied_bridge.emit_finding`` for operator approval.

## Ethical constraints (non-negotiable)
- Operate only against assets in scope (HackerOne / Bugcrowd /
  Intigriti / explicit invitation from founder).
- 90-day coordinated disclosure timer starts on first contact.
- No data exfiltration beyond minimum required to prove impact.
- Never test against production payment, customer messaging, or
  identity providers without explicit written consent.

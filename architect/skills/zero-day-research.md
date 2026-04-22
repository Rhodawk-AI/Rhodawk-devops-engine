---
name: zero-day-research
domain: methodology
triggers:
  languages:    [c, cpp, rust, go, python, java, javascript, kotlin]
  frameworks:   []
  asset_types:  [oss, repo, library, framework, runtime]
tools:          [joern, codeql, semgrep, afl, libfuzzer, klee, angr]
severity_focus: [P1, P2]
---

# Zero-Day Research Methodology

## When to load
Any deep-dive on an open-source library / runtime / kernel where the goal
is *new* CVE generation, not known-bug confirmation.

## Repeatable methodology

### 1. CVE archaeology (cheap, high-yield)
- Pull the project's last 24 months of CVEs from NVD + GitHub Advisory.
- Classify each by CWE, file, and root-cause primitive.
- Identify the **bug class concentration** — almost every project has one
  or two recurring failure modes (e.g. nginx → integer overflow on header
  parsing; curl → state-machine confusion in protocol handlers).

### 2. Variant hunting (the actual exploit)
- For each historical CVE, write a Semgrep / CodeQL query that matches the
  *pattern*, not just the patched line.
- Run the pattern across the whole repo. Anything unpatched that matches is
  a high-prior candidate.
- Use Joern / CodeQL CPG to follow data flow from sinks back to sources for
  every candidate.

### 3. Differential fuzzing
- Pick a sibling implementation (BoringSSL ↔ OpenSSL, Node vs Bun vs Deno).
- Feed the same corpus to both, diff the outputs / crashes / timing.
- Differences are bugs in *one* of them; usually exploitable in the slower
  / older one.

### 4. State-machine review
- Manually annotate every state transition in protocol parsers (TLS, HTTP/2,
  QUIC, WebSocket, OAuth, SAML).
- Look for: skipped states, reusable nonces, pre-authentication code paths,
  wildcard transitions, error states that grant access.

### 5. Build & sanitiser farm
- Always build with `-fsanitize=address,undefined,thread`.
- Replay the project's own corpus + AFL++ runs ≥ 24h.
- Triage every sanitizer hit; many are CVEs the project hasn't noticed.

### 6. The "what would the patch look like?" test
- For every candidate bug, draft the patch *first*. If the patch is one
  line, you have found a real bug. If your patch breaks tests, you have
  found a feature.

## Scoring (decides effort)
- Critical surface (kernel, parser, crypto, network) × variant of an old
  CVE × no public proof yet = drop everything else and chase it.
- Non-public surface (tests, examples, docs) × novel pattern = log and
  move on.

## Disclosure
File via `disclosure_vault.intake()`. 90-day timer. Never publish PoC
before the vendor patches.

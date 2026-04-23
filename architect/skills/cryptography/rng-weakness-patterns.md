---
name: rng-weakness-patterns
domain: cryptography
triggers:
  languages: [any]
severity_focus: [P1, P2, P3]
---

# rng-weakness-patterns

Insecure RNG (Math.random, rand()), seeded with time(0)/PID, predictable session IDs, JWT secret derivation from PRNG, language-specific gotchas.

## Detection checklist
- enumerate exposure
- match canonical sinks
- confirm reproducibility
- map to CWE / OWASP / CVSS

## Exploitation primitives
- reproduce in lab
- minimise the PoC
- assess blast radius

## Reporting fingerprint
- include affected version range
- include suggested fix snippet
- include CVSS 3.1 vector

---
name: timing-side-channels
domain: cryptography
triggers:
  languages: [any]
severity_focus: [P1, P2, P3]
---

# timing-side-channels

Non-constant-time string comparison for tokens/HMACs, branch-on-secret, table-lookup AES, RSA/ECC scalar mults; Lucky13, Bleichenbacher.

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

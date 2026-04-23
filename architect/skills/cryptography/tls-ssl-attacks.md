---
name: tls-ssl-attacks
domain: cryptography
triggers:
  languages: [any]
severity_focus: [P1, P2, P3]
---

# tls-ssl-attacks

BEAST/CRIME/BREACH/Lucky13/POODLE history; modern: weak cipher suites, missing HSTS preload, OCSP stapling gaps, mTLS misconfig, certificate pinning gaps.

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

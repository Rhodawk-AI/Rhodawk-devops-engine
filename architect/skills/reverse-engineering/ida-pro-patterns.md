---
name: ida-pro-patterns
domain: reverse-engineering
triggers:
  languages: [any]
severity_focus: [P1, P2, P3]
---

# ida-pro-patterns

Conceptual workflow (commercial tool): Hex-Rays decompile, structures, FLIRT signatures, BinDiff for patch analysis.

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

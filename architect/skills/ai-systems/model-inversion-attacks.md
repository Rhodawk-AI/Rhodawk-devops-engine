---
name: model-inversion-attacks
domain: ai-systems
triggers:
  languages: [any]
severity_focus: [P1, P2, P3]
---

# model-inversion-attacks

Membership inference, training-data extraction (verbatim recall), gradient leakage, attribute inference.

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

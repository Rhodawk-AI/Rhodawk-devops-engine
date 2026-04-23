---
name: autosar-architecture-security
domain: automotive
triggers:
  languages: [automotive]
severity_focus: [P1, P2, P3]
---

# autosar-architecture-security

AUTOSAR Classic vs Adaptive: SecOC config gaps, IPsec for SOME/IP, OS partition isolation, BSW component trust boundaries.

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

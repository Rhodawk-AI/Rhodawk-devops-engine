---
name: arinc429-security
domain: aviation
triggers:
  languages: [aviation]
severity_focus: [P1, P2, P3]
---

# arinc429-security

ARINC-429 unidirectional bus: lack of auth, source-spoofing on shared bus, label collision, gateway leaks to passenger network.

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

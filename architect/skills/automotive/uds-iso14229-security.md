---
name: uds-iso14229-security
domain: automotive
triggers:
  languages: [automotive]
severity_focus: [P1, P2, P3]
---

# uds-iso14229-security

UDS services: Security Access (0x27) seed/key brute, Routine Control abuse, Read/Write Memory unprotected, weak diagnostic-session auth.

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

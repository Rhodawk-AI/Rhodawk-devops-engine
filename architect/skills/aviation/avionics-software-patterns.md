---
name: avionics-software-patterns
domain: aviation
triggers:
  languages: [aviation]
severity_focus: [P1, P2, P3]
---

# avionics-software-patterns

ARINC-653 partition leakage, IMA module isolation, RTCA DO-326A airworthiness security process, EASA Part-IS adoption.

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

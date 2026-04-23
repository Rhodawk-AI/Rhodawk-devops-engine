---
name: can-bus-attacks
domain: automotive
triggers:
  languages: [automotive]
severity_focus: [P1, P2, P3]
---

# can-bus-attacks

CAN: arbitration ID spoofing, DoS via dominant flooding, ECU reflashing, gateway misconfig allowing OBD-II -> CAN-A jumps.

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

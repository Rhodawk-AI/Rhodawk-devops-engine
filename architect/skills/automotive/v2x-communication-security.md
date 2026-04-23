---
name: v2x-communication-security
domain: automotive
triggers:
  languages: [automotive]
severity_focus: [P1, P2, P3]
---

# v2x-communication-security

V2X (DSRC/C-V2X): pseudonym certificate misuse, replay of BSMs, misbehaviour detection bypass, PKI revocation latency.

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

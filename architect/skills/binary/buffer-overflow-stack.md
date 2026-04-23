---
name: buffer-overflow-stack
domain: binary
triggers:
  languages: [c, cpp]
severity_focus: [P1, P2, P3]
---

# buffer-overflow-stack

Classic stack BO: detection patterns (strcpy/gets/sprintf/scanf %s), defences (canary/NX/ASLR/PIE), bypass primitives (info leak → ROP, ret2libc, ret2csu, partial overwrites).

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

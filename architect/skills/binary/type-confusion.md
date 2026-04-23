---
name: type-confusion
domain: binary
triggers:
  languages: [c, cpp]
severity_focus: [P1, P2, P3]
---

# type-confusion

C++ vtable confusion via reinterpret_cast, JIT engine type confusion (V8/SpiderMonkey), Java/.NET unsafe-cast in deserialization.

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

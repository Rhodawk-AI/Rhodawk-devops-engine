---
name: integer-overflow-underflow
domain: binary
triggers:
  languages: [c, cpp, go, rust]
severity_focus: [P1, P2, P3]
---

# integer-overflow-underflow

Integer wraps lead to undersized allocations → BOF. Sinks: malloc(n*size), alloca, length checks. Mitigations: __builtin_*_overflow, checked_arith.

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

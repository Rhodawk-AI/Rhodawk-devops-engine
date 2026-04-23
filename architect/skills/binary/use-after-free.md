---
name: use-after-free
domain: binary
triggers:
  languages: [c, cpp, rust-unsafe]
severity_focus: [P1, P2, P3]
---

# use-after-free

UAF: dangling pointer reuse, vtable hijack, type confusion via heap reuse. Detection via ASan/UBSan and KASAN for kernel. Patch patterns: smart pointers, IDs over pointers.

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

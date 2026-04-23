---
name: rust-unsafe-patterns
domain: languages
triggers:
  languages: [rust]
severity_focus: [P1, P2, P3]
---

# rust-unsafe-patterns

Rust unsafe blocks: lifetime extension, transmute, raw-pointer arithmetic, FFI boundary mistakes, Send/Sync soundness bugs (Cell/UnsafeCell). Detection: cargo-geiger, MIRI.

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

---
name: ghidra-workflow
domain: reverse-engineering
triggers:
  languages: [any]
severity_focus: [P1, P2, P3]
---

# ghidra-workflow

Ghidra import -> analyse all -> entry point ID -> struct recovery -> decompile -> cross-ref vulnerable libc calls -> annotate. Headless mode for batch.

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

---
name: binary-diffing-patch-analysis
domain: reverse-engineering
triggers:
  languages: [any]
severity_focus: [P1, P2, P3]
---

# binary-diffing-patch-analysis

Patch diff workflow: BinDiff/Diaphora/BinExport, identify changed funcs, locate fix -> infer vuln (1-day exploit dev). Used for silent security patches (CAD).

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

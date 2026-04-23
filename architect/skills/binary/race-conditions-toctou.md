---
name: race-conditions-toctou
domain: binary
triggers:
  languages: [any]
severity_focus: [P1, P2, P3]
---

# race-conditions-toctou

TOCTOU file-system races (access/open), shared-state races in async runtimes, double-fetch in syscalls, signal handler races.

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

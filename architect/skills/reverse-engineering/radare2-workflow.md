---
name: radare2-workflow
domain: reverse-engineering
triggers:
  languages: [any]
severity_focus: [P1, P2, P3]
---

# radare2-workflow

r2 cycle: aaa, afl, pdf @ main, axt @ sym.imp.system, /R for ROP. Useful: r2pipe, retdec integration, esil for symbolic-ish exec.

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

---
name: javascript-node-security
domain: languages
triggers:
  languages: [javascript, typescript, node]
severity_focus: [P1, P2, P3]
---

# javascript-node-security

Node sinks: child_process.exec, vm/vm2 escape gadgets, eval/Function, require() with user path, fs operations on attacker paths, prototype pollution gadgets.

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

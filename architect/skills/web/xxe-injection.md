---
name: xxe-injection
domain: web
triggers:
  languages: [any]
severity_focus: [P1, P2, P3]
---

# xxe-injection

XXE: enabled DTD external entities, file:// reads, OOB exfil via parameter entities + http://, billion-laughs DoS, XInclude variants, SVG-based XXE in image parsers.

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

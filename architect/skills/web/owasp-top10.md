---
name: owasp-top10
domain: web
triggers:
  languages: [python, javascript, typescript, go, ruby, php, java]
severity_focus: [P1, P2, P3]
---

# owasp-top10

OWASP Top 10 (2021) cheat-sheet for prioritised triage. Sinks: SQLi, broken auth, sensitive data exposure, XXE, broken access control, security misconfig, XSS, insecure deserialization, vulnerable components, insufficient logging.

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

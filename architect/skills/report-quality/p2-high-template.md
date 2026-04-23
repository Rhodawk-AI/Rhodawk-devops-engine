---
name: p2-high-template
domain: report-quality
triggers:
  languages: [any]
severity_focus: [P1, P2, P3]
---

# p2-high-template

P2 template: same skeleton as P1 but emphasise scenario realism (auth-required? customer-data?). Avoid CVSS inflation - triagers downgrade aggressively.

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

---
name: p1-critical-template
domain: report-quality
triggers:
  languages: [any]
severity_focus: [P1, P2, P3]
---

# p1-critical-template

P1 report skeleton: 1 sentence summary, business impact in $ or compliance terms, full reproduction with curl, evidence (screenshots/HAR), CVSS 3.1 vector, suggested fix patch.

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

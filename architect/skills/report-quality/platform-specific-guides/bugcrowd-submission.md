---
name: bugcrowd-submission
domain: report-quality
triggers:
  languages: [any]
severity_focus: [P1, P2, P3]
---

# bugcrowd-submission

Bugcrowd VRT taxonomy mapping, target classification, P1/P2 floors per program, mandatory PoC URL for web.

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

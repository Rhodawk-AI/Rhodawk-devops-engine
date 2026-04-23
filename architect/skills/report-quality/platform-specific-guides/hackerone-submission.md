---
name: hackerone-submission
domain: report-quality
triggers:
  languages: [any]
severity_focus: [P1, P2, P3]
---

# hackerone-submission

H1 specifics: weakness taxonomy field, asset selection from program scope, CVSS calculator embedded, attachments preferred over inline base64, do not duplicate-spam.

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

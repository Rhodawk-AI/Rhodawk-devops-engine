---
name: prompt-injection-indirect
domain: ai-systems
triggers:
  languages: [any]
severity_focus: [P1, P2, P3]
---

# prompt-injection-indirect

Indirect PI from retrieved docs / web pages / emails. Test corpus: hidden instructions in HTML comments, base64 payloads, unicode tag chars (U+E0000).

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

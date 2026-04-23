---
name: prompt-injection-direct
domain: ai-systems
triggers:
  languages: [any]
severity_focus: [P1, P2, P3]
---

# prompt-injection-direct

Direct PI: 'ignore previous instructions', role-swap, system-prompt extraction, jailbreaks via translation/obfuscation. Defenses: structured boundaries, allow-listed tools, output filters.

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

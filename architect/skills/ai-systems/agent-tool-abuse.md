---
name: agent-tool-abuse
domain: ai-systems
triggers:
  languages: [any]
severity_focus: [P1, P2, P3]
---

# agent-tool-abuse

Function-calling abuse: arg smuggling, recursive tool calls, cost-DoS via tool loops, exfil via outbound HTTP tools, prompt-injected tool selection.

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

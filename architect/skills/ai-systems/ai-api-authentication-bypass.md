---
name: ai-api-authentication-bypass
domain: ai-systems
triggers:
  languages: [any]
severity_focus: [P1, P2, P3]
---

# ai-api-authentication-bypass

OpenAI-compatible APIs without auth, model-name spoofing, key smuggling via headers, free-tier abuse via account farms, IDOR on threads/runs.

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

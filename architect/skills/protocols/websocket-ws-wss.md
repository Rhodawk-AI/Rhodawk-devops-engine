---
name: websocket-ws-wss
domain: protocols
triggers:
  languages: [any]
severity_focus: [P1, P2, P3]
---

# websocket-ws-wss

See web/websocket-security; protocol-level: missing TLS, mixed content, ping/pong DoS, lack of per-message auth.

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

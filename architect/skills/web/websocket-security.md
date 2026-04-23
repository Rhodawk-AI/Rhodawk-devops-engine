---
name: websocket-security
domain: web
triggers:
  languages: [javascript, typescript, python, go]
severity_focus: [P1, P2, P3]
---

# websocket-security

WebSocket hardening: missing Origin check, cross-site WebSocket hijacking (CSWSH), message smuggling, lack of msg-level auth, plaintext over ws://, slow-loris-style DoS via half-open frames, sub-protocol confusion.

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

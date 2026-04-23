---
name: grpc-security
domain: protocols
triggers:
  languages: [any]
severity_focus: [P1, P2, P3]
---

# grpc-security

gRPC: reflection without auth, message-size DoS, no rate limiting on streams, mTLS cert validation gaps, JWT-in-metadata mistakes.

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

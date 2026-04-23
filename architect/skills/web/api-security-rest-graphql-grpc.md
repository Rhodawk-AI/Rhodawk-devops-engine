---
name: api-security-rest-graphql-grpc
domain: web
triggers:
  languages: [any]
severity_focus: [P1, P2, P3]
---

# api-security-rest-graphql-grpc

REST: BOLA/IDOR, mass assignment, broken function-level auth, rate-limit bypass via headers. GraphQL: see graphql-security. gRPC: missing auth on reflection, message-size DoS, mTLS misconfig.

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

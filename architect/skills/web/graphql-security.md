---
name: graphql-security
domain: web
triggers:
  languages: [javascript, typescript, python, go, ruby]
severity_focus: [P1, P2, P3]
---

# graphql-security

GraphQL attack surface: introspection enabled, batching abuse, depth/breadth DoS, alias-based rate-limit bypass, mutation injection, JWT in custom directives, SSRF via @stream/@defer, broken object-level auth in resolvers.

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

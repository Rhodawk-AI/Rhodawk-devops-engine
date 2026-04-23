---
name: web-cache-poisoning
domain: web
triggers:
  languages: [any]
severity_focus: [P1, P2, P3]
---

# web-cache-poisoning

Unkeyed inputs (X-Forwarded-Host, X-Original-URL), fat GET, cache deception via path confusion, parameter cloaking, cache key normalisation differences between CDN and origin.

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

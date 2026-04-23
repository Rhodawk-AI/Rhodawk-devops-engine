---
name: ssrf-advanced
domain: web
triggers:
  languages: [any]
severity_focus: [P1, P2, P3]
---

# ssrf-advanced

SSRF deep dive: 169.254.169.254 metadata, DNS rebinding, gopher://, IPv6 localhost, decimal/octal IP encoding, blind SSRF via timing/redirects, PDF renderers, image loaders, webhook validators.

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

---
name: http-request-smuggling
domain: web
triggers:
  languages: [any]
severity_focus: [P1, P2, P3]
---

# http-request-smuggling

CL.TE / TE.CL / TE.TE smuggling chains, HTTP/2 downgrade smuggling, header normalisation between front-end CDNs (Cloudflare/Akamai/Fastly) and origin (nginx/apache/node).

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

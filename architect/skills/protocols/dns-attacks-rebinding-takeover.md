---
name: dns-attacks-rebinding-takeover
domain: protocols
triggers:
  languages: [any]
severity_focus: [P1, P2, P3]
---

# dns-attacks-rebinding-takeover

DNS rebinding (multi-A TTL=0), subdomain takeover (CNAME to dangling SaaS), zone walking, NS delegation hijack, DoH abuse for C2.

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

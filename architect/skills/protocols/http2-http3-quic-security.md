---
name: http2-http3-quic-security
domain: protocols
triggers:
  languages: [any]
severity_focus: [P1, P2, P3]
---

# http2-http3-quic-security

HTTP/2 rapid reset (CVE-2023-44487), HPACK bombs, HTTP/3 connection migration auth gaps, 0-RTT replay.

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

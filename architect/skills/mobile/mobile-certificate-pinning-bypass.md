---
name: mobile-certificate-pinning-bypass
domain: mobile
triggers:
  languages: [mobile]
severity_focus: [P1, P2, P3]
---

# mobile-certificate-pinning-bypass

Pinning patterns (cert/SPKI/CA), Frida script catalogue, OkHttp CertificatePinner internals, iOS NSURLSession evaluateForChallenge.

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

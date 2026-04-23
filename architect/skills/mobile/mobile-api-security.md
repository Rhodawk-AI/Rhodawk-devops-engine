---
name: mobile-api-security
domain: mobile
triggers:
  languages: [mobile]
severity_focus: [P1, P2, P3]
---

# mobile-api-security

Mobile-backend: cert pinning bypass for testing (Frida), mTLS, attestation (Play Integrity / DeviceCheck), JWT in shared prefs/keychain.

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

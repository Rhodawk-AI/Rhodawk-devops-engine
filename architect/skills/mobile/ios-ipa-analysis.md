---
name: ios-ipa-analysis
domain: mobile
triggers:
  languages: [ios]
severity_focus: [P1, P2, P3]
---

# ios-ipa-analysis

IPA static: class-dump + Hopper, App Transport Security exemptions, Keychain ACL, URL scheme hijack, Universal Links validation, biometric auth bypass.

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

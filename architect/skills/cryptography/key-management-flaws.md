---
name: key-management-flaws
domain: cryptography
triggers:
  languages: [any]
severity_focus: [P1, P2, P3]
---

# key-management-flaws

Hard-coded keys, keys in env vars without rotation, missing key separation (sign vs encrypt), KMS misuse, JWT signing-key reuse across environments.

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

---
name: post-quantum-migration-risks
domain: cryptography
triggers:
  languages: [any]
severity_focus: [P1, P2, P3]
---

# post-quantum-migration-risks

Hybrid KEM rollout pitfalls (X25519+Kyber), parameter confusion, downgrade vectors, harvest-now-decrypt-later threat model. NIST PQC suite status.

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

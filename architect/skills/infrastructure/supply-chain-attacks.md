---
name: supply-chain-attacks
domain: infrastructure
triggers:
  languages: [any]
severity_focus: [P1, P2, P3]
---

# supply-chain-attacks

Typo-squatting, dep confusion, malicious post-install scripts, namespace hijack, build-tool plugin compromise, signed-attestation gaps (SLSA).

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

---
name: crypto-implementation-flaws
domain: cryptography
triggers:
  languages: [any]
severity_focus: [P1, P2, P3]
---

# crypto-implementation-flaws

ECB instead of GCM, IV reuse with CTR/GCM, key reuse across protocols, lack of authenticated encryption, padding oracle (CBC), AES-NI side channels, Cryptopals classics.

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

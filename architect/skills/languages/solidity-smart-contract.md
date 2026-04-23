---
name: solidity-smart-contract
domain: languages
triggers:
  languages: [solidity]
severity_focus: [P1, P2, P3]
---

# solidity-smart-contract

Solidity: reentrancy (CEI), integer wrap (pre-0.8), tx.origin auth, delegatecall hijack, uninitialised storage pointers, oracle manipulation, MEV, sandwich risk.

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

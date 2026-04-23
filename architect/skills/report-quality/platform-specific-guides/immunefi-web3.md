---
name: immunefi-web3
domain: report-quality
triggers:
  languages: [solidity]
severity_focus: [P1, P2, P3]
---

# immunefi-web3

Immunefi PoC requirements: forge test reproducer, mainnet fork at exact block, dollar-impact calculation, no on-chain attack execution.

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

---
name: cvss-scoring-guide
domain: report-quality
triggers:
  languages: [any]
severity_focus: [P1, P2, P3]
---

# cvss-scoring-guide

CVSS 3.1 base/temporal/environmental. Common mistakes: PR/UI mis-scoring, Scope changed only with cross-trust-boundary impact, Integrity 'low' for read-only RCE preconditions.

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

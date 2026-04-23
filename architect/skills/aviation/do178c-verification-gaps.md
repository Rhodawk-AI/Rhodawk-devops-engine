---
name: do178c-verification-gaps
domain: aviation
triggers:
  languages: [aviation]
severity_focus: [P1, P2, P3]
---

# do178c-verification-gaps

DO-178C objectives by DAL level, MC/DC coverage gaps, tool qualification (DO-330) skips, requirement-to-test traceability holes.

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

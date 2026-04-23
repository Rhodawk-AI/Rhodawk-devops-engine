---
name: impact-statement-writing
domain: report-quality
triggers:
  languages: [any]
severity_focus: [P1, P2, P3]
---

# impact-statement-writing

Impact = (what can attacker do) x (what data/users) x (how realistic). Always answer: what's the worst case I can demonstrate vs theorise? Triagers reward demo, penalise theory.

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

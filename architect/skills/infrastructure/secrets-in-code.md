---
name: secrets-in-code
domain: infrastructure
triggers:
  languages: [any]
severity_focus: [P1, P2, P3]
---

# secrets-in-code

Detection patterns: AWS keys (AKIA*), GitHub PATs (ghp_*/gho_*), GCP SA JSON, Slack tokens, Stripe keys. Always run trufflehog over full git history.

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

---
name: ci-cd-pipeline-attacks
domain: infrastructure
triggers:
  languages: [github-actions, gitlab, jenkins]
severity_focus: [P1, P2, P3]
---

# ci-cd-pipeline-attacks

GitHub Actions: pull_request_target + checkout untrusted code, expression injection in run:, workflow_run from forks, cache poisoning, OIDC trust misconfig.

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

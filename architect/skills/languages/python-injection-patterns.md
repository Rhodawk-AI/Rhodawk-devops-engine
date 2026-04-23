---
name: python-injection-patterns
domain: languages
triggers:
  languages: [python]
severity_focus: [P1, P2, P3]
---

# python-injection-patterns

Python sinks: eval/exec/compile, subprocess shell=True, os.system, pickle.loads, yaml.load (pre-5.1), jinja2 SSTI, ORM raw().format().

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

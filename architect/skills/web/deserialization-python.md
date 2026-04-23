---
name: deserialization-python
domain: web
triggers:
  languages: [python]
severity_focus: [P1, P2, P3]
---

# deserialization-python

Python deser: pickle (any unpickle of untrusted data is RCE), PyYAML yaml.load() pre-5.1, marshal, jsonpickle, dill. Detection: any *.load(...) on user-controlled bytes.

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

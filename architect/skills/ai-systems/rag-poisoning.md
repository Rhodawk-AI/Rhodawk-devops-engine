---
name: rag-poisoning
domain: ai-systems
triggers:
  languages: [any]
severity_focus: [P1, P2, P3]
---

# rag-poisoning

Poisoned chunks in vector DB, embedding-space adversarial vectors, doc-level instruction smuggling, source-priority confusion.

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

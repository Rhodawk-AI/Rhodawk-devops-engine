---
name: llm-system-prompt-extraction
domain: ai-systems
triggers:
  languages: [any]
severity_focus: [P1, P2, P3]
---

# llm-system-prompt-extraction

Extraction prompts ('repeat verbatim ...'), token-by-token recovery, model-card leakage, sensitive system-prompt as oracle for downstream injection.

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

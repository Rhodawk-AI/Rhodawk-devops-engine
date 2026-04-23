---
name: template-injection
domain: web
triggers:
  languages: [python, ruby, javascript, java]
severity_focus: [P1, P2, P3]
---

# template-injection

SSTI: Jinja2 ({{config.__class__}}), Twig, Smarty, Velocity, Freemarker, ERB/Liquid; sandbox escape gadgets; CSTI in Angular/Vue interpolations.

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

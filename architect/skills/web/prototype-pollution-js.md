---
name: prototype-pollution-js
domain: web
triggers:
  languages: [javascript, typescript, node]
severity_focus: [P1, P2, P3]
---

# prototype-pollution-js

JS proto pollution sinks: lodash _.merge/_.set, jQuery $.extend(true), Object.assign with user input, recursive for..in copies. Gadgets: Express body-parser, Mongoose, Handlebars, JSONata.

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

---
name: php-security-legacy
domain: languages
triggers:
  languages: [php]
severity_focus: [P1, P2, P3]
---

# php-security-legacy

PHP: include()/require() with user input → LFI/RFI, unserialize(), assert() string eval, type juggling (== vs ===), magic methods on attacker-controlled objects.

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

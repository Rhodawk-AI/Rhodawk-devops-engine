---
name: rtos-security-freertos
domain: embedded-iot
triggers:
  languages: [rtos]
severity_focus: [P1, P2, P3]
---

# rtos-security-freertos

FreeRTOS heap_4/heap_5 vulns, task priority inversion, interrupt-context misuse, stack-overflow detection (configCHECK_FOR_STACK_OVERFLOW).

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

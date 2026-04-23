---
name: uart-jtag-debug-interfaces
domain: embedded-iot
triggers:
  languages: [hardware]
severity_focus: [P1, P2, P3]
---

# uart-jtag-debug-interfaces

UART pad identification (TX/RX/GND/VCC), baud-rate sweep, JTAG fingerprinting (JTAGulator), SWD on Cortex-M, glitching attacks.

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

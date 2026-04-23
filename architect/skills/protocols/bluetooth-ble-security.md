---
name: bluetooth-ble-security
domain: protocols
triggers:
  languages: [bluetooth]
severity_focus: [P1, P2, P3]
---

# bluetooth-ble-security

BLE pairing modes (JustWorks/Passkey/OOB), KNOB attack, LE Secure Connections downgrade, GATT auth gaps, BlueBorne-class kernel bugs.

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

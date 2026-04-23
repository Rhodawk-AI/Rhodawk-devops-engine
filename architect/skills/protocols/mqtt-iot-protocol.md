---
name: mqtt-iot-protocol
domain: protocols
triggers:
  languages: [iot]
severity_focus: [P1, P2, P3]
---

# mqtt-iot-protocol

MQTT: anonymous brokers, wildcard subs leaking topics, retained-msg poisoning, lack of TLS, weak ACLs, $SYS topic disclosure.

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

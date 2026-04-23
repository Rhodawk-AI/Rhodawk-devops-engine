---
name: iot-cloud-api-attacks
domain: embedded-iot
triggers:
  languages: [iot]
severity_focus: [P1, P2, P3]
---

# iot-cloud-api-attacks

IoT cloud APIs: device-ID enumeration, claim/unclaim race, device-shadow IDOR, MQTT topic guess (deviceId in topic).

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

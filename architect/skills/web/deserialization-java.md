---
name: deserialization-java
domain: web
triggers:
  languages: [java]
severity_focus: [P1, P2, P3]
---

# deserialization-java

Java deserialization: ObjectInputStream gadgets (CommonsCollections, Spring, Hibernate, JRE7u21), ysoserial chains, Jackson polymorphic typing, SnakeYAML default tag, JNDI gadgets via LDAP/RMI.

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

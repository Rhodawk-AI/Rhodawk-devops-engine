---
name: java-security-patterns
domain: languages
triggers:
  languages: [java, kotlin, scala]
severity_focus: [P1, P2, P3]
---

# java-security-patterns

Spring/Tomcat sinks: ObjectInputStream, Spring SpEL, MyBatis SQL fragments, Velocity SSTI, JNDI lookups (Log4Shell), SnakeYAML.

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

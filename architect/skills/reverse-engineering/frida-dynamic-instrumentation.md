---
name: frida-dynamic-instrumentation
domain: reverse-engineering
triggers:
  languages: [any]
severity_focus: [P1, P2, P3]
---

# frida-dynamic-instrumentation

Frida: Interceptor.attach for native, Java.use for Android, ObjC.classes for iOS. Common scripts: SSL pinning bypass, root detect bypass, anti-debug bypass.

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

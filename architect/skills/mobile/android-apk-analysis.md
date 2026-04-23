---
name: android-apk-analysis
domain: mobile
triggers:
  languages: [android]
severity_focus: [P1, P2, P3]
---

# android-apk-analysis

APK static: jadx + apktool + AndroidManifest review (exported components, deep links, permissions), Network Security Config, hard-coded secrets, WebView misconfig.

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

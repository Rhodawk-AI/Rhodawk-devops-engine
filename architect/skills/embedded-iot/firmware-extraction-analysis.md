---
name: firmware-extraction-analysis
domain: embedded-iot
triggers:
  languages: [firmware]
severity_focus: [P1, P2, P3]
---

# firmware-extraction-analysis

Extraction: vendor portal, OTA capture, flash dump (SPI/eMMC), JTAG/SWD. Analysis: binwalk, unblob, Ghidra, find hard-coded keys & update URLs.

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

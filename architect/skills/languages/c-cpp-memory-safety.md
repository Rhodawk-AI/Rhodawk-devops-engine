---
name: c-cpp-memory-safety
domain: languages
triggers:
  languages: [c, cpp]
severity_focus: [P1, P2, P3]
---

# c-cpp-memory-safety

Memory-safety in C/C++: out-of-bounds, UAF, double-free, missing length checks. Tools: ASan/MSan/UBSan, Coverity, CodeQL. Modernisation: std::span, std::string_view, RAII.

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

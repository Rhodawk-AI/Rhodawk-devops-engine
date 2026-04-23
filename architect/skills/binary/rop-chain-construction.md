---
name: rop-chain-construction
domain: binary
triggers:
  languages: [c, cpp, asm]
severity_focus: [P1, P2, P3]
---

# rop-chain-construction

ROP/SROP/COP/JOP. Tools: ROPgadget, ropper, pwntools.rop. Patterns: stack pivot, mprotect to RWX, dup2+execve, syscall-only chains for sandboxes.

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

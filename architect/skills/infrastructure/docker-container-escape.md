---
name: docker-container-escape
domain: infrastructure
triggers:
  languages: [docker]
severity_focus: [P1, P2, P3]
---

# docker-container-escape

Container escapes: privileged + cgroup release_agent, mount /proc, exposed docker.sock, capabilities (CAP_SYS_ADMIN/CAP_NET_ADMIN), kernel-bug pivots, runc CVE-2019-5736 class.

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

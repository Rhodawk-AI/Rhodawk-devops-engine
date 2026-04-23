---
name: kubernetes-rbac-misconfig
domain: infrastructure
triggers:
  languages: [kubernetes]
severity_focus: [P1, P2, P3]
---

# kubernetes-rbac-misconfig

K8s RBAC: cluster-admin overuse, service-account token mounted in unrelated pods, RoleBinding -> privileged namespace pivot, exec/portforward verb abuse, etcd plaintext.

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

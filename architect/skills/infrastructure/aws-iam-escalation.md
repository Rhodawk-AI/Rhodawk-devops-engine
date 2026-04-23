---
name: aws-iam-escalation
domain: infrastructure
triggers:
  languages: [aws]
severity_focus: [P1, P2, P3]
---

# aws-iam-escalation

AWS privesc: iam:PassRole + ec2 RunInstances, lambda:UpdateFunctionCode, iam:CreateAccessKey on self, sts:AssumeRole loops, S3 bucket policy + replication abuse.

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

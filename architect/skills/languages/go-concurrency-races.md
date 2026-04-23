---
name: go-concurrency-races
domain: languages
triggers:
  languages: [go]
severity_focus: [P1, P2, P3]
---

# go-concurrency-races

Go: data races on shared maps, channel close-after-write, sync.WaitGroup misuse, context leaks, goroutine leaks via blocked send. Detection: go test -race.

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

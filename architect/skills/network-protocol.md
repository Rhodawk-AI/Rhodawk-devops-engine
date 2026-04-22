---
name: network-protocol
domain: network
triggers:
  asset_types:  [tcp, udp, tls, dns, bgp, http, smtp, smb]
tools:          [scapy, masscan, nmap, dnsx, tlsfuzzer]
severity_focus: [P1, P2]
---

# Network-Protocol Implementation Bugs

## When to load
Network daemons, custom binary protocols, DNS / TLS / BGP implementations,
mail servers, VPN concentrators.

## Vulnerability classes
* **Parser DoS** — recursion, malloc bomb, billion-laughs analogue.
* **Length-prefix mismatch** — declared > actual or vice versa.
* **State-machine confusion** — replay handshake messages out of order.
* **TLS** — renegotiation flaws, client-cert spoof via SAN tricks, ALPN
  confusion, session-resumption oracle.
* **DNS** — cache poisoning (predictable txid), zone walk, NSEC3 enumeration,
  DDoS amplifier (ANY queries on open resolver).
* **BGP** — leaked routes, missing RPKI validation.
* **SMTP** — STARTTLS stripping, command injection in `MAIL FROM`.

## Procedure
1. Capture a baseline pcap of normal traffic.
2. Mutate fields with scapy / boofuzz / pulledpork; re-send.
3. Track crashes via the AFL++ network-protocol harness.
4. For TLS: `tlsfuzzer` test suite; flag any bogus handshake the server
   accepts.
5. For DNS: `dnsperf` + custom scapy mutators; check resolver cache for
   poisoning.

## Reporting
Capture pcap of the malicious flow.  Provide minimal protocol message that
triggers the bug.

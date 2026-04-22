---
name: automotive-security
domain: automotive
triggers:
  asset_types:  [can, uds, ecu, telematics, infotainment, obd]
tools:          [python-can, scapy, caringcaribou, savvycan, can-bus-mcp]
severity_focus: [P1, P2]
---

# Automotive Security

## When to load
Any automotive bug-bounty target: CAN dongles, telematics units, OBD
adapters, infotainment systems.

## Stack
* CAN / CAN-FD physical & data-link layer
* ISO-TP (15765-2) transport
* UDS (ISO 14229) diagnostic protocol
* SOME/IP, DoIP for newer service-oriented vehicle networks

## Procedure
1. Connect a CAN interface (vcan0 / SocketCAN / Vector / PCAN).  Use the
   `can-bus-mcp` tool for scripted access.
2. Listen passively (`candump`); identify cycle times, gateway IDs.
3. `caringcaribou listener` then `caringcaribou uds discovery` — enumerate
   addressable ECUs.
4. UDS service hunt: `0x10` (DiagSession), `0x27` (SecurityAccess),
   `0x34/0x36/0x37` (RequestDownload), `0x31` (RoutineControl), `0x2E`
   (WriteDataByIdentifier).  Focus on `SecurityAccess` seeds → key
   reversibility (XOR, weak hash, look-up table in firmware).
5. Telematics modems (TCU): web/MQTT/HTTP attack surface as well — apply the
   `web-security-advanced` and `network-protocol` skills.

## Reporting
Frame-level capture (`asc` / `pcap`), description of the privilege gained
(unlock, start, immobiliser bypass, OTA inject).  No on-public-road testing.

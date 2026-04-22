---
name: ics-scada
domain: ics
triggers:
  asset_types:  [plc, scada, hmi, modbus, dnp3, s7, opcua, iec61850]
tools:          [pymodbus, scapy, nmap-ics, snap7, opcua-client]
severity_focus: [P1, P2]
---

# Industrial Control Systems (SCADA / PLC)

## When to load
Energy / utilities / manufacturing programs that explicitly include OT in
scope.  Never touch production OT without written authorisation.

## Protocols and known weaknesses
* **Modbus TCP (502/tcp)** — no auth; arbitrary read/write of coils &
  registers from any reachable IP.
* **DNP3 (20000/tcp)** — Secure-Auth often disabled; replay attacks.
* **S7Comm (102/tcp, Siemens)** — `nmap --script s7-info`; PLC stop/run
  control without auth on legacy firmware.
* **OPC-UA** — anonymous endpoint with `SecurityPolicy#None` allows full
  browse / write.
* **IEC 61850 / Goose** — multicast on the substation LAN; lack of message
  auth → spoofed trip command.

## Procedure
1. Discovery: `nmap -sV -p 102,502,20000,4840 --script "modbus*,s7*,dnp3*"`.
2. For Modbus: `pymodbus client read_input_registers` to baseline; never
   write to a live process.
3. For OPC-UA: `opcua-client` GUI to enumerate node hierarchy; flag
   `SecurityPolicy=None` and any object missing `WriteMask`.
4. For S7: `snap7` `client.connect()` → `client.plc_get_cpu_state()`.

## Reporting
Always coordinate with the asset owner before writing to any OT device.
Default to **read-only** evidence (register dump, info.plist).  Suggest
network segmentation, modbus-secure, OPC-UA `Basic256Sha256` profile, and
NERC CIP / IEC 62443 alignment.

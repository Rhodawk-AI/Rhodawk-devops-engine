---
name: aviation-aerospace
domain: aviation
triggers:
  asset_types:  [arinc429, arinc664, ads-b, mavlink, do178c, avionics, uav]
tools:          [python-arinc, scapy-aviation, mavsdk, dump1090, gnuradio]
severity_focus: [P1, P2]
---

# Aviation & Aerospace

## When to load
Avionics bug-bounty programs (Boeing / Airbus / FAA), drone / UAV testing,
ADS-B receiver implementations, flight-management software.

## Surface
* **ARINC 429** — single-source label-based bus; spoofable on the wire if
  you have access (engineering rigs, MRO bays).
* **AFDX / ARINC 664 (part 7)** — switched Ethernet with virtual links; flag
  any virtual link exposed without VLAN segregation or with wrong BAG.
* **ADS-B (1090ES)** — unauthenticated; receiver software must validate
  Mode S CRC and reject impossible kinematics (but most don't).
* **MAVLink** — MAVLink2 signing optional; default keys in many open-source
  GCS builds.
* **DO-178C software** — flag departures from the verification artefacts
  promised in the data package.

## Procedure
1. For receiver software: feed crafted Mode-S frames (Type 17 ADS-B) with
   impossible coords, NaN, malformed length; observe parser behaviour.
2. For MAVLink: `mavlink-router` test rig, then send unsigned `MAV_CMD_DO_*`
   commands; should be rejected.
3. For AFDX: `scapy-afdx` virtual-link spoof on a controlled bench, never
   on a live aircraft network.

## Ethics
Never engage with a real aircraft, real ATC infrastructure, or real airspace.
Coordinate every test through a legal lab harness or the operator's program.

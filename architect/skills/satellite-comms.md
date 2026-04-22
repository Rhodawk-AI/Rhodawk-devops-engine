---
name: satellite-comms
domain: satellite
triggers:
  asset_types:  [dvb-s2, leo, geo, ground-station, cubesat, iridium, starlink]
tools:          [gnu-radio, gr-satellites, gpredict, sdr-analysis-mcp]
severity_focus: [P1, P2]
---

# Satellite Communications

## When to load
Ground-station software audits, cubesat firmware, telemetry/command (TT&C)
chain reviews, downlink decoder implementations, LEO commodity-modem
research with explicit operator authorisation.

## Surface
* **DVB-S2 / DVB-S2X** — modem firmware vulnerabilities; lawful intercept
  back-doors; codec parser bugs.
* **TT&C** — uplink without command authentication (legacy CCSDS); CRC-only
  integrity → forgeable command.
* **Telemetry decoders** — packet parser DoS / RCE (CCSDS Space Packet
  Protocol, AOS framing).
* **Ground software** — generic web / API surface (apply the
  `web-security-advanced` skill against the management UI).

## Procedure
1. Capture downlink using SDR (HackRF / LimeSDR / RTL-SDR Blog v3).
2. Demodulate with gr-satellites for known birds; for proprietary protocols,
   reverse-engineer modulation in Inspectrum.
3. Build a parser fuzzer against the decoder; feed known-bad CCSDS frames.
4. Audit the ground-station web UI / API with browser-agent-mcp.

## Ethics
Never transmit on a licensed space-uplink frequency without an authorised
test article and licensed station.  Always coordinate with the satellite
operator before any uplink test.

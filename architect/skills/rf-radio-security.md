---
name: rf-radio-security
domain: rf
triggers:
  asset_types:  [sdr, ble, zigbee, lora, zwave, rfid, nfc]
tools:          [gnu-radio, gr-bluetooth, scapy-radio, ubertooth, sdr-analysis-mcp]
severity_focus: [P1, P2]
---

# RF / Radio Security

## When to load
Smart-home, key-fob, IoT gateway, BLE peripheral, LoRa-WAN, Zigbee mesh,
RFID/NFC, GPS spoofing engagements.

## Surface
* **BLE** — pairing without OOB, fixed PIN `000000`, GATT characteristic
  with `Write` permission and no auth → control device.
* **Zigbee** — default trust-centre key (`5A 69 67 42 65 65 41 6C 6C 69 61
  6E 63 65 30 39`) → join arbitrary network.
* **Z-Wave** — S0 key derivable; downgrade S2 to S0 with rogue controller.
* **LoRaWAN** — root keys on device printed plaintext / derivable from DevEUI.
* **RFID 125 kHz / 13.56 MHz** — clone with Proxmark3 / Flipper.
* **GPS** — civilian L1 trivially spoofable with HackRF + `gps-sdr-sim`.

## Procedure
1. Identify the band & modulation (`rtl_power -f X:Y:Z`, look at waterfall).
2. Capture IQ via `sdr-analysis-mcp.capture_iq`.
3. Demodulate in GNU Radio Companion or `inspectrum`.
4. Replay / mutate; observe device behaviour.

## Reporting
Include the IQ capture, demodulated payload, and decoded protocol message.
Always operate within legal RF bands authorised in the program scope.

---
name: hardware-protocols
domain: hardware
triggers:
  asset_types:  [embedded, iot, router, ics, firmware]
tools:          [minicom, openocd, flashrom, screen, picocom, sigrok]
severity_focus: [P1, P2]
---

# Hardware Protocols (UART / JTAG / I2C / SPI)

## When to load
Physical-access work on embedded devices: routers, IoT cameras, automotive
ECUs, smart appliances.

## Procedure
1. **PCB inspection** — locate test pads.  Probe `Vcc`, `GND`, `TX`, `RX`
   with a logic analyser (sigrok / DSLogic).
2. **UART** — connect FTDI at typical baud (115200, 57600, 9600).  Watch boot
   log; many devices drop into U-Boot / CFE shell on a kernel-arg override.
3. **JTAG** — discover pinout with `JTAGulator`; speak SWD/JTAG via OpenOCD;
   halt CPU, dump SRAM/flash.
4. **SPI flash** — desolder or in-circuit clip; dump with `flashrom -p
   ch341a_spi -r dump.bin`; pass to `binwalk -e`.
5. **I2C** — enumerate devices with `i2cdetect`; read EEPROMs containing
   credentials/keys.

## Findings
* Boot log printing root password hash
* JTAG/SWD enabled on production unit → full firmware extraction
* Unencrypted SPI flash → static AES key, hard-coded admin password
* Unauthenticated I2C bootloader → can flash arbitrary firmware

## Reporting
Photograph the test point, document the exact tool chain and pin map; suggest
disabling JTAG by blowing eFuse and signing the firmware image with the SoC
secure-boot root.

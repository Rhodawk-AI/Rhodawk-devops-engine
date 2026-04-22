---
name: firmware-analysis
domain: firmware
triggers:
  asset_types:  [firmware, bin, uefi, bootloader, rtos]
tools:          [binwalk, qemu, buildroot, ubidump, fmk, uefi-firmware-parser]
severity_focus: [P1, P2]
---

# Firmware Analysis

## When to load
Bin firmware images for routers/IoT, UEFI capsules, RTOS images, vendor
update artefacts.

## Procedure
1. `binwalk -Me firmware.bin` — recursive extraction.  Identify embedded
   filesystem (squashfs / ubifs / cpio).
2. `chroot _firmware.bin.extracted/squashfs-root /bin/sh` (or QEMU-static
   for cross-arch).
3. Static analysis on every setuid / network-listening binary inside.
4. UEFI: `uefi-firmware-parser -e capsule.bin`; look at SMM modules for
   unauth ed CommBuffer handlers (CWE-77 in System Management Mode).
5. Hunt for hard-coded credentials, debug back-doors, telnetd compiled in,
   default WiFi keys derivable from MAC.
6. Identify update mechanism — is the update signed? Encrypted? Is it
   downloaded over HTTP?  An unsigned OTA is automatic P1.

## Reporting
Always include: device model + firmware version, SHA256 of the original
image, exact filesystem path of the vulnerable binary, and either a network
PoC or a static call graph proving the path.

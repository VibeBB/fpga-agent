---
name: fpga-device-pins
description: Choosing FPGA device profiles and package pins — bundled iCE40/ECP5/Gowin profiles, clock-capable pins, configuration and JTAG pins, I/O standards, and custom profiles.
version: 0.1.0
license: BSD-3-Clause
triggers:
  - package pin
  - device profile
  - ice40
  - ecp5
  - gowin
  - ピン配置
---

# Device profiles and pins

`fpga profile` lists bundled profiles; `fpga profile <id>` prints one.

| profile | part | boards |
| --- | --- | --- |
| `ice40-up5k-sg48` | iCE40UP5K SG48 | iCEBreaker, UPduino v3 |
| `ecp5-lfe5u-25f-cabga381` | LFE5U-25F CABGA381 | ULX3S (25F) |
| `ecp5-lfe5u-85f-cabga381` | LFE5U-85F CABGA381 | ULX3S (85F), OrangeCrab 85F |
| `gowin-gw1nr9c-qn88p` | GW1NR-LV9QN88PC6/I5 | Sipeed Tang Nano 9K |

Profiles are extracted from the open device databases (IceStorm, Trellis,
Apicula) by `scripts/extract_device_profiles.py`, so every listed pin is a
bondable user I/O. Each pin records its functions, whether it is a
dedicated clock input, and a `caution` of `config` or `jtag`.

- Put clocks on pins with `"clock": true` (global buffers); otherwise the
  report carries a warning.
- Configuration (SPI flash, CDONE/CRESET, PROGRAMN, DONE) and JTAG pins
  fail `fpga.pins` unless the pin lists the caution in `acknowledge`.
- ECP5/Gowin I/O standards must be one of the profile's `io_standards`
  and consistent with the board's bank voltage from the schematic.
- A board not covered by a bundled profile: put `<profile-id>.fpga-device.json` next
  to the contract with the same schema; it takes precedence over bundled
  profiles of the same id. Never invent pins; derive them from the device
  database or the vendor's package pinout.

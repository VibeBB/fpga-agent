---
description: Run one declared FPGA simulation (NVC or Icarus Verilog).
allowed-tools:
  - terminal
---

Run `python3 <fpga plugin root>/scripts/fpga_launcher.py sim <contract> --id <sim-id>`
and report matched and missing `expect` lines from the `sim-<id>.log` transcript.

Look at the PNG renders the run returns and record a `fpga_record_vision_review`
for each one before you report.

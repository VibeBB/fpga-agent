---
description: Export the FPGA pin map for the circuit agent.
allowed-tools:
  - terminal
---

Run `python3 <fpga plugin root>/scripts/fpga_launcher.py pinmap <contract>`
and point the circuit agent at the written `<name>.fpga-pinmap.json`.

Look at the PNG renders the run returns and record a `fpga_record_vision_review`
for each one before you report.

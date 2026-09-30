---
description: Validate the FPGA contract and run the static gates (pins, constraints, provenance, circuit match).
allowed-tools:
  - terminal
---

Run `python3 <fpga plugin root>/scripts/fpga_launcher.py check <contract>`
and report each failing static check from `<name>.fpga-report.md`.

---
description: Run every FPGA gate (lint, simulation, formal, synthesis, P&R, timing, utilization, bitstream).
allowed-tools:
  - terminal
---

Run `python3 <fpga plugin root>/scripts/fpga_launcher.py gates <contract>`
and report the verdict and each failing check from `<name>.fpga-report.md`.

---
description: Re-render the FPGA pin map, floorplan, utilization, timing, waveform and gate-report images from existing artifacts.
allowed-tools:
  - terminal
---

Run `python3 <fpga plugin root>/scripts/fpga_launcher.py render <contract> --view all`
(MCP `fpga_render`), look at every PNG it lists, and record one
`fpga_record_vision_review` per image with a long-form impression.

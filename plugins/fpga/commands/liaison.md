---
description: Check the UX-creator liaison inbox and answer every FPGA request with hashed artifacts, gate verdicts and record references.
allowed-tools:
  - terminal
---

Run `python3 <fpga plugin root>/scripts/fpga_launcher.py ux inbox` (MCP
`fpga_ux_inbox`). For every `new` or `stale` request do the work, record the
decision and stage impression, then answer with `fpga ux respond --json <file>`
(MCP `fpga_ux_respond`). Report blocked requests and malformed files to the
user.

---
name: fpga-contract-rules
description: Path rule — schema and provenance reminders injected whenever a *.fpga.json file is touched.
version: 0.1.0
license: BSD-3-Clause
paths:
  - "**/*.fpga.json"
---

# FPGA contract file rules

- `*.fpga.json` follows the `FpgaContract` schema in
  `src/fpga/contract.py` (schema_version 1, strict — unknown keys are
  errors). Check the field reference in
  `plugins/fpga/skills/fpga-contract/SKILL.md` before editing.
- `pins[].port` names a top-level port or one bit (`led[3]`); the
  synthesized top must match the pin set exactly — `fpga.synth` fails
  otherwise. `pins[].acknowledge` lists `config`/`jtag` with a
  `rationale` when a port deliberately uses such a pin.
- External HDL libraries stay pinned (`repo`, `revision`, `license`,
  `files[]`) — sources are referenced from `third_party/` checkouts,
  never copied into the tree.
- Generated projections (constraints `*.fpga.pcf/lpf/cst`, pinmaps,
  regmaps, production exports, reports and renders, `sim-*.log`,
  `formal-*.log`, `observations/fpga/*.jsonl`) are never hand-edited —
  change the contract and re-run the gates; `protect-generated` enforces.

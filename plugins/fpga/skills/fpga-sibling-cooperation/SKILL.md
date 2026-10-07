---
name: fpga-sibling-cooperation
description: How the FPGA plugin exchanges JSON artifacts with sibling plugins — circuit connectivity in, fpga-pinmap out, and fpga-request change proposals.
version: 0.1.0
license: BSD-3-Clause
triggers:
  - circuit
  - sibling
  - fpga-request
  - 姉妹連携
---

# Sibling cooperation

Cooperation is JSON files in the shared workspace — never code imports.

| direction | artifact | producer | consumer |
| --- | --- | --- | --- |
| in | `<design>.firmware.json` (`circuit_firmware_connectivity`) | `circuit firmware-export` | `fpga.netlist_match` |
| out | `<name>.fpga-pinmap.json` (`fpga_pinmap`) | `fpga pinmap` / `fpga gates` | the circuit agent |
| out | `<name>.fpga-regmap.json` (`fpga_regmap`) | `fpga regmap` | firmware `fw.fpga_regmap` |
| out | `<name>.fpga-production.json` (`fpga_production`) | `fpga production` after a passing `fpga gates` | production-engineering-agent's programming operation |
| out | `<design>.<id>.fpga-request.json` (`fpga_request`) | `fpga request` | the target sibling |
| out | `<name>.thermal.sim.json` + `<name>.thermal.sim-request.json` | `fpga sim-request` / `fpga_sim_thermal_request` | simulation-agent `sim respond` |
| in | `<name>.thermal.sim-response.json` (`thermal.response_path`) | simulation-agent | `fpga.sim_thermal`, `fpga sim-check` |
| out | `<name>.fpga-report.json` (`fpga_gate_report`) | `fpga gates` | firmware, production, doc |

The circuit connectivity export lists the FPGA as one of its devices
(`mcus[]` with `ref` = `device.ref`). The gate report records the export's
sha256 (`circuit_sha256`) and the pin map records the contract's sha256,
so either side can detect a stale artifact. Re-export after every circuit
change.

Change requests: `fpga request <contract> --target circuit --risk high
--change "..." --rationale "..." [--net NET] [--failing-check ID]`.
`target` is one of `circuit`, `firmware`, `mech`, `wire`, `ux`, `bard`,
`doc`, `production`; use `risk: high` for anything that changes the board.
Never edit a sibling's input files.

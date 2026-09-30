---
name: fpga-workflow
description: End-to-end FPGA workflow — contract first, circuit-matched pin map, generated constraints, lint, NVC/Icarus simulation, SymbiYosys formal, Yosys synthesis, nextpnr place-and-route, timing, utilization and bitstream — with deterministic fpga.* gates.
version: 0.1.0
license: BSD-3-Clause
triggers:
  - fpga
  - hdl
  - rtl
  - vhdl
  - verilog
  - bitstream
  - ビットストリーム
  - 論理合成
---

# FPGA workflow

The contract `<name>.fpga.json` is the single source of truth. Constraint
files, the pin map export, reports and tool transcripts are projections of
it and are write-protected by the `protect-generated` hook.

1. **Circuit export** — the circuit agent writes `<design>.firmware.json`
   (`circuit_firmware_connectivity`, the FPGA is one of its devices). Point
   `circuit.connectivity` at it (`fpga-sibling-cooperation` skill).
2. **Contract** — device profile, top, sources, libraries, clocks, pins,
   build, simulations, formal runs (`fpga-contract` skill).
3. **Constraints** — `fpga constraints <contract>` writes the PCF (iCE40),
   LPF (ECP5) or CST (Gowin) named by `build.constraints`.
4. **Static gates** — `fpga check <contract>` (MCP `fpga_check`).
5. **RTL + verification** — HDL, self-checking testbenches, PSL/SVA
   properties (`fpga-verification` skill).
6. **Full gates** — `fpga gates <contract>` (MCP `fpga_gates`) writes
   `fpga-reports/<name>.fpga-report.{json,md}` plus the pin map export.
7. **Circuit confirmation** — hand `<name>.fpga-pinmap.json` to the circuit
   agent.
8. **Programming** — a human runs `fpga program <contract>
   --confirm-sha256 <bitstream sha256>` on the host. Agents never program
   hardware.

## Gates (all fail closed)

| id | passes when |
| --- | --- |
| `fpga.contract` | contract validates, the device profile resolves and matches the build suffixes |
| `fpga.provenance` | every external library file exists, carries an SPDX header, and its identifiers match the declared license |
| `fpga.pins` | every package pin is a user I/O of the profile, config/JTAG pins are acknowledged, I/O standards and pulls are valid for the family |
| `fpga.constraints` | the constraint file matches the contract projection byte for byte |
| `fpga.netlist_match` | every pin lands on its declared circuit net, voltages fit the I/O maximum, and no connected circuit pin is left unconstrained |
| `fpga.lint` | NVC analysis/elaboration (VHDL) or Verilator `--lint-only` (Verilog) is clean |
| `fpga.sim.<id>` | the simulator prints every `expect` line in order, no `forbid` line, and exits 0 before the timeout |
| `fpga.formal.<id>` | SymbiYosys reports `PASS` for the declared mode and depth |
| `fpga.synth` | Yosys synthesizes the top and its ports equal the pinned ports |
| `fpga.pnr` | nextpnr places and routes the design |
| `fpga.timing` | every declared clock meets its frequency |
| `fpga.utilization` | each resource class stays within `build.budget` |
| `fpga.bitstream` | the packer writes a non-empty bitstream with the family's preamble; its sha256 is recorded |

Missing tools, missing files and unparseable output are failures, never
skips. Run `fpga doctor` first when a tool is missing.

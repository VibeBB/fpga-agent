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
8. **Production handoff** — after a passing `fpga gates`, run
   `fpga production <contract>` so production-engineering-agent can bind
   the gated bitstream to its programming operation. Set
   `programmer.write_flash` for products: an `sram` target is volatile.
9. **Programming** — a human runs `fpga program <contract>
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
| `fpga.regmap` | when `registers` is set: `registers.hdl_package` matches `fpga regmap` output and a design source uses it |
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

## Records you must leave (VibeBB Record Protocol — mandatory, unprompted)

Record these without being asked; the Stop hook (`require-records`) refuses
to finish a session that still owes them (see `docs/records-and-vision.md`).

- **Decision** (`fpga_record_decision`) for every non-trivial choice — device
  profile, clock pin and frequency, pin moves, I/O standard and pull, reset and
  clock-domain-crossing strategy, FSM encoding, library adoption, simulation
  and formal coverage, budget or seed changes, how a timing or utilization
  failure was fixed, every answer to a UX-creator request. Give the question,
  the first principles it rests on (setup/hold and clock period, metastability
  and synchronizer MTBF, I/O bank voltage and drive, resource counts of the
  part, license terms), at least two options with pros and cons, the chosen
  option, a rationale of 200+ characters, evidence (contract, gate report,
  render and transcript paths are hashed; cite datasheets and standards as
  references), assumptions, unknowns, residual risks and the observation that
  would reopen it. Reason from principles, not from habit.
- **Stage impression** (`fpga_record_impression`) when a stage ends, after its
  final regeneration. FPGA stages: `requirements` (intake, circuit export),
  `pin-plan` (contract, profile, constraints, static gates), `rtl` (HDL and
  testbenches), `verification` (simulation and formal), `implementation`
  (synthesis, place and route, timing, utilization, bitstream), `review`, and
  `liaison` (UX-creator answers). 400+ characters and 3+ sentences on what you
  noticed, what works, what worries you, how the board designer, firmware
  author or the person who will program the board would read the result, and
  what to do next. List the stage's output files or directories so the
  impression is bound to their sha256.
- **Vision review** (`fpga_record_vision_review`) every time you look at an
  image — a render under `fpga-reports/` (pin map, floorplan, utilization,
  timing, waveform, gate report), a user photo of a board, a datasheet figure,
  a logic-analyzer capture, an `inspect_image_with_vision` answer: findings plus
  a long-form impression of 400+ characters judging accuracy against the
  contract and reports, ambiguity, whether the design intent comes across and
  whether the board designer or bench operator could act on it — not only
  legibility. Bind it to `image_path` or to the vision event's
  `source_event_id`.

Vision and impressions are advisory: they never override a deterministic
`fpga.*` gate verdict. Results do not have to be identical from run to run;
the reasoning must be recorded every run. `fpga_records_status` shows what is
still owed.

## Look at what you produced (vision points)

Every image-producing tool (`fpga_gates`, `fpga_build`, `fpga_sim`,
`fpga_pinmap_export`, `fpga_render`) returns its PNG renders inline, and the
files stay under `fpga-reports/`. Look at each one, compare it with the numbers
in the JSON report, and record a vision review. When your model cannot see the
inline image, call `inspect_image_with_vision` (declared as
`VisionInspectTool`; it consults a saved vision-capable LLM profile and only
inspects images attached to the latest user message) or say that you could
not look, and decide from the JSON report alone.

| Render | Look for |
| --- | --- |
| `<name>.fpga-pinmap.png` | every port on the intended package pin and net, clocks on clock-capable pins, caution (configuration/JTAG) pins only where acknowledged, banks and neighbours that make board routing awkward |
| `<name>.fpga-floorplan.png` | placement clustered sensibly, I/O logic near its pins, no surprising spread that hints at a long critical path |
| `<name>.fpga-utilization.png` | headroom against each budget for the next feature, unexpected resource classes (RAM or DSP inferred where you meant logic, or the reverse) |
| `<name>.fpga-timing.png` | slack per clock, the worst path's start and end, whether the margin survives temperature, voltage and the next feature |
| `<name>.fpga-wave-<sim>.png` | protocol timing (start/stop bits, handshakes, reset release) matches the spec, no `x`/`z` after reset, the testbench really exercises what its `expect` line claims |
| `<name>.fpga-report.png` | the overall verdict and which stage a failure points back to |

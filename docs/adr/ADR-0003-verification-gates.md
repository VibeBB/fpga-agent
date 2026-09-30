# ADR-0003: Simulation, formal, timing and bitstream gates

- Status: accepted
- Date: 2026-09-30

## Decision

- Simulation: NVC for VHDL, Icarus Verilog for Verilog. A run passes only
  when the simulator exits 0 before `timeout_s`, prints every `expect`
  line in order and no `forbid` line. Testbenches must self-check.
- Formal: SymbiYosys with a generated `.sby`: VHDL through the GHDL Yosys
  plugin (PSL), Verilog through `read_verilog -formal` (SVA subset).
  Modes `prove`, `bmc`, `cover`; `depth` is mandatory; `parameters`
  override generics so proofs can use reduced widths.
- Implementation: nextpnr runs with `--timing-allow-fail` and `--report`
  so the router always produces a report; `fpga.timing` then fails any
  declared clock (and any other constrained clock net) below its
  frequency. Utilization maps cell types to resource classes per profile
  and fails unclassified cells.
- Bitstream: the packer output must exist, be at least 1 KiB and carry the
  family preamble (iCE40 `7EAA997E`, ECP5 `FFFFBDB3`, Gowin `A5C3`); its
  sha256 goes into the report.
- Synthesized top ports must equal the contract's pinned ports.

## Consequences

- Timing failures are reported with the achieved fmax instead of a bare
  router error.
- A passing report is the only thing that unlocks programming (ADR-0005).

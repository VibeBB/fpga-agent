---
name: fpga-verification
description: Verifying HDL — self-checking NVC and Icarus Verilog testbenches, PSL and SVA properties proven with SymbiYosys, and reading timing and utilization reports.
version: 0.1.0
license: BSD-3-Clause
triggers:
  - testbench
  - simulation
  - formal
  - psl
  - sva
  - シミュレーション
  - 形式検証
---

# Verification

## Simulation (`fpga.sim.<id>`)

- VHDL runs on NVC (`--std=2008` unless `build.vhdl_standard` is `93`);
  Verilog on Icarus Verilog (`iverilog -g2012` + `vvp`).
- Testbenches self-check: VHDL `assert ... severity failure`, Verilog
  `$fatal(1, ...)`. Print a pass line (`report "PASS: ..."`,
  `$display("PASS: ...")`) and list it in `expect`; list failure markers in
  `forbid`.
- End the run: stop the clock and let the simulation run out, call
  `std.env.finish` / `$finish`, or set `stop_time`.
- `waveform: true` records `fpga-reports/sim-<id>.fst` (NVC) for GTKWave
  or Surfer.

## Formal (`fpga.formal.<id>`)

- VHDL: PSL comments in the architecture, read through the GHDL Yosys
  plugin:
  `-- psl default clock is rising_edge(clk);`
  `-- psl name: assert always (a -> next b);`
- Verilog: immediate `assert`/`assume`/`cover` under `` `ifdef FORMAL ``
  (read with `read_verilog -formal`), with a `past_valid` guard for
  `$past`.
- `prove` runs k-induction to `depth`; `bmc` checks `depth` cycles;
  `cover` must reach every cover statement. Use `parameters` to shrink
  counters so induction converges.
- A failing proof leaves a counterexample trace under
  `build/formal-<id>/`; the transcript is `fpga-reports/formal-<id>.log`.

## Implementation reports

- `fpga.timing` reads nextpnr's `--report` JSON; nextpnr runs with
  `--timing-allow-fail` so the gate, not the router, decides and reports
  the achieved fmax of every clock.
- `fpga.utilization` maps each cell type to a resource class (logic, ram,
  dsp, io, clock, pll) and compares against `build.budget`.

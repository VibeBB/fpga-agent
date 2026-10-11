# ADR-0012: Line/branch coverage of product RTL simulations

- Status: accepted
- Date: 2026-10-11

## Context

`fpga.sim.<id>` proves a testbench passes, not how much of the design it
exercised. Designers using fpga-agent need a structural coverage floor on
their own RTL (C0 line, C1 branch) without new dependencies.

## Decision

- Add optional `simulations[].coverage {measure, min_line_pct,
  min_branch_pct, rationale}` and gate `fpga.coverage.<id>`. Contracts
  without it are unchanged.
- Verilog: Icarus has no coverage, so the testbench is rebuilt with the
  Verilator already shipped in OSS CAD Suite (`--binary --timing
  --coverage-line`) and `coverage.dat` is parsed (`t=line`, `t=branch`).
  The tools image gains `g++` and `make`, which Verilator needs to build
  the model.
- VHDL: NVC elaborates with `--cover=statement,branch`; the database is
  exported with `nvc --cover-export --format=cobertura` and parsed with the
  standard library.
- Only points whose file is in `measure` count; `measure` must be design
  sources, so testbench code cannot inflate coverage.
- Fail closed: missing tool, build/run failure, unreadable data, or no
  coverage point in the measured files.

## Consequences

- Verilator counts each if/else or case arm; NVC counts a decision covered
  only when every outcome ran. The floors are per contract, so the
  difference is documented rather than normalised.
- Condition coverage (MC/DC) and toggle coverage are out of scope:
  Verilator has no MC/DC, and toggle counts depend on simulation length.
- Verilog testbenches must be Verilator-compatible to use the gate.

# ADR-0015 — CPU core libraries

Status: Accepted.

## Context

FPGA designs commonly need a soft CPU. Research (official docs, community
threads, LibFPGA/LibHunt comparisons, toolchain track records) identified
cores that (a) synthesize through our GHDL/Yosys/nextpnr path, (b) carry
compatible licenses, and (c) are referenced unmodified from `third_party/`.

## Decision

Adopt five cores through the existing `libraries[]` + `components`
mechanism:

- **SERV** (ISC): `serv_rf_top` — ~200 LUT bit-serial RV32I.
- **PicoRV32** (ISC): `picorv32` — ~1k LUT RV32IMC.
- **NEORV32** (BSD-3): `neorv32_top`/`file_list_core.f` — full MCU SoC.
- **Hazard3** (Apache-2.0): `hazard3_cpu_1port`/`hazard3.f` — RV32IMACZb,
  the RP2350 core, iCEBreaker-proven.
- **VexRiscv** via `litex-hub/pythondata-cpu-vexriscv` (MIT): prebuilt
  single-file variants selected with `files:`; avoids adding
  SpinalHDL/Scala as a tool dependency.

Resolver extensions needed by these libraries:

- `Library.exclude`: root-relative glob patterns skipped during the
  unit scan (upstream test setups, benches, SoC wrappers).
- `.f` file lists now indexed for VHDL libraries too; entries may use
  per-line keywords (`file <path>`) and env-style root prefixes
  (`$NEORV32_HOME/...`, resolved against the library root).
- `ifdef`-guarded `` `include``s are tracked but do not fail when the
  target is absent (no defines are ever set).
- `` `include`` targets resolve against the including file's directory
  and the library root; headers (`.vh`/`.svh`) contribute include dirs
  (`Resolved.includes`, merged into `hdl.include_dirs`) but are never
  compile units.
- Instantiating a unit declared in the same file is not a dependency
  cycle; component lookup is case-insensitive (providers are indexed
  lowercased, Verilog module names keep their case for `-top`).

## Consequences

Firmware images (boot ROM, `$readmemh`) remain outside `libraries[]`;
they are design artifacts produced by the user or a sibling agent.
LiteX (a SoC *generator*, not a library) stays out of scope — its
apicula toolchain path is a candidate for a separate ADR. Rejected
candidates (CV32E40P/Ibex — heavy SystemVerilog + bespoke clock-gating;
CVA6 — Linux-class; ZipCPU — GPL; Microwatt — POWER ISA;
VexiiRiscv/Black Parrot — generator or SV dependency; FemtoRV —
duplicates PicoRV32) are recorded in the research notes.

## Verification

`scripts/library_smoke.py` synthesizes every adoptable top per library
for Gowin inside the fpga-tools image; SERV, PicoRV32, NEORV32, Hazard3
and VexRiscv top modules synthesize cleanly (`synth_gowin`), and
remaining per-unit failures are vendor-primitive or simulator-limit
cases documented in `fpga-external-libraries/SKILL.md`.

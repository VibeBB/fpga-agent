# ADR-0014: Component resolution and more HDL libraries

- Status: accepted
- Date: 2026-10-11

## Context

ADR-0004 introduced `contract.libraries[]` with an explicit, hand-ordered
`files[]` list. Only three Colibri files could realistically be declared
that way: Colibri's units depend on each other through `use colibri.*`
and `entity work.*` references, so any non-trivial component required
manually tracing and ordering a dozen files.

A survey of candidate HDL libraries (the user's six plus community
candidates: OSVVM/UVVM/VUnit, LiteX, NEORV32/SERV/VexRiscv, ZipCPU cores,
OpenCores, secworks sha256, vhdl-extras) identified several worth
adopting — but they carry no per-file SPDX headers, and their internal
references make manual `files[]` ordering impractical at scale.

## Decision

- `libraries[]` gains `components[]`: design-unit names (VHDL
  entity/package, Verilog module, `<name>.f` file list, directory, or
  `all`) resolved to an ordered file list by `fpga.libraries`, which
  scans the checkout, indexes declared units and statically traces
  `use`/`entity`/`configuration`/`include`/`import` references. Cycles,
  unknown units, ambiguity and references to undeclared or later-declared
  libraries are gate failures. `files[]` remains for explicit control and
  is appended after resolved files.
- `libraries[]` gains `license_file`: a root-relative license text that
  `fpga.provenance` verifies exists and mentions the declared license,
  covering files without SPDX headers. `fpga.provenance` also verifies
  the checkout HEAD equals `revision` when the checkout is a git clone.
- `scripts/fetch_hdl_libraries.py` + registry `scripts/hdl_libraries.json`
  generalize `fetch_colibri.py` (kept as a wrapper). `--contract <file>`
  fetches exactly what a contract declares into its workspace-relative
  `root`s — this is how OpenHands SDK agents get libraries on the host
  before the `--network none` tools container runs (`fpga_launcher.py
  fetch <contract>`).

### Adopted (registry)

- **open-logic** (PSI): broad, actively maintained VHDL library,
  LGPL-2.1-or-later + PSI HDL exception (bitstream distribution
  explicitly allowed). No SPDX headers → `license_file: License.txt`.
- **hdl-modules**: high-quality VHDL modules under BSD-3-Clause. Its
  module-per-library layout maps onto cross-library references — declare
  used modules (`common`, `fifo`, …) as separate `libraries[]` entries
  in dependency order. No SPDX headers → `license_file: license.txt`.
- **verilog-axis**, **verilog-uart** (Alex Forencich): de-facto standard
  MIT Verilog components with `.f` file lists. No SPDX headers →
  `license_file: COPYING`.
- **libfpga**: compact MIT Verilog utilities under `rtl/`.

### Evaluated and not adopted (record kept)

- **VHDL/PoC**: large overlap with Colibri/Open Logic and vendor-specific
  parts mixed in; revisit if a specific PoC unit is needed.
- **slaclab/surf**: Xilinx-primitive-heavy and built around the ruckus
  flow; poor fit for the open-toolchain lane.
- **ohwr general-cores**: license-mixed (CERN-OHL-W-2.0 plus LGPL-2.1
  and some GPL); Wishbone cores are a candidate for a later, selective
  adoption.
- **pulp-platform/common_cells**: SystemVerilog; deferred until the
  flow's SV support is verified end-to-end (yosys `-sv`/iverilog).
- **OSVVM/UVVM/VUnit**: verification frameworks, not synthesizable
  component libraries; the sim lane may adopt them separately.
- **LiteX ecosystem**: Python generators, not reusable HDL.
- **NEORV32/SERV/VexRiscv**: CPU cores, not libraries; out of scope.
- **ZipCPU**: GPL — conflicts with the BSD-3-Clause lane.
- **OpenCores**, **secworks/sha256**, **vhdl-extras**: mixed or stale.

## Consequences

- Contracts name what they use (`components: ["uart"]`) instead of
  reverse-engineering a library's file order — Colibri's full 102 units
  become usable by name.
- Provenance stays fail-closed and now also records revision pinning;
  libraries without SPDX headers need a verified `license_file`.
- CI and SDK fetches are contract-driven: adding a declared library to an
  example or workspace contract is sufficient — no workflow edits.

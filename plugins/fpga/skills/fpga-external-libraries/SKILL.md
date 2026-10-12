---
name: fpga-external-libraries
description: Using third-party HDL libraries (Colibri, Open Logic, hdl-modules, verilog-axis, verilog-uart, libfpga) — pinned checkouts, contract library declarations, component resolution, and license obligations.
version: 0.2.0
license: BSD-3-Clause
triggers:
  - colibri
  - open-logic
  - hdl-modules
  - verilog-axis
  - verilog-uart
  - libfpga
  - library
  - ip core
  - ライブラリ
  - ライセンス
---

# External HDL libraries

External HDL is never copied into the design tree. Declare it in the
contract so the gates can compile it into its own HDL library and record
its provenance:

```json
"libraries": [{
  "name": "colibri",
  "root": "third_party/colibri",
  "language": "vhdl",
  "components": ["uart"],
  "license": "CERN-OHL-W-2.0",
  "license_file": "LICENSES/CERN-OHL-W-2.0.txt",
  "source_url": "https://gitlab.com/colibri-cern/colibri",
  "revision": "3fa784121ccea86d9e65b2e0dc08d2a3327f5f2f"
}]
```

- `root` is relative to the contract file. In a product workspace use
  `third_party/<name>`; the repo's own examples use
  `../../third_party/<name>`.
- `components` names design units to pull in: VHDL entity/package names,
  Verilog module names, `<name>.f` file lists, directory names, or `all`
  for the whole library. Files are resolved to compile order by tracing
  `use`/`entity`/`include`/`import` references — you do not list
  dependencies yourself.
- `files` (explicit paths in compile order) may be combined with
  `components` or used alone, as before.
- Instantiate with the library name: `library colibri;` and
  `entity colibri.uart`. For Verilog libraries, instantiate modules
  directly.
- `license_file` points at the root-relative license text; it covers
  files that carry no SPDX header. `fpga.provenance` verifies the file
  exists and mentions the declared license, and also checks the checkout
  HEAD matches `revision`.
- `fpga.provenance` fails when a resolved file is missing, has an SPDX
  header that does not match `license`, or has no SPDX header and no
  `license_file`.

## Fetching libraries

- Repo development: `python3 scripts/fetch_hdl_libraries.py [names...]`
  fetches registry entries into `third_party/` (gitignored).
- In an OpenHands/agent workspace, run on the host:
  `python3 <plugin>/scripts/fpga_launcher.py fetch <contract>.fpga.json`
  — it clones every declared library at its pinned revision into the
  contract-relative `root` inside the workspace, which the tools
  container then sees through the workspace mount.
- Never run `git clone` inside the tools container; it has no network.

## Adopted libraries (registry in `scripts/hdl_libraries.json`)

| Library | Lang | License | Notes |
|---|---|---|---|
| colibri | VHDL | CERN-OHL-W-2.0 | General-purpose blocks; instantiate `entity colibri.<unit>` |
| open-logic | VHDL | LGPL-2.1-or-later WITH PSI HDL exception | Units compile into `olo` lib; use `library olo;` |
| hdl-modules | VHDL | BSD-3-Clause | Library name = module name (e.g. `fifo`, `common`) — declare each used module as its own `libraries[]` entry, dependencies first |
| verilog-axis | Verilog | MIT | AXI-Stream components; pick modules via `components` or `.f` lists |
| verilog-uart | Verilog | MIT | Minimal UART rx/tx |
| libfpga | Verilog | MIT | uart/spi/i2c/fifo/cdc/arbiter/crc/lfsr/axi4lite under `rtl/` |

Files without SPDX headers are covered by `license_file` (root-relative
license text that `fpga.provenance` verifies mentions the declared
license). Colibri files carry their own SPDX headers; keep
`license_file` set anyway for coverage of headerless helpers.

## CPU cores

| Core | Lib name | Language | License | Top module / selection |
|---|---|---|---|---|
| SERV | `serv` | Verilog | ISC | `components: ["serv_rf_top"]` (or `serving` — the full SoC wrapper); exclude `bench/**`, `servant/**`, `data/**` |
| PicoRV32 | `picorv32` | Verilog | ISC | `components: ["picorv32"]` — `picorv32_axi`/`picorv32_wb` variants in the same file; exclude `scripts/**`, `picosoc/**`, `testbench*.v` |
| NEORV32 | `neorv32` | VHDL | BSD-3 | `components: ["neorv32_top"]` or `["file_list_core.f"]`; exclude `rtl/test_setups/**`, `rtl/system_integration/**`; instantiate `entity neorv32.neorv32_top` |
| Hazard3 | `hazard3` | Verilog | Apache-2.0 | root = `hdl`; `components: ["hazard3_cpu_1port"]` (single-ported, SoC-friendly) or `["hazard3.f"]` |
| VexRiscv | `vexriscv` | Verilog | MIT | root = `pythondata_cpu_vexriscv/verilog`; every variant declares `module VexRiscv` — select with `files: ["VexRiscv_Lite.v"]` etc., not `components` |

Peripheral attach: SERV exposes a simple SRAM bus (`wb_*`/`mem_*`), PicoRV32
has native/WB/AXI-Lite variants, NEORV32 offers Wishbone+optional AXI4/XBUS,
Hazard3 uses AHB5, VexRiscv uses AXI4. Firmware (boot ROM/`$readmemh`
images) is out of scope for the contract's `libraries[]` — supply it via
`files:`-style design sources or a sibling firmware flow.

Units not usable via GHDL/Yosys/Gowin (verified by sweep): `serv/cv_96`
(Intel HPS), `neorv32 dmem/imem/cache_ram/imem_rom` (GHDL elaboration
limits — they synthesize inside `neorv32_top`), `neotrng` (ring-oscillator
latches), `neorv32_verilog_wrapper` (mixed-language helper),
`hazard3_ecp5_jtag_dtm`/`xilinx7_jtag_dtm` (vendor JTAGG/BSCANE2 cells).

## hdl-modules declaration order

Each used module is its own `libraries[]` entry whose VHDL library name
equals the module directory name. A `modules/<name>/src` tree holds the
RTL (`rtl/` holds netlist-build wrappers, not the RTL). Declare
dependencies before dependents:

1. `math` (leaf)
2. `common` — uses `resync` in `debounce`/`clock_counter`, and `resync`
   uses `common` in several `resync_*` units: a file-level cycle between
   the two libraries. Declaring both works only when the *resolved*
   closure does not cross both directions (e.g. `common` packages +
   `resync` units; avoid `debounce`/`clock_counter` together with
   `resync` units that need `common` packages). The resolver reports the
   violated direction.
3. `resync`
4. `axi`, `axi_lite`, `axi_stream`, `register_file`, `ring_buffer`,
   `fifo`, `dma_axi_write_simple`, `hard_fifo`, `lfsr`,
   `sine_generator` — depend on the layers above
   (`fifo` → `common`, `math`, `resync`).

`scripts/library_smoke.py` emits this order automatically; when unsure,
run it (see below).

## Units that do not synthesize via GHDL/Yosys for Gowin

Verified by a `synth_gowin` sweep of every unreferenced unit. Expected
misses — units requiring generics to elaborate (most `olo_fix_*`,
colibri `stream_*`/`axi*`, parameterized `hdl-modules` entities) — are
not listed; instantiate them inside a design instead.

| Unit(s) | Library | Reason |
|---|---|---|
| `wb_ram`, `wb_to_pipelined_wb` | colibri | latch inference unsupported by GHDL |
| `true_dpram` | colibri | base `true_dpram.vhdl` generate-instantiates the Xilinx variant whose code infers a latch; unusable via GHDL regardless of vendor selection |
| `aurora*`, `avst_cdc`, `synchro_handshake` | colibri | Intel/Xilinx FF init values + async resets `synth_gowin` cannot legalize |
| `hard_fifo` | hdl-modules | instantiates `unisim.vcomponents` primitives |
| `olo_base_ram_tdp`, `olo_base_ram_sdp` | open-logic | `Mem_v` multiple-assignment analysis error in GHDL |
| `olo_base_packet_fifo` | open-logic | `CONSTRAINT_ERROR` during analysis |
| `olo_intf_spi_master`, `olo_intf_uart_*` | open-logic | integer literal out-of-range / elaboration limits in GHDL |
| `dma_axi_write_simple` | hdl-modules | requires a generated register-record package not in the repo |
| `pipeline_buffer`, `mmap_fifo`, `interleaver` | hdl-modules | GHDL analysis limits (reference-before-elab, no-choice-for, >120 s) |

## Smoke-check a library set

`scripts/library_smoke.py` sweeps every unit that nothing else
references (the prospective tops) through `synth_<family>` inside the
fpga-tools container:

```bash
docker run --rm -v "$PWD":/repo -v out:/out -w /repo fpga-tools:dev \
    python3 scripts/library_smoke.py --family gowin --out /out/smoke
```

Options: `--libraries a,b` (sweep only those — dependencies are still
declared), `--contract path/to/x.fpga.json` (sweep a real contract's
libraries instead of the registry), `--family ice40|ecp5|gowin`,
`--timeout SEC`. A `results.json` and per-unit `synth.log` land under
`--out`. A `RESOLVE-FAIL` entry means `components`/`files` could not be
mapped to a compile list — fix the contract, not the library.

## Colibri licensing

Colibri is published under CERN-OHL-W-2.0 (a weakly reciprocal hardware
licence), with Apache-2.0 and CC-BY-SA-4.0 files in the repository.
Using the unmodified library inside a larger design is allowed; whoever
ships a product must keep the notices, and modifications to Colibri files
themselves must be made available under CERN-OHL-W-2.0. Keep the library
unmodified; if a change is needed, propose it upstream or record it in
the design notes so the obligation stays visible.

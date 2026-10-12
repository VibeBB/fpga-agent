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

## Colibri licensing

Colibri is published under CERN-OHL-W-2.0 (a weakly reciprocal hardware
licence), with Apache-2.0 and CC-BY-SA-4.0 files in the repository.
Using the unmodified library inside a larger design is allowed; whoever
ships a product must keep the notices, and modifications to Colibri files
themselves must be made available under CERN-OHL-W-2.0. Keep the library
unmodified; if a change is needed, propose it upstream or record it in
the design notes so the obligation stays visible.

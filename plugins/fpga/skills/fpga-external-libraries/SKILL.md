---
name: fpga-external-libraries
description: Using third-party HDL libraries such as the CERN Colibri VHDL library — pinned checkouts, contract library declarations, compile order, and license obligations (CERN-OHL-W-2.0).
version: 0.1.0
license: BSD-3-Clause
triggers:
  - colibri
  - library
  - ip core
  - ライブラリ
  - ライセンス
---

# External HDL libraries

External HDL is never copied into the design tree. Declare it in the
contract so the gates can compile it into its own VHDL library and record
its provenance:

```json
"libraries": [{
  "name": "colibri",
  "root": "../../third_party/colibri",
  "language": "vhdl",
  "files": ["src/io/uart/uart_rx.vhdl", "src/io/uart/uart_tx.vhdl", "src/io/uart/uart.vhdl"],
  "license": "CERN-OHL-W-2.0",
  "source_url": "https://gitlab.com/colibri-cern/colibri",
  "revision": "3fa784121ccea86d9e65b2e0dc08d2a3327f5f2f"
}]
```

- `files` are in compile order (dependencies first); take the order from
  the library's FuseSoC `.core` file.
- Instantiate with the library name: `library colibri;` and
  `entity colibri.uart`.
- `fpga.provenance` fails when a file is missing, lacks an SPDX header, or
  its SPDX identifiers do not match `license`.
- Fetch Colibri at the pinned revision with
  `python3 scripts/fetch_colibri.py` (writes `third_party/colibri`,
  gitignored). Do this on a networked host before running the gates in
  the network-isolated tools container.

## Colibri licensing

Colibri is published under CERN-OHL-W-2.0 (a weakly reciprocal hardware
licence), with Apache-2.0 and CC-BY-SA-4.0 files in the repository.
Using the unmodified library inside a larger design is allowed; whoever
ships a product must keep the notices, and modifications to Colibri files
themselves must be made available under CERN-OHL-W-2.0. Keep the library
unmodified; if a change is needed, propose it upstream or record it in
the design notes so the obligation stays visible.

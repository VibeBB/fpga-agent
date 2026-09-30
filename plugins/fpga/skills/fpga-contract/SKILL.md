---
name: fpga-contract
description: Authoring <name>.fpga.json — device profile, sources and VHDL libraries, clocks, pins, build outputs and budgets, simulations, formal runs, circuit link and programmer.
version: 0.1.0
license: BSD-3-Clause
triggers:
  - fpga.json
  - fpga contract
  - pin constraint
  - 制約ファイル
---

# FPGA contract

Schema version 1, strict: unknown keys are errors. Paths are relative to
the contract (POSIX, no absolute paths).

```json
{
  "schema_version": 1,
  "system": "fpga",
  "artifact_kind": "fpga_contract",
  "name": "uart-echo",
  "device": {"profile": "ice40-up5k-sg48", "ref": "U1"},
  "top": "uart_echo",
  "sources": [{"path": "rtl/uart_echo.vhdl", "language": "vhdl"}],
  "libraries": [],
  "clocks": [{"port": "clk", "frequency_mhz": 12}],
  "pins": [{"port": "clk", "package_pin": "35", "net": "CLK_12M"}],
  "build": {
    "dir": "build",
    "constraints": "build/uart-echo.fpga.pcf",
    "bitstream": "build/uart-echo.bin",
    "vhdl_standard": "08",
    "parameters": {},
    "seed": 1,
    "budget": {"logic_pct": 80, "ram_pct": 90}
  },
  "simulations": [],
  "formal": [],
  "circuit": {"connectivity": "circuit/board.firmware.json", "unused_pins": []},
  "programmer": {"board": "ice40_generic"}
}
```

- `sources[].language`: `vhdl`, `verilog` or `systemverilog`; one design
  language per contract. VHDL sources may set `library` (default `work`).
- Constraint suffix follows the family: `.fpga.pcf` (iCE40),
  `.fpga.lpf` (ECP5), `.fpga.cst` (Gowin). Bitstream suffix: `.bin`,
  `.bit`, `.fs`.
- `pins[].port` is a top-level port or a bit (`led[3]`). `io_standard` is
  set for ECP5/Gowin (iCE40 takes the bank VCCIO). `pull` is `up`, `down`
  or `none`; iCE40 has no pull-down.
- `pins[].acknowledge` lists `config` / `jtag` when a port deliberately
  uses such a pin; add a `rationale`.
- `build.parameters` sets top-level generics/parameters for synthesis.
- `simulations[]`: `runner` `nvc` (VHDL) or `iverilog` (Verilog),
  testbench `sources`, ordered `expect` lines, `forbid` lines, `timeout_s`,
  optional `waveform` (NVC FST) and `stop_time`.
- `formal[]`: `top`, `mode` (`prove`, `bmc`, `cover`), `depth`, `engine`,
  extra `sources`, and `parameters` to shrink generics for the proof.
- `programmer` names an openFPGALoader `board` or `cable`; `write_flash`
  writes SPI flash instead of SRAM.

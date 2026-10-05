# Commands

Slash commands under `plugins/fpga/commands/`; all delegate to the
launcher (`python3 <fpga plugin root>/scripts/fpga_launcher.py`) and allow
only `terminal`.

| command | runs | notes |
| --- | --- | --- |
| `doctor` | `fpga doctor` | probe the toolchain inside the pinned image |
| `design` | guided contract + pin plan | architect entry point |
| `gates` | `fpga gates <contract>` | authoritative run; inspect every returned PNG and record a vision review per image |
| `pinmap` | `fpga pinmap <contract>` | writes `*.fpga-pinmap.{json,md,png}` for the circuit agent; vision-review the render |
| `simulate` | `fpga sim <contract> --id <sim>` | transcript plus VCD waveform and its render; vision-review it |
| `verify` | review checklist | fpga-review entry point |
| `build` | `fpga build <contract>` | advisory synth/P&R/pack; vision-review the renders |
| `render` | `fpga render <contract> --view all` | re-render PNGs without rerunning tools (MCP `fpga_render`); one vision review per image |
| `liaison` | `fpga ux inbox` then `fpga ux respond --json <file>` | answer every `new`/`stale` UX request; report `blocked` and malformed files (MCP `fpga_ux_inbox`/`fpga_ux_respond`) |
| `records` | `fpga record status` | show records this session still owes (MCP `fpga_records_status`) |

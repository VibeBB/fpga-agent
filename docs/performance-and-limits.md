# Performance and limits

## Timeouts

| where | value |
| --- | --- |
| tool subprocesses (`src/fpga/flow.py` `TOOL_TIMEOUT_S`) — lint, synth, P&R, pack, simulation compile/run | 1800 s |
| per-simulation `timeout_s` (contract field) | default 120 s, max 3600 s |
| per-formal-run `timeout_s` (contract field) | default 300 s, max 7200 s |
| launcher `docker image inspect` | 30 s (`_INSPECT_TIMEOUT_S`) |
| launcher `docker pull` | 900 s (`_PULL_TIMEOUT_S`) |
| launcher attestation fetch | 120 s (`_ATTEST_TIMEOUT_S`) |
| launcher `gh auth status` | 15 s (`_GH_AUTH_TIMEOUT_S`) |
| `fpga program` openFPGALoader run | 600 s |

## Render caps (`src/fpga/render.py`)

| cap | value |
| --- | --- |
| canvas dimension | 4096 px (`MAX_DIM`) |
| VCD file size | 64 MiB (`VCD_MAX_BYTES`; larger captures render `TRUNCATED`) |
| VCD value changes | 2 000 000 (`VCD_MAX_CHANGES`; over the cap → truncated render) |
| waveform rows | 32 signals (`MAX_WAVE_ROWS`) |
| text scale | ≥ 2 (`MIN_TEXT_SCALE`); signal labels capped at 32 chars |

## MCP image caps (`src/fpga/mcp_server.py`)

At most 8 inline PNGs per tool call (`_MAX_IMAGES`), each ≤ 4 MiB
(`_MAX_IMAGE_BYTES`); larger or extra images are listed in `image_notes`
and left on disk under `fpga-reports/`.

## Records caps (`src/fpga/records.py`)

impression ≥ 400 chars and ≥ 3 distinct sentences; decision rationale
≥ 200 chars; principle ≥ 12 chars; question ≥ 10 chars; stop-hook denials
capped by `records-policy.json` `max_stop_denials` (2).

## Structural limits

- Families: Lattice iCE40, Lattice ECP5, Gowin GW1N/GW2A via nextpnr
  `ice40`/`ecp5`/`himbaechel`. No vendor tools.
- HDL: VHDL-2008 (GHDL plugin + NVC) and Verilog/SystemVerilog
  (Verilator lint, Icarus sim).
- Single-corner static timing from the nextpnr report; no multi-corner
  STA or power estimation ([improvement notes](improvement-notes.md)).
- The placed-JSON floorplan only knows BEL coordinates (no die outline,
  congestion or wire density); when nextpnr writes unparseable JSON the
  view degrades to a regex scan that still pairs each `type` with its
  `NEXTPNR_BEL` so cell classes survive.
- `fpga program` is host-only, human-confirmed, and never a gate or MCP
  tool.

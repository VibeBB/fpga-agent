# Records and vision

The VibeBB Record Protocol (VRP) v1 gives the agent an auditable,
append-only evidence trail under `observations/fpga/`:

- `decisions.jsonl` — why a non-trivial choice was made (device profile,
  clock pin, pin moves, I/O standard, reset/CDC strategy, FSM encoding,
  library adoption, verification coverage, budget/seed changes, how a
  failing gate was fixed, every UX-creator answer),
- `impressions.jsonl` — a ≥400-character, ≥3-sentence stage impression,
- `vision-reviews.jsonl` — findings plus a long-form impression after
  looking at any image,
- `vision-tool-events.jsonl` / `image-observations.jsonl` — hook-written
  observations a review can cite via `source_event_id`,
- `records-status.json` — the last Stop-hook verdict.

Records are written by `fpga_record_decision` / `fpga_record_impression` /
`fpga_record_vision_review` (CLI `fpga record ...`) and inspected with
`fpga_records_status`. The Stop hook (`require-records`) refuses to finish
a session that still owes records (up to `max_stop_denials` denials, then
the status file records the debt). Records are advisory evidence: they
never change a gate verdict.

## Vision points

Every image-producing tool (`fpga_gates`, `fpga_build`, `fpga_sim`,
`fpga_pinmap_export`, `fpga_render`) returns its PNG renders inline —
up to 8 images per call, each ≤ 4 MiB — and the files stay under
`fpga-reports/`. When the model cannot see the inline image it calls
`inspect_image_with_vision` (`VisionInspectTool`) or reports that it could
not look and decides from the JSON report alone.

| render | look for |
| --- | --- |
| `<name>.fpga-pinmap.png` | every port on its package pin and net, clocks on clock-capable pins, acknowledged caution pins, awkward banks/neighbours |
| `<name>.fpga-floorplan.png` | clustered placement, I/O logic near its pins, no spread hinting at a long critical path |
| `<name>.fpga-utilization.png` | headroom per budget, unexpected RAM/DSP inference |
| `<name>.fpga-timing.png` | slack per clock, worst-path endpoints, margin for temperature/voltage/the next feature |
| `<name>.fpga-wave-<sim>.png` | protocol timing matches the spec, no `x`/`z` after reset, the testbench exercises its `expect` claims |
| `<name>.fpga-report.png` | overall verdict and which stage a failure points back to |

A render that contradicts the JSON report is a finding against the
renderer — never a reason to change a verdict.

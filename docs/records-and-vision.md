# Records and vision

The VibeBB Record Protocol (VRP) v2 gives the agent an auditable,
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

Render legibility is part of the contract with the vision model: text is
a classic 5x7 font (real lowercase, so HDL/VCD names keep their case) at
scale ≥ 2, pads and columns are sized from the longest content, and every
canvas carries `layout_problems()` — an assertion the tests run on every
view so text never overlaps, covers a bar or leaves the canvas. Waveform
labels are scope-qualified when names collide (`inner.tx [8]`), the time
axis uses engineering units (`0 us .. 200 us`), `$var string` values
(NVC enums/booleans) draw as labelled bus boxes, and perimeter packages
draw every package pin — user I/O or not — with a legend entry for every
colour used.

A render that contradicts the JSON report is a finding against the
renderer — never a reason to change a verdict.

## VRP v2 logs

`observations/fpga/` holds `decisions.jsonl`, `impressions.jsonl`,
`vision-reviews.jsonl`, `reconciles.jsonl`, `insights.jsonl`, `reads.jsonl`
and `song-receipts.jsonl`. Every line carries `schema_version` 2, `sequence`,
`prev_event_id`, `writer` and `event_id` (the SHA-256 of the canonical
record). The writer verifies the chain before appending and refuses a log
that was edited, truncated or reordered; readers report such a log under
`integrity_problems` and never resolve references into it. A log written
entirely by VRP v1 is renamed to `<name>.v1.jsonl` on the first v2 write.

Impressions carry facets (`observed`, `works`, `concerns`, maker/user
`feelings`, `next_actions`), two or more claims quoting exact tokens from the
bound artifacts, and a confidence; a near copy of an earlier impression, or
a concern a sister already disputed, is refused. Taking in a sister artifact
needs a `fpga_record_read` receipt and an `upstream` entry.

## Blind review

`fpga-reports/*.png` renders are dual-review images (`dual_review_globs`
in `records-policy.json`). After the primary review, `fpga-blind-review`
reviews the same image without seeing it (`reviewer: "blind"`), and the
caller records `fpga_record_reconcile` over `[primary, blind]`. A split goes
to one tiebreak round (`[primary, blind, tiebreak]`); a split after the
tiebreak stays `unknown` and never becomes pass.

## Insights, songs, digest

`fpga_record_insight` moves an insight through
tried/adopted/rejected/deferred/superseded. fpga only receives bard songs:
`fpga_record_song_receipt` records one receipt per
`liaison/<id>.bard-song.json` (sha256-pinned, never a gate input, never a
request for another song; the song file is protected from edits).
`fpga_records_digest` and `fpga_records_search` read every plugin's
impressions in the workspace.

# MCP tools

`fpga.mcp_server` is a stdio server exposing the same payload functions as
the CLI. Every tool returns a JSON payload with `verdict` plus
`TextContent`; image-producing tools append up to 8 `ImageContent` PNGs
(each ≤ 4 MiB; skipped images are noted in `image_notes`). A thrown
exception becomes `isError` with `verdict: fail` — the transport fails
closed. Read-only tools set `readOnlyHint`.

| tool | inputs (required bold) | effect / output | errors |
| --- | --- | --- | --- |
| `fpga_doctor` | — | tool versions, `verdict` | read-only |
| `fpga_validate` | **contract_path** | parsed contract summary | fail on bad schema |
| `fpga_check` | **contract_path**, out_dir | static gates report | writes reports dir |
| `fpga_gates` | **contract_path**, out_dir | full gate report + `renders` + `images` (pinmap/report/utilization/timing/floorplan/waveform PNGs) | any check fail → `fail` |
| `fpga_constraints` | **contract_path** | rewrites the contract's constraint file | fail on bad contract |
| `fpga_pinmap_export` | **contract_path**, out_dir | `*.fpga-pinmap.{json,md,png}` + images | fail on bad contract |
| `fpga_regmap_export` | **contract_path**, out_dir | `registers.hdl_package` + `*.fpga-regmap.json` | fail on bad contract or no `registers` |
| `fpga_production_export` | **contract_path**, out_dir | `<name>.fpga-production.json` for production-engineering-agent | no passing full gate report, changed contract/bitstream or no programmer → `fail` |
| `fpga_lint` | **contract_path**, out_dir | lint transcript | tool failure → `fail` |
| `fpga_sim` | **contract_path**, **simulation**, out_dir | matched/missing `expect` lines, transcript, `sim-<id>.vcd` + wave PNG | unknown id → `fail` |
| `fpga_formal` | **contract_path**, **formal**, out_dir | prove/bmc/cover status + transcript | unknown id → `fail` |
| `fpga_build` | **contract_path**, out_dir | implementation checks + renders + images | advisory |
| `fpga_request` | **contract_path**, **target**, **risk**, **change**, **rationale**, **decision_refs**, nets, failing_checks, inputs, out_dir | writes `<design>.<id>.fpga-request.json` (v2) | unverifiable/missing decision_ref or input → `fail` |
| `fpga_profile` | profile | bundled ids or one profile | unknown id → `fail` |
| `fpga_render` | **contract_path**, view, out_dir | `rendered`/`skipped` lists + images | never fails on render errors |
| `fpga_record_decision` | DecisionInput fields | appended decision record + `event_id` | validation → `fail` |
| `fpga_record_impression` | StageImpressionInput fields | appended impression record | prose check → `fail` |
| `fpga_record_vision_review` | VisionReviewInput fields | appended vision-review record | needs image_path or source_event_id |
| `fpga_records_status` | — | counts per log + last stop verdict | read-only |
| `fpga_ux_inbox` | workspace | request states new/answered/stale/blocked, malformed files | read-only |
| `fpga_ux_respond` | **request**, **status**, reason, artifacts, gate_verdicts, gate_report, decision_refs, impression_refs, questions_for_user, workspace | writes `liaison/<id>.ux-response.json` | every refusal rule → `fail` |

Board programming (`fpga program`) is deliberately **not** exposed over
MCP; it is a host-only CLI command.

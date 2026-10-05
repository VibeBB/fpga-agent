# Agents

Three AgentDefinitions under `plugins/fpga/agents/`. All declare
`terminal`, `file_editor`, `grep`, `glob`, `task_tracker` and
`VisionInspectTool`, mount the `fpga` MCP server, and run the
`protect-generated`, `safety-rail`, `deny-programming`,
`record-vision-tool-event` and `record-image-observation` hooks. All three
carry the mandatory "Records you must leave" section and the vision-points
table for the renders.

## fpga-architect

Owns `<name>.fpga.json`: picks the device profile, assigns package pins,
I/O standards and clocks, declares external HDL libraries, and reconciles
the pin map with the circuit connectivity artifact. Runs `fpga check`
until the static gates pass, writes `fpga request` artifacts for the
circuit agent when the board must change, and owns the UX-creator liaison:
`fpga_ux_inbox` at session start, answers via `fpga_ux_respond` with hashed
artifacts, gate verdicts and record references. Delegates RTL work to
fpga-developer and independent review to fpga-review when loaded.

## fpga-developer

Implements HDL for an existing contract: top-level ports must match the
contract pins exactly (the `fpga.netlist_match` gate compares them),
constraints are regenerated from the contract, every behavior gets a
self-checking testbench and every invariant a formal property. Runs
`fpga gates` until all checks pass; opens the waveform, floorplan, timing
and utilization renders before touching RTL for a failure and records what
the picture showed in the decision. Never programs a board.

## fpga-review

Read-only review (`permission_mode: never_confirm`, no edits): re-runs
`fpga gates`, checks the contract (acknowledged config pins, clock-capable
pins, un-loosened budgets), verification depth, RTL hazards the gates
cannot see, and provenance of external libraries. Then inspects every
render under `fpga-reports/` — a render that contradicts the JSON report
is a finding against the renderer, not a reason to change the verdict —
and verifies `fpga_records_status` owes nothing and answered UX requests
are `answered`, not `stale`.

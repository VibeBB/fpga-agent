# ADR-0010 — VRP records, PNG renders, SLP v2 liaison, fail-closed launcher

## Status

Accepted.

## Context

The fpga plugin produced verdicts but no auditable reasoning, no images an
agent could look at, no waveform an agent could read (NVC emitted FST), a
launcher that silently fell back to host tools, outbound sister requests
without hashed inputs or justification, and no liaison channel with
UX-creator.

## Decision

1. **VRP v1 records** (`src/fpga/records.py`, ported from wire-agent):
   append-only `decisions.jsonl`, `impressions.jsonl`,
   `vision-reviews.jsonl` plus hook-written observation logs under
   `observations/fpga/`; the shared `require_records.py` Stop hook
   re-validates the logs and refuses to finish a session that still owes
   records. Records are advisory and never change a verdict.
2. **Stdlib PNG renders** (`src/fpga/render.py`): a self-contained
   canvas/PNG writer renders pin map, utilization, timing, floorplan,
   per-simulation waveform (from VCD) and a report card; MCP tools attach
   up to 8 PNGs ≤ 4 MiB as `ImageContent`. Render failures are evidence
   notes, never verdicts. GateReport schema_version 2 carries `renders`.
3. **VCD everywhere**: NVC writes `--format=vcd`; Icarus runs compile a
   generated `fpga_wave_dump.v` that `$dumpvars` the sim top. The contract
   no longer ties `waveform` to NVC.
4. **SLP v2 liaison** (`src/fpga/liaison.py`): strict local mirrors of
   UX-creator's request/response schema (schema_version 2), `inbox` triage
   (`new`/`answered`/`stale`/`blocked`) and `respond` with fail-closed
   refusal rules (stale inputs, unverifiable record refs, unproven
   `done`). The mirror cannot validate UX-side job-id citations —
   documented asymmetry.
5. **Fail-closed launcher**: `plugins/fpga/scripts/fpga_launcher.py` runs
   every command except `program` inside the pinned `fpga-tools` image;
   when no image resolves, exit 1 (`--warn` exits 0 with a fail payload).
   `program` stays host-only and human-confirmed.
6. **Interchange v2**: `FpgaRequest` gains hashed `inputs` and required
   `decision_refs`; `FpgaPinmap` gains `circuit_sha256`.

## Consequences

- A session cannot end without its decision/impression/vision trail.
- Agents can look at everything they produce; vision reviews are bound to
  image bytes or hook event ids.
- No third-party runtime dependencies were added (stdlib + pydantic +
  mcp only).
- Intermediate git commits for this refactor are not individually green
  (the feature spans files that several steps touched); the pushed head
  is the verified state.
- Known render limitations and open items are tracked in
  [improvement-notes](../improvement-notes.md).

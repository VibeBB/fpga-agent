# Sister cooperation

Two JSON channels, never code imports; the agent never edits a sibling's
inputs.

## SLP v2 — UX-creator liaison (`src/fpga/liaison.py`)

UX-creator drops `liaison/<id>.ux-request.json` files in the workspace.
`fpga ux inbox` (MCP `fpga_ux_inbox`) triages them:

- `new` — unanswered request addressed to `fpga`,
- `answered` — a valid `liaison/<id>.ux-response.json` with
  `responder: "fpga"` and `request == id` exists,
- `stale` — any request input's current sha256 differs from the request
  (missing counts) or from the response's `input_hashes`,
- `blocked` — a `depends_on` id has no valid response file (any
  responder).

Malformed files land in `malformed[]`: request files when the raw
`target_agent` is `fpga`, missing, or unreadable (requests aimed at other
agents are skipped silently), and every response file whose JSON or
schema is broken or whose `request` does not match the file stem.

Both `inbox` and `respond` resolve `workspace` inside
`workspace_root()` — a path outside the root is a ValueError, and
`respond` only writes inside the workspace. `stale` also covers changed
deliverables: a response artifact whose tree-hash no longer matches puts
the request back in `stale` and lists it in `changed_artifacts`.

`fpga ux respond --json <file>` (MCP `fpga_ux_respond`) writes
`liaison/<id>.ux-response.json` and refuses (ValueError / MCP isError /
CLI exit 1) when: the request is missing, malformed, or not for `fpga`;
an artifact path is missing, outside the workspace, or behind a symlink;
a `decision_ref`/`impression_ref` is not a real record event_id; the
status is `done` while any gate verdict is fail/unknown; `done` lacks an
artifact, a gate verdict, a decision_ref or an impression_ref; or any
request input went stale while answering `done`/`accepted`/`in_progress`.
`gate_report` loads a `*.fpga-report.json`, maps check statuses
(pass→pass, fail→fail, else unknown; `not_applicable` skipped) and adds
the report itself to the artifacts. Directory artifacts are hashed with
the records tree-hash. `input_hashes` holds the current sha256 of every
existing request input (missing ones become warnings).

The mirror is strict but cannot validate the UX producer's job-id
citations (UX-creator owns that contract) — a documented asymmetry.

## Outbound requests (`src/fpga/requests.py`, schema v2)

`fpga request` / `fpga_request` writes `<design>.<id>.fpga-request.json`
for one of the ten siblings (`bard`, `circuit`, `dashboard`, `doc`,
`firmware`, `mech`, `prodeng`, `sim`, `wire`, `ux-creator`). The request
always carries the contract's sha256 in `inputs`, any extra hashed input
files (`--input`), and ≥1 `decision_refs` validated against
`observations/fpga/decisions.jsonl` — a request without a recorded
justification cannot be written.

## simulation-agent thermal handoff (`src/fpga/sim_thermal.py`)

The FPGA package is often the hottest part on the board, and only
simulation-agent solves junction temperature. A contract with a `thermal`
section hands it over:

1. `fpga sim-request <contract> [--out DIR]` / `fpga_sim_thermal_request`
   writes `<name>.thermal.sim.json` and `<name>.thermal.sim-request.json`
   (default `fpga-reports/`, which must be inside the workspace).
2. simulation-agent answers with `sim respond <request>`, writing
   `<name>.thermal.sim-response.json` beside the request and a hashed
   `sim-report.json`.
3. `fpga.sim_thermal` (every `check`/`gates` run) and `fpga sim-check` /
   `fpga_sim_thermal_check` read `thermal.response_path`:
   - request file changed, not an fpga/thermal request, request ID or brief
     sha256 the **current** contract would not emit (stale), report changed,
     or report/response verdict mismatch → fail;
   - response unset, missing or malformed, `needs_info`/`deferred`, report
     missing or outside the workspace → `unknown` (`sim-check`) — the binary
     fpga gate fails closed with an `unknown:` detail;
   - otherwise each simulation `thermal.*` result is reported with
     simulation's verdict, measured temperature, limit, margin and guidance.
     A simulation fail is never promoted.

## Inbound circuit data

`contract.circuit.connectivity` links the circuit plugin's connectivity
export; `fpga.netlist_match` checks every pin lands on its circuit net and
the pinmap export records `circuit_sha256` so the circuit agent can see
exactly which export the pin map was checked against.

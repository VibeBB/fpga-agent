# Improvement notes

Done in this refactor:

- No design-rationale/impression/vision records → VRP v1 (`records.py`,
  `require-records` Stop hook, `records-policy.json`).
- No images for vision review → stdlib PNG renders (pin map, floorplan,
  utilization, timing, waveform, report) returned inline by MCP.
- Waveforms were NVC-only FST, unreadable by agents → VCD for NVC and
  Icarus (`fpga_wave_dump.v` wrapper), rendered to PNG.
- Launcher silently fell back to host tools → fail-closed Docker-only
  (`program` stays host/human-only).
- FPGA→sister requests had no input hashes or decision refs → request
  schema v2 with sha256 inputs and required VRP decision_refs.
- Pin map export did not bind the circuit export it was checked against →
  `circuit_sha256`.
- No UX-creator liaison → SLP v2 `liaison/*.ux-request|response.json`,
  `fpga_ux_inbox`/`fpga_ux_respond`.
- Sparse docs → full `docs/` tree and a README rewritten for
  non-engineers.

Discovered while building:

- nextpnr's `--write` output is not strict JSON: HDL attribute strings
  (e.g. `altera_attribute`) embed raw quotes, so the ice40 `*.placed.json`
  can fail `json.loads`. The floorplan render degrades to a regex scan of
  `NEXTPNR_BEL` values; anything else that needs the placed netlist must
  sanitize first.
- nextpnr `critical_paths` is a list of `{from, to, path[]}` entries, not
  a per-net dict — the timing render accepts both shapes.
- Normalized-AST sha256 of the shared hooks is Python-version-sensitive;
  `check_shared_hooks.py` must run under `uv run` (Python 3.14), not the
  system Python.
- Devin's exported `gh` shell function breaks the stub-gh tests; run
  pytest via `env -u BASH_ENV -u "BASH_FUNC_gh%%"`.

Open (outside this refactor or needs upstream):

- Multi-corner STA / hold analysis: nextpnr reports a single corner; no
  open tool for Gowin/ECP5 multi-corner sign-off.
- Power estimation: no open-source power model for iCE40/ECP5/Gowin.
- Floorplan render uses BEL coordinates only; no die outline, routing
  congestion or wire density.
- High-risk UX request job-id citation can only be validated by
  UX-creator (it owns the contract jobs).
- Hardware-in-the-loop evidence after human programming (logic analyzer
  capture intake) is a manual vision step.

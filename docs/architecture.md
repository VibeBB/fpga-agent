# Architecture

fpga-agent is a deterministic Python core (`src/fpga/`, Python 3.12,
stdlib + pydantic v2 + mcp) wrapped by an OpenHands plugin
(`plugins/fpga/`). Every public function of `src/fpga` is listed below.

## Module map

```text
src/fpga/
├── contract.py    # FpgaContract schema — the source of truth
├── devices.py     # generated DeviceProfile models + loaders
├── interchange.py # circuit connectivity input + fpga_pinmap/fpga_regmap output schemas
├── hdl.py         # HDL unit ordering, VHDL/Verilog arg builders
├── flow.py        # lint / synth / P&R / pack subprocess flows
├── sim.py         # simulation runners (NVC, Icarus) + VCD capture
├── formal.py      # SymbiYosys run generation and driver
├── gates.py       # authoritative gate checks + GateReport v2
├── render.py      # stdlib PNG renderer: pinmap/utilization/timing/
│                  # floorplan/waveform/report views
├── records.py     # VibeBB Record Protocol v1 writers and loaders
├── liaison.py     # SLP v2 UX-creator request/response handling
├── requests.py    # outbound *.fpga-request.json (schema v2)
├── projections.py # constraint-file and pinmap text projections
├── regmap.py      # register map: fpga_regmap export, HDL constants, binding check
├── program.py     # host-only openFPGALoader planning
├── doctor.py      # toolchain probe
├── toolrun.py     # subprocess runner with timeout + transcript
├── workspace.py   # workspace path validation (no escapes, no symlinks)
├── service.py     # payload functions shared by CLI and MCP
├── cli.py         # python -m fpga <command>
└── mcp_server.py  # stdio MCP boundary
```

`plugins/fpga/scripts/fpga_launcher.py` is the single exec point for hooks,
commands and the MCP server: it runs `python -m fpga` inside the pinned
`fpga-tools` image resolved from `$FPGA_TOOLS_IMAGE`, `tools-image.json` or
the digest lock, and fails closed when no image resolves. `program` is the
exception — it always execs on the host.

## Public API reference

### contract.py
`Device`, `Source`, `Library`, `Clock`, `Pin`, `Budget`, `Build`,
`Simulation`, `Formal`, `CircuitLink`, `Programmer`, `FpgaContract`;
`load_contract(path)`, `resolve(contract_path, relative)`,
`library_files(contract_path, library)`.

### devices.py
`DevicePin`, `DeviceProfile`; `bundled_ids()`,
`load_profile(profile_id, search_dirs)`.

### interchange.py
`CircuitDevicePin`, `CircuitDevice`, `CircuitConnectivity`, `PinmapEntry`,
`FpgaPinmap`; `sha256_file(path)`, `load_circuit(path)`.

### hdl.py
`Unit`; `units(...)`, `all_files(unit_list)`, `is_systemverilog(unit_list)`,
`param_text(value)`, `vhdl_generic(value)`, `ghdl_args(...)`,
`verilog_read(contract, unit_list, formal=)`.

### flow.py
`Paths`; `paths(contract, contract_path, profile)`, `nvc_std(contract)`,
`nvc_analyse(...)`, `nvc_elaborate_argv(...)`,
`lint(contract, contract_path, out_dir)`,
`synth_script(contract, contract_path, profile)`, `synthesize(...)`,
`netlist_ports(netlist, top)`, `pnr_argv(contract, contract_path, profile)`,
`placed_json(out, family)`, `place_and_route(...)`, `pack(...)`,
`load_report(report)`, `bitstream_problems(family, data)`, `sha256(path)`.
Constant: `TOOL_TIMEOUT_S = 1800`.

### sim.py
`SimResult`; `progress(lines, expect)`,
`run_simulation(contract, contract_path, sim, out_dir)` — NVC sims write
`sim-<id>.vcd` via `--wave --format=vcd`; Icarus sims compile a generated
`fpga_wave_dump.v` with `$dumpvars(0, <top>)`.

### formal.py
`FormalResult`; `sby_text(contract, contract_path, run)`, `run_formal(...)`.

### gates.py
`RenderRef`, `Check`, `GateReport` (schema_version 2; includes `renders`);
`contract_files`, `check_contract`, `spdx_ids`, `check_provenance`,
`check_pins`, `check_constraints`, `check_netlist_match`,
`check_synth_ports`, `check_timing`, `check_utilization`, `check_bitstream`,
`sim_thermal_checks` (`fpga.sim_thermal`, static scope, only with `thermal`),
`run_gates(contract_path, out_dir, full=)`, `simulation_checks`,
`formal_checks`, `implementation_checks`, `report_markdown(report)`,
`write_outputs(contract_path, report, out_dir)` — writes the JSON/Markdown
report, the pin map export, and `*.fpga-pinmap.png` / `*.fpga-report.png`.

### sim_thermal.py
`SimResponse` (strict mirror of simulation-agent `SimulationResponse` v2),
`thermal_brief`, `expected_request`, `write_sim_request`, `resolve_response`,
`thermal_findings`, `thermal_check` — the FPGA package thermal handoff.

### render.py
`Canvas` (fill_rect, rect, line, 5x7 text, `png_bytes()` — deterministic
RGB8 filter-0 zlib output, dimension cap `MAX_DIM = 4096`);
`write_png(canvas, path)`; view renderers `pinmap_canvas`,
`utilization_canvas`, `timing_canvas`, `floorplan_canvas`, `waveform_canvas`,
`report_canvas`; `VcdSignal`, `parse_vcd(path)`;
`render_view_pngs(contract, profile, out_dir, *, build_dir, views,
gate_report_path)` returning `(rendered, skipped)` and never raising;
`skipped_note(view, reason)`, `related_check(view)`.
Caps: `VCD_MAX_BYTES = 64 MiB`, `VCD_MAX_CHANGES = 2_000_000`,
`MAX_WAVE_ROWS = 32`.

### records.py
Models: `ArtifactRef`, `EvidenceRef`, `DecisionOption`, `EvidenceInput`,
`DecisionInput`, `StageImpressionInput`, `VisionFinding`,
`VisionReviewInput`, `DecisionRecord`, `StageImpression`, `VisionReview`.
Writers: `record_decision`, `record_impression`, `record_vision_review`
(each `(payload, root=None)`), `RECORDERS`. Helpers: `sentence_count`,
`impression_is_prose`, `sha256_file`, `tree_sha256`, `records_dir`,
`decision_event_ids`, `impression_event_ids`, `records_summary`.
Constants: `PLUGIN`, `SCHEMA_VERSION`, `RECORDS_DIR`,
`IMPRESSION_MIN_CHARS` (400), `IMPRESSION_MIN_SENTENCES` (3),
`RATIONALE_MIN_CHARS` (200), `PRINCIPLE_MIN_CHARS` (12),
`QUESTION_MIN_CHARS` (10), `LOG_FILES`, `SKIP_PARTS`.

### liaison.py
`InputRef`, `GateVerdict`, `UxRequest`, `UxResponse` (schema v2, strict);
`liaison_dir(root)`, `inbox(workspace=None)` returning request states
(`new`/`answered`/`stale`/`blocked`) plus `malformed` entries;
`respond(workspace, request_id, status, *, reason, artifacts,
gate_verdicts, gate_report, decision_refs, impression_refs,
questions_for_user)` — writes `liaison/<id>.ux-response.json` or raises
`ValueError` on every refusal rule.

### requests.py
`RequestInput`, `FpgaRequest` (schema v2: `inputs` with sha256, required
`decision_refs`); `slug(text)`, `write_request(contract_path, design,
out_dir, *, target, risk, change, rationale, nets, failing_checks,
extra_inputs, decision_refs, root)`.

### projections.py
`constraints_text(contract, profile)`, `pinmap_export(contract, profile,
contract_sha256, circuit_sha256=None)`, `pinmap_markdown(pinmap)`,
`write_text(path, text)`.

### regmap.py
`regmap_export(contract, contract_sha256)`, `package_name(contract)`,
`hdl_package_text(contract)` (VHDL package or Verilog include, chosen by
the design language), `regmap_problems(contract, contract_path)` — the
`fpga.regmap` gate's missing/stale/unused checks.

### program.py
`ProgramPlan`; `plan(contract, contract_path, out_dir, confirm_sha256)` —
requires a passing gate report and a matching bitstream hash.
`gated_bitstream(...)` holds that check; `production_export(contract,
contract_path, profile, out_dir)` reuses it to build the
`fpga-production.json` handoff without touching hardware.

### doctor.py
`ToolCheck`; `checks()`.

### toolrun.py
`ToolRun`; `run_tool(argv, cwd, log, timeout_s)`.

### workspace.py
`workspace_root()` (`OPENHANDS_PROJECT_DIR` or cwd),
`workspace_path(value, root=None)` — rejects `..` escapes and symlinks.

### service.py
`default_out(contract_path)`; payloads: `doctor_payload`,
`validate_payload`, `gates_payload(contract_path, out_dir, full=)`,
`constraints_payload`, `pinmap_payload`, `sim_payload`, `formal_payload`,
`lint_payload`, `build_payload`, `program_payload`, `request_payload`,
`render_payload(contract_path, out_dir, view)`, `ux_inbox_payload`,
`ux_respond_payload`, `profile_payload`. Image-producing payloads add
`images` (PNG paths) and `render_errors`; renders never change verdicts.

### cli.py
`main(argv=None)` — subcommands: `doctor`, `validate`, `check`, `gates`,
`constraints`, `pinmap`, `lint`, `sim`, `formal`, `build`, `program`,
`request`, `profile`, `record`, `render`, `ux inbox`, `ux respond`.
Exit 0 only on `verdict: pass`.

### mcp_server.py
`server`, `TOOLS`, `tool_specs()`, `dispatch(name, arguments)`, `main()`.
Inline image caps: at most 8 PNGs per call, each ≤ 4 MiB; skipped images are
listed in `image_notes`.

# Workflow

The agent works in stages; each stage ends with generated artifacts and a
mandatory stage impression record (see [records-and-vision](records-and-vision.md)).

| stage | what happens | records left |
| --- | --- | --- |
| `requirements` | read the brief and the circuit connectivity export; confirm values read off images with the user | decision (device/profile choice), stage impression |
| `pin-plan` | author `<name>.fpga.json`, pick the device profile, assign package pins, generate constraints, run `fpga check` | decisions (clock pin, pin moves, I/O standards), stage impression, pin map render + vision review |
| `rtl` | write HDL and self-checking testbenches (PSL/SVA under `ifdef FORMAL`) | decisions (FSM encoding, CDC strategy, library adoption), stage impression |
| `verification` | `fpga sim` / `fpga formal` per declared run | decisions (coverage), stage impression, waveform renders + vision reviews |
| `implementation` | `fpga gates` — lint, synth, P&R, timing, utilization, bitstream | decisions (how failures were fixed), stage impression, utilization/timing/floorplan renders + vision reviews |
| `review` | fpga-review re-runs gates and inspects the contract, evidence depth and renders | vision reviews per render, records-completeness check |
| `liaison` | answer UX-creator requests | decision + impression referenced by the response, `liaison` stage impression |

## Gate discipline

`fpga gates` is the authoritative run. Missing tools, missing files and
unparseable output are failures, never skips. Renders are produced after the
toolchain checks and are best-effort: a render failure becomes an evidence
note on the related check and never changes the verdict.

## VCD waveforms

Every simulation declared `waveform: true` produces `fpga-reports/sim-<id>.vcd`
— NVC writes VCD natively; for Icarus the runner compiles a generated
`fpga_wave_dump.v` wrapper that calls `$dumpvars(0, <top>)`. The waveform
render `<name>.fpga-wave-<id>.png` shows scalars as 0/1/x/z traces and buses
as hex boxes (band rendering for dense signals, `TRUNCATED` marker when the
capture exceeds the caps).

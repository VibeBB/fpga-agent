# ADR-0001: Python core with JSON contracts and deterministic gates

- Status: accepted
- Date: 2026-09-30

## Context

VibeBB plugins share one convention: a strict JSON contract is the source
of truth, a Python package (stdlib + pydantic v2 + mcp) judges it, and
OpenHands agents, commands and skills are Markdown that delegate every
executable step to that package. FPGA development needs the same
auditable shape on top of large native toolchains.

## Decision

- `<name>.fpga.json` (`artifact_kind: fpga_contract`) holds the device
  profile, top, sources, libraries, clocks, pins, build, simulations and
  formal runs. Unknown keys are rejected.
- `src/fpga/` implements every gate. Tools are subprocesses whose exit
  codes, transcripts and JSON reports are parsed; anything missing or
  unparseable fails.
- Device knowledge is versioned JSON (`src/fpga/devices/*.json`)
  generated from the open device databases, so every pin, bank, clock
  capability and configuration/JTAG caution is traceable to data rather
  than transcription.
- Constraint files (PCF, LPF, CST) are deterministic projections of the
  contract; the `fpga.constraints` gate compares them byte for byte.
- The CLI and the MCP server share `service.py` payloads; every payload
  carries a `verdict` and the CLI exits 0 only on `pass`.

## Consequences

- Adding a part is a profile extraction plus tests, not code.
- Verdicts are reproducible from the contract, sources and the pinned
  tools image; reports record the contract, circuit and bitstream hashes.

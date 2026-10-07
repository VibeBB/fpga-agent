# fpga-agent documentation

Start with the repository [README](../README.md) for the product overview.

## Guides

- [Architecture](architecture.md) — module map and public API reference
- [Workflow](workflow.md) — stages, what happens, records left
- [Agents](agents.md) — fpga-architect, fpga-developer, fpga-review
- [Skills](skills.md) — the plugin skills and when they apply
- [Commands](commands.md) — the slash commands
- [MCP tools](mcp.md) — every tool: inputs, outputs, errors, read/write
- [Hooks](hooks.md) — session_start / pre / post / stop hook behavior
- [Contracts](contracts.md) — every JSON schema the repo reads or writes
- [Records and vision](records-and-vision.md) — the VibeBB Record Protocol
- [Sister cooperation](sister-cooperation.md) — SLP v2 liaison + interchange
- [Performance and limits](performance-and-limits.md) — timeouts and caps
- [Operations](operations.md) — images, pins, releases
- [Development](development.md) — verification commands and setup
- [Test coverage and test design](test-coverage.md) — C0/C1/C2/MCC/MC/DC and boundary coverage, floors, test-design techniques
- [Improvement notes](improvement-notes.md) — known gaps and open work
- [Dependency updates](dependency-updates.md) — pinned-version policy

## Architecture decision records

- [ADR-0001](adr/ADR-0001-python-core-json-contracts.md) — Python core, JSON contracts, deterministic gates
- [ADR-0002](adr/ADR-0002-open-toolchain-image-and-licenses.md) — open-source toolchain, Ubuntu 26.04 image, tool licenses
- [ADR-0003](adr/ADR-0003-verification-gates.md) — simulation, formal, timing and bitstream gates
- [ADR-0004](adr/ADR-0004-external-hdl-libraries-colibri.md) — external HDL libraries and Colibri
- [ADR-0005](adr/ADR-0005-host-only-programming.md) — host-only, hash-confirmed programming
- [ADR-0006](adr/ADR-0006-circuit-fpga-interchange.md) — circuit/FPGA interchange artifacts
- [ADR-0007](adr/ADR-0007-coverage-gate.md) — line-coverage gate in CI
- [ADR-0008](adr/ADR-0008-published-image-digest-lock.md) — published image digest lock
- [ADR-0009](adr/ADR-0009-attest-published-tools-images.md) — attest published tools images
- [ADR-0010](adr/ADR-0010-records-vision-liaison.md) — VRP records, PNG renders, SLP v2, fail-closed launcher
- [ADR-0011](adr/ADR-0011-structural-coverage.md) — structural coverage gate (C0, C1, C2, MC/DC, boundaries)

## Skills

The workflow and field references live in the plugin skills:
[workflow](../plugins/fpga/skills/fpga-workflow/SKILL.md),
[contract](../plugins/fpga/skills/fpga-contract/SKILL.md),
[device profiles and pins](../plugins/fpga/skills/fpga-device-pins/SKILL.md),
[verification](../plugins/fpga/skills/fpga-verification/SKILL.md),
[external libraries](../plugins/fpga/skills/fpga-external-libraries/SKILL.md),
[sibling cooperation](../plugins/fpga/skills/fpga-sibling-cooperation/SKILL.md).

## Research

- [Agent Canvas v1.25 feature evaluation](research/ac-v1.25-feature-evaluation.md) — Agent Canvas / OpenHands surface adoption decisions
- [SDK v1.51.0 feature evaluation](research/sdk-v1.51.0-feature-evaluation.md) — OpenHands SDK/tools adoption decisions
- [SDK v1.52.0 feature evaluation](research/sdk-v1.52.0-feature-evaluation.md) — OpenHands SDK/tools adoption decisions
- [SDK v1.53.0 feature evaluation](research/sdk-v1.53.0-feature-evaluation.md) — OpenHands SDK/tools adoption decisions
- [SDK v1.50.1 feature evaluation](research/sdk-v1.50.1-feature-evaluation.md) — previous round's adoption decisions

# fpga-agent documentation

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

## Skills

The workflow and field references live in the plugin skills:
[workflow](../plugins/fpga/skills/fpga-workflow/SKILL.md),
[contract](../plugins/fpga/skills/fpga-contract/SKILL.md),
[device profiles and pins](../plugins/fpga/skills/fpga-device-pins/SKILL.md),
[verification](../plugins/fpga/skills/fpga-verification/SKILL.md),
[external libraries](../plugins/fpga/skills/fpga-external-libraries/SKILL.md),
[sibling cooperation](../plugins/fpga/skills/fpga-sibling-cooperation/SKILL.md).

## Maintenance

Review [dependency update candidates](dependency-updates.md) before changing
upstream pins or regenerating `uv.lock`.

## Research

- [SDK v1.51.0 feature evaluation](research/sdk-v1.51.0-feature-evaluation.md) — OpenHands SDK/tools adoption decisions
- [SDK v1.52.0 feature evaluation](research/sdk-v1.52.0-feature-evaluation.md) — OpenHands SDK/tools adoption decisions
- [SDK v1.50.1 feature evaluation](research/sdk-v1.50.1-feature-evaluation.md) — previous round's adoption decisions

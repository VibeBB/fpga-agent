# Skills

Plugin skills under `plugins/fpga/skills/`, keyword-triggered
(`triggers:`), path-triggered (`paths:`) and model-invocable.

| skill | covers |
| --- | --- |
| `fpga-workflow` | stage order, gate table, the mandatory VRP records section and the vision-points table |
| `fpga-contract` | `<name>.fpga.json` field reference: device, sources, libraries, clocks, pins, build, simulations, formal, circuit link, programmer |
| `fpga-device-pins` | bundled device profiles, package pin rules, clock-capable and configuration/JTAG pins, I/O standards |
| `fpga-verification` | testbench `expect` lines, PSL/SVA properties, SymbiYosys modes, waveforms |
| `fpga-external-libraries` | pinned `third_party/` checkouts (Colibri), SPDX provenance requirements |
| `fpga-sibling-cooperation` | interchange artifacts, `fpga request`, and the SLP v2 liaison with UX-creator |
| `fpga-contract-rules` | path rule on `**/*.fpga.json` | Short schema and provenance reminders injected whenever a contract file is touched. |
| `fpga-out-rules` | path rule on `**/out/**` | Reminds that generated artifacts under `out/` are read-only projections — change the contract and regenerate (the `protect-generated` hook enforces). |

Agents read the skills by name at the top of their prompts; the workflow
skill is the entry point and includes the records obligations verbatim.

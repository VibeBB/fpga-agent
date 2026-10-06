# Hooks

Declared in `plugins/fpga/hooks/hooks.json`; scripts live under
`plugins/fpga/hooks/scripts/` and run through the launcher resolver.

## session_start (in order)

| hook | behavior |
| --- | --- |
| `ensure-llm-profiles` | seeds the vision-capable LLM profile used by `VisionInspectTool` |
| `require-records` | denies resuming when owed records would be lost (shared canonical hook) |
| `fpga-doctor` | one-shot toolchain probe summary |
| `intake-attachments` | materializes user-attached images under `intake/attachments/` with a `manifest.jsonl` |

## pre_tool_use

| hook | matcher | behavior |
| --- | --- | --- |
| `protect-generated` | file_editor, apply_patch, terminal | denies hand edits of generated artifacts: `*.fpga.pcf/lpf/cst`, `*.fpga-pinmap.*`, `*.fpga-production.json`, `*.fpga-report.*`, `sim-*.log`, `formal-*.log`, `observations/fpga/*.jsonl`, `records-status.json`, `liaison/*.ux-response.json`, `fpga-reports/*.png` |
| `safety-rail` | terminal | blocks destructive shell commands |
| `deny-programming` | terminal | denies programmer invocations for agents |

## post_tool_use

| hook | matcher | behavior |
| --- | --- | --- |
| `record-vision-tool-event` | inspect_image_with_vision | appends the event to `vision-tool-events.jsonl` for `source_event_id` binding |
| `record-image-observation` | file_editor | records image observations for `file_editor`, `fpga_gates`, `fpga_build`, `fpga_sim`, `fpga_pinmap_export`, `fpga_render` results |

## stop (in order; `require-records` first)

| hook | behavior |
| --- | --- |
| `require-records` | re-validates `observations/fpga/*.jsonl` against the VRP rules (`records-policy.json`) and refuses to stop while the session owes records (max 2 denials) |
| `report-fpga-status` | prints the session's artifact status summary |

Shared hooks (`_records.py`, `require_records.py`, `safety_rail.py`,
`protect_generated.py`, `intake_attachments.py`, `ensure_llm_profiles.py`)
are canonical across the VibeBB family — `scripts/check_shared_hooks.py`
verifies them by normalized-AST sha256; never edit them in one repo only.

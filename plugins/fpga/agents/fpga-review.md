---
name: fpga-review
description: "USE THIS for an independent review of FPGA changes against the contract and gate reports. Returns findings only; never edits HDL and never overrides a gate verdict. <example>Review the blinky design before release.</example> <example>FPGA の変更をレビューして。</example>"
model: vibebb-review
tools:
  - terminal
  - file_editor
  - grep
  - glob
  - task_tracker
mcp_config:
  fpga:
    command: sh
    args:
      - -c
      - 'p=$(for c in "${FPGA_PLUGIN_ROOT:-}" "${OPENHANDS_PROJECT_DIR:-.}/plugins/fpga" "${HOME:-}/.agents/plugins/fpga" "${HOME:-}/.openhands/plugins/installed/fpga"; do [ -f "$c/scripts/fpga_launcher.py" ] && printf %s "$c" && break; done); [ -n "$p" ] || { echo "fpga plugin root unresolved" >&2; exit 2; }; exec python3 "$p/scripts/fpga_launcher.py" mcp_server'
max_iteration_per_run: 24
max_budget_per_run: 3.0
when_to_use_examples:
  - Review HDL, constraints and fpga-report before a release
  - Check that pin acknowledgements and library licenses are justified
  - FPGA 設計のレビュー
hooks:
  pre_tool_use:
    - matcher: file_editor|apply_patch|terminal
      hooks:
        - type: command
          name: protect-generated
          command: 'p=$(for c in "${FPGA_PLUGIN_ROOT:-}" "${OPENHANDS_PROJECT_DIR:-.}/plugins/fpga" "${HOME:-}/.agents/plugins/fpga" "${HOME:-}/.openhands/plugins/installed/fpga"; do [ -f "$c/hooks/scripts/protect_generated.py" ] && printf %s "$c" && break; done); [ -n "$p" ] || { echo "fpga plugin root unresolved" >&2; exit 2; }; exec python3 "$p/hooks/scripts/protect_generated.py"'
    - matcher: terminal
      hooks:
        - type: command
          name: safety-rail
          command: 'p=$(for c in "${FPGA_PLUGIN_ROOT:-}" "${OPENHANDS_PROJECT_DIR:-.}/plugins/fpga" "${HOME:-}/.agents/plugins/fpga" "${HOME:-}/.openhands/plugins/installed/fpga"; do [ -f "$c/hooks/scripts/safety_rail.py" ] && printf %s "$c" && break; done); [ -n "$p" ] || exit 0; exec python3 "$p/hooks/scripts/safety_rail.py"'
  post_tool_use:
    - matcher: inspect_image_with_vision
      hooks:
        - type: command
          name: record-vision-tool-event
          command: 'p=$(for c in "${FPGA_PLUGIN_ROOT:-}" "${OPENHANDS_PROJECT_DIR:-.}/plugins/fpga" "${HOME:-}/.agents/plugins/fpga" "${HOME:-}/.openhands/plugins/installed/fpga"; do [ -f "$c/hooks/scripts/record_vision_tool_event.py" ] && printf %s "$c" && break; done); [ -n "$p" ] || exit 0; exec python3 "$p/hooks/scripts/record_vision_tool_event.py"'
    - matcher: file_editor
      hooks:
        - type: command
          name: record-image-observation
          command: 'p=$(for c in "${FPGA_PLUGIN_ROOT:-}" "${OPENHANDS_PROJECT_DIR:-.}/plugins/fpga" "${HOME:-}/.agents/plugins/fpga" "${HOME:-}/.openhands/plugins/installed/fpga"; do [ -f "$c/hooks/scripts/record_image_observation.py" ] && printf %s "$c" && break; done); [ -n "$p" ] || exit 0; exec python3 "$p/hooks/scripts/record_image_observation.py"'
permission_mode: never_confirm
---

You review an FPGA change. Read the `fpga-workflow` and
`fpga-verification` skills first. You report findings; you do not edit
sources and you never override a gate verdict.

Check, in order:
1. `fpga gates <contract>` (MCP `fpga_gates`) — cite each failing check id.
2. The contract: acknowledged configuration pins have a rationale, clocks
   sit on clock-capable pins, budgets are not loosened without reason.
3. Verification depth: every requirement has a testbench `expect` line or
   a formal property; testbenches fail loudly (`severity failure`,
   `$fatal`) rather than print and continue.
4. RTL hazards the gates cannot see: unsynchronized inputs crossing into
   the clock domain, missing resets on control state, combinational loops,
   latches reported in `fpga-reports/synth.log`.
5. Provenance: external libraries are pinned by revision and their
   licenses (e.g. CERN-OHL-W-2.0 for Colibri) are recorded.

User-attached images are materialized under `intake/attachments/` with a
provenance `manifest.jsonl`. A value read off an image (a pin label on a
board photo, a schematic net name, a timing figure from a datasheet, a
logic-analyzer capture) is an assumption whose source is that image path:
ask the user to confirm it before it goes into the contract, and never let
it replace the circuit connectivity artifact or the device profile as the
source of pin assignments.

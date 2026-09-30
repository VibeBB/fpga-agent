# ADR-0006: Circuit/FPGA interchange artifacts

- Status: accepted
- Date: 2026-09-30

## Decision

- Input: the electrical-circuit-agent connectivity export
  `<design>.firmware.json` (`circuit_firmware_connectivity`). The FPGA is
  one of its devices, selected by `device.ref`. Reusing the export the
  firmware sibling already consumes keeps one circuit-side producer.
- `fpga.netlist_match` checks every pin against the export's nets,
  signal classes and voltages, and flags connected circuit pins the
  contract leaves unconstrained unless listed in `circuit.unused_pins`.
- Output: `<name>.fpga-pinmap.json` (`fpga_pinmap`) with the contract
  sha256, for the circuit side to confirm; and
  `<design>.<id>.fpga-request.json` (`fpga_request`) change requests to a
  named sibling.
- No sibling code is imported and no sibling input is edited.

## Consequences

- If the circuit agent adds a dedicated FPGA export kind, the loader
  accepts it as an additional literal without changing gate semantics.

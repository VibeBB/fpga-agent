# ADR-0005: Host-only, hash-confirmed programming

- Status: accepted
- Date: 2026-09-30

## Decision

- `fpga program` builds an openFPGALoader command only when the contract
  declares a programmer, the last full gate report passed for the current
  contract hash, the bitstream on disk still has the reported sha256, and
  the caller repeats that sha256 via `--confirm-sha256`. `--dry-run`
  prints the command.
- It is not an MCP tool and not a gate. The launcher always runs it on
  the host (the container has no USB access).
- The `safety-rail` hook denies agents direct programmer executables
  (openFPGALoader, iceprog, ecpprog, fujprog, dfu-util, vendor
  programmers) and `fpga program` without `--dry-run`.

## Consequences

- An agent can prepare and dry-run programming; a human flips the board.
- A rebuilt or edited bitstream cannot be flashed on a stale approval.

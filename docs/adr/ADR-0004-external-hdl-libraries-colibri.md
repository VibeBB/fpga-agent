# ADR-0004: External HDL libraries and Colibri

- Status: accepted
- Date: 2026-09-30

## Context

Designs reuse third-party HDL. CERN's Colibri is a vendor-independent
VHDL-2008 library (FuseSoC CAPI-2 cores) under CERN-OHL-W-2.0, a weakly
reciprocal hardware licence: unmodified use inside a larger design is
permitted, notices must be kept, and modifications to Colibri files must
be published under the same licence when distributed.

## Decision

- Libraries are declared in `contract.libraries[]` with name, root,
  ordered files, SPDX license, HTTPS source URL and revision. Their files
  compile into a VHDL library of that name (`colibri`), separate from
  `work`.
- `fpga.provenance` requires each file to exist and carry an SPDX header
  whose identifiers are covered by the declared license.
- Colibri is not vendored. `scripts/fetch_colibri.py` checks out a pinned
  revision into `third_party/colibri` (gitignored); the example contract
  references it relatively. The tools image does not contain it, so the
  checkout happens on a networked host before gates run offline.

## Consequences

- The repository stays BSD-3-Clause with no CERN-OHL-W files in it.
- Users shipping bitstreams built with Colibri carry the CERN-OHL-W-2.0
  obligations; the skill and notices state them.

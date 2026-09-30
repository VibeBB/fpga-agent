# ADR-0002: Open-source toolchain, Ubuntu 26.04 image and tool licenses

- Status: accepted
- Date: 2026-09-30

## Context

Vendor suites (Vivado, Quartus, Radiant, Gowin EDA) are proprietary,
large, license-managed and not redistributable, so they cannot live in
an image or run unattended in CI. The open flow — Yosys, nextpnr and the
IceStorm / Trellis / Apicula databases — covers Lattice iCE40 and ECP5
and Gowin GW1N / GW2A end to end, to a bitstream. VHDL needs GHDL (synthesis
front end) and a simulator; NVC is the most complete open VHDL-2008
simulator.

## Decision

- The image is `ubuntu:26.04` pinned by digest. Debian 13 slim was
  evaluated and rejected: the NVC 1.23.0 release package targets Ubuntu
  and cannot resolve `libllvm21` on Debian 13.
- Tools come from one OSS CAD Suite release (`2026-09-30`) and the NVC
  1.23.0 Ubuntu 26.04 package, both downloaded over HTTPS and verified by
  sha256 at build time. Versions and licenses are listed in
  `THIRD_PARTY_NOTICES.md`; the suite's per-tool licenses stay in the
  image.
- GPL/LGPL tools (GHDL, GHDL plugin, NVC, Icarus, Yices, Verilator) run
  only as subprocesses; `fpga` never links or imports them, so the
  package stays BSD-3-Clause.
- The launcher runs gates in the image with `--network none`, mounting
  the workspace at the same path. The image build runs a full gate smoke
  test.
- Vendor tools are reported by `doctor` as `vendor` probes only; no gate
  depends on them.

## Consequences

- Xilinx/Intel parts are out of scope for the gates until an open flow
  covers them; the contract families are an enum that can grow.
- The image is about 4 GB; the CI job caches layers.

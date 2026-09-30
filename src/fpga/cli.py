"""fpga command line interface.

Subcommands:
  doctor       probe the toolchain
  validate     validate a <name>.fpga.json contract against its device profile
  check        static gates (contract, provenance, pins, constraints, netlist match)
  gates        every gate: static + lint, simulation, formal, synthesis, P&R,
               timing, utilization, bitstream
  constraints  regenerate the contract's PCF/LPF/CST constraint file
  pinmap       export <name>.fpga-pinmap.json for electrical-circuit-agent
  lint         analyse and elaborate the design top (NVC or Verilator)
  sim          run one declared simulation
  formal       run one declared SymbiYosys proof
  build        synthesis, place and route, bitstream (advisory)
  program      host-only: program a board with openFPGALoader
  request      write a change request to a sibling agent
  profile      list bundled device profiles or print one

Every command prints a JSON payload; exit 0 only when verdict is pass.
"""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from pathlib import Path

from . import service


def _emit(payload: service.Json) -> int:
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if payload.get("verdict") == "pass" else 1


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="fpga")
    sub = parser.add_subparsers(dest="command", required=True)
    doctor = sub.add_parser("doctor")
    doctor.add_argument("--warn", action="store_true", help="always exit 0")
    for name in ("validate", "constraints"):
        sub.add_parser(name).add_argument("contract", type=Path)
    for name in ("check", "gates", "pinmap", "lint", "build"):
        command = sub.add_parser(name)
        command.add_argument("contract", type=Path)
        command.add_argument("--out", type=Path)
    for name in ("sim", "formal"):
        command = sub.add_parser(name)
        command.add_argument("contract", type=Path)
        command.add_argument("--id", required=True)
        command.add_argument("--out", type=Path)
    prog = sub.add_parser("program")
    prog.add_argument("contract", type=Path)
    prog.add_argument("--confirm-sha256", required=True)
    prog.add_argument("--dry-run", action="store_true")
    prog.add_argument("--out", type=Path)
    request = sub.add_parser("request")
    request.add_argument("contract", type=Path)
    request.add_argument("--target", required=True)
    request.add_argument("--risk", choices=("low", "high"), required=True)
    request.add_argument("--change", required=True)
    request.add_argument("--rationale", required=True)
    request.add_argument("--net", dest="nets", action="append", default=[])
    request.add_argument("--failing-check", dest="failing_checks", action="append", default=[])
    request.add_argument("--out", type=Path)
    sub.add_parser("profile").add_argument("id", nargs="?")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    command: str = args.command
    if command == "doctor":
        code = _emit(service.doctor_payload())
        return 0 if args.warn else code
    if command == "validate":
        return _emit(service.validate_payload(args.contract))
    if command in ("check", "gates"):
        return _emit(service.gates_payload(args.contract, args.out, full=command == "gates"))
    if command == "constraints":
        return _emit(service.constraints_payload(args.contract))
    if command == "pinmap":
        return _emit(service.pinmap_payload(args.contract, args.out))
    if command == "lint":
        return _emit(service.lint_payload(args.contract, args.out))
    if command == "build":
        return _emit(service.build_payload(args.contract, args.out))
    if command == "sim":
        return _emit(service.sim_payload(args.contract, args.id, args.out))
    if command == "formal":
        return _emit(service.formal_payload(args.contract, args.id, args.out))
    if command == "program":
        return _emit(
            service.program_payload(
                args.contract, args.out, args.confirm_sha256, dry_run=args.dry_run
            )
        )
    if command == "request":
        return _emit(
            service.request_payload(
                args.contract,
                args.out,
                target=args.target,
                risk=args.risk,
                change=args.change,
                rationale=args.rationale,
                nets=args.nets,
                failing_checks=args.failing_checks,
            )
        )
    return _emit(service.profile_payload(args.id))


if __name__ == "__main__":
    raise SystemExit(main())

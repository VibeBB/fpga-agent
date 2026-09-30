"""Host-only board programming with openFPGALoader.

Programming changes real hardware, so it is never a gate and never an MCP
tool. It runs only when the last full gate report for the current
contract passed, the bitstream on disk still has the reported SHA-256, and
the caller repeats that SHA-256 as confirmation.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from pydantic import ValidationError

from .contract import FpgaContract, resolve
from .flow import sha256
from .gates import GateReport
from .interchange import sha256_file


@dataclass
class ProgramPlan:
    argv: list[str]
    bitstream: Path
    sha256: str


def plan(
    contract: FpgaContract, contract_path: Path, out_dir: Path, confirm_sha256: str
) -> ProgramPlan:
    if contract.programmer is None or not (contract.programmer.board or contract.programmer.cable):
        raise ValueError("contract declares no programmer board or cable")
    report_path = out_dir / f"{contract.name}.fpga-report.json"
    try:
        report = GateReport.model_validate(json.loads(report_path.read_text(encoding="utf-8")))
    except (OSError, ValueError, ValidationError) as exc:
        raise ValueError(
            f"no readable gate report ({report_path}); run `fpga gates` first"
        ) from exc
    if report.scope != "full" or report.verdict != "pass" or report.bitstream_sha256 is None:
        raise ValueError("the last full gate run did not pass; run `fpga gates` first")
    if report.contract_sha256 != sha256_file(contract_path):
        raise ValueError("the contract changed since the last gate run; rerun `fpga gates`")
    bitstream = resolve(contract_path, contract.build.bitstream)
    if not bitstream.is_file():
        raise ValueError(f"bitstream {contract.build.bitstream} is missing")
    digest = sha256(bitstream)
    if digest != report.bitstream_sha256:
        raise ValueError("the bitstream changed since the last gate run; rerun `fpga gates`")
    if confirm_sha256 != digest:
        raise ValueError(f"confirmation must repeat the bitstream sha256 {digest}")
    argv = ["openFPGALoader"]
    if contract.programmer.board:
        argv += ["-b", contract.programmer.board]
    if contract.programmer.cable:
        argv += ["-c", contract.programmer.cable]
    if contract.programmer.write_flash:
        argv.append("-f")
    argv.append(bitstream.as_posix())
    return ProgramPlan(argv, bitstream, digest)

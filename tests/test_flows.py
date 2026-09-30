"""Tool-backed flows; run inside the fpga-tools image or with OSS CAD Suite and NVC on PATH."""

from __future__ import annotations

from pathlib import Path
from typing import cast

import pytest

from fpga import service
from fpga.gates import GateReport, run_gates

from .conftest import read_json, tools_available, write_json

pytestmark = [
    pytest.mark.tools,
    pytest.mark.skipif(not tools_available(), reason="FPGA toolchain not on PATH"),
]


def _full(contract: Path) -> GateReport:
    return run_gates(contract, contract.parent / "fpga-reports", full=True)


def _failed(report: GateReport) -> list[str]:
    return [c.id for c in report.checks if c.status == "fail"]


def test_doctor_passes() -> None:
    assert service.doctor_payload()["verdict"] == "pass"


@pytest.mark.parametrize(
    "example", ["ulx3s", "tangnano", "tangnano20k", "tangprimer20k", "uart_echo"]
)
def test_full_gates_pass(example: str, request: pytest.FixtureRequest) -> None:
    contract: Path = request.getfixturevalue(example)
    report = _full(contract)
    assert report.verdict == "pass", _failed(report)
    assert report.bitstream_sha256 is not None
    ids = {c.id for c in report.checks}
    assert {"fpga.synth", "fpga.pnr", "fpga.timing", "fpga.utilization", "fpga.bitstream"} <= ids


def test_program_dry_run_after_passing_gates(ulx3s: Path) -> None:
    payload = service.gates_payload(ulx3s, None, full=True)
    payload.pop("written")
    report = GateReport.model_validate(payload)
    assert report.bitstream_sha256 is not None
    wrong = service.program_payload(ulx3s, None, "0" * 64, dry_run=True)
    assert wrong["verdict"] == "fail" and report.bitstream_sha256 in str(wrong["detail"])
    ok = service.program_payload(ulx3s, None, report.bitstream_sha256, dry_run=True)
    assert ok["verdict"] == "pass"
    assert cast(list[str], ok["argv"])[:3] == ["openFPGALoader", "-b", "ulx3s"]
    (ulx3s.parent / "build" / "blinky.bit").write_bytes(b"tampered")
    tampered = service.program_payload(ulx3s, None, report.bitstream_sha256, dry_run=True)
    assert tampered["verdict"] == "fail" and "bitstream changed" in str(tampered["detail"])


def test_simulation_missing_expectation_fails(ulx3s: Path) -> None:
    value = read_json(ulx3s)
    value["simulations"][0]["expect"].append("NEVER PRINTED")
    write_json(ulx3s, value)
    payload = service.sim_payload(ulx3s, "count", None)
    assert payload["verdict"] == "fail"
    assert payload["missing"] == ["NEVER PRINTED"]


def test_formal_counterexample_fails(ulx3s: Path) -> None:
    rtl = ulx3s.parent / "rtl" / "blinky.v"
    source = rtl.read_text(encoding="utf-8")
    broken = source.replace("assert (", "assert (1'b0 && ", 1)
    assert broken != source
    rtl.write_text(broken, encoding="utf-8")
    payload = service.formal_payload(ulx3s, "increment", None)
    assert payload["verdict"] == "fail"


def test_timing_budget_fails(tangnano: Path) -> None:
    value = read_json(tangnano)
    value["clocks"][0]["frequency_mhz"] = 1000
    write_json(tangnano, value)
    assert service.constraints_payload(tangnano)["verdict"] == "pass"
    report = _full(tangnano)
    assert "fpga.timing" in _failed(report)
    assert report.verdict == "fail"


def test_port_pin_mismatch_fails_synth(ulx3s: Path) -> None:
    value = read_json(ulx3s)
    value["pins"] = [p for p in value["pins"] if p["port"] != "led[7]"]
    write_json(ulx3s, value)
    assert service.constraints_payload(ulx3s)["verdict"] == "pass"
    report = _full(ulx3s)
    synth = next(c for c in report.checks if c.id == "fpga.synth")
    assert synth.status == "fail" and "led" in synth.detail

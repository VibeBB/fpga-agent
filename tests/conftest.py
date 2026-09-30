from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "examples"
COLIBRI = ROOT / "third_party" / "colibri"
TOOLS = ("yosys", "nvc", "nextpnr-ice40", "nextpnr-ecp5", "nextpnr-himbaechel", "sby")


def tools_available() -> bool:
    return all(shutil.which(tool) for tool in TOOLS)


def _copy(tmp_path: Path, name: str, contract: str) -> Path:
    target = tmp_path / "examples" / name
    shutil.copytree(EXAMPLES / name, target, ignore=shutil.ignore_patterns("build", "fpga-reports"))
    return target / contract


@pytest.fixture
def ulx3s(tmp_path: Path) -> Path:
    """Copy of the ECP5 ULX3S blinky example; returns the contract path."""
    return _copy(tmp_path, "blinky-ulx3s", "blinky.fpga.json")


@pytest.fixture
def tangnano(tmp_path: Path) -> Path:
    """Copy of the Gowin Tang Nano 9K blinky example; returns the contract path."""
    return _copy(tmp_path, "blinky-tangnano9k", "blinky.fpga.json")


@pytest.fixture
def tangnano20k(tmp_path: Path) -> Path:
    """Copy of the Gowin GW2AR-18C Tang Nano 20K blinky example; returns the contract path."""
    return _copy(tmp_path, "blinky-tangnano20k", "blinky.fpga.json")


@pytest.fixture
def tangprimer20k(tmp_path: Path) -> Path:
    """Copy of the Gowin GW2A-18C Tang Primer 20K blinky example; returns the contract path."""
    return _copy(tmp_path, "blinky-tangprimer20k", "blinky.fpga.json")


@pytest.fixture
def uart_echo(tmp_path: Path) -> Path:
    """Copy of the iCEBreaker UART echo example with Colibri linked beside it."""
    if not (COLIBRI / "src" / "io" / "uart" / "uart.vhdl").is_file():
        pytest.skip("Colibri not fetched; run scripts/fetch_colibri.py")
    (tmp_path / "third_party").mkdir()
    (tmp_path / "third_party" / "colibri").symlink_to(COLIBRI)
    return _copy(tmp_path, "uart-echo-icebreaker", "uart-echo.fpga.json")


def read_json(path: Path) -> dict[str, Any]:
    value: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    return value


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")

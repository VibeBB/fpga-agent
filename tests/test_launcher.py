from __future__ import annotations

import importlib.util
import subprocess
from pathlib import Path
from types import ModuleType
from unittest.mock import Mock

import pytest

LAUNCHER = Path(__file__).resolve().parents[1] / "plugins" / "fpga" / "scripts" / "fpga_launcher.py"


def _docker_which(_command: str) -> str:
    return "docker"


def _launcher_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location("fpga_launcher", LAUNCHER)
    if spec is None or spec.loader is None:
        raise AssertionError("could not load fpga_launcher")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_launcher_inspect_timeout_does_not_pull(monkeypatch: pytest.MonkeyPatch) -> None:
    launcher = _launcher_module()
    run = Mock(side_effect=subprocess.TimeoutExpired("docker image inspect", timeout=30))
    monkeypatch.setattr(launcher.shutil, "which", _docker_which)
    monkeypatch.setattr(launcher.subprocess, "run", run)

    with pytest.raises(RuntimeError, match="docker image inspect timed out after 30s"):
        launcher._ensure_image("fpga-tools:ci", pull=True)

    assert run.call_count == 1
    assert run.call_args.kwargs["timeout"] == 30


def test_launcher_pull_timeout_is_reported(monkeypatch: pytest.MonkeyPatch) -> None:
    launcher = _launcher_module()
    run = Mock(
        side_effect=[
            subprocess.CompletedProcess(["docker", "image", "inspect"], returncode=1),
            subprocess.TimeoutExpired("docker pull", timeout=900),
        ]
    )
    monkeypatch.setattr(launcher.shutil, "which", _docker_which)
    monkeypatch.setattr(launcher.subprocess, "run", run)

    with pytest.raises(RuntimeError, match="docker pull timed out after 900s"):
        launcher._ensure_image("fpga-tools:ci", pull=True)

    assert run.call_count == 2
    assert run.call_args_list[0].kwargs["timeout"] == 30
    assert run.call_args_list[1].kwargs["timeout"] == 900


def _main_module(
    monkeypatch: pytest.MonkeyPatch,
    argv: list[str],
    *,
    inside_image: bool = False,
    pin: str | None = None,
) -> tuple[ModuleType, list[list[str]]]:
    launcher = _launcher_module()
    monkeypatch.setattr(launcher.sys, "argv", ["fpga_launcher.py", *argv])
    monkeypatch.setattr(
        launcher,
        "image_pin",
        lambda _root: (
            {"ref": pin, "image": None, "digest": None, "attestation": None} if pin else None
        ),
    )
    monkeypatch.setattr(launcher, "resolve_source", lambda _root: Path("/src"))
    monkeypatch.setattr(launcher, "running_inside_tools_image", lambda: inside_image)
    exec_calls: list[list[str]] = []
    monkeypatch.setattr(
        launcher.os, "execvpe", lambda *args: exec_calls.append(list(args)), raising=True
    )
    monkeypatch.setattr(
        launcher.os, "execvp", lambda *args: exec_calls.append(list(args)), raising=True
    )
    return launcher, exec_calls


def test_launcher_fails_closed_without_image(monkeypatch: pytest.MonkeyPatch) -> None:
    for argv in (["gates", "x.fpga.json"], ["doctor"], ["mcp_server"]):
        launcher, exec_calls = _main_module(monkeypatch, argv)
        assert launcher.main() == 1
        assert exec_calls == []


def test_launcher_fail_closed_warn_exits_zero(monkeypatch: pytest.MonkeyPatch) -> None:
    launcher, exec_calls = _main_module(monkeypatch, ["doctor", "--warn"])
    assert launcher.main() == 0
    assert exec_calls == []


def test_launcher_prewarm_without_pin_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    launcher, _ = _main_module(monkeypatch, ["prewarm"])
    assert launcher.main() == 1


def test_launcher_runs_in_process_inside_tools_image(monkeypatch: pytest.MonkeyPatch) -> None:
    launcher, exec_calls = _main_module(monkeypatch, ["gates", "x.fpga.json"], inside_image=True)
    assert launcher.main() == 0
    assert len(exec_calls) == 1
    assert exec_calls[0][1][1:] == ["-m", "fpga.cli", "gates", "x.fpga.json"]


def test_launcher_program_stays_on_host(monkeypatch: pytest.MonkeyPatch) -> None:
    launcher, exec_calls = _main_module(
        monkeypatch, ["program", "x.fpga.json"], pin="fpga-tools:ci"
    )
    assert launcher.main() == 0
    assert len(exec_calls) == 1
    assert exec_calls[0][0] != "docker"
    assert exec_calls[0][1][1:] == ["-m", "fpga.cli", "program", "x.fpga.json"]

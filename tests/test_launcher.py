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

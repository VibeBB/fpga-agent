from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest
import scripts.check_dependency_updates as check_dependency_updates_module
from scripts.check_dependency_updates import (
    HTTP_TIMEOUT_SECONDS,
    ROOT,
    SUBPROCESS_TIMEOUT_SECONDS,
    DependencyDeferral,
    DependencyStatus,
    _github_latest_date_tag,  # pyright: ignore[reportPrivateUsage]
    _github_latest_tag,  # pyright: ignore[reportPrivateUsage]
    check_docker_args,
    main,
)


def test_github_latest_tag_treats_timeout_as_fetch_failure():
    def timed_out(url: str) -> list[str]:
        raise subprocess.TimeoutExpired(["git", "ls-remote", "--tags", url], 1)

    assert _github_latest_tag("actions/checkout", timed_out) == ""


def test_github_latest_tag_matches_prefixed_multi_segment_tags():
    def tags(url: str) -> list[str]:
        return ["jdk-27.0-m1", "jdk-27.0.0.0", "jdk-27.0.0.0-m1a", "jdk-27.0.1.0-m1"]

    latest = _github_latest_tag("ibmruntimes/semeru27-binaries", tags, prefix="jdk-")
    assert latest == "jdk-27.0.0.0"


def test_github_latest_date_tag_ignores_non_date_tags():
    def tags(url: str) -> list[str]:
        return ["main", "2026-09-30", "2025-11-03", "2026-99-99"]

    assert _github_latest_date_tag("YosysHQ/oss-cad-suite-build", tags) == "2026-09-30"


def test_docker_args_report_fetch_failed_on_timeout():
    def timed_out(url: str) -> list[str]:
        raise subprocess.TimeoutExpired(["git", "ls-remote", "--tags", url], 1)

    statuses = check_docker_args(ROOT, list_remote_tags=timed_out)
    for name in ("UV_VERSION", "NVC_VERSION", "OSS_CAD_SUITE_RELEASE"):
        status = next(item for item in statuses if item.name == name)
        assert status.latest == "?"
        assert status.note == "fetch failed"
        assert status.outdated is False
        assert status.fetch_failed is True


def test_docker_release_pins_use_upstream_latest_tags() -> None:
    def tags(url: str) -> list[str]:
        if url.endswith("astral-sh/uv"):
            return ["0.12.21"]
        if url.endswith("nickg/nvc"):
            return ["r1.23.0", "r1.24.0"]
        if url.endswith("YosysHQ/oss-cad-suite-build"):
            return ["2026-09-30", "2026-12-01", "main"]
        return []

    statuses = check_docker_args(ROOT, list_remote_tags=tags)
    uv_status = next(status for status in statuses if status.name == "UV_VERSION")
    nvc_status = next(status for status in statuses if status.name == "NVC_VERSION")
    oss_status = next(status for status in statuses if status.name == "OSS_CAD_SUITE_RELEASE")
    assert (uv_status.current, uv_status.latest, uv_status.outdated) == (
        "0.12.21",
        "0.12.21",
        False,
    )
    assert (nvc_status.current, nvc_status.latest, nvc_status.outdated) == (
        "1.23.0",
        "r1.24.0",
        True,
    )
    assert (oss_status.current, oss_status.latest, oss_status.outdated) == (
        "2026-09-30",
        "2026-12-01",
        True,
    )


def test_subprocess_timeout_is_bounded():
    assert SUBPROCESS_TIMEOUT_SECONDS >= HTTP_TIMEOUT_SECONDS > 0


def test_main_reports_timeout_as_failure(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
):
    def timed_out(repo_root: Path) -> list[DependencyStatus]:
        raise subprocess.TimeoutExpired(["uv", "lock"], SUBPROCESS_TIMEOUT_SECONDS)

    monkeypatch.setattr(check_dependency_updates_module, "check_dependency_updates", timed_out)
    assert main([]) == 1
    assert "dependency update check failed" in capsys.readouterr().err


def test_main_reports_unknown_count_in_json(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def failed_fetch(_repo_root: Path) -> list[DependencyStatus]:
        return [
            DependencyStatus(
                "pypi",
                "example",
                "1.0.0",
                "?",
                "pyproject.toml",
                False,
                fetch_failed=True,
            )
        ]

    def no_deferrals(_root: Path) -> list[DependencyDeferral]:
        return []

    monkeypatch.setattr(check_dependency_updates_module, "check_dependency_updates", failed_fetch)
    monkeypatch.setattr(check_dependency_updates_module, "load_deferrals", no_deferrals)
    report = tmp_path / "report.json"
    assert main(["--repo-root", str(tmp_path), "--json", str(report)]) == 0
    assert json.loads(report.read_text(encoding="utf-8"))["unknown_count"] == 1

"""Fetch the pinned Colibri revision into ``third_party/colibri``.

Colibri (CERN-OHL-W-2.0) is used unmodified as an external VHDL library
and is not redistributed in this repository; the examples reference this
checkout. Run on a networked host before starting the network-isolated
tools container.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

URL = "https://gitlab.com/colibri-cern/colibri.git"
REVISION = "3fa784121ccea86d9e65b2e0dc08d2a3327f5f2f"
TARGET = Path(__file__).resolve().parents[1] / "third_party" / "colibri"


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(TARGET), *args], capture_output=True, text=True, check=True
    ).stdout.strip()


def main() -> int:
    if not (TARGET / ".git").is_dir():
        TARGET.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(["git", "clone", "--quiet", URL, str(TARGET)], check=True)
    if _git("rev-parse", "HEAD") != REVISION:
        subprocess.run(["git", "-C", str(TARGET), "fetch", "--quiet", "origin"], check=True)
        _git("checkout", "--quiet", "--detach", REVISION)
    print(f"colibri {_git('rev-parse', 'HEAD')} at {TARGET}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

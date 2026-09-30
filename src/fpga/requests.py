"""Change requests from the FPGA agent to a sibling (``*.fpga-request.json``).

The FPGA agent never edits a sibling's inputs. When the pin map needs a
circuit change (a different ball, a pull resistor, a level shifter, a
clock source) or a firmware-side change, it writes a request the owning
agent triages.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from .interchange import sha256_file

Target = Literal["circuit", "firmware", "mech", "wire", "ux", "bard", "doc", "production"]


class FpgaRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_version: Literal[1] = 1
    system: Literal["fpga"] = "fpga"
    artifact_kind: Literal["fpga_request"] = "fpga_request"
    id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]*$")
    design: str
    target: Target
    risk: Literal["low", "high"]
    change: str = Field(min_length=8)
    rationale: str = Field(min_length=8)
    nets: list[str] = Field(default_factory=list[str])
    failing_checks: list[str] = Field(default_factory=list[str])
    contract_sha256: str


def slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:48] or "request"


def write_request(
    contract_path: Path,
    design: str,
    out_dir: Path,
    *,
    target: str,
    risk: str,
    change: str,
    rationale: str,
    nets: list[str],
    failing_checks: list[str],
) -> tuple[FpgaRequest, Path]:
    request = FpgaRequest.model_validate(
        {
            "id": f"{target}-{slug(change)}",
            "design": design,
            "target": target,
            "risk": risk,
            "change": change,
            "rationale": rationale,
            "nets": nets,
            "failing_checks": failing_checks,
            "contract_sha256": sha256_file(contract_path),
        }
    )
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{design}.{request.id}.fpga-request.json"
    path.write_text(
        json.dumps(request.model_dump(mode="json"), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return request, path

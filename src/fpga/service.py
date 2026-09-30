"""Entry points shared by the CLI and the MCP server. Each returns a JSON
payload with a fail-closed ``verdict``."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import ValidationError

from . import doctor, flow, program
from .contract import FpgaContract, load_contract, resolve
from .devices import DeviceProfile, bundled_ids, load_profile
from .formal import run_formal
from .gates import (
    FAIL,
    PASS,
    Check,
    implementation_checks,
    run_gates,
    write_outputs,
)
from .interchange import sha256_file
from .projections import constraints_text, pinmap_export, pinmap_markdown, write_text
from .requests import write_request
from .sim import run_simulation
from .toolrun import run_tool

type Json = dict[str, object]


def default_out(contract_path: Path) -> Path:
    return contract_path.resolve().parent / "fpga-reports"


def _load(contract_path: Path) -> tuple[FpgaContract, DeviceProfile]:
    contract = load_contract(contract_path)
    return contract, load_profile(contract.device.profile, [contract_path.resolve().parent])


def doctor_payload() -> Json:
    results = doctor.checks()
    ok = all(item.status != "fail" for item in results)
    return {
        "verdict": PASS if ok else FAIL,
        "checks": [item.model_dump(mode="json") for item in results],
    }


def validate_payload(contract_path: Path) -> Json:
    try:
        contract, profile = _load(contract_path)
    except (OSError, ValueError, ValidationError) as exc:
        return {"verdict": FAIL, "stage": "validate", "detail": str(exc)}
    return {
        "verdict": PASS,
        "stage": "validate",
        "design": contract.name,
        "language": contract.design_language,
        "profile": profile.id,
        "part": profile.part,
        "pins": len(contract.pins),
        "libraries": [lib.name for lib in contract.libraries],
        "simulations": [s.id for s in contract.simulations],
        "formal": [f.id for f in contract.formal],
    }


def gates_payload(contract_path: Path, out_dir: Path | None, *, full: bool) -> Json:
    out = out_dir or default_out(contract_path)
    report = run_gates(contract_path, out, full=full)
    written = write_outputs(contract_path.resolve(), report, out)
    payload: Json = json.loads(report.model_dump_json())
    payload["written"] = [str(p) for p in written]
    return payload


def constraints_payload(contract_path: Path) -> Json:
    try:
        contract, profile = _load(contract_path)
    except (OSError, ValueError, ValidationError) as exc:
        return {"verdict": FAIL, "stage": "constraints", "detail": str(exc)}
    path = write_text(
        resolve(contract_path.resolve(), contract.build.constraints),
        constraints_text(contract, profile),
    )
    return {"verdict": PASS, "stage": "constraints", "written": [str(path)]}


def pinmap_payload(contract_path: Path, out_dir: Path | None) -> Json:
    try:
        contract, profile = _load(contract_path)
    except (OSError, ValueError, ValidationError) as exc:
        return {"verdict": FAIL, "stage": "pinmap", "detail": str(exc)}
    out = out_dir or default_out(contract_path)
    pinmap = pinmap_export(contract, profile, sha256_file(contract_path))
    json_path = write_text(
        out / f"{contract.name}.fpga-pinmap.json",
        json.dumps(pinmap.model_dump(mode="json"), indent=2, ensure_ascii=False) + "\n",
    )
    md_path = write_text(out / f"{contract.name}.fpga-pinmap.md", pinmap_markdown(pinmap))
    return {"verdict": PASS, "stage": "pinmap", "written": [str(json_path), str(md_path)]}


def sim_payload(contract_path: Path, sim_id: str, out_dir: Path | None) -> Json:
    try:
        contract = load_contract(contract_path)
    except (OSError, ValueError, ValidationError) as exc:
        return {"verdict": FAIL, "stage": "sim", "detail": str(exc)}
    sim = contract.simulation(sim_id)
    if sim is None:
        return {"verdict": FAIL, "stage": "sim", "detail": f"unknown simulation {sim_id}"}
    out = out_dir or default_out(contract_path)
    result = run_simulation(contract, contract_path.resolve(), sim, out)
    return {
        "verdict": PASS if result.ok else FAIL,
        "stage": "sim",
        "simulation": sim.id,
        "detail": result.detail,
        "argv": result.argv,
        "matched": result.matched,
        "missing": result.missing,
        "forbidden": result.forbidden,
        "transcript": str(result.transcript) if result.transcript else None,
        "waveform": str(result.waveform) if result.waveform else None,
    }


def formal_payload(contract_path: Path, run_id: str, out_dir: Path | None) -> Json:
    try:
        contract = load_contract(contract_path)
    except (OSError, ValueError, ValidationError) as exc:
        return {"verdict": FAIL, "stage": "formal", "detail": str(exc)}
    run = contract.formal_run(run_id)
    if run is None:
        return {"verdict": FAIL, "stage": "formal", "detail": f"unknown formal run {run_id}"}
    out = out_dir or default_out(contract_path)
    result = run_formal(contract, contract_path.resolve(), run, out)
    return {
        "verdict": PASS if result.ok else FAIL,
        "stage": "formal",
        "formal": run.id,
        "status": result.status,
        "detail": result.detail,
        "argv": result.argv,
        "transcript": str(out / f"formal-{run.id}.log"),
    }


def lint_payload(contract_path: Path, out_dir: Path | None) -> Json:
    try:
        contract = load_contract(contract_path)
    except (OSError, ValueError, ValidationError) as exc:
        return {"verdict": FAIL, "stage": "lint", "detail": str(exc)}
    out = out_dir or default_out(contract_path)
    run = flow.lint(contract, contract_path.resolve(), out)
    return {
        "verdict": PASS if run.ok else FAIL,
        "stage": "lint",
        "detail": run.detail,
        "argv": run.argv,
        "evidence": run.evidence,
        "transcript": str(out / "lint.log"),
    }


def build_payload(contract_path: Path, out_dir: Path | None) -> Json:
    """Synthesis, place and route and packing, without simulation or formal."""
    try:
        contract, profile = _load(contract_path)
    except (OSError, ValueError, ValidationError) as exc:
        return {"verdict": FAIL, "stage": "build", "detail": str(exc)}
    out = out_dir or default_out(contract_path)
    out.mkdir(parents=True, exist_ok=True)
    checks: list[Check] = implementation_checks(contract, contract_path.resolve(), profile, out)
    ok = all(c.status != "fail" for c in checks)
    return {
        "verdict": PASS if ok else FAIL,
        "stage": "build",
        "checks": [c.model_dump(mode="json") for c in checks],
        "note": "advisory; `fpga gates` is the authoritative run",
    }


def program_payload(
    contract_path: Path, out_dir: Path | None, confirm_sha256: str, *, dry_run: bool
) -> Json:
    try:
        contract = load_contract(contract_path)
        planned = program.plan(
            contract, contract_path.resolve(), out_dir or default_out(contract_path), confirm_sha256
        )
    except (OSError, ValueError, ValidationError) as exc:
        return {"verdict": FAIL, "stage": "program", "detail": str(exc)}
    if dry_run:
        return {"verdict": PASS, "stage": "program", "dry_run": True, "argv": planned.argv}
    run = run_tool(planned.argv, contract_path.resolve().parent, None, 600)
    return {
        "verdict": PASS if run.ok else FAIL,
        "stage": "program",
        "argv": planned.argv,
        "sha256": planned.sha256,
        "detail": run.detail,
        "output": run.output[-4000:],
    }


def request_payload(
    contract_path: Path,
    out_dir: Path | None,
    *,
    target: str,
    risk: str,
    change: str,
    rationale: str,
    nets: list[str],
    failing_checks: list[str],
) -> Json:
    try:
        contract = load_contract(contract_path)
        request, path = write_request(
            contract_path,
            contract.name,
            out_dir or default_out(contract_path),
            target=target,
            risk=risk,
            change=change,
            rationale=rationale,
            nets=nets,
            failing_checks=failing_checks,
        )
    except (OSError, ValueError, ValidationError) as exc:
        return {"verdict": FAIL, "stage": "request", "detail": str(exc)}
    return {"verdict": PASS, "stage": "request", "id": request.id, "written": [str(path)]}


def profile_payload(profile_id: str | None) -> Json:
    if profile_id is None:
        return {"verdict": PASS, "stage": "profile", "bundled": bundled_ids()}
    try:
        profile = load_profile(profile_id)
    except (OSError, ValueError, ValidationError) as exc:
        return {"verdict": FAIL, "stage": "profile", "detail": str(exc)}
    payload: Json = json.loads(profile.model_dump_json())
    payload["verdict"] = PASS
    return payload

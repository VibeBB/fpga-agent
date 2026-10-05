"""Deterministic FPGA gates. Unknown evidence fails; nothing passes on an
agent's word.

Static gates (no toolchain): ``fpga.contract``, ``fpga.provenance``,
``fpga.pins``, ``fpga.constraints``, ``fpga.netlist_match``.
Toolchain gates: ``fpga.lint``, ``fpga.sim.<id>``, ``fpga.formal.<id>``,
``fpga.synth``, ``fpga.pnr``, ``fpga.timing``, ``fpga.utilization``,
``fpga.bitstream``.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Literal, cast

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from . import flow
from .contract import FpgaContract, library_files, load_contract, resolve
from .devices import DeviceProfile, load_profile
from .formal import run_formal
from .interchange import CircuitConnectivity, load_circuit, sha256_file
from .projections import (
    CONSTRAINT_SUFFIX,
    constraints_text,
    pinmap_export,
    pinmap_markdown,
    write_text,
)
from .sim import run_simulation
from .toolrun import ToolRun

Status = Literal["pass", "fail", "not_applicable"]
Verdict = Literal["pass", "fail"]
PASS: Verdict = "pass"
FAIL: Verdict = "fail"
POWER_CLASSES = frozenset({"power", "ground"})
SPDX = re.compile(r"SPDX-License-Identifier:\s*([^\s*/].*?)\s*(?:\*/|-->)?\s*$")
SPDX_TOKEN = re.compile(r"[A-Za-z0-9.+-]+")
SPDX_OPERATORS = frozenset({"AND", "OR", "WITH"})


class RenderRef(BaseModel):
    model_config = ConfigDict(extra="forbid")
    view: str
    path: str
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


class Check(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    subject: str = ""
    status: Status
    detail: str = ""
    evidence: list[str] = Field(default_factory=list[str])


class GateReport(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_version: Literal[2] = 2
    system: Literal["fpga"] = "fpga"
    artifact_kind: Literal["fpga_gate_report"] = "fpga_gate_report"
    design: str
    scope: Literal["static", "full"]
    contract_sha256: str
    circuit_sha256: str | None
    profile: str | None
    bitstream_sha256: str | None = None
    verdict: Verdict
    checks: list[Check]
    renders: list[RenderRef] = Field(default_factory=list[RenderRef])


def _check(
    check_id: str, subject: str, problems: list[str], evidence: list[str] | None = None
) -> Check:
    return Check(
        id=check_id,
        subject=subject,
        status="fail" if problems else "pass",
        detail="; ".join(problems),
        evidence=evidence or [],
    )


def _na(check_id: str, detail: str) -> Check:
    return Check(id=check_id, status="not_applicable", detail=detail)


def _run_check(check_id: str, subject: str, run: ToolRun, extra: list[str] | None = None) -> Check:
    evidence = [" ".join(run.argv), f"seconds={run.seconds:.1f}", *run.evidence, *(extra or [])]
    return _check(check_id, subject, [] if run.ok else [run.detail], evidence)


def contract_files(contract: FpgaContract, contract_path: Path) -> list[tuple[str, Path]]:
    files: list[tuple[str, Path]] = [
        (s.path, resolve(contract_path, s.path)) for s in contract.sources
    ]
    for lib in contract.libraries:
        files += [(f"{lib.name}:{p.name}", p) for p in library_files(contract_path, lib)]
    for sim in contract.simulations:
        files += [(s.path, resolve(contract_path, s.path)) for s in sim.sources]
    for run in contract.formal:
        files += [(s.path, resolve(contract_path, s.path)) for s in run.sources]
    return files


def check_contract(
    contract: FpgaContract, contract_path: Path, profile: DeviceProfile, circuit_problem: str | None
) -> Check:
    problems = [
        f"{label}: missing ({path})"
        for label, path in contract_files(contract, contract_path)
        if not path.is_file()
    ]
    expected = CONSTRAINT_SUFFIX[profile.family]
    if not contract.build.constraints.endswith(f".fpga{expected}"):
        problems.append(f"build.constraints must end with .fpga{expected} for {profile.family}")
    if circuit_problem:
        problems.append(circuit_problem)
    return _check("fpga.contract", contract.name, problems, [f"profile={profile.id}"])


def spdx_ids(path: Path) -> list[str]:
    try:
        with path.open(encoding="utf-8", errors="replace") as handle:
            head = [next(handle, "") for _ in range(30)]
    except OSError:
        return []
    found: list[str] = []
    for line in head:
        match = SPDX.search(line)
        if match:
            found += [t for t in SPDX_TOKEN.findall(match.group(1)) if t not in SPDX_OPERATORS]
    return found


def check_provenance(contract: FpgaContract, contract_path: Path) -> Check:
    if not contract.libraries:
        return _check("fpga.provenance", contract.name, [], ["no external libraries"])
    problems: list[str] = []
    evidence: list[str] = []
    for lib in contract.libraries:
        declared = {t for t in SPDX_TOKEN.findall(lib.license) if t not in SPDX_OPERATORS}
        headed = 0
        for path in library_files(contract_path, lib):
            if not path.is_file():
                problems.append(f"{lib.name}:{path.as_posix()} is missing")
                continue
            ids = spdx_ids(path)
            if not ids:
                problems.append(f"{lib.name}:{path.name} has no SPDX-License-Identifier header")
                continue
            headed += 1
            undeclared = sorted(set(ids) - declared)
            if undeclared:
                problems.append(
                    f"{lib.name}:{path.name} is {', '.join(undeclared)}, "
                    f"library declares {lib.license}"
                )
        evidence.append(
            f"{lib.name}: {lib.license} @ {lib.revision} ({lib.source_url}); "
            f"SPDX headers {headed}/{len(lib.files)}"
        )
    return _check("fpga.provenance", contract.name, problems, evidence)


def check_pins(contract: FpgaContract, profile: DeviceProfile) -> Check:
    problems: list[str] = []
    evidence: list[str] = []
    for pin in contract.pins:
        device_pin = profile.pin(pin.package_pin)
        if device_pin is None:
            problems.append(
                f"{pin.port}: {pin.package_pin} is not a user I/O of "
                f"{profile.part} {profile.package}"
            )
            continue
        if device_pin.caution is not None and device_pin.caution not in pin.acknowledge:
            problems.append(
                f"{pin.port}: {pin.package_pin} is a {device_pin.caution} pin "
                f"({'/'.join(device_pin.functions)}); acknowledge it with a rationale "
                "or move the port"
            )
        if pin.io_standard is not None:
            if profile.family == "ice40":
                problems.append(
                    f"{pin.port}: iCE40 PCF cannot set an I/O standard; the bank VCCIO sets it"
                )
            elif pin.io_standard not in profile.io_standards:
                problems.append(
                    f"{pin.port}: I/O standard {pin.io_standard} not in "
                    f"{', '.join(profile.io_standards)}"
                )
        if profile.family == "ice40" and pin.pull == "down":
            problems.append(f"{pin.port}: iCE40 I/O has no pull-down")
    for clock in contract.clocks:
        pin = contract.pin(clock.port)
        if pin is None:
            problems.append(f"clock {clock.port} has no pin")
            continue
        device_pin = profile.pin(pin.package_pin)
        if device_pin is not None and not device_pin.clock:
            evidence.append(
                f"clock {clock.port} on {pin.package_pin} is not a dedicated clock input"
            )
    evidence.append(f"pins={len(contract.pins)}/{len(profile.pins)} user I/O")
    return _check("fpga.pins", f"{profile.part} {profile.package}", problems, evidence)


def check_constraints(contract: FpgaContract, profile: DeviceProfile, contract_path: Path) -> Check:
    path = resolve(contract_path, contract.build.constraints)
    if not path.is_file():
        return _check(
            "fpga.constraints", contract.build.constraints, ["missing; run `fpga constraints`"]
        )
    if path.read_text(encoding="utf-8") != constraints_text(contract, profile):
        return _check(
            "fpga.constraints",
            contract.build.constraints,
            ["stale; regenerate with `fpga constraints`"],
        )
    return _check("fpga.constraints", contract.build.constraints, [])


def check_netlist_match(
    contract: FpgaContract, profile: DeviceProfile, circuit: CircuitConnectivity
) -> Check:
    ref = contract.device.ref
    device = circuit.device(ref)
    if device is None:
        refs = ", ".join(m.ref for m in circuit.mcus)
        return _check("fpga.netlist_match", ref, [f"circuit has no device {ref} ({refs})"])
    problems: list[str] = []
    evidence = [f"circuit source={circuit.source}"]
    by_pin = {p.pin: p for p in device.pins}
    claimed: set[str] = set()
    for pin in contract.pins:
        found = by_pin.get(pin.package_pin)
        if found is None:
            problems.append(f"{pin.port}: {ref}.{pin.package_pin} is not in the circuit export")
            continue
        claimed.add(found.pin)
        if pin.net is None:
            if found.net is not None:
                problems.append(
                    f"{pin.port}: {ref}.{pin.package_pin} is on net {found.net}; "
                    "name it in the contract"
                )
            continue
        if found.net != pin.net:
            problems.append(
                f"{pin.port}: {ref}.{pin.package_pin} is on net {found.net or 'unconnected'}, "
                f"contract says {pin.net}"
            )
            continue
        if found.signal_class in POWER_CLASSES:
            problems.append(f"{pin.port}: net {pin.net} is a {found.signal_class} net")
        if found.voltage_v is not None and found.voltage_v > profile.io_voltage_max_v:
            problems.append(
                f"{pin.port}: net {pin.net} at {found.voltage_v} V exceeds the "
                f"{profile.io_voltage_max_v} V I/O maximum"
            )
        evidence.append(f"{pin.port}={ref}.{pin.package_pin}/{pin.net}")
    unused = set(contract.circuit.unused_pins) if contract.circuit else set[str]()
    for circuit_pin in device.pins:
        if circuit_pin.pin in claimed or circuit_pin.net is None:
            continue
        if circuit_pin.signal_class in POWER_CLASSES:
            continue
        device_pin = profile.pin(circuit_pin.pin)
        if device_pin is None or device_pin.caution is not None or circuit_pin.pin in unused:
            continue
        problems.append(
            f"{ref}.{circuit_pin.pin} drives net {circuit_pin.net} but the contract constrains "
            "nothing on it (constrain it or list it in circuit.unused_pins)"
        )
    return _check("fpga.netlist_match", ref, problems, evidence)


def check_synth_ports(contract: FpgaContract, netlist: Path) -> list[str]:
    try:
        ports = flow.netlist_ports(netlist, contract.top)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return [f"netlist unreadable: {exc}"]
    pinned = {p.port for p in contract.pins}
    scalar = {name.removesuffix("[0]"): name for name in pinned if name.endswith("[0]")}
    problems: list[str] = []
    for port in sorted(ports):
        if port not in pinned and scalar.get(port) is None:
            problems.append(f"top port {port} has no pin")
    known = set(ports) | {scalar_name + "[0]" for scalar_name in ports}
    problems += [
        f"pin {port} is not a top port of {contract.top}" for port in sorted(pinned - known)
    ]
    return problems


def _clock_nets(fmax: dict[str, Any], port: str) -> list[str]:
    base = port.split("[", 1)[0]
    pattern = re.compile(rf"(^|[^A-Za-z0-9]){re.escape(base)}([^A-Za-z0-9]|$)")
    return [net for net in fmax if pattern.search(net)]


def check_timing(contract: FpgaContract, report: dict[str, Any]) -> Check:
    if not contract.clocks:
        return _na("fpga.timing", "contract declares no clocks")
    fmax = cast(dict[str, dict[str, float]], report.get("fmax", {}))
    problems: list[str] = []
    evidence: list[str] = []
    for clock in contract.clocks:
        nets = _clock_nets(fmax, clock.port)
        if not nets:
            problems.append(
                f"no timing data for clock {clock.port} (nets: {', '.join(fmax) or 'none'})"
            )
            continue
        for net in nets:
            achieved = float(fmax[net].get("achieved", 0.0))
            evidence.append(
                f"{clock.port}: {achieved:.2f} MHz achieved, {clock.frequency_mhz:g} MHz required"
            )
            if achieved < clock.frequency_mhz:
                problems.append(
                    f"clock {clock.port} ({net}) reaches {achieved:.2f} MHz "
                    f"< {clock.frequency_mhz:g} MHz"
                )
    for net, entry in fmax.items():
        achieved, constraint = (
            float(entry.get("achieved", 0.0)),
            float(entry.get("constraint", 0.0)),
        )
        if achieved < constraint and not any(
            net in _clock_nets(fmax, c.port) for c in contract.clocks
        ):
            problems.append(f"clock net {net} reaches {achieved:.2f} MHz < {constraint:g} MHz")
    return _check("fpga.timing", contract.top, problems, evidence)


def check_utilization(
    contract: FpgaContract, profile: DeviceProfile, report: dict[str, Any]
) -> Check:
    utilization = cast(dict[str, dict[str, int]], report.get("utilization", {}))
    if not utilization:
        return _check("fpga.utilization", profile.part, ["nextpnr report has no utilization"])
    problems: list[str] = []
    evidence: list[str] = []
    for cell, entry in sorted(utilization.items()):
        used, available = int(entry.get("used", 0)), int(entry.get("available", 0))
        if used == 0:
            continue
        resource_class = profile.resources.get(cell)
        if resource_class is None:
            problems.append(f"{cell}: used {used} but unclassified in profile {profile.id}")
            continue
        pct = 100.0 * used / available if available else 100.0
        evidence.append(f"{cell}={used}/{available} ({pct:.1f}%, {resource_class})")
        limit = contract.build.budget.limit(resource_class)
        if limit is not None and pct > limit:
            problems.append(f"{cell}: {pct:.1f}% exceeds the {resource_class} budget {limit:g}%")
    return _check("fpga.utilization", profile.part, problems, evidence)


def check_bitstream(
    contract: FpgaContract, profile: DeviceProfile, bitstream: Path, run: ToolRun
) -> tuple[Check, str | None]:
    if not run.ok:
        return _run_check("fpga.bitstream", contract.build.bitstream, run), None
    if not bitstream.is_file():
        return _check(
            "fpga.bitstream", contract.build.bitstream, ["packer wrote no bitstream"]
        ), None
    data = bitstream.read_bytes()
    digest = flow.sha256(bitstream)
    problems = flow.bitstream_problems(profile.family, data)
    evidence = [" ".join(run.argv), f"bytes={len(data)}", f"sha256={digest}"]
    return _check("fpga.bitstream", contract.build.bitstream, problems, evidence), (
        None if problems else digest
    )


def _load_inputs(
    contract_path: Path, profile_dirs: list[Path]
) -> tuple[FpgaContract, DeviceProfile, CircuitConnectivity | None, str | None, str | None]:
    contract = load_contract(contract_path)
    profile = load_profile(contract.device.profile, [contract_path.parent, *profile_dirs])
    if contract.circuit is None:
        return contract, profile, None, None, None
    path = resolve(contract_path, contract.circuit.connectivity)
    try:
        return contract, profile, load_circuit(path), sha256_file(path), None
    except (OSError, ValueError, ValidationError) as exc:
        return (
            contract,
            profile,
            None,
            None,
            f"circuit connectivity {contract.circuit.connectivity}: {exc}",
        )


def run_gates(
    contract_path: Path,
    out_dir: Path,
    *,
    full: bool = True,
    profile_dirs: list[Path] | None = None,
) -> GateReport:
    contract_path = contract_path.resolve()
    contract_sha = sha256_file(contract_path)
    scope: Literal["static", "full"] = "full" if full else "static"
    try:
        contract, profile, circuit, circuit_sha, circuit_problem = _load_inputs(
            contract_path, profile_dirs or []
        )
    except (OSError, ValueError, ValidationError) as exc:
        return GateReport(
            design=contract_path.name.removesuffix(".json").removesuffix(".fpga"),
            scope=scope,
            contract_sha256=contract_sha,
            circuit_sha256=None,
            profile=None,
            verdict=FAIL,
            checks=[Check(id="fpga.contract", status="fail", detail=str(exc))],
        )
    out_dir.mkdir(parents=True, exist_ok=True)
    checks = [
        check_contract(contract, contract_path, profile, circuit_problem),
        check_provenance(contract, contract_path),
        check_pins(contract, profile),
        check_constraints(contract, profile, contract_path),
    ]
    if contract.circuit is None:
        checks.append(_na("fpga.netlist_match", "contract links no circuit connectivity"))
    elif circuit is None:
        checks.append(
            _check("fpga.netlist_match", contract.device.ref, ["no circuit connectivity"])
        )
    else:
        checks.append(check_netlist_match(contract, profile, circuit))
    bitstream_sha: str | None = None
    renders: list[RenderRef] = []
    if full:
        if checks[0].status == "fail":
            checks.append(_check("fpga.lint", contract.top, ["contract gate failed"]))
        else:
            checks += _toolchain_checks(contract, contract_path, profile, out_dir)
            bitstream_check = next((c for c in checks if c.id == "fpga.bitstream"), None)
            if bitstream_check is not None and bitstream_check.status == "pass":
                bitstream_sha = next(
                    (
                        e.removeprefix("sha256=")
                        for e in bitstream_check.evidence
                        if e.startswith("sha256=")
                    ),
                    None,
                )
    if full:
        renders = _render_checks(contract, profile, out_dir, contract_path, checks)
    verdict: Verdict = PASS if all(c.status != "fail" for c in checks) else FAIL
    return GateReport(
        design=contract.name,
        scope=scope,
        contract_sha256=contract_sha,
        circuit_sha256=circuit_sha,
        profile=profile.id,
        bitstream_sha256=bitstream_sha,
        verdict=verdict,
        checks=checks,
        renders=renders,
    )


def _render_checks(
    contract: FpgaContract,
    profile: DeviceProfile,
    out_dir: Path,
    contract_path: Path,
    checks: list[Check],
) -> list[RenderRef]:
    """Render the run's views; failures are evidence notes, never verdicts."""
    from .render import related_check, render_view_pngs, skipped_note

    build_dir = resolve(contract_path, contract.build.dir)
    rendered, skipped = render_view_pngs(
        contract,
        profile,
        out_dir,
        build_dir=build_dir,
        views=["utilization", "timing", "floorplan", "waveform"],
        gate_report_path=out_dir / "_never.json",
    )
    for item in skipped:
        check_id = related_check(item["view"])
        note = skipped_note(item["view"], item["reason"])
        target = next((c for c in checks if c.id == check_id), None)
        if target is not None:
            target.evidence.append(note)
    return [
        RenderRef(
            view=str(item["view"]),
            path=Path(str(item["path"])).name,
            sha256=str(item["sha256"]),
        )
        for item in rendered
    ]


def _toolchain_checks(
    contract: FpgaContract, contract_path: Path, profile: DeviceProfile, out_dir: Path
) -> list[Check]:
    checks = [_run_check("fpga.lint", contract.top, flow.lint(contract, contract_path, out_dir))]
    checks += simulation_checks(contract, contract_path, out_dir)
    checks += formal_checks(contract, contract_path, out_dir)
    checks += implementation_checks(contract, contract_path, profile, out_dir)
    return checks


def simulation_checks(contract: FpgaContract, contract_path: Path, out_dir: Path) -> list[Check]:
    if not contract.simulations:
        return [_na("fpga.sim", "contract declares no simulation runs")]
    checks: list[Check] = []
    for sim in contract.simulations:
        result = run_simulation(contract, contract_path, sim, out_dir)
        evidence = [
            " ".join(result.argv),
            f"matched={len(result.matched)}/{len(sim.expect)}",
            f"seconds={result.seconds:.1f}",
        ]
        if result.waveform is not None:
            evidence.append(f"waveform={result.waveform.name}")
        checks.append(
            _check(
                f"fpga.sim.{sim.id}",
                f"{sim.runner}:{sim.top}",
                [] if result.ok else [result.detail],
                evidence,
            )
        )
    return checks


def formal_checks(contract: FpgaContract, contract_path: Path, out_dir: Path) -> list[Check]:
    if not contract.formal:
        return [_na("fpga.formal", "contract declares no formal runs")]
    checks: list[Check] = []
    for run in contract.formal:
        result = run_formal(contract, contract_path, run, out_dir)
        checks.append(
            _check(
                f"fpga.formal.{run.id}",
                f"{run.mode} depth {run.depth} ({run.engine})",
                [] if result.ok else [result.detail],
                [" ".join(result.argv), f"status={result.status}", f"seconds={result.seconds:.1f}"],
            )
        )
    return checks


def implementation_checks(
    contract: FpgaContract, contract_path: Path, profile: DeviceProfile, out_dir: Path
) -> list[Check]:
    out = flow.paths(contract, contract_path, profile)
    synth = flow.synthesize(contract, contract_path, profile, out_dir)
    port_problems = check_synth_ports(contract, out.netlist) if synth.ok else []
    synth_check = _run_check("fpga.synth", f"{flow.SYNTH[profile.family]} {contract.top}", synth)
    if port_problems:
        synth_check = _check("fpga.synth", synth_check.subject, port_problems, synth_check.evidence)
    downstream = ("fpga.pnr", "fpga.timing", "fpga.utilization", "fpga.bitstream")
    if synth_check.status == "fail":
        return [synth_check, *(_check(i, contract.name, ["synthesis failed"]) for i in downstream)]
    if not out.constraints.is_file():
        blocked = [_check(i, contract.name, ["constraint file missing"]) for i in downstream]
        return [synth_check, *blocked]
    pnr = flow.place_and_route(contract, contract_path, profile, out_dir)
    pnr_check = _run_check("fpga.pnr", flow.NEXTPNR[profile.family], pnr)
    if pnr_check.status == "fail":
        return [
            synth_check,
            pnr_check,
            *(_check(i, contract.name, ["place and route failed"]) for i in downstream[1:]),
        ]
    try:
        report = flow.load_report(out.report)
    except (OSError, json.JSONDecodeError) as exc:
        report_problem = [f"nextpnr report unreadable: {exc}"]
        return [
            synth_check,
            pnr_check,
            _check("fpga.timing", contract.top, report_problem),
            _check("fpga.utilization", profile.part, report_problem),
            _check("fpga.bitstream", contract.build.bitstream, ["no trusted layout"]),
        ]
    packed = flow.pack(contract, contract_path, profile, out_dir)
    bitstream_check, _ = check_bitstream(contract, profile, out.bitstream, packed)
    return [
        synth_check,
        pnr_check,
        check_timing(contract, report),
        check_utilization(contract, profile, report),
        bitstream_check,
    ]


def report_markdown(report: GateReport) -> str:
    lines = [
        f"# FPGA gate report: {report.design}",
        "",
        f"- verdict: **{report.verdict}** ({report.scope})",
        f"- device profile: {report.profile}",
        f"- contract sha256: `{report.contract_sha256}`",
        f"- circuit sha256: `{report.circuit_sha256}`",
        f"- bitstream sha256: `{report.bitstream_sha256}`",
        "",
        "| Check | Subject | Status | Detail |",
        "| --- | --- | --- | --- |",
    ]
    for check in report.checks:
        detail = check.detail or "; ".join(check.evidence[-3:])
        lines.append(
            f"| {check.id} | {check.subject} | {check.status} | {detail.replace('|', '\\|')} |"
        )
    return "\n".join(lines) + "\n"


def write_outputs(contract_path: Path, report: GateReport, out_dir: Path) -> list[Path]:
    """Write the report plus the pin map export and its Markdown view."""
    out_dir.mkdir(parents=True, exist_ok=True)
    written = [
        write_text(
            out_dir / f"{report.design}.fpga-report.json", report.model_dump_json(indent=2) + "\n"
        ),
        write_text(out_dir / f"{report.design}.fpga-report.md", report_markdown(report)),
    ]
    try:
        contract = load_contract(contract_path)
        profile = load_profile(contract.device.profile, [contract_path.parent])
    except (OSError, ValueError, ValidationError):
        return written
    circuit_sha: str | None = None
    if contract.circuit is not None:
        circuit_path = resolve(contract_path, contract.circuit.connectivity)
        if circuit_path.is_file():
            circuit_sha = sha256_file(circuit_path)
    pinmap = pinmap_export(contract, profile, sha256_file(contract_path), circuit_sha)
    written.append(
        write_text(
            out_dir / f"{contract.name}.fpga-pinmap.json",
            json.dumps(pinmap.model_dump(mode="json"), indent=2, ensure_ascii=False) + "\n",
        )
    )
    written.append(write_text(out_dir / f"{contract.name}.fpga-pinmap.md", pinmap_markdown(pinmap)))
    try:
        from .render import pinmap_canvas, report_canvas, write_png

        write_png(pinmap_canvas(contract, profile), out_dir / f"{contract.name}.fpga-pinmap.png")
        write_png(
            report_canvas(report.model_dump(mode="json")),
            out_dir / f"{contract.name}.fpga-report.png",
        )
    except Exception:  # renders are best-effort, never a verdict
        pass
    return written

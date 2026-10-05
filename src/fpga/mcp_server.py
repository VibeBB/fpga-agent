"""Expose the fpga entry points over a stdio MCP transport.

Every tool returns the same JSON payload as the CLI; the transport never
judges the design itself. Board programming is deliberately not exposed.
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import Callable, Mapping
from pathlib import Path

from mcp import types
from mcp.server import Server
from mcp.server.lowlevel import NotificationOptions
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server

from . import __version__, service
from .records import (
    DecisionInput,
    StageImpressionInput,
    VisionReviewInput,
    record_decision,
    record_impression,
    record_vision_review,
    records_summary,
)
from .workspace import workspace_path

server: Server = Server(f"fpga-mcp/{__version__}")

_CONTRACT = {"contract_path": {"type": "string"}}
_OUT = {"out_dir": {"type": "string"}}
_STRINGS = {"type": "array", "items": {"type": "string"}}


def _schema(properties: Mapping[str, object], required: list[str]) -> dict[str, object]:
    return {
        "type": "object",
        "properties": dict(properties),
        "required": required,
        "additionalProperties": False,
    }


TOOLS: dict[str, tuple[str, dict[str, object], bool]] = {
    "fpga_doctor": ("Probe the open-source FPGA toolchain", _schema({}, []), True),
    "fpga_validate": (
        "Validate a <name>.fpga.json contract and resolve its device profile",
        _schema(_CONTRACT, ["contract_path"]),
        True,
    ),
    "fpga_check": (
        "Static gates: contract, library provenance, pins, constraints, netlist match",
        _schema({**_CONTRACT, **_OUT}, ["contract_path"]),
        False,
    ),
    "fpga_gates": (
        "All gates: static + lint, simulation, formal, synthesis, P&R, timing, "
        "utilization, bitstream",
        _schema({**_CONTRACT, **_OUT}, ["contract_path"]),
        False,
    ),
    "fpga_constraints": (
        "Regenerate the contract's PCF/LPF/CST constraint file",
        _schema(_CONTRACT, ["contract_path"]),
        False,
    ),
    "fpga_pinmap_export": (
        "Export <name>.fpga-pinmap.json for electrical-circuit-agent",
        _schema({**_CONTRACT, **_OUT}, ["contract_path"]),
        False,
    ),
    "fpga_lint": (
        "Analyse and elaborate the design top (NVC for VHDL, Verilator for Verilog)",
        _schema({**_CONTRACT, **_OUT}, ["contract_path"]),
        False,
    ),
    "fpga_sim": (
        "Run one declared simulation (NVC or Icarus Verilog)",
        _schema(
            {**_CONTRACT, **_OUT, "simulation": {"type": "string"}}, ["contract_path", "simulation"]
        ),
        False,
    ),
    "fpga_formal": (
        "Run one declared SymbiYosys proof, BMC or cover",
        _schema({**_CONTRACT, **_OUT, "formal": {"type": "string"}}, ["contract_path", "formal"]),
        False,
    ),
    "fpga_build": (
        "Synthesis, place and route and bitstream packing (advisory; gates are authoritative)",
        _schema({**_CONTRACT, **_OUT}, ["contract_path"]),
        False,
    ),
    "fpga_request": (
        "Write a change request (*.fpga-request.json) to a sibling agent",
        _schema(
            {
                **_CONTRACT,
                **_OUT,
                "target": {"type": "string"},
                "risk": {"type": "string", "enum": ["low", "high"]},
                "change": {"type": "string"},
                "rationale": {"type": "string"},
                "nets": _STRINGS,
                "failing_checks": _STRINGS,
            },
            ["contract_path", "target", "risk", "change", "rationale"],
        ),
        False,
    ),
    "fpga_profile": (
        "List bundled device profiles, or show one (package pins, resources)",
        _schema({"profile": {"type": "string"}}, []),
        True,
    ),
    "fpga_record_decision": (
        "Record a non-trivial design decision (question, first principles, "
        "options, chosen option, 200+ char rationale, evidence, risks)",
        DecisionInput.model_json_schema(),
        False,
    ),
    "fpga_record_impression": (
        "Record a long-form stage impression (400+ chars, 3+ sentences) bound "
        "to the stage artifacts by sha256",
        StageImpressionInput.model_json_schema(),
        False,
    ),
    "fpga_record_vision_review": (
        "Record findings plus a long-form impression after looking at an image; "
        "bind to image_path or a vision source_event_id",
        VisionReviewInput.model_json_schema(),
        False,
    ),
    "fpga_records_status": (
        "Counts of decision / impression / vision-review records and the last "
        "Stop-hook verdict listing records this session still owes",
        _schema({}, []),
        True,
    ),
}


def tool_specs() -> list[types.Tool]:
    return [
        types.Tool(
            name=name,
            description=description,
            inputSchema=schema,
            annotations=types.ToolAnnotations(readOnlyHint=read_only),
        )
        for name, (description, schema, read_only) in TOOLS.items()
    ]


@server.list_tools()
async def list_tools() -> list[types.Tool]:
    return tool_specs()


def _str(arguments: dict[str, object], key: str) -> str:
    value = arguments.get(key)
    if not isinstance(value, str) or not value:
        raise ValueError(f"{key} must be a non-empty string")
    return value


def _contract(arguments: dict[str, object]) -> Path:
    return workspace_path(_str(arguments, "contract_path"))


def _opt_path(arguments: dict[str, object], key: str) -> Path | None:
    value = arguments.get(key)
    return workspace_path(value) if isinstance(value, str) and value else None


def _opt_str(arguments: dict[str, object], key: str) -> str | None:
    value = arguments.get(key)
    return value if isinstance(value, str) and value else None


def _strs(arguments: dict[str, object], key: str) -> list[str]:
    value = arguments.get(key)
    if value is None:
        return []
    if not isinstance(value, list):
        raise ValueError(f"{key} must be a list of strings")
    items: list[str] = []
    for item in value:  # pyright: ignore[reportUnknownVariableType]
        if not isinstance(item, str):
            raise ValueError(f"{key} must be a list of strings")
        items.append(item)
    return items


def dispatch(name: str, arguments: dict[str, object]) -> service.Json:
    handlers: dict[str, Callable[[], service.Json]] = {
        "fpga_doctor": service.doctor_payload,
        "fpga_validate": lambda: service.validate_payload(_contract(arguments)),
        "fpga_check": lambda: service.gates_payload(
            _contract(arguments), _opt_path(arguments, "out_dir"), full=False
        ),
        "fpga_gates": lambda: service.gates_payload(
            _contract(arguments), _opt_path(arguments, "out_dir"), full=True
        ),
        "fpga_constraints": lambda: service.constraints_payload(_contract(arguments)),
        "fpga_pinmap_export": lambda: service.pinmap_payload(
            _contract(arguments), _opt_path(arguments, "out_dir")
        ),
        "fpga_lint": lambda: service.lint_payload(
            _contract(arguments), _opt_path(arguments, "out_dir")
        ),
        "fpga_sim": lambda: service.sim_payload(
            _contract(arguments), _str(arguments, "simulation"), _opt_path(arguments, "out_dir")
        ),
        "fpga_formal": lambda: service.formal_payload(
            _contract(arguments), _str(arguments, "formal"), _opt_path(arguments, "out_dir")
        ),
        "fpga_build": lambda: service.build_payload(
            _contract(arguments), _opt_path(arguments, "out_dir")
        ),
        "fpga_request": lambda: service.request_payload(
            _contract(arguments),
            _opt_path(arguments, "out_dir"),
            target=_str(arguments, "target"),
            risk=_str(arguments, "risk"),
            change=_str(arguments, "change"),
            rationale=_str(arguments, "rationale"),
            nets=_strs(arguments, "nets"),
            failing_checks=_strs(arguments, "failing_checks"),
        ),
        "fpga_profile": lambda: service.profile_payload(_opt_str(arguments, "profile")),
        "fpga_record_decision": lambda: record_decision(arguments),
        "fpga_record_impression": lambda: record_impression(arguments),
        "fpga_record_vision_review": lambda: record_vision_review(arguments),
        "fpga_records_status": records_summary,
    }
    handler = handlers.get(name)
    if handler is None:
        return {"verdict": "fail", "detail": f"unknown tool {name}"}
    return handler()


@server.call_tool()
async def call_tool(name: str, arguments: dict[str, object]) -> types.CallToolResult:
    is_error = False
    try:
        payload = await asyncio.to_thread(dispatch, name, arguments or {})
        if name not in TOOLS:
            payload["error_type"] = "unknown_tool"
            is_error = True
    except Exception as exc:  # fail-closed transport
        payload = {
            "verdict": "fail",
            "detail": f"{name} error: {exc}",
            "error_type": type(exc).__name__,
        }
        is_error = True
    return types.CallToolResult(
        content=[
            types.TextContent(type="text", text=json.dumps(payload, ensure_ascii=False, indent=2))
        ],
        isError=is_error,
    )


async def _run() -> None:
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name=f"fpga-mcp/{__version__}",
                server_version=__version__,
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )


def main() -> None:
    asyncio.run(_run())


if __name__ == "__main__":
    main()

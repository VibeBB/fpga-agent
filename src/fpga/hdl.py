"""Compilation units and per-tool source arguments shared by every flow.

VHDL is compiled library by library in declaration order (external
libraries first, then the design's own libraries, then ``work``); each
unit keeps its files in the listed order. Verilog and SystemVerilog are a
flat file list.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .contract import FpgaContract, ParamValue, Source, library_files, resolve


@dataclass(frozen=True)
class Unit:
    library: str
    language: str
    files: tuple[Path, ...]


def units(
    contract: FpgaContract, contract_path: Path, extra: list[Source] | None = None
) -> list[Unit]:
    result: list[Unit] = [
        Unit(lib.name, lib.language, tuple(library_files(contract_path, lib)))
        for lib in contract.libraries
    ]
    sources = [*contract.sources, *(extra or [])]
    order: list[str] = []
    for source in sources:
        if source.library not in order:
            order.append(source.library)
    order.sort(key=lambda name: name == "work")
    for library in order:
        files = tuple(resolve(contract_path, s.path) for s in sources if s.library == library)
        language = next(s.language for s in sources if s.library == library)
        result.append(Unit(library, language, files))
    return result


def include_dirs(contract: FpgaContract, contract_path: Path) -> list[Path]:
    """Directories Verilog front ends search for `` `include `` files.

    Only the generated register-constants header is included today; it is
    never a source, so its directory has to be on every tool's search path.
    """
    regs = contract.registers
    if regs is None or contract.design_language == "vhdl":
        return []
    return [resolve(contract_path, regs.hdl_package).parent]


def all_files(unit_list: list[Unit]) -> list[Path]:
    return [path for unit in unit_list for path in unit.files]


def is_systemverilog(unit_list: list[Unit]) -> bool:
    return any(unit.language == "systemverilog" for unit in unit_list)


def param_text(value: ParamValue) -> str:
    if isinstance(value, bool):
        return "1" if value else "0"
    return str(value)


def vhdl_generic(value: ParamValue) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def ghdl_args(
    contract: FpgaContract, unit_list: list[Unit], top: str, parameters: dict[str, ParamValue]
) -> str:
    """Arguments of the Yosys ``ghdl`` command (ghdl-yosys-plugin)."""
    std = "08" if contract.build.vhdl_standard == "08" else "93c"
    parts = [f"--std={std}", "-frelaxed"]
    parts += [f"-g{k}={vhdl_generic(v)}" for k, v in parameters.items()]
    for unit in unit_list:
        parts.append(f"--work={unit.library}")
        parts += [path.as_posix() for path in unit.files]
    parts += ["-e", top]
    return " ".join(parts)


def verilog_read(
    contract: FpgaContract,
    unit_list: list[Unit],
    *,
    formal: bool,
    includes: list[Path] | None = None,
) -> list[str]:
    """Yosys commands that read the Verilog/SystemVerilog design."""
    defines = [f"-I{path.as_posix()}" for path in includes or []]
    defines += [f"-D{k}={v}" for k, v in contract.build.defines.items()]
    if formal:
        defines.append("-DFORMAL")
    files = [path.as_posix() for path in all_files(unit_list)]
    flag = "-sv" if is_systemverilog(unit_list) else ""
    mode = "-formal" if formal else ""
    return [" ".join(p for p in ["read_verilog", mode, flag, *defines, *files] if p)]

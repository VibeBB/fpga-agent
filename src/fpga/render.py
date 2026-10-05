"""Deterministic PNG renders of FPGA artifacts, stdlib only.

Six views give a vision model something to look at: the package pin map,
utilization against budgets, timing against requirements, the placed
floorplan, simulation waveforms (VCD) and the gate report itself. Renders
are advisory; a render failure never changes a gate verdict. Every image
is RGB8 PNG with filter 0 and zlib level 9, so bytes are deterministic.
"""

from __future__ import annotations

import contextlib
import hashlib
import json
import re
import struct
import zlib
from pathlib import Path
from typing import Any, Literal, cast

from .contract import FpgaContract
from .devices import DeviceProfile
from .gates import Check

MAX_DIM = 4096
VCD_MAX_BYTES = 64 * 1024 * 1024
VCD_MAX_CHANGES = 2_000_000
MAX_WAVE_ROWS = 32

WHITE = (255, 255, 255)
BLACK = (20, 20, 20)
GREY = (200, 200, 200)
DARK_GREY = (110, 110, 110)
RED = (210, 40, 40)
GREEN = (30, 150, 70)
BLUE = (40, 110, 220)
ORANGE = (235, 160, 30)
PURPLE = (150, 80, 200)
TEAL = (30, 160, 160)
LIGHT_GREEN = (220, 240, 220)

Color = tuple[int, int, int]

# 5x7 bitmap font, rows top to bottom, '#'/space pixels. Covers the
# characters used in labels; lowercase is folded to uppercase on draw and
# anything unknown renders as '?'.
_FONT_ROWS: dict[str, str] = {
    " ": "               ",
    "!": "  #    #    #    #    #         #  ",
    '"': " # #  # #  # #                    ",
    "#": " # #  # # ##### # # ##### # #  # # ",
    "$": "  #   #### # #   ###    # #####  #  ",
    "%": "##  ### #    #   #   #  # ##  ##",
    "&": " ##  #  # # #   #   # # #  #  ## #",
    "'": "  #    #   #                       ",
    "(": "   #   #   #    #    #    #    #  ",
    ")": " #     #    #    #    #   #   #   ",
    "*": "      #   # #  ###  # #   #       ",
    "+": "      #    #   ###   #    #       ",
    ",": "                  ##    #   #     ",
    "-": "             ###                  ",
    ".": "                  ##   ##         ",
    "/": "    #   #    #   #   #   #  #    ",
    "0": " ### #   ##  ## # ###   ##   # ### ",
    "1": "  #   ##    #    #    #    #   ### ",
    "2": " ### #   #    #  ##  #   #    #####",
    "3": " ### #   #    #  ##     ##   # ### ",
    "4": "   #   ##  # # #  #######   #   # ",
    "5": "######     ####     #    ##   # ### ",
    "6": "  ## #    #   #### #   ##   # ### ",
    "7": "######    #   #   #    #    #    # ",
    "8": " ### #   ##   # ### #   ##   # ### ",
    "9": " ### #   ##   # ####     #   #  ## ",
    ":": "      ##   ##        ##   ##       ",
    ";": "      ##   ##        ##   #   #    ",
    "<": "   #   #   #   #      #    #    # ",
    "=": "          ###       ###            ",
    ">": " #     #    #      #   #   #   #  ",
    "?": " ### #   #    #   #   #         #  ",
    "@": " ### #   ## ### # # ## ## #     ### ",
    "A": " ### #   ##   #######   ##   ##   #",
    "B": "#### #   ##   ##### #   ##   ##### ",
    "C": " ### #   ##    #    #    #   # ### ",
    "D": "###  #  # #   ##   ##   ##  # ###  ",
    "E": "######    #    #### #    #    #####",
    "F": "######    #    #### #    #    #    ",
    "G": " ### #   ##    #  ###   ##   # ####",
    "H": "#   ##   ##   #######   ##   ##   #",
    "I": " ###   #    #    #    #    #   ### ",
    "J": "    #    #    #    ##   ##   # ### ",
    "K": "#   ##  # # #  ##   # #  #  ##   #",
    "L": "#    #    #    #    #    #    #####",
    "M": "#   ### ### # ## # ##   ##   ##   #",
    "N": "#   ###  ## # ##  ###   ##   ##   #",
    "O": " ### #   ##   ##   ##   ##   # ### ",
    "P": "#### #   ##   ##### #    #    #    ",
    "Q": " ### #   ##   ##   ## # ##  #  ## #",
    "R": "#### #   ##   ##### # #  #  ##   #",
    "S": " #####    #     ###      #    #### ",
    "T": "#####  #    #    #    #    #    #  ",
    "U": "#   ##   ##   ##   ##   ##   # ### ",
    "V": "#   ##   ##   ##   # # #  # #   #  ",
    "W": "#   ##   ##   ## # ## # ## # # # # ",
    "X": "#   # # #   #    #    #  # # #   #",
    "Y": "#   # # #   #    #    #    #    #  ",
    "Z": "#####    #   #   #   #   #    #####",
    "[": " ###  #    #    #    #    #    ### ",
    "\\": "#     #    #    #    #   #      #",
    "]": " ###    #    #    #    #    #  ### ",
    "^": "  #   # # #   #                    ",
    "_": "                          #####",
    "{": "   #   #    #   #     #    #    # ",
    "|": "  #    #    #    #    #    #    #  ",
    "}": " #     #    #     #   #    #   #   ",
    "~": "        #  # # #  #               ",
}
_FALLBACK = _FONT_ROWS["?"]
_CELL = 6  # glyph advance in pixels at scale 1


class Canvas:
    """RGB8 pixel canvas with rects, Bresenham lines and 5x7 text."""

    def __init__(self, width: int, height: int, background: Color = WHITE) -> None:
        if not (0 < width <= MAX_DIM and 0 < height <= MAX_DIM):
            raise ValueError(f"canvas {width}x{height} exceeds the {MAX_DIM}px cap")
        self.width = width
        self.height = height
        self.pixels = bytearray(background * (width * height))

    def _set(self, x: int, y: int, color: Color) -> None:
        if 0 <= x < self.width and 0 <= y < self.height:
            offset = (y * self.width + x) * 3
            self.pixels[offset : offset + 3] = bytes(color)

    def fill_rect(self, x: int, y: int, width: int, height: int, color: Color) -> None:
        x0, y0 = max(0, x), max(0, y)
        x1, y1 = min(self.width, x + width), min(self.height, y + height)
        if x1 <= x0 or y1 <= y0:
            return
        row = bytes(color) * (x1 - x0)
        for yy in range(y0, y1):
            offset = (yy * self.width + x0) * 3
            self.pixels[offset : offset + len(row)] = row

    def rect(self, x: int, y: int, width: int, height: int, color: Color) -> None:
        self.fill_rect(x, y, width, 1, color)
        self.fill_rect(x, y + height - 1, width, 1, color)
        self.fill_rect(x, y, 1, height, color)
        self.fill_rect(x + width - 1, y, 1, height, color)

    def line(self, x0: int, y0: int, x1: int, y1: int, color: Color) -> None:
        dx, dy = abs(x1 - x0), -abs(y1 - y0)
        sx, sy = (1 if x0 < x1 else -1), (1 if y0 < y1 else -1)
        error = dx + dy
        while True:
            self._set(x0, y0, color)
            if x0 == x1 and y0 == y1:
                return
            e2 = 2 * error
            if e2 >= dy:
                error += dy
                x0 += sx
            if e2 <= dx:
                error += dx
                y0 += sy

    def text(self, x: int, y: int, text: str, color: Color, scale: int = 1) -> None:
        scale = max(1, min(3, scale))
        cx = x
        for char in text.upper():
            glyph = _FONT_ROWS.get(char, _FALLBACK)
            for row in range(7):
                bits = glyph[row * 5 : row * 5 + 5]
                for col, mark in enumerate(bits):
                    if mark != " ":
                        self.fill_rect(cx + col * scale, y + row * scale, scale, scale, color)
            cx += _CELL * scale

    def png_bytes(self) -> bytes:
        raw = b"".join(
            b"\x00" + bytes(self.pixels[y * self.width * 3 : (y + 1) * self.width * 3])
            for y in range(self.height)
        )
        compressed = zlib.compress(raw, 9)

        def chunk(tag: bytes, data: bytes) -> bytes:
            return (
                struct.pack(">I", len(data))
                + tag
                + data
                + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
            )

        return (
            b"\x89PNG\r\n\x1a\n"
            + chunk(b"IHDR", struct.pack(">IIBBBBB", self.width, self.height, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", compressed)
            + chunk(b"IEND", b"")
        )


def write_png(canvas: Canvas, path: Path) -> dict[str, object]:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = canvas.png_bytes()
    path.write_bytes(data)
    return {
        "path": path.name,
        "sha256": hashlib.sha256(data).hexdigest(),
        "width": canvas.width,
        "height": canvas.height,
    }


def _clip_label(canvas: Canvas, x: int, y: int, text: str, color: Color, scale: int) -> None:
    max_chars = max(1, (canvas.width - x - 8) // (_CELL * scale))
    canvas.text(x, y, text[:max_chars], color, scale)


def _legend(canvas: Canvas, x: int, y: int, entries: list[tuple[Color, str]]) -> None:
    for i, (color, label) in enumerate(entries):
        canvas.fill_rect(x, y + i * 18 + 2, 12, 12, color)
        canvas.rect(x, y + i * 18 + 2, 12, 12, BLACK)
        _clip_label(canvas, x + 16, y + i * 18, label, BLACK, 2)


_BGA_NAME = re.compile(r"^[A-Z]{1,2}[0-9]+$")


def _pin_color(contract: FpgaContract, profile: DeviceProfile, name: str) -> Color:
    by_pin = {p.package_pin: p for p in contract.pins}
    clocks = {c.port for c in contract.clocks}
    entry = by_pin.get(name)
    device_pin = profile.pin(name)
    if entry is not None:
        if device_pin is not None and device_pin.caution is not None:
            return ORANGE
        return GREEN if entry.port in clocks else BLUE
    if device_pin is None:
        return DARK_GREY
    if device_pin.caution is not None:
        return RED
    return GREY


def pinmap_canvas(contract: FpgaContract, profile: DeviceProfile) -> Canvas:
    """Package drawing: a BGA grid or a QFP-style perimeter + pin table."""
    names = [p.name for p in profile.pins]
    margin, cell, gap = 12, 30, 4
    positions: dict[str, tuple[int, int]] = {}
    if names and all(_BGA_NAME.match(n) for n in names):
        letters = sorted(
            {match.group(0) for n in names if (match := re.match(r"[A-Z]+", n)) is not None}
        )
        digits = sorted(
            {int(match.group(0)) for n in names if (match := re.search(r"[0-9]+", n)) is not None}
        )
        for row, letter in enumerate(letters):
            for col, digit in enumerate(digits):
                name = f"{letter}{digit}"
                positions[name] = (
                    margin + col * (cell + gap),
                    margin + row * (cell + gap),
                )
        grid_w = margin + len(digits) * (cell + gap)
        grid_h = margin + len(letters) * (cell + gap)
    else:
        match = re.search(r"(\d+)\s*$", profile.package)
        if match:
            count = int(match.group(1))
        else:
            numeric = [int(n) for n in names if n.isdigit()]
            count = max(numeric) if numeric else len(names)
        count = max(count, len(names))
        numeric_names = sorted((n for n in names if n.isdigit()), key=int)
        ordered = numeric_names if len(numeric_names) >= count else names
        side = max(1, count // 4)
        box = side * 16 + 2 * margin
        for index, name in enumerate(ordered):
            edge, slot = divmod(index, side)
            x, y = margin + slot * 16, margin + side * 16 + slot * 0
            if edge == 0:  # left edge, pin 1 at top
                x, y = margin, margin + slot * 16
            elif edge == 1:  # bottom, left to right
                x, y = margin + slot * 16, margin + side * 16
            elif edge == 2:  # right, bottom to top
                x, y = margin + side * 16, margin + (side - 1 - slot) * 16
            else:  # top, right to left
                x, y = margin + (side - 1 - slot) * 16, margin
            positions[name] = (x, y)
        grid_w = box + 2 * margin
        grid_h = box + 2 * margin
    used = {p.package_pin for p in contract.pins}
    user_io = len(profile.pins)
    table_x = grid_w + 20
    table_y = 56
    row_h = 16
    table_h = table_y + (len(contract.pins) + 2) * row_h
    height = max(grid_h + 60, table_h + 140)
    canvas = Canvas(min(table_x + 860, MAX_DIM), min(height, MAX_DIM))
    title = (
        f"{contract.name} pin map - {profile.part} {profile.package} "
        f"({len(used)}/{user_io} user I/O)"
    )
    canvas.text(12, 12, title, BLACK, 2)
    if positions and all(_BGA_NAME.match(n) for n in names):
        for name, (x, y) in positions.items():
            canvas.fill_rect(x, y, cell, cell, _pin_color(contract, profile, name))
            canvas.rect(x, y, cell, cell, BLACK)
            canvas.text(x + 1, y + 10, name, BLACK, 1)
    else:
        x0, y0, size = margin + 32, margin + 32, (max(1, len(positions) // 4)) * 16 - 32
        canvas.fill_rect(x0, y0, size, size, (245, 245, 245))
        canvas.rect(x0, y0, size, size, BLACK)
        canvas.text(x0 + 8, y0 + 8, profile.package, BLACK, 1)
        for name, (x, y) in positions.items():
            canvas.fill_rect(x, y, 14, 14, _pin_color(contract, profile, name))
            canvas.rect(x, y, 14, 14, BLACK)
            canvas.text(x + 3, y + 4, name, BLACK, 1)
    _legend(
        canvas,
        12,
        max(grid_h + 12, 40),
        [
            (BLUE, "used signal"),
            (GREEN, "used clock"),
            (ORANGE, "used caution pin (acknowledged)"),
            (RED, "unused caution pin"),
            (GREY, "free user I/O"),
            (DARK_GREY, "not user I/O"),
        ],
    )
    canvas.text(table_x, 24, "package pin  port      net      io_std   pull", BLACK, 1)
    canvas.line(table_x, 36, table_x + 520, 36, BLACK)
    for row, pin in enumerate(contract.pins):
        y = table_y + row * row_h
        canvas.fill_rect(table_x - 4, y, 8, 8, _pin_color(contract, profile, pin.package_pin))
        canvas.rect(table_x - 4, y, 8, 8, BLACK)
        columns = (
            f"{pin.package_pin:<12} {pin.port:<11} {(pin.net or '-'):<10} "
            f"{pin.io_standard or '-':<8} {pin.pull or '-'}"
        )
        _clip_label(canvas, table_x + 10, y, columns, BLACK, 1)
    return canvas


def utilization_canvas(
    contract: FpgaContract, profile: DeviceProfile, report: dict[str, Any]
) -> Canvas:
    """One bar per used cell type against its resource-class budget."""
    utilization = cast(dict[str, dict[str, int]], report.get("utilization", {}))
    entries = sorted(
        (cell, int(e.get("used", 0)), int(e.get("available", 0)))
        for cell, e in utilization.items()
        if int(e.get("used", 0)) > 0
    )
    width, row_h = 900, 44
    height = 70 + max(1, len(entries)) * row_h
    canvas = Canvas(min(width, MAX_DIM), min(height, MAX_DIM))
    canvas.text(12, 12, f"{contract.name} utilization - {profile.part}", BLACK, 2)
    bar_x, bar_w = 300, 520
    for row, (cell, used, available) in enumerate(entries):
        y = 50 + row * row_h
        resource_class = profile.resources.get(cell, "other")
        pct = 100.0 * used / available if available else 100.0
        budget = contract.build.budget.limit(resource_class)
        over = budget is not None and pct > budget
        canvas.fill_rect(bar_x, y + 6, bar_w, 16, (235, 235, 235))
        fill = int(bar_w * min(pct, 100.0) / 100.0)
        canvas.fill_rect(bar_x, y + 6, fill, 16, RED if over else BLUE)
        if budget is not None:
            marker = bar_x + int(bar_w * budget / 100.0)
            canvas.line(marker, y + 2, marker, y + 26, BLACK)
        label = f"{cell} {used}/{available} {pct:.1f}% {resource_class}" + (
            f" (budget {budget:g}%)" if budget is not None else ""
        )
        _clip_label(canvas, 12, y + 2, label, RED if over else BLACK, 2)
    if not entries:
        canvas.text(12, 60, "no utilization data", RED, 2)
    return canvas


def timing_canvas(contract: FpgaContract, report: dict[str, Any]) -> Canvas:
    """Achieved vs required MHz per clock net, with slack and worst path."""
    fmax = cast(dict[str, dict[str, float]], report.get("fmax", {}))
    paths_data: Any = report.get("critical_paths", {})
    rows: list[tuple[str, float, float]] = []
    for clock in contract.clocks:
        base = clock.port.split("[", 1)[0]
        pattern = re.compile(rf"(^|[^A-Za-z0-9]){re.escape(base)}([^A-Za-z0-9]|$)")
        nets = [net for net in fmax if pattern.search(net)]
        for net in nets or [clock.port]:
            achieved = float(fmax.get(net, {}).get("achieved", 0.0))
            rows.append((net, achieved, clock.frequency_mhz))
    width, row_h = 900, 40
    worst: list[tuple[str, dict[str, Any]]] = []
    if isinstance(paths_data, dict):
        for net, info in cast(dict[str, Any], paths_data).items():
            if isinstance(info, dict):
                worst.append((str(net), cast(dict[str, Any], info)))
    elif isinstance(paths_data, list):
        for entry in cast(list[Any], paths_data)[:6]:
            if isinstance(entry, dict):
                item = cast(dict[str, Any], entry)
                label = f"{item.get('from', '?')} -> {item.get('to', '?')}"
                merged = dict(item)
                merged.setdefault("segments", item.get("path", []))
                worst.append((label, merged))
    height = 70 + max(1, len(rows)) * row_h + len(worst) * 90
    canvas = Canvas(min(width, MAX_DIM), min(height, MAX_DIM))
    canvas.text(12, 12, f"{contract.name} timing", BLACK, 2)
    bar_x, bar_w = 300, 520
    for row, (net, achieved, required) in enumerate(rows):
        y = 50 + row * row_h
        slack = (1000.0 / required - 1000.0 / achieved) if achieved else float("-inf")
        scale_max = max(required, achieved, 1.0) * 1.2
        canvas.fill_rect(bar_x, y + 6, bar_w, 14, (235, 235, 235))
        canvas.fill_rect(
            bar_x,
            y + 6,
            int(bar_w * min(achieved, scale_max) / scale_max),
            14,
            GREEN if achieved >= required else RED,
        )
        canvas.line(
            bar_x + int(bar_w * required / scale_max),
            y + 2,
            bar_x + int(bar_w * required / scale_max),
            y + 24,
            BLACK,
        )
        slack_text = f"slack {slack:.2f} ns" if achieved else "no timing data"
        _clip_label(
            canvas,
            12,
            y + 2,
            f"{net} {achieved:.2f}/{required:g} MHz {slack_text}",
            GREEN if achieved >= required else RED,
            2,
        )
    if not rows:
        canvas.text(12, 60, "contract declares no clocks", DARK_GREY, 2)
    y = 60 + len(rows) * row_h
    for net, info in worst:
        canvas.text(12, y, f"worst path on {net}:", BLACK, 2)
        delay = info.get("total_delay_ns", info.get("delay", "?"))
        canvas.text(
            12,
            y + 20,
            f"{info.get('from', '?')} -> {info.get('to', '?')} {delay} ns",
            DARK_GREY,
            2,
        )
        segments = info.get("segments", [])
        if isinstance(segments, list):
            for seg_i, segment in enumerate(cast(list[Any], segments)[:5]):
                if isinstance(segment, dict):
                    seg = cast(dict[str, Any], segment)
                    seg_text = (
                        f"{seg.get('type', '?')} {float(seg.get('delay', 0.0)):.2f} ns "
                        f"{seg.get('net', '')}"
                    )
                else:
                    seg_text = str(segment)
                canvas.text(24, y + 40 + seg_i * 16, seg_text[:72], DARK_GREY, 1)
        y += 90
    return canvas


_BEL = re.compile(r"X(\d+)/?Y(\d+)")
_CLASS_COLORS: dict[str, Color] = {
    "logic": BLUE,
    "ram": PURPLE,
    "dsp": ORANGE,
    "io": TEAL,
    "clock": GREEN,
    "pll": GREEN,
    "other": DARK_GREY,
}


def _bel_coords(attributes: dict[str, Any]) -> tuple[int, int] | None:
    for key in ("NEXTPNR_BEL", "bel", "BEL"):
        value = attributes.get(key)
        if isinstance(value, str):
            match = _BEL.search(value)
            if match:
                return int(match.group(1)), int(match.group(2))
    return None


def floorplan_canvas(placed: dict[str, Any], profile: DeviceProfile, top: str) -> Canvas:
    """Tile grid of placed cells, colored by the dominant resource class."""
    modules = cast(dict[str, Any], placed.get("modules", {}))
    module = cast(dict[str, Any] | None, modules.get(top))
    if module is None:
        module = next(iter(modules.values()), None)
    cells = cast(dict[str, Any], (module or {}).get("cells", {}))
    grid: dict[tuple[int, int], dict[str, int]] = {}
    for cell in cells.values():
        cell = cast(dict[str, Any], cell)
        coords = _bel_coords(cast(dict[str, Any], cell.get("attributes", {})))
        if coords is None:
            continue
        resource_class = profile.resources.get(str(cell.get("type", "")), "other")
        bucket = grid.setdefault(coords, {})
        bucket[resource_class] = bucket.get(resource_class, 0) + 1
    if not grid:
        canvas = Canvas(420, 120)
        canvas.text(12, 40, "no NEXTPNR_BEL placement data", RED, 2)
        return canvas
    max_x = max(x for x, _ in grid)
    max_y = max(y for _, y in grid)
    tile = 14
    origin_x, origin_y = 60, 50
    width = origin_x + (max_x + 1) * tile + 260
    height = origin_y + (max_y + 1) * tile + 60
    canvas = Canvas(min(width, MAX_DIM), min(height, MAX_DIM))
    counts: dict[str, int] = {}
    for bucket in grid.values():
        for resource_class, n in bucket.items():
            counts[resource_class] = counts.get(resource_class, 0) + n
    summary = ", ".join(f"{k}={v}" for k, v in sorted(counts.items()))
    canvas.text(12, 12, f"{top} floorplan ({summary})", BLACK, 2)
    for (gx, gy), bucket in sorted(grid.items()):
        dominant, total = max(bucket.items(), key=lambda kv: kv[1])
        total = sum(bucket.values())
        base = _CLASS_COLORS.get(dominant, DARK_GREY)
        intensity = 255 - min(160, 60 * total)
        color = tuple(min(255, c * intensity // 255 + (255 - intensity)) for c in base)
        canvas.fill_rect(
            origin_x + gx * tile,
            origin_y + gy * tile,
            tile - 1,
            tile - 1,
            cast(Color, color),
        )
    for gx in range(0, max_x + 1, max(1, (max_x + 1) // 10)):
        canvas.line(origin_x + gx * tile, origin_y - 4, origin_x + gx * tile, origin_y, BLACK)
        canvas.text(origin_x + gx * tile, origin_y - 16, str(gx), BLACK, 1)
    for gy in range(0, max_y + 1, max(1, (max_y + 1) // 10)):
        canvas.line(origin_x - 4, origin_y + gy * tile, origin_x, origin_y + gy * tile, BLACK)
        canvas.text(origin_x - 40, origin_y + gy * tile, str(gy), BLACK, 1)
    canvas.text(origin_x + (max_x + 1) * tile // 2, origin_y - 34, "X", BLACK, 1)
    canvas.text(origin_x - 52, origin_y + (max_y + 1) * tile // 2, "Y", BLACK, 1)
    _legend(
        canvas,
        origin_x + (max_x + 1) * tile + 20,
        origin_y,
        [(_CLASS_COLORS[k], f"{k} ({v})") for k, v in sorted(counts.items())],
    )
    return canvas


def _hex(bits: str) -> str:
    if set(bits) - {"0", "1"}:
        return "x"
    value = int(bits, 2) if bits else 0
    width = max(1, (len(bits) + 3) // 4)
    return f"{value:0{width}x}"


class VcdSignal:
    __slots__ = ("changes", "name", "scope", "width")

    def __init__(self, name: str, scope: str, width: int) -> None:
        self.name = name
        self.scope = scope
        self.width = width
        self.changes: list[tuple[int, str]] = []


def parse_vcd(path: Path) -> tuple[list[VcdSignal], str, bool]:
    """Parse a VCD file; returns (signals, timescale, truncated)."""
    size = path.stat().st_size
    truncated = size > VCD_MAX_BYTES
    with path.open("rb") as stream:
        data = stream.read(VCD_MAX_BYTES)
    text = data.decode("ascii", "replace")
    header, _, body = text.partition("$enddefinitions")
    signals: dict[str, VcdSignal] = {}
    timescale = "1ns"
    scopes: list[str] = []
    top_scope: str | None = None
    for match in re.finditer(r"\$(timescale|scope|upscope|var)\b([^$]*)", header):
        kind, rest = match.group(1), match.group(2)
        if kind == "timescale":
            parts = rest.replace("$end", "").split()
            if parts:
                timescale = parts[0]
        elif kind == "scope":
            parts = rest.split()
            if len(parts) >= 2:
                scopes.append(parts[1])
                if top_scope is None:
                    top_scope = parts[1]
        elif kind == "upscope":
            if scopes:
                scopes.pop()
        elif kind == "var":
            parts = rest.replace("$end", "").split()
            if len(parts) >= 4:
                ident = parts[2]
                name = parts[3].split("[")[0]
                width = int(parts[1]) if parts[1].isdigit() else 1
                signals[ident] = VcdSignal(name, ".".join(scopes), width)
    changes = 0
    time = 0
    for line in body.splitlines():
        line = line.strip()
        if not line:
            continue
        if line[0] == "#":
            with contextlib.suppress(ValueError):
                time = int(line[1:])
            continue
        if line[0] == "$":
            continue
        if line[0] in "bBrR":
            value, _, ident = line[1:].partition(" ")
            signal = signals.get(ident)
            if signal is not None:
                signal.changes.append((time, value.lower()))
                changes += 1
        else:
            signal = signals.get(line[1:])
            if signal is not None:
                signal.changes.append((time, line[0].lower()))
                changes += 1
        if changes > VCD_MAX_CHANGES:
            truncated = True
            break
    ordered = sorted(signals.values(), key=lambda s: (s.scope != top_scope, s.scope, s.name))
    return ordered[:MAX_WAVE_ROWS], timescale, truncated


def waveform_canvas(vcd_path: Path, title: str) -> Canvas:
    """Digital traces from a VCD file: scalars as waveforms, buses as boxes."""
    signals, timescale, truncated = parse_vcd(vcd_path)
    if truncated:
        title = f"{title} TRUNCATED"
    label_w = 170
    t0 = min((c[0] for s in signals for c in s.changes), default=0)
    t1 = max((c[0] for s in signals for c in s.changes), default=1)
    span = max(1, t1 - t0)
    row_h = 30
    width = 980
    height = 80 + max(1, len(signals)) * row_h + 30
    canvas = Canvas(min(width, MAX_DIM), min(height, MAX_DIM))
    canvas.text(12, 12, f"{title} ({timescale})", BLACK, 2)
    plot_x, plot_w = label_w, width - label_w - 20
    axis_y = 60 + len(signals) * row_h + 6
    canvas.line(plot_x, axis_y, plot_x + plot_w, axis_y, BLACK)
    ticks = 10
    for i in range(ticks + 1):
        t = t0 + span * i // ticks
        x = plot_x + plot_w * i // ticks
        canvas.line(x, axis_y, x, axis_y + 4, BLACK)
        canvas.text(x, axis_y + 8, str(t), DARK_GREY, 1)

    def x_of(t: int) -> int:
        return plot_x + int(plot_w * (t - t0) / span)

    for row, signal in enumerate(signals):
        y = 60 + row * row_h
        mid, hi, lo = y + 14, y + 4, y + 24
        label = f"{signal.name} [{signal.width}]" if signal.width > 1 else signal.name
        _clip_label(canvas, 8, y + 6, label, BLACK, 2)
        changes = signal.changes
        if not changes:
            canvas.text(plot_x + 4, mid - 4, "x", RED, 2)
            continue
        if len(changes) > plot_w * 2:
            xs = {x_of(c[0]) for c in changes}
            canvas.fill_rect(min(xs), hi, max(xs) - min(xs) + 1, lo - hi, (190, 215, 255))
            canvas.rect(min(xs), hi, max(xs) - min(xs) + 1, lo - hi, BLUE)
            continue
        if signal.width == 1:
            prev_t, prev_v = changes[0]
            for t, v in [*changes[1:], (t1, prev_v)]:
                x0, x1 = x_of(prev_t), x_of(t)
                if prev_v in ("x", "z"):
                    canvas.line(x0, mid, x1, mid, RED)
                else:
                    level = hi if prev_v == "1" else lo
                    canvas.line(x0, level, x1, level, BLACK)
                    if t != prev_t:
                        canvas.line(x0, hi if prev_v != "1" else lo, x0, level, BLACK)
                prev_t, prev_v = t, v
            if prev_v in ("x", "z"):
                canvas.line(x_of(prev_t), mid, plot_x + plot_w, mid, RED)
        else:
            prev_t, prev_v = changes[0]
            for t, v in [*changes[1:], (t1, prev_v)]:
                x0, x1 = x_of(prev_t), x_of(t)
                if x1 - x0 < 2:
                    prev_t, prev_v = t, v
                    continue
                canvas.line(x0, hi, x1, hi, BLACK)
                canvas.line(x0, lo, x1, lo, BLACK)
                canvas.line(x0, hi, x0, lo, BLACK)
                canvas.line(x1, hi, x1, lo, BLACK)
                value = _hex(prev_v) if set(prev_v) <= {"0", "1"} else "x"
                if x1 - x0 > 30:
                    canvas.text(
                        x0 + 4,
                        mid - 4,
                        value[: (x1 - x0 - 6) // 6],
                        RED if value == "x" else DARK_GREY,
                        1,
                    )
                prev_t, prev_v = t, v
    return canvas


def report_canvas(report: dict[str, Any]) -> Canvas:
    """One row per gate check with a status chip, plus a verdict banner."""
    checks = cast(list[dict[str, Any]], report.get("checks", []))
    verdict = str(report.get("verdict", "fail"))
    width, row_h = 980, 30
    height = 80 + max(1, len(checks)) * row_h
    canvas = Canvas(min(width, MAX_DIM), min(height, MAX_DIM))
    banner = GREEN if verdict == "pass" else RED
    canvas.fill_rect(0, 0, canvas.width, 44, banner)
    canvas.text(
        12,
        12,
        f"{report.get('design', '?')} gate report: {verdict.upper()} ({report.get('scope', '?')})",
        WHITE,
        2,
    )
    chips = {"pass": GREEN, "fail": RED, "not_applicable": GREY}
    for row, check in enumerate(checks):
        y = 60 + row * row_h
        status = str(check.get("status", "fail"))
        canvas.fill_rect(8, y, 110, 22, chips.get(status, GREY))
        canvas.text(14, y + 6, status.replace("_", " "), WHITE, 1)
        detail = str(check.get("detail") or "")
        subject = str(check.get("subject") or "")
        _clip_label(
            canvas,
            128,
            y + 4,
            f"{check.get('id', '?')}  {subject}  {detail}",
            RED if status == "fail" else BLACK,
            2,
        )
    return canvas


RenderView = Literal["pinmap", "utilization", "timing", "floorplan", "waveform", "report"]


def render_view_pngs(
    contract: FpgaContract,
    profile: DeviceProfile,
    out_dir: Path,
    *,
    build_dir: Path,
    views: list[str] | None = None,
    gate_report_path: Path | None = None,
) -> tuple[list[dict[str, object]], list[dict[str, str]]]:
    """Render requested views from existing artifacts; never raises."""
    wanted = set(views or ["all"])
    rendered: list[dict[str, object]] = []
    skipped: list[dict[str, str]] = []

    def want(view: str) -> bool:
        return "all" in wanted or view in wanted

    def emit(view: str, path: Path, canvas: Canvas) -> None:
        info = write_png(canvas, path)
        rendered.append({"view": view, **info, "path": str(path)})

    def attempt(view: str, fn: Any, *args: Any) -> None:
        try:
            fn(*args)
        except Exception as exc:  # renders never fail the run
            skipped.append({"view": view, "reason": str(exc)})

    if want("pinmap"):
        attempt(
            "pinmap",
            lambda: emit(
                "pinmap",
                out_dir / f"{contract.name}.fpga-pinmap.png",
                pinmap_canvas(contract, profile),
            ),
        )
    report_json = build_dir / f"{contract.name}.nextpnr-report.json"
    if want("utilization"):

        def _util() -> None:
            report = json.loads(report_json.read_text(encoding="utf-8"))
            emit(
                "utilization",
                out_dir / f"{contract.name}.fpga-utilization.png",
                utilization_canvas(contract, profile, cast(dict[str, Any], report)),
            )

        if report_json.is_file():
            attempt("utilization", _util)
        else:
            skipped.append({"view": "utilization", "reason": "no nextpnr report"})
    if want("timing"):

        def _timing() -> None:
            report = json.loads(report_json.read_text(encoding="utf-8"))
            emit(
                "timing",
                out_dir / f"{contract.name}.fpga-timing.png",
                timing_canvas(contract, cast(dict[str, Any], report)),
            )

        if report_json.is_file():
            attempt("timing", _timing)
        else:
            skipped.append({"view": "timing", "reason": "no nextpnr report"})
    placed = build_dir / f"{contract.name}.placed.json"
    if not placed.is_file():
        placed = build_dir / f"{contract.name}.pnr.json"
    if want("floorplan"):

        def _floorplan() -> None:
            text = placed.read_text(encoding="utf-8")
            try:
                data: dict[str, Any] = cast(dict[str, Any], json.loads(text))
            except json.JSONDecodeError:
                # nextpnr writes attributes verbatim, so quotes inside HDL
                # attributes can make the JSON unparseable; degrade to a
                # regex scan of the NEXTPNR_BEL strings only.
                bels = re.findall(r'"NEXTPNR_BEL":\s*"([^"]+)"', text)
                data = {
                    "modules": {
                        contract.top: {
                            "cells": {
                                f"cell{i}": {"type": "", "attributes": {"NEXTPNR_BEL": bel}}
                                for i, bel in enumerate(bels)
                            }
                        }
                    }
                }
            emit(
                "floorplan",
                out_dir / f"{contract.name}.fpga-floorplan.png",
                floorplan_canvas(data, profile, contract.top),
            )

        if placed.is_file():
            attempt("floorplan", _floorplan)
        else:
            skipped.append({"view": "floorplan", "reason": "no placed netlist"})
    if want("waveform"):
        vcds = sorted(out_dir.glob("sim-*.vcd"))
        if not vcds:
            skipped.append({"view": "waveform", "reason": "no sim-*.vcd captures"})
        for vcd in vcds:
            sim_id = vcd.stem.removeprefix("sim-")
            attempt(
                f"waveform:{sim_id}",
                lambda vcd=vcd, sim_id=sim_id: emit(
                    "waveform",
                    out_dir / f"{contract.name}.fpga-wave-{sim_id}.png",
                    waveform_canvas(vcd, f"{contract.name} wave {sim_id}"),
                ),
            )
    report_path = gate_report_path or out_dir / f"{contract.name}.fpga-report.json"
    if want("report"):

        def _report() -> None:
            data = json.loads(report_path.read_text(encoding="utf-8"))
            emit(
                "report",
                out_dir / f"{contract.name}.fpga-report.png",
                report_canvas(cast(dict[str, Any], data)),
            )

        if report_path.is_file():
            attempt("report", _report)
        else:
            skipped.append({"view": "report", "reason": "no gate report"})
    return rendered, skipped


def skipped_note(view: str, reason: str) -> str:
    return f"render {view} skipped: {reason}"


def related_check(view: str) -> str | None:
    """Gate check a failed/skipped render should be noted on."""
    base = view.split(":", 1)[0]
    return {
        "pinmap": "fpga.pins",
        "utilization": "fpga.utilization",
        "timing": "fpga.timing",
        "floorplan": "fpga.pnr",
        "waveform": f"fpga.sim.{view.split(':', 1)[1]}" if ":" in view else "fpga.sim",
        "report": None,
    }.get(base)


__all__ = [
    "Canvas",
    "Check",
    "VcdSignal",
    "floorplan_canvas",
    "parse_vcd",
    "pinmap_canvas",
    "related_check",
    "render_view_pngs",
    "report_canvas",
    "skipped_note",
    "timing_canvas",
    "utilization_canvas",
    "waveform_canvas",
    "write_png",
]

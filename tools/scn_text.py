#!/usr/bin/env python3
"""Readable, editable text form of the DW1 scene scripts.

The text is a textual assembler for ``DG.SCN`` and ``MAPHEAD.SCN``.  The Rust
build (``crates/dw1/build.rs``) assembles and embeds it, so these files -- not
the SCN blobs -- are the source of truth.  ``disassemble`` turns an SCN into this text and ``assemble`` turns
the text back into the exact original bytes.

Layout of a file::

    # DW1-SCN-TEXT 1
    # DG.SCN: the map scripts and their offset table.

    .scn DG

    .header
      .offsets
      .names
        "\\SCN\\MAP133.SCN"
        ...
      .end
      .bytes 5c 53 43 4e
    .end

    .map 0
      .copy MAPHEAD 0x606e
      .copy MAPHEAD 0x0792
    .end

    .map 1
      .entries
        0x0fe -> m1_s2c
        0x005 -> m1_sa8
      .end
    m1_s2c:
      SET_BGM bgm=0x25
      .if
        THEN pstat 0x6b >= 0x07
        if false goto m1_b2a
      .end
    m1_b2a:
      .text
        "こんにちは"
      .end
      END_SECTION
    .end

Sections are laid out in file order and end at the next label (or the object's
``.end``).  Section labels carry the section's offset in the object (``m1_s2c``
is map 1, object offset 0x2c) and every branch/selection/switch target gets its
own label (``m1_b3a``), so code can be inserted without retargeting jumps.  Text
is standard ASCII for the glyphs the game font maps from ASCII (``"I'll go"``);
other CP932 glyphs keep their character, and ``{control}`` /
``{control:args}`` tokens cover the interpreter's text commands.  Known pstat
indices (date fields, shop variable, builtin arguments) are annotated, and the
``pstat`` subcommand lists where one is written and read.  Digimon, item
and move operands take an id or a US name (``digimon=Agumon``,
``item="Blue Flute"``); the disassembler also appends the name as a comment.

Bytes that are not reachable code (stale CD-buffer tails) are written as
``.copy`` of an earlier range, ``.pad`` for zeros, ``.byte`` for one byte, a
nested ``.script`` object, or ``.bytes`` if nothing else fits.  The real files
need only ``.copy``/``.pad``/``.script`` here.
"""

from __future__ import annotations

import argparse
import bisect
import re
import sys
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

import scn_dumper as D


HEADER = "# DW1-SCN-TEXT 1"
DG_HEADER_SIZE = 0x800
DG_OFFSET_ENTRIES = 223
DG_NAMES_OFFSET = 0x37C
DG_NAMES_SIZE = 0x480

# ---------------------------------------------------------------------------
# Text controls, from showTextbox() in script_textbox.c.  Every control is one
# byte plus this many argument bytes.
# ---------------------------------------------------------------------------

CONTROLS: dict[int, tuple[str, int]] = {
    0x01: ("color", 1),
    0x02: ("ctrl02", 1),
    0x03: ("raw", 3),
    0x04: ("pstat_number", 1),
    0x05: ("speaker_jijimon", 1),
    0x06: ("speaker_player", 1),
    0x07: ("digimon_name", 1),
    0x08: ("move_name", 1),
    0x09: ("item_name", 1),
    0x0A: ("money", 1),
    0x0B: ("merit", 1),
    0x0C: ("clear8", 1),
    0x0D: ("newline", 1),
    0x0E: ("clear11", 1),
    0x0F: ("clear6", 1),
    0x10: ("shop_variable", 1),
    0x11: ("bgm_name", 1),
    0x12: ("tournament_name", 1),
    0x13: ("tournaments_won", 1),
    0x14: ("tournament_wins", 1),
    0x15: ("tournaments_lost", 1),
}
CONTROL_BY_NAME = {name: (byte, args) for byte, (name, args) in CONTROLS.items()}
CONTROL_BY_NAME["glyph"] = None
CONTROL_BY_NAME["bytes"] = None

COMPARE_SYMBOL = {0: "==", 1: "!=", 2: ">=", 3: "<=", 4: ">", 5: "<"}
SYMBOL_COMPARE = {symbol: code for code, symbol in COMPARE_SYMBOL.items()}

# Operand labels used by the text form, in the order of the non-padding
# operands in scn_dumper.OPERANDS.
OPERAND_NAMES: dict[int, tuple[str, ...]] = {
    0x1B: ("entity",),
    0x1C: ("trigger",),
    0x1D: ("trigger",),
    0x1E: ("pstat", "value"),
    0x1F: ("pstat", "amount"),
    0x20: ("pstat", "amount"),
    0x21: ("pstat_out",),
    0x22: ("pstat_out",),
    0x23: ("size",),
    0x24: ("pstat_out", "max"),
    0x25: ("pstat_date",),
    0x26: ("origin", "columns", "rows"),
    0x27: ("textbox",),
    0x28: ("item", "amount"),
    0x29: ("item", "amount"),
    0x2A: ("amount",),
    0x2B: ("amount",),
    0x2C: ("pstat_date", "year", "month", "day", "hour", "minute", "flags"),
    0x2D: ("move",),
    0x2E: ("value",),
    0x2F: ("card",),
    0x30: ("card",),
    0x31: ("value",),
    0x32: ("amount",),
    0x33: ("amount",),
    0x34: ("stat", "value"),
    0x35: ("stat", "amount"),
    0x36: ("stat", "amount"),
    0x37: ("pstat_date",),
    0x38: ("pstat_date", "minutes"),
    0x39: ("pstat_date", "minutes"),
    0x3A: ("arg1", "arg2"),
    0x3B: ("arg1", "arg2"),
    0x3C: ("arg1", "arg2"),
    0x3D: ("value",),
    0x3E: ("value",),
    0x3F: ("pstat_digimon", "pstat_out"),
    0x46: ("digimon",),
    0x47: ("digimon", "slot", "autotalk"),
    0x48: ("entity",),
    0x49: ("routine",),
    0x4A: ("entity",),
    0x4B: ("map", "exit", "section"),
    0x4C: ("entity", "target"),
    0x4D: ("entity", "rotation"),
    0x4E: ("entity", "x", "z", "animation", "flags"),
    0x4F: ("speed", "x", "z"),
    0x50: ("entity", "speed"),
    0x51: ("entity", "animation", "target"),
    0x52: ("entity", "x", "z", "animation", "flags"),
    0x53: ("entity", "animation", "target"),
    0x54: ("entity",),
    0x55: ("x", "y", "z"),
    0x56: ("entity", "animation"),
    0x57: ("object", "visible"),
    0x58: ("pstat_map_exit",),
    0x5A: ("bank", "sound"),
    0x5B: ("value",),
    0x5C: ("value",),
    0x5D: ("bgm",),
    0x5E: ("arg",),
    0x5F: ("value",),
    0x64: ("builtin",),
    0x65: ("condition_mask",),
    0x66: ("battle",),
    0x67: ("frames",),
    0x68: ("mode", "frames"),
    0x69: ("damage_percent",),
    0x6A: ("entity", "autotalk"),
    0x6C: ("entity", "x", "z", "speed", "flags"),
    0x6D: ("entity", "target", "speed"),
    0x6E: ("entity", "x", "z", "speed", "flags"),
    0x6F: ("entity", "target", "speed"),
    0x70: ("door", "arg", "target"),
    0x71: ("slot", "entity", "speed", "angle", "x", "z"),
    0x72: ("entity", "target", "axis", "speed"),
    0x73: ("entity", "target", "axis", "speed"),
    0x74: ("item", "x", "z"),
    0x75: ("item", "x", "y", "z", "w", "trigger"),
    0x76: ("boulder",),
    0x77: ("boulder", "x", "z"),
    0x78: ("boulder",),
    0x79: ("digimon",),
    0x7A: ("pstat_from", "pstat_to"),
    0x7B: ("section",),
    0x7C: ("rect", "x", "z", "width", "height"),
    0x7D: ("sprite", "x", "y", "z", "w"),
    0x7E: ("entity", "node", "sprite"),
    0xFB: ("script", "map"),
    0xFC: (),
    0xFD: (),
}


def operand_names(op: int, count: int) -> list[str]:
    names = list(OPERAND_NAMES.get(op, ()))
    seen: set[str] = set()
    result: list[str] = []
    for index in range(count):
        name = names[index] if index < len(names) else f"arg{index + 1}"
        if name in seen:
            name = f"{name}{index + 1}"
        seen.add(name)
        result.append(name)
    return result


# ---------------------------------------------------------------------------
# Names usable in operands
# ---------------------------------------------------------------------------

_ASCII_TO_JIS: dict[int, int] | None = None


def ascii_to_jis() -> dict[int, int]:
    """The game's ASCII -> Shift-JIS glyph map (the font's standard text).

    This mirrors ``convertAsciiToJis()`` in ``decomp/src/main/sjis.c``, except that
    the scene text spells the apostrophe with glyph 0x8175 rather than 0x8166.
    """
    global _ASCII_TO_JIS
    if _ASCII_TO_JIS is not None:
        return _ASCII_TO_JIS

    import re

    source = (D.ROOT / "decomp/src/main/sjis.c").read_text(encoding="utf-8")

    def entries(declaration: str) -> list[tuple[int, int]]:
        start = source.index(declaration)
        opening = source.index("{", start)
        closing = source.index("};", opening)
        return [
            (int(shift, 16), int(ascii_code, 16))
            for shift, ascii_code in re.findall(
                r"\{\s*(0x[0-9a-fA-F]+),\s*(0x[0-9a-fA-F]+)\s*\}",
                source[opening:closing],
            )
        ]

    mapping = {ascii_code: shift for shift, ascii_code in entries("CHAR_MAPPING_SPECIAL")}
    for value in range(0x30, 0x3A):
        mapping[value] = 0x824F + value - 0x30
    for value in range(0x41, 0x5B):
        mapping[value] = 0x8260 + value - 0x41
    for value in range(0x61, 0x7B):
        mapping[value] = 0x8281 + value - 0x61
    mapping[0x27] = 0x8175
    _ASCII_TO_JIS = mapping
    return mapping


_JIS_TO_ASCII: dict[int, int] | None = None


def jis_to_ascii() -> dict[int, int]:
    global _JIS_TO_ASCII
    if _JIS_TO_ASCII is None:
        _JIS_TO_ASCII = {code: ascii_code for ascii_code, code in ascii_to_jis().items()}
    return _JIS_TO_ASCII


_NAME_TABLES: dict[str, dict[int, str]] | None = None
NAME_KINDS = ("digimon", "item", "move")

# Pstats are a 256-byte save-state scratch area; most indices are reused by
# different maps. These have a meaning fixed by the interpreter (pstat.h and
# the CALL_ROUTINE builtins in script_interp.c).
PSTAT_NOTES: dict[int, str] = {
    0x00: "time speed",
    0x01: "prosperity points",
    0x02: "tournament day",
    0x03: "tournament id",
    0x04: "tournament Digimon",
    0x05: "Sukamon backup Digimon",
    0x69: "date year",
    0x6A: "date day",
    0x6B: "date hour",
    0x6C: "date minute",
    0xF3: "shop variable high byte",
    0xF4: "shop variable low byte",
    0xF7: "builtin parameter 1 (entity/script id)",
    0xF8: "builtin parameter 2 (mood/amount)",
    0xF9: "builtin highlighted item",
    0xFA: "predefined battle flag",
    0xFB: "battle enemy 1 script id",
    0xFC: "battle enemy 2 script id",
    0xFD: "battle enemy 3 script id",
    0xFE: "builtin argument (selection/item)",
    0xFF: "last battle/tournament result",
}

PSTAT_SOURCES: dict[int, str] = {
    0xF3: "CALL_ROUTINE builtin=0x38 writes SHOP_VARIABLE / 256",
    0xF4: "CALL_ROUTINE builtin=0x38 writes SHOP_VARIABLE & 0xff; "
          "builtin=0x1f adds (pstat_f3 << 8) + pstat_f4 to SHOP_VARIABLE",
    0xFE: "read by CALL_ROUTINE builtins as the current selection/item",
    0xFF: "written by START_BATTLE and tournament results",
    0x6B: "written by STORE_DATE pstat_date=0x69 (hour)",
}


def name_tables() -> dict[str, dict[int, str]]:
    """Name tables (US) for operands that refer to game data."""
    global _NAME_TABLES
    if _NAME_TABLES is None:
        digimon, _, moves, items = D.game_tables()
        _NAME_TABLES = {"digimon": digimon, "move": moves, "item": items}
    return _NAME_TABLES


def names_for(kind: str) -> dict[int, str]:
    return name_tables()[kind]


def normalize_name(name: str) -> str:
    """A case-insensitive operand spelling for a name with spaces or punctuation."""
    out: list[str] = []
    last = False
    for char in name:
        if char.isalnum():
            out.append(char.lower())
            last = False
        elif not last:
            out.append("_")
            last = True
    return "".join(out).strip("_")


def resolve_named(kind: str, value: str, where: str) -> int:
    """Resolve a numeric id or a US name used as an operand value."""
    names = names_for(kind)
    wanted = normalize_name(value)
    matches = sorted(index for index, name in names.items()
                     if normalize_name(name) == wanted)
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        options = ", ".join(f"{match:#04x}" for match in matches)
        raise TextError(
            f"{where}: {kind} name {value!r} is ambiguous ({options}); "
            f"write the id instead")
    raise TextError(f"{where}: unknown {kind} {value!r}")


def parse_named_or_int(kind: str, text: str, where: str) -> int:
    try:
        return int(text, 0)
    except ValueError:
        return resolve_named(kind, text, where)


_MAP_NAMES: dict[int, str] | None = None


def map_names() -> dict[int, str]:
    """Map screen id -> ``"FILENAME — Display name"`` from the decomp tables."""
    global _MAP_NAMES
    if _MAP_NAMES is None:
        _MAP_NAMES = D.game_tables()[1]
    return _MAP_NAMES


def resolve_map(value: str, where: str) -> int:
    names = map_names()

    def parts(entry: str) -> tuple[str, str]:
        filename, _, display = entry.partition(" — ")
        return filename, display

    wanted = normalize_name(value)
    matches = sorted(
        index for index, entry in names.items()
        if normalize_name(parts(entry)[0]) == wanted
    )
    if not matches:
        matches = sorted(
            index for index, entry in names.items()
            if normalize_name(parts(entry)[1]) == wanted and parts(entry)[1]
        )
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        options = ", ".join(f"{match:#04x}" for match in matches)
        raise TextError(
            f"{where}: map name {value!r} is ambiguous ({options}); "
            f"write the id or the map filename")
    raise TextError(f"{where}: unknown map {value!r}")


def parse_map_or_int(text: str, where: str) -> int:
    try:
        return int(text, 0)
    except ValueError:
        return resolve_map(text, where)


# ---------------------------------------------------------------------------
# Decoding
# ---------------------------------------------------------------------------


class TextError(ValueError):
    """Malformed SCN data or text source."""


@dataclass
class Condition:
    flag: int  # 0, 0x80 (AND), 0x40 (OR)
    kind: str
    args: dict[str, int]


@dataclass
class Instr:
    at: int
    end: int
    op: int
    kind: str
    args: list[tuple[str, int]] = field(default_factory=list)
    targets: list[int] = field(default_factory=list)
    text_start: int = 0
    pstat: int = 0
    count: int = 0
    extra: int = 0
    conditions: list[Condition] = field(default_factory=list)
    payload: bytes = b""
    pad: int = 0
    truncated: bool = False


@dataclass
class Item:
    kind: str  # instr, copy, pad, byte, script, bytes
    start: int
    end: int
    instr: Instr | None = None
    src: int = 0
    value: int = 0
    script: "ScriptObj | None" = None
    payload: bytes = b""
    src_label: str = ""


@dataclass
class ScriptObj:
    name: str
    base: int
    limit: int
    sections: list[tuple[int, int]]  # (id, absolute start)
    starts: list[int]  # distinct absolute starts, ascending
    items: list[Item]
    nested: list["ScriptObj"]
    labels: dict[int, str] = field(default_factory=dict)
    note: str = ""
    map_id: int | None = None
    is_maphead: bool = False
    raw_copy: bool = False


def _u16(data: bytes, at: int) -> int:
    return int.from_bytes(data[at : at + 2], "little")


def _s16(data: bytes, at: int) -> int:
    return int.from_bytes(data[at : at + 2], "little", signed=True)


def decode_one(data: bytes, at: int, limit: int) -> Instr:
    """Decode one instruction using the interpreter's operand layouts."""
    if at < 0 or at >= limit:
        raise TextError(f"instruction outside object at {at:#x}")
    op = data[at]
    if op == 0x1A:
        pad = data[at + 1]
        start = at + 2
        end = D.text_end(data, start, limit)
        truncated = end is None
        if truncated:
            end = limit
        return Instr(at, end, op, "text", text_start=start, pad=pad,
                     truncated=truncated)
    if op == 0x10:
        if at + 2 > limit:
            raise TextError(f"truncated selection at {at:#x}")
        count = data[at + 1]
        table = at + 2 + 2 * (count + 1)
        if table > limit:
            raise TextError(f"truncated selection table at {at:#x}")
        targets = [_u16(data, at + 2 + 2 * i) for i in range(count)]
        extra = _u16(data, at + 2 + 2 * count)
        end = D.text_end(data, table, limit)
        truncated = end is None
        if truncated:
            end = limit
        return Instr(at, end, op, "selection", targets=targets, count=count,
                     extra=extra, text_start=table, truncated=truncated)
    if op == 0x19:
        pad = data[at + 1]
        p = at + 2
        conditions: list[Condition] = []
        while p + 2 <= limit:
            cond = data[p]
            flag = cond & 0xC0
            kind = cond & 0x38
            comparator = cond & 0x07
            p += 2
            if cond == 0x19:
                return Instr(at, p, op, "if", conditions=conditions, pad=pad)
            if kind in (0x10, 0x18):
                if p + 2 > limit:
                    raise TextError(f"truncated branch condition at {at:#x}")
                conditions.append(Condition(flag, "branch", {
                    "jump_if": 1 if kind == 0x10 else 0,
                    "target": _u16(data, p),
                }))
                p += 2
            elif kind == 0x00:
                if p + 2 > limit:
                    raise TextError(f"truncated trigger condition at {at:#x}")
                conditions.append(Condition(flag, "trigger", {
                    "trigger": _u16(data, p), "cmp": comparator}))
                p += 2
            elif kind == 0x08:
                if p + 2 > limit:
                    raise TextError(f"truncated pstat condition at {at:#x}")
                conditions.append(Condition(flag, "pstat", {
                    "pstat": data[p], "cmp": comparator, "value": data[p + 1]}))
                p += 2
            elif kind == 0x20:
                if comparator == 0:
                    if p + 4 > limit:
                        raise TextError(f"truncated stat condition at {at:#x}")
                    stat = data[p]
                    value = _s16(data, p + 2) if stat == 9 else _u16(data, p + 2)
                    conditions.append(Condition(flag, "stat", {
                        "stat": stat, "cmp": data[p + 1], "value": value}))
                    p += 4
                elif comparator == 1:
                    if p + 4 > limit:
                        raise TextError(f"truncated card condition at {at:#x}")
                    conditions.append(Condition(flag, "card", {
                        "card": data[p], "cmp": data[p + 1],
                        "value": _u16(data, p + 2)}))
                    p += 4
                elif comparator == 2:
                    if p + 2 > limit:
                        raise TextError(f"truncated move condition at {at:#x}")
                    conditions.append(Condition(flag, "move", {
                        "move": data[p], "negate": data[p + 1]}))
                    p += 2
                elif comparator == 3:
                    if p + 2 > limit:
                        raise TextError(f"truncated condition at {at:#x}")
                    conditions.append(Condition(flag, "condition", {
                        "mask": data[p], "negate": data[p + 1]}))
                    p += 2
                elif comparator == 4:
                    if p + 4 > limit:
                        raise TextError(f"truncated item condition at {at:#x}")
                    conditions.append(Condition(flag, "item", {
                        "item": data[p], "cmp": data[p + 1],
                        "value": _u16(data, p + 2)}))
                    p += 4
                elif comparator == 5:
                    if p + 6 > limit:
                        raise TextError(f"truncated money condition at {at:#x}")
                    conditions.append(Condition(flag, "money", {
                        "pad": data[p], "cmp": data[p + 1],
                        "value": int.from_bytes(data[p + 2 : p + 6], "little")}))
                    p += 6
                else:
                    raise TextError(f"unknown IF comparator {comparator} at {at:#x}")
            else:
                raise TextError(f"unknown IF condition class {kind:#x} at {at:#x}")
        raise TextError(f"unterminated IF at {at:#x}")
    if op == 0x18:
        if at + 4 > limit:
            raise TextError(f"truncated SWITCH at {at:#x}")
        count = _u16(data, at + 2)
        end = at + 4 + 2 * count
        if end > limit:
            raise TextError(f"SWITCH table overruns object at {at:#x}")
        targets = [_u16(data, at + 4 + 2 * i) for i in range(count)]
        return Instr(at, end, op, "switch", targets=targets, count=count,
                     pstat=data[at + 1])
    if op in (0x13, 0x16):
        if at + 4 > limit:
            raise TextError(f"truncated branch at {at:#x}")
        return Instr(at, at + 4, op, "branch", targets=[_u16(data, at + 2)],
                     pad=data[at + 1])
    if op in (0x14, 0x17):
        if at + 6 > limit:
            raise TextError(f"truncated file branch at {at:#x}")
        return Instr(at, at + 6, op, "file_branch", args=[
            ("map", _u16(data, at + 2)), ("section", _u16(data, at + 4))],
            pad=data[at + 1])
    if op == 0x15:
        if at + 2 > limit:
            raise TextError(f"truncated return at {at:#x}")
        return Instr(at, at + 2, op, "return", pad=data[at + 1])
    if op == 0x6B:
        sentinel = data.find(b"\xff", at + 2, limit)
        if sentinel < 0:
            raise TextError(f"DATA at {at:#x} has no 0xff sentinel")
        return Instr(at, sentinel + 1, op, "data", payload=data[at + 2 : sentinel])
    if op in (0xFE, 0xFF):
        if at + 2 > limit:
            raise TextError(f"truncated END at {at:#x}")
        return Instr(at, at + 2, op, "end", pad=data[at + 1])
    if op in D.OPERANDS:
        length = D.FIXED_LENGTH[op]
        if at + length > limit:
            raise TextError(f"truncated {D.OPCODES.get(op, hex(op))} at {at:#x}")
        args = D.decode_operands(data, at + 1, D.OPERANDS[op])
        pad = data[at + 1] if D.OPERANDS[op] and D.OPERANDS[op][0] == "_" else 0
        return Instr(at, at + length, op, "op", args=args, pad=pad)
    raise TextError(f"unknown opcode {op:#04x} at {at:#x}")


def _step_targets(instr: Instr) -> list[int]:
    """Offsets the interpreter can jump to, relative to the object base."""
    if instr.kind in ("text", "selection"):
        return instr.targets
    if instr.kind == "if":
        return [c.args["target"] for c in instr.conditions if c.kind == "branch"]
    if instr.kind == "switch":
        return instr.targets
    if instr.kind == "branch":
        return instr.targets
    return []


def _falls_through(instr: Instr) -> bool:
    if instr.kind in ("branch", "file_branch", "return", "end", "switch"):
        return False
    if instr.kind == "selection":
        # Cancelling a selection resumes after its text.
        return True
    return True


def cover_object(data: bytes, base: int, limit: int) -> tuple[dict[int, Instr], bytearray]:
    """Decode all reachable instructions and mark the bytes they cover."""
    sections = D.section_table(data, base, limit)
    starts = sorted({start for _, start in sections})
    covered = bytearray(limit - base)
    instrs: dict[int, Instr] = {}
    pending = list(starts)
    while pending:
        at = pending.pop()
        if at in instrs:
            continue
        instr = decode_one(data, at, limit)
        if instr.end <= at or instr.end > limit:
            raise TextError(f"instruction overruns object at {at:#x}")
        for pos in range(at, instr.end):
            covered[pos - base] = 1
        instrs[at] = instr
        if _falls_through(instr) and instr.end < limit:
            pending.append(instr.end)
        for offset in _step_targets(instr):
            target = base + offset
            if base <= target < limit:
                pending.append(target)
    return instrs, covered


def _uncovered_runs(covered: bytearray, base: int) -> list[tuple[int, int]]:
    runs: list[list[int]] = []
    for index, value in enumerate(covered):
        if value:
            continue
        at = base + index
        if runs and at == runs[-1][1]:
            runs[-1][1] = at + 1
        else:
            runs.append([at, at + 1])
    return [(a, b) for a, b in runs]


def _looks_like_script(data: bytes, at: int, limit: int) -> bool:
    if at + 6 > limit:
        return False
    first = _u16(data, at)
    pos = at + 2
    entries: list[tuple[int, int]] = []
    while pos + 4 <= limit:
        section_id = _u16(data, pos)
        offset = _u16(data, pos + 2)
        pos += 4
        if section_id == 0xFFFF:
            break
        if offset < pos - at or at + offset >= limit:
            return False
        entries.append((section_id, offset))
    else:
        return False
    if not entries or entries[0][1] != first:
        return False
    if first != pos - at - 2:
        return False
    if any(b[1] < a[1] for a, b in zip(entries, entries[1:])):
        return False
    return True


def _find_copy(data: bytes, at: int, end: int) -> tuple[int, int] | None:
    """Longest prefix of data[at:end] that occurs earlier in the file."""
    length = end - at
    while length > 0:
        src = data.find(data[at : at + length], 0, at)
        if 0 <= src < at:
            return src, length
        length -= 1
    return None


def _linear_decode(data: bytes, start: int, end: int) -> list[Instr] | None:
    """Decode a gap as a run of instructions that ends exactly at ``end``."""
    instrs: list[Instr] = []
    pos = start
    while pos < end:
        try:
            instr = decode_one(data, pos, end)
        except TextError:
            return None
        if instr.end <= pos:
            return None
        instrs.append(instr)
        pos = instr.end
    return instrs or None


def decode_object(data: bytes, base: int, limit: int, name: str,
                  map_id: int | None = None, is_maphead: bool = False) -> ScriptObj:
    sections = D.section_table(data, base, limit)
    starts = sorted({start for _, start in sections})
    instrs, covered = cover_object(data, base, limit)
    items: list[Item] = []
    nested: list[ScriptObj] = []
    first_start = starts[0]
    # Bytes before the first section are the generated section table.
    for run_start, run_end in _uncovered_runs(covered, base):
        if run_end <= first_start:
            continue
        if run_start < first_start:
            run_start = first_start
        items.extend(_classify_gap(data, run_start, run_end, base, limit, name,
                                   nested))
    labels = {start: f"{name}_s{start - base:x}" for start in starts}
    for at, instr in instrs.items():
        for offset in _step_targets(instr):
            target = base + offset
            if target in instrs and target not in labels:
                labels[target] = f"{name}_b{target - base:x}"
    for start, instr in instrs.items():
        items.append(Item("instr", start, instr.end, instr=instr))
    items.sort(key=lambda item: item.start)
    return ScriptObj(name=name, base=base, limit=limit, sections=sections,
                     starts=starts, items=items, nested=nested, labels=labels,
                     map_id=map_id, is_maphead=is_maphead)


def _classify_gap(data: bytes, at: int, end: int, base: int, limit: int,
                  name: str, nested: list[ScriptObj]) -> list[Item]:
    items: list[Item] = []
    while at < end:
        if not any(data[at:end]):
            items.append(Item("pad", at, end))
            return items
        found = _find_copy(data, at, end)
        if found and found[1] == end - at:
            src, length = found
            if length == 1:
                items.append(Item("byte", at, end, value=data[at]))
            else:
                items.append(Item("copy", at, end, src=src))
            return items
        if _looks_like_script(data, at, end):
            script = decode_object(data, at, end, f"{name}_n{at - base:x}")
            nested.append(script)
            items.append(Item("script", at, end, script=script))
            return items
        if found:
            src, length = found
            if length == 1:
                items.append(Item("byte", at, at + 1, value=data[at]))
            else:
                items.append(Item("copy", at, at + length, src=src))
            at += length
            continue
        instructions = _linear_decode(data, at, end)
        if instructions is not None:
            for instr in instructions:
                items.append(Item("instr", instr.at, instr.end, instr=instr))
            return items
        items.append(Item("bytes", at, end, payload=data[at:end]))
        return items
    return items


# ---------------------------------------------------------------------------
# Emitting text
# ---------------------------------------------------------------------------


def _hex(value: int, width: int = 2) -> str:
    return f"0x{value:0{width}x}"


def _escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace('"', '\\"').replace("{", "\\{")


def _glyph_text(raw: bytes) -> str:
    ascii_code = jis_to_ascii().get(int.from_bytes(raw, "big"))
    if ascii_code is not None:
        return _escape(chr(ascii_code))
    try:
        char = raw.decode("cp932")
    except UnicodeDecodeError:
        return "{glyph:" + raw.hex() + "}"
    try:
        if len(char) == 1 and char.encode("cp932") == raw:
            return _escape(char)
    except UnicodeEncodeError:
        pass
    return "{glyph:" + raw.hex() + "}"


def text_lines(data: bytes, start: int, end: int) -> list[str]:
    """Split a script text stream into rendered source lines."""
    lines: list[list[str]] = [[]]
    pos = start
    while pos < end:
        byte = data[pos]
        if byte == 0x0D and pos + 1 < end and data[pos + 1] == 0:
            if pos + 3 < end and data[pos + 2] == 0 and data[pos + 3] == 0:
                break
            lines.append([])
            pos += 2
            continue
        if byte in CONTROLS:
            name, arg_count = CONTROLS[byte]
            args = data[pos + 1 : pos + 1 + arg_count]
            token = "{" + name
            if args:
                token += ":" + args.hex()
            token += "}"
            lines[-1].append(token)
            pos += 1 + arg_count
            continue
        raw = data[pos : pos + 2]
        lines[-1].append(_glyph_text(raw))
        pos += 2
    return ["".join(parts) for parts in lines]


def _target_name(obj: ScriptObj, target: int) -> str:
    absolute = obj.base + target
    if absolute in obj.labels:
        return obj.labels[absolute]
    if not obj.starts or absolute < obj.starts[0] or absolute >= obj.limit:
        # Only dead (unreachable) instructions can point outside their object.
        return f"{obj.name}+{_hex(target, 4)}"
    index = bisect.bisect_right(obj.starts, absolute) - 1
    if index < 0:
        return f"{obj.name}+{_hex(target, 4)}"
    start = obj.starts[index]
    label = section_label(obj, start)
    offset = absolute - start
    return label if offset == 0 else f"{label}+{_hex(offset)}"


def section_label(obj: ScriptObj, start: int) -> str:
    return f"{obj.name}_s{start - obj.base:x}"


def _operand_value(kind: str, value: int) -> str:
    if kind.startswith("s"):
        return str(value)
    if kind == "u8" or kind == "id" or kind == "pstat":
        return _hex(value, 2)
    if kind == "u16":
        return _hex(value, 4)
    return _hex(value, 8)


def _condition_text(condition: Condition, obj: ScriptObj) -> str:
    args = condition.args
    if condition.kind == "branch":
        which = "true" if args["jump_if"] else "false"
        return f"if {which} goto {_target_name(obj, args['target'])}"
    prefix = {0x00: "THEN", 0x80: "AND", 0x40: "OR"}[condition.flag]
    if condition.kind == "trigger":
        mode = "set" if args["cmp"] == 0 else "clear"
        return f"{prefix} trigger {_hex(args['trigger'], 4)} {mode}"
    if condition.kind == "pstat":
        line = (f"{prefix} pstat {_hex(args['pstat'])} "
                f"{COMPARE_SYMBOL[args['cmp']]} {_hex(args['value'])}")
        note = PSTAT_NOTES.get(args["pstat"])
        return line + (f"  # {note}" if note else "")
    if condition.kind == "stat":
        return (f"{prefix} stat {_hex(args['stat'])} "
                f"{COMPARE_SYMBOL[args['cmp']]} {args['value']}")
    if condition.kind == "card":
        return (f"{prefix} card {_hex(args['card'])} "
                f"{COMPARE_SYMBOL[args['cmp']]} {_hex(args['value'], 4)}")
    if condition.kind == "item":
        line = (f"{prefix} item {_hex(args['item'])} "
                f"{COMPARE_SYMBOL[args['cmp']]} {_hex(args['value'], 4)}")
        label = names_for("item").get(args["item"])
        return line + (f"  # {label}" if label else "")
    if condition.kind == "money":
        return (f"{prefix} money {COMPARE_SYMBOL[args['cmp']]} "
                f"{_hex(args['value'], 8)}")
    if condition.kind == "move":
        suffix = " not" if args["negate"] else ""
        line = f"{prefix} move {_hex(args['move'])}{suffix}"
        label = names_for("move").get(args["move"])
        return line + (f"  # {label}" if label else "")
    if condition.kind == "condition":
        suffix = " not" if args["negate"] else ""
        return f"{prefix} condition {_hex(args['mask'])}{suffix}"
    raise TextError(f"cannot render condition {condition.kind}")


def _instruction_text(instr: Instr, obj: ScriptObj) -> list[str]:
    op = instr.op
    mnemonic = D.OPCODES.get(op, f"OP_{op:02X}")
    if instr.kind == "text":
        lines = [".text"]
        for line in text_lines(instr_data(instr), instr.text_start, instr.end):
            lines.append(f'  "{line}"')
        if instr.truncated:
            lines.append("  .truncated")
        lines.append(".end")
        return lines
    if instr.kind == "selection":
        lines = [".selection"]
        if instr.extra != 0x1A:
            lines.append(f"  .extra {_hex(instr.extra, 4)}")
        # The text has exactly `count` lines, one per option.
        text = text_lines(instr_data(instr), instr.text_start, instr.end)
        if not instr.truncated and len(text) != len(instr.targets):
            raise TextError(
                f"selection at {instr.at:#x} has {len(instr.targets)} targets "
                f"but {len(text)} text lines")
        for index, target in enumerate(instr.targets):
            line = text[index] if index < len(text) else ""
            lines.append(f'  "{line}" -> {_target_name(obj, target)}')
        if instr.truncated:
            lines.append("  .truncated")
        lines.append(".end")
        return lines
    if instr.kind == "if":
        lines = [".if"]
        for condition in instr.conditions:
            lines.append("  " + _condition_text(condition, obj))
        lines.append(".end")
        return lines
    if instr.kind == "switch":
        targets = " ".join(_target_name(obj, target) for target in instr.targets)
        line = f"{mnemonic} pstat={_hex(instr.pstat)}"
        if targets:
            line += " " + targets
        return [line]
    if instr.kind == "branch":
        return [f"{mnemonic} {_target_name(obj, instr.targets[0])}"]
    if instr.kind == "file_branch":
        return [f"{mnemonic} map={_hex(instr.args[0][1], 4)} "
                f"section={_hex(instr.args[1][1], 4)}"]
    if instr.kind == "return":
        return [mnemonic]
    if instr.kind == "data":
        return [".data " + " ".join(f"{byte:02x}" for byte in instr.payload)]
    if instr.kind == "end":
        return [mnemonic]
    names = operand_names(op, len(instr.args))
    parts = [mnemonic]
    note = None
    for name, (kind, value) in zip(names, instr.args):
        parts.append(f"{name}={_operand_value(kind, value)}")
        if name in NAME_KINDS:
            label = names_for(name).get(value)
            if label:
                note = label
        elif name == "map":
            label = map_names().get(value)
            if label:
                note = label
        elif name == "pstat_date":
            note = note or "date (year,day,hour,minute)"
        elif name.startswith("pstat") and name != "pstat_digimon":
            note = note or PSTAT_NOTES.get(value)
    line = " ".join(parts)
    if note is not None:
        line += f"  # {note}"
    return [line]


def instr_data(instr: Instr) -> bytes:
    return instr._data  # type: ignore[attr-defined]


def _copy_source(src: int, ranges: list[tuple[int, int, str]]) -> str:
    index = bisect.bisect_right([start for start, _, _ in ranges], src) - 1
    if index < 0:
        raise TextError(f"copy source {src:#x} has no containing object")
    start, end, label = ranges[index]
    if not (start <= src < end):
        raise TextError(f"copy source {src:#x} is outside every object")
    offset = src - start
    return label if offset == 0 else f"{label}+{_hex(offset, 4)}"


def emit_object(obj: ScriptObj, ranges: list[tuple[int, int, str]], out: list[str],
                indent: str = "") -> None:
    if obj.is_maphead:
        out.append(f"{indent}.object MAPHEAD")
    elif obj.map_id is not None:
        suffix = f"  # {obj.note}" if obj.note else ""
        out.append(f"{indent}.map {obj.map_id}{suffix}")
    else:
        out.append(f"{indent}.script {obj.name}")
    if obj.raw_copy:
        # DG map 0 is a byte range, not a script object.
        for item in obj.items:
            source = item.src_label or _copy_source(item.src, ranges)
            out.append(f"{indent}  .copy {source} "
                       f"{_hex(item.end - item.start, 4)}")
        out.append(f"{indent}.end")
        return
    out.append(f"{indent}  .entries")
    for section_id, start in obj.sections:
        out.append(f"{indent}    {_hex(section_id, 3)} -> "
                   f"{section_label(obj, start)}")
    out.append(f"{indent}  .end")
    # Emit items in file order, inserting a label at every section start and
    # every branch/selection/switch target (so edits can move code freely).
    labels = dict(obj.labels)
    for item in obj.items:
        if item.start in labels:
            out.append(f"{indent}{labels.pop(item.start)}:")
        if item.kind == "instr":
            for line in _instruction_text(item.instr, obj):
                out.append(f"{indent}  {line}")
        elif item.kind == "copy":
            out.append(f"{indent}  .copy {_copy_source(item.src, ranges)} "
                       f"{_hex(item.end - item.start, 4)}")
        elif item.kind == "pad":
            out.append(f"{indent}  .pad {_hex(item.end - item.start, 4)}")
        elif item.kind == "byte":
            out.append(f"{indent}  .byte {_hex(item.value)}")
        elif item.kind == "bytes":
            out.append(f"{indent}  .bytes " +
                       " ".join(f"{byte:02x}" for byte in item.payload))
        elif item.kind == "script":
            emit_object(item.script, ranges, out, indent + "  ")
    out.append(f"{indent}.end")


def _object_ranges(objects: list[ScriptObj], header_size: int) -> list[tuple[int, int, str]]:
    ranges: list[tuple[int, int, str]] = []
    if header_size:
        ranges.append((0, header_size, "DG"))
    for obj in objects:
        ranges.append((obj.base, obj.limit, obj.name))
        _nested_ranges(obj, ranges)
    ranges.sort(key=lambda item: (item[0], item[1]))
    return ranges


def _nested_ranges(obj: ScriptObj, ranges: list[tuple[int, int, str]]) -> None:
    for item in obj.items:
        if item.kind == "script" and item.script is not None:
            ranges.append((item.script.base, item.script.limit, item.script.name))
            _nested_ranges(item.script, ranges)


def _attach_data(obj: ScriptObj, data: bytes) -> None:
    for item in obj.items:
        if item.kind == "instr":
            item.instr._data = data  # type: ignore[attr-defined]
        elif item.kind == "script":
            _attach_data(item.script, data)


def disassemble_maphead(data: bytes) -> str:
    obj = decode_object(data, 0, len(data), "MAPHEAD", is_maphead=True)
    _attach_data(obj, data)
    ranges = _object_ranges([obj], 0)
    out = [HEADER, "# MAPHEAD.SCN: the map-head script.", ""]
    emit_object(obj, ranges, out)
    out.append("")
    return "\n".join(out)


def _maphead_script_screens(data: bytes, base: int, limit: int) -> dict[int, list[int]]:
    """DG script id -> screen ids, from the first SET_SCRIPT of each MAPHEAD section."""
    from bisect import bisect_right

    obj = decode_object(data, base, limit, "MAPHEAD_DATA", is_maphead=True)
    starts = sorted({start for _, start in obj.sections})
    first: dict[int, tuple[int, int]] = {}
    for item in obj.items:
        if item.kind != "instr" or item.instr.op != 0xFB:
            continue
        index = bisect_right(starts, item.start) - 1
        if index < 0 or starts[index] in first:
            continue
        names = operand_names(0xFB, len(item.instr.args))
        values = {name: value for name, (_, value) in zip(names, item.instr.args)}
        if "script" in values and "map" in values:
            first[starts[index]] = (values["script"], values["map"])
    screens: dict[int, list[int]] = {}
    for script, screen in first.values():
        screens.setdefault(script, []).append(screen)
    return screens


def disassemble_dg(data: bytes) -> str:
    offsets = D.parse_dg_offsets(data)
    objects: list[ScriptObj] = []
    # Map 0 is the MAPHEAD.SCN bytes plus the start of MAPHEAD again.
    map0 = ScriptObj(name="m0", base=offsets[0], limit=offsets[1],
                     sections=[], starts=[], items=[], nested=[], map_id=0,
                     raw_copy=True)
    first = offsets[0]
    map0.items = [
        Item("copy", first, first + 0x606E, src_label="MAPHEAD"),
        Item("copy", first + 0x606E, first + 0x6800, src_label="MAPHEAD"),
    ]
    objects.append(map0)
    for map_id in range(1, len(offsets) - 1):
        base, limit = offsets[map_id], offsets[map_id + 1]
        objects.append(decode_object(data, base, limit, f"m{map_id}", map_id=map_id))
    screens = _maphead_script_screens(data, offsets[0], offsets[0] + 0x606E)
    names = map_names()
    for obj in objects:
        if obj.map_id is None or obj.map_id == 0:
            continue
        used = sorted(set(screens.get(obj.map_id, [])))
        if len(used) == 1:
            obj.note = f"screen {used[0]}: {names.get(used[0], '?')}"
        elif used:
            obj.note = (f"{len(used)} screens: "
                        + ", ".join(str(screen) for screen in used))
    for obj in objects:
        _attach_data(obj, data)
    ranges = _object_ranges(objects, DG_HEADER_SIZE)
    out = [HEADER, "# DG.SCN: the map scripts and their offset table.", "",
           ".scn DG", "", ".header", "  .offsets", "  .names"]
    for index in range(36):
        raw = data[DG_NAMES_OFFSET + index * 32 : DG_NAMES_OFFSET + (index + 1) * 32]
        name = raw.split(b"\x00", 1)[0].decode("ascii")
        out.append(f'    "{name}"')
    out.append("  .end")
    out.append("  .bytes " + " ".join(f"{b:02x}" for b in data[0x7FC:0x800]))
    out.append(".end")
    out.append("")
    for obj in objects:
        emit_object(obj, ranges, out)
        out.append("")
    return "\n".join(out)


# ---------------------------------------------------------------------------
# Assembling text
# ---------------------------------------------------------------------------


def _encode_glyph(text: str, where: str) -> bytes:
    if len(text) == 1:
        code = ascii_to_jis().get(ord(text))
        if code is not None:
            return code.to_bytes(2, "big")
    try:
        raw = text.encode("cp932")
    except UnicodeEncodeError:
        raise TextError(f"{where}: no CP932 encoding for {text!r}") from None
    if len(raw) != 2:
        raise TextError(
            f"{where}: {text!r} is not a CP932 glyph (ASCII letters and "
            f"punctuation are mapped by the game's font; use {{glyph:....}} "
            f"for a raw pair)")
    return raw


def _parse_text_line(line: str, where: str) -> bytes:
    out = bytearray()
    pos = 0
    while pos < len(line):
        char = line[pos]
        if char == "\\":
            pos += 1
            if pos >= len(line):
                raise TextError(f"{where}: trailing backslash")
            escaped = line[pos]
            if escaped not in ('"', "\\", "{", "}"):
                raise TextError(f"{where}: unknown escape \\{escaped}")
            out += _encode_glyph(escaped, where)
            pos += 1
            continue
        if char == "{":
            end = line.find("}", pos + 1)
            if end < 0:
                raise TextError(f"{where}: unterminated {{...}} control")
            token = line[pos + 1 : end]
            name, _, args = token.partition(":")
            args = args.strip()
            if name == "glyph":
                raw = bytes.fromhex(args)
                if len(raw) != 2:
                    raise TextError(f"{where}: {{glyph:...}} needs two bytes")
                out += raw
            elif name == "bytes":
                out += bytes.fromhex(args)
            elif name in CONTROL_BY_NAME and CONTROL_BY_NAME[name] is not None:
                byte, count = CONTROL_BY_NAME[name]
                raw = bytes.fromhex(args) if args else b""
                if len(raw) != count:
                    raise TextError(
                        f"{where}: {{{name}}} needs {count} argument byte(s)")
                out.append(byte)
                out += raw
            else:
                raise TextError(f"{where}: unknown control {{{name}}}")
            pos = end + 1
            continue
        out += _encode_glyph(char, where)
        pos += 1
    return bytes(out)


def strip_comment(line: str) -> str:
    """Drop a trailing ``#`` comment, keeping hashes inside quoted text."""
    out: list[str] = []
    quoted = False
    escaped = False
    for char in line:
        if escaped:
            out.append(char)
            escaped = False
        elif char == "\\":
            out.append(char)
            escaped = True
        elif char == '"':
            out.append(char)
            quoted = not quoted
        elif char == "#" and not quoted:
            break
        else:
            out.append(char)
    return "".join(out)


def split_operands(text: str) -> list[str]:
    """Split ``name=value`` tokens, allowing quoted values with spaces."""
    tokens: list[str] = []
    current: list[str] = []
    quoted = False
    escaped = False
    for char in text:
        if escaped:
            current.append(char)
            escaped = False
        elif char == "\\":
            escaped = True
        elif char == '"':
            quoted = not quoted
        elif char.isspace() and not quoted:
            if current:
                tokens.append("".join(current))
                current = []
        else:
            current.append(char)
    if current:
        tokens.append("".join(current))
    return tokens


def _parse_int(text: str, where: str) -> int:
    try:
        return int(text, 0)
    except ValueError:
        raise TextError(f"{where}: invalid number {text!r}") from None


@dataclass
class Node:
    kind: str
    line: int
    data: dict = field(default_factory=dict)
    size: int = 0


@dataclass
class SectionNode:
    label: str
    line: int
    nodes: list[Node] = field(default_factory=list)


@dataclass
class ObjectNode:
    kind: str  # map, maphead, script
    name: str
    map_id: int | None
    line: int
    entries: list[tuple[int, str]] | None = None
    sections: list[SectionNode] = field(default_factory=list)
    raw_copy: bool = False


@dataclass
class HeaderNode:
    names: list[str]
    trailing: bytes


@dataclass
class FileNode:
    kind: str
    header: HeaderNode | None
    objects: list[ObjectNode]


class Parser:
    def __init__(self, source: str, name: str):
        self.name = name
        self.lines = source.splitlines()
        self.index = 0

    def where(self, line: int | None = None) -> str:
        return f"{self.name}:{line if line is not None else self.index + 1}"

    def peek(self) -> tuple[int, str] | None:
        while self.index < len(self.lines):
            line = strip_comment(self.lines[self.index])
            if not line.strip():
                self.index += 1
                continue
            return self.index + 1, line
        return None

    def next(self) -> tuple[int, str]:
        item = self.peek()
        if item is None:
            raise TextError(f"{self.name}: unexpected end of file")
        self.index += 1
        return item

    def parse(self) -> FileNode:
        if not self.lines or self.lines[0].strip() != HEADER:
            raise TextError(f"{self.name}:1: expected {HEADER!r}")
        self.index = 1
        line, text = self.next()
        kind = "MAPHEAD"
        if text.strip().startswith(".scn "):
            kind = text.strip().split()[1]
        else:
            self.index -= 1
        header = None
        objects: list[ObjectNode] = []
        if kind == "DG":
            line, text = self.next()
            if text.strip() != ".header":
                raise TextError(f"{self.where(line)}: expected .header")
            header = self.parse_header()
        while self.peek() is not None:
            line, text = self.next()
            stripped = text.strip()
            if stripped.startswith(".map "):
                map_id = _parse_int(stripped.split()[1], self.where(line))
                objects.append(self.parse_object("map", f"m{map_id}", map_id, line))
            elif stripped == ".object MAPHEAD":
                objects.append(self.parse_object("maphead", "MAPHEAD", None, line))
            elif stripped.startswith(".object "):
                name = stripped.split()[1]
                objects.append(self.parse_object("maphead", name, None, line))
            else:
                raise TextError(f"{self.where(line)}: unexpected top-level {stripped!r}")
        return FileNode(kind, header, objects)

    def parse_header(self) -> HeaderNode:
        line, text = self.next()
        if text.strip() != ".offsets":
            raise TextError(f"{self.where(line)}: expected .offsets")
        line, text = self.next()
        if text.strip() != ".names":
            raise TextError(f"{self.where(line)}: expected .names")
        names: list[str] = []
        while True:
            line, text = self.next()
            stripped = text.strip()
            if stripped == ".end":
                break
            value, rest = self.parse_quoted(stripped, self.where(line))
            if rest:
                raise TextError(f"{self.where(line)}: trailing text after name")
            names.append(value)
        line, text = self.next()
        stripped = text.strip()
        if not stripped.startswith(".bytes "):
            raise TextError(f"{self.where(line)}: expected .bytes for the header tail")
        trailing = bytes.fromhex(stripped[len(".bytes ") :])
        line, text = self.next()
        if text.strip() != ".end":
            raise TextError(f"{self.where(line)}: expected .end after .header")
        return HeaderNode(names, trailing)

    def parse_quoted(self, text: str, where: str) -> tuple[str, str]:
        if not text.startswith('"'):
            raise TextError(f"{where}: expected a quoted string")
        out: list[str] = []
        pos = 1
        while pos < len(text):
            char = text[pos]
            if char == "\\":
                pos += 1
                if pos >= len(text):
                    raise TextError(f"{where}: trailing backslash")
                escaped = text[pos]
                if escaped in ('"', "\\"):
                    out.append(escaped)
                else:
                    out.append("\\" + escaped)
                pos += 1
                continue
            if char == '"':
                return "".join(out), text[pos + 1 :].strip()
            out.append(char)
            pos += 1
        raise TextError(f"{where}: unterminated quoted string")

    def parse_object(self, kind: str, name: str, map_id: int | None,
                     line: int) -> ObjectNode:
        obj = ObjectNode(kind, name, map_id, line)
        # DG map 0 is a raw byte range.
        peeked = self.peek()
        if peeked is None:
            raise TextError(f"{self.where(line)}: unexpected end of file")
        if peeked[1].strip().startswith(".copy"):
            obj.raw_copy = True
            while True:
                line2, text = self.next()
                stripped = text.strip()
                if stripped == ".end":
                    break
                if not stripped.startswith(".copy "):
                    raise TextError(f"{self.where(line2)}: expected .copy or .end")
                parts = stripped.split()
                if len(parts) != 3:
                    raise TextError(f"{self.where(line2)}: expected .copy SOURCE LENGTH")
                obj.sections.append(SectionNode("", line2, [
                    Node("copy", line2, {"source": parts[1],
                                         "length": _parse_int(parts[2], self.where(line2))})]))
            return obj
        line2, text = self.next()
        if text.strip() != ".entries":
            raise TextError(f"{self.where(line2)}: expected .entries")
        obj.entries = []
        while True:
            line2, text = self.next()
            stripped = text.strip()
            if stripped == ".end":
                break
            match = re.fullmatch(r"(0x[0-9a-fA-F]+|\d+)\s*->\s*([A-Za-z_][A-Za-z0-9_]*)", stripped)
            if not match:
                raise TextError(f"{self.where(line2)}: expected ID -> LABEL")
            obj.entries.append((_parse_int(match.group(1), self.where(line2)),
                                match.group(2)))
        while True:
            line2, text = self.next()
            stripped = text.strip()
            if stripped == ".end":
                break
            if not stripped.endswith(":"):
                raise TextError(f"{self.where(line2)}: expected a section label")
            section = SectionNode(stripped[:-1], line2)
            obj.sections.append(section)
            self.parse_section(section)
        return obj

    def parse_section(self, section: SectionNode) -> None:
        while True:
            peeked = self.peek()
            if peeked is None:
                raise TextError(f"{self.name}: unterminated section {section.label}")
            line, text = self.next()
            stripped = text.strip()
            if stripped == ".end" or stripped.endswith(":"):
                self.index -= 1
                return
            if stripped == ".if":
                section.nodes.append(self.parse_if(line))
            elif stripped == ".text":
                section.nodes.append(self.parse_text(line))
            elif stripped == ".selection":
                section.nodes.append(self.parse_selection(line))
            elif stripped.startswith(".script "):
                name = stripped[len(".script ") :].strip()
                section.nodes.append(Node("script", line, {
                    "object": self.parse_object("script", name, None, line)}))
            elif stripped.startswith(".copy "):
                parts = stripped.split()
                if len(parts) != 3:
                    raise TextError(f"{self.where(line)}: expected .copy SOURCE LENGTH")
                section.nodes.append(Node("copy", line, {
                    "source": parts[1],
                    "length": _parse_int(parts[2], self.where(line))}))
            elif stripped.startswith(".pad "):
                section.nodes.append(Node("pad", line, {
                    "length": _parse_int(stripped.split()[1], self.where(line))}))
            elif stripped.startswith(".byte "):
                section.nodes.append(Node("byte", line, {
                    "value": _parse_int(stripped.split()[1], self.where(line))}))
            elif stripped.startswith(".bytes "):
                section.nodes.append(Node("bytes", line, {
                    "payload": bytes.fromhex(stripped[len(".bytes ") :])}))
            elif stripped.startswith(".data "):
                section.nodes.append(Node("data", line, {
                    "payload": bytes.fromhex(stripped[len(".data ") :])}))
            else:
                section.nodes.append(self.parse_instruction(stripped, line))

    def parse_if(self, line: int) -> Node:
        conditions: list[dict] = []
        while True:
            line2, text = self.next()
            stripped = text.strip()
            if stripped == ".end":
                break
            conditions.append(self.parse_condition(stripped, self.where(line2)))
        return Node("if", line, {"conditions": conditions})

    def parse_condition(self, text: str, where: str) -> dict:
        parts = split_operands(text)
        if not parts:
            raise TextError(f"{where}: empty condition")
        if parts[0] in ("THEN", "AND", "OR"):
            flag = {"THEN": 0x00, "AND": 0x80, "OR": 0x40}[parts.pop(0)]
        else:
            flag = 0x00
        if parts[:1] == ["if"]:
            if len(parts) != 4 or parts[2] != "goto":
                raise TextError(f"{where}: expected 'if true|false goto LABEL'")
            return {"flag": flag, "kind": "branch",
                    "jump_if": 1 if parts[1] == "true" else 0,
                    "target": parts[3]}
        if not parts:
            raise TextError(f"{where}: empty condition")
        kind = parts[0]
        if kind == "trigger":
            if len(parts) != 3:
                raise TextError(f"{where}: expected 'trigger N set|clear'")
            mode = parts[2]
            if mode not in ("set", "clear"):
                raise TextError(f"{where}: expected set or clear")
            return {"flag": flag, "kind": "trigger",
                    "trigger": _parse_int(parts[1], where),
                    "cmp": 0 if mode == "set" else 1}
        if kind in ("pstat", "stat", "card", "item"):
            if len(parts) != 4:
                raise TextError(f"{where}: expected '{kind} N CMP VALUE'")
            key = (parse_named_or_int("item", parts[1], where)
                   if kind == "item" else _parse_int(parts[1], where))
            return {"flag": flag, "kind": kind,
                    kind: key,
                    "cmp": SYMBOL_COMPARE.get(parts[2], -1),
                    "value": _parse_int(parts[3], where)}
        if kind == "money":
            if len(parts) != 3:
                raise TextError(f"{where}: expected 'money CMP VALUE'")
            return {"flag": flag, "kind": "money",
                    "cmp": SYMBOL_COMPARE.get(parts[1], -1),
                    "value": _parse_int(parts[2], where)}
        if kind in ("move", "condition"):
            if len(parts) not in (2, 3) or (len(parts) == 3 and parts[2] != "not"):
                raise TextError(f"{where}: expected '{kind} N [not]'")
            key = "move" if kind == "move" else "mask"
            value = (parse_named_or_int("move", parts[1], where)
                     if kind == "move" else _parse_int(parts[1], where))
            return {"flag": flag, "kind": kind,
                    key: value,
                    "negate": 1 if len(parts) == 3 else 0}
        raise TextError(f"{where}: unknown condition {kind!r}")

    def parse_text(self, line: int) -> Node:
        lines: list[str] = []
        truncated = False
        while True:
            line2, text = self.next()
            stripped = text.strip()
            if stripped == ".end":
                break
            if stripped == ".truncated":
                truncated = True
                continue
            value, rest = self.parse_quoted(stripped, self.where(line2))
            if rest:
                raise TextError(f"{self.where(line2)}: trailing text after string")
            lines.append(value)
        return Node("text", line, {"lines": lines, "truncated": truncated})

    def parse_selection(self, line: int) -> Node:
        options: list[tuple[str, str]] = []
        extra = 0x1A
        truncated = False
        while True:
            line2, text = self.next()
            stripped = text.strip()
            if stripped == ".end":
                break
            if stripped == ".truncated":
                truncated = True
                continue
            if stripped.startswith(".extra "):
                extra = _parse_int(stripped.split()[1], self.where(line2))
                continue
            value, rest = self.parse_quoted(stripped, self.where(line2))
            if not rest.startswith("->"):
                raise TextError(f"{self.where(line2)}: expected 'TEXT -> LABEL'")
            label = rest[2:].strip()
            options.append((value, label))
        return Node("selection", line, {"options": options, "extra": extra,
                                        "truncated": truncated})

    def parse_instruction(self, text: str, line: int) -> Node:
        parts = text.split(None, 1)
        mnemonic = parts[0]
        rest = parts[1].strip() if len(parts) > 1 else ""
        op = next((code for code, name in D.OPCODES.items() if name == mnemonic), None)
        if op is None:
            raise TextError(f"{self.where(line)}: unknown mnemonic {mnemonic!r}")
        if op in (0x13, 0x16):
            if not rest:
                raise TextError(f"{self.where(line)}: {mnemonic} needs a target")
            return Node("branch", line, {"op": op, "target": rest})
        if op in (0x14, 0x17):
            match = re.fullmatch(r"map=(\S+)\s+section=(\S+)", rest)
            if not match:
                raise TextError(f"{self.where(line)}: expected map=N section=N")
            return Node("file_branch", line, {
                "op": op,
                "map": parse_map_or_int(match.group(1), self.where(line)),
                "section": _parse_int(match.group(2), self.where(line))})
        if op == 0x15:
            return Node("return", line, {"op": op})
        if op == 0x18:
            match = re.match(r"pstat=(\S+)(?:\s+(.*))?$", rest)
            if not match:
                raise TextError(f"{self.where(line)}: expected pstat=N [TARGET...]")
            targets = match.group(2).split() if match.group(2) else []
            return Node("switch", line, {
                "op": op,
                "pstat": _parse_int(match.group(1), self.where(line)),
                "targets": targets})
        if op in (0xFE, 0xFF):
            return Node("end", line, {"op": op})
        names = operand_names(op, len(D.OPERANDS[op]) - sum(
            1 for kind in D.OPERANDS[op] if kind == "_"))
        spec = list(D.OPERANDS[op])
        values: dict[str, int] = {}
        for token in split_operands(rest):
            if "=" not in token:
                raise TextError(f"{self.where(line)}: expected name=value, got {token!r}")
            key, value = token.split("=", 1)
            where = self.where(line)
            if key in NAME_KINDS:
                values[key] = parse_named_or_int(key, value, where)
            elif key == "map":
                values[key] = parse_map_or_int(value, where)
            else:
                values[key] = _parse_int(value, where)
        missing = [name for name in names if name not in values]
        if missing:
            raise TextError(f"{self.where(line)}: missing operand(s) {', '.join(missing)}")
        unknown = [key for key in values if key not in names]
        if unknown:
            raise TextError(f"{self.where(line)}: unknown operand(s) {', '.join(unknown)}")
        # Pair the non-padding operands with their names in order.
        ordered = []
        name_iter = iter(names)
        for kind in spec:
            ordered.append(0 if kind == "_" else values[next(name_iter)])
        return Node("instr", line, {"op": op, "spec": spec,
                                    "values": ordered})


# ---------------------------------------------------------------------------
# Layout and emission
# ---------------------------------------------------------------------------


def _instr_size(node: Node) -> int:
    op = node.data["op"]
    if op in (0x13, 0x16):
        return 4
    if op in (0x14, 0x17):
        return 6
    if op == 0x15:
        return 2
    if op == 0x18:
        return 4 + 2 * len(node.data["targets"])
    if op in (0xFE, 0xFF):
        return 2
    return D.FIXED_LENGTH[op]


def _node_size(node: Node) -> int:
    if node.kind == "instr":
        return _instr_size(node)
    if node.kind == "script":
        raise TextError(".script must be laid out by layout_object")
    if node.kind == "branch":
        return 4
    if node.kind == "file_branch":
        return 6
    if node.kind == "return":
        return 2
    if node.kind == "switch":
        return 4 + 2 * len(node.data["targets"])
    if node.kind == "end":
        return 2
    if node.kind == "copy":
        return node.data["length"]
    if node.kind == "pad":
        return node.data["length"]
    if node.kind == "byte":
        return 1
    if node.kind == "bytes":
        return len(node.data["payload"])
    if node.kind == "data":
        return 2 + len(node.data["payload"]) + 1
    if node.kind == "text":
        lines = node.data["lines"]
        body = sum(len(_parse_text_line(line, "text")) for line in lines)
        terminator = 0 if node.data.get("truncated") else 4
        return 2 + body + 2 * max(len(lines) - 1, 0) + terminator
    if node.kind == "selection":
        options = node.data["options"]
        body = sum(len(_parse_text_line(text, "selection")) for text, _ in options)
        terminator = 0 if node.data.get("truncated") else 4
        return (1 + 1 + 2 * len(options) + 2 + body
                + 2 * max(len(options) - 1, 0) + terminator)
    if node.kind == "if":
        total = 2
        for condition in node.data["conditions"]:
            kind = condition["kind"]
            if kind in ("trigger", "pstat", "branch", "move", "condition"):
                total += 4
            elif kind in ("stat", "card", "item"):
                total += 6
            elif kind == "money":
                total += 8
            else:
                raise TextError(f"unknown condition {kind}")
        return total + 2
    raise TextError(f"unknown node {node.kind}")


def layout_object(obj: ObjectNode) -> tuple[int, dict[str, int]]:
    """Compute an object's size and the offsets of every label it defines.

    Offsets are relative to the object's base, including labels of nested
    ``.script`` objects.
    """
    if obj.raw_copy:
        size = 0
        for section in obj.sections:
            for node in section.nodes:
                size += _node_size(node)
        return size, {}
    table_size = 2 + 4 * len(obj.entries or ()) + 2
    offset = table_size
    labels: dict[str, int] = {obj.name: 0}
    for section in obj.sections:
        if section.label in labels:
            raise TextError(f"{obj.name}: duplicate label {section.label}")
        labels[section.label] = offset
        for node in section.nodes:
            if node.kind == "script":
                nested = node.data["object"]
                nested_size, nested_labels = layout_object(nested)
                for label, nested_offset in nested_labels.items():
                    if label in labels:
                        raise TextError(f"{obj.name}: duplicate label {label}")
                    labels[label] = offset + nested_offset
                node.size = nested_size
            else:
                node.size = _node_size(node)
            offset += node.size
    return offset, labels


def _parse_target(text: str, labels: dict[str, int], object_base: int,
                  where: str) -> int:
    match = re.fullmatch(r"([A-Za-z_][A-Za-z0-9_]*)(?:\+(\S+))?", text)
    if not match:
        raise TextError(f"{where}: invalid target {text!r}")
    label, offset = match.group(1), match.group(2)
    if label not in labels:
        raise TextError(f"{where}: unknown label {label!r}")
    value = labels[label] - object_base
    if offset:
        value += _parse_int(offset, where)
    return value


class Emitter:
    def __init__(self, labels: dict[str, int], output: bytearray,
                 external: dict[str, bytes]):
        self.labels = labels
        self.output = output
        self.external = external

    def put(self, data: bytes) -> None:
        self.output += data

    def copy_from(self, source: str, length: int, where: str) -> None:
        match = re.fullmatch(r"([A-Za-z_][A-Za-z0-9_]*)(?:\+(\S+))?", source)
        if not match:
            raise TextError(f"{where}: invalid copy source {source!r}")
        label, offset = match.group(1), match.group(2)
        extra = _parse_int(offset, where) if offset else 0
        if label in self.labels:
            start = self.labels[label] + extra
            if start >= len(self.output):
                raise TextError(
                    f"{where}: .copy source {source} is not assembled yet")
            if start + length <= len(self.output):
                self.output += self.output[start : start + length]
            else:
                # Overlapping copy: each byte may come from one written just
                # before it, which is how the original stale tails repeat.
                for index in range(length):
                    self.output.append(self.output[start + index])
        elif label in self.external:
            data = self.external[label]
            start = extra
            if start + length > len(data):
                raise TextError(f"{where}: .copy source {source} is out of range")
            self.output += data[start : start + length]
        else:
            raise TextError(f"{where}: unknown copy source {label!r}")

    def emit_object(self, obj: ObjectNode, base: int, labels: dict[str, int],
                    where: str) -> None:
        if obj.raw_copy:
            for section in obj.sections:
                for node in section.nodes:
                    self.copy_from(node.data["source"], node.data["length"],
                                   f"{where}:{node.line}")
            return
        table_size = 2 + 4 * len(obj.entries or ()) + 2
        self.put(table_size.to_bytes(2, "little"))
        for section_id, label in obj.entries or ():
            if label not in labels:
                raise TextError(f"{where}: unknown section label {label!r}")
            self.put(section_id.to_bytes(2, "little"))
            self.put((labels[label] - base).to_bytes(2, "little"))
        self.put(b"\xff\xff")
        for section in obj.sections:
            for node in section.nodes:
                self.emit_node(node, obj, base, labels, where)

    def emit_node(self, node: Node, obj: ObjectNode, base: int,
                  labels: dict[str, int], where: str) -> None:
        w = f"{where}:{node.line}"
        kind = node.kind
        if kind == "instr":
            op = node.data["op"]
            self.put(bytes((op,)))
            for operand_kind, value in zip(node.data["spec"], node.data["values"]):
                width = D.operand_width(operand_kind)
                signed = operand_kind.startswith("s")
                self.put(value.to_bytes(width, "little", signed=signed))
            return
        if kind == "branch":
            op = node.data["op"]
            target = _parse_target(node.data["target"], labels, base, w)
            self.put(bytes((op, 0)))
            self.put(target.to_bytes(2, "little"))
            return
        if kind == "file_branch":
            self.put(bytes((node.data["op"], 0)))
            self.put(node.data["map"].to_bytes(2, "little"))
            self.put(node.data["section"].to_bytes(2, "little"))
            return
        if kind == "return":
            self.put(bytes((node.data["op"], 0)))
            return
        if kind == "switch":
            targets = [_parse_target(text, labels, base, w)
                       for text in node.data["targets"]]
            self.put(bytes((node.data["op"], node.data["pstat"])))
            self.put(len(targets).to_bytes(2, "little"))
            for target in targets:
                self.put(target.to_bytes(2, "little"))
            return
        if kind == "end":
            self.put(bytes((node.data["op"], 0)))
            return
        if kind == "script":
            nested = node.data["object"]
            self.emit_object(nested, self.labels[nested.name], labels, w)
            return
        if kind == "copy":
            self.copy_from(node.data["source"], node.data["length"], w)
            return
        if kind == "pad":
            self.put(b"\x00" * node.data["length"])
            return
        if kind == "byte":
            self.put(bytes((node.data["value"],)))
            return
        if kind == "bytes":
            self.put(node.data["payload"])
            return
        if kind == "data":
            self.put(b"\x6b\x00")
            self.put(node.data["payload"])
            self.put(b"\xff")
            return
        if kind == "text":
            self.put(b"\x1a\x00")
            lines = node.data["lines"]
            for index, line in enumerate(lines):
                self.put(_parse_text_line(line, w))
                if index + 1 < len(lines):
                    self.put(b"\x0d\x00")
            if not node.data.get("truncated"):
                self.put(b"\x0d\x00\x00\x00")
            return
        if kind == "selection":
            options = node.data["options"]
            self.put(bytes((0x10, len(options))))
            for _, target in options:
                self.put(_parse_target(target, labels, base, w).to_bytes(2, "little"))
            self.put(node.data["extra"].to_bytes(2, "little"))
            for index, (line, _) in enumerate(options):
                self.put(_parse_text_line(line, w))
                if index + 1 < len(options):
                    self.put(b"\x0d\x00")
            if not node.data.get("truncated"):
                self.put(b"\x0d\x00\x00\x00")
            return
        if kind == "if":
            self.put(b"\x19\x00")
            for condition in node.data["conditions"]:
                self.emit_condition(condition, labels, base, w)
            self.put(b"\x19\x00")
            return
        raise TextError(f"{w}: cannot emit {kind}")

    def emit_condition(self, condition: dict, labels: dict[str, int],
                       base: int, where: str) -> None:
        flag = condition["flag"]
        kind = condition["kind"]
        if kind == "branch":
            cond = 0x10 if condition["jump_if"] else 0x18
            self.put(bytes((cond | flag, 0)))
            self.put(_parse_target(condition["target"], labels, base, where)
                     .to_bytes(2, "little"))
            return
        cmp_value = condition.get("cmp", 0)
        if kind == "trigger":
            self.put(bytes((flag | 0x00 | cmp_value, 0)))
            self.put(condition["trigger"].to_bytes(2, "little"))
            return
        if kind == "pstat":
            self.put(bytes((flag | 0x08 | cmp_value, 0)))
            self.put(bytes((condition["pstat"], condition["value"])))
            return
        if kind == "stat":
            self.put(bytes((flag | 0x20, 0)))
            self.put(bytes((condition["stat"], condition["cmp"])))
            self.put(condition["value"].to_bytes(2, "little", signed=condition["stat"] == 9))
            return
        if kind == "card":
            self.put(bytes((flag | 0x20 | 1, 0)))
            self.put(bytes((condition["card"], condition["cmp"])))
            self.put(condition["value"].to_bytes(2, "little"))
            return
        if kind == "move":
            self.put(bytes((flag | 0x20 | 2, 0)))
            self.put(bytes((condition["move"], condition["negate"])))
            return
        if kind == "condition":
            self.put(bytes((flag | 0x20 | 3, 0)))
            self.put(bytes((condition["mask"], condition["negate"])))
            return
        if kind == "item":
            self.put(bytes((flag | 0x20 | 4, 0)))
            self.put(bytes((condition["item"], condition["cmp"])))
            self.put(condition["value"].to_bytes(2, "little"))
            return
        if kind == "money":
            self.put(bytes((flag | 0x20 | 5, 0)))
            self.put(b"\x00")
            self.put(bytes((condition["cmp"],)))
            self.put(condition["value"].to_bytes(4, "little"))
            return
        raise TextError(f"{where}: unknown condition {kind}")


def assemble(source: str, name: str = "source",
             external: dict[str, bytes] | None = None) -> bytes:
    external = external or {}
    tree = Parser(source, name).parse()
    labels: dict[str, int] = {}
    sizes: list[tuple[ObjectNode, int, dict[str, int]]] = []
    if tree.kind == "DG":
        base = DG_HEADER_SIZE
        for obj in tree.objects:
            size, obj_labels = layout_object(obj)
            sizes.append((obj, size, obj_labels))
            if obj.name in labels:
                raise TextError(f"{name}: duplicate object {obj.name}")
            labels[obj.name] = base
            for label, offset in obj_labels.items():
                if label == obj.name:
                    continue
                if label in labels:
                    raise TextError(f"{name}: duplicate label {label}")
                labels[label] = base + offset
            base += size
        eof = base
    else:
        base = 0
        for obj in tree.objects:
            size, obj_labels = layout_object(obj)
            sizes.append((obj, size, obj_labels))
            labels[obj.name] = base
            for label, offset in obj_labels.items():
                if label == obj.name:
                    continue
                labels[label] = base + offset
            base += size
        eof = base
    output = bytearray()
    if tree.kind == "DG":
        if tree.header is None:
            raise TextError(f"{name}: DG source needs a .header")
        if len(tree.objects) != DG_OFFSET_ENTRIES - 1:
            raise TextError(
                f"{name}: DG needs {DG_OFFSET_ENTRIES - 1} map objects, "
                f"found {len(tree.objects)}")
        if len(tree.header.names) != 36:
            raise TextError(f"{name}: DG header needs 36 file names")
        offsets = [labels[obj.name] for obj in tree.objects] + [eof]
        if len(offsets) != DG_OFFSET_ENTRIES:
            raise TextError(f"{name}: invalid offset table")
        for value in offsets:
            output += value.to_bytes(4, "little")
        if len(output) != DG_NAMES_OFFSET:
            raise TextError(f"{name}: offset table does not end at {DG_NAMES_OFFSET:#x}")
        for entry in tree.header.names:
            raw = entry.encode("ascii")
            if len(raw) > 32:
                raise TextError(f"{name}: file name {entry!r} is longer than 32 bytes")
            output += raw + b"\x00" * (32 - len(raw))
        output += tree.header.trailing
        if len(output) != DG_HEADER_SIZE:
            raise TextError(f"{name}: DG header is {len(output):#x} bytes, "
                            f"expected {DG_HEADER_SIZE:#x}")
    emitter = Emitter(labels, output, external)
    if tree.kind == "DG":
        labels["DG"] = 0
    for obj, size, obj_labels in sizes:
        before = len(output)
        emitter.emit_object(obj, labels[obj.name], labels, name)
        actual = len(output) - before
        if actual != size:
            raise TextError(
                f"{name}: {obj.name} assembled to {actual:#x} bytes, "
                f"layout said {size:#x}")
    return bytes(output)


# ---------------------------------------------------------------------------
# Command line
# ---------------------------------------------------------------------------


def pstat_report(source: str, index: int) -> str:
    """List every reference to one pstat, with its meaning when known."""
    lines: list[str] = []
    header = f"pstat {index:#04x}"
    note = PSTAT_NOTES.get(index)
    if note:
        header += f": {note}"
    else:
        header += " (no fixed meaning; scripts use it as scratch state)"
    lines.append(header)
    if index in PSTAT_SOURCES:
        lines.append(f"  {PSTAT_SOURCES[index]}")
    lines.append("")

    context = ""
    section = ""
    hits = 0
    for number, raw in enumerate(source.splitlines(), 1):
        line = strip_comment(raw).strip()
        if not line:
            continue
        if (line.startswith(".map ") or line.startswith(".object ")
                or line.startswith(".script ")):
            context = line
            section = ""
            continue
        if line.endswith(":"):
            section = line
            continue

        mention = None
        for key, value in re.findall(r"\b(pstat\w*)=(\S+)", line):
            try:
                value = int(value, 0)
            except ValueError:
                continue
            if key == "pstat_date":
                if value <= index < value + 4:
                    mention = f"date field {index - value}"
            elif value == index:
                mention = key
        match = re.search(r"\b(?:THEN|AND|OR)\s+pstat\s+(\S+)", line)
        if match:
            try:
                if int(match.group(1), 0) == index:
                    mention = "condition"
            except ValueError:
                pass
        if mention is None:
            continue
        hits += 1
        where = " ".join(part for part in (context, section) if part)
        lines.append(f"{number:6}: [{where}] {line}    <{mention}>")
    if hits == 0:
        lines.append("(no references in this source)")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    dis = sub.add_parser("disassemble", help="SCN -> readable text")
    dis.add_argument("scn", type=Path,
                     help="SCN file, or - to read it from stdin")
    dis.add_argument("--name", help="DG.SCN or MAPHEAD.SCN when reading stdin")
    dis.add_argument("-o", "--output", type=Path)
    asm = sub.add_parser("assemble", help="readable text -> SCN")
    asm.add_argument("source", type=Path)
    asm.add_argument("-o", "--output", type=Path)
    asm.add_argument("--maphead", type=Path,
                     help="MAPHEAD.txt needed to assemble DG.txt")
    pstat = sub.add_parser("pstat", help="explain a pstat and list its uses")
    pstat.add_argument("index", help="pstat index, e.g. 0xf3")
    pstat.add_argument("sources", type=Path, nargs="+")
    args = parser.parse_args(argv)

    if args.command == "pstat":
        try:
            index = int(args.index, 0)
        except ValueError:
            parser.error(f"invalid pstat index {args.index!r}")
        if not 0 <= index <= 0xFF:
            parser.error("a pstat index is 0..0xff")
        blocks = []
        for path in args.sources:
            blocks.append(f"== {path}")
            blocks.append(pstat_report(path.read_text(encoding="utf-8"), index))
        sys.stdout.write("\n".join(blocks))
        return 0

    if args.command == "disassemble":
        if str(args.scn) == "-":
            if not args.name:
                parser.error("--name is required when reading from stdin")
            data = sys.stdin.buffer.read()
            name = args.name.upper()
        else:
            data = args.scn.read_bytes()
            name = args.scn.name.upper()
        if name == "MAPHEAD.SCN":
            text = disassemble_maphead(data)
        elif name == "DG.SCN":
            text = disassemble_dg(data)
        else:
            parser.error("input must be DG.SCN or MAPHEAD.SCN")
        if args.output:
            args.output.write_text(text, encoding="utf-8")
        else:
            sys.stdout.write(text)
        return 0

    source = args.source.read_text(encoding="utf-8")
    external: dict[str, bytes] = {}
    if args.maphead:
        maphead_source = args.maphead.read_text(encoding="utf-8")
        external["MAPHEAD"] = assemble(maphead_source, str(args.maphead))
    data = assemble(source, str(args.source), external)
    if args.output:
        args.output.write_bytes(data)
    else:
        sys.stdout.buffer.write(data)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except TextError as error:
        sys.stderr.write(f"scn_text: {error}\n")
        raise SystemExit(1)

#!/usr/bin/env python3
"""Readable, editable text form of the DW1 ``.MAP`` files (round-trip).

A ``.MAP`` is a small offset table followed by several sections: the map setup
(camera, lights, tile grid), the 8/4-bpp texture images, the animated map
objects, the entity section (player warps and placed Digimon) and a 100x100
collision grid.  Only the entity section -- the warps and the NPC placements --
is meant to be edited; the other sections are binary (TIM images, a collision
grid) and are taken from the original ``.MAP`` when reassembling.

``disassemble`` turns a ``.MAP`` into this text, and ``assemble`` reads the
binary sections back from the original ``.MAP`` (on the disc image, or an
extracted copy) and splices in the edited entities.  The offset table is
adjusted, so NPCs can be added or removed.  No companion file is written.

Layout of a file::

    # DW1-MAP-TEXT 1
    # MAYO01.MAP — Native Forest (id=0, flags=0x80, num8bpp=3 num4bpp=0 doors=0 toilet=1)
    # The setup, image, object and collision sections come from the original .MAP.
    .map MAYO01
      .base disc "/MAP/MAP1/MAYO01.MAP"
      .entities
        .warps
          warp 0 spawn=(-1980,0,610) rot=0x0000 target=MAYO01 exit=1
        .end
        .digimon count=8
          npc 0
            type=49       # Agumon
            follow=1
            pos=(2214,0,865)
            rot=(0,512,0)
            track=10
            unk2=0
            script=5
            stats=(2000,2000,2000,2000,300,200,100,100)  # hp,mp,curHP,curMP,off,def,spd,brn
            bits=0x96
            charge=1
            unk1=1
            moves=(49,50,51,255)
            prio=(50,30,20,0)
            flee=(-2264,0,1100)
            ai=(0,-1,-1,-1,-1,-1,-1,-1)
            wp=(10,0,0)
        .end
      .end
    .end

``.base disc "ISO_PATH"`` reads the original from the disc image (``--disc`` or
``DW1_DISC``); ``.base file "PATH"`` reads an extracted ``.MAP``.  ``type=``,
``moves=`` and warp ``target=`` accept an id or a US name; the disassembler
appends the name as a comment.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

import scn_dumper as D
import scn_text as S

HEADER = "# DW1-MAP-TEXT 1"
WARP_COUNT = 10
MAP_WARPS_BYTES = WARP_COUNT * 6 * 2
COLLISION_BYTES = 0x2710  # loadMapCollisionData copies this many bytes
SECTOR_BYTES = 2352
SECTOR_DATA_OFFSET = 24  # sync + header + subheader in a MODE2/2352 sector

TextError = S.TextError

_ENTRIES: list[dict] | None = None
_AMBIGUOUS: set[str] | None = None


def _entries() -> list[dict]:
    global _ENTRIES
    if _ENTRIES is None:
        _ENTRIES = D.map_entries()[1]
    return _ENTRIES


def _ambiguous_filenames() -> set[str]:
    """Map filenames that appear under more than one ``MapEntry`` id."""
    global _AMBIGUOUS
    if _AMBIGUOUS is None:
        counts: dict[str, int] = {}
        for meta in _entries():
            if meta is None:
                continue
            counts[meta["filename"]] = counts.get(meta["filename"], 0) + 1
        _AMBIGUOUS = {name for name, count in counts.items() if count > 1}
    return _AMBIGUOUS


def _s16(data: bytes, at: int) -> int:
    return int.from_bytes(data[at : at + 2], "little", signed=True)


def _s32(data: bytes, at: int) -> int:
    return int.from_bytes(data[at : at + 4], "little", signed=True)


def _offset_table(data: bytes, name: str) -> tuple[list[int], int]:
    """Return ``(offsets, collision_index)`` of a ``.MAP``.

    The collision grid always ends the file, so its offset is the table entry
    equal to ``len(data) - COLLISION_BYTES``.
    """
    target = len(data) - COLLISION_BYTES
    for index in range(min(len(data) // 4, 32)):
        if _s32(data, index * 4) == target:
            offsets = [_s32(data, i * 4) for i in range(index + 1)]
            return offsets, index
    raise TextError(f"{name}: no collision offset found (expected {target:#x})")


# ---------------------------------------------------------------------------
# Reading the original .MAP from the disc image
# ---------------------------------------------------------------------------

def _disc_binary(disc: Path) -> Path:
    """The .bin of a .cue sheet, or the path itself when it is already a .bin."""
    if disc.suffix.lower() == ".cue":
        text = disc.read_text(errors="replace")
        match = re.search(r'FILE\s+"([^"]+)"\s+BINARY', text)
        if not match:
            raise TextError(f"{disc}: no FILE entry in the cue sheet")
        return disc.parent / match.group(1)
    return disc


def _read_sector(handle, lba: int) -> bytes:
    handle.seek(lba * SECTOR_BYTES + SECTOR_DATA_OFFSET)
    return handle.read(2048)


def _parse_record(record: bytes) -> tuple[int, int, bool, str] | None:
    if record[0] == 0:
        return None
    lba = int.from_bytes(record[2:6], "little")
    size = int.from_bytes(record[10:14], "little")
    is_dir = bool(record[25] & 0x02)
    namelen = record[32]
    raw = record[33 : 33 + namelen]
    if namelen == 1 and raw[0] in (0, 1):
        name = ""
    else:
        name = raw.split(b";")[0].decode("latin1")
    return lba, size, is_dir, name


def _read_extent(handle, lba: int, size: int) -> bytes:
    data = bytearray()
    remaining = size
    while remaining > 0:
        chunk = min(remaining, 2048)
        data += _read_sector(handle, lba)[:chunk]
        remaining -= chunk
        lba += 1
    return bytes(data)


def read_disc_file(disc_path: Path, iso_path: str) -> bytes:
    """Read one file from the disc image by its ISO path (e.g. ``/MAP/...``).

    Only the sectors of the directory chain and the target file are read, so the
    whole image is never loaded into memory.
    """
    binary = _disc_binary(disc_path)
    with binary.open("rb") as handle:
        pvd = _read_sector(handle, 16)
        current = _parse_record(pvd[156:190])
        if current is None:
            raise TextError(f"{disc_path}: no root directory record")
        for part in (p for p in iso_path.replace("\\", "/").split("/") if p):
            if not current[2]:
                raise TextError(f"{iso_path}: not a directory in {disc_path}")
            directory = _read_extent(handle, current[0], current[1])
            found = None
            offset = 0
            while offset < len(directory):
                record = _parse_record(directory[offset:])
                if record is None:
                    break
                offset += directory[offset]
                if record[3] and record[3].upper() == part.upper():
                    found = record
                    break
            if found is None:
                raise TextError(f"{iso_path}: {part!r} not found in {disc_path}")
            current = found
        if current[2]:
            raise TextError(f"{iso_path}: is a directory")
        return _read_extent(handle, current[0], current[1])


def _resolve_disc(explicit: str | None) -> Path:
    if explicit:
        return Path(explicit)
    env = os.environ.get("DW1_DISC")
    if env:
        return Path(env)
    for candidate in ("disc/Digimon World (USA).cue",
                      "disc/Digimon World (USA).bin"):
        if Path(candidate).is_file():
            return Path(candidate)
    raise TextError("no disc image; pass --disc or set DW1_DISC")


def _resolve_base_file(ref: str, text_name: str) -> Path:
    path = Path(ref)
    if path.is_absolute() and path.is_file():
        return path
    parent = Path(text_name).parent
    if str(parent) != ".":
        candidate = parent / path
        if candidate.is_file():
            return candidate
    if path.is_file():
        return path
    raise TextError(f"{text_name}: cannot find base .MAP {ref!r}")


# ---------------------------------------------------------------------------
# Decoding
# ---------------------------------------------------------------------------

def _decode_warps(data: bytes, at: int) -> tuple[list[dict], int]:
    warps: list[dict] = []
    for _ in range(WARP_COUNT):
        warps.append(
            {
                "spawn": (_s16(data, at), _s16(data, at + 2), _s16(data, at + 4)),
                "rot": _s16(data, at + 6),
                "target": _s16(data, at + 8),
                "exit": _s16(data, at + 10),
            }
        )
        at += 12
    return warps, at


def _decode_npc(data: bytes, at: int) -> tuple[dict, int]:
    if at + 84 > len(data):
        raise TextError("truncated npc record")
    npc: dict = {}
    npc["type"] = _s16(data, at)
    npc["follow"] = _s16(data, at + 2)
    npc["pos"] = (_s16(data, at + 4), _s16(data, at + 6), _s16(data, at + 8))
    npc["rot"] = (_s16(data, at + 10), _s16(data, at + 12), _s16(data, at + 14))
    npc["track"] = _s16(data, at + 16)
    npc["unk2"] = _s16(data, at + 18)
    npc["script"] = _s16(data, at + 20)
    npc["stats"] = tuple(_s16(data, at + 22 + 2 * i) for i in range(8))
    at += 38
    npc["bits"] = _s16(data, at)
    npc["charge"] = _s16(data, at + 2)
    npc["unk1"] = _s16(data, at + 4)
    npc["moves"] = tuple(_s16(data, at + 6 + 2 * i) for i in range(4))
    npc["prio"] = tuple(_s16(data, at + 14 + 2 * i) for i in range(4))
    npc["flee"] = (_s16(data, at + 22), _s16(data, at + 24), _s16(data, at + 26))
    npc["waypoints"] = _s16(data, at + 28)
    npc["ai"] = tuple(_s16(data, at + 30 + 2 * i) for i in range(8))
    at += 46
    wpts: list[tuple[int, int, int]] = []
    for _ in range(npc["waypoints"]):
        if at + 6 > len(data):
            raise TextError("truncated waypoint")
        wpts.append((_s16(data, at), _s16(data, at + 2), _s16(data, at + 4)))
        at += 6
    npc["wpts"] = wpts
    return npc, at


def decode_entities(data: bytes) -> tuple[list[dict], int, list[dict], bytes | None]:
    """Return ``(warps, count, npcs, tail)`` from an entity section.

    ``npcs`` holds the decoded digimon records when they fill the section
    exactly; otherwise ``npcs`` is empty and ``tail`` holds the unparsed bytes
    that follow the count (some maps without the ``0x80`` flag carry no records,
    just an opaque tail).
    """
    warps, at = _decode_warps(data, 0)
    count = _s16(data, at)
    at += 2
    rest = data[at:]
    npcs: list[dict] = []
    if 0 <= count:
        try:
            pos = 0
            for _ in range(count):
                npc, pos = _decode_npc(rest, pos)
                npcs.append(npc)
            if pos == len(rest):
                return warps, count, npcs, None
        except TextError:
            npcs = []
    return warps, count, [], rest


def disassemble(data: bytes, name: str, base_disc: str | None = None,
                base_file: str | None = None) -> str:
    """Return the readable text for a ``.MAP``.

    The setup, texture, object and collision bytes are not written out; the text
    references the original ``.MAP`` through ``.base``: either ``.base disc
    "ISO_PATH"`` (read from the disc image when reassembling) or ``.base file
    "PATH"`` (an extracted ``.MAP``). ``base_disc`` / ``base_file`` choose which;
    by default a file base named after ``name`` is used.
    """
    stem = Path(name).stem.upper()
    offsets, _ = _offset_table(data, name)
    entity = offsets[-2]
    collision = offsets[-1]
    n_entries = len(offsets)

    # Sections in file order: setup, images, objects (if images), entities,
    # collision.  With no images the table is [setup, entities, collision].
    n_images = n_entries - 4
    if n_images < 0:
        n_images = 0

    # Look up the map entry, disambiguating a shared filename by image count.
    map_id = None
    meta = None
    candidates = [i for i, e in enumerate(_entries())
                  if e is not None and e["filename"].upper() == stem]
    if candidates:
        map_id = candidates[0]
        for candidate in candidates:
            if (_entries()[candidate]["num8bpp"]
                    + _entries()[candidate]["num4bpp"] == n_images):
                map_id = candidate
                break
        meta = _entries()[map_id]

    warps, count, npcs, tail = decode_entities(data[entity:collision])

    lines = [HEADER]
    if meta and meta["display"]:
        title = f"{meta['filename']}.MAP — {meta['display']}"
    else:
        title = f"{stem}.MAP"
    detail = (
        f"(id={map_id}, flags=0x{meta['flags']:02x}, "
        f"num8bpp={meta['num8bpp']} num4bpp={meta['num4bpp']} "
        f"doors={meta['doorsId']} toilet={meta['toiletId']})"
        if meta
        else "(unknown map id)"
    )
    lines.append(f"# {title} {detail}")
    lines.append("# The setup, image, object and collision sections come from the original .MAP.")
    lines.append(f".map {stem}")
    if base_disc is not None:
        lines.append(f'  .base disc "{base_disc}"')
    else:
        lines.append(f'  .base file "{base_file if base_file is not None else name}"')
    lines.append("  .entities")
    lines.append("    .warps")
    for index, warp in enumerate(warps):
        lines.append("      " + _format_warp(index, warp))
    lines.append("    .end")
    lines.append(f"    .digimon count={count}")
    if tail is not None:
        lines.append("      .tail")
        lines.append("        .bytes " + tail.hex())
        lines.append("      .end")
    else:
        for index, npc in enumerate(npcs):
            lines.append(f"      npc {index}")
            for field in _format_npc(npc):
                lines.append(f"        {field}")
    lines.append("    .end")
    lines.append("  .end")
    lines.append(".end")
    return "\n".join(lines) + "\n"


def _format_warp(index: int, warp: dict) -> str:
    target = warp["target"]
    target_text = str(target)
    comment = ""
    if 0 <= target < len(_entries()) and _entries()[target] is not None:
        meta = _entries()[target]
        filename = meta["filename"]
        if filename not in _ambiguous_filenames():
            target_text = filename
        if meta["display"]:
            comment = f"  # -> {filename} — {meta['display']}"
    x, y, z = warp["spawn"]
    rot = warp["rot"] & 0xFFFF
    return (
        f"warp {index} spawn=({x},{y},{z}) rot=0x{rot:04x} "
        f"target={target_text} exit={warp['exit']}{comment}"
    )


def _format_npc(npc: dict) -> list[str]:
    lines = []
    type_line = f"type={npc['type']}"
    digimon = S.names_for("digimon").get(npc["type"])
    if digimon:
        type_line += f"   # {digimon}"
    lines.append(type_line)
    lines.append(f"follow={npc['follow']}")
    lines.append(f"pos=({','.join(str(v) for v in npc['pos'])})")
    lines.append(f"rot=({','.join(str(v) for v in npc['rot'])})")
    lines.append(f"track={npc['track']}")
    lines.append(f"unk2={npc['unk2']}")
    lines.append(f"script={npc['script']}")
    lines.append(
        f"stats=({','.join(str(v) for v in npc['stats'])})"
        "  # hp,mp,curHP,curMP,off,def,spd,brn"
    )
    lines.append(f"bits=0x{npc['bits'] & 0xffff:x}")
    lines.append(f"charge={npc['charge']}")
    lines.append(f"unk1={npc['unk1']}")
    moves = ",".join(str(v) for v in npc["moves"])
    move_names = S.names_for("move")
    move_comment = ", ".join(move_names[v] for v in npc["moves"] if v in move_names)
    lines.append(f"moves=({moves})" + (f"   # {move_comment}" if move_comment else ""))
    lines.append(f"prio=({','.join(str(v) for v in npc['prio'])})")
    lines.append(f"flee=({','.join(str(v) for v in npc['flee'])})")
    lines.append(f"ai=({','.join(str(v) for v in npc['ai'])})")
    for wpt in npc["wpts"]:
        lines.append(f"wp=({','.join(str(v) for v in wpt)})")
    return lines


# ---------------------------------------------------------------------------
# Encoding
# ---------------------------------------------------------------------------

def _i16(out: bytearray, value: int, where: str) -> None:
    if not -32768 <= value <= 65535:
        raise TextError(f"{where}: value {value} does not fit in 16 bits")
    out += (value & 0xFFFF).to_bytes(2, "little")


def _encode_npc(npc: dict, where: str) -> bytes:
    out = bytearray()
    for value in (npc["type"], npc["follow"]):
        _i16(out, value, where)
    for value in npc["pos"] + npc["rot"]:
        _i16(out, value, where)
    for value in (npc["track"], npc["unk2"], npc["script"]):
        _i16(out, value, where)
    for value in npc["stats"]:
        _i16(out, value, where)
    for value in (npc["bits"], npc["charge"], npc["unk1"]):
        _i16(out, value, where)
    for value in npc["moves"] + npc["prio"]:
        _i16(out, value, where)
    for value in npc["flee"]:
        _i16(out, value, where)
    _i16(out, len(npc["wpts"]), where)
    for value in npc["ai"]:
        _i16(out, value, where)
    for wpt in npc["wpts"]:
        for value in wpt:
            _i16(out, value, where)
    return bytes(out)


def _encode_entities(warps: list[dict], count: int, npcs: list[dict],
                     tail: bytes | None, where: str) -> bytes:
    out = bytearray()
    if len(warps) != WARP_COUNT:
        raise TextError(f"{where}: expected {WARP_COUNT} warps, got {len(warps)}")
    for warp in warps:
        for value in warp["spawn"]:
            _i16(out, value, where)
        for value in (warp["rot"], warp["target"], warp["exit"]):
            _i16(out, value, where)
    _i16(out, count, where)
    if tail is not None:
        out += tail
    else:
        if len(npcs) != count:
            raise TextError(
                f"{where}: digimon count={count} but {len(npcs)} npc records"
            )
        for index, npc in enumerate(npcs):
            out += _encode_npc(npc, f"{where}: npc {index}")
    return bytes(out)


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------

def _parse_int(text: str, where: str) -> int:
    try:
        return int(text, 0)
    except ValueError:
        raise TextError(f"{where}: invalid number {text!r}") from None


def _parse_tuple(text: str, count: int, where: str) -> list[int]:
    match = re.fullmatch(r"\(\s*(.*?)\s*\)", text)
    if not match:
        raise TextError(f"{where}: expected (a,b,c)")
    parts = [part.strip() for part in match.group(1).split(",")]
    if len(parts) != count:
        raise TextError(f"{where}: expected {count} values, got {len(parts)}")
    return [_parse_int(part, where) for part in parts]


def _resolve(kind: str, value: str, where: str) -> int:
    if kind == "map":
        return S.parse_map_or_int(value, where)
    return S.parse_named_or_int(kind, value, where)


class Parser:
    def __init__(self, source: str, name: str):
        self.name = name
        self.lines = source.splitlines()
        self.tokens: list[tuple[int, str]] = []
        for number, raw in enumerate(self.lines, 1):
            line = S.strip_comment(raw).strip()
            if line:
                self.tokens.append((number, line))
        self.pos = 0
        self.base_kind: str | None = None
        self.base_ref: str | None = None
        self.entities: dict | None = None

    def where(self, line: int | None = None) -> str:
        return f"{self.name}:{line if line is not None else self.tokens[self.pos][0]}"

    def next(self) -> tuple[int, str]:
        if self.pos >= len(self.tokens):
            raise TextError(f"{self.name}: unexpected end of file")
        item = self.tokens[self.pos]
        self.pos += 1
        return item

    def peek(self) -> tuple[int, str] | None:
        if self.pos >= len(self.tokens):
            return None
        return self.tokens[self.pos]

    def parse(self) -> None:
        if not self.lines or self.lines[0].strip() != HEADER:
            raise TextError(f"{self.name}:1: expected {HEADER!r}")
        line, text = self.next()
        if not re.fullmatch(r"\.map\s+\S+", text):
            raise TextError(f"{self.where(line)}: expected .map NAME")
        line, text = self.next()
        match = re.fullmatch(r'\.base\s+(disc|file)\s+"([^"]+)"', text)
        if not match:
            raise TextError(
                f"{self.where(line)}: expected .base disc/file \"PATH\""
            )
        self.base_kind = match.group(1)
        self.base_ref = match.group(2)
        line, text = self.next()
        if text != ".entities":
            raise TextError(f"{self.where(line)}: expected .entities")
        self.entities = self.parse_entities()
        line, text = self.next()
        if text != ".end":
            raise TextError(f"{self.where(line)}: expected .end after .entities")
        if self.peek() is not None:
            raise TextError(f"{self.where()}: trailing content after .map")

    def parse_entities(self) -> dict:
        line, text = self.next()
        if text != ".warps":
            raise TextError(f"{self.where(line)}: expected .warps")
        warps: list[dict] = []
        while True:
            line2, text2 = self.next()
            if text2 == ".end":
                break
            warps.append(self.parse_warp(text2, self.where(line2)))
        line3, text3 = self.next()
        match = re.fullmatch(r"\.digimon\s+count=(\S+)", text3)
        if not match:
            raise TextError(f"{self.where(line3)}: expected .digimon count=N")
        count = _parse_int(match.group(1), self.where(line3))
        npcs: list[dict] = []
        tail: bytes | None = None
        item = self.peek()
        if item is None:
            raise TextError(f"{self.name}: unterminated .digimon")
        if item[1] == ".tail":
            self.next()
            tail = self.parse_tail()
            line4, text4 = self.next()
            if text4 != ".end":
                raise TextError(f"{self.where(line4)}: expected .end after .tail")
        else:
            while True:
                item = self.peek()
                if item is None:
                    raise TextError(f"{self.name}: unterminated .digimon")
                line4, text4 = item
                if text4 == ".end":
                    self.next()
                    break
                if not text4.startswith("npc "):
                    raise TextError(f"{self.where(line4)}: expected npc N or .end")
                self.next()
                npcs.append(self.parse_npc(self.where(line4)))
        line5, text5 = self.next()
        if text5 != ".end":
            raise TextError(f"{self.where(line5)}: expected .end after .digimon")
        return {"kind": "entities", "warps": warps, "count": count,
                "npcs": npcs, "tail": tail}

    def parse_tail(self) -> bytes:
        """Parse a ``.tail`` block whose opening line has been consumed."""
        chunks: list[bytes] = []
        while True:
            line, text = self.next()
            if text == ".end":
                break
            if not text.startswith(".bytes "):
                raise TextError(f"{self.where(line)}: expected .bytes or .end")
            try:
                chunks.append(bytes.fromhex(text[len(".bytes "):]))
            except ValueError:
                raise TextError(f"{self.where(line)}: bad hex in .bytes")
        return b"".join(chunks)

    def parse_warp(self, text: str, where: str) -> dict:
        match = re.fullmatch(
            r"warp\s+(\d+)\s+spawn=\(([^)]*)\)\s+rot=(\S+)\s+target=(\S+)\s+exit=(\S+)",
            text,
        )
        if not match:
            raise TextError(f"{where}: bad warp line {text!r}")
        spawn = [_parse_int(part, where) for part in match.group(2).split(",")]
        if len(spawn) != 3:
            raise TextError(f"{where}: warp spawn needs 3 values")
        return {
            "spawn": tuple(spawn),
            "rot": _parse_int(match.group(3), where),
            "target": _resolve("map", match.group(4), where),
            "exit": _parse_int(match.group(5), where),
        }

    def parse_npc(self, where: str) -> dict:
        npc: dict = {}
        fields: dict[str, list[int]] = {}
        while True:
            item = self.peek()
            if item is None:
                raise TextError(f"{where}: unterminated npc block")
            line, text = item
            if text == ".end" or text.startswith("npc "):
                break
            self.next()
            key, _, value = text.partition("=")
            key = key.strip()
            if not key or not value:
                raise TextError(f"{self.where(line)}: expected key=value")
            if key in ("pos", "rot", "flee", "wp"):
                fields.setdefault(key, []).extend(
                    _parse_tuple(value, 3, self.where(line))
                )
            elif key == "stats":
                fields["stats"] = _parse_tuple(value, 8, self.where(line))
            elif key == "moves":
                match = re.fullmatch(r"\(\s*(.*?)\s*\)", value)
                if not match:
                    raise TextError(f"{self.where(line)}: expected (a,b,c,d)")
                parts = [part.strip() for part in match.group(1).split(",")]
                if len(parts) != 4:
                    raise TextError(
                        f"{self.where(line)}: moves needs 4 values, got {len(parts)}"
                    )
                fields["moves"] = [
                    _resolve("move", part, self.where(line)) for part in parts
                ]
            elif key == "prio":
                fields[key] = _parse_tuple(value, 4, self.where(line))
            elif key == "ai":
                fields["ai"] = _parse_tuple(value, 8, self.where(line))
            elif key == "type":
                npc["type"] = _resolve("digimon", value, self.where(line))
            else:
                npc[key] = _parse_int(value, self.where(line))

        required = ("type", "follow", "pos", "rot", "track", "unk2", "script",
                    "stats", "bits", "charge", "unk1", "moves", "prio", "flee", "ai")
        missing = [key for key in required if key not in npc and key not in fields]
        if missing:
            raise TextError(f"{where}: missing npc fields {', '.join(missing)}")
        wpts = fields.get("wp", [])
        if len(wpts) % 3:
            raise TextError(f"{where}: wp lines must each have 3 values")
        npc["wpts"] = [tuple(wpts[i : i + 3]) for i in range(0, len(wpts), 3)]
        npc["pos"] = tuple(fields["pos"])
        npc["rot"] = tuple(fields["rot"])
        npc["flee"] = tuple(fields["flee"])
        npc["stats"] = tuple(fields["stats"])
        npc["moves"] = tuple(fields["moves"])
        npc["prio"] = tuple(fields["prio"])
        npc["ai"] = tuple(fields["ai"])
        return npc


def _read_base(parser: Parser, name: str, base_bytes: bytes | None,
               disc_path: str | None) -> bytes:
    """The original ``.MAP`` the text references."""
    if base_bytes is not None:
        return base_bytes
    if parser.base_kind == "file":
        return _resolve_base_file(parser.base_ref or "", name).read_bytes()
    return read_disc_file(_resolve_disc(disc_path), parser.base_ref or "")


def _assemble_parsed(parser: Parser, name: str, base: bytes) -> bytes:
    assert parser.entities is not None
    offsets, collision_index = _offset_table(base, parser.base_ref or name)
    entity = offsets[-2]
    collision = offsets[-1]
    entities = _encode_entities(
        parser.entities["warps"], parser.entities["count"],
        parser.entities["npcs"], parser.entities["tail"], name
    )

    # Keep everything before the entity section and the collision grid from the
    # base, splice in the new entities, and move the collision entry with it.
    output = bytearray(base[:entity])
    output += entities
    output += base[collision:]
    new_collision = entity + len(entities)
    output[collision_index * 4 : collision_index * 4 + 4] = new_collision.to_bytes(
        4, "little"
    )
    return bytes(output)


def assemble(source: str, name: str = "source",
             base_bytes: bytes | None = None,
             disc_path: str | None = None) -> bytes:
    """Assemble the text back into a ``.MAP``.

    The binary sections come from the original ``.MAP`` named by ``.base``:
    ``base_bytes`` supplies it in memory (used by tests), ``disc_path`` (or
    ``DW1_DISC``) locates the disc image for a ``.base disc`` reference, and a
    ``.base file`` reference is read from disk.
    """
    parser = Parser(source, name)
    parser.parse()
    base = _read_base(parser, name, base_bytes, disc_path)
    return _assemble_parsed(parser, name, base)


def batch_reassemble(source_dir: Path, out_dir: Path,
                     disc_path: str | None = None,
                     mods_dir: Path | None = None) -> list[str]:
    """Reassemble every ``*.map.txt`` and write the ones that differ from the disc.

    Returns the map stems written into ``out_dir`` as ``<stem>.MAP``.  Unedited
    sources reassemble byte-identically to the original, so they are skipped.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    written: list[str] = []
    for txt in sorted(source_dir.glob("*.map.txt")):
        text = txt.read_text(encoding="utf-8")
        if mods_dir is not None:
            import apply_mods
            map_name = txt.name[: -len(".map.txt")]
            for mod in sorted(mods_dir.rglob("*.maps.json")):
                changes = json.loads(mod.read_text(encoding="utf-8"))
                if map_name in changes:
                    text = apply_mods.apply_map_mods(text, changes[map_name], map_name)
        parser = Parser(text, str(txt))
        parser.parse()
        base = _read_base(parser, str(txt), None, disc_path)
        rebuilt = _assemble_parsed(parser, str(txt), base)
        if rebuilt == base:
            continue
        stem = txt.name[: -len(".map.txt")]
        (out_dir / f"{stem}.MAP").write_bytes(rebuilt)
        written.append(stem)
    return written


# ---------------------------------------------------------------------------
# Command line
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    dis = sub.add_parser("disassemble", help="MAP -> readable text")
    dis.add_argument("map", type=Path, help="MAP file, or - to read it from stdin")
    dis.add_argument("--name", help="MAP filename when reading stdin (MAYO01.MAP)")
    dis.add_argument("--iso-path",
                     help="ISO path in the disc (e.g. /MAP/MAP1/MAYO01.MAP)")
    dis.add_argument("-o", "--output", type=Path)
    asm = sub.add_parser("assemble", help="readable text -> MAP")
    asm.add_argument("source", type=Path)
    asm.add_argument("-o", "--output", type=Path)
    asm.add_argument("--base", type=Path,
                     help="an extracted .MAP to read the binary sections from")
    asm.add_argument("--disc", type=Path,
                     help="disc image for a .base disc reference (or DW1_DISC)")
    bat = sub.add_parser("batch",
                         help="reassemble a directory; write the changed .MAPs")
    bat.add_argument("--source", type=Path, default=Path("scripts/maps"))
    bat.add_argument("--out", type=Path, required=True)
    bat.add_argument("--disc", type=Path,
                     help="disc image for .base disc references (or DW1_DISC)")
    bat.add_argument("--mods", type=Path, help="directory containing *.maps.json mods")
    args = parser.parse_args(argv)

    if args.command == "batch":
        written = batch_reassemble(args.source, args.out,
                                   str(args.disc) if args.disc else None, args.mods)
        for stem in written:
            print(stem)
        return 0

    if args.command == "disassemble":
        if str(args.map) == "-":
            if not args.name:
                parser.error("--name is required when reading from stdin")
            data = sys.stdin.buffer.read()
            name = args.name
        else:
            data = args.map.read_bytes()
            name = args.map.name
        if args.iso_path:
            text = disassemble(data, name, base_disc=args.iso_path)
        else:
            base_file = args.name if str(args.map) == "-" else str(args.map)
            text = disassemble(data, name, base_file=base_file)
        if args.output:
            args.output.write_text(text, encoding="utf-8")
        else:
            sys.stdout.write(text)
        return 0

    source = args.source.read_text(encoding="utf-8")
    base_bytes = args.base.read_bytes() if args.base else None
    data = assemble(source, str(args.source), base_bytes=base_bytes,
                    disc_path=args.disc)
    if args.output:
        args.output.write_bytes(data)
    else:
        sys.stdout.buffer.write(data)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (TextError, OSError) as error:
        sys.stderr.write(f"map_text: {error}\n")
        raise SystemExit(1)

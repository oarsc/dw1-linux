#!/usr/bin/env python3
"""Disassemble Digimon World USA SCN files using the native interpreter's format."""

from __future__ import annotations

import argparse
import contextlib
import io
import re
import sys
import unicodedata
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DG_OFFSET_READ_SIZE = 0x2000  # initializeScripts reads this much for SCRIPT_OFFSET_TABLE
MAP_SCRIPT_BUFFER_SIZE = 0x4000  # US MAP_SCRIPT_BUFFER in script_interp.c


class ScnError(ValueError):
    """Malformed or unsupported SCN structure."""


def u16(data: bytes, at: int) -> int:
    if at < 0 or at + 2 > len(data):
        raise ScnError(f"u16 read outside file at {at:#x}")
    return int.from_bytes(data[at : at + 2], "little")


def s16(data: bytes, at: int) -> int:
    return int.from_bytes(data[at : at + 2], "little", signed=True)


def c_array_entries(source: str, declaration: str) -> list[str]:
    """Extract top-level brace entries from a C array declaration."""
    start = source.find(declaration)
    if start < 0:
        return []
    opening = source.find("{", start)
    if opening < 0:
        return []
    depth = 1
    entries: list[str] = []
    entry_start: int | None = None
    for pos in range(opening + 1, len(source)):
        ch = source[pos]
        if ch == "{":
            if depth == 1:
                entry_start = pos
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 1 and entry_start is not None:
                entries.append(source[entry_start : pos + 1])
                entry_start = None
            elif depth == 0:
                return entries
    return []


def yaml_us_names(path: Path) -> dict[str, str]:
    """Read generated-text keys' en_us labels without requiring PyYAML."""
    if not path.is_file():
        return {}
    lines = path.read_text(encoding="utf-8").splitlines()
    result: dict[str, str] = {}
    symbol: str | None = None
    for line in lines + ["- name: __END__"]:
        stripped = line.strip()
        if stripped.startswith("- name:"):
            symbol = stripped.split(":", 1)[1].strip()
            continue
        if stripped.startswith("STR_") and stripped.endswith(":"):
            symbol = stripped[:-1]
        if symbol and (stripped.startswith("en_us:") or stripped.startswith("en_us@us:")):
            value = stripped.split(":", 1)[1].strip()
            if value and value != "NULL":
                result[symbol] = value.strip("'\"").strip()
    return result


def ordered_yaml_names(path: Path, block: str) -> dict[int, str]:
    """Read ordered named entries from an embedded-text YAML table."""
    if not path.is_file():
        return {}
    lines = path.read_text(encoding="utf-8").splitlines()
    active = False
    entries = False
    names: list[str | None] = []
    labels = yaml_us_names(path)
    for line in lines:
        if line and not line[0].isspace():
            active = line.rstrip().startswith(block + ":")
            entries = False
        elif active:
            stripped = line.strip()
            if stripped == "entries:":
                entries = True
            elif entries and stripped.startswith("- name:"):
                symbol = stripped.split(":", 1)[1].strip()
                names.append(labels.get(symbol))
            elif entries and stripped == "- NULL":
                names.append(None)
    return {i: name for i, name in enumerate(names) if name}


def map_entries() -> tuple[list[str], list[dict]]:
    """Return ``(map_names, entries)`` from the decomp's map tables.

    ``map_names`` is the ``MAP_NAME_PTR`` display strings, indexed by
    ``MapEntry.loadingName``.  ``entries`` is one element per ``MapEntry`` array
    slot (indexed by map id) with keys ``filename``, ``num8bpp``, ``num4bpp``,
    ``flags``, ``doorsId``, ``toiletId``, ``loadingName`` and ``display``;
    empty slots are ``None``.
    """
    map_names: list[str] = []
    entries: list[dict] = []
    source_path = ROOT / "decomp/src/main/map.c"
    if not source_path.is_file():
        return map_names, entries
    source = source_path.read_text(encoding="utf-8")
    raw_entries = c_array_entries(source, "MapEntry MAP_ENTRIES[255]")
    name_labels = yaml_us_names(ROOT / "decomp/text/main/map.yaml")

    declaration = "char *MAP_NAME_PTR[70]"
    start = source.find(declaration)
    opening = source.find("{", start) if start >= 0 else -1
    closing = source.find("};", opening) if opening >= 0 else -1
    name_body = source[opening + 1 : closing] if closing >= 0 else ""
    excluded_us_branch = False
    for line in name_body.splitlines():
        if line.strip() == "#if !VERSION_IS(US)":
            excluded_us_branch = True
            continue
        if line.strip() in ("#else", "#endif"):
            excluded_us_branch = False
            continue
        if excluded_us_branch:
            continue
        match = re.search(r"STR_MAP_NAME_([A-Z0-9_]+)", line)
        if match:
            symbol = "STR_MAP_NAME_" + match.group(1)
            map_names.append(name_labels.get(symbol, match.group(1)))

    for map_id, entry in enumerate(raw_entries):
        filename = re.search(r'^\s*\{\s*"([^"]+)"', entry)
        if not filename:
            entries.append(None)
            continue
        # MapEntry is a flat seven-element initializer; the string is first, then
        # num8bpp, num4bpp, flags, doorsId, toiletId, loadingName.
        rest = re.sub(r"/\*.*?\*/|//[^\n]*", "", entry[filename.end() :], flags=re.S)
        values = re.findall(r"(?<![A-Za-z0-9_])(?:0x[0-9a-fA-F]+|-?\d+)", rest)
        if len(values) < 6:
            entries.append(None)
            continue
        loading_name = int(values[5], 0)
        meta = {
            "filename": filename.group(1),
            "num8bpp": int(values[0], 0),
            "num4bpp": int(values[1], 0),
            "flags": int(values[2], 0),
            "doorsId": int(values[3], 0),
            "toiletId": int(values[4], 0),
            "loadingName": loading_name,
        }
        meta["display"] = map_names[loading_name] if loading_name < len(map_names) else ""
        entries.append(meta)
    return map_names, entries


def game_tables() -> tuple[dict[int, str], dict[int, str], dict[int, str], dict[int, str]]:
    """Return Digimon, map, move and item names from game tables/text YAML."""
    digimon: dict[int, str] = {}
    source_path = ROOT / "decomp/src/main/main.c"
    if source_path.is_file():
        source = source_path.read_text(encoding="utf-8")
        entries = c_array_entries(source, "DigimonPara DIGIMON_DATA[180]")
        labels = yaml_us_names(ROOT / "decomp/text/main/main.yaml")
        for index, entry in enumerate(entries):
            match = re.search(r"DIGIMON_PARA_NAME\(STR_DIGIMON_NAME_([A-Z0-9_]+)\)", entry)
            if match:
                symbol = "STR_DIGIMON_NAME_" + match.group(1)
                digimon[index] = labels.get(symbol, match.group(1))

    _, map_meta = map_entries()
    maps: dict[int, str] = {}
    for map_id, meta in enumerate(map_meta):
        if meta is None:
            continue
        maps[map_id] = meta["filename"] + (f" — {meta['display']}" if meta["display"] else "")
    item_yaml = ROOT / "decomp/text/main/item.yaml"
    return digimon, maps, ordered_yaml_names(item_yaml, "MOVE_NAMES"), ordered_yaml_names(item_yaml, "ITEM_NAMES")


def parse_dg_offsets(data: bytes) -> list[int]:
    """Read the monotonic DG.SCN map-offset prefix and stop at its end marker.

    The 0x2000-byte CD read buffer is larger than the real table. Once the final
    offset reaches EOF, subsequent words are ordinary file contents, not indices.
    """
    if len(data) < 8:
        raise ScnError("DG.SCN is too short to contain its offset table")
    max_entries = min(DG_OFFSET_READ_SIZE, len(data)) // 4
    offsets: list[int] = []
    for index in range(max_entries):
        value = int.from_bytes(data[index * 4 : index * 4 + 4], "little")
        if value == 0:
            break
        if value > len(data):
            # The first word past the valid prefix is not an offset. It must not
            # be reinterpreted as another script/map.
            break
        if offsets and value < offsets[-1]:
            break
        offsets.append(value)
        if value == len(data):
            break
    if len(offsets) < 2 or offsets[0] >= len(data) or offsets[-1] != len(data):
        raise ScnError(
            "could not find a valid monotonic map-offset table ending at the DG.SCN file size"
        )
    return offsets


def section_table(data: bytes, base: int, limit: int) -> list[tuple[int, int]]:
    """Return section IDs and absolute file offsets, as getScriptSection does."""
    if base < 0 or limit > len(data) or base + 2 > limit:
        raise ScnError(f"section table bounds invalid: {base:#x}..{limit:#x}")
    entries: list[tuple[int, int]] = []
    pos = base + 2
    while pos + 4 <= limit:
        section_id = u16(data, pos)
        offset = u16(data, pos + 2)
        pos += 4
        if section_id == 0xFFFF:
            if not entries:
                raise ScnError(f"empty section table at {base:#x}")
            return entries
        target = base + offset
        if target < pos or target >= limit:
            raise ScnError(
                f"section {section_id} target {target:#x} outside script extent {base:#x}..{limit:#x}"
            )
        entries.append((section_id, target))
    raise ScnError(f"unterminated section table at {base:#x}")


def text_end(data: bytes, start: int, limit: int) -> int | None:
    """Locate showTextbox's final 0d 00 00 00 sequence, bounded by its script."""
    end = data.find(b"\x0d\x00\x00\x00", start, limit)
    return None if end < 0 else end + 4


CONTROL_NAMES = {
    1: "style", 2: "style2", 3: "raw", 4: "pstat_number", 5: "speaker_jijimon",
    6: "speaker_player", 7: "digimon_name", 8: "move_name", 9: "item_name",
    10: "money", 11: "merit", 12: "control_0c", 13: "newline", 14: "control_0e",
    15: "control_0f", 16: "shop_variable", 17: "bgm_name", 18: "tournament_name",
    19: "tournaments_won", 20: "tournament_wins", 21: "tournaments_lost",
}


def decode_text(data: bytes, start: int, end: int) -> str:
    """Decode CP932 glyphs and retain interpreter control codes symbolically."""
    out: list[str] = []
    pos = start
    while pos < end:
        byte = data[pos]
        if byte == 0:
            break
        if byte == 0x0D and pos + 1 < end and data[pos + 1] == 0:
            out.append("\n")
            pos += 2
            continue
        if 1 <= byte <= 0x15:
            width = 4 if byte == 3 else 2
            raw = data[pos : min(pos + width, end)]
            name = CONTROL_NAMES[byte]
            args = " ".join(f"{value:02x}" for value in raw[1:])
            out.append("{" + name + (":" + args if args else "") + "}")
            pos += width
            continue
        # CP932 lead bytes are 81-9f and e0-fc; a1-df are single-byte kana.
        width = 2 if (0x81 <= byte <= 0x9F or 0xE0 <= byte <= 0xFC) and pos + 1 < end else 1
        raw = data[pos : pos + width]
        try:
            out.append(raw.decode("cp932"))
        except UnicodeDecodeError:
            out.append("<" + raw.hex(" ") + ">")
        pos += width
    # The US script text is often stored in full-width Latin characters and
    # ideographic spaces. Compatibility normalization makes dialogue easier to
    # read/search while retaining Japanese text as Unicode.
    return unicodedata.normalize("NFKC", "".join(out))


COMPARE = {0: "==", 1: "!=", 2: ">=", 3: "<=", 4: ">", 5: "<"}
STAT_NAMES = {
    0: "OFFENSE", 1: "DEFENSE", 2: "SPEED", 3: "BRAINS", 4: "MAX_HP", 5: "MAX_MP",
    6: "CURRENT_HP", 7: "CURRENT_MP", 8: "TIREDNESS", 9: "HAPPINESS", 10: "DISCIPLINE",
    11: "ENERGY", 12: "VIRUS", 13: "LIFETIME", 14: "MERIT", 15: "STARTED_BATTLES",
    16: "FLED_BATTLES", 17: "TOURNAMENTS_WON", 18: "TOURNAMENT_WINS",
    19: "TOURNAMENTS_LOST", 20: "WEIGHT", 21: "TAMER_LEVEL", 22: "LIVES",
}


def decode_if(
    data: bytes,
    at: int,
    end: int,
    base: int = 0,
    sections: list[tuple[int, int]] | None = None,
    move_names: dict[int, str] | None = None,
    item_names: dict[int, str] | None = None,
) -> tuple[int, list[str]]:
    """Decode IF entries using the condition layouts in scriptIfInstruction()."""
    move_names = move_names or {}
    item_names = item_names or {}
    pos = at + 2  # opcode and padding; the interpreter skips the padding
    lines: list[str] = []
    while pos + 2 <= end:
        cond = data[pos]
        pos += 2  # condition byte and reserved byte
        if cond == 0x19:
            return pos, lines
        kind, comparator = cond & 0x38, cond & 7
        if kind == 0:
            if pos + 2 > end:
                raise ScnError(f"truncated trigger condition in IF at {at:#x}")
            trigger = u16(data, pos)
            pos += 2
            text = f"trigger[{trigger}] {'== 1 (set)' if comparator == 0 else '== 0 (clear)'}"
        elif kind == 8:
            if pos + 2 > end:
                raise ScnError(f"truncated pstat condition in IF at {at:#x}")
            pstat, value = data[pos], data[pos + 1]
            pos += 2
            text = f"pstat[{pstat}] {COMPARE.get(comparator, f'op{comparator}')} {value} (0x{value:02x})"
        elif kind in (16, 24):
            if pos + 2 > end:
                raise ScnError(f"truncated branch target in IF at {at:#x}")
            target = u16(data, pos)
            pos += 2
            text = f"if {'true' if kind == 16 else 'false'} then goto {format_target(target, base, sections or [])}"
        elif kind == 32:
            if comparator == 0:
                if pos + 4 > end:
                    raise ScnError(f"truncated stat comparison in IF at {at:#x}")
                stat, compare = data[pos], data[pos + 1]
                value = s16(data, pos + 2) if stat == 9 else u16(data, pos + 2)
                pos += 4
                text = f"stat[{STAT_NAMES.get(stat, hex(stat))}] {COMPARE.get(compare, f'op{compare}')} {value}"
            elif comparator == 1:
                if pos + 4 > end:
                    raise ScnError(f"truncated card comparison in IF at {at:#x}")
                item, compare = data[pos], data[pos + 1]
                value = u16(data, pos + 2)
                pos += 4
                text = f"card[{item}] {COMPARE.get(compare, f'op{compare}')} {value}"
            elif comparator == 2:
                if pos + 2 > end:
                    raise ScnError(f"truncated move comparison in IF at {at:#x}")
                move, negate = data[pos], data[pos + 1]
                pos += 2
                text = f"has_move[{move} ({move_names.get(move, 'unknown move')})] == {0 if negate else 1}"
            elif comparator == 3:
                if pos + 2 > end:
                    raise ScnError(f"truncated condition comparison in IF at {at:#x}")
                mask, negate = data[pos], data[pos + 1]
                pos += 2
                conditions = ((1, "SLEEPY"), (2, "TIRED"), (4, "HUNGRY"), (8, "POOPY"),
                              (16, "UNHAPPY"), (32, "INJURED"), (64, "SICK"))
                selected = [name for bit, name in conditions if mask & bit]
                mask_text = "|".join(selected) if selected else "NONE"
                text = f"(partner.condition & {mask_text} [0x{mask:02x}]) {'== 0' if negate else '!= 0'}"
            elif comparator == 4:
                if pos + 4 > end:
                    raise ScnError(f"truncated item comparison in IF at {at:#x}")
                item, compare = data[pos], data[pos + 1]
                value = u16(data, pos + 2)
                pos += 4
                text = f"item_count[{item} ({item_names.get(item, 'unknown item')})] {COMPARE.get(compare, f'op{compare}')} {value}"
            elif comparator == 5:
                if pos + 6 > end:
                    raise ScnError(f"truncated money comparison in IF at {at:#x}")
                compare = data[pos + 1]
                value = int.from_bytes(data[pos + 2 : pos + 6], "little", signed=False)
                pos += 6
                text = f"money {COMPARE.get(compare, f'op{compare}')} {value}"
            else:
                raise ScnError(f"unknown IF comparison {comparator} at {pos - 2:#x}")
        else:
            raise ScnError(f"unknown IF condition class {kind:#x} at {pos - 2:#x}")
        if pos > end:
            raise ScnError(f"truncated IF at {at:#x}")
        join = "AND" if cond & 0x80 else "OR" if cond & 0x40 else "THEN"
        lines.append(f"{join} {text}")
    raise ScnError(f"unterminated IF at {at:#x}")


OPCODES = {
    0x10: "SET_SELECTION", 0x11: "UNUSED_11", 0x12: "UNUSED_12", 0x13: "JUMP_AND_LINK",
    0x14: "JUMP_TO_FILE_AND_LINK", 0x15: "JUMP_RETURN", 0x16: "JUMP_TO", 0x17: "JUMP_TO_FILE",
    0x18: "SWITCH", 0x19: "IF", 0x1A: "SHOW_TEXTBOX", 0x1B: "SET_DIALOG_OWNER",
    0x1C: "SET_TRIGGER", 0x1D: "UNSET_TRIGGER", 0x1E: "SET_PSTAT", 0x1F: "ADD_TO_PSTAT",
    0x20: "REDUCE_PSTAT", 0x21: "STORE_MAP_ID", 0x22: "STORE_DIGIMON_TYPE",
    0x23: "SET_INVENTORY_SIZE", 0x24: "STORE_RANDOM", 0x25: "STORE_DATE",
    0x26: "SET_TEXTBOX_SIZE", 0x27: "FADEOUT_HUD", 0x28: "GIVE_ITEM", 0x29: "REMOVE_ITEM",
    0x2A: "ADD_MONEY", 0x2B: "REDUCE_MONEY", 0x2C: "COMPARE_DATE", 0x2D: "LEARN_MOVE",
    0x2E: "UNUSED_2E", 0x2F: "GIVE_CARD", 0x30: "TAKE_CARD", 0x31: "SET_MERIT",
    0x32: "ADD_MERIT", 0x33: "REDUCE_MERIT", 0x34: "SET_STAT", 0x35: "ADD_STAT",
    0x36: "REDUCE_STAT", 0x37: "ADVANCE_TO_DATE_AT", 0x38: "ADD_MINUTES_TO_DATE_AT",
    0x39: "ADD_MINUTES_TO_DATE_AT_2", 0x3A: "UNUSED_3A", 0x3B: "UNUSED_3B",
    0x3C: "UNUSED_3C", 0x3D: "UNUSED_3D", 0x3E: "UNUSED_3E", 0x3F: "STORE_DIGIMON_VALUE",
    0x46: "LOAD_DIGIMON", 0x47: "SET_DIGIMON", 0x48: "UNLOAD_ENTITY",
    0x49: "CALL_DIGIMON_ROUTINE", 0x4A: "WAIT_FOR_ENTITY", 0x4B: "WARP_TO",
    0x4C: "ENTITY_LOOK_AT_ENTITY", 0x4D: "ENTITY_SET_ROTATION", 0x4E: "ENTITY_WALK_TO",
    0x4F: "MOVE_CAMERA_TO", 0x50: "MOVE_CAMERA_TO_ENTITY", 0x51: "ENTITY_WALK_TO_ENTITY",
    0x52: "ENTITY_WALK_TO_WITH_CAMERA", 0x53: "ENTITY_WALK_TO_ENTITY_WITH_CAMERA",
    0x54: "RESET_ENTITY_ORIGIN", 0x55: "SET_TEXTBOX_ORIGIN", 0x56: "PLAY_ANIMATION",
    0x57: "SET_OBJ_VISIBILITY", 0x58: "TELEPORT", 0x5A: "PLAY_SOUND", 0x5B: "UNUSED_5B",
    0x5C: "UNUSED_5C", 0x5D: "SET_BGM", 0x5E: "STOP_BGM", 0x5F: "UNUSED_5F",
    0x64: "CALL_ROUTINE", 0x65: "REMOVE_CONDITION", 0x66: "START_BATTLE", 0x67: "DELAY",
    0x68: "SET_TEXTBOX_MODE", 0x69: "DEAL_DAMAGE", 0x6A: "SET_AUTOTALK", 0x6B: "DATA",
    0x6C: "ENTITY_MOVE_TO", 0x6D: "ENTITY_MOVE_TO_ENTITY", 0x6E: "ENTITY_MOVE_TO_WITH_CAMERA",
    0x6F: "ENTITY_MOVE_TO_ENTITY_WITH_CAMERA", 0x70: "ROTATE_3D_OBJECT", 0x71: "MOVE_OBJECT_TO",
    0x72: "ENTITY_MOVE_TO_AXIS", 0x73: "ENTITY_MOVE_TO_AXIS_WITH_CAMERA", 0x74: "SPAWN_ITEM",
    0x75: "SPAWN_CHEST", 0x76: "SPAWN_BOULDER", 0x77: "MOVE_BOULDER", 0x78: "DESPAWN_BOULDER",
    0x79: "UNLOAD_DIGIMON", 0x7A: "COPY_PSTAT", 0x7B: "SECTION_ON_EXIT",
    0x7C: "SET_RECT_IMPASSABLE", 0x7D: "SPAWN_SPRITE_AT_LOCATION",
    0x7E: "SPAWN_SPRITE_AT_ENTITY", 0xFB: "SET_SCRIPT", 0xFC: "UNUSED_FC",
    0xFD: "UNUSED_FD", 0xFE: "END_SECTION", 0xFF: "END_SCRIPT",
}

# Fixed operand widths/types, transcribed from dw/script.h. Padding is one byte.
OPERANDS = {
    0x11: ("_",), 0x12: ("_",), 0x15: ("_",), 0x1B: ("id",),
    0x1C: ("_", "u16"), 0x1D: ("_", "u16"),
    0x1E: ("_", "pstat", "u8"), 0x1F: ("_", "pstat", "u8"), 0x20: ("_", "pstat", "u8"),
    0x21: ("pstat",), 0x22: ("pstat",), 0x23: ("u8",), 0x24: ("_", "pstat", "u8"),
    0x25: ("pstat",), 0x26: ("id", "u8", "u8"), 0x27: ("u8",),
    0x28: ("_", "u8", "u8"), 0x29: ("_", "u8", "u8"), 0x2A: ("_", "s32"), 0x2B: ("_", "s32"),
    0x2C: ("pstat", "u16", "u8", "u8", "u8", "u8", "u8", "_"),
    0x2D: ("u8",), 0x2E: ("u8",), 0x2F: ("u8",), 0x30: ("u8",),
    0x31: ("_", "u16"), 0x32: ("_", "u16"), 0x33: ("_", "u16"),
    0x34: ("u8", "u16"), 0x35: ("u8", "u16"), 0x36: ("u8", "u16"),
    0x37: ("pstat",), 0x38: ("pstat", "s32"), 0x39: ("pstat", "s32"),
    0x3A: ("_", "u8", "u8"), 0x3B: ("_", "u8", "u8"), 0x3C: ("_", "u8", "u8"),
    0x3D: ("u8",), 0x3E: ("u8",), 0x3F: ("_", "pstat", "pstat"),
    0x46: ("u8",), 0x47: ("u8", "u8", "u8"), 0x48: ("id",), 0x49: ("u8",),
    0x4A: ("id",), 0x4B: ("u8", "u8", "u8"), 0x4C: ("_", "id", "id"),
    0x4D: ("id", "s16"), 0x4E: ("id", "s16", "s16", "u8", "u8"),
    0x4F: ("u8", "s16", "s16"), 0x50: ("_", "id", "u8"), 0x51: ("id", "u8", "id"),
    0x52: ("id", "s16", "s16", "u8", "u8"), 0x53: ("id", "u8", "id"), 0x54: ("id",),
    0x55: ("_", "s16", "s16", "s16"), 0x56: ("_", "id", "u8"), 0x57: ("_", "u8", "u8"),
    0x58: ("pstat",), 0x5A: ("_", "u8", "u8"), 0x5B: ("u8",), 0x5C: ("u8",),
    0x5D: ("u8",), 0x5E: ("u8",), 0x5F: ("u8",), 0x64: ("u8",), 0x65: ("u8",),
    0x66: ("u8",), 0x67: ("_", "u16"), 0x68: ("_", "u8", "u8"), 0x69: ("pstat",),
    0x6A: ("_", "id", "u8"), 0x6C: ("id", "s16", "s16", "u8", "u8"),
    0x6D: ("id", "id", "u8"), 0x6E: ("id", "s16", "s16", "u8", "u8"),
    0x6F: ("id", "id", "u8"), 0x70: ("u8", "u8", "u8"),
    0x71: ("u8", "id", "u8", "s8", "_", "s16", "s16"),
    0x72: ("id", "s16", "u8", "u8"), 0x73: ("id", "s16", "u8", "u8"),
    0x74: ("u8", "s16", "s16"), 0x75: ("u8", "s16", "s16", "s16", "s16", "u16"),
    0x76: ("u8",), 0x77: ("u8", "s16", "s16"), 0x78: ("u8",), 0x79: ("u8",),
    0x7A: ("_", "pstat", "pstat"), 0x7B: ("u8",), 0x7C: ("u8", "s16", "s16", "u8", "u8"),
    0x7D: ("u8", "s16", "s16", "s16", "s16"), 0x7E: ("id", "u8", "u8"),
    0xFB: ("_", "u16", "u16"), 0xFC: (), 0xFD: (),
}


def operand_width(kind: str) -> int:
    return 1 if kind in ("u8", "s8", "id", "pstat", "_") else 2 if kind in ("u16", "s16") else 4


FIXED_LENGTH = {op: 1 + sum(operand_width(kind) for kind in spec) for op, spec in OPERANDS.items()}
FIXED_LENGTH[0x2C] = 10


def decode_operands(data: bytes, at: int, spec: tuple[str, ...]) -> list[tuple[str, int]]:
    result: list[tuple[str, int]] = []
    argument = 1
    for kind in spec:
        width = operand_width(kind)
        raw = int.from_bytes(data[at : at + width], "little", signed=kind.startswith("s"))
        if kind != "_":
            result.append((kind, raw))
            argument += 1
        at += width
    return result


def format_target(target: int, base: int, sections: list[tuple[int, int]]) -> str:
    absolute = base + target
    owner = max(((sid, start) for sid, start in sections if start <= absolute), key=lambda pair: pair[1], default=None)
    label = f"section {owner[0]}+{absolute - owner[1]:#x}; " if owner else ""
    return f"{label}script+{target:#06x} (@{absolute:#08x})"


def format_args(op: int, args: list[tuple[str, int]], digimon_names: dict[int, str], map_names: dict[int, str], move_names: dict[int, str] | None = None, item_names: dict[int, str] | None = None) -> str:
    move_names = move_names or {}
    item_names = item_names or {}
    if op in (0x46, 0x47, 0x79) and args:
        digimon_id = args[0][1]
        name = digimon_names.get(digimon_id, "unknown ID")
        result = f"digimon={digimon_id}/0x{digimon_id:02x} ({name})"
        if op == 0x47 and len(args) == 3:
            result += f", slot={args[1][1]}, autotalk={args[2][1]}"
        return result
    if op == 0x4B and args:
        map_id = args[0][1]
        result = f"map={map_id} ({map_names.get(map_id, 'unknown map')}), exit={args[1][1]}, section={args[2][1]}"
        return result
    if op in (0x14, 0x17):
        map_id, section_id = args[0][1], args[1][1]
        return f"map={map_id} ({map_names.get(map_id, 'unknown map')}), section={section_id}"
    if op == 0xFB:
        script_id, map_id = args[0][1], args[1][1]
        return f"script={script_id}, map={map_id} ({map_names.get(map_id, 'unknown map')})"
    if op == 0x2D and args:
        value = args[0][1]
        return f"move={value:#04x} ({move_names.get(value, 'unknown move')})"
    if op in (0x28, 0x29, 0x74, 0x75) and args:
        value = args[0][1]
        text = f"item={value:#04x} ({item_names.get(value, 'unknown item')})"
        if op in (0x74, 0x75):
            fields = ("x", "z") if op == 0x74 else ("x", "y", "z", "w", "trigger")
            for field, (_, coordinate) in zip(fields, args[1:]):
                text += f", {field}={coordinate}"
            return text
        if len(args) > 1:
            return f"{text}, amount={args[1][1]}"
        return text + (", " + ", ".join(f"arg{i}={v:#x}" for i, (_, v) in enumerate(args[1:], 1)) if len(args) > 1 else "")
    rendered = []
    labels = {
        0x1B: ("entity",), 0x1C: ("trigger",), 0x1D: ("trigger",),
        0x1E: ("pstat", "value"), 0x1F: ("pstat", "amount"), 0x20: ("pstat", "amount"),
        0x21: ("pstat_out",), 0x22: ("pstat_out",), 0x23: ("size",),
        0x24: ("pstat_out", "max"), 0x25: ("pstat_date",),
        0x26: ("origin", "columns", "rows"), 0x27: ("textbox",),
        0x2A: ("amount",), 0x2B: ("amount",), 0x2F: ("card",), 0x30: ("card",),
        0x31: ("value",), 0x32: ("amount",), 0x33: ("amount",),
        0x34: ("stat", "value"), 0x35: ("stat", "amount"), 0x36: ("stat", "amount"),
        0x37: ("pstat_date",), 0x38: ("pstat_date", "minutes"), 0x39: ("pstat_date", "minutes"),
        0x3F: ("pstat_digimon", "pstat_out"), 0x46: ("digimon",),
        0x48: ("entity",), 0x49: ("routine",), 0x4A: ("entity",),
        0x4C: ("entity", "target"), 0x4D: ("entity", "rotation"),
        0x4E: ("entity", "x", "z", "animation", "flags"),
        0x4F: ("speed", "x", "z"), 0x50: ("entity", "speed"),
        0x51: ("entity", "animation", "target"),
        0x52: ("entity", "x", "z", "animation", "flags"),
        0x53: ("entity", "animation", "target"), 0x54: ("entity",),
        0x55: ("x", "y", "z"), 0x56: ("entity", "animation"),
        0x57: ("object", "visible"), 0x58: ("pstat_map_exit",),
        0x5A: ("bank", "sound"), 0x5D: ("bgm",), 0x5E: ("arg",),
        0x64: ("builtin",), 0x65: ("condition_mask",), 0x66: ("battle",),
        0x67: ("frames",), 0x68: ("mode", "frames"), 0x69: ("damage_percent",),
        0x6A: ("entity", "autotalk"), 0x6C: ("entity", "x", "z", "speed", "flags"),
        0x6D: ("entity", "target", "speed"), 0x6E: ("entity", "x", "z", "speed", "flags"),
        0x6F: ("entity", "target", "speed"), 0x70: ("door", "arg", "target"),
        0x71: ("slot", "entity", "speed", "angle", "x", "z"),
        0x72: ("entity", "target", "axis", "speed"), 0x73: ("entity", "target", "axis", "speed"),
        0x74: ("item", "x", "z"), 0x75: ("item", "x", "y", "z", "w", "trigger"),
        0x76: ("boulder",), 0x77: ("boulder", "x", "z"), 0x78: ("boulder",),
        0x79: ("digimon",), 0x7A: ("pstat_from", "pstat_to"), 0x7B: ("section",),
        0x7C: ("rect", "x", "z", "width", "height"),
        0x7D: ("sprite", "x", "y", "z", "w"), 0x7E: ("entity", "node", "sprite"),
    }
    names = labels.get(op, ())
    for index, (kind, value) in enumerate(args):
        key = names[index] if index < len(names) else f"{kind}{index + 1}"
        if op in (0x34, 0x35, 0x36) and index == 0:
            rendered.append(f"stat={STAT_NAMES.get(value, f'stat_{value:#x}')} ({value:#x})")
            continue
        rendered.append(f"{key}={value if kind.startswith('s') else f'{value} (0x{value:x})'}")
    return ", ".join(rendered)


def disassemble_script(
    data: bytes,
    base: int,
    limit: int,
    label: str,
    digimon_names: dict[int, str],
    map_names: dict[int, str],
    move_names: dict[int, str] | None = None,
    item_names: dict[int, str] | None = None,
) -> None:
    sections = section_table(data, base, limit)
    print(f"\n## {label} (file range {base:#08x}..{limit:#08x})")
    for section_id, start in sections:
        next_start = min((pos for _, pos in sections if pos > start), default=limit)
        print(f"\n### section {section_id} @ {start:#08x}")
        at = start
        while at < next_start:
            op = data[at]
            if op in (0x1A, 0x10):
                if op == 0x1A:
                    text_start = at + 2
                    table = []
                else:
                    if at + 2 > next_start:
                        raise ScnError(f"truncated SET_SELECTION at {at:#x}")
                    count = data[at + 1]
                    table_start = at + 2
                    table = [u16(data, table_start + 2 * i) for i in range(count + 1)]
                    text_start = table_start + 2 * (count + 1)
                end = text_end(data, text_start, next_start)
                if end is None:
                    raise ScnError(f"unterminated textbox at {at:#x} (section {section_id})")
                text = decode_text(data, text_start, end - 4)
                if op == 0x1A:
                    print(f"{at:08x}: SHOW_TEXTBOX {text!r}")
                else:
                    count = data[at + 1]
                    lines = [line for line in text.splitlines() if line]
                    print(f"{at:08x}: SET_SELECTION count={count}")
                    for i, target in enumerate(table[:count]):
                        choice = lines[i] if i < len(lines) else "<option text unavailable>"
                        print(f"         option {i}: {choice!r} -> {format_target(target, base, sections)}")
                    if len(table) > count:
                        print(f"         fallback -> {format_target(table[-1], base, sections)}")
                    if len(lines) > count:
                        print(f"         prompt/extra text: {lines[count:]!r}")
                at = end
                continue
            if op == 0x19:
                if_at = at
                at, conditions = decode_if(data, at, next_start, base, sections, move_names, item_names)
                print(f"{if_at:08x}: IF [{at - if_at} bytes]")
                for condition in conditions:
                    print(f"         {condition}")
                continue
            if op == 0x18:
                if at + 4 > next_start:
                    raise ScnError(f"truncated SWITCH at {at:#x}")
                count = u16(data, at + 2)
                end = at + 4 + count * 2
                if end > next_start:
                    raise ScnError(f"SWITCH target table overruns section at {at:#x}")
                targets = [u16(data, at + 4 + 2 * i) for i in range(count)]
                print(f"{at:08x}: SWITCH pstat={data[at + 1]:#04x} count={count}")
                for index, target in enumerate(targets):
                    print(f"         case {index}: {format_target(target, base, sections)}")
                at = end
                continue
            if op in (0x13, 0x16):
                if at + 4 > next_start:
                    raise ScnError(f"truncated {OPCODES[op]} at {at:#x}")
                print(f"{at:08x}: {OPCODES[op]} {format_target(u16(data, at + 2), base, sections)}")
                at += 4
                continue
            if op in (0x14, 0x17):
                if at + 6 > next_start:
                    raise ScnError(f"truncated {OPCODES[op]} at {at:#x}")
                args = [("u16", u16(data, at + 2)), ("u16", u16(data, at + 4))]
                print(f"{at:08x}: {OPCODES[op]} {format_args(op, args, digimon_names, map_names, move_names, item_names)}")
                at += 6
                continue
            if op == 0x6B:
                sentinel = data.find(b"\xff", at + 2, next_start)
                if sentinel < 0:
                    raise ScnError(f"DATA block at {at:#x} has no 0xff sentinel")
                payload = data[at + 2 : sentinel]
                print(f"{at:08x}: DATA [{len(payload)} bytes] {payload.hex(' ')}")
                at = sentinel + 1
                continue
            if op in (0xFE, 0xFF):
                print(f"{at:08x}: {OPCODES[op]}")
                break
            if op in OPERANDS:
                length = FIXED_LENGTH[op]
                if at + length > next_start:
                    raise ScnError(f"truncated {OPCODES.get(op, hex(op))} at {at:#x}")
                args = decode_operands(data, at + 1, OPERANDS[op])
                text = format_args(op, args, digimon_names, map_names, move_names, item_names)
                print(f"{at:08x}: {OPCODES.get(op, hex(op)):<34} {text}")
                at += length
                continue
            raise ScnError(f"unknown opcode {op:#04x} at {at:#x} in section {section_id}; cannot safely continue")


def run(args: argparse.Namespace) -> str:
    path = args.scn
    name = path.name.upper()
    if name not in ("DG.SCN", "MAPHEAD.SCN"):
        raise ScnError("input must be DG.SCN or MAPHEAD.SCN")
    data = path.read_bytes()
    digimon, maps, moves, items = game_tables()
    output = io.StringIO()
    with contextlib.redirect_stdout(output):
        if name == "MAPHEAD.SCN":
            disassemble_script(data, 0, len(data), name, digimon, maps, moves, items)
        else:
            offsets = parse_dg_offsets(data)
            terminal_index = len(offsets) - 1
            if args.list_maps:
                print("map-id  file-offset  length  map")
                for map_id in range(1, terminal_index):
                    start, end = offsets[map_id], offsets[map_id + 1]
                    print(f"{map_id:6}  {start:#010x}  {end - start:6}  {maps.get(map_id, 'unknown map')}")
                return output.getvalue()
            map_ids = [args.map_id] if args.map_id is not None else list(range(1, terminal_index))
            for map_id in map_ids:
                if map_id <= 0 or map_id >= terminal_index:
                    raise ScnError(f"map ID {map_id} outside valid range 1..{terminal_index - 1}; map 0 is MAPHEAD.SCN")
                base, limit = offsets[map_id], offsets[map_id + 1]
                if limit == base:
                    print(f"\n## map {map_id} ({maps.get(map_id, 'unknown map')}): empty extent")
                    continue
                if limit - base > MAP_SCRIPT_BUFFER_SIZE:
                    raise ScnError(f"map {map_id} extent {limit - base:#x} exceeds the game's 0x4000-byte map script buffer")
                disassemble_script(data, base, limit, f"map {map_id} ({maps.get(map_id, 'unknown map')})", digimon, maps, moves, items)
    return output.getvalue()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("scn", type=Path, help="DG.SCN or MAPHEAD.SCN")
    parser.add_argument("--output", "-o", type=Path, help="write the listing to this file")
    parser.add_argument("--map", dest="map_id", type=int, help="only disassemble this DG.SCN map ID")
    parser.add_argument("--list-maps", action="store_true", help="list valid DG.SCN map IDs and extents")
    args = parser.parse_args(argv)
    if args.list_maps and args.map_id is not None:
        parser.error("--list-maps and --map cannot be used together")
    try:
        listing = run(args)
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(listing, encoding="utf-8")
        else:
            sys.stdout.write(listing)
    except (OSError, ScnError) as error:
        print(f"scn-dumper: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

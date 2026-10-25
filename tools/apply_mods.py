#!/usr/bin/env python3
"""Apply source-only DW1 mods to locally extracted SCN and MAP text."""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


def apply_script_mod(source: str, mod_path: Path) -> str:
    """Apply @ FILE label blocks; MAPHEAD @ entries supports ID -> label rows."""
    lines = source.splitlines()
    source_file = "DG" if any(row.strip() == ".scn DG" for row in lines) else "MAPHEAD"
    directives = mod_path.read_text(encoding="utf-8").splitlines()
    blocks: list[tuple[str, str, list[str], str]] = []
    current: tuple[str, str, list[str]] | None = None
    for number, line in enumerate(directives, 1):
        if line.startswith("@ "):
            parts = line[2:].split()
            if len(parts) != 2 or parts[0] not in ("DG", "MAPHEAD"):
                raise ValueError(f"{mod_path}:{number}: expected @ DG|MAPHEAD LABEL|entries")
            current = (parts[0], parts[1], [], "replace")
            blocks.append(current)
        elif line.startswith("- "):
            parts = line[2:].split()
            if len(parts) != 2 or parts[0] != "DG":
                raise ValueError(f"{mod_path}:{number}: expected - DG LABEL")
            current = ("DG", parts[1], [], "delete")
            blocks.append(current)
        elif line.startswith("+ "):
            parts = line[2:].split()
            if parts[:2] == ["DG", "map"] and len(parts) == 5 and parts[3] == "section":
                current = ("DG", parts[4], [], f"add-map-{parts[2]}")
            elif parts[:2] == ["MAPHEAD", "entry"] and len(parts) == 5 and parts[3] == "->":
                current = ("MAPHEAD", parts[4], [], f"add-entry-{parts[2]}")
            else:
                raise ValueError(f"{mod_path}:{number}: invalid addition directive")
            blocks.append(current)
        elif current is None:
            if line.strip() and not line.lstrip().startswith("#"):
                raise ValueError(f"{mod_path}:{number}: content before first @ block")
        else:
            current[2].append(line)

    for file_name, label, body, mode in blocks:
        if file_name != source_file:
            continue
        if mode == "delete":
            if any(line.strip() and not line.lstrip().startswith("#") for line in body):
                raise ValueError(f"{mod_path}: - DG {label} does not take a body")
            label_line = f"{label}:"
            matches = [i for i, row in enumerate(lines) if row.strip() == label_line]
            if len(matches) != 1:
                raise ValueError(
                    f"{mod_path}: expected exactly one DG label {label!r}, found {len(matches)}"
                )
            start = matches[0]

            # Remove any DG map-entry rows that make this label an externally
            # selectable section. The assembler validates remaining code refs.
            map_start = next(
                (i for i in range(start, -1, -1) if re.match(r"^\s*\.map\s+", lines[i])),
                None,
            )
            if map_start is None:
                raise ValueError(f"{mod_path}: DG label {label!r} is not inside a map")
            map_end = next(
                (i for i in range(map_start + 1, len(lines)) if re.match(r"^\s*\.map\s+", lines[i])),
                len(lines),
            )
            entries_start = next(
                (i for i in range(map_start + 1, map_end) if lines[i].strip() == ".entries"),
                None,
            )
            if entries_start is not None:
                entries_end = next(
                    (i for i in range(entries_start + 1, map_end) if lines[i].strip() == ".end"),
                    None,
                )
                if entries_end is None:
                    raise ValueError(f"{mod_path}: unterminated .entries in DG map")
                entry_pattern = re.compile(
                    r"^\s*(?:0x[0-9a-fA-F]+|\d+)\s*->\s*([A-Za-z_]\w*)\s*(?:#.*)?$"
                )
                lines = [
                    row for i, row in enumerate(lines)
                    if not (entries_start < i < entries_end
                            and (entry := entry_pattern.match(row))
                            and entry.group(1) == label)
                ]

            start = next(i for i, row in enumerate(lines) if row.strip() == label_line)
            following = next(
                (i for i in range(start + 1, len(lines))
                 if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*:", lines[i]) or lines[i] == ".end"),
                len(lines),
            )
            del lines[start:following]
            continue
        if mode.startswith("add-map-"):
            if any(line.strip() == "~CONTINUE" for line in body):
                raise ValueError(f"{mod_path}: ~CONTINUE is only valid when overriding an existing block")
            map_id = int(mode.removeprefix("add-map-"), 0)
            match = re.search(rf"(?m)^\.map\s+{map_id}\b.*$", "\n".join(lines))
            if not match:
                raise ValueError(f"{mod_path}: DG map {map_id} not found")
            start = next(i for i, row in enumerate(lines) if row == match.group(0))
            next_map = next((i for i in range(start + 1, len(lines))
                             if re.match(r"^\s*\.map\s+", lines[i])), len(lines))
            end = max((i for i in range(start + 1, next_map)
                       if lines[i] == ".end"), default=None)
            if end is None:
                raise ValueError(f"{mod_path}: unterminated DG map {map_id}")
            lines[end:end] = [label + ":", *body]
            continue
        if mode.startswith("add-entry-"):
            if any(line.strip() == "~CONTINUE" for line in body):
                raise ValueError(f"{mod_path}: ~CONTINUE is only valid when overriding an existing block")
            if file_name != "MAPHEAD":
                raise ValueError(f"{mod_path}: MAPHEAD entry addition is invalid here")
            entry_id = int(mode.removeprefix("add-entry-"), 0)
            entries_start = next((i for i, row in enumerate(lines) if row.strip() == ".entries"), None)
            entries_end = (next((i for i in range(entries_start + 1, len(lines)) if lines[i].strip() == ".end"), None)
                           if entries_start is not None else None)
            if entries_end is None:
                raise ValueError(f"{mod_path}: MAPHEAD .entries block not found")
            entry_pattern = re.compile(r"^(\s*)(0x[0-9a-fA-F]+|\d+)\s*->\s*[A-Za-z_]\w*\s*$")
            existing = next((i for i, row in enumerate(lines[entries_start + 1:entries_end], entries_start + 1)
                             if (match := entry_pattern.match(row)) and int(match.group(2), 0) == entry_id), None)
            if existing is None:
                lines.insert(entries_end, f"    0x{entry_id:03x} -> {label}")
            else:
                match = entry_pattern.match(lines[existing])
                assert match is not None
                lines[existing] = f"{match.group(1)}0x{entry_id:03x} -> {label}"
            if any(row.strip() == f"{label}:" for row in lines):
                raise ValueError(f"{mod_path}: MAPHEAD label {label!r} already exists")
            # Insert the new labeled body before the enclosing MAPHEAD object terminator.
            obj = next(i for i, row in enumerate(lines) if row.strip() == ".object MAPHEAD")
            obj_end = max(i for i in range(obj + 1, len(lines)) if lines[i].strip() == ".end")
            lines[obj_end:obj_end] = [label + ":", *body]
            continue
        if label == "entries":
            if file_name != "MAPHEAD":
                raise ValueError(f"{mod_path}: entries block is only valid for MAPHEAD")
            pattern = re.compile(r"^(\s*)(0x[0-9a-fA-F]+|\d+)\s*->\s*\w+\s*$")
            replacements = [line for line in body if line.strip() and not line.lstrip().startswith("#")]
            for entry in replacements:
                match = re.match(r"^\s*(0x[0-9a-fA-F]+|\d+)\s*->\s*[A-Za-z_]\w*\s*$", entry)
                if not match:
                    raise ValueError(f"{mod_path}: invalid MAPHEAD entry {entry!r}")
                key = int(match.group(1), 0)
                found = False
                for i, old in enumerate(lines):
                    parsed = pattern.match(old)
                    if parsed and int(parsed.group(2), 0) == key:
                        lines[i] = parsed.group(1) + entry.strip()
                        found = True
                        break
                if not found:
                    entries_start = next((i for i, row in enumerate(lines)
                                          if row.strip() == ".entries"), None)
                    at = (next((i for i in range(entries_start + 1, len(lines))
                                if lines[i].strip() == ".end"), None)
                          if entries_start is not None else None)
                    if at is None:
                        raise ValueError(f"{mod_path}: MAPHEAD .entries block not found")
                    lines.insert(at, "    " + entry.strip())
            continue

        label_line = f"{label}:"
        try:
            start = next(i for i, row in enumerate(lines) if row.strip() == label_line)
        except StopIteration:
            # A new MAPHEAD section is declared at file scope, before the object terminator.
            if file_name != "MAPHEAD":
                raise ValueError(f"{mod_path}: label {label!r} not present in {file_name}")
            obj = next((i for i, row in enumerate(lines) if row.strip() == ".object MAPHEAD"), None)
            if obj is None:
                raise ValueError(f"{mod_path}: MAPHEAD object not found")
            end = max(i for i in range(obj + 1, len(lines)) if lines[i] == ".end")
            lines[end:end] = [label_line, *body]
            continue
        following = next((i for i in range(start + 1, len(lines))
                          if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*:", lines[i])
                          or lines[i] == ".end"), len(lines))
        continue_at = [i for i, line in enumerate(body) if line.strip() == "~CONTINUE"]
        if len(continue_at) > 1:
            raise ValueError(f"{mod_path}: block {label!r} has more than one ~CONTINUE marker")
        if continue_at:
            split = continue_at[0]
            prefix = body[:split]
            suffix = body[split + 1:]
            original = lines[start + 1:following]
            merged = [*prefix, *original]
            if suffix:
                end_section = [i for i, line in enumerate(original)
                               if line.split("#", 1)[0].strip() == "END_SECTION"]
                insert_at = len(merged) - len(original) + (end_section[-1] if end_section else len(original))
                merged[insert_at:insert_at] = suffix
            lines[start + 1:following] = merged
        else:
            # No continuation marker retains the established full-block replacement mode.
            lines[start + 1:following] = body
    return "\n".join(lines) + "\n"


def apply_map_mods(text: str, changes: dict, name: str) -> str:
    """Set fields on `warps` or `npcs` records, addressed by numeric index."""
    lines = text.splitlines()
    for collection, records in changes.items():
        if collection not in ("warps", "npcs") or not isinstance(records, dict):
            raise ValueError(f"{name}: expected warps/npcs objects")
        if collection == "npcs":
            remove = records.get("remove", [])
            additions = records.get("add", [])
            if not isinstance(remove, list) or not all(isinstance(i, int) and i >= 0 for i in remove):
                raise ValueError(f"{name}: npcs.remove must be an array of nonnegative indices")
            if not isinstance(additions, list) or not all(isinstance(npc, dict) for npc in additions):
                raise ValueError(f"{name}: npcs.add must be an array of NPC field objects")
            updates = {key: value for key, value in records.items() if key not in ("remove", "add")}
            for index, fields in updates.items():
                if not str(index).isdigit() or not isinstance(fields, dict):
                    raise ValueError(f"{name}: invalid NPC index/fields {index!r}")
                start = next((i for i, row in enumerate(lines)
                              if row.strip() == f"npc {index}"), None)
                if start is None:
                    raise ValueError(f"{name}: NPC {index} not found")
                end = _npc_block_end(lines, start)
                _set_npc_fields(lines, start, end, fields, name)
            if remove or additions:
                lines = _change_npc_set(lines, remove, additions, name)
            continue
        for index, fields in records.items():
            if not str(index).isdigit() or not isinstance(fields, dict):
                raise ValueError(f"{name}: invalid {collection} index/fields")
            record = "warp " if collection == "warps" else "npc "
            start = next((i for i, row in enumerate(lines)
                          if row.strip().startswith(record) and
                          row.strip().split()[1] == str(index)), None)
            if start is None:
                raise ValueError(f"{name}: {collection} record {index} not found")
            end = start + 1
            if collection == "npcs":
                while end < len(lines) and lines[end].strip() != ".end":
                    end += 1
            for field_name, value in fields.items():
                replacement = f"{field_name}={_format_value(value)}"
                search_start = start if collection == "warps" else start + 1
                match_line = next((i for i in range(search_start, end)
                                   if re.search(rf"(?:^|\s){re.escape(field_name)}=", lines[i])), None)
                if match_line is None:
                    raise ValueError(f"{name}: {collection} {index} has no field {field_name!r}")
                lines[match_line] = re.sub(rf"(?<!\S){re.escape(field_name)}=[^\s#]+", replacement, lines[match_line], count=1)
    return "\n".join(lines) + "\n"


NPC_REQUIRED = {"type", "follow", "pos", "rot", "track", "unk2", "script",
                "stats", "bits", "charge", "unk1", "moves", "prio", "flee", "ai"}


def _digimon_section(lines: list[str], name: str) -> tuple[int, int, int]:
    count_at = next((i for i, row in enumerate(lines) if re.match(r"\s*\.digimon\s+count=", row)), None)
    if count_at is None:
        raise ValueError(f"{name}: .digimon section not found")
    end = next((i for i in range(count_at + 1, len(lines)) if lines[i].strip() == ".end"), None)
    if end is None:
        raise ValueError(f"{name}: unterminated .digimon section")
    if any(row.strip() == ".tail" for row in lines[count_at + 1:end]):
        raise ValueError(f"{name}: cannot add/remove NPCs in an opaque .tail section")
    match = re.search(r"count=(\d+)", lines[count_at])
    return count_at, end, int(match.group(1))


def _npc_block_end(lines: list[str], start: int) -> int:
    return next((i for i in range(start + 1, len(lines))
                 if lines[i].strip().startswith("npc ") or lines[i].strip() == ".end"), len(lines))


def _set_npc_fields(lines: list[str], start: int, end: int, fields: dict, name: str) -> None:
    for field_name, value in fields.items():
        if field_name == "wp":
            continue
        replacement = f"{field_name}={_format_value(value)}"
        matched = [i for i in range(start + 1, end)
                   if re.search(rf"(?:^|\s){re.escape(field_name)}=", lines[i])]
        if not matched:
            raise ValueError(f"{name}: NPC {lines[start].strip()[4:]} has no field {field_name!r}")
        lines[matched[0]] = re.sub(rf"(?<!\S){re.escape(field_name)}=[^\s#]+", replacement,
                                   lines[matched[0]], count=1)
    if "wp" in fields:
        value = fields["wp"]
        if not isinstance(value, list) or any(not isinstance(wp, list) or len(wp) != 3 for wp in value):
            raise ValueError(f"{name}: NPC wp must be an array of 3-value arrays")
        matched = [i for i in range(start + 1, end) if re.match(r"\s*wp=", lines[i])]
        for i in reversed(matched):
            del lines[i]
        lines[start + 1:start + 1] = ["        wp=" + _format_value(wp) for wp in value]


def _change_npc_set(lines: list[str], remove: list[int], additions: list[dict], name: str) -> list[str]:
    count_at, section_end, count = _digimon_section(lines, name)
    starts = [i for i in range(count_at + 1, section_end) if re.match(r"\s*npc\s+\d+\s*$", lines[i])]
    if len(starts) != count:
        raise ValueError(f"{name}: count={count} but found {len(starts)} NPC blocks")
    if any(i >= count for i in remove):
        raise ValueError(f"{name}: remove index outside NPC list (count={count})")
    blocks: list[list[str]] = []
    for start, end in zip(starts, [*starts[1:], section_end]):
        blocks.append(lines[start:end])
    blocks = [block for index, block in enumerate(blocks) if index not in set(remove)]
    blocks.extend(_new_npc_block(fields, name) for fields in additions)
    for index, block in enumerate(blocks):
        block[0] = re.sub(r"npc\s+\d+", f"npc {index}", block[0])
    replacement = [line for block in blocks for line in block]
    lines[count_at] = re.sub(r"count=\d+", f"count={len(blocks)}", lines[count_at])
    lines[count_at + 1:section_end] = replacement
    return lines


def _new_npc_block(fields: dict, name: str) -> list[str]:
    missing = NPC_REQUIRED - fields.keys()
    unknown = fields.keys() - NPC_REQUIRED - {"wp"}
    if missing or unknown:
        raise ValueError(f"{name}: added NPC needs fields {sorted(missing)}; unknown fields {sorted(unknown)}")
    for field in NPC_REQUIRED:
        value = fields[field]
        if isinstance(value, bool) or not isinstance(value, (int, list)):
            raise ValueError(f"{name}: added NPC field {field} must be an integer or integer array")
    expected_lengths = {"pos": 3, "rot": 3, "stats": 8, "moves": 4, "prio": 4, "flee": 3, "ai": 8}
    for field, length in expected_lengths.items():
        if not isinstance(fields[field], list) or len(fields[field]) != length:
            raise ValueError(f"{name}: added NPC {field} must have {length} values")
    waypoints = fields.get("wp", [])
    if not isinstance(waypoints, list) or any(not isinstance(wp, list) or len(wp) != 3 for wp in waypoints):
        raise ValueError(f"{name}: added NPC wp must be an array of 3-value arrays")
    block = ["      npc 0"]
    for field in ("type", "follow", "pos", "rot", "track", "unk2", "script", "stats", "bits", "charge", "unk1", "moves", "prio", "flee", "ai"):
        block.append(f"        {field}={_format_value(fields[field])}")
    block.extend(f"        wp={_format_value(wp)}" for wp in waypoints)
    return block


def _format_value(value) -> str:
    if isinstance(value, list):
        return "(" + ",".join(_format_value(item) for item in value) + ")"
    if isinstance(value, int):
        return str(value)
    raise ValueError(f"field values must be integers or integer arrays, got {value!r}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scripts", type=Path)
    parser.add_argument("--maps", type=Path)
    parser.add_argument("--mods", type=Path, default=Path("mods"))
    args = parser.parse_args()
    if args.scripts:
        for filename in ("DG", "MAPHEAD"):
            path = args.scripts / f"{filename}.txt"
            for mod in sorted(args.mods.rglob("*.scnmod")):
                updated = apply_script_mod(path.read_text(encoding="utf-8"), mod)
                path.write_text(updated, encoding="utf-8")
    if args.maps:
        for mod in sorted(args.mods.rglob("*.maps.json")):
            data = json.loads(mod.read_text(encoding="utf-8"))
            for map_name, changes in data.items():
                path = args.maps / f"{map_name}.map.txt"
                if not path.is_file():
                    raise ValueError(f"{mod}: missing local source {path}")
                path.write_text(apply_map_mods(path.read_text(encoding="utf-8"), changes, map_name), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

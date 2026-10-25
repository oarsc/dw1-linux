#!/usr/bin/env python3
"""Tests for the readable .MAP assembler and disassembler."""

import re
import tempfile
import unittest
from pathlib import Path

import map_text
import scn_text

ROOT = Path(__file__).resolve().parent.parent
ORIGINALS = ROOT / "disc/extracted-maps"


def extracted_maps() -> list[Path]:
    if not ORIGINALS.is_dir():
        return []
    return sorted(ORIGINALS.rglob("*.MAP"))


def first_map_with_digimon() -> tuple[bytes, str] | None:
    for path in extracted_maps():
        data = path.read_bytes()
        name = path.name
        try:
            text = map_text.disassemble(data, name, base_file=name)
        except map_text.TextError:
            continue
        if "\n      npc 0\n" in text:
            return data, name
    return None


class RoundTripTests(unittest.TestCase):
    def test_all_maps_round_trip(self) -> None:
        found = extracted_maps()
        if not found:
            self.skipTest(
                "no extracted maps; run "
                "`cargo run -p pack --bin extract_maps -- --raw`"
            )
        for path in found:
            data = path.read_bytes()
            name = path.name
            text = map_text.disassemble(data, name, base_file=name)
            rebuilt = map_text.assemble(text, name, base_bytes=data)
            self.assertEqual(rebuilt, data, f"{name} must round-trip byte-exactly")

    def test_disassembly_is_stable(self) -> None:
        found = extracted_maps()
        if not found:
            self.skipTest("no extracted maps")
        for path in found[:40]:
            data = path.read_bytes()
            name = path.name
            text = map_text.disassemble(data, name, base_file=name)
            rebuilt = map_text.assemble(text, name, base_bytes=data)
            self.assertEqual(
                map_text.disassemble(rebuilt, name, base_file=name), text,
                f"{name} disassembly must be stable",
            )

    def test_npc_edit_is_reflected(self) -> None:
        sample = first_map_with_digimon()
        if sample is None:
            self.skipTest("no map with a placed digimon")
        data, name = sample
        text = map_text.disassemble(data, name, base_file=name)
        self.assertIn("track=", text)
        edited = text.replace("track=500", "track=999", 1)
        self.assertNotEqual(edited, text)
        rebuilt = map_text.assemble(edited, name, base_bytes=data)
        self.assertNotEqual(rebuilt, data)
        text2 = map_text.disassemble(rebuilt, name, base_file=name)
        self.assertIn("track=999", text2)

    def test_removing_an_npc_adjusts_the_table(self) -> None:
        sample = first_map_with_digimon()
        if sample is None:
            self.skipTest("no map with a placed digimon")
        data, name = sample
        text = map_text.disassemble(data, name, base_file=name)
        lines = text.splitlines()
        starts = [i for i, line in enumerate(lines)
                  if line.startswith("      npc ")]
        if len(starts) < 2:
            self.skipTest("need at least two NPCs")
        last = starts[-1]
        end = next(i for i in range(last, len(lines))
                   if lines[i] == "    .end")
        new_text = "\n".join(lines[:last] + lines[end:]) + "\n"
        old_count = re.search(r"\.digimon count=(\d+)", text)
        self.assertIsNotNone(old_count)
        new_count = int(old_count.group(1)) - 1
        new_text = re.sub(r"\.digimon count=\d+", f".digimon count={new_count}",
                          new_text, count=1)
        rebuilt = map_text.assemble(new_text, name, base_bytes=data)
        rebuilt_offsets, _ = map_text._offset_table(rebuilt, name)
        self.assertEqual(rebuilt_offsets[-1] + map_text.COLLISION_BYTES,
                         len(rebuilt))
        self.assertEqual(rebuilt[-map_text.COLLISION_BYTES:],
                         data[-map_text.COLLISION_BYTES:])
        text2 = map_text.disassemble(rebuilt, name, base_file=name)
        self.assertEqual(len([line for line in text2.splitlines()
                              if line.startswith("      npc ")]), new_count)

    def test_disc_base_reads_the_original(self) -> None:
        found = extracted_maps()
        if not found:
            self.skipTest("no extracted maps")
        disc = ROOT / "disc/Digimon World (USA).cue"
        if not disc.is_file():
            self.skipTest("no disc image")
        path = found[0]
        data = path.read_bytes()
        iso = f"/MAP/{path.parent.name}/{path.name}"
        text = map_text.disassemble(data, path.name, base_disc=iso)
        rebuilt = map_text.assemble(text, "test.txt", disc_path=str(disc))
        self.assertEqual(rebuilt, data)

    def test_batch_writes_only_edited_maps(self) -> None:
        found = extracted_maps()
        if len(found) < 2:
            self.skipTest("need at least two extracted maps")
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "source"
            output = Path(tmp) / "output"
            source.mkdir()
            names = []
            for path in found[:2]:
                data = path.read_bytes()
                text = map_text.disassemble(data, path.name, base_file=str(path))
                (source / f"{path.stem}.map.txt").write_text(text)
                names.append(path.stem)
            edited_path = source / f"{names[0]}.map.txt"
            text = edited_path.read_text()
            match = re.search(r"rot=0x([0-9a-f]{4})", text)
            self.assertIsNotNone(match)
            new_rot = "0000" if match.group(1) != "0000" else "0001"
            edited_path.write_text(
                text[: match.start(1)] + new_rot + text[match.end(1):]
            )
            written = map_text.batch_reassemble(source, output)
            self.assertEqual(written, [names[0]])
            self.assertTrue((output / f"{names[0]}.MAP").is_file())
            self.assertFalse((output / f"{names[1]}.MAP").exists())

    def test_tail_maps_round_trip(self) -> None:
        # YAKA22 is the one map whose entity section has an opaque tail.
        found = [p for p in extracted_maps() if p.name == "YAKA22.MAP"]
        if not found:
            self.skipTest("no YAKA22.MAP")
        path = found[0]
        data = path.read_bytes()
        text = map_text.disassemble(data, "YAKA22.MAP", base_file="YAKA22.MAP")
        self.assertIn(".tail", text)
        rebuilt = map_text.assemble(text, "YAKA22.MAP", base_bytes=data)
        self.assertEqual(rebuilt, data)


class NameTests(unittest.TestCase):
    def test_digimon_and_move_names_resolve(self) -> None:
        # The assembler accepts US names for npc type and moves.
        data, name = first_map_with_digimon() or (None, None)
        if data is None:
            self.skipTest("no map with a placed digimon")
        text = map_text.disassemble(data, name, base_file=name)
        # Replace the first npc's numeric type with a name and a move with a name.
        self.assertIn("type=", text)
        edited = text.replace("type=83", "type=ModokiBetamon", 1)
        edited = edited.replace("moves=(46,", "moves=(Megaton Punch,", 1)
        map_text.assemble(edited, name, base_bytes=data)

    def test_ambiguous_map_name_is_rejected(self) -> None:
        # YAKA25 is a filename shared by two MapEntry ids.
        with self.assertRaises(scn_text.TextError):
            scn_text.resolve_map("YAKA25", "test")

    def test_map_tables_parse(self) -> None:
        names, entries = map_text.D.map_entries()
        self.assertGreater(len(entries), 200)
        self.assertEqual(entries[0]["filename"], "MAYO01")
        self.assertEqual(entries[0]["display"], "Native Forest")


if __name__ == "__main__":
    unittest.main()

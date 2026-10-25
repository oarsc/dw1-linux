#!/usr/bin/env python3
"""Tests for the readable SCN assembler and disassembler."""

import re
import unittest
from pathlib import Path

import scn_dumper
import scn_text

ROOT = Path(__file__).resolve().parent.parent
ORIGINALS = ROOT / "disc/extracted-scripts/SCN"


def original(name: str) -> bytes | None:
    path = ORIGINALS / name
    return path.read_bytes() if path.is_file() else None


class RoundTripTests(unittest.TestCase):
    def test_maphead_round_trip(self) -> None:
        data = original("MAPHEAD.SCN")
        if data is None:
            self.skipTest("no extracted MAPHEAD.SCN")
        text = scn_text.disassemble_maphead(data)
        self.assertEqual(scn_text.assemble(text, "MAPHEAD.txt"), data)

    def test_maphead_text_is_stable(self) -> None:
        data = original("MAPHEAD.SCN")
        if data is None:
            self.skipTest("no extracted MAPHEAD.SCN")
        text = scn_text.disassemble_maphead(data)
        rebuilt = scn_text.assemble(text, "MAPHEAD.txt")
        self.assertEqual(scn_text.disassemble_maphead(rebuilt), text)

    def test_dg_round_trip(self) -> None:
        dg = original("DG.SCN")
        maphead = original("MAPHEAD.SCN")
        if dg is None or maphead is None:
            self.skipTest("no extracted DG.SCN/MAPHEAD.SCN")
        maphead_bytes = scn_text.assemble(
            scn_text.disassemble_maphead(maphead), "MAPHEAD.txt"
        )
        text = scn_text.disassemble_dg(dg)
        rebuilt = scn_text.assemble(
            text, "DG.txt", {"MAPHEAD": maphead_bytes}
        )
        self.assertEqual(rebuilt, dg)

    def test_dg_requires_maphead_for_map_zero(self) -> None:
        dg = original("DG.SCN")
        if dg is None:
            self.skipTest("no extracted DG.SCN")
        text = scn_text.disassemble_dg(dg)
        with self.assertRaises(scn_text.TextError):
            scn_text.assemble(text, "DG.txt")


class TableTests(unittest.TestCase):
    """The Rust assembler embeds the dumper's opcode tables; keep them in sync."""

    def test_rust_tables_match_the_python_dumper(self) -> None:
        source = (ROOT / "crates/script-format/src/lib.rs").read_text()

        def block(name: str) -> str:
            start = source.index(f"const {name}")
            return source[start : source.index("];", start)]

        opcodes = {
            name: int(code, 16)
            for name, code in re.findall(
                r'\("([A-Z0-9_]+)", (0x[0-9A-F]{2})\),', block("OPCODES")
            )
        }
        self.assertEqual(opcodes, {name: code for code, name in scn_dumper.OPCODES.items()})

        kinds = {
            "U8": "u8",
            "S8": "s8",
            "U16": "u16",
            "S16": "s16",
            "Id": "id",
            "Pstat": "pstat",
            "Pad": "_",
            "S32": "s32",
        }
        operands = {}
        for code, spec in re.findall(
            r"\(\s*(0x[0-9A-F]{2}),\s*&\[(.*?)\]\s*\)?\s*,",
            block("OPERANDS"),
            re.DOTALL,
        ):
            operands[int(code, 16)] = tuple(
                kinds[name] for name in re.findall(r"Operand::([A-Za-z0-9]+)", spec)
            )
        self.assertEqual(operands, scn_dumper.OPERANDS)

        digimon, _, moves, items = scn_dumper.game_tables()
        for constant, expected in (
            ("DIGIMON_NAMES", digimon),
            ("MOVE_NAMES", moves),
            ("ITEM_NAMES", items),
        ):
            names = {
                int(index, 16): name
                for index, name in re.findall(
                    r'\(0x([0-9A-F]{2}), "([^"]*)"\),', block(constant)
                )
            }
            self.assertEqual(names, expected)

        maps = scn_dumper.game_tables()[1]
        expected_maps = {}
        for index, entry in maps.items():
            filename, _, display = entry.partition(" — ")
            expected_maps[index] = (filename, display)
        rust_source = (ROOT / "crates/script-format/src/lib.rs").read_text()
        start = rust_source.index("const MAP_NAMES")
        rust_block = rust_source[start : rust_source.index("];", start)]
        rust_maps = {
            int(index, 16): (filename, display)
            for index, filename, display in re.findall(
                r'\(0x([0-9A-F]{2}), "([^"]*)", "([^"]*)"\),', rust_block
            )
        }
        self.assertEqual(rust_maps, expected_maps)

    def test_rust_ascii_table_matches_sjis_c(self) -> None:
        c_source = (ROOT / "decomp/src/main/sjis.c").read_text()
        start = c_source.index("CHAR_MAPPING_SPECIAL")
        c_block = c_source[start : c_source.index("};", start)]
        expected = {
            int(ascii_code, 16): int(jis, 16)
            for jis, ascii_code in re.findall(
                r"\{\s*(0x[0-9a-fA-F]+),\s*(0x[0-9a-fA-F]+)\s*\}", c_block
            )
        }
        rust_source = (ROOT / "crates/script-format/src/lib.rs").read_text()
        start = rust_source.index("const ASCII_SPECIAL")
        rust_block = rust_source[start : rust_source.index("];", start)]
        rust = {
            int(ascii_code, 16): int(jis, 16)
            for ascii_code, jis in re.findall(
                r"\(0x([0-9A-F]{2}), 0x([0-9A-F]{4})\)", rust_block
            )
        }
        self.assertEqual(rust, expected)


class ParseTests(unittest.TestCase):
    def minimal(self, body: str) -> str:
        return (
            "# DW1-SCN-TEXT 1\n"
            ".object MAPHEAD\n"
            "  .entries\n"
            "    0x000 -> head\n"
            "  .end\n"
            "head:\n"
            + body
            + ".end\n"
        )

    def test_unmappable_glyph_is_rejected(self) -> None:
        source = self.minimal('  .text\n    "\U0001f642"\n  .end\n')
        with self.assertRaisesRegex(scn_text.TextError, "CP932"):
            scn_text.assemble(source, "test.txt")

    def test_ascii_text_round_trips(self) -> None:
        phrase = "Probably. Anyway, I'll go"
        source = self.minimal(f'  .text\n    "{phrase}"\n  .end\n')
        data = scn_text.assemble(source, "test.txt")
        # 1a 00, then two bytes per glyph, then the 0d 00 00 00 terminator.
        expected = bytes.fromhex(
            "1a00"
            "826f8292828f828282818282828c8299"
            "81428140"
            "8260828e8299829782818299"
            "81438140"
            "82688175828c828c81408287828f"
            "0d000000"
        )
        self.assertEqual(data[8:], expected)
        # The disassembler shows the standard text, not the full-width glyphs.
        self.assertIn(phrase, scn_text.disassemble_maphead(data))

    def test_glyph_escape_round_trips(self) -> None:
        source = self.minimal('  .text\n    "{glyph:0000}Ａ"\n  .end\n')
        data = scn_text.assemble(source, "test.txt")
        self.assertEqual(data[:8], b"\x08\x00\x00\x00\x08\x00\xff\xff")
        self.assertEqual(data[0x08:0x0E], b"\x1a\x00\x00\x00\x82\x60")
        self.assertEqual(data[0x0E:0x12], b"\x0d\x00\x00\x00")

    def test_digimon_name_resolves_and_comments_are_ignored(self) -> None:
        source = self.minimal(
            "  LOAD_DIGIMON digimon=Agumon  # Agumon\n  END_SCRIPT\n"
        )
        data = scn_text.assemble(source, "test.txt")
        self.assertEqual(data[8:12], b"\x46\x03\xff\x00")

    def test_quoted_digimon_name_resolves(self) -> None:
        source = self.minimal(
            '  LOAD_DIGIMON digimon="King of Sukamon"\n  END_SCRIPT\n'
        )
        data = scn_text.assemble(source, "test.txt")
        self.assertEqual(data[8:12], b"\x46\x78\xff\x00")

    def test_item_and_move_names_resolve(self) -> None:
        source = self.minimal(
            '  GIVE_ITEM item="Blue Flute" amount=0x01\n'
            '  LEARN_MOVE move=Fire_Tower\n'
            '  END_SCRIPT\n'
        )
        data = scn_text.assemble(source, "test.txt")
        self.assertEqual(data[8:12], b"\x28\x00\x73\x01")
        self.assertEqual(data[12:16], b"\x2d\x00\xff\x00")

    def test_item_condition_name_resolves(self) -> None:
        source = self.minimal(
            '  .if\n'
            '    THEN item "Gold banana" >= 0x0001\n'
            '  .end\n'
        )
        data = scn_text.assemble(source, "test.txt")
        self.assertEqual(data[8:16], b"\x19\x00\x24\x00\x6d\x02\x01\x00")

    def test_ambiguous_move_name_is_rejected(self) -> None:
        source = self.minimal("  LEARN_MOVE move=Dynamite_Kick\n")
        with self.assertRaisesRegex(scn_text.TextError, "ambiguous"):
            scn_text.assemble(source, "test.txt")

    def test_pstat_annotations(self) -> None:
        source = self.minimal(
            "  SET_PSTAT pstat=0xf3 value=0x03\n"
            "  STORE_DATE pstat_date=0x69\n"
            "  .if\n"
            "    THEN pstat 0x6b <= 0x06\n"
            "    AND pstat 0xf3 >= 0x02\n"
            "  .end\n"
        )
        data = scn_text.assemble(source, "test.txt")
        text = scn_text.disassemble_maphead(data)
        self.assertIn("SET_PSTAT pstat=0xf3 value=0x03  # shop variable high byte", text)
        self.assertIn("STORE_DATE pstat_date=0x69  # date (year,day,hour,minute)", text)
        self.assertIn("THEN pstat 0x6b <= 0x06  # date hour", text)
        self.assertIn("AND pstat 0xf3 >= 0x02  # shop variable high byte", text)

    def test_pstat_report(self) -> None:
        source = (
            ".map 49  # screen 49: GCAN11 — Monochrome Shop\n"
            "m49_b740:\n"
            "  SET_PSTAT pstat=0xf3 value=0x03\n"
            "  STORE_DATE pstat_date=0x69\n"
            "  .if\n"
            "    THEN pstat 0xf3 <= 0x06\n"
            "  .end\n"
        )
        report = scn_text.pstat_report(source, 0xF3)
        self.assertIn("pstat 0xf3: shop variable high byte", report)
        self.assertIn("CALL_ROUTINE builtin=0x38", report)
        self.assertIn("SET_PSTAT pstat=0xf3 value=0x03", report)
        self.assertIn("THEN pstat 0xf3 <= 0x06", report)
        date = scn_text.pstat_report(source, 0x6A)
        self.assertIn("date day", date)
        self.assertIn("date field 1", date)

    def test_map_names_resolve(self) -> None:
        source = self.minimal(
            '  WARP_TO map=MAYO02_2 exit=0x03 section=0xff\n  END_SCRIPT\n'
        )
        data = scn_text.assemble(source, "test.txt")
        self.assertEqual(data[8:12], b"\x4b\x6f\x03\xff")
        with self.assertRaisesRegex(scn_text.TextError, "ambiguous"):
            scn_text.assemble(
                self.minimal(
                    '  WARP_TO map="Native Forest" exit=0x03 section=0xff\n'
                ),
                "test.txt",
            )

    def test_ambiguous_digimon_name_is_rejected(self) -> None:
        source = self.minimal("  LOAD_DIGIMON digimon=Greymon\n")
        with self.assertRaisesRegex(scn_text.TextError, "ambiguous"):
            scn_text.assemble(source, "test.txt")

    def test_unknown_mnemonic_is_rejected(self) -> None:
        source = self.minimal("  NOT_AN_OPCODE\n")
        with self.assertRaisesRegex(scn_text.TextError, "unknown mnemonic"):
            scn_text.assemble(source, "test.txt")

    def test_branch_targets_resolve(self) -> None:
        source = self.minimal("  JUMP_TO head+0x04\n  END_SCRIPT\n")
        data = scn_text.assemble(source, "test.txt")
        # Table is 2 + 4 + 2 = 8 bytes, so `head` is at 0x08 and head+4 is 0x0c.
        self.assertEqual(data[8:12], b"\x16\x00\x0c\x00")
        self.assertEqual(data[12:14], b"\xff\x00")


if __name__ == "__main__":
    unittest.main()

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import scn_dumper as dump


class ScnDumperTests(unittest.TestCase):
    def test_map_offsets_stop_at_terminal_file_offset(self):
        data = bytearray(20)
        for i, value in enumerate((4, 12, 20)):
            data[i * 4 : i * 4 + 4] = value.to_bytes(4, "little")
        # Bytes after the terminal offset are not extra table entries.
        data[12:16] = (0x4E4F4953).to_bytes(4, "little")
        self.assertEqual(dump.parse_dg_offsets(bytes(data)), [4, 12, 20])

    def test_map_offsets_reject_nonterminal_prefix(self):
        data = bytearray(20)
        for i, value in enumerate((4, 12, 0xFFFFFFFF)):
            data[i * 4 : i * 4 + 4] = value.to_bytes(4, "little")
        with self.assertRaises(dump.ScnError):
            dump.parse_dg_offsets(bytes(data))

    def test_section_table_uses_script_relative_offsets(self):
        data = bytes((10, 0, 5, 0, 10, 0, 0xFF, 0xFF, 0, 0, 0xFE))
        self.assertEqual(dump.section_table(data, 0, len(data)), [(5, 10)])

    def test_if_decoder_reads_conditions_and_conditional_destinations(self):
        # IF, padding, pstat comparison, conditional jump, IF terminator.
        encoded = bytes((0x19, 0, 0x0A, 0, 5, 2, 0x90, 0, 0x34, 0x12, 0x19, 0))
        end, lines = dump.decode_if(encoded, 0, len(encoded))
        self.assertEqual(end, len(encoded))
        self.assertEqual(lines, ["THEN pstat[5] >= 2 (0x02)", "AND if true then goto script+0x1234 (@0x001234)"])

    def test_if_decodes_item_and_move_names(self):
        # item count >= 2, then branch-if-false to script offset 0x20.
        encoded = bytes((0x19, 0, 0x24, 0, 7, 2, 2, 0, 0x18, 0, 0x30, 0, 0x19, 0))
        end, lines = dump.decode_if(encoded, 0, len(encoded), move_names={2: "Fire Tower"}, item_names={7: "Meat"})
        self.assertEqual(end, len(encoded))
        self.assertEqual(lines, ["THEN item_count[7 (Meat)] >= 2", "THEN if false then goto script+0x0030 (@0x000030)"])

    def test_cp932_half_width_and_full_width_text(self):
        data = "ｶﾀｶﾅＡ".encode("cp932")
        self.assertEqual(dump.decode_text(data, 0, len(data)), "カタカナA")

    def test_text_newline_is_a_real_line_break(self):
        data = b"First\r\x00Second"
        self.assertEqual(dump.decode_text(data, 0, len(data)), "First\nSecond")

    def test_digimon_names_follow_data_table_order(self):
        names, _, _, _ = dump.game_tables()
        if not (Path(__file__).resolve().parents[1] / "decomp/src/main/main.c").is_file():
            self.skipTest("decomp submodule is not initialized")
        self.assertEqual(names[3], "Agumon")
        self.assertEqual(len(names), 180)

    def test_digimon_instruction_gets_symbolic_label(self):
        args = [("u8", 3)]
        self.assertEqual(
            dump.format_args(0x46, args, {3: "Agumon"}, {}, {}, {}),
            "digimon=3/0x03 (Agumon)",
        )

    def test_ordered_yaml_tables_preserve_indices(self):
        moves = dump.ordered_yaml_names(dump.ROOT / "decomp/text/main/item.yaml", "MOVE_NAMES")
        items = dump.ordered_yaml_names(dump.ROOT / "decomp/text/main/item.yaml", "ITEM_NAMES")
        self.assertEqual(moves[0], "Fire Tower")
        self.assertIn("sm.recovery", items.values())

    def test_instruction_arguments_are_descriptive(self):
        self.assertEqual(
            dump.format_args(0x74, [("u8", 2), ("s16", -12), ("s16", 35)], {}, {}, {}, {2: "Meat"}),
            "item=0x02 (Meat), x=-12, z=35",
        )
        self.assertIn(
            "stat=OFFENSE (0x0), value=5 (0x5)",
            dump.format_args(0x34, [("u8", 0), ("u16", 5)], {}, {}, {}, {}),
        )


if __name__ == "__main__":
    unittest.main()

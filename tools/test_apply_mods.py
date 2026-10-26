import tempfile
import unittest
from pathlib import Path

import apply_mods


class ModTests(unittest.TestCase):
    def test_script_label_replacement_and_maphead_entry(self):
        source = """# DW1-SCN-TEXT 1
.object MAPHEAD
  .entries
    0x001 -> old
  .end
old:
  END_SECTION
.end
"""
        with tempfile.TemporaryDirectory() as tmp:
            mod = Path(tmp) / "sample.scnmod"
            mod.write_text("""@ MAPHEAD entries
0x001 -> custom
0x004 -> MAPHEAD_custom1

@ MAPHEAD old
  RETURN

@ MAPHEAD MAPHEAD_custom1
  END_SECTION
""")
            result = apply_mods.apply_script_mod(source, mod)
        self.assertIn("0x001 -> custom", result)
        self.assertIn("0x004 -> MAPHEAD_custom1", result)
        self.assertIn("old:\n  RETURN", result)
        self.assertIn("MAPHEAD_custom1:\n  END_SECTION", result)

    def test_add_map_section_and_maphead_entry_section(self):
        dg = """# DW1-SCN-TEXT 1
.scn DG
.header
  .offsets
  .names
    "x"
  .end
  .bytes 00 00 00 00
.end
.map 1
  .entries
    0x001 -> m1_s0
  .end
m1_s0:
  END_SECTION
.end
"""
        maphead = """# DW1-SCN-TEXT 1
.object MAPHEAD
  .entries
    0x001 -> MAPHEAD_s0
  .end
MAPHEAD_s0:
  END_SECTION
.end
"""
        with tempfile.TemporaryDirectory() as tmp:
            mod = Path(tmp) / "add.scnmod"
            mod.write_text("""+ DG map 1 section m1_b3a_new
  END_SECTION

+ MAPHEAD entry 0x4e5 -> MAPHEAD_custom1
  SET_BGM bgm=0x01
  END_SECTION
""")
            updated_dg = apply_mods.apply_script_mod(dg, mod)
            updated_head = apply_mods.apply_script_mod(maphead, mod)
        self.assertIn("m1_b3a_new:\n  END_SECTION", updated_dg)
        self.assertIn("0x4e5 -> MAPHEAD_custom1", updated_head)
        self.assertIn("MAPHEAD_custom1:\n  SET_BGM", updated_head)

    def test_maphead_plus_entry_replaces_existing_id(self):
        source = """# DW1-SCN-TEXT 1
.object MAPHEAD
  .entries
    0x004e5 -> original
  .end
original:
  END_SECTION
.end
"""
        with tempfile.TemporaryDirectory() as tmp:
            mod = Path(tmp) / "replace.scnmod"
            mod.write_text("""+ MAPHEAD entry 0x4e5 -> custom
  END_SECTION
""")
            result = apply_mods.apply_script_mod(source, mod)
        self.assertEqual(result.count("0x4e5 -> custom"), 1)
        self.assertNotIn("0x004e5 -> original", result)

    def test_delete_dg_section_removes_entry_and_body(self):
        source = """# DW1-SCN-TEXT 1
.scn DG
.map 49
  .entries
    0x001 -> m49_s0
    0x002 -> m49_s1
  .end
m49_s0:
  END_SECTION
m49_s1:
  SET_BGM bgm=0x01
  END_SECTION
.end
"""
        with tempfile.TemporaryDirectory() as tmp:
            mod = Path(tmp) / "delete.scnmod"
            mod.write_text("- DG m49_s1\n")
            result = apply_mods.apply_script_mod(source, mod)
        self.assertIn("0x001 -> m49_s0", result)
        self.assertNotIn("0x002 -> m49_s1", result)
        self.assertNotIn("m49_s1:", result)
        self.assertNotIn("SET_BGM bgm=0x01", result)

    def test_delete_dg_internal_label_does_not_remove_other_blocks(self):
        source = """# DW1-SCN-TEXT 1
.scn DG
.map 49
  .entries
    0x001 -> m49_s0
  .end
m49_s0:
  END_SECTION
m49_b1:
  SET_BGM bgm=0x01
m49_b2:
  END_SECTION
.end
"""
        with tempfile.TemporaryDirectory() as tmp:
            mod = Path(tmp) / "delete.scnmod"
            mod.write_text("- DG m49_b1\n")
            result = apply_mods.apply_script_mod(source, mod)
        self.assertIn("0x001 -> m49_s0", result)
        self.assertNotIn("m49_b1:", result)
        self.assertNotIn("SET_BGM bgm=0x01", result)
        self.assertIn("m49_b2:\n  END_SECTION", result)

    def test_delete_dg_requires_existing_label_and_no_body(self):
        source = """# DW1-SCN-TEXT 1
.scn DG
.map 49
  .entries
  .end
.end
"""
        with tempfile.TemporaryDirectory() as tmp:
            mod = Path(tmp) / "delete.scnmod"
            mod.write_text("- DG missing\n")
            with self.assertRaisesRegex(ValueError, "found 0"):
                apply_mods.apply_script_mod(source, mod)
            mod.write_text("- DG missing\n  END_SECTION\n")
            with self.assertRaisesRegex(ValueError, "does not take a body"):
                apply_mods.apply_script_mod(source, mod)

    def test_function_call_expands_named_arguments_and_nested_end(self):
        source = """# DW1-SCN-TEXT 1
.scn DG
.map 49
  .entries
    0x001 -> m49_ba14
  .end
m49_ba14:
  END_SECTION
m49_bacc:
  END_SECTION
.end
"""
        with tempfile.TemporaryDirectory() as tmp:
            mod = Path(tmp) / "function.scnmod"
            mod.write_text("""@ DG m49_ba14
  .if
    THEN pstat 0xf3 >= 0x07
    CALL_FUNCTION showEmote entity=0x06 mood=0x05 # add emote
  .end
  ~CONTINUE

+ FUNCTION showEmote entity mood
  .if
    THEN pstat $entity >= $mood
  .end
  SET_PSTAT pstat=0xf7 value=$entity
  SET_PSTAT pstat=0xf8 value=$mood
.end
""")
            result = apply_mods.apply_script_mod(source, mod)
        self.assertIn("pstat 0x06 >= 0x05", result)
        self.assertIn("pstat=0xf7 value=0x06", result)
        self.assertIn("pstat=0xf8 value=0x05", result)
        self.assertNotIn("CALL_FUNCTION", result)
        self.assertNotIn("$entity", result)
        self.assertLess(result.index("pstat=0xf8 value=0x05"), result.index("END_SECTION"))

    def test_function_call_checks_arguments_and_recursion(self):
        source = """# DW1-SCN-TEXT 1
.scn DG
.map 1
  .entries
  .end
label:
  END_SECTION
.end
"""
        with tempfile.TemporaryDirectory() as tmp:
            mod = Path(tmp) / "function.scnmod"
            mod.write_text("""@ DG label
  CALL_FUNCTION f value=1

+ FUNCTION f value
  CALL_FUNCTION f value=$value
.end
""")
            with self.assertRaisesRegex(ValueError, "recursive function"):
                apply_mods.apply_script_mod(source, mod)

            mod.write_text("""@ DG label
  CALL_FUNCTION f

+ FUNCTION f value
  SET_PSTAT pstat=0xf7 value=$value
.end
""")
            with self.assertRaisesRegex(ValueError, "argument mismatch"):
                apply_mods.apply_script_mod(source, mod)

    def test_function_arguments_support_quoted_text_and_escaped_quotes(self):
        source = """# DW1-SCN-TEXT 1
.scn DG
.map 1
  .entries
  .end
label:
  END_SECTION
.end
"""
        with tempfile.TemporaryDirectory() as tmp:
            mod = Path(tmp) / "quoted.scnmod"
            mod.write_text(r'''@ DG label
  CALL_FUNCTION showText text="Let me rethink this"
  CALL_FUNCTION addOption selectionOption="\"Let me rethink this\" -> m1_b2" # option

+ FUNCTION showText text
  .text
    "$text"
  .end
.end

+ FUNCTION addOption selectionOption
  $selectionOption
.end
''')
            result = apply_mods.apply_script_mod(source, mod)
        self.assertIn('"Let me rethink this"', result)
        self.assertIn('"Let me rethink this" -> m1_b2', result)
        self.assertNotIn("CALL_FUNCTION", result)

    def test_nested_function_forwards_decoded_multiline_argument_without_retokenizing(self):
        source = """# DW1-SCN-TEXT 1
.scn DG
.map 199
  .entries
  .end
m199_test:
  END_SECTION
.end
"""
        with tempfile.TemporaryDirectory() as tmp:
            mod = Path(tmp) / "nested.scnmod"
            mod.write_text(r'''@ DG m199_test
  CALL_FUNCTION doSomething option="\"Let me rethink this\" -> m199_test"

+ FUNCTION doSomething option
  .selection
    $option
  .end
  CALL_FUNCTION doSomething2 option=$option
.end

+ FUNCTION doSomething2 option
  .selection
    $option
  .end
.end
''')
            result = apply_mods.apply_script_mod(source, mod)
        self.assertEqual(result.count('"Let me rethink this" -> m199_test'), 2)
        self.assertNotIn("CALL_FUNCTION", result)

    def test_constants_expand_in_code_and_function_arguments_regardless_of_order(self):
        source = """# DW1-SCN-TEXT 1
.scn DG
.map 1
  .entries
  .end
label:
  END_SECTION
next:
  END_SECTION
.end
"""
        with tempfile.TemporaryDirectory() as tmp:
            mod = Path(tmp) / "constants.scnmod"
            mod.write_text(r'''@ DG label
  SET_PSTAT pstat=$FIELD value=0x03
  .text
    "$NAME"
  .end
  CALL_FUNCTION choose option=$OPTION

+ FUNCTION choose option
  .selection
    $option
  .end
.end

+ CONST FIELD 0xf7
+ CONST NAME "Pepito"
+ CONST OPTION "\"Selectable option\" -> next"
''')
            result = apply_mods.apply_script_mod(source, mod)
        self.assertIn("SET_PSTAT pstat=0xf7 value=0x03", result)
        self.assertIn('"Pepito"', result)
        self.assertIn('"Selectable option" -> next', result)
        self.assertNotIn("$FIELD", result)
        self.assertNotIn("CALL_FUNCTION", result)

    def test_constants_reject_duplicate_and_unterminated_definitions(self):
        source = """# DW1-SCN-TEXT 1
.scn DG
.map 1
  .entries
  .end
label:
  END_SECTION
.end
"""
        with tempfile.TemporaryDirectory() as tmp:
            mod = Path(tmp) / "constants.scnmod"
            mod.write_text("""+ CONST VALUE 1
+ CONST VALUE 2
""")
            with self.assertRaisesRegex(ValueError, "duplicate constant"):
                apply_mods.apply_script_mod(source, mod)

            mod.write_text("""+ CONST VALUE "unterminated
""")
            with self.assertRaisesRegex(ValueError, "unterminated quote"):
                apply_mods.apply_script_mod(source, mod)

    def test_continue_injects_before_and_before_end_section(self):
        source = """# DW1-SCN-TEXT 1
.object MAPHEAD
  .entries
    0x001 -> block
  .end
block:
  SET_BGM bgm=0x01
  END_SECTION
.end
"""
        with tempfile.TemporaryDirectory() as tmp:
            mod = Path(tmp) / "inject.scnmod"
            mod.write_text("""@ MAPHEAD block
  SET_TRIGGER trigger=0x0001
  ~CONTINUE
  SET_TRIGGER trigger=0x0002
""")
            result = apply_mods.apply_script_mod(source, mod)
        self.assertLess(result.index("SET_TRIGGER trigger=0x0001"), result.index("SET_BGM"))
        self.assertLess(result.index("SET_BGM"), result.index("SET_TRIGGER trigger=0x0002"))
        self.assertLess(result.index("SET_TRIGGER trigger=0x0002"), result.index("END_SECTION"))

    def test_continue_appends_when_original_has_no_end_section(self):
        source = """# DW1-SCN-TEXT 1
.object MAPHEAD
  .entries
    0x001 -> block
  .end
block:
  SET_BGM bgm=0x01
.end
"""
        with tempfile.TemporaryDirectory() as tmp:
            mod = Path(tmp) / "inject.scnmod"
            mod.write_text("""@ MAPHEAD block
  ~CONTINUE
  SET_TRIGGER trigger=0x0002
""")
            result = apply_mods.apply_script_mod(source, mod)
        self.assertLess(result.index("SET_BGM"), result.index("SET_TRIGGER"))

    def test_continue_rejects_duplicate_markers(self):
        source = """# DW1-SCN-TEXT 1
.object MAPHEAD
  .entries
    0x001 -> block
  .end
block:
  END_SECTION
.end
"""
        with tempfile.TemporaryDirectory() as tmp:
            mod = Path(tmp) / "inject.scnmod"
            mod.write_text("""@ MAPHEAD block
  ~CONTINUE
  SET_TRIGGER trigger=0x0001
  ~CONTINUE
""")
            with self.assertRaisesRegex(ValueError, "more than one"):
                apply_mods.apply_script_mod(source, mod)

    def test_map_field_overrides(self):
        source = """# DW1-MAP-TEXT 1
.entities
  .warps
    warp 0 spawn=(1,2,3) rot=0x0000 target=2 exit=0
  .end
  .digimon count=1
    npc 0
      pos=(1,2,3)
      rot=(0,0,0)
  .end
.end
"""
        result = apply_mods.apply_map_mods(source, {
            "warps": {"0": {"spawn": [4, 5, 6]}},
            "npcs": {"0": {"wp": [[1, 2, 3]], "pos": [7, 8, 9]}},
        }, "TEST")
        self.assertIn("spawn=(4,5,6)", result)
        self.assertIn("pos=(7,8,9)", result)
        self.assertIn("wp=(1,2,3)", result)

    def test_map_npc_add_remove(self):
        npc = {
            "type": 2, "follow": 1, "pos": [1, 2, 3], "rot": [0, 512, 0],
            "track": 500, "unk2": 0, "script": 0,
            "stats": [100, 100, 100, 100, 10, 10, 10, 10], "bits": 0,
            "charge": 1, "unk1": 0, "moves": [1, 2, 3, 255],
            "prio": [50, 30, 20, 0], "flee": [0, 0, 0],
            "ai": [0, -1, -1, -1, -1, -1, -1, -1], "wp": [[10, 0, 0]],
        }
        source = """# DW1-MAP-TEXT 1
.map TEST
  .entities
    .warps
      warp 0 spawn=(1,2,3) rot=0 target=0 exit=0
    .end
    .digimon count=1
      npc 0
        type=1
    .end
  .end
.end
"""
        added = apply_mods.apply_map_mods(source, {"npcs": {"add": [npc]}}, "TEST")
        self.assertIn(".digimon count=2", added)
        self.assertIn("npc 1", added)
        self.assertIn("wp=(10,0,0)", added)
        removed = apply_mods.apply_map_mods(added, {"npcs": {"remove": [0]}}, "TEST")
        self.assertIn(".digimon count=1", removed)
        self.assertIn("npc 0", removed)
        self.assertIn("type=2", removed)


if __name__ == "__main__":
    unittest.main()

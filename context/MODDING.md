# Modding and script extraction

Mods are author-supplied changes only; do not include extracted game data in a mod or commit it
to the repository. The build applies mods to fresh temporary text generated from the user's own
disc. `scripts/` is gitignored, optional reference material: neither `scripts/*.txt` nor
`scripts/maps/` is read by the build, and no files need to be extracted there before building.

Mods can be stored in subdirectories under `mods/`; the build discovers `*.scnmod` and
`*.maps.json` files recursively. Missing targets, unknown fields, and malformed mod data make the
build fail rather than being silently ignored.

## Extract optional references

Use a legal game disc image in `disc/` (the default is
`disc/Digimon World (USA).cue` and its `.bin`), or set `DW1_DISC` to a CUE or BIN path. Extraction
reads the disc and does not modify it. Run the commands from the repository root.

### Scene scripts

The SCN files contain the map scripts, section tables, and dialogue. The default extraction reads
`MAPHEAD.SCN` and `DG.SCN` and writes readable assembler text; it does not write binary SCN files:

```sh
./tools/do cargo run -p pack --bin extract_scripts -- "disc/Digimon World (USA).cue" scripts
```

This creates `scripts/MAPHEAD.txt` and `scripts/DG.txt`. These are useful for looking up labels,
branches, instructions, and dialogue while authoring mods. The text format is an assembler and
round-trips to the original SCN bytes. `DG.txt` contains per-map section tables and labeled code;
`MAPHEAD.txt` contains the map-header section table and code.

To extract the original binary `.SCN` files instead, add `--raw` flag.

### Map files

MAP files contain both editable entity data (player warps and placed Digimon/NPCs) and binary
sections such as textures, collision, and camera/light data. Extract readable references for all
maps with:

```sh
./tools/do cargo run -p pack --bin extract_maps -- "disc/Digimon World (USA).cue" scripts/maps
```

This writes `scripts/maps/NAME.map.txt` files, with no binary companion. The text contains the
map name, warps, and NPC placements; its `.base disc` line points to the original MAP so the other
binary sections can be read when assembling.

Flag `--raw` can be used to extract original binary `.MAP` files instead.

As for scene scripts, these full text extracts are just for reference for MOD buuilding.

## Mod creation

### Scene-script mods (`*.scnmod`)

An `@ FILE LABEL` block targets `DG` or `MAPHEAD`. It replaces the body after that label up to the
next label or the containing object's `.end`. Keep the label when replacing a section so existing
branches continue to point to it. The body is ordinary SCN text with its normal indentation.

To inject code around the original body instead of replacing it, put one `~CONTINUE` marker in
the override. Lines before it are inserted before the original body. Lines after it are inserted
after the original body, but before its `END_SECTION` if present; if there is no `END_SECTION`,
they are appended to the body. More than one marker in a block is an error. Without the marker,
`@` retains its full-body replacement behavior.

```text
@ DG m112_sfc
  DO_SOMETHING_BEFORE_START_HERE
  ~CONTINUE
  DO_SOMETHING_AFTER_END_HERE
```

To add a new section to a DG map, use `+ DG map ID section LABEL`. The new label can be referenced
from other modded code:

```text
+ DG map 1 section m1_b3a_new
  END_SECTION
```

To remove a DG label block, use `- DG LABEL`. The block runs from that label up to the next label
or the containing map's `.end`; any `.entries` row in that map that targets the label is removed
as well. Assembly fails if remaining code still refers to the deleted label, so update or remove
those branches/calls too. Deletion does not analyze fall-through control flow; only remove a block
after checking that execution cannot reach it unintentionally.

```text
- DG m49_bacc
```

For MAPHEAD, `@ MAPHEAD entries` can add or replace `ID -> LABEL` lookup rows. A new section can
be defined by `@ MAPHEAD LABEL`; if the label does not already exist, it is added to the MAPHEAD
object. To add a MAPHEAD entry and its section together, use `+ MAPHEAD entry ID -> LABEL` followed
by the section body. An existing entry with the same ID is redirected to the new label.

```text
@ MAPHEAD entries
0x4e5 -> MAPHEAD_custom1

@ MAPHEAD MAPHEAD_custom1
  END_SECTION

+ MAPHEAD entry 0x4e6 -> MAPHEAD_custom2
  SET_BGM bgm=0x01
  END_SECTION
```

#### Constants

Define a compile-time text constant with `+ CONST NAME VALUE`, then use `$NAME` in SCN code or
function arguments. Definitions are local to the `.scnmod` file and may appear before or after
their use. Values use the same quoting and escaping rules as function arguments; quote values that
contain spaces. Constants are textual substitutions, not run-time variables. Within a function, a
parameter takes precedence over a constant with the same name.

```text
+ CONST VALUE 0xf3
+ CONST DIGIMON_NAME "Agumon"
+ CONST OPTION "\"Selectable option\" -> m199_section"

@ DG m199_section
  SET_PSTAT pstat=0xf9 value=$VALUE
  .text
    "$DIGIMON_NAME"
  .end
  .selection
    $OPTION
  .end
```

#### Functions

SCN mods can also define reusable, compile-time code templates with `+ FUNCTION NAME PARAM ...`
and call them with `CALL_FUNCTION NAME param=value ...`. A call is replaced inline with the function
body; `$param` placeholders are substituted with the supplied values. Define and call functions
within the same `.scnmod` file. Calls may appear before their definitions, and templates may call
other templates; recursive calls and missing/extra arguments are errors. Arguments are
whitespace-separated single tokens (for example, `entity=0x06`). Close the definition with an
unindented `.end`; indented `.end` lines inside SCN constructs such as `.if` remain part of the
function body.

```text
@ DG m49_ba14
  .if
    THEN pstat 0xf3 >= 0x07
    CALL_FUNCTION showEmote entity=0x06 mood=0x05
  .end
  ~CONTINUE

+ FUNCTION showEmote entity mood
  SET_PSTAT pstat=0xf7 value=$entity
  SET_PSTAT pstat=0xf8 value=$mood
  CALL_ROUTINE builtin=0x1c
.end
```

Quoted arguments can also carry a text or a complete SCN line. Escape its inner quotes so the argument
parser keeps the line together, then insert it without adding more quotes in the function body:

```text
@ DG m199_ba14
  CALL_FUNCTION addOption text="Let me rethink this"

+ FUNCTION addOption text
  .selection
    "$text" -> m199_meat_decide
  .end
.end
```

Escaping with `\"` or `\\\"` is supported.


### Map field mods (`*.maps.json`)

Each JSON object is keyed by map filename (for example `TRAI00`), then by `warps` or `npcs`,
then by the zero-based record index and fields to edit. Values are integers or integer arrays in
the field's expected shape. NPC updates are field-level edits; `wp` replaces that NPC's waypoint
list and is an array of three-value arrays.

```json
{
  "TRAI00": {
    "warps": {
      "0": { "spawn": [4, 5, 6] }
    },
    "npcs": {
      "0": { "pos": [123, 0, 456], "rot": [0, 512, 0] }
    }
  }
}
```

NPC changes can also remove original indices or append complete records in the same `npcs`
object. A new record must provide `type`, `follow`, `pos`, `rot`, `track`, `unk2`, `script`,
`stats`, `bits`, `charge`, `unk1`, `moves`, `prio`, `flee`, and `ai`; `wp` is optional and defaults
to an empty list. The expected array lengths are: `pos`/`rot`/`flee` 3, `stats`/`ai` 8, and
`moves`/`prio` 4. Updates are applied first, removals use the original indices, and additions are
appended after removals. Remaining NPCs are renumbered and the `.digimon count` is updated.

```json
{
  "TRAI00": {
    "npcs": {
      "0": { "pos": [123, 0, 456] },
      "remove": [1],
      "add": [{
        "type": 2, "follow": 1, "pos": [10, 0, 20], "rot": [0, 0, 0],
        "track": 0, "unk2": 0, "script": 0,
        "stats": [100, 100, 100, 100, 10, 10, 10, 10], "bits": 0,
        "charge": 0, "unk1": 0, "moves": [255, 255, 255, 255],
        "prio": [0, 0, 0, 0], "flee": [0, 0, 0],
        "ai": [-1, -1, -1, -1, -1, -1, -1, -1], "wp": []
      }]
    }
  }
}
```

NPC addition/removal is not supported for maps whose entity section is an opaque `.tail`
(currently YAKA22).

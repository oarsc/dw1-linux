//! Assemble the editable scene-script text.
//!
//! `tools/scn_text.py` generates these sources from the player's own disc; the build creates
//! temporary copies, applies mods, and assembles them. This crate is also used by the round-trip
//! tests. The format is a textual assembler (maps, section
//! tables, instructions, labels, dialog text) and reassembles to the original
//! bytes exactly.

use std::collections::HashMap;

use encoding_rs::SHIFT_JIS;

const HEADER: &str = "# DW1-SCN-TEXT 1";
const DG_HEADER_SIZE: usize = 0x800;
const DG_OFFSET_ENTRIES: usize = 223;
const DG_NAMES_OFFSET: usize = 0x37C;
const DG_NAMES_COUNT: usize = 36;

#[derive(Clone, Copy, PartialEq, Eq, Debug)]
pub(crate) enum Operand {
    U8,
    S8,
    U16,
    S16,
    Id,
    Pstat,
    Pad,
    S32,
}

impl Operand {
    fn width(self) -> usize {
        match self {
            Operand::U8 | Operand::S8 | Operand::Id | Operand::Pstat | Operand::Pad => 1,
            Operand::U16 | Operand::S16 => 2,
            Operand::S32 => 4,
        }
    }

    fn signed(self) -> bool {
        matches!(self, Operand::S8 | Operand::S16 | Operand::S32)
    }
}

pub(crate) const OPCODES: &[(&str, u8)] = &[
    ("ADD_MERIT", 0x32),
    ("ADD_MINUTES_TO_DATE_AT", 0x38),
    ("ADD_MINUTES_TO_DATE_AT_2", 0x39),
    ("ADD_MONEY", 0x2A),
    ("ADD_STAT", 0x35),
    ("ADD_TO_PSTAT", 0x1F),
    ("ADVANCE_TO_DATE_AT", 0x37),
    ("CALL_DIGIMON_ROUTINE", 0x49),
    ("CALL_ROUTINE", 0x64),
    ("COMPARE_DATE", 0x2C),
    ("COPY_PSTAT", 0x7A),
    ("DATA", 0x6B),
    ("DEAL_DAMAGE", 0x69),
    ("DELAY", 0x67),
    ("DESPAWN_BOULDER", 0x78),
    ("END_SCRIPT", 0xFF),
    ("END_SECTION", 0xFE),
    ("ENTITY_LOOK_AT_ENTITY", 0x4C),
    ("ENTITY_MOVE_TO", 0x6C),
    ("ENTITY_MOVE_TO_AXIS", 0x72),
    ("ENTITY_MOVE_TO_AXIS_WITH_CAMERA", 0x73),
    ("ENTITY_MOVE_TO_ENTITY", 0x6D),
    ("ENTITY_MOVE_TO_ENTITY_WITH_CAMERA", 0x6F),
    ("ENTITY_MOVE_TO_WITH_CAMERA", 0x6E),
    ("ENTITY_SET_ROTATION", 0x4D),
    ("ENTITY_WALK_TO", 0x4E),
    ("ENTITY_WALK_TO_ENTITY", 0x51),
    ("ENTITY_WALK_TO_ENTITY_WITH_CAMERA", 0x53),
    ("ENTITY_WALK_TO_WITH_CAMERA", 0x52),
    ("FADEOUT_HUD", 0x27),
    ("GIVE_CARD", 0x2F),
    ("GIVE_ITEM", 0x28),
    ("IF", 0x19),
    ("JUMP_AND_LINK", 0x13),
    ("JUMP_RETURN", 0x15),
    ("JUMP_TO", 0x16),
    ("JUMP_TO_FILE", 0x17),
    ("JUMP_TO_FILE_AND_LINK", 0x14),
    ("LEARN_MOVE", 0x2D),
    ("LOAD_DIGIMON", 0x46),
    ("MOVE_BOULDER", 0x77),
    ("MOVE_CAMERA_TO", 0x4F),
    ("MOVE_CAMERA_TO_ENTITY", 0x50),
    ("MOVE_OBJECT_TO", 0x71),
    ("PLAY_ANIMATION", 0x56),
    ("PLAY_SOUND", 0x5A),
    ("REDUCE_MERIT", 0x33),
    ("REDUCE_MONEY", 0x2B),
    ("REDUCE_PSTAT", 0x20),
    ("REDUCE_STAT", 0x36),
    ("REMOVE_CONDITION", 0x65),
    ("REMOVE_ITEM", 0x29),
    ("RESET_ENTITY_ORIGIN", 0x54),
    ("ROTATE_3D_OBJECT", 0x70),
    ("SECTION_ON_EXIT", 0x7B),
    ("SET_AUTOTALK", 0x6A),
    ("SET_BGM", 0x5D),
    ("SET_DIALOG_OWNER", 0x1B),
    ("SET_DIGIMON", 0x47),
    ("SET_INVENTORY_SIZE", 0x23),
    ("SET_MERIT", 0x31),
    ("SET_OBJ_VISIBILITY", 0x57),
    ("SET_PSTAT", 0x1E),
    ("SET_RECT_IMPASSABLE", 0x7C),
    ("SET_SCRIPT", 0xFB),
    ("SET_SELECTION", 0x10),
    ("SET_STAT", 0x34),
    ("SET_TEXTBOX_MODE", 0x68),
    ("SET_TEXTBOX_ORIGIN", 0x55),
    ("SET_TEXTBOX_SIZE", 0x26),
    ("SET_TRIGGER", 0x1C),
    ("SHOW_TEXTBOX", 0x1A),
    ("SPAWN_BOULDER", 0x76),
    ("SPAWN_CHEST", 0x75),
    ("SPAWN_ITEM", 0x74),
    ("SPAWN_SPRITE_AT_ENTITY", 0x7E),
    ("SPAWN_SPRITE_AT_LOCATION", 0x7D),
    ("START_BATTLE", 0x66),
    ("STOP_BGM", 0x5E),
    ("STORE_DATE", 0x25),
    ("STORE_DIGIMON_TYPE", 0x22),
    ("STORE_DIGIMON_VALUE", 0x3F),
    ("STORE_MAP_ID", 0x21),
    ("STORE_RANDOM", 0x24),
    ("SWITCH", 0x18),
    ("TAKE_CARD", 0x30),
    ("TELEPORT", 0x58),
    ("UNLOAD_DIGIMON", 0x79),
    ("UNLOAD_ENTITY", 0x48),
    ("UNSET_TRIGGER", 0x1D),
    ("UNUSED_11", 0x11),
    ("UNUSED_12", 0x12),
    ("UNUSED_2E", 0x2E),
    ("UNUSED_3A", 0x3A),
    ("UNUSED_3B", 0x3B),
    ("UNUSED_3C", 0x3C),
    ("UNUSED_3D", 0x3D),
    ("UNUSED_3E", 0x3E),
    ("UNUSED_5B", 0x5B),
    ("UNUSED_5C", 0x5C),
    ("UNUSED_5F", 0x5F),
    ("UNUSED_FC", 0xFC),
    ("UNUSED_FD", 0xFD),
    ("WAIT_FOR_ENTITY", 0x4A),
    ("WARP_TO", 0x4B),
];

pub(crate) const OPERANDS: &[(u8, &[Operand])] = &[
    (0x11, &[Operand::Pad]),
    (0x12, &[Operand::Pad]),
    (0x15, &[Operand::Pad]),
    (0x1B, &[Operand::Id]),
    (0x1C, &[Operand::Pad, Operand::U16]),
    (0x1D, &[Operand::Pad, Operand::U16]),
    (0x1E, &[Operand::Pad, Operand::Pstat, Operand::U8]),
    (0x1F, &[Operand::Pad, Operand::Pstat, Operand::U8]),
    (0x20, &[Operand::Pad, Operand::Pstat, Operand::U8]),
    (0x21, &[Operand::Pstat]),
    (0x22, &[Operand::Pstat]),
    (0x23, &[Operand::U8]),
    (0x24, &[Operand::Pad, Operand::Pstat, Operand::U8]),
    (0x25, &[Operand::Pstat]),
    (0x26, &[Operand::Id, Operand::U8, Operand::U8]),
    (0x27, &[Operand::U8]),
    (0x28, &[Operand::Pad, Operand::U8, Operand::U8]),
    (0x29, &[Operand::Pad, Operand::U8, Operand::U8]),
    (0x2A, &[Operand::Pad, Operand::S32]),
    (0x2B, &[Operand::Pad, Operand::S32]),
    (
        0x2C,
        &[
            Operand::Pstat,
            Operand::U16,
            Operand::U8,
            Operand::U8,
            Operand::U8,
            Operand::U8,
            Operand::U8,
            Operand::Pad,
        ],
    ),
    (0x2D, &[Operand::U8]),
    (0x2E, &[Operand::U8]),
    (0x2F, &[Operand::U8]),
    (0x30, &[Operand::U8]),
    (0x31, &[Operand::Pad, Operand::U16]),
    (0x32, &[Operand::Pad, Operand::U16]),
    (0x33, &[Operand::Pad, Operand::U16]),
    (0x34, &[Operand::U8, Operand::U16]),
    (0x35, &[Operand::U8, Operand::U16]),
    (0x36, &[Operand::U8, Operand::U16]),
    (0x37, &[Operand::Pstat]),
    (0x38, &[Operand::Pstat, Operand::S32]),
    (0x39, &[Operand::Pstat, Operand::S32]),
    (0x3A, &[Operand::Pad, Operand::U8, Operand::U8]),
    (0x3B, &[Operand::Pad, Operand::U8, Operand::U8]),
    (0x3C, &[Operand::Pad, Operand::U8, Operand::U8]),
    (0x3D, &[Operand::U8]),
    (0x3E, &[Operand::U8]),
    (0x3F, &[Operand::Pad, Operand::Pstat, Operand::Pstat]),
    (0x46, &[Operand::U8]),
    (0x47, &[Operand::U8, Operand::U8, Operand::U8]),
    (0x48, &[Operand::Id]),
    (0x49, &[Operand::U8]),
    (0x4A, &[Operand::Id]),
    (0x4B, &[Operand::U8, Operand::U8, Operand::U8]),
    (0x4C, &[Operand::Pad, Operand::Id, Operand::Id]),
    (0x4D, &[Operand::Id, Operand::S16]),
    (
        0x4E,
        &[
            Operand::Id,
            Operand::S16,
            Operand::S16,
            Operand::U8,
            Operand::U8,
        ],
    ),
    (0x4F, &[Operand::U8, Operand::S16, Operand::S16]),
    (0x50, &[Operand::Pad, Operand::Id, Operand::U8]),
    (0x51, &[Operand::Id, Operand::U8, Operand::Id]),
    (
        0x52,
        &[
            Operand::Id,
            Operand::S16,
            Operand::S16,
            Operand::U8,
            Operand::U8,
        ],
    ),
    (0x53, &[Operand::Id, Operand::U8, Operand::Id]),
    (0x54, &[Operand::Id]),
    (
        0x55,
        &[Operand::Pad, Operand::S16, Operand::S16, Operand::S16],
    ),
    (0x56, &[Operand::Pad, Operand::Id, Operand::U8]),
    (0x57, &[Operand::Pad, Operand::U8, Operand::U8]),
    (0x58, &[Operand::Pstat]),
    (0x5A, &[Operand::Pad, Operand::U8, Operand::U8]),
    (0x5B, &[Operand::U8]),
    (0x5C, &[Operand::U8]),
    (0x5D, &[Operand::U8]),
    (0x5E, &[Operand::U8]),
    (0x5F, &[Operand::U8]),
    (0x64, &[Operand::U8]),
    (0x65, &[Operand::U8]),
    (0x66, &[Operand::U8]),
    (0x67, &[Operand::Pad, Operand::U16]),
    (0x68, &[Operand::Pad, Operand::U8, Operand::U8]),
    (0x69, &[Operand::Pstat]),
    (0x6A, &[Operand::Pad, Operand::Id, Operand::U8]),
    (
        0x6C,
        &[
            Operand::Id,
            Operand::S16,
            Operand::S16,
            Operand::U8,
            Operand::U8,
        ],
    ),
    (0x6D, &[Operand::Id, Operand::Id, Operand::U8]),
    (
        0x6E,
        &[
            Operand::Id,
            Operand::S16,
            Operand::S16,
            Operand::U8,
            Operand::U8,
        ],
    ),
    (0x6F, &[Operand::Id, Operand::Id, Operand::U8]),
    (0x70, &[Operand::U8, Operand::U8, Operand::U8]),
    (
        0x71,
        &[
            Operand::U8,
            Operand::Id,
            Operand::U8,
            Operand::S8,
            Operand::Pad,
            Operand::S16,
            Operand::S16,
        ],
    ),
    (0x72, &[Operand::Id, Operand::S16, Operand::U8, Operand::U8]),
    (0x73, &[Operand::Id, Operand::S16, Operand::U8, Operand::U8]),
    (0x74, &[Operand::U8, Operand::S16, Operand::S16]),
    (
        0x75,
        &[
            Operand::U8,
            Operand::S16,
            Operand::S16,
            Operand::S16,
            Operand::S16,
            Operand::U16,
        ],
    ),
    (0x76, &[Operand::U8]),
    (0x77, &[Operand::U8, Operand::S16, Operand::S16]),
    (0x78, &[Operand::U8]),
    (0x79, &[Operand::U8]),
    (0x7A, &[Operand::Pad, Operand::Pstat, Operand::Pstat]),
    (0x7B, &[Operand::U8]),
    (
        0x7C,
        &[
            Operand::U8,
            Operand::S16,
            Operand::S16,
            Operand::U8,
            Operand::U8,
        ],
    ),
    (
        0x7D,
        &[
            Operand::U8,
            Operand::S16,
            Operand::S16,
            Operand::S16,
            Operand::S16,
        ],
    ),
    (0x7E, &[Operand::Id, Operand::U8, Operand::U8]),
    (0xFB, &[Operand::Pad, Operand::U16, Operand::U16]),
    (0xFC, &[]),
    (0xFD, &[]),
];

pub(crate) const OPERAND_NAMES: &[(u8, &[&str])] = &[
    (0x1B, &["entity"]),
    (0x1C, &["trigger"]),
    (0x1D, &["trigger"]),
    (0x1E, &["pstat", "value"]),
    (0x1F, &["pstat", "amount"]),
    (0x20, &["pstat", "amount"]),
    (0x21, &["pstat_out"]),
    (0x22, &["pstat_out"]),
    (0x23, &["size"]),
    (0x24, &["pstat_out", "max"]),
    (0x25, &["pstat_date"]),
    (0x26, &["origin", "columns", "rows"]),
    (0x27, &["textbox"]),
    (0x28, &["item", "amount"]),
    (0x29, &["item", "amount"]),
    (0x2A, &["amount"]),
    (0x2B, &["amount"]),
    (
        0x2C,
        &[
            "pstat_date",
            "year",
            "month",
            "day",
            "hour",
            "minute",
            "flags",
        ],
    ),
    (0x2D, &["move"]),
    (0x2E, &["value"]),
    (0x2F, &["card"]),
    (0x30, &["card"]),
    (0x31, &["value"]),
    (0x32, &["amount"]),
    (0x33, &["amount"]),
    (0x34, &["stat", "value"]),
    (0x35, &["stat", "amount"]),
    (0x36, &["stat", "amount"]),
    (0x37, &["pstat_date"]),
    (0x38, &["pstat_date", "minutes"]),
    (0x39, &["pstat_date", "minutes"]),
    (0x3A, &["arg1", "arg2"]),
    (0x3B, &["arg1", "arg2"]),
    (0x3C, &["arg1", "arg2"]),
    (0x3D, &["value"]),
    (0x3E, &["value"]),
    (0x3F, &["pstat_digimon", "pstat_out"]),
    (0x46, &["digimon"]),
    (0x47, &["digimon", "slot", "autotalk"]),
    (0x48, &["entity"]),
    (0x49, &["routine"]),
    (0x4A, &["entity"]),
    (0x4B, &["map", "exit", "section"]),
    (0x4C, &["entity", "target"]),
    (0x4D, &["entity", "rotation"]),
    (0x4E, &["entity", "x", "z", "animation", "flags"]),
    (0x4F, &["speed", "x", "z"]),
    (0x50, &["entity", "speed"]),
    (0x51, &["entity", "animation", "target"]),
    (0x52, &["entity", "x", "z", "animation", "flags"]),
    (0x53, &["entity", "animation", "target"]),
    (0x54, &["entity"]),
    (0x55, &["x", "y", "z"]),
    (0x56, &["entity", "animation"]),
    (0x57, &["object", "visible"]),
    (0x58, &["pstat_map_exit"]),
    (0x5A, &["bank", "sound"]),
    (0x5B, &["value"]),
    (0x5C, &["value"]),
    (0x5D, &["bgm"]),
    (0x5E, &["arg"]),
    (0x5F, &["value"]),
    (0x64, &["builtin"]),
    (0x65, &["condition_mask"]),
    (0x66, &["battle"]),
    (0x67, &["frames"]),
    (0x68, &["mode", "frames"]),
    (0x69, &["damage_percent"]),
    (0x6A, &["entity", "autotalk"]),
    (0x6C, &["entity", "x", "z", "speed", "flags"]),
    (0x6D, &["entity", "target", "speed"]),
    (0x6E, &["entity", "x", "z", "speed", "flags"]),
    (0x6F, &["entity", "target", "speed"]),
    (0x70, &["door", "arg", "target"]),
    (0x71, &["slot", "entity", "speed", "angle", "x", "z"]),
    (0x72, &["entity", "target", "axis", "speed"]),
    (0x73, &["entity", "target", "axis", "speed"]),
    (0x74, &["item", "x", "z"]),
    (0x75, &["item", "x", "y", "z", "w", "trigger"]),
    (0x76, &["boulder"]),
    (0x77, &["boulder", "x", "z"]),
    (0x78, &["boulder"]),
    (0x79, &["digimon"]),
    (0x7A, &["pstat_from", "pstat_to"]),
    (0x7B, &["section"]),
    (0x7C, &["rect", "x", "z", "width", "height"]),
    (0x7D, &["sprite", "x", "y", "z", "w"]),
    (0x7E, &["entity", "node", "sprite"]),
    (0xFB, &["script", "map"]),
    (0xFC, &[]),
    (0xFD, &[]),
];

/// US Digimon names by id, from ``decomp/src/main/main.c`` and its text YAML.
/// Related ids can share a name; editing by name then needs the numeric id.
/// ``tools/test_scn_text.py`` keeps this in sync with the Python dumper.
pub(crate) const DIGIMON_NAMES: &[(u8, &str)] = &[
    (0x00, "main character"),
    (0x01, "Botamon"),
    (0x02, "Koromon"),
    (0x03, "Agumon"),
    (0x04, "Betamon"),
    (0x05, "Greymon"),
    (0x06, "Devimon"),
    (0x07, "Airdramon"),
    (0x08, "Tyrannomon"),
    (0x09, "Meramon"),
    (0x0A, "Seadramon"),
    (0x0B, "Numemon"),
    (0x0C, "MetalGreymon"),
    (0x0D, "Mamemon"),
    (0x0E, "Monzaemon"),
    (0x0F, "Punimon"),
    (0x10, "Tsunomon"),
    (0x11, "Gabumon"),
    (0x12, "Elecmon"),
    (0x13, "Kabuterimon"),
    (0x14, "Angemon"),
    (0x15, "Birdramon"),
    (0x16, "Garurumon"),
    (0x17, "Frigimon"),
    (0x18, "Whamon"),
    (0x19, "Vegiemon"),
    (0x1A, "SkullGreymon"),
    (0x1B, "MetalMamemon"),
    (0x1C, "Vademon"),
    (0x1D, "Poyomon"),
    (0x1E, "Tokomon"),
    (0x1F, "Patamon"),
    (0x20, "Kunemon"),
    (0x21, "Unimon"),
    (0x22, "Ogremon"),
    (0x23, "Shellmon"),
    (0x24, "Centarumon"),
    (0x25, "Bakemon"),
    (0x26, "Drimogemon"),
    (0x27, "Sukamon"),
    (0x28, "Andromon"),
    (0x29, "Giromon"),
    (0x2A, "Etemon"),
    (0x2B, "Yuramon"),
    (0x2C, "Tanemon"),
    (0x2D, "Biyomon"),
    (0x2E, "Palmon"),
    (0x2F, "Monochromon"),
    (0x30, "Leomon"),
    (0x31, "Coelamon"),
    (0x32, "Kokatorimon"),
    (0x33, "Kuwagamon"),
    (0x34, "Mojyamon"),
    (0x35, "Nanimon"),
    (0x36, "Megadramon"),
    (0x37, "Piximon"),
    (0x38, "Digitamamon"),
    (0x39, "Penguinmon"),
    (0x3A, "Ninjamon"),
    (0x3B, "Phoenixmon"),
    (0x3C, "H-Kabuterimon"),
    (0x3D, "MegaSeadramon"),
    (0x3E, "WereGarurumon"),
    (0x3F, "Panjyamon"),
    (0x40, "Gigadramon"),
    (0x41, "MetalEtemon"),
    (0x42, "Myotismon"),
    (0x43, "Yanmamon"),
    (0x44, "Gotsumon"),
    (0x45, "Flarerizamon"),
    (0x46, "WaruMonzaemon"),
    (0x47, "SnowAgumon"),
    (0x48, "Hyogamon"),
    (0x49, "PlatinumSukamon"),
    (0x4A, "Dokunemon"),
    (0x4B, "ShimaUnimon"),
    (0x4C, "Tankmon"),
    (0x4D, "RedVegiemon"),
    (0x4E, "J-Mojyamon"),
    (0x4F, "NiseDrimogemon"),
    (0x50, "Goburimon"),
    (0x51, "MudFrigimon"),
    (0x52, "Psychemon"),
    (0x53, "ModokiBetamon"),
    (0x54, "ToyAgumon"),
    (0x55, "Piddomon"),
    (0x56, "Aruraumon"),
    (0x57, "Geremon"),
    (0x58, "Vermilimon"),
    (0x59, "Fugamon"),
    (0x5A, "Tekkamon"),
    (0x5B, "MoriShellmon"),
    (0x5C, "Guardromon"),
    (0x5D, "Muchomon"),
    (0x5E, "Icemon"),
    (0x5F, "Akatorimon"),
    (0x60, "Tsukaimon"),
    (0x61, "Sharmamon"),
    (0x62, "ClearAgumon"),
    (0x63, "Weedmon"),
    (0x64, "IceDevimon"),
    (0x65, "Darkrizamon"),
    (0x66, "SandYanmamon"),
    (0x67, "SnowGoburimon"),
    (0x68, "BlueMeramon"),
    (0x69, "Gururumon"),
    (0x6A, "Saberdramon"),
    (0x6B, "Soulmon"),
    (0x6C, "Rockmon"),
    (0x6D, "Otamamon"),
    (0x6E, "Gekomon"),
    (0x6F, "Tentomon"),
    (0x70, "WaruSeadramon"),
    (0x71, "Meteormon"),
    (0x72, ""),
    (0x73, "Machinedramon"),
    (0x74, "Analogman"),
    (0x75, "Jijimon"),
    (0x76, "Market Manager"),
    (0x77, "ShogunGekomon"),
    (0x78, "King of Sukamon"),
    (0x79, "Cherrymon"),
    (0x7A, "Hagurumon"),
    (0x7B, "Tinmon"),
    (0x7C, "Master Tyrannomon"),
    (0x7D, "Goburimon"),
    (0x7E, "Brachiomon"),
    (0x7F, "DemiMeramon"),
    (0x80, "Betamon"),
    (0x81, "Greymon"),
    (0x82, "Devimon"),
    (0x83, "Airdramon"),
    (0x84, "Tyrannomon"),
    (0x85, "Meramon"),
    (0x86, "Seadramon"),
    (0x87, "Numemon"),
    (0x88, "MetalGreymon"),
    (0x89, "Mamemon"),
    (0x8A, "Monzaemon"),
    (0x8B, "Gabumon"),
    (0x8C, "Elecmon"),
    (0x8D, "Kabuterimon"),
    (0x8E, "Angemon"),
    (0x8F, "Birdramon"),
    (0x90, "Garurumon"),
    (0x91, "Frigimon"),
    (0x92, "Whamon"),
    (0x93, "Vegiemon"),
    (0x94, "SkullGreymon"),
    (0x95, "MetalGreymon"),
    (0x96, "Vademon"),
    (0x97, "Patamon"),
    (0x98, "Kunemon"),
    (0x99, "Unimon"),
    (0x9A, "Ogremon"),
    (0x9B, "Shellmon"),
    (0x9C, "Centarumon"),
    (0x9D, "Bakemon"),
    (0x9E, "Drimogemon"),
    (0x9F, "Sukamon"),
    (0xA0, "Andromon"),
    (0xA1, "Giromon"),
    (0xA2, "Etemon"),
    (0xA3, "Biyomon"),
    (0xA4, "Palmon"),
    (0xA5, "Monochromon"),
    (0xA6, "Leomon"),
    (0xA7, "Coelamon"),
    (0xA8, "Kokatorimon"),
    (0xA9, "Kuwagamon"),
    (0xAA, "Mojyamon"),
    (0xAB, "Nanimon"),
    (0xAC, "Megadramon"),
    (0xAD, "Piximon"),
    (0xAE, "Digitamamon"),
    (0xAF, "Ninjamon"),
    (0xB0, "Penguinmon"),
    (0xB1, "Myotismon"),
    (0xB2, "Greymon"),
    (0xB3, "MetalGreymon"),
];

/// Move names by id (US), from ``decomp/text/main/item.yaml``.
/// ``tools/test_scn_text.py`` keeps this in sync with the Python dumper.
pub(crate) const MOVE_NAMES: &[(u8, &str)] = &[
    (0x00, "Fire Tower"),
    (0x01, "Prominence Beam"),
    (0x02, "Spit Fire"),
    (0x03, "Red Inferno"),
    (0x04, "Magma Bomb"),
    (0x05, "Heat Laser"),
    (0x06, "Inifinity Burn"),
    (0x07, "Meltdown"),
    (0x08, "Thunder Justice"),
    (0x09, "Spinning Shot"),
    (0x0A, "Electric Cloud"),
    (0x0B, "Megalo Spark"),
    (0x0C, "Static Elect"),
    (0x0D, "Wind Cutter"),
    (0x0E, "Confused Storm"),
    (0x0F, "Hurricane"),
    (0x10, "Giga Freeze"),
    (0x11, "Ice Statue"),
    (0x12, "Winter Blast"),
    (0x13, "Ice Needle"),
    (0x14, "Water Blit"),
    (0x15, "Aqua Magic"),
    (0x16, "Aurora Freeze"),
    (0x17, "Tear Drop"),
    (0x18, "Power Crane"),
    (0x19, "All Range Beam"),
    (0x1A, "Metal Sprinter"),
    (0x1B, "Pulse Laser"),
    (0x1C, "Delete Program"),
    (0x1D, "DG Dimension"),
    (0x1E, "Full Potential"),
    (0x1F, "Reverse Prog"),
    (0x20, "Poison Powder"),
    (0x21, "Bug"),
    (0x22, "Mass Morph"),
    (0x23, "Insect Plague"),
    (0x24, "Charm Perfume"),
    (0x25, "Poison Claw"),
    (0x26, "Danger Sting"),
    (0x27, "Green Trap"),
    (0x28, "Tremar"),
    (0x29, "Muscle Charge"),
    (0x2A, "War Cry"),
    (0x2B, "Sonic Jab"),
    (0x2C, "Dynamite Kick"),
    (0x2D, "Counter"),
    (0x2E, "Megaton Punch"),
    (0x2F, "Dynamite Kick"),
    (0x30, "Odor Spray"),
    (0x31, "Poop Spd Toss"),
    (0x32, "Big Poop Toss"),
    (0x33, "Big Rnd Toss"),
    (0x34, "Poop Rnd Toss"),
    (0x35, "Rnd Spd Toss"),
    (0x36, "Horizontal Kick"),
    (0x37, "Horizontal Kick"),
    (0x38, "Blaze Blast"),
    (0x39, "Pepper Breath"),
    (0x3A, "Lovely Attack"),
    (0x3B, "Fireball"),
    (0x3C, "Death Claw"),
    (0x3D, "Mega Flame"),
    (0x3E, "Howling Blaster"),
    (0x3F, "Party time"),
    (0x40, "Electric Shock"),
    (0x41, "Abduction Beam"),
    (0x42, "Smiley Bomb"),
    (0x43, "Spnning Needle"),
    (0x44, "Spiral Twister"),
    (0x45, "Boom Bubble"),
    (0x46, "Sweet Breath"),
    (0x47, "Bit Bomb"),
    (0x48, "Deadly Bomb"),
    (0x49, "Drill Spin"),
    (0x4A, "Electric Thread"),
    (0x4B, "Energy Bomb"),
    (0x4C, "Genoside Attack"),
    (0x4D, "Giga Scissor Claw"),
    (0x4E, "Dark Shot"),
    (0x4F, "Pummel Whack"),
    (0x50, "Hand of Fate"),
    (0x51, "Dark Claw"),
    (0x52, "Aerial Attack"),
    (0x53, "Bone Boomerang"),
    (0x54, "Solar Ray"),
    (0x55, "Hydro Pressure"),
    (0x56, "Ice Blast"),
    (0x57, "Iga School Knife Throw"),
    (0x58, "Blasting Spout"),
    (0x59, "Fist of the Beast King"),
    (0x5A, "Dark Network & Concert Crush"),
    (0x5B, "Electro Shocker"),
    (0x5C, "Meteor Wing"),
    (0x5D, "Super Slap"),
    (0x5E, "Nightmare Syndromer"),
    (0x5F, "Frozen Fire Shot"),
    (0x60, "Poison Ivy"),
    (0x61, "Blue Blaster"),
    (0x62, "Scissor Claw"),
    (0x63, "Super Thunder Strike"),
    (0x64, "Spiral Sword"),
    (0x65, "Variable Darts"),
    (0x66, "Volcanic Strike"),
    (0x67, "Subzero Ice Punch"),
    (0x68, "Infinity Cannon"),
    (0x69, "Party time"),
    (0x6A, "Party time"),
    (0x6B, "Crimson Flare"),
    (0x6C, "Glacial Blast"),
    (0x6D, "Mail Strome"),
    (0x6E, "High Electro Shocker"),
    (0x6F, "Bubble"),
    (0x70, "Bubble"),
    (0x71, "Bubble"),
    (0x72, "Bubble"),
    (0x73, "Bubble"),
];

/// Item names by id (US), from ``decomp/text/main/item.yaml``.
/// ``tools/test_scn_text.py`` keeps this in sync with the Python dumper.
pub(crate) const ITEM_NAMES: &[(u8, &str)] = &[
    (0x00, "sm.recovery"),
    (0x01, "med.recovery"),
    (0x02, "lrg.recovery"),
    (0x03, "sup.recovery"),
    (0x04, "MP Floppy"),
    (0x05, "Medium MP"),
    (0x06, "Large MP"),
    (0x07, "Double flop"),
    (0x08, "Various"),
    (0x09, "Omnipotent"),
    (0x0A, "Protection"),
    (0x0B, "Restore"),
    (0x0C, "Sup.restore"),
    (0x0D, "Bandage"),
    (0x0E, "Medicine"),
    (0x0F, "Off. Disk"),
    (0x10, "Def. Disk"),
    (0x11, "Hispeed dsk"),
    (0x12, "Omni Disk"),
    (0x13, "S.Off.disk"),
    (0x14, "S.Def.disk"),
    (0x15, "S.speed.disk"),
    (0x16, "Auto Pilot"),
    (0x17, "Off. Chip"),
    (0x18, "Def. Chip"),
    (0x19, "Brain Chip"),
    (0x1A, "Quick Chip"),
    (0x1B, "HP Chip"),
    (0x1C, "MP Chip"),
    (0x1D, "DV Chip A"),
    (0x1E, "DV Chip D"),
    (0x1F, "DV Chip E"),
    (0x20, "Port. potty"),
    (0x21, "Trn. manual"),
    (0x22, "Rest pillow"),
    (0x23, "Enemy repel"),
    (0x24, "Enemy bell"),
    (0x25, "Health shoe"),
    (0x26, "Meat"),
    (0x27, "Giant Meat"),
    (0x28, "Sirloin"),
    (0x29, "Supercarrot"),
    (0x2A, "Hawk radish"),
    (0x2B, "Spiny green"),
    (0x2C, "Digimushrm"),
    (0x2D, "Ice mushrm"),
    (0x2E, "Deluxmushrm"),
    (0x2F, "Digipine"),
    (0x30, "Blue apple"),
    (0x31, "Red Berry"),
    (0x32, "Gold Acorn"),
    (0x33, "Big Berry"),
    (0x34, "Sweet Nut"),
    (0x35, "Super veggy"),
    (0x36, "Pricklypear"),
    (0x37, "Orange bana"),
    (0x38, "Power fruit"),
    (0x39, "Power Ice"),
    (0x3A, "Speed Leaf"),
    (0x3B, "Sage Fruit"),
    (0x3C, "Muscle Yam"),
    (0x3D, "Calm berry"),
    (0x3E, "Digianchovy"),
    (0x3F, "Digisnapper"),
    (0x40, "DigiTrout"),
    (0x41, "Black trout"),
    (0x42, "Digicatfish"),
    (0x43, "Digiseabass"),
    (0x44, "Moldy Meat"),
    (0x45, "Happymushrm"),
    (0x46, "Chain melon"),
    (0x47, "Grey Claws"),
    (0x48, "Fireball"),
    (0x49, "Flamingwing"),
    (0x4A, "Iron Hoof"),
    (0x4B, "Mono Stone"),
    (0x4C, "Steel drill"),
    (0x4D, "White Fang"),
    (0x4E, "Black Wing"),
    (0x4F, "Spike Club"),
    (0x50, "Flamingmane"),
    (0x51, "White Wing"),
    (0x52, "Torn tatter"),
    (0x53, "Electo ring"),
    (0x54, "Rainbowhorn"),
    (0x55, "Rooster"),
    (0x56, "Unihorn"),
    (0x57, "Horn helmet"),
    (0x58, "Scissor jaw"),
    (0x59, "Fertilizer"),
    (0x5A, "Koga laws"),
    (0x5B, "Waterbottle"),
    (0x5C, "North Star"),
    (0x5D, "Red Shell"),
    (0x5E, "Hard Scale"),
    (0x5F, "Bluecrystal"),
    (0x60, "Ice crystal"),
    (0x61, "Hair grower"),
    (0x62, "Sunglasses"),
    (0x63, "Metal part"),
    (0x64, "Fatal Bone"),
    (0x65, "Cyber part"),
    (0x66, "Mega Hand"),
    (0x67, "Silver ball"),
    (0x68, "Metal armor"),
    (0x69, "Chainsaw"),
    (0x6A, "Small spear"),
    (0x6B, "X Bandage"),
    (0x6C, "Ray Gun"),
    (0x6D, "Gold banana"),
    (0x6E, "Mysty Egg"),
    (0x6F, "Red Ruby"),
    (0x70, "Beetlepearl"),
    (0x71, "Coral charm"),
    (0x72, "Moon mirror"),
    (0x73, "Blue Flute"),
    (0x74, "old fishrod"),
    (0x75, "Amazing rod"),
    (0x76, "Leomonstone"),
    (0x77, "Mansion key"),
    (0x78, "Gear"),
    (0x79, "Rain Plant"),
    (0x7A, "Steak"),
    (0x7B, "Frig Key"),
    (0x7C, "AS Decoder"),
    (0x7D, "Giga Hand"),
    (0x7E, "Noble Mane"),
    (0x7F, "Metalbanana"),
];

/// The special cases of convertAsciiToJis() in decomp/src/main/sjis.c:
/// printable ASCII -> its two-byte glyph. Digits and letters are ranges.
/// tools/test_scn_text.py keeps this in sync with the C table.
const ASCII_SPECIAL: &[(u8, u16)] = &[
    (0x20, 0x8140),
    (0x21, 0x8149),
    (0x22, 0x8168),
    (0x23, 0x8194),
    (0x24, 0x8190),
    (0x25, 0x8193),
    (0x26, 0x8195),
    (0x27, 0x8166),
    (0x28, 0x8169),
    (0x29, 0x816A),
    (0x2A, 0x8196),
    (0x2B, 0x817B),
    (0x2C, 0x8143),
    (0x2D, 0x817C),
    (0x2E, 0x8142),
    (0x2F, 0x815E),
    (0x3A, 0x8146),
    (0x3B, 0x8147),
    (0x3C, 0x8171),
    (0x3D, 0x8181),
    (0x3E, 0x8172),
    (0x3F, 0x8148),
    (0x40, 0x8197),
    (0x5B, 0x816D),
    (0x5C, 0x815F),
    (0x5D, 0x816E),
    (0x5E, 0x814F),
    (0x5F, 0x8151),
    (0x60, 0x8165),
    (0x7B, 0x816F),
    (0x7C, 0x8162),
    (0x7D, 0x8170),
    (0x7E, 0x8150),
];

/// Screen id -> map filename and display name, from MAP_ENTRIES/MAP_NAME_PTR.
/// tools/test_scn_text.py keeps this in sync with the Python dumper.
pub(crate) const MAP_NAMES: &[(u8, &str, &str)] = &[
    (0x00, "MAYO01", "Native Forest"),
    (0x01, "MAYO02", "Kunemon's Bed"),
    (0x02, "MAYO03", "Native Forest"),
    (0x03, "MAYO04A", "Native Forest"),
    (0x04, "MAYO04B", "Native Forest"),
    (0x05, "MAYO05", "Coela Point"),
    (0x06, "MAYO06", "Dragon Eye Lake"),
    (0x07, "MAYO11", "Drill Tunnel Entrance"),
    (0x08, "MAYO10", "Dragon Eye Lake"),
    (0x09, "MAYO08A", "Digimon Bridge"),
    (0x0A, "MAYO08B", "Digimon Bridge"),
    (0x0B, "TROP00", "Tropical Jungle"),
    (0x0C, "TROP01", "Tropical Jungle"),
    (0x0D, "TROP02", "Tropical Jungle"),
    (0x0E, "TROP03", "Tropical Jungle"),
    (0x0F, "TROP04", "Mangrove Region"),
    (0x10, "TROP05", "Mangrove Region"),
    (0x11, "TROP06", "Amida Forest"),
    (0x12, "MIHA00", "Path Thru Mt. Panorama"),
    (0x13, "MIHA01", "Mt. Panorama Plains"),
    (0x14, "MIHA02", "Path Thru Mt. Panorama"),
    (0x15, "MIHA03", "Mt. Panorama Spore Area"),
    (0x16, "MIHA04A", "Foot of Mt. Panorama"),
    (0x17, "MIHA04B", "Foot of Mt. Panorama"),
    (0x18, "TUNN01", "Drill Tunnel"),
    (0x19, "TUNN02", "Drill Tunnel 2nd floor"),
    (0x1A, "TUNN03", "Drill Tunnel 3rd floor"),
    (0x1B, "TUNN04", "Residential Area"),
    (0x1C, "TUNN05", "Underground Pond"),
    (0x1D, "TUNN06", "Drill Tunnel 2nd floor"),
    (0x1E, "TUNN07", "Lava Cave"),
    (0x1F, "TUNN08", "Lava Cave"),
    (0x20, "TUNN09", "Drill Tunnel"),
    (0x21, "TUNN10", "Lava Cave"),
    (0x22, "DGHA01", "Overdell"),
    (0x23, "DGHA02", "Overdell Cemetery"),
    (0x24, "GCAN01", "Great Canyon Entrance"),
    (0x25, "GCAN02", "Great Canyon Top Area"),
    (0x26, "GCAN03", "Great Canyon Top Area"),
    (0x27, "GCAN04", "Great Canyon Bridge"),
    (0x28, "GCAN05", "Fortress Entrance"),
    (0x29, "GCAN06", "Great Canyon Bot. Area"),
    (0x2A, "GCAN07", "Great Canyon Bot. Area"),
    (0x2B, "GCAN08_1", "Great Canyon Top Area"),
    (0x2C, "GCAN09", "Great Canyon Top Area"),
    (0x2D, "OGRE00", "Ogre Fortress"),
    (0x2E, "OGRE01", "Ogre Fortress"),
    (0x2F, "OGRE02", "Ogre Fortress"),
    (0x30, "OGRE03", "Ogre Fortress"),
    (0x31, "GCAN11", "Monochrome Shop"),
    (0x32, "YAKA01", "Grey Lord's Mansion"),
    (0x33, "YAKA02", "Grey Lord's Mansion"),
    (0x34, "YAKA11A", "Grey Lord's Mansion"),
    (0x35, "YAKA11B", "Grey Lord's Mansion"),
    (0x36, "YAKA12", "Grey Lord's Mansion"),
    (0x37, "YAKA13", "Grey Lord's Mansion"),
    (0x38, "YAKA14", "Grey Lord's Mansion"),
    (0x39, "YAKA15", "Grey Lord's Mansion"),
    (0x3A, "YAKA16", "Grey Lord's Mansion"),
    (0x3B, "YAKA17", "Grey Lord's Mansion"),
    (0x3C, "YAKA18", "Grey Lord's Mansion"),
    (0x3D, "YAKA21", "Grey Lord's Mansion"),
    (0x3E, "YAKA22", "Grey Lord's Mansion"),
    (0x3F, "YAKA23", "Grey Lord's Mansion"),
    (0x40, "YAKA24", "Grey Lord's Mansion"),
    (0x41, "YAKA25", "Grey Lord's Mansion"),
    (0x42, "CHKA01", "Mansion Basement"),
    (0x43, "SAIB01", "Underground Lab"),
    (0x44, "SAIB02", "Underground Lab"),
    (0x45, "GIAS00", "Gear Savanna"),
    (0x46, "GIAS01", "Gear Savanna"),
    (0x47, "GIAS02", "Gear Savanna"),
    (0x48, "GIAS03", "Gear Savanna"),
    (0x49, "GIAS04", "Gear Savanna"),
    (0x4A, "GIAS05", "Gear Savanna"),
    (0x4B, "GIAS06A", "Gear Savanna"),
    (0x4C, "GIAS07", "Gear Savanna"),
    (0x4D, "GIAS08", "Gear Savanna"),
    (0x4E, "GIAS09", "Gear Savanna"),
    (0x4F, "KODA00", "Ancient Dino Region"),
    (0x50, "KODA01", "Ancient Glacial Region"),
    (0x51, "KODA02", "Ancient Glacial Region"),
    (0x52, "KODA03", "Ancient Glacial Region"),
    (0x53, "KODA04", "Ancient Speedy Region"),
    (0x54, "KODA05", "Ancient Speedy Region"),
    (0x55, "KODA06", "Ancient Speedy Region"),
    (0x56, "KODA07", "Ancient Speedy Region"),
    (0x57, "KODA08", "Ancient Speedy Region"),
    (0x58, "FRZL01", "Freezeland"),
    (0x59, "FRZL02", "Freezeland"),
    (0x5A, "FRZL03", "Freezeland"),
    (0x5B, "FRZL04", "Freezeland"),
    (0x5C, "FRZL05", "Freezeland"),
    (0x5D, "FRZL06", "Freezeland"),
    (0x5E, "FRZL07", "Freezeland"),
    (0x5F, "FRZL08", "Freezeland"),
    (0x60, "FRZL12", "Freezeland"),
    (0x61, "ICSA01", "Ice Sanctuary"),
    (0x62, "ICSA02", "Ice Sanctuary"),
    (0x63, "ICSA03", "Ice Sanctuary"),
    (0x64, "ICSA04", "Ice Sanctuary"),
    (0x65, "ICSA05", "Ice Sanctuary"),
    (0x66, "ICSA06", "Ice Sanctuary"),
    (0x67, "ICSA07", "Ice Sanctuary"),
    (0x68, "ICSA08", "Ice Sanctuary"),
    (0x69, "BETL01", "Beetle Land"),
    (0x6A, "BETL02", "Beetle Land"),
    (0x6B, "BETL03", "Beetle Land"),
    (0x6C, "BETL04", "Beetle Land"),
    (0x6D, "MAYO00", "Native Forest"),
    (0x6E, "MAYO01_2", "Native Forest"),
    (0x6F, "MAYO02_2", "Native Forest"),
    (0x70, "TRAI00", "Green Gym"),
    (0x71, "LEOM01", "Leomon Ancestor's Cave"),
    (0x72, "LEOM02", "Leomon Ancestor's Cave"),
    (0x73, "MIST01", "Misty Trees"),
    (0x74, "MIST02", "Misty Trees"),
    (0x75, "MIST03", "Misty Trees"),
    (0x76, "MIST04", "Misty Trees"),
    (0x77, "MIST05", "Misty Trees"),
    (0x78, "MIST06", "Misty Trees"),
    (0x79, "MIST07", "Misty Trees"),
    (0x7A, "TUNN07_2", "Lava Cave"),
    (0x7B, "TUNN07_3", "Lava Cave"),
    (0x7C, "TUNN08_2", "Lava Cave"),
    (0x7D, "TUNN08_3", "Lava Cave"),
    (0x7E, "TUNN03_2", "Drill Tunnel"),
    (0x7F, "GCAN04_2", "Great Canyon"),
    (0x80, "GCAN08_2", "Great Canyon"),
    (0x81, "GCAN10", "Great Canyon"),
    (0x82, "OGRE04", "Ogre Fortress"),
    (0x83, "GIAS06B", "Gear Savanna"),
    (0x84, "FRZL13", "Freezeland"),
    (0x85, "FRZL14", "Freezeland"),
    (0x86, "FRZL15", "Freezeland"),
    (0x87, "FRZL16", "Freezeland"),
    (0x88, "FRZL17", "Freezeland"),
    (0x89, "FRZL18", "Freezeland"),
    (0x8A, "STIC01", "Geko Swamp"),
    (0x8B, "STIC02", "Geko Swamp"),
    (0x8C, "GKYO01", "Volume Villa"),
    (0x8D, "GKYO02", "Volume Villa"),
    (0x8E, "OGRE10", "Secret Beach Cave"),
    (0x8F, "OGRE11", "Secret Beach Cave"),
    (0x90, "OMOC01", "Toy Town"),
    (0x91, "OMOC02", "Costume House"),
    (0x92, "OMOC03", "Robot House"),
    (0x93, "OMOC04", "Toy Mansion"),
    (0x94, "OMOC05", "Toy Mansion"),
    (0x95, "OMOC06", "Toy Mansion"),
    (0x96, "OMOC07", "Toy Mansion"),
    (0x97, "OMOC08", "Toy Mansion"),
    (0x98, "FACT01", "Factorial Town"),
    (0x99, "FACT02", "Factorial Town"),
    (0x9A, "FACT03", "Factorial Town"),
    (0x9B, "FACT04", "Factorial Town"),
    (0x9C, "FACT05", "Factorial Town"),
    (0x9D, "FACT06", "Factorial Town"),
    (0x9E, "FACT07", "Factorial Town"),
    (0x9F, "FACT08A", "Factorial Town"),
    (0xA0, "FACT08B", "Factorial Town"),
    (0xA1, "FACT09", "Factorial Town"),
    (0xA2, "FACT10", "Factorial Town"),
    (0xA3, "FACT11A", "Sewer"),
    (0xA4, "GOMI01", "Trash Mountain"),
    (0xA5, "GOMI02", "Trash Mountain"),
    (0xA6, "MGEN01", "Mt. Infinity"),
    (0xA7, "MGEN02", "Mt. Infinity"),
    (0xA8, "TWNA02", "File City"),
    (0xA9, "TWNA03", "File City"),
    (0xAA, "TWNA04", "File City"),
    (0xAB, "TWNA05", "File City"),
    (0xAC, "TWNA06", "File City"),
    (0xAD, "TWNA07", "File City"),
    (0xAE, "TWNA08", "File City"),
    (0xAF, "TWNA09", "File City"),
    (0xB0, "TWNA10", "File City"),
    (0xB1, "TWNA11", "File City"),
    (0xB2, "TWNA12", "File City"),
    (0xB3, "TWNA13", "File City"),
    (0xB4, "TWNB01", "File City"),
    (0xB5, "TWNB02", "File City"),
    (0xB6, "TWNB03", "File City"),
    (0xB7, "TWNB04", "File City"),
    (0xB8, "TWNB05", "File City"),
    (0xB9, "TWNB06", "File City"),
    (0xBA, "TWNB07", "File City"),
    (0xBB, "TWNB08", "File City"),
    (0xBC, "TWNB09", "File City"),
    (0xBD, "TWNB10", "File City"),
    (0xBE, "TWNB11", "File City"),
    (0xBF, "TWNB12", "File City"),
    (0xC0, "TWNB13", "File City"),
    (0xC1, "TWNB14", "File City"),
    (0xC2, "TWNB15", "File City"),
    (0xC3, "TWNB16", "File City"),
    (0xC4, "TWNB17", "File City"),
    (0xC5, "TWNB18", "File City"),
    (0xC6, "TWNB19", "File City"),
    (0xC7, "TWNB20", "File City"),
    (0xC8, "TWNB21", "File City"),
    (0xC9, "TWNB22", "File City"),
    (0xCA, "TWNB23", "File City"),
    (0xCB, "TWNB24", "File City"),
    (0xCC, "TWNA01", "File City"),
    (0xCD, "ROOM10", "Jijimon's house"),
    (0xCE, "ROOM11", "Jijimon's house"),
    (0xCF, "ROOM12", "Birdra Transport"),
    (0xD0, "ROOM13", "Arena Lobby"),
    (0xD1, "ROOM14", "Treasure Hunt"),
    (0xD2, "MGEN03", "Mt. Infinity"),
    (0xD3, "ROOM02", "Item Keeper"),
    (0xD4, "MGEN04", "Mt. Infinity"),
    (0xD5, "ROOM04", "Centar Clinic"),
    (0xD6, "ROOM05A", "Restaurant"),
    (0xD7, "ROOM05B", "Restaurant"),
    (0xD8, "ROOM06", "Item Shop"),
    (0xD9, "ROOM07", "Secret Item Shop"),
    (0xDA, "ROOM08", "Jijimon's house"),
    (0xDB, "MGEN05", "Mt. Infinity"),
    (0xDC, "FACT11B", "Sewer"),
    (0xDD, "SAIB03", "Underground Lab"),
    (0xDE, "MGEN98", "Mt. Infinity"),
    (0xDF, "ROOM19", "Arena Lobby"),
    (0xE0, "YAKA26", "Grey Lord's Mansion"),
    (0xE1, "MGEN99", "Mt. Infinity"),
    (0xE2, "MGEN11", "Back Dimension"),
    (0xE3, "MGEN12", "Back Dimension"),
    (0xE4, "MGEN13", "Back Dimension"),
    (0xE5, "MGEN14", "Mt. Infinity"),
    (0xE6, "MGEN15", "Mt. Infinity"),
    (0xE7, "MGEN16", "Mt. Infinity"),
    (0xE8, "YAKA25", "Grey Lord's Mansion"),
    (0xE9, "MIHA05", "Mt. Panorama Spore Area"),
    (0xEA, "MIHA06", "Mt. Panorama Spore Area"),
    (0xEB, "ROOM20", "Digimon Curling"),
    (0xEC, "TEND01", "File City"),
    (0xED, "TEND02", "File City"),
    (0xEE, "TOPN01", "File City"),
    (0xF7, "MGEN06", "Mt. Infinity"),
    (0xF8, "MGEN07", "Mt. Infinity"),
    (0xF9, "MGEN08", "Mt. Infinity"),
    (0xFD, "MGEN09", "Mt. Infinity"),
    (0xFE, "MGEN10", "Mt. Infinity"),
];

const CONTROLS: &[(&str, u8, usize)] = &[
    ("color", 0x01, 1),
    ("ctrl02", 0x02, 1),
    ("raw", 0x03, 3),
    ("pstat_number", 0x04, 1),
    ("speaker_jijimon", 0x05, 1),
    ("speaker_player", 0x06, 1),
    ("digimon_name", 0x07, 1),
    ("move_name", 0x08, 1),
    ("item_name", 0x09, 1),
    ("money", 0x0A, 1),
    ("merit", 0x0B, 1),
    ("clear8", 0x0C, 1),
    ("newline", 0x0D, 1),
    ("clear11", 0x0E, 1),
    ("clear6", 0x0F, 1),
    ("shop_variable", 0x10, 1),
    ("bgm_name", 0x11, 1),
    ("tournament_name", 0x12, 1),
    ("tournaments_won", 0x13, 1),
    ("tournament_wins", 0x14, 1),
    ("tournaments_lost", 0x15, 1),
];

const COMPARISONS: &[(&str, u8)] = &[
    ("==", 0),
    ("!=", 1),
    (">=", 2),
    ("<=", 3),
    (">", 4),
    ("<", 5),
];

fn comparison(text: &str) -> Option<u8> {
    COMPARISONS
        .iter()
        .find(|(symbol, _)| *symbol == text)
        .map(|(_, code)| *code)
}

fn operand_spec(op: u8) -> Option<&'static [Operand]> {
    OPERANDS
        .iter()
        .find(|(code, _)| *code == op)
        .map(|(_, spec)| *spec)
}

fn operand_names(op: u8, count: usize) -> Vec<String> {
    let known: &[&str] = OPERAND_NAMES
        .iter()
        .find(|(code, _)| *code == op)
        .map(|(_, names)| *names)
        .unwrap_or(&[]);
    let mut names = Vec::with_capacity(count);
    for index in 0..count {
        let mut name = known
            .get(index)
            .map(|name| name.to_string())
            .unwrap_or_else(|| format!("arg{}", index + 1));
        if names.contains(&name) {
            name = format!("{name}{}", index + 1);
        }
        names.push(name);
    }
    names
}

fn opcode_by_name(name: &str) -> Option<u8> {
    OPCODES
        .iter()
        .find(|(mnemonic, _)| *mnemonic == name)
        .map(|(_, op)| *op)
}

// ---------------------------------------------------------------------------
// Parsed source
// ---------------------------------------------------------------------------

#[derive(Debug)]
struct Source {
    kind: Kind,
    header: Option<Header>,
    objects: Vec<Object>,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
enum Kind {
    Dg,
    Maphead,
}

#[derive(Debug)]
struct Header {
    names: Vec<String>,
    trailing: Vec<u8>,
}

#[derive(Debug)]
struct Object {
    name: String,
    entries: Vec<(u16, String)>,
    sections: Vec<Section>,
    raw: Option<Vec<Node>>,
}

#[derive(Debug)]
struct Section {
    label: String,
    nodes: Vec<Node>,
}

#[derive(Debug)]
enum Node {
    Instr {
        op: u8,
        spec: &'static [Operand],
        values: Vec<i64>,
    },
    Branch {
        op: u8,
        target: String,
    },
    FileBranch {
        op: u8,
        map: u16,
        section: u16,
    },
    Return {
        op: u8,
    },
    Switch {
        op: u8,
        pstat: u8,
        targets: Vec<String>,
    },
    End {
        op: u8,
    },
    Copy {
        source: String,
        length: usize,
    },
    Pad(usize),
    Byte(u8),
    Bytes(Vec<u8>),
    Data(Vec<u8>),
    Text {
        lines: Vec<String>,
        truncated: bool,
    },
    Selection {
        options: Vec<(String, String)>,
        extra: u16,
        truncated: bool,
    },
    If(Vec<Condition>),
    Script(Box<Object>),
}

#[derive(Debug)]
enum Condition {
    Branch {
        flag: u8,
        jump_if: bool,
        target: String,
    },
    Trigger {
        flag: u8,
        value: u16,
        set: bool,
    },
    Pstat {
        flag: u8,
        pstat: u8,
        cmp: u8,
        value: u8,
    },
    Stat {
        flag: u8,
        stat: u8,
        cmp: u8,
        value: i64,
    },
    Card {
        flag: u8,
        card: u8,
        cmp: u8,
        value: u16,
    },
    Item {
        flag: u8,
        item: u8,
        cmp: u8,
        value: u16,
    },
    Money {
        flag: u8,
        cmp: u8,
        value: u32,
    },
    Move {
        flag: u8,
        value: u8,
        negate: bool,
    },
    ConditionBit {
        flag: u8,
        mask: u8,
        negate: bool,
    },
}

impl Condition {
    fn size(&self) -> usize {
        match self {
            Condition::Stat { .. } | Condition::Card { .. } | Condition::Item { .. } => 6,
            Condition::Money { .. } => 8,
            _ => 4,
        }
    }
}

// ---------------------------------------------------------------------------
// Parser
// ---------------------------------------------------------------------------

struct Parser<'a> {
    file: &'a str,
    lines: Vec<&'a str>,
    index: usize,
}

impl<'a> Parser<'a> {
    fn new(source: &'a str, file: &'a str) -> Self {
        Parser {
            file,
            lines: source.lines().collect(),
            index: 0,
        }
    }

    fn where_(&self, line: usize) -> String {
        format!("{}:{}", self.file, line)
    }

    fn peek(&mut self) -> Option<(usize, &'a str)> {
        while self.index < self.lines.len() {
            let line = strip_comment(self.lines[self.index]);
            if line.trim().is_empty() {
                self.index += 1;
                continue;
            }
            return Some((self.index + 1, line));
        }
        None
    }

    fn next(&mut self) -> Result<(usize, &'a str), String> {
        let item = self
            .peek()
            .ok_or_else(|| format!("{}: unexpected end of file", self.file))?;
        self.index += 1;
        Ok(item)
    }

    fn parse(&mut self) -> Result<Source, String> {
        if self.lines.first().map(|line| line.trim()) != Some(HEADER) {
            return Err(format!("{}:1: expected {HEADER:?}", self.file));
        }
        self.index = 1;
        let mut kind = Kind::Maphead;
        if let Some((_, line)) = self.peek() {
            let trimmed = line.trim();
            if let Some(rest) = trimmed.strip_prefix(".scn ") {
                kind = match rest.trim() {
                    "DG" => Kind::Dg,
                    other => return Err(format!("{}: unknown .scn {other:?}", self.file)),
                };
                self.index += 1;
            }
        }
        let header = if kind == Kind::Dg {
            let (line, text) = self.next()?;
            if text.trim() != ".header" {
                return Err(format!("{}: expected .header", self.where_(line)));
            }
            Some(self.parse_header()?)
        } else {
            None
        };
        let mut objects = Vec::new();
        loop {
            let Some((line, text)) = self.peek() else {
                break;
            };
            self.index += 1;
            let trimmed = text.trim();
            if let Some(rest) = trimmed.strip_prefix(".map ") {
                let map_id = parse_number(rest)
                    .ok_or_else(|| format!("{}: invalid map id {rest:?}", self.where_(line)))?;
                objects.push(self.parse_object("m", map_id as u32, line)?);
            } else if let Some(rest) = trimmed.strip_prefix(".object ") {
                objects.push(self.parse_object(rest.trim(), 0, line)?);
            } else {
                return Err(format!(
                    "{}: unexpected top-level line {trimmed:?}",
                    self.where_(line)
                ));
            }
        }
        Ok(Source {
            kind,
            header,
            objects,
        })
    }

    fn parse_header(&mut self) -> Result<Header, String> {
        let (line, text) = self.next()?;
        if text.trim() != ".offsets" {
            return Err(format!("{}: expected .offsets", self.where_(line)));
        }
        let (line, text) = self.next()?;
        if text.trim() != ".names" {
            return Err(format!("{}: expected .names", self.where_(line)));
        }
        let mut names = Vec::new();
        loop {
            let (line, text) = self.next()?;
            if text.trim() == ".end" {
                break;
            }
            let (value, rest) = parse_quoted(text.trim())
                .ok_or_else(|| format!("{}: expected a quoted name", self.where_(line)))?;
            if !rest.is_empty() {
                return Err(format!("{}: trailing text after name", self.where_(line)));
            }
            names.push(value);
        }
        let (line, text) = self.next()?;
        let trimmed = text.trim();
        let payload = trimmed
            .strip_prefix(".bytes ")
            .ok_or_else(|| format!("{}: expected .bytes", self.where_(line)))?;
        let trailing = parse_hex_bytes(payload)
            .ok_or_else(|| format!("{}: invalid header bytes", self.where_(line)))?;
        let (line, text) = self.next()?;
        if text.trim() != ".end" {
            return Err(format!(
                "{}: expected .end after .header",
                self.where_(line)
            ));
        }
        Ok(Header { names, trailing })
    }

    /// Parse one object body.  `prefix` names map objects (`m7`); MAPHEAD keeps its name.
    fn parse_object(&mut self, name: &str, map_id: u32, _line: usize) -> Result<Object, String> {
        let name = if name == "m" {
            format!("m{map_id}")
        } else {
            name.to_string()
        };
        let mut object = Object {
            name,
            entries: Vec::new(),
            sections: Vec::new(),
            raw: None,
        };
        if let Some((_, text)) = self.peek() {
            if text.trim().starts_with(".copy") {
                let mut nodes = Vec::new();
                loop {
                    let (line, text) = self.next()?;
                    let trimmed = text.trim();
                    if trimmed == ".end" {
                        break;
                    }
                    nodes.push(self.parse_copy(trimmed, line)?);
                }
                object.raw = Some(nodes);
                return Ok(object);
            }
        }
        let (line, text) = self.next()?;
        if text.trim() != ".entries" {
            return Err(format!("{}: expected .entries", self.where_(line)));
        }
        loop {
            let (line, text) = self.next()?;
            let trimmed = text.trim();
            if trimmed == ".end" {
                break;
            }
            let (id, label) = trimmed
                .split_once("->")
                .ok_or_else(|| format!("{}: expected ID -> LABEL", self.where_(line)))?;
            let id = parse_number(id.trim())
                .filter(|value| (0..=0xffff).contains(value))
                .ok_or_else(|| format!("{}: invalid section id", self.where_(line)))?;
            object.entries.push((id as u16, label.trim().to_string()));
        }
        loop {
            let (line, text) = self.next()?;
            let trimmed = text.trim();
            if trimmed == ".end" {
                break;
            }
            let Some(label) = trimmed.strip_suffix(':') else {
                return Err(format!("{}: expected a section label", self.where_(line)));
            };
            let mut section = Section {
                label: label.trim().to_string(),
                nodes: Vec::new(),
            };
            loop {
                let Some((line, text)) = self.peek() else {
                    return Err(format!(
                        "{}: unterminated section {}",
                        self.file, section.label
                    ));
                };
                let trimmed = text.trim();
                if trimmed == ".end" || trimmed.ends_with(':') {
                    break;
                }
                self.index += 1;
                section.nodes.push(self.parse_node(trimmed, line)?);
            }
            object.sections.push(section);
        }
        Ok(object)
    }

    fn parse_copy(&self, text: &str, line: usize) -> Result<Node, String> {
        let parts: Vec<&str> = text.split_whitespace().collect();
        if parts.len() != 3 || parts[0] != ".copy" {
            return Err(format!(
                "{}: expected .copy SOURCE LENGTH",
                self.where_(line)
            ));
        }
        let length = parse_number(parts[2])
            .filter(|value| *value >= 0)
            .ok_or_else(|| format!("{}: invalid .copy length", self.where_(line)))?;
        Ok(Node::Copy {
            source: parts[1].to_string(),
            length: length as usize,
        })
    }

    fn parse_node(&mut self, trimmed: &str, line: usize) -> Result<Node, String> {
        if trimmed == ".if" {
            let mut conditions = Vec::new();
            loop {
                let (line, text) = self.next()?;
                if text.trim() == ".end" {
                    break;
                }
                conditions.push(self.parse_condition(text.trim(), line)?);
            }
            return Ok(Node::If(conditions));
        }
        if trimmed == ".text" {
            let mut lines = Vec::new();
            let mut truncated = false;
            loop {
                let (line, text) = self.next()?;
                let trimmed = text.trim();
                if trimmed == ".end" {
                    break;
                }
                if trimmed == ".truncated" {
                    truncated = true;
                    continue;
                }
                let (value, rest) = parse_quoted(trimmed)
                    .ok_or_else(|| format!("{}: expected a text line", self.where_(line)))?;
                if !rest.is_empty() {
                    return Err(format!("{}: trailing text after string", self.where_(line)));
                }
                lines.push(value);
            }
            return Ok(Node::Text { lines, truncated });
        }
        if trimmed == ".selection" {
            let mut options = Vec::new();
            let mut extra = 0x1A;
            let mut truncated = false;
            loop {
                let (line, text) = self.next()?;
                let trimmed = text.trim();
                if trimmed == ".end" {
                    break;
                }
                if trimmed == ".truncated" {
                    truncated = true;
                    continue;
                }
                if let Some(rest) = trimmed.strip_prefix(".extra ") {
                    extra = parse_number(rest)
                        .filter(|value| (0..=0xffff).contains(value))
                        .ok_or_else(|| format!("{}: invalid .extra", self.where_(line)))?
                        as u16;
                    continue;
                }
                let (value, rest) = parse_quoted(trimmed)
                    .ok_or_else(|| format!("{}: expected a selection line", self.where_(line)))?;
                let Some(target) = rest.strip_prefix("->") else {
                    return Err(format!("{}: expected TEXT -> LABEL", self.where_(line)));
                };
                options.push((value, target.trim().to_string()));
            }
            if options.len() > 255 {
                return Err(format!(
                    "{}: a selection has at most 255 options",
                    self.file
                ));
            }
            return Ok(Node::Selection {
                options,
                extra,
                truncated,
            });
        }
        if trimmed.starts_with(".copy ") {
            return self.parse_copy(trimmed, line);
        }
        if let Some(rest) = trimmed.strip_prefix(".pad ") {
            let length = parse_number(rest)
                .filter(|value| *value >= 0)
                .ok_or_else(|| format!("{}: invalid .pad", self.where_(line)))?;
            return Ok(Node::Pad(length as usize));
        }
        if let Some(rest) = trimmed.strip_prefix(".byte ") {
            let value = parse_number(rest)
                .filter(|value| (0..=0xff).contains(value))
                .ok_or_else(|| format!("{}: invalid .byte", self.where_(line)))?;
            return Ok(Node::Byte(value as u8));
        }
        if let Some(rest) = trimmed.strip_prefix(".bytes ") {
            let payload = parse_hex_bytes(rest)
                .ok_or_else(|| format!("{}: invalid .bytes", self.where_(line)))?;
            return Ok(Node::Bytes(payload));
        }
        if let Some(rest) = trimmed.strip_prefix(".data ") {
            let payload = parse_hex_bytes(rest)
                .ok_or_else(|| format!("{}: invalid .data", self.where_(line)))?;
            return Ok(Node::Data(payload));
        }
        if let Some(rest) = trimmed.strip_prefix(".script ") {
            let nested = self.parse_object(rest.trim(), 0, line)?;
            return Ok(Node::Script(Box::new(nested)));
        }
        self.parse_instruction(trimmed, line)
    }

    fn parse_condition(&self, text: &str, line: usize) -> Result<Condition, String> {
        let mut parts: Vec<String> = split_operands(text);
        if parts.is_empty() {
            return Err(format!("{}: empty condition", self.where_(line)));
        }
        let flag = match parts[0].as_str() {
            "THEN" => {
                parts.remove(0);
                0x00
            }
            "AND" => {
                parts.remove(0);
                0x80
            }
            "OR" => {
                parts.remove(0);
                0x40
            }
            _ => 0x00,
        };
        let error = |expected: &str| format!("{}: expected {expected}", self.where_(line));
        if parts.first().map(String::as_str) == Some("if") {
            if parts.len() != 4 || parts[2] != "goto" {
                return Err(error("if true|false goto LABEL"));
            }
            return Ok(Condition::Branch {
                flag,
                jump_if: parts[1] == "true",
                target: parts[3].to_string(),
            });
        }
        let kind = parts[0].as_str();
        let number = |text: &str| {
            parse_number(text).ok_or_else(|| format!("{}: invalid number", self.where_(line)))
        };
        match kind {
            "trigger" => {
                if parts.len() != 3 {
                    return Err(error("trigger N set|clear"));
                }
                let set = match parts[2].as_str() {
                    "set" => true,
                    "clear" => false,
                    _ => return Err(error("trigger N set|clear")),
                };
                Ok(Condition::Trigger {
                    flag,
                    value: u16_of(number(&parts[1])?, "trigger", self.file)?,
                    set,
                })
            }
            "pstat" | "stat" | "card" | "item" => {
                if parts.len() != 4 {
                    return Err(error("KIND N CMP VALUE"));
                }
                let cmp = comparison(&parts[2]).ok_or_else(|| error("a comparison"))?;
                let value = number(&parts[3])?;
                let key = if kind == "item" {
                    match parse_number(&parts[1]) {
                        Some(value) => value,
                        None => resolve_named(ITEM_NAMES, "item", &parts[1])
                            .map_err(|message| format!("{}: {message}", self.where_(line)))?,
                    }
                } else {
                    number(&parts[1])?
                };
                Ok(match kind {
                    "pstat" => Condition::Pstat {
                        flag,
                        pstat: u8_of(key, "pstat", self.file)?,
                        cmp,
                        value: u8_of(value, "pstat value", self.file)?,
                    },
                    "stat" => Condition::Stat {
                        flag,
                        stat: u8_of(key, "stat", self.file)?,
                        cmp,
                        value,
                    },
                    "card" => Condition::Card {
                        flag,
                        card: u8_of(key, "card", self.file)?,
                        cmp,
                        value: u16_of(value, "card value", self.file)?,
                    },
                    _ => Condition::Item {
                        flag,
                        item: u8_of(key, "item", self.file)?,
                        cmp,
                        value: u16_of(value, "item value", self.file)?,
                    },
                })
            }
            "money" => {
                if parts.len() != 3 {
                    return Err(error("money CMP VALUE"));
                }
                let cmp = comparison(&parts[1]).ok_or_else(|| error("a comparison"))?;
                let value = number(&parts[2])?;
                let value = u32::try_from(value)
                    .map_err(|_| format!("{}: money value does not fit", self.file))?;
                Ok(Condition::Money { flag, cmp, value })
            }
            "move" | "condition" => {
                if parts.len() != 2 && parts.len() != 3 {
                    return Err(error("move N [not]"));
                }
                if parts.len() == 3 && parts[2] != "not" {
                    return Err(error("move N [not]"));
                }
                let value = if kind == "move" {
                    match parse_number(&parts[1]) {
                        Some(value) => value,
                        None => resolve_named(MOVE_NAMES, "move", &parts[1])
                            .map_err(|message| format!("{}: {message}", self.where_(line)))?,
                    }
                } else {
                    number(&parts[1])?
                };
                let value = u8_of(value, "condition value", self.file)?;
                let negate = parts.len() == 3;
                if kind == "move" {
                    Ok(Condition::Move {
                        flag,
                        value,
                        negate,
                    })
                } else {
                    Ok(Condition::ConditionBit {
                        flag,
                        mask: value,
                        negate,
                    })
                }
            }
            other => Err(format!(
                "{}: unknown condition {other:?}",
                self.where_(line)
            )),
        }
    }

    fn parse_instruction(&mut self, text: &str, line: usize) -> Result<Node, String> {
        let mut parts = text.splitn(2, char::is_whitespace);
        let mnemonic = parts.next().unwrap_or("");
        let rest = parts.next().unwrap_or("").trim();
        let op = opcode_by_name(mnemonic)
            .ok_or_else(|| format!("{}: unknown mnemonic {mnemonic:?}", self.where_(line)))?;
        let error = |message: String| format!("{}: {message}", self.where_(line));
        match op {
            0x13 | 0x16 => {
                if rest.is_empty() {
                    return Err(error(format!("{mnemonic} needs a target")));
                }
                Ok(Node::Branch {
                    op,
                    target: rest.to_string(),
                })
            }
            0x14 | 0x17 => {
                let fields: Vec<&str> = rest.split_whitespace().collect();
                let mut map = None;
                let mut section = None;
                for field in fields {
                    if let Some(value) = field.strip_prefix("map=") {
                        map = Some(match parse_number(value) {
                            Some(value) => value,
                            None => resolve_map(value).map_err(|message| error(message))?,
                        });
                    } else if let Some(value) = field.strip_prefix("section=") {
                        section = parse_number(value);
                    }
                }
                let (Some(map), Some(section)) = (map, section) else {
                    return Err(error("expected map=N section=N".to_string()));
                };
                Ok(Node::FileBranch {
                    op,
                    map: u16_of(map, "map", self.file)?,
                    section: u16_of(section, "section", self.file)?,
                })
            }
            0x15 => Ok(Node::Return { op }),
            0x18 => {
                let mut pstat = None;
                let mut targets = Vec::new();
                for (index, field) in rest.split_whitespace().enumerate() {
                    if index == 0 {
                        let Some(value) = field.strip_prefix("pstat=") else {
                            return Err(error("expected pstat=N [TARGET...]".to_string()));
                        };
                        pstat = parse_number(value);
                    } else {
                        targets.push(field.to_string());
                    }
                }
                let Some(pstat) = pstat else {
                    return Err(error("expected pstat=N [TARGET...]".to_string()));
                };
                Ok(Node::Switch {
                    op,
                    pstat: u8_of(pstat, "pstat", self.file)?,
                    targets,
                })
            }
            0xFE | 0xFF => Ok(Node::End { op }),
            _ => {
                let spec = operand_spec(op)
                    .ok_or_else(|| error(format!("no operand layout for {mnemonic}")))?;
                let count = spec.iter().filter(|kind| **kind != Operand::Pad).count();
                let names = operand_names(op, count);
                let mut values = HashMap::new();
                for token in split_operands(rest) {
                    let Some((name, value)) = token.split_once('=') else {
                        return Err(error(format!("expected name=value, got {token:?}")));
                    };
                    if !names.iter().any(|known| known == name) {
                        return Err(error(format!("unknown operand {name:?}")));
                    }
                    let value = match parse_number(value) {
                        Some(value) => value,
                        None if name == "map" => {
                            resolve_map(value).map_err(|message| error(message))?
                        }
                        None => match named_table(name) {
                            Some(table) => resolve_named(table, name, value)
                                .map_err(|message| error(message))?,
                            None => return Err(error(format!("invalid number in {token:?}"))),
                        },
                    };
                    values.insert(name.to_string(), value);
                }
                let mut ordered = Vec::with_capacity(spec.len());
                let mut name_index = 0;
                for kind in spec {
                    if *kind == Operand::Pad {
                        ordered.push(0);
                    } else {
                        let name = &names[name_index];
                        name_index += 1;
                        let Some(value) = values.get(name) else {
                            return Err(error(format!("missing operand {name:?}")));
                        };
                        ordered.push(*value);
                    }
                }
                Ok(Node::Instr {
                    op,
                    spec,
                    values: ordered,
                })
            }
        }
    }
}

// ---------------------------------------------------------------------------
// Small parsers
// ---------------------------------------------------------------------------

/// Drop a trailing ``#`` comment, keeping hashes inside quoted text.
fn strip_comment(line: &str) -> &str {
    let mut quoted = false;
    let mut escaped = false;
    for (index, ch) in line.char_indices() {
        if escaped {
            escaped = false;
            continue;
        }
        match ch {
            '\\' => escaped = true,
            '"' => quoted = !quoted,
            '#' if !quoted => return &line[..index],
            _ => {}
        }
    }
    line
}

/// Split ``name=value`` tokens, allowing quoted values with spaces.
fn split_operands(text: &str) -> Vec<String> {
    let mut tokens = Vec::new();
    let mut current = String::new();
    let mut quoted = false;
    let mut escaped = false;
    for ch in text.chars() {
        if escaped {
            current.push(ch);
            escaped = false;
        } else if ch == '\\' {
            escaped = true;
        } else if ch == '"' {
            quoted = !quoted;
        } else if ch.is_whitespace() && !quoted {
            if !current.is_empty() {
                tokens.push(std::mem::take(&mut current));
            }
        } else {
            current.push(ch);
        }
    }
    if !current.is_empty() {
        tokens.push(current);
    }
    tokens
}

/// A case-insensitive operand spelling for a name with spaces or punctuation.
fn normalize_name(name: &str) -> String {
    let mut out = String::new();
    let mut separator = false;
    for ch in name.chars() {
        if ch.is_alphanumeric() {
            out.extend(ch.to_lowercase());
            separator = false;
        } else if !separator {
            out.push('_');
            separator = true;
        }
    }
    out.trim_matches('_').to_string()
}

/// Resolve a US name in one of the operand tables; related ids can share a
/// name, which stays ambiguous.
fn resolve_named(table: &[(u8, &str)], kind: &str, value: &str) -> Result<i64, String> {
    let wanted = normalize_name(value);
    let matches: Vec<u8> = table
        .iter()
        .filter(|(_, name)| normalize_name(name) == wanted)
        .map(|(id, _)| *id)
        .collect();
    match matches.len() {
        1 => Ok(i64::from(matches[0])),
        0 => Err(format!("unknown {kind} {value:?}")),
        _ => {
            let options = matches
                .iter()
                .map(|id| format!("{id:#04x}"))
                .collect::<Vec<_>>()
                .join(", ");
            Err(format!(
                "{kind} name {value:?} is ambiguous ({options}); write the id instead"
            ))
        }
    }
}

fn resolve_map(value: &str) -> Result<i64, String> {
    let wanted = normalize_name(value);
    let mut matches: Vec<u8> = MAP_NAMES
        .iter()
        .filter(|(_, filename, _)| normalize_name(filename) == wanted)
        .map(|(id, _, _)| *id)
        .collect();
    if matches.is_empty() {
        matches = MAP_NAMES
            .iter()
            .filter(|(_, _, display)| !display.is_empty() && normalize_name(display) == wanted)
            .map(|(id, _, _)| *id)
            .collect();
    }
    match matches.len() {
        1 => Ok(i64::from(matches[0])),
        0 => Err(format!("unknown map {value:?}")),
        _ => {
            let options = matches
                .iter()
                .map(|id| format!("{id:#04x}"))
                .collect::<Vec<_>>()
                .join(", ");
            Err(format!(
                "map name {value:?} is ambiguous ({options}); write the id or the map filename"
            ))
        }
    }
}

fn named_table(kind: &str) -> Option<&'static [(u8, &'static str)]> {
    match kind {
        "digimon" => Some(DIGIMON_NAMES),
        "item" => Some(ITEM_NAMES),
        "move" => Some(MOVE_NAMES),
        _ => None,
    }
}

fn parse_number(text: &str) -> Option<i64> {
    let text = text.trim();
    let (negative, digits) = match text.strip_prefix('-') {
        Some(rest) => (true, rest),
        None => match text.strip_prefix('+') {
            Some(rest) => (false, rest),
            None => (false, text),
        },
    };
    let (radix, digits) = if let Some(rest) = digits
        .strip_prefix("0x")
        .or_else(|| digits.strip_prefix("0X"))
    {
        (16, rest)
    } else if let Some(rest) = digits
        .strip_prefix("0o")
        .or_else(|| digits.strip_prefix("0O"))
    {
        (8, rest)
    } else if let Some(rest) = digits
        .strip_prefix("0b")
        .or_else(|| digits.strip_prefix("0B"))
    {
        (2, rest)
    } else {
        (10, digits)
    };
    if digits.is_empty() || !digits.chars().all(|c| c.is_digit(radix)) {
        return None;
    }
    let value = i64::from_str_radix(digits, radix).ok()?;
    Some(if negative { -value } else { value })
}

fn u8_of(value: i64, what: &str, file: &str) -> Result<u8, String> {
    u8::try_from(value).map_err(|_| format!("{file}: {what} {value} does not fit in a byte"))
}

fn u16_of(value: i64, what: &str, file: &str) -> Result<u16, String> {
    u16::try_from(value).map_err(|_| format!("{file}: {what} {value} does not fit in 16 bits"))
}

fn parse_hex_bytes(text: &str) -> Option<Vec<u8>> {
    // Like Python's bytes.fromhex: hexadecimal digits, whitespace allowed between bytes.
    let compact: String = text.split_whitespace().collect();
    if compact.is_empty() || compact.len() % 2 != 0 {
        return None;
    }
    let mut out = Vec::with_capacity(compact.len() / 2);
    for pair in compact.as_bytes().chunks(2) {
        let pair = std::str::from_utf8(pair).ok()?;
        out.push(u8::from_str_radix(pair, 16).ok()?);
    }
    Some(out)
}

/// Parse a quoted string, returning its value and the remaining text.
fn parse_quoted(text: &str) -> Option<(String, String)> {
    let mut chars = text.char_indices();
    if chars.next()?.1 != '"' {
        return None;
    }
    let mut value = String::new();
    while let Some((index, ch)) = chars.next() {
        match ch {
            '"' => return Some((value, text[index + 1..].trim().to_string())),
            '\\' => {
                let (_, escaped) = chars.next()?;
                if escaped == '"' || escaped == '\\' {
                    value.push(escaped);
                } else {
                    value.push('\\');
                    value.push(escaped);
                }
            }
            _ => value.push(ch),
        }
    }
    None
}

/// The game font's ASCII -> Shift-JIS glyph mapping (`convertAsciiToJis` in
/// `sjis.c`). The scene text spells the apostrophe with glyph 0x8175.
fn ascii_to_jis(ch: u8) -> Option<u16> {
    match ch {
        0x27 => Some(0x8175),
        0x30..=0x39 => Some(0x824f + u16::from(ch - 0x30)),
        0x41..=0x5a => Some(0x8260 + u16::from(ch - 0x41)),
        0x61..=0x7a => Some(0x8281 + u16::from(ch - 0x61)),
        _ => ASCII_SPECIAL
            .iter()
            .find(|(ascii, _)| *ascii == ch)
            .map(|(_, jis)| *jis),
    }
}

/// Encode one glyph as a two-byte CP932/Shift-JIS unit.
fn encode_glyph(text: &str) -> Result<[u8; 2], String> {
    if text.len() == 1 && text.as_bytes()[0] < 0x80 {
        if let Some(code) = ascii_to_jis(text.as_bytes()[0]) {
            return Ok([(code >> 8) as u8, code as u8]);
        }
    }
    let (bytes, _, errors) = SHIFT_JIS.encode(text);
    if errors || bytes.len() != 2 {
        return Err(format!(
            "{text:?} is not a two-byte CP932 character (use {{glyph:....}} \
             for a raw pair)"
        ));
    }
    Ok([bytes[0], bytes[1]])
}

/// Parse a dialog line into its exact script bytes.
fn encode_text_line(line: &str) -> Result<Vec<u8>, String> {
    let mut out = Vec::new();
    let mut pos = 0;
    while pos < line.len() {
        let ch = line[pos..].chars().next().unwrap();
        match ch {
            '\\' => {
                let escaped = line[pos + 1..]
                    .chars()
                    .next()
                    .ok_or_else(|| "trailing backslash in text".to_string())?;
                if !matches!(escaped, '"' | '\\' | '{' | '}') {
                    return Err(format!("unknown escape \\{escaped}"));
                }
                out.extend_from_slice(&encode_glyph(&escaped.to_string())?);
                pos += 1 + escaped.len_utf8();
            }
            '{' => {
                let end = line[pos + 1..]
                    .find('}')
                    .ok_or_else(|| "unterminated {...} control".to_string())?;
                let token = &line[pos + 1..pos + 1 + end];
                let (name, args) = match token.split_once(':') {
                    Some((name, args)) => (name, args.trim()),
                    None => (token, ""),
                };
                if name == "glyph" {
                    let raw =
                        parse_hex_bytes(args).ok_or_else(|| "invalid {glyph:...}".to_string())?;
                    if raw.len() != 2 {
                        return Err("{glyph:...} needs two bytes".to_string());
                    }
                    out.extend_from_slice(&raw);
                } else if name == "bytes" {
                    out.extend_from_slice(
                        &parse_hex_bytes(args).ok_or_else(|| "invalid {bytes:...}".to_string())?,
                    );
                } else if let Some((_, byte, count)) =
                    CONTROLS.iter().find(|(control, _, _)| *control == name)
                {
                    let raw = if args.is_empty() {
                        Vec::new()
                    } else {
                        parse_hex_bytes(args).ok_or_else(|| format!("invalid {{{name}:...}}"))?
                    };
                    if raw.len() != *count {
                        return Err(format!("{{{name}}} needs {count} argument byte(s)"));
                    }
                    out.push(*byte);
                    out.extend_from_slice(&raw);
                } else {
                    return Err(format!("unknown control {{{name}}}"));
                }
                pos += 1 + end + 1;
            }
            _ => {
                let mut buffer = [0u8; 4];
                out.extend_from_slice(&encode_glyph(ch.encode_utf8(&mut buffer))?);
                pos += ch.len_utf8();
            }
        }
    }
    Ok(out)
}

// ---------------------------------------------------------------------------
// Layout
// ---------------------------------------------------------------------------

struct Layout {
    size: usize,
    labels: Vec<(String, usize)>,
}

fn node_size(node: &Node) -> Result<usize, String> {
    Ok(match node {
        Node::Instr { spec, .. } => 1 + spec.iter().map(|kind| kind.width()).sum::<usize>(),
        Node::Branch { .. } => 4,
        Node::FileBranch { .. } => 6,
        Node::Return { .. } => 2,
        Node::Switch { targets, .. } => 4 + 2 * targets.len(),
        Node::End { .. } => 2,
        Node::Copy { length, .. } => *length,
        Node::Pad(length) => *length,
        Node::Byte(_) => 1,
        Node::Bytes(payload) => payload.len(),
        Node::Data(payload) => 2 + payload.len() + 1,
        Node::Text { lines, truncated } => {
            let body = lines
                .iter()
                .map(|line| encode_text_line(line).map(|bytes| bytes.len()))
                .collect::<Result<Vec<_>, _>>()?
                .into_iter()
                .sum::<usize>();
            2 + body + 2 * lines.len().saturating_sub(1) + if *truncated { 0 } else { 4 }
        }
        Node::Selection {
            options, truncated, ..
        } => {
            let body = options
                .iter()
                .map(|(line, _)| encode_text_line(line).map(|bytes| bytes.len()))
                .collect::<Result<Vec<_>, _>>()?
                .into_iter()
                .sum::<usize>();
            2 + 2 * options.len()
                + 2
                + body
                + 2 * options.len().saturating_sub(1)
                + if *truncated { 0 } else { 4 }
        }
        Node::If(conditions) => 2 + conditions.iter().map(Condition::size).sum::<usize>() + 2,
        Node::Script(_) => return Err("nested .script must be laid out by layout_object".into()),
    })
}

fn layout_object(object: &Object) -> Result<Layout, String> {
    let mut labels = vec![(object.name.clone(), 0usize)];
    if let Some(nodes) = &object.raw {
        let mut size = 0;
        for node in nodes {
            size += node_size(node)?;
        }
        return Ok(Layout { size, labels });
    }
    let table_size = 2 + 4 * object.entries.len() + 2;
    let mut offset = table_size;
    for section in &object.sections {
        if labels.iter().any(|(label, _)| *label == section.label) {
            return Err(format!(
                "{}: duplicate label {}",
                object.name, section.label
            ));
        }
        labels.push((section.label.clone(), offset));
        for node in &section.nodes {
            let size = if let Node::Script(nested) = node {
                let nested = layout_object(nested)?;
                for (label, nested_offset) in &nested.labels {
                    if labels.iter().any(|(known, _)| known == label) {
                        return Err(format!("{}: duplicate label {label}", object.name));
                    }
                    labels.push((label.clone(), offset + nested_offset));
                }
                nested.size
            } else {
                node_size(node)?
            };
            offset += size;
        }
    }
    Ok(Layout {
        size: offset,
        labels,
    })
}

// ---------------------------------------------------------------------------
// Emitter
// ---------------------------------------------------------------------------

struct Emitter<'a> {
    file: &'a str,
    labels: HashMap<String, usize>,
    output: Vec<u8>,
    external: &'a [(&'a str, &'a [u8])],
}

impl<'a> Emitter<'a> {
    fn put(&mut self, bytes: &[u8]) {
        self.output.extend_from_slice(bytes);
    }

    fn put_u16(&mut self, value: u16) {
        self.put(&value.to_le_bytes());
    }

    fn resolve(&self, text: &str) -> Result<(String, i64), String> {
        let (label, offset) = match text.split_once('+') {
            Some((label, offset)) => (label.trim(), parse_number(offset).unwrap_or(i64::MIN)),
            None => (text.trim(), 0),
        };
        if label.is_empty()
            || !label.starts_with(|c: char| c.is_ascii_alphabetic() || c == '_')
            || !label.chars().all(|c| c.is_ascii_alphanumeric() || c == '_')
        {
            return Err(format!("{}: invalid label {label:?}", self.file));
        }
        if text.contains('+') && offset == i64::MIN {
            return Err(format!("{}: invalid offset in {text:?}", self.file));
        }
        Ok((label.to_string(), offset))
    }

    fn target(&self, text: &str, base: usize) -> Result<u16, String> {
        let (label, offset) = self.resolve(text)?;
        let Some(address) = self.labels.get(&label) else {
            return Err(format!("{}: unknown label {label:?}", self.file));
        };
        let value = *address as i64 - base as i64 + offset;
        if !(0..=0xffff).contains(&value) {
            return Err(format!("{}: target {text:?} is out of range", self.file));
        }
        Ok(value as u16)
    }

    fn copy(&mut self, source: &str, length: usize) -> Result<(), String> {
        let (label, offset) = self.resolve(source)?;
        if let Some(address) = self.labels.get(&label) {
            let start = *address as i64 + offset;
            if start < 0 || start as usize >= self.output.len() {
                return Err(format!(
                    "{}: .copy source {source} is not assembled yet",
                    self.file
                ));
            }
            let start = start as usize;
            if start + length <= self.output.len() {
                let bytes = self.output[start..start + length].to_vec();
                self.put(&bytes);
            } else {
                // Overlapping copy: each byte may come from one just written.
                for index in 0..length {
                    let byte = self.output[start + index];
                    self.output.push(byte);
                }
            }
            return Ok(());
        }
        if let Some((_, data)) = self.external.iter().find(|(name, _)| *name == label) {
            let start = offset.max(0) as usize;
            let Some(end) = start.checked_add(length) else {
                return Err(format!("{}: .copy source {source} overflows", self.file));
            };
            let Some(bytes) = data.get(start..end) else {
                return Err(format!(
                    "{}: .copy source {source} is out of range",
                    self.file
                ));
            };
            let bytes = bytes.to_vec();
            self.put(&bytes);
            return Ok(());
        }
        Err(format!("{}: unknown copy source {label:?}", self.file))
    }

    fn emit_object(&mut self, object: &Object, base: usize) -> Result<(), String> {
        if let Some(nodes) = &object.raw {
            for node in nodes {
                self.emit_node(node, base)?;
            }
            return Ok(());
        }
        let table_size = 2 + 4 * object.entries.len() + 2;
        self.put_u16(table_size as u16);
        for (id, label) in &object.entries {
            let Some(address) = self.labels.get(label) else {
                return Err(format!("{}: unknown section label {label:?}", self.file));
            };
            let offset = *address as i64 - base as i64;
            if !(0..=0xffff).contains(&offset) {
                return Err(format!("{}: section {label} is out of range", self.file));
            }
            self.put_u16(*id);
            self.put_u16(offset as u16);
        }
        self.put_u16(0xffff);
        for section in &object.sections {
            for node in &section.nodes {
                self.emit_node(node, base)?;
            }
        }
        Ok(())
    }

    fn emit_node(&mut self, node: &Node, base: usize) -> Result<(), String> {
        match node {
            Node::Instr { op, spec, values } => {
                self.put(&[*op]);
                for (kind, value) in spec.iter().zip(values) {
                    let width = kind.width();
                    let bytes = match (kind.signed(), width) {
                        (true, 1) => i8::try_from(*value)
                            .map_err(|_| format!("{}: operand {value} does not fit", self.file))?
                            .to_le_bytes()
                            .to_vec(),
                        (true, 2) => i16::try_from(*value)
                            .map_err(|_| format!("{}: operand {value} does not fit", self.file))?
                            .to_le_bytes()
                            .to_vec(),
                        (true, 4) => i32::try_from(*value)
                            .map_err(|_| format!("{}: operand {value} does not fit", self.file))?
                            .to_le_bytes()
                            .to_vec(),
                        (false, 1) => {
                            vec![u8::try_from(*value).map_err(|_| {
                                format!("{}: operand {value} does not fit", self.file)
                            })?]
                        }
                        (false, 2) => u16::try_from(*value)
                            .map_err(|_| format!("{}: operand {value} does not fit", self.file))?
                            .to_le_bytes()
                            .to_vec(),
                        _ => u32::try_from(*value)
                            .map_err(|_| format!("{}: operand {value} does not fit", self.file))?
                            .to_le_bytes()
                            .to_vec(),
                    };
                    self.put(&bytes);
                }
            }
            Node::Branch { op, target } => {
                self.put(&[*op, 0]);
                let value = self.target(target, base)?;
                self.put_u16(value);
            }
            Node::FileBranch { op, map, section } => {
                self.put(&[*op, 0]);
                self.put_u16(*map);
                self.put_u16(*section);
            }
            Node::Return { op } => self.put(&[*op, 0]),
            Node::Switch { op, pstat, targets } => {
                self.put(&[*op, *pstat]);
                self.put_u16(targets.len() as u16);
                for target in targets {
                    let value = self.target(target, base)?;
                    self.put_u16(value);
                }
            }
            Node::End { op } => self.put(&[*op, 0]),
            Node::Copy { source, length } => self.copy(source, *length)?,
            Node::Pad(length) => self.put(&vec![0; *length]),
            Node::Byte(value) => self.put(&[*value]),
            Node::Bytes(payload) => self.put(payload),
            Node::Data(payload) => {
                self.put(&[0x6b, 0x00]);
                self.put(payload);
                self.put(&[0xff]);
            }
            Node::Text { lines, truncated } => {
                self.put(&[0x1a, 0x00]);
                for (index, line) in lines.iter().enumerate() {
                    self.put(&encode_text_line(line)?);
                    if index + 1 < lines.len() {
                        self.put(&[0x0d, 0x00]);
                    }
                }
                if !truncated {
                    self.put(&[0x0d, 0x00, 0x00, 0x00]);
                }
            }
            Node::Selection {
                options,
                extra,
                truncated,
            } => {
                self.put(&[0x10, options.len() as u8]);
                for (_, target) in options {
                    let value = self.target(target, base)?;
                    self.put_u16(value);
                }
                self.put_u16(*extra);
                for (index, (line, _)) in options.iter().enumerate() {
                    self.put(&encode_text_line(line)?);
                    if index + 1 < options.len() {
                        self.put(&[0x0d, 0x00]);
                    }
                }
                if !truncated {
                    self.put(&[0x0d, 0x00, 0x00, 0x00]);
                }
            }
            Node::If(conditions) => {
                self.put(&[0x19, 0x00]);
                for condition in conditions {
                    self.emit_condition(condition, base)?;
                }
                self.put(&[0x19, 0x00]);
            }
            Node::Script(nested) => {
                let Some(address) = self.labels.get(&nested.name).copied() else {
                    return Err(format!("{}: unknown script {}", self.file, nested.name));
                };
                self.emit_object(nested, address)?;
            }
        }
        Ok(())
    }

    fn emit_condition(&mut self, condition: &Condition, base: usize) -> Result<(), String> {
        match condition {
            Condition::Branch {
                flag,
                jump_if,
                target,
            } => {
                let op = if *jump_if { 0x10 } else { 0x18 };
                self.put(&[op | flag, 0]);
                let value = self.target(target, base)?;
                self.put_u16(value);
            }
            Condition::Trigger { flag, value, set } => {
                self.put(&[flag | if *set { 0 } else { 1 }, 0]);
                self.put_u16(*value);
            }
            Condition::Pstat {
                flag,
                pstat,
                cmp,
                value,
            } => {
                self.put(&[flag | 0x08 | cmp, 0, *pstat, *value]);
            }
            Condition::Stat {
                flag,
                stat,
                cmp,
                value,
            } => {
                self.put(&[flag | 0x20, 0, *stat, *cmp]);
                let value = i16::try_from(*value)
                    .map_err(|_| format!("{}: stat value does not fit", self.file))?;
                self.put(&value.to_le_bytes());
            }
            Condition::Card {
                flag,
                card,
                cmp,
                value,
            } => {
                self.put(&[flag | 0x21, 0, *card, *cmp]);
                self.put_u16(*value);
            }
            Condition::Move {
                flag,
                value,
                negate,
            } => {
                self.put(&[flag | 0x22, 0, *value, u8::from(*negate)]);
            }
            Condition::ConditionBit { flag, mask, negate } => {
                self.put(&[flag | 0x23, 0, *mask, u8::from(*negate)]);
            }
            Condition::Item {
                flag,
                item,
                cmp,
                value,
            } => {
                self.put(&[flag | 0x24, 0, *item, *cmp]);
                self.put_u16(*value);
            }
            Condition::Money { flag, cmp, value } => {
                self.put(&[flag | 0x25, 0, 0, *cmp]);
                self.put(&value.to_le_bytes());
            }
        }
        Ok(())
    }
}

// ---------------------------------------------------------------------------
// Entry point
// ---------------------------------------------------------------------------

/// Assemble a script source.  `external` supplies already assembled files that
/// `DG.txt` refers to by name (`MAPHEAD`).
pub fn assemble(source: &str, file: &str, external: &[(&str, &[u8])]) -> Result<Vec<u8>, String> {
    let mut parser = Parser::new(source, file);
    let parsed = parser.parse()?;
    let mut labels = HashMap::new();
    let mut sizes = Vec::new();
    let mut base = if parsed.kind == Kind::Dg {
        DG_HEADER_SIZE
    } else {
        0
    };
    for object in &parsed.objects {
        let layout = layout_object(object)?;
        if labels.contains_key(&object.name) {
            return Err(format!("{file}: duplicate object {}", object.name));
        }
        labels.insert(object.name.clone(), base);
        for (label, offset) in &layout.labels {
            if label != &object.name && labels.insert(label.clone(), base + offset).is_some() {
                return Err(format!("{file}: duplicate label {label}"));
            }
        }
        sizes.push(layout.size);
        base += layout.size;
    }
    let eof = base;
    let mut output = Vec::new();
    if parsed.kind == Kind::Dg {
        let header = parsed
            .header
            .as_ref()
            .ok_or_else(|| format!("{file}: DG source needs a .header"))?;
        if parsed.objects.len() != DG_OFFSET_ENTRIES - 1 {
            return Err(format!(
                "{file}: DG needs {} map objects, found {}",
                DG_OFFSET_ENTRIES - 1,
                parsed.objects.len()
            ));
        }
        if header.names.len() != DG_NAMES_COUNT {
            return Err(format!(
                "{file}: DG header needs {DG_NAMES_COUNT} file names"
            ));
        }
        for object in &parsed.objects {
            let offset = labels[&object.name] as u32;
            output.extend_from_slice(&offset.to_le_bytes());
        }
        output.extend_from_slice(&(eof as u32).to_le_bytes());
        if output.len() != DG_NAMES_OFFSET {
            return Err(format!(
                "{file}: offset table does not end at {DG_NAMES_OFFSET:#x}"
            ));
        }
        for name in &header.names {
            let raw = name.as_bytes();
            if raw.len() > 32 || !raw.is_ascii() {
                return Err(format!("{file}: invalid file name {name:?}"));
            }
            output.extend_from_slice(raw);
            output.resize(output.len() + 32 - raw.len(), 0);
        }
        output.extend_from_slice(&header.trailing);
        if output.len() != DG_HEADER_SIZE {
            return Err(format!(
                "{file}: DG header is {:#x} bytes, expected {DG_HEADER_SIZE:#x}",
                output.len()
            ));
        }
        labels.insert("DG".to_string(), 0);
    }
    let mut emitter = Emitter {
        file,
        labels,
        output,
        external,
    };
    for (object, size) in parsed.objects.iter().zip(&sizes) {
        let base = emitter.labels[&object.name];
        let before = emitter.output.len();
        emitter.emit_object(object, base)?;
        let actual = emitter.output.len() - before;
        if actual != *size {
            return Err(format!(
                "{file}: {} assembled to {actual:#x} bytes, layout said {size:#x}",
                object.name
            ));
        }
    }
    Ok(emitter.output)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn names_resolve_case_insensitively() {
        let digimon = |value| resolve_named(DIGIMON_NAMES, "digimon", value);
        assert_eq!(digimon("Agumon").unwrap(), 0x03);
        assert_eq!(digimon("agumon").unwrap(), 0x03);
        assert_eq!(digimon("King of Sukamon").unwrap(), 0x78);
        assert_eq!(digimon("king_of_sukamon").unwrap(), 0x78);
        assert!(digimon("Greymon").unwrap_err().contains("ambiguous"));
        assert!(digimon("NotADigimon").is_err());

        let item = |value| resolve_named(ITEM_NAMES, "item", value);
        assert_eq!(item("Blue Flute").unwrap(), 0x73);
        assert_eq!(item("sm.recovery").unwrap(), 0x00);
        assert_eq!(item("Gold banana").unwrap(), 0x6d);

        let mv = |value| resolve_named(MOVE_NAMES, "move", value);
        assert_eq!(mv("Fire Tower").unwrap(), 0x00);
        assert_eq!(mv("Aqua Magic").unwrap(), 0x15);
        assert!(mv("Dynamite Kick").unwrap_err().contains("ambiguous"));
    }

    #[test]
    fn map_names_resolve() {
        assert_eq!(resolve_map("MAYO01_2").unwrap(), 0x6e);
        assert_eq!(resolve_map("mayo02_2").unwrap(), 0x6f);
        assert_eq!(resolve_map("Kunemon's Bed").unwrap(), 0x01);
        assert!(
            resolve_map("Native Forest")
                .unwrap_err()
                .contains("ambiguous")
        );
        assert!(resolve_map("NOT_A_MAP").is_err());
    }

    #[test]
    fn checked_in_sources_match_the_original_assets() {
        let workspace = std::path::Path::new(env!("CARGO_MANIFEST_DIR")).join("../..");
        let scripts = workspace.join("scripts");
        let root = workspace.join("disc/extracted-scripts/SCN");
        if !scripts.join("DG.txt").is_file() || !scripts.join("MAPHEAD.txt").is_file() {
            eprintln!("no script sources in {}; skipped", scripts.display());
            return;
        }
        let maphead_text = std::fs::read_to_string(scripts.join("MAPHEAD.txt")).unwrap();
        let dg_text = std::fs::read_to_string(scripts.join("DG.txt")).unwrap();
        let maphead = assemble(&maphead_text, "MAPHEAD.txt", &[]).unwrap();
        let dg = assemble(&dg_text, "DG.txt", &[("MAPHEAD", maphead.as_slice())]).unwrap();
        for (name, rebuilt) in [("DG.SCN", &dg), ("MAPHEAD.SCN", &maphead)] {
            if let Ok(original) = std::fs::read(root.join(name)) {
                assert_eq!(
                    rebuilt.as_slice(),
                    original.as_slice(),
                    "{name} text source must round-trip"
                );
            }
        }
    }

    #[test]
    fn assembler_rejects_unmappable_glyphs() {
        let source = "\
# DW1-SCN-TEXT 1
.object MAPHEAD
  .entries
    0x000 -> h
  .end
h:
  .text
    \"\u{1f642}\"
  .end
.end
";
        let error = assemble(source, "test.txt", &[]).unwrap_err();
        assert!(error.contains("CP932"), "{error}");
    }

    #[test]
    fn comments_and_named_operands_assemble() {
        let source = "\
# DW1-SCN-TEXT 1
.object MAPHEAD
  .entries
    0x000 -> head
  .end
head:
  LOAD_DIGIMON digimon=Agumon  # Agumon
  LOAD_DIGIMON digimon=\"King of Sukamon\"
  GIVE_ITEM item=\"Blue Flute\" amount=0x01
  LEARN_MOVE move=Fire_Tower
  END_SCRIPT
.end
";
        let bytes = assemble(source, "test.txt", &[]).unwrap();
        assert_eq!(bytes[8..12], [0x46, 0x03, 0x46, 0x78]);
        assert_eq!(bytes[12..16], [0x28, 0x00, 0x73, 0x01]);
        assert_eq!(bytes[16..20], [0x2d, 0x00, 0xff, 0x00]);
    }
}

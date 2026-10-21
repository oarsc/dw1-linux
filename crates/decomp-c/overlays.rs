//! Overlay data lifetimes (build side): each load of an overlay on the PS1 copies its file over
//! its load address, so its initialised data (`.data`, in the file) starts from the file's values
//! every time, while its `.bss` (not in the file) keeps whatever the RAM held, and the small
//! variables CodeWarrior put in the main executable's `.sdata` (resident) keep their values across
//! loads. Natively the overlays' C is linked once, so this module arranges the same:
//!
//! - every overlay C file whose `.data` the original `overlay.ld` places in an overlay is compiled
//!   through a generated wrapper, alone, and its data is moved to two sections of its own per
//!   overlay with `objcopy` (`data_section_renames`): initialised data in `dw1_<u>`,
//!   zero-initialised and uninitialised data in `dw1_<u>z`;
//! - the wrapper also lists the variables a reload must not touch, with their native sizes: the
//!   file's resident variables (names the main symbol list places in the main executable, at
//!   0x80090000 and up) and its definitions without an initialiser (the PS1's overlay `.bss`,
//!   which a load doesn't clear). The definitions come from the preprocessed file
//!   (`top_level_definitions`), so ones built by macros count;
//! - `src/overlays.rs` (generated here as `overlays_table.rs`) snapshots the first section before
//!   the game starts and, when the game loads an overlay (`loadDynamicLibrary`), puts the
//!   snapshot back and zeroes the second, keeping the listed variables' current values.
//!
//! So an explicit zero initialiser resets like any other, as on the PS1 (CodeWarrior put those in
//! `.data`; the `*_bss_us.c` files are all of that kind). Function-local statics can't be listed
//! from the wrapper; the build stops if an overlay data file has one.

use std::collections::{BTreeMap, BTreeSet};
use std::fs;
use std::path::Path;

/// Units that are overlays, with their `Overlay` number (`REL_BIN_FILES` order in utils2.c:
/// BTL is 1 ... EAB is 16; SHOP, 11, is built into the main executable).
pub const OVERLAY_IDS: &[(&str, u32)] = &[
    ("BTL", 1),
    ("STD", 2),
    ("FISH", 3),
    ("EVL", 4),
    ("KAR", 5),
    ("VS", 6),
    ("MOV", 7),
    ("DOO2", 8),
    ("DOOA", 9),
    ("TRN", 10),
    ("DGET", 12),
    ("TRN2", 13),
    ("MURD", 14),
    ("ENDI", 15),
    ("EAB", 16),
];

/// Where the main executable starts (config/us/main.ld's `.header`); symbols at or above it are
/// resident.
const MAIN_BASE: u32 = 0x8009_0000;

/// The section an overlay's initialised data goes in. Its zero-initialised and uninitialised data
/// go in this name plus `z`. No leading dot: GNU ld only defines the `__start_<name>` and
/// `__stop_<name>` symbols (the section bounds, `bounds_c`) for names that are C identifiers.
pub fn section(unit: &str) -> String {
    format!("dw1_{}", unit.to_lowercase())
}

/// The `objcopy` arguments that move a wrapper object's data to the overlay's sections (module
/// docs): every initialised-data section (`.data`, `.data.rel.*`) to `dw1_<u>` and every
/// zero-initialised one (`.bss`) to `dw1_<u>z`. The wrapper is compiled on its own, so those
/// sections hold that file's definitions only; the relocation sections keep pointing at them (by
/// index), so the link still applies them.
///
/// Also says which of the two sections the object contributes, so `bounds_c` only names the ones
/// the link will have (`__start_<section>` of a section nothing defines is an error).
pub fn data_section_renames(obj: &Path, unit: &str) -> (Vec<String>, bool, bool) {
    let data = section(unit);
    let zero = format!("{data}z");
    let mut args = Vec::new();
    let (mut has_data, mut has_zero) = (false, false);
    for (name, kind, size) in object_sections(obj) {
        // An empty section (`cc` always emits a `.bss`) would leave `__start_<section>` undefined.
        let target = match kind.as_str() {
            "PROGBITS" if size > 0 && (name == ".data" || name.starts_with(".data.")) => {
                has_data = true;
                &data
            }
            "NOBITS" if size > 0 && (name == ".bss" || name.starts_with(".bss.")) => {
                has_zero = true;
                &zero
            }
            _ => continue,
        };
        args.push("--rename-section".to_string());
        args.push(format!("{name}={target}"));
    }
    (args, has_data, has_zero)
}

/// An object's sections, as their (name, type, size), from `readelf`.
fn object_sections(obj: &Path) -> Vec<(String, String, u64)> {
    let out = std::process::Command::new("readelf")
        .args(["--wide", "--section-headers"])
        .arg(obj)
        .output()
        .unwrap_or_else(|e| panic!("readelf {}: {e}", obj.display()));
    assert!(
        out.status.success(),
        "readelf {}: {}",
        obj.display(),
        String::from_utf8_lossy(&out.stderr)
    );
    String::from_utf8_lossy(&out.stdout)
        .lines()
        .filter_map(|l| {
            // `  [ 5] .data     PROGBITS  0000000000000000 000040 000018 00  WA  0   0  1`
            let rest = l.trim_start().strip_prefix('[')?;
            let mut fields = rest.split_once(']')?.1.split_whitespace();
            let name = fields.next()?.to_string();
            let kind = fields.next()?.to_string();
            let size = u64::from_str_radix(fields.nth(2)?, 16).ok()?;
            Some((name, kind, size))
        })
        .collect()
}

/// The C files whose `.data` `overlay.ld` places in an overlay (`src/....c.o(.data.*)`).
pub fn overlay_data_files(decomp: &Path) -> BTreeSet<String> {
    let ld = fs::read_to_string(decomp.join("config/us/overlay.ld")).unwrap();
    ld.lines()
        .filter_map(|l| {
            let start = l.find("BUILD_DIR/")? + "BUILD_DIR/".len();
            let rest = &l[start..];
            let end = rest.find(".o(.data.")?;
            Some(rest[..end].to_string())
        })
        .collect()
}

/// Names the main symbol list (config/us/symbols.txt) places in the main executable.
pub fn resident_names(decomp: &Path) -> BTreeSet<String> {
    let text = fs::read_to_string(decomp.join("config/us/symbols.txt")).unwrap();
    text.lines()
        .filter_map(|l| {
            let (name, rest) = l.split_once('=')?;
            let hex = rest.trim().strip_prefix("0x")?;
            let addr = u32::from_str_radix(hex.split(';').next()?.trim(), 16).ok()?;
            (addr >= MAIN_BASE).then(|| name.trim().to_string())
        })
        .collect()
}

/// The C tokens of preprocessed source: identifiers, numbers and punctuation (one character
/// each, enough for nesting and `=`, `,`, `;`); string and character literals become one `"`
/// token each.
fn tokens(src: &str) -> Vec<String> {
    let b = src.as_bytes();
    let mut out = Vec::new();
    let mut i = 0;
    while i < b.len() {
        let c = b[i];
        if c.is_ascii_whitespace() {
            i += 1;
        } else if c == b'#' {
            // A line marker or pragma left by the preprocessor.
            while i < b.len() && b[i] != b'\n' {
                i += 1;
            }
        } else if c == b'"' || c == b'\'' {
            i += 1;
            while i < b.len() && b[i] != c {
                if b[i] == b'\\' {
                    i += 1;
                }
                i += 1;
            }
            i += 1;
            out.push("\"".to_string());
        } else if c.is_ascii_alphanumeric() || c == b'_' {
            let start = i;
            while i < b.len() && (b[i].is_ascii_alphanumeric() || b[i] == b'_' || b[i] == b'.') {
                i += 1;
            }
            out.push(src[start..i].to_string());
        } else {
            out.push((c as char).to_string());
            i += 1;
        }
    }
    out
}

/// The variables a preprocessed C file defines at file scope: (name, has an initialiser).
/// Declarations with `extern` or `typedef`, function declarations and definitions are skipped.
/// Err if a function body declares a `static` (a function-local static, which a wrapper can't
/// name).
pub fn top_level_definitions(pre: &str) -> Result<Vec<(String, bool)>, String> {
    let toks = tokens(pre);
    let mut defs = Vec::new();
    let mut stmt: Vec<&str> = Vec::new();
    // Inside a K&R function header's parameter declarations (`f(a, b) int a; int b; {`).
    let mut kr = false;
    let mut i = 0;
    while i < toks.len() {
        let t = toks[i].as_str();
        if t == "{" && (kr || (!stmt.contains(&"=") && stmt.last() == Some(&")"))) {
            kr = false;
            // A function body: skip to its end.
            let mut depth = 0;
            loop {
                match toks[i].as_str() {
                    "{" => depth += 1,
                    "}" => {
                        depth -= 1;
                        if depth == 0 {
                            break;
                        }
                    }
                    "static" => {
                        return Err(format!(
                            "a function-local static in {}",
                            stmt.iter().take(8).cloned().collect::<Vec<_>>().join(" ")
                        ));
                    }
                    _ => {}
                }
                i += 1;
            }
            stmt.clear();
            i += 1;
            continue;
        }
        if t == ";" && depth_of(&stmt) == 0 {
            if kr || kr_header(&stmt) {
                // A K&R parameter declaration, not a file-scope variable.
                kr = true;
            } else {
                declaration(&stmt, &mut defs);
            }
            stmt.clear();
            i += 1;
            continue;
        }
        stmt.push(t);
        i += 1;
    }
    Ok(defs)
}

/// Whether a statement starts with a K&R function header: a declarator `name (a, b)` whose
/// parameter list is only identifiers, followed by a type (the first parameter declaration).
fn kr_header(toks: &[&str]) -> bool {
    let Some(open) = toks.iter().position(|t| *t == "(") else {
        return false;
    };
    let Some(close) = toks[open..].iter().position(|t| *t == ")").map(|k| k + open) else {
        return false;
    };
    let ident = |t: &str| t.chars().next().is_some_and(|c| c.is_ascii_alphabetic() || c == '_');
    open > 0
        && ident(toks[open - 1])
        && toks[open + 1..close].iter().all(|t| *t == "," || ident(t))
        && close > open + 1
        && toks.get(close + 1).is_some_and(|t| {
            ident(t) && !matches!(*t, "__attribute__" | "__asm" | "__asm__" | "asm")
        })
}

/// The bracket depth at the end of a token run.
fn depth_of(toks: &[&str]) -> i32 {
    toks.iter()
        .map(|t| match *t {
            "(" | "[" | "{" => 1,
            ")" | "]" | "}" => -1,
            _ => 0,
        })
        .sum()
}

/// Adds the variables one file-scope declaration (`toks`, without its `;`) defines.
fn declaration(toks: &[&str], defs: &mut Vec<(String, bool)>) {
    if toks.is_empty() || toks.contains(&"typedef") || toks.contains(&"extern") {
        return;
    }
    // A struct/union/enum body in the type: skip past it, so its member declarations aren't
    // taken for variables.
    let mut start = 0;
    if let Some(open) = toks.iter().position(|t| *t == "{")
        && !toks[..open].contains(&"=")
    {
        let mut depth = 0;
        for (k, t) in toks.iter().enumerate().skip(open) {
            match *t {
                "{" => depth += 1,
                "}" => {
                    depth -= 1;
                    if depth == 0 {
                        start = k + 1;
                        break;
                    }
                }
                _ => {}
            }
        }
    }
    // Declarators split at depth-0 commas.
    let mut parts: Vec<&[&str]> = Vec::new();
    let (mut depth, mut from) = (0, start);
    for (k, t) in toks.iter().enumerate().skip(start) {
        match *t {
            "(" | "[" | "{" => depth += 1,
            ")" | "]" | "}" => depth -= 1,
            "," if depth == 0 => {
                parts.push(&toks[from..k]);
                from = k + 1;
            }
            _ => {}
        }
    }
    parts.push(&toks[from..]);
    for part in parts {
        let eq = {
            let mut d = 0;
            part.iter().position(|t| {
                match *t {
                    "(" | "[" | "{" => d += 1,
                    ")" | "]" | "}" => d -= 1,
                    _ => {}
                }
                *t == "=" && d == 0
            })
        };
        let decl = &part[..eq.unwrap_or(part.len())];
        if let Some(name) = declarator_name(decl) {
            defs.push((name, eq.is_some()));
        }
    }
}

/// The name a declarator declares, or None for a function declaration (`name(...)` not inside
/// a pointer declarator) or no name.
fn declarator_name(decl: &[&str]) -> Option<String> {
    let ident = |t: &str| {
        t.chars().next().is_some_and(|c| c.is_ascii_alphabetic() || c == '_')
            && t.chars().all(|c| c.is_ascii_alphanumeric() || c == '_')
    };
    // The first `(`: after an identifier it opens a function's parameters (a declaration, not
    // a variable); followed by `*` it's a pointer declarator, a function pointer variable whose
    // name follows the `*` (possibly after `const`).
    // (A parameter list never starts with `*`, so `( *` is checked first.)
    if let Some(p) = decl.iter().position(|t| *t == "(") {
        if decl.get(p + 1) == Some(&"*") {
            let k = (p + 2..decl.len())
                .find(|&k| ident(decl[k]) && !matches!(decl[k], "const" | "volatile"))?;
            // `(*name(...))(...)` declares a function returning a function pointer.
            if decl.get(k + 1) == Some(&"(") {
                return None;
            }
            return Some(decl[k].to_string());
        }
        if p > 0 && ident(decl[p - 1]) {
            return None;
        }
    }
    // Otherwise the last identifier before any `[` dimensions; `name (` is a function.
    let end = decl.iter().position(|t| *t == "[").unwrap_or(decl.len());
    let name = decl[..end].iter().rposition(|t| ident(t))?;
    if decl.get(name + 1) == Some(&"(") {
        return None;
    }
    Some(decl[name].to_string())
}

/// A C identifier for a file's keep list.
fn keep_symbol(unit: &str, rel: &str) -> String {
    file_symbol("DW1_KEEP", unit, rel)
}

/// A C identifier for a file's data anchors (`wrapper`).
fn anchor_symbol(unit: &str, rel: &str) -> String {
    file_symbol("DW1_ANCHOR", unit, rel)
}

/// A C identifier `<prefix>_<unit>_<file stem>` for something the wrapper defines.
fn file_symbol(prefix: &str, unit: &str, rel: &str) -> String {
    let stem: String = Path::new(rel)
        .file_stem()
        .unwrap()
        .to_string_lossy()
        .chars()
        .map(|c| if c.is_ascii_alphanumeric() { c } else { '_' })
        .collect();
    format!("{prefix}_{}_{stem}", unit.to_lowercase())
}

/// The variables of a file a reload must not touch: its resident definitions and its definitions
/// without an initialiser (module docs), from `top_level_definitions`.
pub fn keeps(defs: &[(String, bool)], resident: &BTreeSet<String>) -> Vec<String> {
    let mut keep: BTreeSet<String> = BTreeSet::new();
    for (name, init) in defs {
        // Resident variables live in the main executable, not in the overlay.
        // Overlay reload doesn't touch main-executable memory, so don't keep them here.
        if resident.contains(name) {
            continue;
        }
        if !init {
            keep.insert(name.clone());
        }
    }
    keep.into_iter().collect()
}

/// The wrapper TU for an overlay data file: the file itself (`include` is the path to compile:
/// the original, or its CP932 copy). Data ends up in `.data`/`.bss` and is renamed to the
/// overlay's ELF sections by `objcopy` in build.rs, then the list of variables a reload keeps
/// (`keeps`) and the anchors that keep the data (all its `defs`).
pub fn wrapper(
    unit: &str,
    rel: &str,
    include: &Path,
    defs: &[(String, bool)],
    keeps: &[String],
) -> String {
    let mut s = format!(
        "/* Generated by crates/decomp-c/build.rs (overlays.rs): {rel}, overlay {unit}. */\n\
         #include \"{inc}\"\n\
         typedef struct {{ void *addr; uintptr_t size; }} dw1_keep_t;\n\
         const dw1_keep_t {sym}[] = {{\n",
        inc = include.display(),
        sym = keep_symbol(unit, rel),
    );
    for k in keeps {
        s.push_str(&format!("\t{{ (void *)&{k}, sizeof({k}) }},\n"));
    }
    s.push_str("\t{ 0, 0 },\n};\n");
    // The linker garbage collects sections nothing references, and in a binary where the game's
    // code is dead (the tests) that takes the files' data with it. Taking every definition's
    // address in a retained array keeps the sections it lives in, as the PS1's file would.
    s.push_str(&format!(
        "\n/* Keeps the file's data with --gc-sections. */\n\
         __attribute__((retain)) const void *const {anchors}[] = {{\n",
        anchors = anchor_symbol(unit, rel),
    ));
    for (name, _) in defs {
        s.push_str(&format!("\t(const void *)&{name},\n"));
    }
    s.push_str("\t0,\n};\n");
    s
}

/// The C side of the table (compiled into the overlay archive): the section bounds, the
/// `__start_<section>` / `__stop_<section>` symbols GNU ld defines for each overlay's sections
/// (see `section`). `files` says, per overlay unit, which of its two sections the wrappers
/// contribute (initialised data, zero-initialised data).
pub fn bounds_c(files: &BTreeMap<String, (bool, bool)>) -> String {
    // The bounds of a unit's sections; a unit with only one of the two (no `.bss`, e.g. ENDI)
    // points the other's range at its start, so it is empty.
    let bounds = |unit: &str, data: bool, zero: bool| {
        let sec = section(unit);
        let d = (format!("__start_{sec}"), format!("__stop_{sec}"));
        let z = (format!("__start_{sec}z"), format!("__stop_{sec}z"));
        match (data, zero) {
            (true, true) => (d, z),
            (true, false) => (d.clone(), (d.0.clone(), d.0)),
            (false, true) => ((z.0.clone(), z.0.clone()), z),
            (false, false) => panic!("overlay {unit}: no data sections"),
        }
    };
    let mut s = String::from("/* Generated by crates/decomp-c/build.rs (overlays.rs). */\n");
    for (unit, &(data, zero)) in files {
        let (d, z) = bounds(unit, data, zero);
        s.push_str(&format!(
            "extern char {}[], {}[], {}[], {}[];\n",
            d.0, d.1, z.0, z.1
        ));
    }
    s.push_str("int dw1_overlay_bounds(int id, char **start, char **end, char **zstart, char **zend)\n{\n\tswitch (id) {\n");
    for (unit, &(data, zero)) in files {
        let id = OVERLAY_IDS.iter().find(|(u, _)| u == unit).unwrap().1;
        let (d, z) = bounds(unit, data, zero);
        s.push_str(&format!(
            "\tcase {id}:\n\t\t*start = {};\n\t\t*end = {};\n\t\t*zstart = {};\n\t\t*zend = {};\n\t\treturn 1;\n",
            d.0, d.1, z.0, z.1
        ));
    }
    s.push_str("\t}\n\treturn 0;\n}\n");
    s
}

/// The Rust table (`include!`d by src/overlays.rs): per overlay, its number and keep lists (the
/// bounds come from `dw1_overlay_bounds`, `bounds_c`).
pub fn table(files: &BTreeMap<String, Vec<String>>) -> String {
    let mut s = String::from(
        "// Generated by crates/decomp-c/build.rs (overlays.rs).\nunsafe extern \"C\" {\n    fn dw1_overlay_bounds(id: i32, start: *mut *mut u8, end: *mut *mut u8, zstart: *mut *mut u8, zend: *mut *mut u8) -> i32;\n",
    );
    for (unit, rels) in files {
        for rel in rels {
            s.push_str(&format!("    static {}: [Keep; 0];\n", keep_symbol(unit, rel)));
        }
    }
    s.push_str("}\n\n/// Every overlay with data sections: (Overlay number, data start, end, zero start, end, keep lists).\n");
    s.push_str("#[allow(clippy::type_complexity)]\nfn overlay_sections() -> Vec<(u32, *mut u8, *mut u8, *mut u8, *mut u8, Vec<*const Keep>)> {\n    let bounds = |id: i32| {\n        let mut p = [std::ptr::null_mut(); 4];\n        let [a, b, c, d] = &mut p;\n        let ok = unsafe { dw1_overlay_bounds(id, a, b, c, d) };\n        assert_eq!(ok, 1, \"no bounds for overlay {id}\");\n        p\n    };\n    vec![\n");
    for (unit, rels) in files {
        let id = OVERLAY_IDS.iter().find(|(u, _)| u == unit).unwrap().1;
        let keeps: Vec<String> = rels
            .iter()
            .map(|rel| format!("(&raw const {}).cast::<Keep>()", keep_symbol(unit, rel)))
            .collect();
        s.push_str(&format!(
            "        {{ let [a, b, c, d] = bounds({id}); ({id}, a, b, c, d, vec![{}]) }},\n",
            keeps.join(", ")
        ));
    }
    s.push_str("    ]\n}\n");
    s
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn top_level_definitions_are_found() {
        let src = "typedef struct { int a; int b; } T;\n\
                   extern int e;\n\
                   int x = 1, y, z[3] = {0};\n\
                   static T t = { 1, 2 };\n\
                   void f(T *ot, int aabb);\n\
                   int (*fp)(int) = 0;\n\
                   void (*tbl[2])(void);\n\
                   const char *s = \"a;b{\";\n\
                   struct S { int m; } sv;\n\
                   int g(int q) { int local = 2; return q; }\n\
                   int kr(a, b) int a; char b; { return a; }\n\
                   void noret(void) __attribute__((noreturn));\n\
                   void (*cbset(void (*f)(void)))(void);\n\
                   unsigned char last[2];\n";
        let defs = top_level_definitions(src).unwrap();
        assert_eq!(
            defs,
            [
                ("x", true),
                ("y", false),
                ("z", true),
                ("t", true),
                ("fp", true),
                ("tbl", false),
                ("s", true),
                ("sv", false),
                ("last", false),
            ]
            .map(|(n, i)| (n.to_string(), i))
        );
        assert!(top_level_definitions("int h(void) { static int n; return n; }").is_err());
    }
}

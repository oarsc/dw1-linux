//! Build embedded mods from the user's disc and mod files; `scripts/` is reference-only.
//! Base text disassemblies are cached under `OUT_DIR/disassembly-cache`, keyed by source asset
//! bytes and every converter/table input that affects their output.

use std::io::Write;
use std::path::{Path, PathBuf};
use std::process::{Command, Stdio};

fn main() {
    let workspace = Path::new(env!("CARGO_MANIFEST_DIR")).join("../..");
    let out = PathBuf::from(std::env::var_os("OUT_DIR").expect("OUT_DIR"));
    let mods = workspace.join("mods");
    let files = collect_mod_files(&mods);
    println!("cargo:rerun-if-changed={}", mods.display());
    for file in &files {
        println!("cargo:rerun-if-changed={}", file.display());
    }
    for input in disassembler_inputs(&workspace) {
        println!("cargo:rerun-if-changed={}", input.display());
    }
    for tool in [
        "apply_mods.py",
        "scn_text.py",
        "scn_dumper.py",
        "map_text.py",
    ] {
        println!(
            "cargo:rerun-if-changed={}",
            workspace.join("tools").join(tool).display()
        );
    }
    println!("cargo:rerun-if-env-changed=DW1_DISC");
    println!("cargo:rerun-if-env-changed=PYTHON");

    let scn_mods = files
        .iter()
        .any(|p| p.extension().is_some_and(|e| e == "scnmod"));
    let map_mods = files.iter().any(|p| {
        p.file_name()
            .is_some_and(|n| n.to_string_lossy().ends_with(".maps.json"))
    });
    if !scn_mods && !map_mods {
        write_empty_tables(&out);
        return;
    }

    let disc_path = disc_path(&workspace);
    if !disc_path.is_file() {
        panic!(
            "mods require your Digimon World disc; expected {} (set DW1_DISC to override)",
            disc_path.display()
        );
    }
    println!("cargo:rerun-if-changed={}", disc_path.display());
    let disc = open_disc(&disc_path);

    if scn_mods {
        let sources = out.join("modded_scripts");
        let cache = out.join("disassembly-cache");
        std::fs::create_dir_all(&sources).expect("creating temporary script source directory");
        extract_and_disassemble(
            &workspace,
            &disc,
            "/SCN/MAPHEAD.SCN",
            "MAPHEAD.SCN",
            "scn_text.py",
            &sources.join("MAPHEAD.txt"),
            false,
            &cache,
        );
        extract_and_disassemble(
            &workspace,
            &disc,
            "/SCN/DG.SCN",
            "DG.SCN",
            "scn_text.py",
            &sources.join("DG.txt"),
            false,
            &cache,
        );
        run_mod_applier(&workspace, &mods, &sources);
        let maphead_text = std::fs::read_to_string(sources.join("MAPHEAD.txt"))
            .expect("reading generated MAPHEAD source");
        let dg_text =
            std::fs::read_to_string(sources.join("DG.txt")).expect("reading generated DG source");
        let maphead = script_format::assemble(&maphead_text, "MAPHEAD.txt", &[])
            .unwrap_or_else(|e| panic!("{e}"));
        let dg = script_format::assemble(&dg_text, "DG.txt", &[("MAPHEAD", maphead.as_slice())])
            .unwrap_or_else(|e| panic!("{e}"));
        std::fs::write(out.join("MAPHEAD.SCN"), maphead).expect("writing MAPHEAD.SCN");
        std::fs::write(out.join("DG.SCN"), dg).expect("writing DG.SCN");
        std::fs::write(out.join("embedded_scripts.rs"),
            "pub const EMBEDDED: Option<(&[u8], &[u8])> = Some((include_bytes!(\"DG.SCN\"), include_bytes!(\"MAPHEAD.SCN\")));\n")
            .expect("writing embedded script table");
        println!("cargo:warning=embedded SCN mods from the local disc");
    } else {
        std::fs::write(
            out.join("embedded_scripts.rs"),
            "pub const EMBEDDED: Option<(&[u8], &[u8])> = None;\n",
        )
        .expect("writing empty script table");
    }

    if map_mods {
        let sources = out.join("modded_maps");
        extract_mod_maps(&workspace, &disc, &mods, &sources);
        embed_maps(&workspace, &out, &sources, &disc_path);
    } else {
        std::fs::write(
            out.join("embedded_maps.rs"),
            "pub const EMBEDDED_MAPS: &[(&str, &[u8])] = &[];\n",
        )
        .expect("writing empty map table");
    }
}

fn write_empty_tables(out: &Path) {
    std::fs::write(
        out.join("embedded_scripts.rs"),
        "pub const EMBEDDED: Option<(&[u8], &[u8])> = None;\n",
    )
    .expect("writing empty script table");
    std::fs::write(
        out.join("embedded_maps.rs"),
        "pub const EMBEDDED_MAPS: &[(&str, &[u8])] = &[];\n",
    )
    .expect("writing empty map table");
}

fn disc_path(workspace: &Path) -> PathBuf {
    std::env::var_os("DW1_DISC")
        .filter(|v| !v.is_empty())
        .map(PathBuf::from)
        .unwrap_or_else(|| workspace.join("disc/Digimon World (USA).cue"))
}

fn open_disc(path: &Path) -> pack::Disc {
    let result = if path
        .extension()
        .is_some_and(|e| e.eq_ignore_ascii_case("cue"))
    {
        pack::Disc::open(path)
    } else {
        pack::Disc::open_bin(path)
    };
    result.unwrap_or_else(|e| panic!("{}: {e}", path.display()))
}

fn extract_and_disassemble(
    workspace: &Path,
    disc: &pack::Disc,
    iso: &str,
    asset: &str,
    tool_name: &str,
    output: &Path,
    map_iso: bool,
    cache_dir: &Path,
) {
    let bytes = disc
        .read_file(iso)
        .unwrap_or_else(|e| panic!("{iso}: {e}"))
        .unwrap_or_else(|| panic!("{iso} not found on disc"));
    let key = disassembly_key(workspace, iso, asset, tool_name, map_iso, &bytes);
    let cache_file = cache_dir.join(format!("{asset}.{key}.txt"));
    if cache_file.is_file() {
        std::fs::copy(&cache_file, output).unwrap_or_else(|e| {
            panic!(
                "copying cached disassembly {} to {}: {e}",
                cache_file.display(),
                output.display()
            )
        });
        return;
    }
    std::fs::create_dir_all(cache_dir).expect("creating disassembly cache");
    let temporary = cache_file.with_extension("txt.tmp");
    let python = std::env::var_os("PYTHON").unwrap_or_else(|| "python3".into());
    let tool = workspace.join("tools").join(tool_name);
    let mut command = Command::new(&python);
    command
        .arg(tool)
        .arg("disassemble")
        .arg("-")
        .arg("--name")
        .arg(asset);
    if map_iso {
        command.arg("--iso-path").arg(iso);
    }
    let child = command
        .arg("-o")
        .arg(&temporary)
        .stdin(Stdio::piped())
        .spawn()
        .unwrap_or_else(|e| panic!("could not run Python disassembler: {e}"));
    let mut child = child;
    child
        .stdin
        .take()
        .expect("disassembler stdin")
        .write_all(&bytes)
        .expect("sending asset to disassembler");
    let status = child.wait().expect("waiting for Python disassembler");
    if !status.success() {
        let _ = std::fs::remove_file(&temporary);
        panic!("disassembling {asset} failed");
    }
    std::fs::rename(&temporary, &cache_file).unwrap_or_else(|e| {
        panic!(
            "moving disassembly cache {} to {}: {e}",
            temporary.display(),
            cache_file.display()
        )
    });
    std::fs::copy(&cache_file, output).unwrap_or_else(|e| {
        panic!(
            "copying cached disassembly {} to {}: {e}",
            cache_file.display(),
            output.display()
        )
    });
}

fn disassembler_inputs(workspace: &Path) -> Vec<PathBuf> {
    [
        "tools/scn_text.py",
        "tools/scn_dumper.py",
        "tools/map_text.py",
        "decomp/src/main/sjis.c",
        "decomp/src/main/map.c",
        "decomp/text/main/map.yaml",
        "decomp/src/main/main.c",
        "decomp/text/main/main.yaml",
        "decomp/text/main/item.yaml",
    ]
    .iter()
    .map(|path| workspace.join(path))
    .collect()
}

fn disassembly_key(
    workspace: &Path,
    iso: &str,
    asset: &str,
    tool_name: &str,
    map_iso: bool,
    bytes: &[u8],
) -> String {
    let mut hash = sha1_smol::Sha1::new();
    for part in [iso.as_bytes(), asset.as_bytes(), tool_name.as_bytes()] {
        hash.update(part);
        hash.update(&[0]);
    }
    hash.update(&[u8::from(map_iso), 0]);
    hash.update(bytes);
    for path in disassembler_inputs(workspace) {
        hash.update(path.to_string_lossy().as_bytes());
        hash.update(&[0]);
        match std::fs::read(&path) {
            Ok(contents) => hash.update(&contents),
            Err(error) => hash.update(format!("missing:{error}").as_bytes()),
        }
        hash.update(&[0xff]);
    }
    hash.digest().to_string()
}

fn extract_mod_maps(workspace: &Path, disc: &pack::Disc, mods: &Path, output: &Path) {
    let mut names = Vec::new();
    for path in collect_mod_files(mods).into_iter().filter(|p| {
        p.file_name()
            .is_some_and(|n| n.to_string_lossy().ends_with(".maps.json"))
    }) {
        let value: serde_json::Value = serde_json::from_slice(
            &std::fs::read(&path).unwrap_or_else(|e| panic!("{}: {e}", path.display())),
        )
        .unwrap_or_else(|e| panic!("{}: {e}", path.display()));
        let maps = value.as_object().unwrap_or_else(|| {
            panic!(
                "{}: expected a JSON object keyed by map filename",
                path.display()
            )
        });
        names.extend(maps.keys().cloned());
    }
    names.sort();
    names.dedup();
    std::fs::create_dir_all(output).expect("creating temporary map source directory");
    let cache = output.parent().unwrap_or(output).join("disassembly-cache");
    let files = disc
        .files()
        .unwrap_or_else(|e| panic!("listing disc files: {e}"));
    for name in names {
        let candidates: Vec<_> = files
            .iter()
            .filter(|(iso, _)| {
                Path::new(iso)
                    .file_stem()
                    .is_some_and(|s| s.to_string_lossy().eq_ignore_ascii_case(&name))
                    && Path::new(iso)
                        .extension()
                        .is_some_and(|e| e.eq_ignore_ascii_case("MAP"))
            })
            .collect();
        let (iso, _) = candidates
            .first()
            .unwrap_or_else(|| panic!("map {name} not found on disc"));
        extract_and_disassemble(
            workspace,
            disc,
            iso,
            Path::new(iso).file_name().unwrap().to_str().unwrap(),
            "map_text.py",
            &output.join(format!("{name}.map.txt")),
            true,
            &cache,
        );
    }
}

fn embed_maps(workspace: &Path, out: &Path, source: &Path, disc: &Path) {
    let maps_out = out.join("maps");
    let _ = std::fs::remove_dir_all(&maps_out);
    std::fs::create_dir_all(&maps_out).expect("creating embedded map output");
    let python = std::env::var_os("PYTHON").unwrap_or_else(|| "python3".into());
    let result = Command::new(&python)
        .arg(workspace.join("tools/map_text.py"))
        .arg("batch")
        .arg("--source")
        .arg(source)
        .arg("--out")
        .arg(&maps_out)
        .arg("--disc")
        .arg(disc)
        .arg("--mods")
        .arg(workspace.join("mods"))
        .output()
        .expect("running MAP assembler");
    if !result.status.success() {
        panic!(
            "MAP mod assembly failed:\n{}",
            String::from_utf8_lossy(&result.stderr)
        );
    }
    let mut entries: Vec<_> = std::fs::read_dir(&maps_out)
        .expect("reading assembled maps")
        .flatten()
        .map(|e| e.path())
        .filter(|p| p.extension().is_some_and(|e| e == "MAP"))
        .collect();
    entries.sort();
    let mut table = String::from("pub const EMBEDDED_MAPS: &[(&str, &[u8])] = &[\n");
    for path in &entries {
        let name = path.file_stem().unwrap().to_string_lossy();
        table.push_str(&format!(
            "    (\"{name}\", include_bytes!(\"{}\")),\n",
            path.display()
        ));
    }
    table.push_str("];\n");
    std::fs::write(out.join("embedded_maps.rs"), table).expect("writing embedded map table");
    if !entries.is_empty() {
        println!("cargo:warning=embedding {} modded map(s)", entries.len());
    }
}

fn run_mod_applier(workspace: &Path, mods: &Path, scripts: &Path) {
    let python = std::env::var_os("PYTHON").unwrap_or_else(|| "python3".into());
    let mut command = Command::new(python);
    command
        .arg(workspace.join("tools/apply_mods.py"))
        .arg("--mods")
        .arg(mods);
    command.arg("--scripts").arg(scripts);
    let output = command.output().expect("running mod applier");
    if !output.status.success() {
        panic!(
            "applying mods failed:\n{}",
            String::from_utf8_lossy(&output.stderr)
        );
    }
}

fn collect_mod_files(root: &Path) -> Vec<PathBuf> {
    let mut files = Vec::new();
    let Ok(entries) = std::fs::read_dir(root) else {
        return files;
    };
    for entry in entries.flatten() {
        let path = entry.path();
        if path.is_dir() {
            files.extend(collect_mod_files(&path));
        } else if path.extension().is_some_and(|e| e == "scnmod")
            || path
                .file_name()
                .is_some_and(|n| n.to_string_lossy().ends_with(".maps.json"))
        {
            files.push(path);
        }
    }
    files.sort();
    files
}

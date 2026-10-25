//! Read the disc's ``.MAP`` files and write the editable text sources.
//!
//! By default every ``.MAP`` is read into memory and converted to a readable
//! ``.map.txt``; the text references the original ``.MAP`` in the disc image and
//! no binary companion is written. The converter is ``tools/map_text.py`` (the
//! same one used by hand), fed through a pipe. ``--raw`` extracts every ``.MAP``
//! instead, for diagnostics or to compare against the originals.
//!
//! The disc image itself is never modified.

use std::io::Write;
use std::path::{Path, PathBuf};
use std::process::{Command, Stdio};

const USAGE: &str = "\
usage: extract_maps <disc.cue|disc.bin> [output-dir] [--raw]
       (or set DW1_DISC to the disc image)

  default   write each MAP as MAPNAME.map.txt; output-dir defaults to scripts/maps
  --raw     extract every .MAP file instead (output-dir defaults to disc/extracted-maps)

Environment: DW1_MAP_TEXT (path to tools/map_text.py), PYTHON (default python3)";

fn main() {
    if let Err(error) = run() {
        eprintln!("extract-maps: {error}");
        std::process::exit(1);
    }
}

fn run() -> Result<(), String> {
    let mut raw = false;
    let mut positional = Vec::new();
    for arg in std::env::args().skip(1) {
        match arg.as_str() {
            "--raw" => raw = true,
            "-h" | "--help" => {
                println!("{USAGE}");
                return Ok(());
            }
            value if value.starts_with('-') && value != "-" => {
                return Err(format!("unknown option {value:?}\n\n{USAGE}"));
            }
            _ => positional.push(PathBuf::from(arg)),
        }
    }
    if positional.len() > 2 {
        return Err(format!("too many arguments\n\n{USAGE}"));
    }
    let disc_path = positional
        .first()
        .cloned()
        .or_else(|| std::env::var_os("DW1_DISC").map(PathBuf::from))
        .ok_or(USAGE)?;
    let output = positional.get(1).cloned().unwrap_or_else(|| {
        if raw {
            PathBuf::from("disc/extracted-maps")
        } else {
            PathBuf::from("scripts/maps")
        }
    });

    let disc = if disc_path
        .extension()
        .is_some_and(|ext| ext.eq_ignore_ascii_case("cue"))
    {
        pack::Disc::open(&disc_path)
    } else {
        pack::Disc::open_bin(&disc_path)
    }
    .map_err(|e| format!("{}: {e}", disc_path.display()))?;

    if raw {
        extract_raw(&disc, &output)
    } else {
        extract_text(&disc, &output)
    }
}

/// Read every .MAP from the disc and write its text form (plus .map.bin).
fn extract_text(disc: &pack::Disc, output: &Path) -> Result<(), String> {
    let tool = map_tool()?;
    std::fs::create_dir_all(output)
        .map_err(|e| format!("{}: {e}", output.display()))?;
    let maps = find_maps(disc)?;
    for (disc_path, _) in &maps {
        let bytes = disc
            .read_file(disc_path)
            .map_err(|e| format!("{disc_path}: {e}"))?
            .ok_or_else(|| format!("{disc_path} not found on the disc"))?;
        let asset = Path::new(disc_path)
            .file_name()
            .and_then(|n| n.to_str())
            .unwrap_or(disc_path);
        let stem = Path::new(asset)
            .file_stem()
            .and_then(|s| s.to_str())
            .unwrap_or(asset);
        let destination = output.join(format!("{stem}.map.txt"));
        convert(&tool, &bytes, asset, disc_path, &destination)?;
        println!("{disc_path}  {} bytes  -> {}", bytes.len(), destination.display());
    }
    println!("Wrote {} editable maps to {}.", maps.len(), output.display());
    Ok(())
}

/// Extract every .MAP file from the disc, like the old tool did.
fn extract_raw(disc: &pack::Disc, output: &Path) -> Result<(), String> {
    let maps = find_maps(disc)?;
    if maps.is_empty() {
        return Err("no .MAP files found in the disc image".into());
    }
    for (disc_path, entry) in &maps {
        let relative = disc_path
            .strip_prefix('/')
            .ok_or_else(|| format!("unexpected ISO path: {disc_path}"))?;
        let destination = output.join(relative);
        if destination.exists() {
            return Err(format!(
                "{} already exists; choose an empty output directory to avoid overwriting files",
                destination.display()
            ));
        }
        if let Some(parent) = destination.parent() {
            std::fs::create_dir_all(parent)
                .map_err(|e| format!("{}: {e}", parent.display()))?;
        }
        let bytes = disc
            .read_file(disc_path)
            .map_err(|e| e.to_string())?
            .ok_or_else(|| format!("file disappeared from image: {disc_path}"))?;
        std::fs::write(&destination, &bytes)
            .map_err(|e| format!("{}: {e}", destination.display()))?;
        println!(
            "{disc_path}  {} bytes  -> {}",
            entry.size,
            destination.display()
        );
    }
    println!("Extracted {} MAP files to {}", maps.len(), output.display());
    Ok(())
}

fn find_maps(disc: &pack::Disc) -> Result<Vec<(String, pack::FileEntry)>, String> {
    let mut maps: Vec<_> = disc
        .files()
        .map_err(|e| e.to_string())?
        .into_iter()
        .filter(|(path, _)| {
            Path::new(path)
                .extension()
                .is_some_and(|ext| ext.eq_ignore_ascii_case("map"))
        })
        .collect();
    maps.sort_by(|a, b| a.0.cmp(&b.0));
    Ok(maps)
}

/// Find the text converter in the source tree, or from DW1_MAP_TEXT.
fn map_tool() -> Result<PathBuf, String> {
    if let Some(path) = std::env::var_os("DW1_MAP_TEXT").filter(|path| !path.is_empty()) {
        return Ok(path.into());
    }
    let local = PathBuf::from("tools/map_text.py");
    if local.is_file() {
        return Ok(local);
    }
    let workspace = Path::new(env!("CARGO_MANIFEST_DIR")).join("../../tools/map_text.py");
    if workspace.is_file() {
        return Ok(workspace);
    }
    Err("tools/map_text.py not found; run from the repository root or set DW1_MAP_TEXT".into())
}

/// Run `map_text.py disassemble - --name ASSET --iso-path ISO -o DEST` with the
/// MAP bytes on stdin. The text's `.base disc` names ISO so reassembly reads
/// the binary sections from the original .MAP.
fn convert(tool: &Path, bytes: &[u8], asset: &str, iso_path: &str,
           destination: &Path) -> Result<(), String> {
    let python = std::env::var_os("PYTHON").unwrap_or_else(|| "python3".into());
    if let Some(parent) = destination.parent() {
        std::fs::create_dir_all(parent)
            .map_err(|e| format!("{}: {e}", parent.display()))?;
    }
    let mut child = Command::new(&python)
        .arg(tool)
        .arg("disassemble")
        .arg("-")
        .arg("--name")
        .arg(asset)
        .arg("--iso-path")
        .arg(iso_path)
        .arg("-o")
        .arg(destination)
        .stdin(Stdio::piped())
        .spawn()
        .map_err(|e| format!("could not run {}: {e}", Path::new(&python).display()))?;
    let mut stdin = child.stdin.take().ok_or("no stdin for the converter")?;
    stdin
        .write_all(bytes)
        .map_err(|e| format!("could not send {asset} to the converter: {e}"))?;
    drop(stdin);
    let status = child
        .wait()
        .map_err(|e| format!("could not wait for the converter: {e}"))?;
    if !status.success() {
        let _ = std::fs::remove_file(destination);
        return Err(format!("the converter failed for {asset}"));
    }
    Ok(())
}

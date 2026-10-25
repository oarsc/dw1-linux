//! Read the disc's scene scripts and write the editable text sources.
//!
//! By default `DG.SCN` and `MAPHEAD.SCN` are read into memory and converted to
//! `scripts/DG.txt` and `scripts/MAPHEAD.txt`; no `.SCN` file is written. The
//! converter is `tools/scn_text.py` (the same one used by hand), fed through a
//! pipe. `--raw` extracts every `.SCN` instead, for diagnostics or comparison.
//!
//! The disc image itself is never modified.

use std::io::Write;
use std::path::{Path, PathBuf};
use std::process::{Command, Stdio};

const USAGE: &str = "\
usage: extract_scripts <disc.cue|disc.bin> [output-dir] [--raw]
       (or set DW1_DISC to the disc image)

  default   write MAPHEAD.txt and DG.txt (output-dir defaults to scripts)
  --raw     extract every .SCN file instead (output-dir defaults to disc/extracted-scripts)

Environment: DW1_SCN_TEXT (path to tools/scn_text.py), PYTHON (default python3)";

fn main() {
    if let Err(error) = run() {
        eprintln!("extract-scripts: {error}");
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
            PathBuf::from("disc/extracted-scripts")
        } else {
            PathBuf::from("scripts")
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

/// Read DG.SCN and MAPHEAD.SCN from the disc and write their text forms.
fn extract_text(disc: &pack::Disc, output: &Path) -> Result<(), String> {
    let tool = script_tool()?;
    std::fs::create_dir_all(output)
        .map_err(|e| format!("{}: {e}", output.display()))?;
    for asset in ["MAPHEAD.SCN", "DG.SCN"] {
        let disc_path = format!("/SCN/{asset}");
        let bytes = disc
            .read_file(&disc_path)
            .map_err(|e| format!("{disc_path}: {e}"))?
            .ok_or_else(|| format!("{asset} not found on the disc"))?;
        let name = Path::new(asset)
            .file_stem()
            .and_then(|stem| stem.to_str())
            .unwrap_or(asset);
        let destination = output.join(format!("{name}.txt"));
        convert(&tool, &bytes, asset, &destination)?;
        println!(
            "{asset}  {} bytes  -> {}",
            bytes.len(),
            destination.display()
        );
    }
    println!("Wrote the editable scripts to {}.", output.display());
    Ok(())
}

/// Extract every .SCN file from the disc, like the old tool did.
fn extract_raw(disc: &pack::Disc, output: &Path) -> Result<(), String> {
    let scripts: Vec<_> = disc
        .files()
        .map_err(|e| e.to_string())?
        .into_iter()
        .filter(|(path, _)| {
            Path::new(path)
                .extension()
                .is_some_and(|ext| ext.eq_ignore_ascii_case("scn"))
        })
        .collect();
    if scripts.is_empty() {
        return Err("no .SCN files found in the disc image".into());
    }
    for (disc_path, entry) in &scripts {
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
    println!("Extracted {} SCN files to {}", scripts.len(), output.display());
    Ok(())
}

/// Find the text converter in the source tree, or from DW1_SCN_TEXT.
fn script_tool() -> Result<PathBuf, String> {
    if let Some(path) = std::env::var_os("DW1_SCN_TEXT").filter(|path| !path.is_empty()) {
        return Ok(path.into());
    }
    let local = PathBuf::from("tools/scn_text.py");
    if local.is_file() {
        return Ok(local);
    }
    let workspace = Path::new(env!("CARGO_MANIFEST_DIR")).join("../../tools/scn_text.py");
    if workspace.is_file() {
        return Ok(workspace);
    }
    Err("tools/scn_text.py not found; run from the repository root or set DW1_SCN_TEXT".into())
}

/// Run `scn_text.py disassemble - --name ASSET -o DEST` with the SCN bytes on
/// stdin, then move the result into place.
fn convert(tool: &Path, bytes: &[u8], asset: &str, destination: &Path) -> Result<(), String> {
    let python = std::env::var_os("PYTHON").unwrap_or_else(|| "python3".into());
    let temporary = PathBuf::from(format!("{}.tmp", destination.display()));
    let mut child = Command::new(&python)
        .arg(tool)
        .arg("disassemble")
        .arg("-")
        .arg("--name")
        .arg(asset)
        .arg("-o")
        .arg(&temporary)
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
        let _ = std::fs::remove_file(&temporary);
        return Err(format!("the converter failed for {asset}"));
    }
    std::fs::rename(&temporary, destination)
        .map_err(|e| format!("{}: {e}", destination.display()))?;
    Ok(())
}

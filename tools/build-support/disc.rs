// Where the disc image and the files `dumpsxiso` extracted from it are, for the build scripts
// that set `cfg(have_disc)` / `cfg(have_disc_image)` (pack, psyq). Pulled in with
// `include!("../../tools/build-support/disc.rs")` like `watch.rs`.
//
// `DW1_DISC` and `DW1_DISC_FILES` win. The defaults are the repo's `disc/Digimon World (USA).cue`
// and the decomp's `decomp/disks/us` (where its `dumpsxiso` command writes).

// The repo root. `CARGO_MANIFEST_DIR` expands in the build script that includes this file (one
// level down in `crates/`); canonicalized so the skip messages show a plain path.
fn workspace_root() -> std::path::PathBuf {
    let root = std::path::Path::new(env!("CARGO_MANIFEST_DIR")).join("../..");
    std::fs::canonicalize(&root).unwrap_or(root)
}

// The disc image: `DW1_DISC`, else the repo's `disc/Digimon World (USA).cue`.
fn disc_image(root: &std::path::Path) -> std::path::PathBuf {
    std::env::var_os("DW1_DISC")
        .map(std::path::PathBuf::from)
        .unwrap_or_else(|| root.join("disc/Digimon World (USA).cue"))
}

// The directory `dumpsxiso` extracted the disc into: `DW1_DISC_FILES`, else `decomp/disks/us`.
fn disc_files(root: &std::path::Path) -> std::path::PathBuf {
    std::env::var_os("DW1_DISC_FILES")
        .map(std::path::PathBuf::from)
        .unwrap_or_else(|| root.join("decomp/disks/us"))
}

// The skip notice for `dumpsxiso`'s output not being there: where it should go and the command.
// dumpsxiso reads the image, not the cue sheet, so name the cue's `.bin` when it is beside it.
fn extract_hint(files: &std::path::Path, cue: &std::path::Path) -> String {
    let bin = cue.with_extension("bin");
    let image = if bin.exists() { bin } else { cue.to_path_buf() };
    format!(
        "extracted files not found ({}): run `dumpsxiso -x {} -s {}/us.xml \"{}\"`",
        files.display(),
        files.display(),
        files.display(),
        image.display()
    )
}

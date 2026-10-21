//! Sets `cfg(have_disc)` (and `DW1_TEST_DISC` / `DW1_TEST_FILES`, the paths the integration test
//! reads) when Ember's disc and the files dumpsxiso extracted from it exist: `DW1_DISC` (default
//! `<workspace>/disc/Digimon World (USA).cue`) and `DW1_DISC_FILES` (default
//! `<workspace>/decomp/disks/us`). Without them `tests/disc.rs` shows as ignored.

use std::path::Path;

include!("../../tools/build-support/watch.rs");
include!("../../tools/build-support/disc.rs");

fn main() {
    println!("cargo::rustc-check-cfg=cfg(have_disc)");
    println!("cargo::rerun-if-changed=build.rs");
    println!("cargo::rerun-if-env-changed=DW1_DISC");
    println!("cargo::rerun-if-env-changed=DW1_DISC_FILES");
    let root = workspace_root();
    let cue = disc_image(&root);
    let files = disc_files(&root);
    watch(&cue);
    watch(&files);
    if cue.exists() && files.is_dir() {
        println!("cargo::rustc-cfg=have_disc");
        println!("cargo::rustc-env=DW1_TEST_DISC={}", cue.display());
        println!("cargo::rustc-env=DW1_TEST_FILES={}", files.display());
    } else if !cue.exists() {
        skipped(
            "tests/disc.rs",
            format!("disc image not found ({})", cue.display()),
        );
    } else {
        skipped("tests/disc.rs", extract_hint(&files, &cue));
    }
    report_skipped();
}

//! Sets `cfg(have_libgs_capture)` when the `GsSortObject4J` captures (gitignored, local only)
//! exist (see `sort_capture`), and `cfg(have_disc)` (with `DW1_TEST_DISC` and `DW1_TEST_FILES`) when Ember's disc and
//! the files dumpsxiso extracted from it exist, for `tests/libcd_disc.rs`; see
//! `crates/pack/build.rs`.

use std::path::{Path, PathBuf};

include!("../../tools/build-support/watch.rs");
include!("../../tools/build-support/disc.rs");

fn main() {
    disc();
    gte_capture();
    libgs_light_capture();
    sort_capture();
    sort2d_capture();
    libgpu_capture();
    sprite_capture();
    sortot_capture();
    tmd_capture();
    request_run(
        "have_libgpu_drawload_capture",
        "DW1_LIBGPU_DRAWLOAD_CAPTURE",
        "p9-render-drawload",
        "tests/libgpu_drawload_oracle.rs",
    );
    println!("cargo::rerun-if-changed=build.rs");
    report_skipped();
}

/// Sets `cfg(have_libgs_2d_capture)` when at least one `g2d-box-*` or `g2d-spr` capture run of
/// `GsSortBoxFill`, `GsSortPoly` and `GsSortSprite` (`oracle/capture-calls.lua` with `DW1_CAPTURE_STATES=1`) exists under
/// `DW1_SORT_CAPTURES` (default `<workspace>/captures/oracle-runs`). Without one
/// `tests/libgs_2d_capture.rs` shows as an ignored placeholder.
fn sort2d_capture() {
    println!("cargo::rustc-check-cfg=cfg(have_libgs_2d_capture)");
    let root = match std::env::var_os("DW1_SORT_CAPTURES") {
        Some(d) => PathBuf::from(d),
        None => Path::new(env!("CARGO_MANIFEST_DIR")).join("../../captures/oracle-runs"),
    };
    watch(&root);
    let found = std::fs::read_dir(&root).is_ok_and(|entries| {
        entries.flatten().any(|e| {
            e.file_name().to_string_lossy().starts_with("g2d-box-")
                && e.path().join("calls.txt").exists()
        })
    });
    if found {
        println!("cargo::rustc-cfg=have_libgs_2d_capture");
    } else {
        skipped(
            "tests/libgs_2d_capture.rs",
            format!("2D sort captures not found under {}", root.display()),
        );
    }
}

/// The capture runs of `GsSortObject4J` under `DW1_SORT_CAPTURES` (default
/// `<workspace>/captures/oracle-runs`): `libgs-pin` (S0.7, `oracle/capture-libgs.lua`) and every
/// `s4j-*` (`oracle/capture-calls.lua` with `DW1_CAPTURE_STATES=1`). Sets
/// `cfg(have_libgs_capture)` when at least one exists (finished or not); without any,
/// `tests/libgs_capture.rs` shows as an ignored placeholder.
fn sort_capture() {
    println!("cargo::rustc-check-cfg=cfg(have_libgs_capture)");
    println!("cargo::rerun-if-env-changed=DW1_SORT_CAPTURES");
    let root = match std::env::var_os("DW1_SORT_CAPTURES") {
        Some(d) => PathBuf::from(d),
        None => Path::new(env!("CARGO_MANIFEST_DIR")).join("../../captures/oracle-runs"),
    };
    // Watched through `watch` so a missing captures root doesn't rerun this script on every
    // build (and with it everything that depends on it); captures added later still count.
    watch(&root);
    let mut found = 0;
    if let Ok(entries) = std::fs::read_dir(&root) {
        for e in entries.flatten() {
            let name = e.file_name();
            let name = name.to_string_lossy();
            // Any run counts, finished or not: the test fails on an interrupted one rather than
            // being ignored.
            if name == "libgs-pin" || name.starts_with("s4j-") {
                found += 1;
            }
        }
    }
    if found > 0 {
        println!("cargo::rustc-cfg=have_libgs_capture");
    } else {
        skipped(
            "tests/libgs_capture.rs",
            format!("GsSortObject4J captures not found under {}", root.display()),
        );
    }
}

fn disc() {
    println!("cargo::rustc-check-cfg=cfg(have_disc)");
    println!("cargo::rustc-check-cfg=cfg(have_disc_image)");
    println!("cargo::rerun-if-env-changed=DW1_DISC");
    println!("cargo::rerun-if-env-changed=DW1_DISC_FILES");
    let root = workspace_root();
    let cue = disc_image(&root);
    let extracted = disc_files(&root);
    watch(&cue);
    watch(&extracted);
    // The image alone (tests/libgs_disc_models.rs reads its files through `pack`).
    if cue.exists() {
        println!("cargo::rustc-cfg=have_disc_image");
        println!("cargo::rustc-env=DW1_TEST_DISC_IMAGE={}", cue.display());
    }
    if cue.exists() && extracted.is_dir() {
        println!("cargo::rustc-cfg=have_disc");
        println!("cargo::rustc-env=DW1_TEST_DISC={}", cue.display());
        println!("cargo::rustc-env=DW1_TEST_FILES={}", extracted.display());
    } else if !cue.exists() {
        skipped(
            "tests/libcd_disc.rs",
            format!("disc image not found ({})", cue.display()),
        );
    } else {
        skipped("tests/libcd_disc.rs", extract_hint(&extracted, &cue));
    }
}

/// Sets `cfg(have_gte_capture)` when the libgte oracle run (`tools/oracle/gte_requests.py`'s
/// requests, `req.txt` and `results.txt`) exists: `DW1_GTE_CAPTURE`, default
/// `<workspace>/captures/oracle-runs/gte-final`. Without it `tests/libgte_oracle.rs` is ignored.
fn gte_capture() {
    println!("cargo::rustc-check-cfg=cfg(have_gte_capture)");
    println!("cargo::rerun-if-env-changed=DW1_GTE_CAPTURE");
    let dir = match std::env::var_os("DW1_GTE_CAPTURE") {
        Some(d) => PathBuf::from(d),
        None => Path::new(env!("CARGO_MANIFEST_DIR")).join("../../captures/oracle-runs/gte-final"),
    };
    watch(&dir.join("results.txt"));
    if dir.join("req.txt").exists() && dir.join("results.txt").exists() {
        println!("cargo::rustc-cfg=have_gte_capture");
    } else {
        skipped(
            "tests/libgte_oracle.rs",
            format!("libgte oracle run not found ({})", dir.display()),
        );
    }
}

/// Sets `cfg(have_libgs_light_capture)` when the libgs light/view/coordinate oracle run
/// (`tools/oracle/libgs_requests.py`'s requests, `req.txt` and `results.txt`) exists:
/// `DW1_LIBGS_LIGHT_CAPTURE`, default `<workspace>/captures/oracle-runs/libgs-light`. Without it
/// `tests/libgs_oracle.rs` is ignored.
fn libgs_light_capture() {
    println!("cargo::rustc-check-cfg=cfg(have_libgs_light_capture)");
    println!("cargo::rerun-if-env-changed=DW1_LIBGS_LIGHT_CAPTURE");
    let dir = match std::env::var_os("DW1_LIBGS_LIGHT_CAPTURE") {
        Some(d) => PathBuf::from(d),
        None => {
            Path::new(env!("CARGO_MANIFEST_DIR")).join("../../captures/oracle-runs/libgs-light")
        }
    };
    watch(&dir.join("results.txt"));
    if dir.join("req.txt").exists() && dir.join("results.txt").exists() {
        println!("cargo::rustc-cfg=have_libgs_light_capture");
    } else {
        skipped(
            "tests/libgs_oracle.rs",
            format!("libgs light oracle run not found ({})", dir.display()),
        );
    }
}

/// Sets `cfg(have_libgpu_capture)` when the `g2d-tim` and `g2d-clut` capture runs (`OpenTIM`,
/// `ReadTIM` and `LoadClut` from `oracle/capture-calls.lua` with `DW1_CAPTURE_STATES=1`) exist
/// under `DW1_SORT_CAPTURES` (default `<workspace>/captures/oracle-runs`). Without them
/// `tests/libgpu_capture.rs` shows as an ignored placeholder.
fn libgpu_capture() {
    println!("cargo::rustc-check-cfg=cfg(have_libgpu_capture)");
    let root = match std::env::var_os("DW1_SORT_CAPTURES") {
        Some(d) => PathBuf::from(d),
        None => Path::new(env!("CARGO_MANIFEST_DIR")).join("../../captures/oracle-runs"),
    };
    watch(&root);
    if root.join("g2d-tim/calls.txt").exists() && root.join("g2d-clut/calls.txt").exists() {
        println!("cargo::rustc-cfg=have_libgpu_capture");
    } else {
        skipped(
            "tests/libgpu_capture.rs",
            format!(
                "OpenTIM/LoadClut captures not found under {}",
                root.display()
            ),
        );
    }
}

/// Sets `cfg(have_libgs_sprite_capture)` when the `GsSortSprite` oracle run
/// (`tools/oracle/sprite_requests.py`'s requests, `req.txt` and `results.txt`) exists:
/// `DW1_LIBGS_SPRITE_CAPTURE`, default `<workspace>/captures/oracle-runs/libgs-sprite`, and
/// `cfg(have_libgs_sprite_btl_capture)` for its `--set battle` run (`DW1_LIBGS_SPRITE_BTL_CAPTURE`,
/// default `libgs-sprite-btl`). Without them `tests/libgs_sprite_oracle.rs`'s tests are ignored.
fn sprite_capture() {
    request_run(
        "have_libgs_sprite_capture",
        "DW1_LIBGS_SPRITE_CAPTURE",
        "libgs-sprite",
        "tests/libgs_sprite_oracle.rs",
    );
    request_run(
        "have_libgs_sprite_btl_capture",
        "DW1_LIBGS_SPRITE_BTL_CAPTURE",
        "libgs-sprite-btl",
        "tests/libgs_sprite_oracle.rs",
    );
}

/// The `GsSortObject4J` request runs of `tools/oracle/tmd_requests.py` (Phase 9), for
/// `tests/libgs_tmd_oracle.rs`.
/// `DW1_LIBGS_TMD_CAPTURES` names the root holding the runs (default
/// `<workspace>/captures/oracle-runs`).
fn tmd_capture() {
    println!("cargo::rerun-if-env-changed=DW1_LIBGS_TMD_CAPTURES");
    let root = match std::env::var_os("DW1_LIBGS_TMD_CAPTURES") {
        Some(d) => PathBuf::from(d),
        None => Path::new(env!("CARGO_MANIFEST_DIR")).join("../../captures/oracle-runs"),
    };
    for set in ["fast", "div", "attr", "bits", "bounds"] {
        let cfg = format!("have_libgs_tmd_{set}_capture");
        println!("cargo::rustc-check-cfg=cfg({cfg})");
        let dir = root.join(format!("p9-render-s4j-{set}"));
        watch(&dir.join("results.txt"));
        if dir.join("req.txt").exists() && dir.join("results.txt").exists() {
            println!("cargo::rustc-cfg={cfg}");
        } else {
            skipped(
                "tests/libgs_tmd_oracle.rs",
                format!("libgs TMD oracle run not found ({})", dir.display()),
            );
        }
    }
}

/// Sets `cfg(<cfg>)` when an `oracle/call-sdk.lua` run's `req.txt` and `results.txt` exist in
/// `$<env>`, default `<workspace>/captures/oracle-runs/<default>`; `test` is the file using the
/// cfg, for the notice when the run is missing.
fn request_run(cfg: &str, env: &str, default: &str, test: &'static str) {
    println!("cargo::rustc-check-cfg=cfg({cfg})");
    println!("cargo::rerun-if-env-changed={env}");
    let dir = match std::env::var_os(env) {
        Some(d) => PathBuf::from(d),
        None => Path::new(env!("CARGO_MANIFEST_DIR"))
            .join("../../captures/oracle-runs")
            .join(default),
    };
    watch(&dir.join("results.txt"));
    if dir.join("req.txt").exists() && dir.join("results.txt").exists() {
        println!("cargo::rustc-cfg={cfg}");
    } else {
        skipped(
            test,
            format!("oracle run not found ({}) for cfg({cfg})", dir.display()),
        );
    }
}

/// Sets `cfg(have_libgs_sortot_capture)` when `GsSortOt`'s captured calls (`g2d-sortot`,
/// `oracle/capture-calls.lua`) and oracle run (`libgs-sortot`, `tools/oracle/sortot_requests.py`
/// through `oracle/call-sdk.lua`) both exist under `DW1_SORT_CAPTURES` (default
/// `<workspace>/captures/oracle-runs`); otherwise `tests/libgs_sortot.rs` shows as ignored.
fn sortot_capture() {
    println!("cargo::rustc-check-cfg=cfg(have_libgs_sortot_capture)");
    println!("cargo::rerun-if-env-changed=DW1_SORT_CAPTURES");
    let root = match std::env::var_os("DW1_SORT_CAPTURES") {
        Some(d) => PathBuf::from(d),
        None => Path::new(env!("CARGO_MANIFEST_DIR")).join("../../captures/oracle-runs"),
    };
    watch(&root);
    if root.join("g2d-sortot/calls.txt").exists() && root.join("libgs-sortot/results.txt").exists()
    {
        println!("cargo::rustc-cfg=have_libgs_sortot_capture");
    } else {
        skipped(
            "tests/libgs_sortot.rs",
            format!("GsSortOt captures not found under {}", root.display()),
        );
    }
}

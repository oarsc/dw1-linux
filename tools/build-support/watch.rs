// Helpers for the crates' `build.rs`, shared with `include!`.
//
// Each build script is compiled as its own crate, so they can't share a module the usual way.
// This file is pulled in with `include!("../../tools/build-support/watch.rs")`; rustc lists it
// in the build script's dep-info, so editing it recompiles every script that includes it.

/// Emits `rerun-if-changed` for `path`, or for its parent while `path` doesn't exist.
///
/// Cargo treats a watched path that is missing as changed on every build, so watching a
/// gitignored or local-only path unconditionally reran the build script (and with it every crate
/// that depends on it) on every build. The parent still notices the path appearing.
fn watch(path: &Path) {
    let watched = if path.exists() {
        path
    } else if path.parent().is_some_and(Path::exists) {
        path.parent().unwrap()
    } else {
        return;
    };
    println!("cargo::rerun-if-changed={}", watched.display());
}

/// The integration tests this script will leave ignored, with why, queued for `report_skipped`.
///
/// A build script has one notice channel (`cargo::warning`), and a clone without the disc, the
/// captures or the oracle runs misses many of them: queuing them keeps that to one warning per
/// crate instead of one per test file.
#[allow(dead_code)] // Not every script that includes this file skips tests.
static SKIPPED: std::sync::Mutex<Vec<(&'static str, String)>> = std::sync::Mutex::new(Vec::new());

/// Queues that `test` (a path under `tests/`) will be ignored because `why` (what looked for, and
/// where); `report_skipped` prints them.
#[allow(dead_code)]
fn skipped(test: &'static str, why: impl Into<String>) {
    SKIPPED.lock().unwrap().push((test, why.into()));
}

/// Prints the queued tests as one `cargo::warning`: their names, and with `DW1_BUILD_NOTICES=1`
/// also what was looked for and where (for when a capture you have isn't being found);
/// `DW1_BUILD_NOTICES=0` prints nothing.
#[allow(dead_code)]
fn report_skipped() {
    println!("cargo::rerun-if-env-changed=DW1_BUILD_NOTICES");
    let queued = std::mem::take(&mut *SKIPPED.lock().unwrap());
    let asked = std::env::var("DW1_BUILD_NOTICES").ok();
    if queued.is_empty() || asked.as_deref() == Some("0") {
        return;
    }
    let detail = asked.as_deref() == Some("1");
    // One file can miss several fixtures (the TMD sets); list each file once unless the detail is
    // asked for, which says what each miss was.
    let mut tests: Vec<&str> = Vec::new();
    for (test, _) in &queued {
        if detail || !tests.contains(test) {
            tests.push(test);
        }
    }
    let mut msg = format!(
        "{} integration test file(s) will be ignored (no disc, captures or oracle runs): {}",
        tests.len(),
        tests.join(", ")
    );
    if detail {
        let why: Vec<String> = queued
            .iter()
            .map(|(test, why)| format!("{test}: {why}"))
            .collect();
        msg.push_str("; ");
        msg.push_str(&why.join("; "));
    } else {
        msg.push_str(" (DW1_BUILD_NOTICES=1 for what was looked for, 0 to hide)");
    }
    println!("cargo::warning={msg}");
}

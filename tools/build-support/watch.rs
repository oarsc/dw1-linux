// `watch()` for the crates' `build.rs`, shared with `include!`.
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

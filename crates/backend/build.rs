//! Sets `cfg(have_gpu_capture)` when the GPU oracle run (`tools/oracle/gpu_requests.py`'s
//! `cases.txt` and the emulator's `results.txt`) exists: `DW1_GPU_CAPTURE`, default
//! `<workspace>/captures/oracle-runs/gpu-prims`. Without it `tests/gpu_oracle.rs` is ignored.

use std::path::{Path, PathBuf};

include!("../../tools/build-support/watch.rs");

fn main() {
    println!("cargo::rustc-check-cfg=cfg(have_gpu_capture)");
    println!("cargo::rerun-if-changed=build.rs");
    println!("cargo::rerun-if-env-changed=DW1_GPU_CAPTURE");
    let dir = match std::env::var_os("DW1_GPU_CAPTURE") {
        Some(d) => PathBuf::from(d),
        None => Path::new(env!("CARGO_MANIFEST_DIR")).join("../../captures/oracle-runs/gpu-prims"),
    };
    // Watched through `watch`, so the missing capture doesn't rerun this script every build.
    watch(&dir.join("results.txt"));
    if dir.join("cases.txt").exists() && dir.join("results.txt").exists() {
        println!("cargo::rustc-cfg=have_gpu_capture");
    } else {
        println!(
            "cargo::warning=GPU oracle run not found ({}): tests/gpu_oracle.rs will be ignored",
            dir.display()
        );
    }
}

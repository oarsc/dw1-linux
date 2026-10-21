fn main() {
    // Replays name the native game code's functions (`dladdr` in `headless.rs`), so those
    // symbols have to be in the binary's dynamic symbol table: without `-rdynamic` every
    // checkpoint comes out as an address and no replay can be compared.
    if std::env::var("CARGO_CFG_TARGET_OS").as_deref() == Ok("linux") {
        println!("cargo::rustc-link-arg=-rdynamic");
    }
    println!("cargo::rerun-if-changed=build.rs");
}

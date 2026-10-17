# Phase 2: C Compilation

## Goal
Compile the game C code on Linux without macOS-specific tools (xcrun) and adjust for Linux compilers.

## Current State
- `crates/decomp-c/build.rs` compiles game C for arm64 macOS
- Uses `xcrun --show-sdk-path` to get macOS SDK path (lines 410-413)
- Reads macOS SDK `.tbd` files for host symbol checking (lines 416-426)
- Assumes Apple clang behavior

## Changes Required

### 1. Conditionalize xcrun Usage

**File:** `crates/decomp-c/build.rs`

Replace the xcrun section (lines 410-426) with platform-specific code:

```rust
fn check_host_symbols(archive: &Path) {
    let nm = |args: &[&str]| -> BTreeSet<String> {
        let output = Command::new("nm")
            .args(args)
            .arg(archive)
            .output()
            .expect("running nm");
        assert!(
            output.status.success(),
            "nm failed on {}",
            archive.display()
        );
        String::from_utf8(output.stdout)
            .unwrap()
            .lines()
            .filter(|l| !l.is_empty() && !l.ends_with(':'))
            .map(str::to_string)
            .collect()
    };
    let undefined = nm(&["-u", "-j"]);
    let defined = nm(&["g", "-j", "-U"]);

    #[cfg(target_os = "macos")]
    {
        let sdk = Command::new("xcrun")
            .arg("--show-sdk-path")
            .output()
            .expect("running xcrun");
        let sdk = PathBuf::from(String::from_utf8(sdk.stdout).unwrap().trim());
        let mut host = BTreeSet::new();
        for tbd in fs::read_dir(sdk.join("usr/lib/system")).unwrap() {
            let tbd = tbd.unwrap().path();
            if tbd.extension().is_some_and(|e| e == "tbd") {
                let text = fs::read_to_string(&tbd).unwrap();
                host.extend(
                    text.split(|c: char| !(c.is_ascii_alphanumeric() || c == '_' || c == '$'))
                        .filter(|s| s.starts_with('_'))
                        .map(str::to_string),
                );
            }
        }
        let bound_to_host: Vec<_> = undefined
            .iter()
            .filter(|s| {
                !defined.contains(*s) && host.contains(*s) && !HOST_ALLOWED.contains(&s.as_str())
            })
            .collect();
        assert!(
            bound_to_host.is_empty(),
            "game C would call macOS libc for {bound_to_host:?}: rename them in \
             include/dw1_native.h and implement them in crates/psyq"
        );
    }

    #[cfg(not(target_os = "macos"))]
    {
        // On Linux, check against common libc symbols (glibc, musl)
        // We'll check for a few known symbols that shouldn't be bound
        let linux_forbidden = [
            "malloc", "free", "calloc", "realloc",  // Memory functions (renamed to dw1_*)
            "printf", "fprintf", "sprintf",         // Printf family (renamed to dw1_*)
            "strlen", "strcpy", "strcmp",           // String functions (renamed to dw1_*)
            "open", "read", "write", "close",       // File I/O (renamed to dw1_*)
        ];
        let bound_to_host: Vec<_> = undefined
            .iter()
            .filter(|s| {
                !defined.contains(*s)
                    && linux_forbidden.contains(&s.as_str())
                    && !HOST_ALLOWED.contains(&s.as_str())
            })
            .collect();
        assert!(
            bound_to_host.is_empty(),
            "game C would call Linux libc for {bound_to_host:?}: rename them in \
             include/dw1_native.h and implement them in crates/psyq"
        );
    }
}
```

### 2. Update Build Comments

Update the comment at the top of `build.rs` (line 1):

```rust
//! Compiles the game C from the `decomp/` submodule for the host platform
//! (arm64 macOS or Linux), links all of it, and generates Rust bindings for
//! the decomp and SDK structs Rust needs to read.
```

### 3. Update Other Architecture References

Line 127 comment:
```rust
// From: Plain char is signed for MIPS GCC and for Apple arm64; pinned so it can't drift.
// To: Plain char is signed for MIPS GCC and for most modern platforms; pinned so it can't drift.
```

Line 129 - The flag itself is fine (works on Linux):
```rust
.flag("-fsigned-char")
```

### 4. Test Compilation

First, ensure the renderer change (Phase 3) is done or temporarily disable render:

**Option A: Build without render (for testing C compilation only)**
```bash
# Temporarily modify workspace Cargo.toml to exclude render
# Comment out render from members list
# Then build just decomp-c:
cargo build --release -p decomp-c
```

**Option B: Do Phase 3 first, then test both together**

Recommended: Do Phase 3 first, then test compilation.

### 5. Verify Compiler Flags

The current flags should work on Linux:
- `-std=gnu99` - Standard C, supported by clang/gcc
- `-fwrapv` - Standard
- `-fno-strict-aliasing` - Standard
- `-fno-common` - Standard
- `-fno-builtin` - Standard
- `-fsigned-char` - Standard
- `-fno-inline` - Standard
- `-fno-optimize-sibling-calls` - Standard

No changes needed here.

### 6. Test Headless Build

Once Phase 3 is also done, test headless mode:

```bash
# Set up disc
export DW1_DISC=/path/to/Digimon\ World\ \(USA\).cue

# Run headless (should at least start)
export DW1_HEADLESS=1
./target/release/dw1
```

This will likely fail with other issues (file paths, etc.), but if it compiles
and links, Phase 2 is successful.

## Alternative: Use Clang on Both Platforms

For maximum consistency, use clang on both macOS and Linux:

### Linux: Install clang
```bash
sudo apt install clang
```

### Set CC environment variable
```bash
export CC=clang
export CXX=clang++
cargo build --release -p dw1
```

### Update build.rs to prefer clang
```rust
// In build.rs, after line 108:
if env::var("CC").is_none() {
    // Try to use clang if available
    if Command::new("clang").arg("--version").output().is_ok() {
        build.compiler("clang");
    }
}
```

## Deliverables

- [x] `check_host_symbols()` conditionalized for Linux
- [x] xcrun usage guarded with `#[cfg(target_os = "macos")]`
- [x] Linux host symbol checking implemented
- [x] Build comments updated
- [ ] `decomp-c` compiles on Linux
- [ ] Binary links successfully

## Testing

**Unit tests (before actual build):**
```bash
# Check the conditional compiles
cargo check -p decomp-c

# On macOS: should still compile
cargo build -p decomp-c

# On Linux: should compile
cargo build -p decomp-c
```

**Integration tests (after Phase 3):**
```bash
# Full build
cargo build --release -p dw1

# Check binary
file target/release/dw1 | grep -q ELF

# Check it's dynamically linked to Linux libraries
ldd target/release/dw1
```

## Debugging

### If nm fails
```bash
# Check nm is installed
which nm

# On Debian/Ubuntu
sudo apt install binutils
```

### If compiler not found
```bash
# Check clang/gcc is installed
which clang gcc

# Install if needed
sudo apt install clang
```

### If symbol check fails
```bash
# See what symbols are undefined
nm -u target/debug/build/decomp-c-*/out/libdecomp.a

# Check if they're in HOST_ALLOWED
```

## Commit Message

```
build: make C compilation work on Linux

Conditionalize xcrun usage in crates/decomp-c/build.rs for macOS only.
On Linux, check against a list of forbidden libc symbols instead of
reading macOS SDK .tbd files.

Update build comments to reflect cross-platform support.

The compiler flags remain unchanged - they work on both macOS (clang)
and Linux (clang/gcc).

This enables decomp-c to compile on Linux, though the full build still
requires Phase 3 (rendering backend) to complete.
```

## Notes

### Why not read Linux .so files?

Linux .so files are actual binaries, not text stubs like macOS .tbd.
Reading them would require parsing ELF format, which is complex.

Instead, we use a simpler approach: check against a known list of
forbidden symbols that should have been renamed in dw1_native.h.

### Extending the Linux check

If the game C accidentally binds to new libc symbols, add them to
`linux_forbidden` in `check_host_symbols()`.

### Keeping macOS behavior

The macOS check remains unchanged, so macOS builds continue to work
exactly as before.

### Next Steps

After this phase, move to **Phase 3: Rendering Backend** to change from
Metal to Vulkan/OpenGL.

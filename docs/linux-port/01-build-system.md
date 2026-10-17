# Phase 1: Build System

## Goal
Enable building on Linux without macOS-specific tools (xcrun, otool, codesign, sips, iconutil, plutil).

## Current State
- `tools/make-app.sh` creates macOS .app bundle
- Uses macOS-specific tools:
  - `otool` - checks linked libraries
  - `codesign` - signs the app
  - `sips` - generates icon sizes
  - `iconutil` - creates .icns
  - `plutil` - validates Info.plist
- Depends on `xcrun` indirectly

## Changes Required

### 1. Create Linux Build Script

**File:** `tools/build-linux.sh`

```bash
#!/bin/sh
# Builds dw1 for Linux (release build).
# On Linux, we don't create an app bundle - just the binary.
set -eu
cd "$(dirname "$0")/.." || exit 1

# CMake (SDL's build): the one on PATH, else the repo's .venv
if ! command -v cmake > /dev/null 2>&1 && [ -x .venv/bin/cmake ]; then
    CMAKE="$PWD/.venv/bin/cmake"
    export CMAKE
fi

cargo build --release -p dw1
bin=target/release/dw1

echo "build-linux: built $bin"
echo "build-linux: run with DW1_DISC=/path/to/Digimon\ World\ \(USA\).cue $bin"
```

**Make executable:**
```bash
chmod +x tools/build-linux.sh
```

### 2. Update `tools/make-app.sh` (Optional)

Keep it for macOS, add guard at top:

```bash
#!/bin/sh
# Builds the Mac app from this repo (macOS only).
# On Linux, use tools/build-linux.sh instead.

if [ "$(uname)" != "Darwin" ]; then
    echo "make-app.sh is for macOS only. On Linux, use tools/build-linux.sh" >&2
    exit 1
fi
```

### 3. Test Build

```bash
# Install dependencies if needed
sudo apt install build-essential clang cmake python3-venv pkg-config

# Set up Python venv
python3 -m venv .venv
.venv/bin/pip install pyyaml cmake

# Initialize submodules
git submodule update --init decomp
git -C decomp submodule update --init external/psyq_headers

# Build
./tools/build-linux.sh
```

**Expected output:**
```
build-linux: built target/release/dw1
build-linux: run with DW1_DISC=/path/to/Digimon World (USA).cue target/release/dw1
```

**Note:** This will fail initially because:
- `crates/decomp-c/build.rs` uses xcrun (Phase 2)
- `crates/render` uses Metal (Phase 3)

That's expected - we'll fix those in later phases.

### 4. Document Linux Build in README

Add section to `README.md`:

```markdown
## Building on Linux

You need Rust, your own disc image of Digimon World (USA) as a `.cue`/`.bin` pair,
and build dependencies:

```sh
# Debian/Ubuntu
sudo apt install build-essential clang cmake python3-venv pkg-config libsdl3-dev libvulkan-dev

# Fedora/RHEL
sudo dnf install gcc cmake python3 pkg-config SDL3-devel vulkan-devel
```

Then:

```sh
git clone https://github.com/loafykitten/dw1-silicon.git
cd dw1-silicon
git submodule update --init decomp
git -C decomp submodule update --init external/psyq_headers
python3 -m venv .venv && .venv/bin/pip install pyyaml cmake
./tools/build-linux.sh
```

Run the game:

```sh
export DW1_DISC=/path/to/Digimon\ World\ \(USA\).cue
./target/release/dw1
```
```

## Deliverables

- [x] `tools/build-linux.sh` created
- [x] Script is executable
- [x] macOS build script has guard
- [x] README.md updated with Linux instructions
- [ ] Script runs without error (after Phases 2-3)

## Testing

**Pre-phase testing:**
```bash
# Script exists and is executable
test -x tools/build-linux.sh || echo "FAIL: script not executable"

# macOS script has guard
grep -q "uname.*Darwin" tools/make-app.sh || echo "FAIL: no guard in make-app.sh"
```

**Post-phase testing (after Phases 2-3):**
```bash
# Actually build
./tools/build-linux.sh

# Check binary exists
test -x target/release/dw1 || echo "FAIL: binary not built"

# Check it's a Linux ELF binary
file target/release/dw1 | grep -q ELF || echo "FAIL: not an ELF binary"
```

## Commit Message

```
build: add Linux build script

Add tools/build-linux.sh for building on Linux without macOS-specific
tools (xcrun, otool, codesign, etc.). On Linux, we build a plain binary
instead of an .app bundle.

Update tools/make-app.sh to reject non-macOS platforms with a clear error
message.

Add Linux build instructions to README.md.

Note: Full Linux build will require changes in Phases 2 (C compilation)
and 3 (rendering backend) before the binary actually works.
```

## Notes

### Why not use `cargo build` directly?

The build script:
- Sets up CMake from .venv if needed
- Provides a consistent interface
- Makes it easy to add Linux-specific packaging later

### Keeping macOS compatibility

We're NOT removing macOS support - just adding Linux support. The macOS build
script remains unchanged (except for the guard).

### Next Steps

After this phase, move to **Phase 2: C Compilation** to fix the xcrun dependency
in `crates/decomp-c/build.rs`.

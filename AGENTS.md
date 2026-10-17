# dw1-silicon - Agent Context for Linux Port

## Project Overview

dw1-silicon is a native port of Digimon World (PS1, USA SLUS-01032) from the matching decompilation project (jype0/dw_decomp). The original target is **arm64 macOS** (Apple Silicon), but the goal is to make it buildable on Linux.

**Architecture:** Hybrid approach - game C from decomp + Rust for everything new (PS1 libraries reimplemented). Long-term goal: full Rust migration.

**Current Status (2026-10-15):** Phases 1-4, 6, 7, 8 done; Phase 9 under way. See PLAN.md for details.

---

## Critical Mac-Related Components for Linux Port

### 1. Build System (`tools/make-app.sh`)

**Purpose:** Creates macOS `.app` bundle from the built binary.

**Mac-specific tools used:**
- `otool` - Checks linked libraries (line 29)
- `codesign` - Signs the app ad-hoc (line 58)
- `sips` - Generates icon sizes (lines 51, 53)
- `iconutil` - Creates .icns from iconset (line 55)
- `plutil` - Validates Info.plist (line 45)
- `xcrun` - Not used directly but implied by otool for SDK info

**Linux requirements:**
- Remove or replace `.app` creation logic
- Linux doesn't use app bundles; use standard binary packaging
- Icons should be .png/.svg for Linux desktop files
- No code signing needed (or use gpg for optional signing)

**File locations:**
- App template: `packaging/Info.plist.in`
- Icon source: `packaging/icon-1024.png`

---

### 2. C Compilation (`crates/decomp-c/build.rs`)

**Target:** Currently compiles for **arm64 macOS** using Apple clang.

**Mac-specific code:**
- Line 1: Comment states "for arm64 macOS"
- Line 410-413: Uses `xcrun --show-sdk-path` to get macOS SDK
- Lines 416-426: Reads macOS SDK `.tbd` files to check for host symbol binding
- Line 127: Comment "Plain char is signed for MIPS GCC and for Apple arm64"
- Compile flags assume Apple clang behavior

**`check_host_symbols()` function (lines 388-438):**
- Ensures game C doesn't bind to macOS libSystem functions
- Reads macOS SDK `.tbd` stub files to get allowed symbols
- This entire check is macOS-specific

**Linux requirements:**
- Use system clang/gcc instead of Apple clang
- Remove `xcrun` dependency
- Replace host symbol checking with Linux equivalent (check against glibc/musl symbols)
- Handle different char signedness (Linux x86_64: char is signed by default)
- Target x86_64 or keep arm64 if desired

**Key includes/paths:**
- Native include: `crates/decomp-c/include/dw1_native.h`
- Psy-Q headers: `decomp/external/psyq_headers/mw_lib41/include`
- Generated headers: from decomp's `tools/gen_text.py`

---

### 3. Rendering Backend (`crates/render`)

**Current:** wgpu with **Metal** backend.

**Mac-specific code:**
- `Cargo.toml` line 3: description mentions "wgpu on Metal"
- `Cargo.toml` line 12: `features = ["metal", "wgsl", "std"]`
- `src/lib.rs` line 1: Comment "wgpu (Metal)"
- Window code uses `metal_view()` method

**Linux requirements:**
- Change wgpu backend from Metal to Vulkan or OpenGL
- Update `Cargo.toml` features: replace `metal` with `vulkan` or `gl`
- No changes to the rendering logic itself (wgpu is cross-platform)

**Alternative:** Use Vulkan (preferred for performance) or OpenGL (more compatible)

---

### 4. Window System (`crates/dw1/src/window.rs`)

**Current:** SDL3 with Metal rendering.

**Mac-specific references:**
- Line 1: Comment "wgpu on Metal"
- Line 201: Comment about Metal layer order
- Line 429: Calls `metal_view()`

**Linux requirements:**
- SDL3 is cross-platform - should work on Linux
- Ensure SDL3 Vulkan/OpenGL backend is used instead of Metal
- No other Mac-specific code detected

---

### 5. File Paths (Multiple Files)

**Mac-specific paths:**

**Saves directory:**
- `crates/dw1/src/main.rs` line 139-142: `~/Library/Application Support/dw1-silicon/`
- `crates/dw1/src/settings.rs` line 2: Same path for settings.txt
- `crates/dw1/src/window/snapshot.rs` line 2: Same path for reports

**DuckStation card import:**
- `crates/dw1/src/main.rs` line 217: `~/Library/Application Support/DuckStation/memcards/`

**Linux equivalents:**
- Use XDG Base Directory Specification:
  - Saves/settings: `$XDG_DATA_HOME/dw1-silicon/` (default: `~/.local/share/dw1-silicon/`)
  - Config: `$XDG_CONFIG_HOME/dw1-silicon/` (default: `~/.config/dw1-silicon/`)
  - Cache: `$XDG_CACHE_HOME/dw1-silicon/` (default: `~/.cache/dw1-silicon/`)
- DuckStation path on Linux: `~/.local/share/duckstation/memcards/` or similar

**Functions to modify:**
- `default_save_dir()` in `main.rs`
- Settings loading in `settings.rs`
- Snapshot path in `snapshot.rs`
- DuckStation card path in `main.rs`

---

### 6. Splash Screen (`crates/dw1/src/window/splash.rs`)

**Mac-specific text:**
- Line 32: "Native Mac build, written in Rust"

**Linux requirements:**
- Change to "Native Linux build" or "Native build"
- Keep the rest of the splash screen logic (it's cross-platform)

---

### 7. Crash Handler (`crates/dw1/src/main.rs`)

**Current:** arm64 macOS-specific signal handling.

**Mac-specific code:**
- Lines 39-127: Custom SIGSEGV/SIGBUS handler
- Line 39: Comment mentions "arm64 macOS keeps frame pointers"
- Lines 63-68: Uses `<mach/arm/_structs.h>` offsets for arm64
- Lines 70-76: Uses macOS-specific system calls (`sigaction`, `sigaltstack`, `backtrace_symbols_fd`)

**Linux requirements:**
- Replace with Linux signal handling
- Use Linux-specific ucontext offsets (different from macOS)
- Keep frame pointer walking (Linux x86_64 can be configured to keep them)
- Use `backtrace()` from libgcc or similar for stack traces

**Note:** This is crash trace only - can be simpler on Linux initially.

---

### 8. Metadata (`packaging/Info.plist.in`)

**Purpose:** macOS app bundle metadata.

**Mac-specific keys:**
- CFBundleIdentifier
- LSMinimumSystemVersion
- NSHighResolutionCapable
- LSApplicationCategoryType

**Linux requirements:**
- Create `.desktop` file for Linux desktop integration
- Use freedesktop.org standards
- Include icon reference, categories, etc.

**Example `.desktop` file location:** `/usr/share/applications/dw1-silicon.desktop`

---

### 9. Architecture Assumptions

**Current:** Assumes **arm64** (Apple Silicon).

**References:**
- `crates/decomp-c/build.rs` line 1: "arm64 macOS"
- `crates/decomp-c/build.rs` line 127: "Apple arm64"
- `crates/decomp-c/src/lib.rs` line 1: "compiled for arm64"
- `crates/psyq/src/trap.rs` line 5: "on arm64 the caller's arguments"
- `crates/psyq/src/libetc.rs` line 183: "arm64 macOS always keeps [frame pointers]"
- `crates/dw1/src/main.rs` line 39: "arm64 macOS keeps frame pointers"
- `crates/dw1/src/main.rs` line 63: `<mach/arm/_structs.h> (arm64)`

**Linux requirements:**
- Target x86_64 (most common) or arm64 (for ARM Linux)
- Update any architecture-specific code
- Test on both if possible

---

### 10. Build Dependencies

**Current (from README.md):**
- Apple command line tools (`xcode-select --install`)
- Rust (rustup)
- Python venv with PyYAML and CMake

**Linux requirements:**
- Rust (rustup) - same
- Python venv with PyYAML and CMake - same
- Clang or GCC for C compilation
- SDL3 development libraries
- Vulkan or OpenGL development libraries (for rendering)
- pkg-config for finding libraries

**Typical Linux packages (Debian/Ubuntu):**
```bash
sudo apt install build-essential clang cmake python3-venv libssl-dev pkg-config
sudo apt install libsdl3-dev libvulkan-dev vulkan-tools  # or libgl1-mesa-dev
```

---

## 11. Entorno de desarrollo (Docker)

Para no contaminar la máquina host, las dependencias se instalan en Docker. Hay dos imágenes:

| Dockerfile | Base | Propósito |
|---|---|---|
| `Dockerfile` (raíz) | `archlinux:latest` | Build principal de dw1-silicon (Rust, C, SDL3, Vulkan, etc.) |
| `decomp/Dockerfile` | `ubuntu:noble` | Build de `dw_decomp` (toolchain MIPS, splat, etc.) |

### Script `do`

El fichero `do` en la raíz es un wrapper para Docker:

- **Construir la imagen** (sin parámetros):
  ```bash
  ./do
  ```
  Construye y etiqueta la imagen como `dw1-builder`.

- **Ejecutar un comando dentro del contenedor** (con parámetros):
  ```bash
  ./do cargo build --release -p dw1
  ./do bash
  ./do cargo test
  ```

Monta el directorio actual (`$SCRIPT_DIR`) como `/dw1` dentro del contenedor y lo establece como `WORKDIR`.

### Flujo recomendado

```bash
# 1. Construir la imagen Docker (una sola vez)
./do

# 2. Ejecutar comandos de build dentro del contenedor
./do cargo build --release -p dw1

# 3. O entrar a un shell interactivo
./do bash
```

---

---

## Build Flow for Linux

### 1. Initial Setup

```bash
git clone https://github.com/loafykitten/dw1-silicon.git
cd dw1-silicon
git submodule update --init decomp
git -C decomp submodule update --init external/psyq_headers
python3 -m venv .venv
.venv/bin/pip install pyyaml cmake
```

### 2. Build Changes Required

**Modify `crates/decomp-c/build.rs`:**
- Remove or conditionalize `xcrun` usage
- Replace `check_host_symbols()` with Linux equivalent
- Ensure compiler flags work with Linux clang/gcc

**Modify `crates/render/Cargo.toml`:**
- Change wgpu features from `metal` to `vulkan` or `gl`

**Modify `crates/dw1/src/*.rs`:**
- Update file paths to use XDG directories
- Update splash screen text
- Update crash handler for Linux

**Remove/replace `tools/make-app.sh`:**
- Create Linux build script or just use `cargo build --release`
- Create `.desktop` file generation

### 3. Running on Linux

```bash
cargo build --release -p dw1
./target/release/dw1
```

Environment variables for disc path:
```bash
export DW1_DISC=/path/to/Digimon\ World\ \(USA\).cue
./target/release/dw1
```

---

## Key Files to Modify for Linux

### High Priority (Must Change)

1. **`crates/decomp-c/build.rs`**
   - Remove `xcrun` dependency (lines 410-426)
   - Replace `check_host_symbols()` with Linux version
   - Adjust compiler flags for Linux

2. **`crates/render/Cargo.toml`**
   - Change `features = ["metal", ...]` to `features = ["vulkan", ...]` or `["gl", ...]`

3. **`crates/dw1/src/main.rs`**
   - Update `default_save_dir()` to use XDG paths (lines 139-143)
   - Update `duckstation_card()` path (line 217)
   - Update crash handler for Linux (lines 39-127)

4. **`crates/dw1/src/settings.rs`**
   - Update settings path (line 2)

5. **`crates/dw1/src/window/snapshot.rs`**
   - Update reports path (line 2)

6. **`tools/make-app.sh`**
   - Replace with Linux build/packaging script
   - Or remove and document simple `cargo build` usage

### Medium Priority (Should Change)

7. **`crates/dw1/src/window/splash.rs`**
   - Update "Native Mac build" text (line 32)

8. **`packaging/Info.plist.in`**
   - Replace with `.desktop` file template

### Low Priority (Optional)

9. **Documentation files**
   - Update README.md for Linux instructions
   - Update guide.html if needed

---

## Testing Strategy

### Phase 1: Headless Build
- Build without window/renderer to verify C compilation
- Run headless replay tests
- Verify canonical state matches

### Phase 2: Window/Renderer
- Build with SDL3 + Vulkan/OpenGL
- Test window opens and displays
- Verify rendering matches (may need shader adjustments)

### Phase 3: Full Game
- Test save system with XDG paths
- Test controls on Linux
- Test audio (SDL3 audio should work)

### Phase 4: Packaging
- Create .desktop file
- Test installation
- Test icon display

---

## Potential Issues

### 1. Endianness
- PS1 is little-endian
- Both macOS (arm64) and Linux (x86_64/arm64) are little-endian
- No changes needed

### 2. Integer Sizes
- `dw1_native.h` redefines `long` as 32-bit
- This should work on Linux LP64 (where long is 64-bit)
- Test thoroughly

### 3. Alignment
- PS1 had specific alignment requirements
- macOS arm64 and Linux x86_64 may differ
- Watch for alignment-related bugs

### 4. Threading
- SDL3 threading differences between macOS and Linux
- Test audio threading carefully

### 5. File Systems
- macOS is case-insensitive by default
- Linux is case-sensitive
- Ensure all file paths use consistent case

---

## Dependencies by Crate

### `decomp-c`
- cc crate (C compilation)
- bindgen (Rust bindings)
- Python (for text generation)
- Clang/GCC

### `render`
- wgpu (graphics)
- pollster (async runtime)

### `dw1`
- SDL3 (window, input, audio)
- Other workspace crates

### `psyq`
- Pure Rust (no platform deps)

### `backend`
- Pure Rust (no platform deps)

---

## Notes from PLAN.md

**Important constraints:**
- Never commit disc data (image, extracted files, assets, dumps, captures)
- Gitignored directories: `disc/`, `dumps/`, `build/`, `captures/`, `ref/`
- Check `git status` before every commit
- Work on branch, never `main` directly
- Commit and push at discretion
- Never commit Docker-built artifacts or container state

**Architecture notes:**
- Sony's SDK is reimplemented clean (never translated from disassembly)
- Hybrid approach: decomp C game + Rust for everything new
- Full Rust as endgame (not Bevy)

**Docker notes:**
- Dependencies are installed in Docker containers to avoid polluting the host
- Two Dockerfiles: root `Dockerfile` (Arch, main build) and `decomp/Dockerfile` (Ubuntu, MIPS toolchain)
- Use `./do` to build the image or run commands inside the container
- The `do` script mounts the current directory as `/dw1` inside the container

---

## Quick Reference

### File Paths Summary

| Purpose | macOS Path | Linux Path (XDG) |
|---------|-----------|------------------|
| Saves | `~/Library/Application Support/dw1-silicon/saves/` | `~/.local/share/dw1-silicon/saves/` |
| Settings | `~/Library/Application Support/dw1-silicon/settings.txt` | `~/.config/dw1-silicon/settings.txt` |
| Reports | `~/Library/Application Support/dw1-silicon/reports/` | `~/.local/share/dw1-silicon/reports/` |
| DuckStation cards | `~/Library/Application Support/DuckStation/memcards/` | `~/.local/share/duckstation/memcards/` |

### Reference documents

- **`README-linux.md`** — Project summary and step-by-step to compile/run on Linux (in English).
- **`tools/build-linux.sh`** — Linux build script (run inside Docker via `./do`).
- **`external/`** — Gitignored folder for your legal `.cue`/`.bin` game disc.
- **`docs/linux-port/`** — Detailed port plan (7 phases, one document per phase).
- **`LINUX_PORT_STATUS.md`** — Phase progress checklist.
- **`LINUX_PORT_DECISIONS.md`** — Design decisions made.

### Platform: Linux only

**The project is Linux-only. macOS support has been intentionally removed.**

- `crates/decomp-c/build.rs` no longer contains any macOS-specific code:
  - `check_host_symbols()` (used `xcrun` + macOS SDK `.tbd` files) — deleted
  - `HOST_ALLOWED` host symbol allow-list — deleted
  - All `#[cfg(target_os = "macos")]` conditional blocks — deleted
- The code compiles on Linux x86_64 only. It will **not** compile on macOS.
- If macOS support is ever needed again, `check_host_symbols()` and the `xcrun` calls must be reimplemented from scratch.

### Tool Replacements

| macOS Tool | Linux Equivalent |
|------------|------------------|
| xcrun | None (use system paths) |
| otool | `objdump` or `readelf` |
| codesign | gpg (optional) or none |
| sips | ImageMagick (`convert`) |
| iconutil | None (use .png directly) |
| plutil | None (no .plist on Linux) |

### Cargo Feature Changes

**Current:**
```toml
wgpu = { version = "30.0.1", default-features = false, features = ["metal", "wgsl", "std"] }
```

**Linux (Vulkan):**
```toml
wgpu = { version = "30.0.1", default-features = false, features = ["vulkan", "wgsl", "std"] }
```

**Linux (OpenGL):**
```toml
wgpu = { version = "30.0.1", default-features = false, features = ["gl", "wgsl", "std"] }
```

---

## Conclusion

The port to Linux is feasible but requires systematic changes to:

1. Build system (remove macOS-specific tools)
2. C compilation (replace xcrun, adjust for Linux compilers)
3. Rendering backend (Metal → Vulkan/OpenGL)
4. File paths (macOS → XDG standard)
5. Crash handling (macOS → Linux signal handling)
6. Packaging (.app → .desktop + binary)

The core game logic (decomp C + PS1 library reimplementation) should remain largely unchanged as it's already cross-platform Rust with appropriate abstractions.

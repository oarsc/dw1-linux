# dw1-silicon - Agent Context for Linux Port

## Project Overview

dw1-silicon is a native port of Digimon World (PS1, USA SLUS-01032) from the matching decompilation project (jype0/dw_decomp). The original target is **arm64 macOS** (Apple Silicon), but the goal is to make it buildable and runnable on Linux.

**Architecture:** Hybrid approach - game C from decomp + Rust for everything new (PS1 libraries reimplemented). Long-term goal: full Rust migration.

**Current Status (2026-10-17):** Build compiles and links for Linux x86_64. Vulkan renderer works.
Game opens a window, shows title screen, skips intro video, reaches main menu, starts a new game,
shows Jijimon naming dialog, loads first map successfully. The `__DATA` segment limit crash on
first map load is fixed (uses `dl_iterate_phdr` for precise ELF segment limit).

---

## Critical Components for Linux Port

### 1. Build System

**Linux:** No app bundle is created. `cargo build --release` produces the plain binary.

**macOS (eliminated):** `tools/make-app.sh`, `packaging/Info.plist.in` and `tools/make-icon.py` were macOS-specific and have been deleted. The project is Linux-only. The icon source (`packaging/icon-1024.png`) is kept for the Linux `.desktop` file.

### 2. C Compilation (`crates/decomp-c/build.rs`)

**Target:** Linux x86_64 using system clang/gcc.

**Done (macOS code removed):**
- `check_host_symbols()` (used `xcrun` + macOS SDK `.tbd` files) — deleted
- `HOST_ALLOWED` host symbol allow-list — deleted
- `xcrun` dependency — removed
- All `#[cfg(target_os = "macos")]` conditional blocks — deleted
- Compiler flags work with Linux clang/gcc

**Remaining:** None for compilation. The build succeeds with `cargo build --release -p dw1`.

**Key includes/paths:**
- Native include: `crates/decomp-c/include/dw1_native.h`
- Psy-Q headers: `decomp/external/psyq_headers/mw_lib41/include`
- Generated headers: from decomp's `tools/gen_text.py`

### 3. Rendering Backend (`crates/render`)

**Current:** wgpu with **Vulkan** backend (was Metal on macOS).

**Done:**
- `Cargo.toml`: `features = ["vulkan", "wgsl", "std"]`
- Description updated to "wgpu on Vulkan"

**Remaining:** None — Vulkan backend compiles and opens a window.

### 4. Window System (`crates/dw1/src/window.rs`)

**Current:** SDL3 with Vulkan rendering.

**Done:**
- Removed `.metal_view()` call (line 429)
- Added `.vulkan()` to SDL3 window builder
- Comment about Metal layer order removed

**Remaining:** None — window opens and displays on Linux.

### 5. File Paths (Multiple Files)

**Done (XDG Base Directory Specification):**

**Saves directory:**
- `crates/dw1/src/main.rs`: `data_dir()` → `$XDG_DATA_HOME/dw1-linux/` (default `~/.local/share/dw1-linux/`). Used by `save_dir()` for save slots (`cardN.mcd`).
- `crates/dw1/src/window/snapshot.rs`: reports go to `data_dir()/reports/` → `~/.local/share/dw1-linux/reports/`.

**Settings:**
- `crates/dw1/src/settings.rs`: `Settings::path()` uses `settings_path()` → `$XDG_CONFIG_HOME/dw1-linux/settings.txt` (default `~/.config/dw1-linux/settings.txt`).

**DuckStation card import:**
- `crates/dw1/src/main.rs`: `duckstation_card()` → `~/.local/share/duckstation/memcards/Digimon World (USA)_1.mcd`.

**Functions:**
- `data_dir()` — XDG data dir for saves/reports
- `config_dir()` — XDG config dir for settings
- `default_save_dir()` — now returns `data_dir()`
- `settings_path()` — returns `config_dir()/settings.txt`
- `DW1_SAVE_DIR` env var still overrides save dir

### 6. Splash Screen (`crates/dw1/src/window/splash.rs`)

**Mac-specific text (still pending):**
- Line 32: "Native Mac build, written in Rust"

**Linux requirements:**
- Change to "Native Linux build" or "Native build"

### 7. Crash Handler (`crates/dw1/src/main.rs`)

**Mac-specific code (still pending):**
- Lines 39-127: Custom SIGSEGV/SIGBUS handler
- Uses `<mach/arm/_structs.h>` offsets for arm64
- Uses macOS-specific system calls (`sigaction`, `sigaltstack`, `backtrace_symbols_fd`)

**Linux requirements:**
- Replace with Linux signal handling
- Use Linux-specific ucontext offsets
- Use `backtrace()` from libgcc or similar for stack traces

### 8. Metadata (`packaging/`)

**Done (Linux .desktop file):**
- `packaging/dw1.desktop.in` — `.desktop` template for Linux desktop integration
- `tools/make-linux.sh` — installs binary, .desktop file, and icon

**macOS (no longer used, kept for reference):**
- `packaging/Info.plist.in` — macOS app bundle metadata
- `tools/make-app.sh` — macOS `.app` bundle creation

### 9. Architecture Assumptions

**Current:** Linux x86_64 (was arm64 macOS).

**Done:**
- `crates/decomp-c/build.rs`: compiles for Linux x86_64
- `crates/psyq/src/memory.rs`: uses `__data_start` + ELF segment limit via `dl_iterate_phdr` instead of macOS Mach-O symbols
- `crates/dw1/src/applog.rs`: uses `pthread_self()` instead of `pthread_main_np()`

### 10. Build Dependencies

**Current (from README.md):**
- Rust (rustup)
- Python venv with PyYAML and CMake
- Clang or GCC for C compilation
- SDL3 development libraries
- Vulkan development libraries
- pkg-config

**Typical Linux packages (Debian/Ubuntu):**
```bash
sudo apt install build-essential clang cmake python3-venv libssl-dev pkg-config
sudo apt install libsdl3-dev libvulkan-dev vulkan-tools
```

### 11. Entorno de desarrollo (Docker)

Para no contaminar la máquina host, las dependencias se instalan en Docker. Hay dos imágenes:

| Dockerfile | Base | Propósito |
|---|---|---|
| `Dockerfile` (raíz) | `archlinux:latest` | Build principal de dw1-silicon (Rust, C, SDL3, Vulkan, etc.) |
| `decomp/Dockerfile` | `ubuntu:noble` | Build de `dw_decomp` (toolchain MIPS, splat, etc.) |

### Script `do`

El fichero `do` en la raíz es un wrapper para Docker:

- **Construir la imagen** (sin parámetros):
  ```bash
  ./compile
  ```
- **Ejecutar un comando dentro del contenedor** (con parámetros):
  ```bash
  ./tools/dtb cargo build --release -p dw1
  ./tools/dtb bash
  ./tools/dtb cargo test
  ```

Monta el directorio actual (`$SCRIPT_DIR`) como `/dw1` dentro del contenedor y lo establece como `WORKDIR`.

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

### 2. Build

```bash
./tools/do                # Build Docker image (once)
./tools/dtb               # Build Distrobox container (once)
./compile                 # Compile the game
```

Produces `target/release/dw1` (ELF x86_64).

### 3. Running on Linux

```bash
export DW1_DISC=/path/to/Digimon\ World\ \(USA\).cue
./target/release/dw1
```

Inside Docker, you also need `XDG_RUNTIME_DIR` set:
```bash
export XDG_RUNTIME_DIR=/tmp/runtime-root
```

---

## Key Files to Modify for Linux

### High Priority (Must Change)

| File | Change | Status |
|------|--------|--------|
| `crates/decomp-c/build.rs` | Remove `xcrun`, `check_host_symbols()` | ✅ Done |
| `crates/render/Cargo.toml` | `metal` → `vulkan` | ✅ Done |
| `crates/dw1/src/window.rs` | Remove `.metal_view()`, add `.vulkan()` | ✅ Done |
| `crates/dw1/src/applog.rs` | Remove `pthread_main_np()`, use `pthread_self()` | ✅ Done |
| `crates/psyq/src/memory.rs` | Mach-O symbols → ELF `__data_start` + `dl_iterate_phdr` | ✅ Done |
| `crates/decomp-c/overlays.rs` | `.global` for overlay end symbols | ✅ Done |
| `crates/dw1/src/main.rs` | `data_dir()`, `config_dir()`, `settings_path()`, `duckstation_card()` (XDG paths) | ✅ Done |
| `crates/dw1/src/settings.rs` | XDG settings path (`config_dir()/settings.txt`) | ✅ Done |
| `crates/dw1/src/window/snapshot.rs` | XDG reports path (`data_dir()/reports/`) | ✅ Done |
| `crates/dw1/src/main.rs` | Crash handler (SIGSEGV/SIGBUS via Linux x86_64 ucontext), DuckStation path | ✅ Done |
| `crates/dw1/src/window/splash.rs` | "Native Mac build" text | ⬜ Pending |
| `packaging/Info.plist.in` | Deleted (macOS-only) | ✅ Done |
| `tools/make-app.sh` | Deleted (macOS-only) | ✅ Done |
| `tools/make-icon.py` | Deleted (macOS-only) | ✅ Done |

---

## Testing Strategy

### Phase 1: Headless Build
- ✅ Build without window/renderer to verify C compilation

### Phase 2: Window/Renderer
- ✅ Build with SDL3 + Vulkan
- ✅ Window opens and displays title screen
- ⬜ Verify rendering matches (may need shader adjustments)

### Phase 3: Full Game
- ⬜ Test save system with XDG paths
- ⬜ Test controls on Linux
- ⬜ Test audio (SDL3 audio should work)

### Phase 4: Packaging
- ⬜ Create .desktop file
- ⬜ Test installation
- ⬜ Test icon display

---

## Potential Issues

### 1. Endianness
- PS1 is little-endian
- Both macOS (arm64) and Linux (x86_64/arm64) are little-endian
- No changes needed

### 2. Integer Sizes
- `dw1_native.h` redefines `long` as 32-bit
- Works on Linux LP64 (where long is 64-bit)

### 3. `__DATA` segment limit on Linux ELF
- `_end` symbol does not always cover all static variables in Linux ELF
- **Fixed:** `crates/psyq/src/memory.rs` uses `dl_iterate_phdr` to find the real PT_LOAD segment limit

### 4. Alignment
- PS1 had specific alignment requirements
- macOS arm64 and Linux x86_64 may differ
- Watch for alignment-related bugs

### 5. File Systems
- macOS is case-insensitive by default
- Linux is case-sensitive
- Ensure all file paths use consistent case

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
- Use `./compile` to build the image or run commands inside the container

---

## Quick Reference

### File Paths Summary

| Purpose | macOS Path | Linux Path (XDG) |
|---------|-----------|------------------|
| Saves | `~/Library/Application Support/dw1-silicon/saves/` | `~/.local/share/dw1-linux/saves/` |
| Settings | `~/Library/Application Support/dw1-silicon/settings.txt` | `~/.config/dw1-linux/settings.txt` |
| Reports | `~/Library/Application Support/dw1-silicon/reports/` | `~/.local/share/dw1-linux/reports/` |
| DuckStation cards | `~/Library/Application Support/DuckStation/memcards/` | `~/.local/share/duckstation/memcards/` |

### Reference documents

- **`README-linux.md`** — Project summary and step-by-step to compile/run on Linux (in English).
- **`tools/build-linux.sh`** — Linux build script (run inside Docker via `./compile`).
- **`external/`** — Gitignored folder for your legal `.cue`/`.bin` game disc.
- **`docs/linux-port/`** — Detailed port plan (7 phases, one document per phase).
- **`LINUX_PORT_STATUS.md`** — Phase progress checklist.
- **`LINUX_PORT_DECISIONS.md`** — Design decisions made.

### Platform: Linux only

**The project is Linux-only. macOS support has been intentionally removed.**

- `crates/decomp-c/build.rs` no longer contains any macOS-specific code
- `crates/psyq/src/memory.rs` uses `#[cfg(target_os = "macos")]` to keep Mach-O symbols for macOS, ELF `dl_iterate_phdr` for Linux
- The code compiles on Linux x86_64

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

**Linux (Vulkan):**
```toml
wgpu = { version = "30.0.1", default-features = false, features = ["vulkan", "wgsl", "std"] }
```

---

## Conclusion

The port to Linux is feasible. Build compiles and links. Vulkan renderer opens a window. Game runs to the first map load, where a `__DATA` segment limit crash needs the `dl_iterate_phdr` fix in `crates/psyq/src/memory.rs` to be tested. Remaining work is platform adaptation (paths, crash handler, packaging), not build breakage.

The core game logic (decomp C + PS1 library reimplementation) remains largely unchanged as it's already cross-platform Rust with appropriate abstractions.
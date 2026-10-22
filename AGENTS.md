# dw1-linux - Agent Context for Linux Port

## Project Overview

dw1-linux is a native port of Digimon World (PS1, USA SLUS-01032) from the matching decompilation project (jype0/dw_decomp). It started from **dw1-silicon**, the arm64 macOS (Apple Silicon) port, and has been adapted to build and run natively on **Linux x86_64** (macOS support was removed).

**Architecture:** Hybrid approach - game C from decomp + Rust for everything new (PS1 libraries reimplemented). Long-term goal: full Rust migration.

**Current Status (2026-10-20):** Build compiles and links for Linux x86_64. Vulkan renderer works.
Game opens a window, shows title screen, skips intro video, reaches main menu, starts a new game,
shows Jijimon naming dialog, loads first map successfully. The `__DATA` segment limit crash on
first map load is fixed (uses `dl_iterate_phdr` for precise ELF segment limit). Saves, settings,
audio and controls have been exercised on Linux. Editing the game C (`decomp/src/`) and
recompiling works. Pending: certified replays against the PCSX-Redux oracle on Linux.

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

**Done:**
- `LINES` shows "Native Linux build, written in Rust" (line 31)
- Leftover comments mentioning the Mac build still need a cosmetic pass (no functional effect)

### 7. Crash Handler (`crates/dw1/src/main.rs`)

**Done (Linux):**
- `install_crash_trace()`: SIGSEGV/SIGBUS/SIGFPE handler installed with a hand-rolled
  `sigaction`/`sigaltstack` (x86_64 glibc layout, `SA_ONSTACK | SA_RESETHAND | SA_SIGINFO`)
- Stack printed with libgcc's `backtrace()` + `backtrace_symbols_fd()` (async-signal-safe)
- Enabled by default; `DW1_CRASH_TRACE=0` disables it

### 8. Metadata (`packaging/`)

**Done (Linux .desktop file):**
- `packaging/dw1.desktop.in` — `.desktop` template for Linux desktop integration
- `tools/make-linux.sh` — installs binary, .desktop file, and icon

**macOS files removed:** `packaging/Info.plist.in`, `tools/make-app.sh` and `tools/make-icon.py`
were deleted (macOS-only). Only `packaging/icon-1024.png` is kept.

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

### 11. Development environment (Docker)

To avoid polluting the host machine, dependencies are installed in Docker. There are two images:

| Dockerfile | Base | Purpose |
|---|---|---|
| `Dockerfile` (root) | `archlinux:latest` | Main dw1-linux build (Rust, C, SDL3, Vulkan, etc.) |
| `decomp/Dockerfile` | `ubuntu:noble` | `dw_decomp` build (MIPS toolchain, splat, etc.) |

`tools/do` (docker) runs with `--rm`, so anything cargo writes at run time is thrown away.
That is fine because the crates do not live in the container:

- The `Dockerfile` prefetches the registry into the image with `cargo fetch --locked`, from
  `Cargo.lock` and the workspace manifests (stub `src/`/`build.rs` files are generated only
  for the fetch). This layer is reused until the manifests or `Cargo.lock` change, so normal
  builds download nothing.
- Cargo still writes a few small files into `CARGO_HOME` (`/opt/cargo`: package-cache lock,
  global cache). Those go to the disposable layer and are recreated as needed. Both
  `/opt/cargo` and `/home/dw1` (the container `HOME`) are world-writable in the image, because
  `tools/do` runs commands with `--user "$(id -u):$(id -g)"`.
- A dependency added locally without rebuilding the image is downloaded into that disposable
  layer, i.e. once per run. Rebuild the image to bake it in, or mount a volume at
  `/opt/cargo` (commented in `tools/do`) if iterating on `Cargo.toml` a lot.

Running as the invoking user keeps `target/` (a bind mount) owned by that user instead of
`root`. Old root-owned build trees can be fixed once with
`docker run --rm -v "$PWD:/dw1" dw1-builder chown -R "$(id -u):$(id -g)" /dw1/target`.

`tools/do` is the default wrapper for running commands in Docker.

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
| `crates/dw1/src/main.rs` | Crash handler (Linux x86_64: `sigaction`/`sigaltstack` + libgcc `backtrace()`), DuckStation path | ✅ Done |
| `crates/dw1/src/window/splash.rs` | "Native Mac build" text → "Native Linux build" | ✅ Done |
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
- ✅ Reaches the main menu, starts a new game and loads the first map
- ⬜ Verify rendering matches the original (may need shader adjustments)

### Phase 3: Full Game
- ✅ Save system with XDG paths (save/load works)
- ✅ Controls on Linux (keyboard and gamepad)
- ✅ Audio (SDL3/ALSA)
- ✅ Splash screen says "Native Linux build"
- ✅ Crash trace on Linux (`DW1_CRASH_TRACE`)

### Phase 4: Packaging
- ✅ `.desktop` file and icon (`tools/make-linux.sh`)
- ⬜ Test installation (`tools/make-linux.sh --install`)
- ⬜ Test icon display
- ⬜ Certified replays (43) against the PCSX-Redux oracle on Linux

---

## Potential Issues

### 1. Endianness
- PS1 is little-endian
- Linux x86_64 is little-endian
- No changes needed

### 2. Integer Sizes
- `dw1_native.h` redefines `long` as 32-bit
- Works on Linux LP64 (where long is 64-bit)

### 3. `__DATA` segment limit on Linux ELF
- `_end` symbol does not always cover all static variables in Linux ELF
- **Fixed:** `crates/psyq/src/memory.rs` uses `dl_iterate_phdr` to find the real PT_LOAD segment limit

### 4. Alignment
- PS1 had specific alignment requirements
- The host (x86_64) may differ
- Watch for alignment-related bugs

### 5. File Systems
- Linux is case-sensitive (macOS was not)
- Ensure all file paths use consistent case

### 6. Host ABI details still assumed from the macOS build
- `crates/decomp-c/include/setjmp.h` declares `jmp_buf` as 48 ints (192 bytes), which was
  arm64 macOS's `_JBLEN`. On x86_64 glibc a `jmp_buf` is a 200-byte struct, but `_setjmp` (the
  mask-less variant used here) only stores 68 bytes, so it works; if the script interpreter ever
  behaves oddly after a `longjmp`, check this first.
- Stack walks use libgcc's `backtrace()` (unwind tables), not frame pointers: keep it that way
  if the build flags change.

### 7. Integer division by zero and `INT32_MIN / -1`
- The R3000A's `DIV` never traps: a zero divisor gives LO = -1 for a non-negative dividend
  (1 for a negative one), and `INT32_MIN / -1` gives `INT32_MIN`. The host's `idiv` raises
  SIGFPE on both, so game C that divides by a script or data value must use `DW1_DIV(a, b)`
  (`decomp/include/dw/types.h`, where the native build's `dw1_div` gives the PS1's results;
  the PS1 build keeps the plain `/`) instead of `/`. `tickMoveObjectTo`/`tickEntityMoveTo*` and
  the healing particles do; an Amida Forest enemy attack crashed on a zero step
  (docs/bugs.md).
- The game's divisions on values that are always non-zero (constants, array sizes, screen
  dimensions) need nothing; the PS1's `DIV` is not emulated globally.

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

| Purpose | macOS Path (old) | Linux Path (XDG) |
|---------|-----------|------------------|
| Saves | `~/Library/Application Support/dw1-silicon/saves/` | `~/.local/share/dw1-linux/card<N>.mcd` |
| Settings | `~/Library/Application Support/dw1-silicon/settings.txt` | `~/.config/dw1-linux/settings.txt` |
| Reports | `~/Library/Application Support/dw1-silicon/reports/` | `~/.local/share/dw1-linux/reports/` |
| DuckStation cards | `~/Library/Application Support/DuckStation/memcards/` | `~/.local/share/duckstation/memcards/` |

### Reference documents

- **`README.md`** — Project summary and step-by-step to compile/run on Linux (in English).
- **`tools/build-linux.sh`** — Linux build script (run inside Docker via `./compile` / `./do`).
- **`disc/`** — Gitignored folder for your legal `.cue`/`.bin` game disc. The build scripts and the
  game find `disc/Digimon World (USA).cue` on their own (`DW1_DISC` overrides), and the disc
  comparison tests additionally need `dumpsxiso`'s files in `decomp/disks/us`
  (`DW1_DISC_FILES` overrides).
- **`docs/`** — Original port plan and phase documents (`phase*-plan.md`, `s0*-*.md`).
- **`LINUX_PORT_STATUS.md`** — Phase progress checklist.
- **`LINUX_PORT_DECISIONS.md`** — Design decisions made.

### Platform: Linux only

**The project is Linux-only. macOS support has been intentionally removed.**

- `crates/decomp-c/build.rs` no longer contains any macOS-specific code
- `crates/psyq/src/memory.rs` uses `__data_start` plus the real ELF `PT_LOAD` segment limit via
  `dl_iterate_phdr` (no `#[cfg(target_os = "macos")]` branches remain anywhere)
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

The Linux port builds and runs: Vulkan window, title screen, intro skip, main menu, new game,
naming dialog and first map. The PS1 SDK, overlays, saves/settings/reports (XDG), audio,
controls, Linux crash traces and Linux packaging are all in place, and game C in
`decomp/src/` can be edited and recompiled. The remaining work is verification (certified
replays against the PCSX-Redux oracle on Linux) and cosmetic cleanup of comments that still
mention the old Mac build.

The core game logic (decomp C + PS1 library reimplementation) remains largely unchanged as it's
already cross-platform Rust with appropriate abstractions.

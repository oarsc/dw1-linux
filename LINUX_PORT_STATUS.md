# LINUX_PORT_STATUS.md — Current status of the Linux port

This file is updated as progress is made. It serves as a unified checkpoint to know which phase the work is in and what remains pending.

---

## Current phase

**Phases 0–6 done; Phase 7 in progress (verification pending)**

The game builds, opens a Vulkan window, reaches the title screen, skips the intro video,
enters the main menu, starts a new game, shows the Jijimon naming dialog, and loads the
first map successfully. The `__DATA` segment limit crash on first map load is fixed.
Saves/settings/reports use XDG paths and have been exercised, as have audio and controls.
The Linux crash trace works, the splash says "Native Linux build", and the game C in
`decomp/src/` can be edited and recompiled. Pending: certified replays against the
PCSX-Redux oracle on Linux, and testing `tools/make-linux.sh --install`.

---

## Checklist of milestones by phase

| Phase | Milestone | Status | Notes |
|---|---|---|---|
| 0 | Read and understand the codebase | ✅ | Done |
| 0 | Document macOS components (AGENTS.md) | ✅ | Done |
| 0 | Create port plan (`docs/`) | ✅ | Done |
| 0 | Docker environment ready (`Dockerfile`, `decomp/Dockerfile`, `tools/do`, `tools/dtb`, `./compile`, `./run`) | ✅ | Done |
| 0 | `README.md` created (summary + step-by-step) | ✅ | Done (was `README-linux.md` before the README swap) |
| 1 | Create `tools/build-linux.sh` | ✅ | Done |
| 1 | macOS `make-app.sh` / `Info.plist.in` / `make-icon.py` | ✅ Deleted (macOS-only) |
| 1 | `README.md` with Linux instructions (build-linux.sh via `./compile`) | ✅ | Done |
| 1 | Document `external/` folder for game disc | ✅ | Done |
| 2 | `check_host_symbols()` removed | ✅ | Deleted from `build.rs` |
| 2 | `xcrun` removed on Linux | ✅ | Removed |
| 2 | `decomp-c` compiles on Linux | ✅ | Builds with clang/gcc on Linux x86_64 |
| 2 | Overlay section symbols `.global` on Linux ELF | ✅ | `crates/decomp-c/overlays.rs`: `_end`/`_zend` now `.global` |
| 2 | macOS-only host symbols replaced | ✅ | `crates/psyq/src/memory.rs`: `__data_start` + real ELF segment limit via `dl_iterate_phdr`; `_end` as fallback |
| 2 | Overlay runtime: keep variables outside sections no longer panic | ✅ | `crates/decomp-c/src/overlays.rs`: skips resident variables outside overlay sections |
| 2 | Overlay keep list excludes resident variables | ✅ | `crates/decomp-c/overlays.rs`: `keeps()` skips resident symbols |
| 3 | wgpu Metal → Vulkan | ✅ | `crates/render/Cargo.toml`: `features = ["vulkan", "wgsl", "std"]` |
| 3 | SDL3 window uses Vulkan (not Metal) | ✅ | `crates/dw1/src/window.rs`: removed `.metal_view()`, added `.vulkan()` |
| 3 | Window opens on Linux | ✅ | Opens, shows title screen, skips intro, reaches main menu |
| 3 | `XDG_RUNTIME_DIR` needed in container | ✅ | Must be set when running headless/in container |
| 3 | `dl_iterate_phdr` for precise ELF `__DATA` segment limit | ✅ | `crates/psyq/src/memory.rs`: uses `dl_iterate_phdr` instead of `_end` + margin |
| 4 | XDG paths for saves/settings/reports | ✅ | `data_dir()` → `$XDG_DATA_HOME/dw1-linux/`; `config_dir()` → `$XDG_CONFIG_HOME/dw1-linux/`; `default_save_dir()` → `data_dir()`; `settings_path()` → `config_dir()/settings.txt`; `duckstation_card()` → `.local/share/duckstation/` |
| 4 | `DW1_DATA_DIR` / `DW1_CONFIG_DIR` | ✅ | Uses `XDG_DATA_HOME`/`XDG_CONFIG_HOME` directly (XDG spec) |
| 4 | Linux packaging (`.desktop` + icon) | ✅ | `packaging/dw1.desktop.in`, `tools/make-linux.sh` |
| 4 | Installation tested (`--install`) | ⬜ | Not tried yet |
| 5 | Linux crash handler (SIGSEGV/SIGBUS/SIGFPE) | ✅ | `crates/dw1/src/main.rs`: `sigaction`/`sigaltstack` (x86_64 glibc layout) + libgcc `backtrace()`; on by default, `DW1_CRASH_TRACE=0` disables |
| 5 | `pthread_main_np` removed (applog main thread) | ✅ | `crates/dw1/src/applog.rs`: captures `pthread_self()` in `start()` |
| 6 | Splash screen text | ✅ | `crates/dw1/src/window/splash.rs`: "Native Linux build, written in Rust" |
| 7 | Window, audio, controls, saves | ✅ | Vulkan window, SDL3/ALSA audio, keyboard+gamepad, XDG save/load all exercised |
| 7 | 43 certified replays pass on Linux | ⬜ | Not run yet against the PCSX-Redux oracle |
| — | Edit C of `dw_decomp` for mod/correction | ✅ | `decomp/src/` edited and recompiled (healing effect, texture loading) |

---

## Immediate next steps

1. **Run the certified replays on Linux** (the only verifiable gap left). They need the local,
   gitignored oracle dumps (`captures/oracle-runs/`) and fixture cards (`captures/fixtures/`),
   which are not present in a fresh checkout:
   ```bash
   tools/dtb tools/replay-check.sh        # or: tools/replay-check.sh, on a host with deps
   tools/dtb tools/replay-check.sh new-game file-city-walk   # a subset
   ```
2. Optionally package/install for Linux (installs to /usr/local):
   ```bash
   tools/dtb tools/make-linux.sh --install
   ```
3. Continue modding: edit `decomp/src/` (or `decomp/text/`), rebuild and test:
   ```bash
   ./compile                     # builds the release binary in the container
   ./run                         # runs it with DW1_DISC pointing at external/
   ```
4. Read `docs/s06-platform.md` and `docs/s08-oracle.md` for context on the oracle.

---

## Current blockers

None for playing: the game builds, opens a Vulkan window, saves to `~/.local/share/dw1-linux/`,
runs to the first map, plays audio, accepts keyboard/gamepad input, and can be packaged/installed.

Pending verification: the 43 certified replays have not been run on Linux yet.

---

## Changes made to get the build passing and running

- `crates/decomp-c/overlays.rs` (build script): `overlay_sections_asm()` marks `dw1_{u}_end`
  and `dw1_{u}_zend` as `.global` so `overlay_bounds.c` can reference them.
- `crates/decomp-c/overlays.rs` (build script): `keeps()` no longer includes resident variables
  (they live in the main executable, not the overlay).
- `crates/decomp-c/src/overlays.rs` (runtime): skips keep variables outside overlay sections
  instead of panicking (they are resident main-executable variables).
- `crates/dw1/src/applog.rs`: replaced macOS-only `pthread_main_np()` with `pthread_self()`
  captured in `start()`.
- `crates/psyq/src/memory.rs`: `DATA_START`/`DATA_END` use `__data_start` + real ELF segment
  limit via `dl_iterate_phdr` (precise, no workaround margin), with `_end` as fallback.
- `crates/render/Cargo.toml`: wgpu features changed from `metal` to `vulkan`.
- `crates/dw1/src/window.rs`: removed `.metal_view()`, added `.vulkan()` to SDL3 window builder.
- `crates/dw1/src/window.rs`: pause/unpause fixes — `self.events()` in `pad()` and
  `wait_for_field()`, `sleep(1ms)` when no input, `start_was_pressed`/`pause_present_needed`
  state, `present_pause_frame()` method.
- `crates/dw1/src/main.rs`: `data_dir()` (`$XDG_DATA_HOME/dw1-linux/`), `config_dir()`
  (`$XDG_CONFIG_HOME/dw1-linux/`), `default_save_dir()` → `data_dir()`,
  `settings_path()` → `config_dir()/settings.txt`, `duckstation_card()` → XDG DuckStation path.
- `crates/dw1/src/settings.rs`: `Settings::path()` uses `settings_path()` (XDG config dir).
- `crates/dw1/src/window/snapshot.rs`: comment updated from macOS to Linux paths.
- `crates/dw1/src/main.rs`: crash handler — replaced the macOS arm64 handler with a Linux
  x86_64 `sigaction`/`sigaltstack` handler (hand-rolled glibc layout) that prints the stack with
  libgcc `backtrace()`/`backtrace_symbols_fd()` for SIGSEGV/SIGBUS/SIGFPE. Enabled by default;
  `DW1_CRASH_TRACE=0` disables it.
- `crates/dw1/Cargo.toml`: added `libc` dependency.
- `crates/dw1/src/window/splash.rs`: splash text is "Native Linux build, written in Rust".
- `packaging/dw1.desktop.in`: new `.desktop` template for Linux desktop integration.
- `tools/make-linux.sh`: new Linux packaging script (builds release binary, `--install`
  copies binary to `$PREFIX/bin`, .desktop to `$PREFIX/share/applications`, icon to
  `$PREFIX/share/icons/hicolor/1024x1024/apps/`).
- `tools/make-app.sh`, `packaging/Info.plist.in`, `tools/make-icon.py`: deleted (macOS-only).

### Cosmetic pass (2026-10-20)

Stale macOS-era comments/docs replaced with Linux wording (no behaviour change): crate
descriptions (`crates/dw1/Cargo.toml`, `crates/decomp-c/Cargo.toml`), `crates/render/src/lib.rs`,
`crates/dw1/src/window.rs` (wgpu on Vulkan, no Cmd-Q, Super-Ctrl-F), `crates/dw1/src/window/splash.rs`,
`crates/dw1/src/window/disc_picker.rs`, `crates/dw1/src/applog.rs`, `crates/psyq/src/{libc,native,trap,libetc}.rs`,
`crates/decomp-c/{build.rs,src/lib.rs,include/dw1_native.h,include/setjmp.h}`. Also fixed the
broken `./do` invocations in `README.md` (the wrapper is `tools/do`/`tools/dtb`) and the
`docs/linux-port/` path references (the plan lives in `docs/`).

---
## Editing game C for mods and corrections

The game C source lives in the `decomp/` submodule (fork `oarsc/dw_decomp`, based on `jype0/dw_decomp`). To modify the game:

1. **Edit** files in `decomp/src/` (or `decomp/text/` for YAML-based text). Never edit generated files (`asm/`, `build/`, `assets/`, `disks/`).
2. **Recompile:** `./compile`
3. **Test:** `DW1_DISC=/path/to/Digimon\ World\ \(USA\).cue ./target/release/dw1` (or `./run`)
4. **Verify:** Run certified replays against the PCSX-Redux oracle (`tools/replay-check.sh`) to confirm no behavioral regression.

The game C calls PS1 SDK functions implemented as `extern "C"` in Rust (`crates/psyq/`). New SDK calls must be added there first.

See `D14` in `LINUX_PORT_DECISIONS.md` for full details.

---
*End of LINUX_PORT_STATUS.md*

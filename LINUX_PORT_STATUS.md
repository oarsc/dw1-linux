# LINUX_PORT_STATUS.md — Current status of the Linux port

This file is updated as progress is made. It serves as a unified checkpoint to know which phase the work is in and what remains pending.

---

## Current phase

**Phase 3 — Rendering backend** (done)

The game builds, opens a Vulkan window, reaches the title screen, skips the intro video,
enters the main menu, starts a new game, shows the Jijimon naming dialog, and loads the
first map successfully. The `__DATA` segment limit crash on first map load is fixed.

---

## Checklist of milestones by phase

| Phase | Milestone | Status | Notes |
|---|---|---|---|
| 0 | Read and understand the codebase | ✅ | Done |
| 0 | Document macOS components (AGENTS.md) | ✅ | Done |
| 0 | Create port plan (docs/linux-port/) | ✅ | Done |
| 0 | Docker environment ready (`Dockerfile`, `decomp/Dockerfile`, `do`) | ✅ | Done |
| 0 | `README-linux.md` created (summary + step-by-step) | ✅ | Done |
| 1 | Create `tools/build-linux.sh` | ✅ | Done |
| 1 | Guard in `tools/make-app.sh` | ⬜ | |
| 1 | `README-linux.md` with Linux instructions (build-linux.sh via `./do`) | ✅ | Done |
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
| 5 | Linux crash handler (SIGSEGV/SIGBUS) | ✅ | `crates/dw1/src/main.rs`: replaced macOS `<mach/arm/_structs.h>` with Linux x86_64 `ucontext_t` + `gregs[]` via `libc` |
| 5 | `pthread_main_np` removed (applog main thread) | ✅ | `crates/dw1/src/applog.rs`: captures `pthread_self()` in `start()` |
| 6 | `.desktop` file | ⬜ | |
| 6 | Install/uninstall scripts | ⬜ | |
| 7 | 43 certified replays pass on Linux | ⬜ | |
| 7 | Window, audio, controls, saves | ⬜ | |
| — | Edit C of `dw_decomp` for mod/correction | ⬜ | Main user goal |

---

## Immediate next steps

1. **The game now runs** — recompile and test:
   ```bash
   ./dtb tools/build-linux.sh
   ./dtb env DW1_DISC="/dw1/external/Digimon World (USA).cue" target/release/dw1
   ```
2. Remaining macOS-only pieces:
   - `crates/dw1/src/window/splash.rs`: "Native Mac build" text.
3. Verify a legal copy of the Digimon World disc is available for testing (`DW1_DISC`).
4. Read `dw1-silicon/docs/s06-platform.md` and `docs/s08-oracle.md` for context.

---

## Current blockers

None — the game builds, opens a Vulkan window, saves to `~/.local/share/dw1-linux/`, and runs to the first map. Remaining work is platform adaptation (splash text, packaging), not build breakage.

---

## Changes made to get the build passing and running

- `crates/decomp-c/overlays.rs` (build script): `overlay_sections_asm()` marks `dw1_{u}_end`
  and `dw1_{u}_zend` as `.global` so `overlay_bounds.c` can reference them.
- `crates/decomp-c/overlays.rs` (build script): `keens()` no longer includes resident variables
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
- `crates/dw1/src/main.rs`: crash handler — replaced macOS `<mach/arm/_structs.h>` arm64
  signal handler with Linux x86_64 `ucontext_t` + `gregs[]` via `libc` for SIGSEGV/SIGBUS.
- `crates/dw1/Cargo.toml`: added `libc` dependency.

---

*End of LINUX_PORT_STATUS.md*
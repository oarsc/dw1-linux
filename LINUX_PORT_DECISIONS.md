# LINUX_PORT_DECISIONS.md — Design decisions for the Linux port

This file records architectural and flow decisions, with their justification, so they are not revisited unnecessarily.

---

## D1. Use dw1-silicon as base, not as external reference

**Decision:** `dw1-silicon` is the codebase for the port. It is cloned/copied and adapted to Linux.

**Justification:** It already has the game running natively: `dw_decomp` C integrated, PS1 hardware models (GTE, GPU, SPU, XA, MDEC), PS1 SDK in Rust, overlays, saves, sound, and oracle against PCSX-Redux. Porting the macOS host layer to Linux is much less work than building from scratch.

**Consequence:** The language is Rust + C. The `dw1-silicon` code is adapted, not rewritten from scratch.

---

## D2. Rust is acceptable for the host layer

**Decision:** Rust is accepted for window, input, audio, GPU, PS1 SDK, and everything that is not game logic.

**Justification:** The user accepts any human-readable language (Rust, C, Kotlin, etc.). `dw1-silicon` already has that layer written and working.

**Consequence:** No need to rewrite the host layer in C. Only adapt macOS-specific parts to Linux.

---

## D3. Target: native Linux x86_64

**Decision:** The final destination is a native Linux x86_64 executable (not macOS, not Windows for now).

**Justification:** The user wants to run on Linux. `dw1-silicon` is macOS/Apple Silicon (arm64), so the host layer must be ported and the target architecture changed.

**Consequence:** Change Metal → Vulkan (or OpenGL), CoreAudio → SDL3/ALSA, `.app` → Linux executable, macOS paths → XDG, arm64 → x86_64.

---

## D4. `dw_decomp` as source of editable C for mods

**Decision:** The Digimon World C source comes from `dw_decomp` (submodule `decomp/`). To make mods or corrections, edit that C and recompile.

**Justification:** It is readable C, written by humans, organized by overlays. It meets the user's requirement of "C code I can edit."

**Consequence:** The C compiles for x86_64 Linux with clang/gcc, linked against the PS1 SDK in Rust (`crates/psyq/`). See `README.md` and `LINUX_PORT_STATUS.md`.

---

## D5. Maintain macOS compatibility — OBSOLETE

**Status: obsolete, superseded by D15.** The port became Linux-only and all macOS-specific code
was removed (no `#[cfg(target_os = "macos")]` branches remain; the macOS packaging scripts were
deleted).

**Original decision:** use `#[cfg(target_os = "...")]` and `#ifdef __linux__` to keep macOS working.

**Why it was dropped:** keeping the macOS host layer alive cost effort in the build script, the
ELF/Mach-O memory handling and the packaging, with no benefit for this fork. The upstream
`dw1-silicon` repository remains the reference for the macOS build.

**Consequence:** platform-conditional branches are no longer required; Linux is the only target.

---

## D6. PS1 SDK cleanly reimplemented

**Decision:** The Sony SDK is reimplemented from public documentation (psx-spx) and emulator observation. Never translate the SDK disassembly line by line.

**Justification:** Rule established in `dw1-silicon` to avoid license and copyright issues.

**Consequence:** `crates/psyq/` contains Rust implementations of SDK calls.

---

## D7. Oracle: PCSX-Redux for verification

**Decision:** PCSX-Redux (pinned revision) is used as ground truth to verify that the Linux port behaves like the original.

**Justification:** `dw1-silicon` already has this oracle system (replays, canonical state, frame comparison). It is adapted to Linux.

**Consequence:** PCSX-Redux must be compiled for Linux for Phase 7 tests.

---

## D8. Personal use only, no distribution

**Decision:** All work is for personal use, no publication or distribution.

**Justification:** Avoids license and copyright issues. It is assumed the user owns a legal copy of the disc.

**Consequence:** No executables, assets, or code are uploaded to the internet. `.bin`/`.cue` files are not committed.

---

## D9. `psxrecomp` as optional reference for future mods

**Decision:** `psxrecomp` (`/home/oar/pro/psxrecomp`) is consulted as reference for the `.psxmod` mod system, but not used as codebase for this port.

**Justification:** `psxrecomp` has a versioned mod system (byte patches, asset overlays, C plugins) that could be reused or inspire future modding functionality in dw1-linux.

**Consequence:** Consulted only as inspiration for future mod tooling; not part of the build.

---

## D10. DW2-PC as PC architecture template

**Decision:** `DW2-PC` (github.com/Wyrelade/DW2-PC, CC0) is used as reference for project organization for a native PC port (`src/`, `psyq/`, `backend/`, `host/`).

**Justification:** `dw1-silicon` explicitly cites DW2-PC as its design template. It is in C and for Windows/Linux.

**Consequence:** See `docs/dw2pc-reuse.md`.

---

## D11. Dependencies in Docker, not on host

**Decision:** Build dependencies are installed in Docker containers, not on the host machine.

**Justification:** Avoids polluting the host system with toolchains, libraries, and compilers specific to the project. Allows reproducibility and cleanliness.

**Consequence:** Two Dockerfiles are used (`Dockerfile` for Arch/main build, `decomp/Dockerfile` for Ubuntu/dw_decomp). Two wrappers run commands inside the container mounting the repo at `/dw1`: `tools/dtb` (distrobox) and `tools/do` (plain docker). `./compile` (through `tools/dtb`) builds the release binary and `./run` runs it.

---

## D12. User documentation in `README.md`

**Decision:** Keep a simple and up-to-date `README.md` with project summary and step-by-step to compile/run on Linux.

**Justification:** It is the entry point for anyone (including future self) who wants to build the project without reading all phase documentation. (The Linux instructions started in `README-linux.md`; the macOS readme was moved to `README-silicon.md` and the Linux one became `README.md`.)

**Consequence:** Every time a new step is added to the build or run flow (e.g., a Linux build script, an environment variable, or a new dependency), it must be reflected in `README.md`.

---

## D13. Build script in `tools/build-linux.sh`

**Decision:** Provide `tools/build-linux.sh` as Linux build script, executed inside the Docker container (via `tools/dtb` or `./compile`).

**Justification:** Provides a consistent interface to compile, configures CMake from `.venv` if not in PATH, and produces a plain binary instead of a macOS `.app` package.

**Consequence:** The script runs inside the container (WORKDIR=/dw1), not on the host. It is invoked as `./compile` (which runs it through `tools/dtb`), or directly with `tools/dtb tools/build-linux.sh`.

---
## D14. Edit dw_decomp C for mods and corrections

**Decision:** The game C source lives in the `decomp/` submodule (fork `oarsc/dw_decomp`, based on `jype0/dw_decomp`). Users edit files in `decomp/src/` directly to modify game logic, stats, text, etc., then recompile with `./compile` (release build inside the container).

**Justification:** The user's main goal is having readable, editable C code that runs natively on Linux. `dw_decomp` provides human-readable C organized by overlays (main, btl, evl, std, trn, etc.), not machine-translated code.

**Consequence:** Changes to game C are made in `decomp/src/` (or `decomp/text/` for YAML-based text). Generated files (`asm/`, `build/`, `assets/`, `disks/`) must never be edited. After editing, recompile and verify against the oracle (PCSX-Redux certified replays) to ensure behavior matches the original PS1.

**C↔Rust boundary:** The game C calls PS1 SDK functions (`GsSortObject4J`, `CdRead`, `PadRead`, etc.) implemented as `extern "C"` in Rust (`crates/psyq/`). If a mod needs a new SDK call, it must be added to `crates/psyq/` first.

**External references:** `psxrecomp` (`.psxmod` versioned mod system) and `DW2-PC` (PC architecture template) are consulted as inspiration for future mod tooling, but are not part of the codebase.

---

## D15. Linux x86_64 is the only target (replaces D5)

**Decision:** The port targets native Linux x86_64 only. macOS support was deliberately removed: no `#[cfg(target_os = "macos")]` / `#ifdef __linux__` branches are kept, and the macOS packaging files (`tools/make-app.sh`, `tools/make-icon.py`, `packaging/Info.plist.in`) were deleted.

**Justification:** Maintaining two host layers cost effort in the build script (`xcrun`/host-symbol checks), the ELF-vs-Mach-O data segment handling and the packaging, with no benefit for this fork. Upstream `dw1-silicon` already covers macOS.

**Consequence:** Platform conditionals are no longer needed. Build/run/packaging are Linux-only (`./compile`, `./run`, `tools/make-linux.sh`), paths follow XDG, and the crash trace uses Linux `sigaction` + libgcc `backtrace()`.

---

## D16. The HD depth test is its own option, on by default

**Decision:** The HD surfaces draw with a per-pixel depth test (`depth` in `settings.txt`, F6, `DW1_DEPTH=1`, default on), separate from "no wobble" (`no_wobble` / F3 / `DW1_PGXP`). The depths are the GTE's per-vertex view depths, which `backend::pgxp` already records; recording is on when either option is (positions for no wobble, depths for the test).

**Justification:** The user reported (from play) a part of a model showing through another that lies in front of it, and asked for it to be fixed with a toggle, on by default, rather than tied to no wobble. The cause is the PS1's own drawing order (whole polygons sorted by average depth; no z-buffer), so a per-pixel test is an addition: it has to be off to see the exact original picture.

**Consequence:** The 1x VRAM never changes, so game logic, saves and replays don't either. The test skips polygons drawn as the 1x picture (2D and sprites) and any polygon whose corners were not all projected this frame; `docs/phase8-plan.md` 8.7 lists the limits. Turning an option off stops its recording.

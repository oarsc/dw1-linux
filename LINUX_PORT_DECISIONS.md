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

**Consequence:** The C compiles for x86_64 Linux with clang/gcc, linked against the PS1 SDK in Rust (`crates/psyq/`). See `docs/linux-port/08-editing-c.md`.

---

## D5. Maintain macOS compatibility

**Decision:** All changes use `#[cfg(target_os = "...")]` and `#ifdef __linux__` to keep macOS working.

**Justification:** We do not want to break the macOS build. The port is additive, not substitutive.

**Consequence:** The codebase will have platform-conditional branches.

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

**Consequence:** See `docs/linux-port/09-external-references.md`.

---

## D10. DW2-PC as PC architecture template

**Decision:** `DW2-PC` (github.com/Wyrelade/DW2-PC, CC0) is used as reference for project organization for a native PC port (`src/`, `psyq/`, `backend/`, `host/`).

**Justification:** `dw1-silicon` explicitly cites DW2-PC as its design template. It is in C and for Windows/Linux.

**Consequence:** See `docs/linux-port/09-external-references.md`.

---

## D11. Dependencies in Docker, not on host

**Decision:** Build dependencies are installed in Docker containers, not on the host machine.

**Justification:** Avoids polluting the host system with toolchains, libraries, and compilers specific to the project. Allows reproducibility and cleanliness.

**Consequence:** Two Dockerfiles are used (`Dockerfile` for Arch/main build, `decomp/Dockerfile` for Ubuntu/dw_decomp) and the `do` script as wrapper to build images and run commands inside the container mounting the current directory.

---

## D12. User documentation in `README-linux.md`

**Decision:** Keep a simple and up-to-date `README-linux.md` with project summary and step-by-step to compile/run on Linux.

**Justification:** It is the entry point for anyone (including future self) who wants to build the project without reading all phase documentation.

**Consequence:** Every time a new step is added to the build or run flow (e.g., a Linux build script, an environment variable, or a new dependency), it must be reflected in `README-linux.md`.

---

## D13. Build script in `tools/build-linux.sh`

**Decision:** Provide `tools/build-linux.sh` as Linux build script, executed inside the Docker container via `./do`.

**Justification:** Provides a consistent interface to compile, configures CMake from `.venv` if not in PATH, and produces a plain binary instead of a macOS `.app` package.

**Consequence:** The script runs inside the container (WORKDIR=/dw1), not on the host. It is invoked as `./do tools/build-linux.sh` or directly `./do cargo build --release -p dw1`.

---
## D14. Edit dw_decomp C for mods and corrections

**Decision:** The game C source lives in the `decomp/` submodule (fork `oarsc/dw_decomp`, based on `jype0/dw_decomp`). Users edit files in `decomp/src/` directly to modify game logic, stats, text, etc., then recompile with `./do cargo build --release -p dw1`.

**Justification:** The user's main goal is having readable, editable C code that runs natively on Linux. `dw_decomp` provides human-readable C organized by overlays (main, btl, evl, std, trn, etc.), not machine-translated code.

**Consequence:** Changes to game C are made in `decomp/src/` (or `decomp/text/` for YAML-based text). Generated files (`asm/`, `build/`, `assets/`, `disks/`) must never be edited. After editing, recompile and verify against the oracle (PCSX-Redux certified replays) to ensure behavior matches the original PS1.

**C↔Rust boundary:** The game C calls PS1 SDK functions (`GsSortObject4J`, `CdRead`, `PadRead`, etc.) implemented as `extern "C"` in Rust (`crates/psyq/`). If a mod needs a new SDK call, it must be added to `crates/psyq/` first.

**External references:** `psxrecomp` (`.psxmod` versioned mod system) and `DW2-PC` (PC architecture template) are consulted as inspiration for future mod tooling, but are not part of the codebase.

# LINUX_PORT_STATUS.md — Current status of the Linux port

This file is updated as progress is made. It serves as a unified checkpoint to know which phase the work is in and what remains pending.

---

## Current phase

**Phase 0 — Preparation** (in progress)

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
| 2 | `check_host_symbols()` conditionalized | ⬜ | |
| 2 | `xcrun` removed on Linux | ⬜ | |
| 2 | `decomp-c` compiles on Linux | ⬜ | |
| 3 | wgpu Metal → Vulkan/OpenGL | ⬜ | |
| 3 | Window opens on Linux | ⬜ | |
| 4 | XDG paths for saves/settings/reports | ⬜ | |
| 4 | `DW1_DATA_DIR` / `DW1_CONFIG_DIR` | ⬜ | |
| 5 | Linux crash handler (SIGSEGV/SIGBUS) | ⬜ | |
| 6 | `.desktop` file | ⬜ | |
| 6 | Install/uninstall scripts | ⬜ | |
| 7 | 43 certified replays pass on Linux | ⬜ | |
| 7 | Window, audio, controls, saves | ⬜ | |
| — | Edit C of `dw_decomp` for mod/correction | ⬜ | Main user goal |

---

## Immediate next steps

1. Start Phase 1: create `tools/build-linux.sh`.
2. Verify that a legal copy of the Digimon World disc is available for testing.
3. Read `dw1-silicon/docs/s06-platform.md` and `docs/s08-oracle.md` for context.

---

## Current blockers

None (project not yet started).

---

*End of LINUX_PORT_STATUS.md*
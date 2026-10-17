# dw1-silicon Linux Port

This directory contains the complete plan for porting dw1-silicon from macOS to Linux.

## Status

**Viability: HIGH** ✅

Estimated effort: **10-12 days** of focused work.

## Overview

dw1-silicon is well-architected for cross-platform porting:
- Game C from decompilation (standard ANSI C)
- PS1 libraries reimplemented in Rust (cross-platform)
- SDL3 for window/input/audio (cross-platform)
- wgpu for rendering (supports Metal, Vulkan, OpenGL)

The main work is replacing macOS-specific tools and paths with Linux equivalents.

## Documents

| Phase | Document | Status |
|-------|----------|--------|
| 0 | [00-overview.md](00-overview.md) | Viability assessment and roadmap |
| 1 | [01-build-system.md](01-build-system.md) | Replace macOS build tools |
| 2 | [02-c-compilation.md](02-compilation.md) | Compile game C on Linux |
| 3 | [03-rendering-backend.md](03-rendering-backend.md) | Switch Metal to Vulkan/OpenGL |
| 4 | [04-file-paths.md](04-file-paths.md) | Use XDG directories |
| 5 | [05-crash-handler.md](05-crash-handler.md) | Linux signal handling |
| 6 | [06-packaging.md](06-packaging.md) | Desktop integration |
| 7 | [07-testing.md](07-testing.md) | Verify with oracle tests |

## Quick Start

### Prerequisites

```bash
# Debian/Ubuntu
sudo apt install build-essential clang cmake python3-venv pkg-config libsdl3-dev libvulkan-dev

# Fedora/RHEL
sudo dnf install gcc cmake python3 pkg-config SDL3-devel vulkan-devel
```

### Build

```bash
git clone https://github.com/loafykitten/dw1-silicon.git
cd dw1-silicon
git submodule update --init decomp
git -C decomp submodule update --init external/psyq_headers
python3 -m venv .venv && .venv/bin/pip install pyyaml cmake
./tools/build-linux.sh
```

### Run

```bash
export DW1_DISC=/path/to/Digimon\ World\ \(USA\).cue
./target/release/dw1
```

## Progress Tracking

Use this checklist to track progress:

- [ ] Phase 0: Read and understand plan
- [ ] Phase 1: Build system (tools/build-linux.sh)
- [ ] Phase 2: C compilation (crates/decomp-c/build.rs)
- [ ] Phase 3: Rendering backend (crates/render/Cargo.toml)
- [ ] Phase 4: File paths (XDG directories)
- [ ] Phase 5: Crash handler (Linux signals)
- [ ] Phase 6: Packaging (.desktop, install script)
- [ ] Phase 7: Testing (oracle tests)

## Key Changes Summary

### Build System
- Remove xcrun, otool, codesign, sips, iconutil, plutil
- Add tools/build-linux.sh
- Keep tools/make-app.sh for macOS

### C Compilation
- Conditionalize xcrun usage with `#[cfg(target_os = "macos")]`
- Implement Linux host symbol checking
- Compiler flags work on both platforms

### Rendering
- Change wgpu from Metal to Vulkan/OpenGL
- Use conditional features for cross-platform support
- No rendering code changes needed

### File Paths
- Use XDG Base Directory Specification on Linux
- Saves: `~/.local/share/dw1-silicon/`
- Settings: `~/.config/dw1-silicon/`
- Reports: `~/.local/share/dw1-silicon/reports/`

### Crash Handler
- Implement Linux signal handler with libc sigaction
- Keep macOS handler unchanged
- Use backtrace for stack traces

### Packaging
- Create .desktop file
- Add install/uninstall scripts
- Handle icons for Linux desktop
- Optional: AppImage, Flatpak

### Testing
- Run all 43 certified replays
- Compare with macOS builds
- Test window mode, saves, audio, controls
- Verify performance

## Risks and Mitigations

| Risk | Mitigation |
|------|------------|
| C compiler differences | Use clang on both platforms |
| Vulkan driver issues | Have OpenGL fallback |
| Oracle timing differences | Use VBlank counting (platform-independent) |
| File system case sensitivity | Ensure consistent case in code |
| SDL3 version differences | Pin SDL3 version |

## Success Criteria

### Must Have
- [x] Builds on Linux
- [x] Runs headless replays correctly
- [x] Opens window and displays game
- [x] Saves work correctly
- [x] All 43 certified replays pass

### Should Have
- [x] .desktop file for desktop integration
- [x] Icon displays correctly
- [x] Crash traces work
- [x] Audio works

### Nice to Have
- [ ] Packages for major distros
- [ ] Flatpak support
- [ ] Documentation updated

## References

- [XDG Base Directory Specification](https://specifications.freedesktop.org/basedir-spec/basedir-spec-latest.html)
- [Desktop Entry Specification](https://specifications.freedesktop.org/desktop-entry-spec/desktop-entry-spec-latest.html)
- [wgpu Backends](https://github.com/gfx-rs/wgpu#supported-platforms)
- [SDL3 Documentation](https://wiki.libsdl.org/SDL3/)

## Notes

### Keeping macOS Compatibility

All changes use conditional compilation (`#[cfg(target_os = "...")]`) to
maintain macOS compatibility. The goal is to support BOTH platforms.

### Testing on Real Hardware

Test on multiple Linux distributions:
- Ubuntu/Debian
- Fedora/RHEL
- Arch Linux
- Other distros if possible

### Oracle Testing

The oracle (PCSX-Redux emulator) is the source of truth. All replays must
match exactly on Linux.

## Getting Help

If you encounter issues:
1. Check the specific phase document for debugging tips
2. Compare with macOS build behavior
3. Check AGENTS.md for architecture details
4. Check PLAN.md for project context

## Contributing

When making changes:
1. Follow the phase documents
2. Test after each phase
3. Commit after each completed phase
4. Update this README with progress
5. Document any deviations from the plan

## License

Same as dw1-silicon: MIT OR Apache-2.0

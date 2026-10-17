# dw1-silicon Linux Port - Overview

## Viability Assessment

**Overall Viability: HIGH** ✅

The project is well-architected for cross-platform porting:

### Strengths
- **Rust is cross-platform** - All new code (PS1 library reimplementation) is pure Rust
- **SDL3 is cross-platform** - Window/input/audio work natively on Linux
- **wgpu supports Vulkan/OpenGL** - Rendering backend can be switched easily
- **C code is standard** - Decomp uses standard ANSI C, no macOS-specific extensions
- **Standard dependencies** - clang, Python, CMake exist on Linux
- **Clean architecture** - Good abstractions between game C and Rust

### Challenges (Medium)
- Build system tools (xcrun, otool, codesign) - packaging layer only
- C compilation adjustments - flags and host symbol checking
- File path changes - to XDG standard
- Crash handler reimplementation - Linux signal handling
- Oracle testing on Linux - but oracle is already cross-platform

### Estimated Effort
- Phase 1 (Build system): 1-2 days
- Phase 2 (C compilation): 2-3 days
- Phase 3 (Rendering): 1 day
- Phase 4 (File paths): 1 day
- Phase 5 (Crash handler): 1 day
- Phase 6 (Packaging): 1 day
- Phase 7 (Testing): 2-3 days

**Total: ~10-12 days of focused work**

---

## Port Strategy

### Approach: Iterative, Test-Driven

Each phase:
1. Make minimal changes for that phase
2. Build and test immediately
3. Verify against oracle when applicable
4. Commit before moving to next phase

### Key Principles

1. **Maintain macOS compatibility** - Use conditional compilation (`#[cfg(target_os = "macos")]`)
2. **Test at each step** - Don't batch changes without verification
3. **Document decisions** - Keep AGENTS.md updated
4. **Oracle remains source of truth** - Port must match PS1 behavior exactly

---

## Roadmap

### Phase 0: Preparation ✅
- [x] Read and understand codebase
- [x] Document Mac-specific components
- [x] Create AGENTS.md
- [ ] Create this plan

### Phase 1: Build System
**Goal:** Build on Linux without macOS-specific tools
- Replace `tools/make-app.sh` with Linux build script
- Remove xcrun, otool, codesign dependencies
- Set up Linux build environment
- **Deliverable:** `cargo build --release` works on Linux

### Phase 2: C Compilation
**Goal:** Compile game C for Linux
- Replace xcrun in `crates/decomp-c/build.rs`
- Implement Linux `check_host_symbols()`
- Adjust compiler flags for Linux clang/gcc
- Test headless build
- **Deliverable:** `decomp-c` crate compiles on Linux

### Phase 3: Rendering Backend
**Goal:** Use Vulkan/OpenGL instead of Metal
- Change wgpu features in `crates/render/Cargo.toml`
- Update any Metal-specific code
- Test window rendering
- **Deliverable:** Window opens and displays correctly on Linux

### Phase 4: File Paths
**Goal:** Use XDG Base Directory Specification
- Update save directory to use XDG paths
- Update settings path
- Update reports path
- Update DuckStation card path
- **Deliverable:** Saves/settings work on Linux

### Phase 5: Crash Handler
**Goal:** Linux-compatible crash tracing
- Replace macOS signal handler with Linux version
- Use Linux ucontext offsets
- Test crash trace output
- **Deliverable:** Crashes produce useful stack traces on Linux

### Phase 6: Packaging
**Goal:** Linux desktop integration
- Create .desktop file
- Add icon handling
- Document installation
- **Deliverable:** Installable Linux package/binary

### Phase 7: Testing
**Goal:** Verify port correctness
- Run headless oracle tests
- Run window mode tests
- Compare with macOS builds
- Test save system
- Test audio
- **Deliverable:** All oracle tests pass on Linux

---

## Success Criteria

### Must Have
- [ ] Builds on Linux with `cargo build --release`
- [ ] Runs headless replays correctly
- [ ] Opens window and displays game
- [ ] Saves work correctly
- [ ] All 43 certified replays pass

### Should Have
- [ ] .desktop file for desktop integration
- [ ] Icon displays correctly
- [ ] Crash traces work
- [ ] Audio works

### Nice to Have
- [ ] Packages for major distros (deb, rpm, AppImage)
- [ ] Flatpak support
- [ ] Documentation updated for Linux

---

## Risks and Mitigations

### Risk 1: C compiler differences
**Mitigation:** Use clang on both macOS and Linux for consistency

### Risk 2: Vulkan driver issues
**Mitigation:** Have OpenGL fallback option

### Risk 3: Oracle timing differences
**Mitigation:** Oracle uses VBlank counting, should be platform-independent

### Risk 4: File system case sensitivity
**Mitigation:** Ensure all paths use consistent case in code

### Risk 5: SDL3 version differences
**Mitigation:** Pin SDL3 version in Cargo.toml

---

## Dependencies

### Required on Linux
- Rust (rustup)
- Python 3 with venv
- CMake
- Clang or GCC
- SDL3 development libraries
- Vulkan or OpenGL development libraries
- pkg-config

### Installation (Debian/Ubuntu)
```bash
sudo apt update
sudo apt install build-essential clang cmake python3-venv pkg-config
sudo apt install libsdl3-dev libvulkan-dev vulkan-tools
# Or for OpenGL:
sudo apt install libsdl3-dev libgl1-mesa-dev
```

### Installation (Fedora/RHEL)
```bash
sudo dnf install gcc cmake python3 pkg-config
sudo dnf install SDL3-devel vulkan-devel
# Or for OpenGL:
sudo dnf install SDL3-devel mesa-libGL-devel
```

---

## Notes

### Platform Detection in Rust
Use `#[cfg(target_os = "...")]` and `#[cfg(not(target_os = "..."))]`:

```rust
#[cfg(target_os = "macos")]
fn mac_specific() { /* ... */ }

#[cfg(not(target_os = "macos"))]
fn linux_specific() { /* ... */ }
```

### Platform Detection in C
Use `__linux__` macro:

```c
#ifdef __linux__
// Linux-specific code
#elif defined(__APPLE__)
// macOS-specific code
#endif
```

### Keeping macOS Compatibility
The goal is to support BOTH platforms, not replace macOS. Use conditional compilation extensively.

---

## Next Steps

1. Review all phase documents in this directory
2. Set up Linux development environment
3. Start with Phase 1 (Build System)
4. Update AGENTS.md as you progress
5. Commit after each completed phase

---

## References

- [XDG Base Directory Specification](https://specifications.freedesktop.org/basedir-spec/basedir-spec-latest.html)
- [Desktop Entry Specification](https://specifications.freedesktop.org/desktop-entry-spec/desktop-entry-spec-latest.html)
- [wgpu Backends](https://github.com/gfx-rs/wgpu#supported-platforms)
- [SDL3 Documentation](https://wiki.libsdl.org/SDL3/)

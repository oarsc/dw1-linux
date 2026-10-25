# Project overview

## What this project is

`dw1-linux` is a native Linux x86_64 port of the US PlayStation game *Digimon World*
(SLUS-01032), based on the matching `dw_decomp` project. It is not an emulator.

The game logic remains C from the decompilation. Rust implements the host application and the
PS1 libraries needed by the game, including graphics, audio, input, and platform services.
Linux is the supported host; the old macOS port was removed.

The Rust PS1 SDK implementations are based on public documentation and emulator observations;
SDK disassembly may be consulted to answer narrow behavior questions, but is not translated
routine by routine.

## Current shape

- SDL3 opens the window; wgpu renders through Vulkan.
- The Linux binary builds in Docker and runs through the first playable map.
- Saves, settings, and reports use XDG paths. Audio, controls, and save/load have been exercised.
- Widescreen is a new, opt-in feature and remains WIP; see its entry in the
  [changelog](CHANGELOG.md).
- Remaining Linux verification: run the certified replay suite against PCSX-Redux and exercise
  `tools/make-linux.sh --install`. These are verification tasks; the porting milestones are
  otherwise complete.

## Where code lives

- `decomp/src/` — decompiled game C, edited and rebuilt for this port.
- `crates/psyq/` — Rust reimplementations of PS1 library behavior.
- `crates/backend/` and `crates/render/` — GPU emulation/HD rendering and window presentation.
- `crates/dw1/` — application startup, settings, window, input, audio integration, and saves.
- `packaging/` and `tools/` — Linux packaging and development scripts.


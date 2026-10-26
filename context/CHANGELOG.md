# Changelog from the original `dw_decomp`

This is a curated record of the port's substantial changes relative to the PS1 decompilation.
It covers the native port, game-C compatibility fixes, and optional additions. It is organized
by subsystem rather than by commit. Current operational guidance lives in the topic pages linked
from [AGENTS.md](../AGENTS.md).

## Native Linux port

- Ported the host application to Linux x86_64. SDL3 provides the window, input, and audio
  integration; wgpu uses Vulkan. Removed the old macOS-only application bundle, Metal setup,
  and packaging.
- Added Docker-based builds for the native application, while retaining a separate container
  for the MIPS decomp build.
- Added Linux ELF overlay/linker handling and replaced Mach-O/platform assumptions with ELF and
  Linux equivalents. Added a Linux crash trace using signal handlers and libgcc backtraces.
- Moved settings, saves, reports, and DuckStation card discovery to Linux/XDG paths. Added a
  Linux `.desktop` entry, icon installation, and Linux splash wording.
- Added a widescreen fix for pausing/unpausing and for menus that were not polling input while
  paused.

## Native C compatibility (`DW1_NATIVE`)

- Added a native C header and build path that preserves PS1-width `long`, PS1 SDK structure
  layouts, pointer/address translation for fixed PS1 RAM, and the expected `NULL` and `main`
  behavior on a 64-bit Linux host.
- Replaced PS1/MIPS-only headers and GTE inline assembly with native interfaces backed by Rust.
  Added host `setjmp` support and native overlay reset/loading behavior.
- Added pointer-width-safe representations and checks for overlays, fixed-address game memory,
  TMD records, and data shared across adjacent PS1 memory regions.
- Corrected native-only pointer casts, `strlen` use, and the EFEDAT filename terminator. Added
  native guards for null entity slots and `clearMapDigimon` paths that are valid on the PS1 but
  unsafe with host pointers.
- Redirected game libc/BIOS calls to Rust implementations with PS1-compatible behavior.
- Preserved the MIPS build path when `DW1_NATIVE` is undefined; see [C flags](C_FLAGS.md)
  for the PS1 parity rule.

## Rust PS1 libraries and runtime

- Implemented the PS1 GPU/VRAM command path, ordering tables, draw/display environments, image
  transfers, CLUTs, fills, textured primitives, and 2D/3D sorting needed by the game.
- Implemented the GTE operations and libgs coordinate, lighting, view, sprite, and TMD model
  paths used by the US game.
- Added the CD/disc reader, deterministic clock/input/replay integration, memory-card support,
  audio/SPU playback, streamed XA audio, MDEC movie decoding, and save support.
- Added a canonical game-state format and PCSX-Redux replay/capture comparison tools to check
  native behavior against the original game.

## Game-C fixes found during native bring-up and play

- Matched the PS1 `DIV` results for division by zero and `INT32_MIN / -1`; applied the helper to
  scripted movement and healing particles to prevent host `SIGFPE` crashes.
- Fixed map tile streaming to check the tile actually being loaded. This avoids a native null
  image read when scrolling onto an empty map tile while preserving the retail branch.
- Fixed fish population division and texture loading, including native pointer-width handling.
- Fixed a missing/stray grey cell in the evolution chart, a techniques-grid open error, and a
  pause input issue.
- Fixed KAR's null-string handling in match and hint pages, FISH model alignment, and scripted
  battle loops that visited empty entity slots. Added the missing file-queue prototype and
  corrected several missing-return paths found while bringing overlays up natively.
- Added native guards for empty entity slots and malformed/out-of-range data encountered in
  battles, overlays, training, death/rebirth, tournaments, and ending sequences. Audits and
  sanitizer-driven fixes cover pointer truncation, record layouts, array bounds, alignment, and
  missing return values while retaining the PS1 branch.
- Fixed native map/model edge cases found in certified routes, including FISH model alignment,
  scripted battles with empty slots, and string handling in KAR hint pages.

## Script, map, and gameplay modding

- Added a readable SCN text assembler and extraction workflow for `DG.SCN` and `MAPHEAD.SCN`.
  SCN mods can replace script blocks, inject code before or after original logic, add or remove DG
  label blocks, and add or redirect MAPHEAD entries. `~CONTINUE` supports non-destructive hooks.
- Added compile-time SCN functions and constants, including quoted text/command arguments and
  nested parameter forwarding. These are expanded into ordinary SCN source before assembly; they
  add no runtime macro system to the game.
- Added JSON MAP mods for warp and NPC field edits, including NPC addition and removal. The build
  extracts only mod-targeted assets from the user's disc, applies the changes, and assembles the
  modified assets into the executable. See the [modding guide](MODDING.md).

## Optional presentation and tooling additions

- Added an HD rendering side path at render scales 2–8 while retaining the PS1 1x VRAM for game
  logic and oracle comparisons.
- Added no-wobble model positioning and full-colour HD shading/blending as opt-in/setting-based
  presentation features.
- Added F12 bug snapshots containing screenshots, canonical state, recent controller input,
  settings, save copies, and logs.
- Added configurable save slots and read-only import from DuckStation memory cards.
- Added an opt-in widescreen mode (F10): HD surfaces extend to 426×240; captured neighboring
  map tiles and widened draw paths fill the margins, with adjustments for fades, actors, HUD,
  pause dimming, and margin audio. Camera limits use the wide extent only while the runtime mode
  is enabled and a map is wide enough. Narrow maps and unsupported scenes can still show black
  margins; widescreen remains WIP. See the [settings guide](SETTINGS.md).

## Verification status

Historical macOS/native phase records document 43 certified replay recordings against PCSX-Redux.
The Linux build reaches the first map; Linux replay verification and testing the install script
remain open. A successful native build is not by itself proof of PS1 behavior equivalence; see
[current project status](PROJECT.md).

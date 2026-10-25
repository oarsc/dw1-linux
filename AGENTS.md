# Agent instructions

## Topic pages

- [Project overview and current status](context/PROJECT.md)
- [Build, run, and local game data](context/BUILD.md)
- [C build flags and PS1 parity](context/C_FLAGS.md)
- [Runtime picture settings and hotkeys](context/SETTINGS.md)
- [Workflow and repository safety](context/WORKFLOW.md)
- [Modding and script extraction](context/MODDING.md)
- [Changelog from the original decomp](context/CHANGELOG.md)
- [Canonical game-state format](context/CANONICAL_STATE.md)

Follow its BUILD, C_FLAGS, and WORKFLOW links for task-specific detail.

The root Cargo workspace builds the `dw1` executable. Game C is in `decomp/src/` and is compiled with generated bindings by `crates/decomp-c`; the Rust PS1 SDK and rendering code are mainly in `crates/psyq`, `crates/backend`, and `crates/render`.

## Build and tests

- Use the Docker image: `./tools/do` (no arguments) builds it; `./compile` builds `target/release/dw1`. `./tools/do <command>` runs inside the container. Rebuild the image after changing workspace members or dependencies so Cargo's prefetched registry is refreshed.
- Run tests with `./tools/do cargo test --workspace`, or focus with `./tools/do cargo test -p <crate> <filter>`. Tests needing a local disc, fixture, or oracle capture may be ignored; an ignored test is not validation against that data.
- If compilation reports missing Psy-Q headers, initialize the nested submodule: `git -C decomp submodule update --init external/psyq_headers`.
- Certified replays use `./tools/do tools/replay-check.sh [--debug] [NAME...]`; they need local data under `captures/oracle-runs/` and `captures/fixtures/`. The script replaces each selected `captures/native-runs/check-<name>/` output directory.

## Invariants

- In decomp C, `DW1_NATIVE` is for Linux/host compatibility and `DW1_PLUS` for added features. With both undefined, preserve the original PS1 expressions and control flow; consult [C_FLAGS.md](context/C_FLAGS.md). For a source-only invariance audit, follow [.agents/skills/ps1-binary-invariance/SKILL.md](.agents/skills/ps1-binary-invariance/SKILL.md).
- Workspace dev and release profiles use `panic = "abort"`; Rust panics must not unwind across the C FFI boundary.
- Never commit disc images, extracted game data, fixture saves, dumps, or captures. They are local-only and gitignored.

# dw1-linux — Linux Port of Digimon World (PS1)

## Project Summary

`dw1-silicon` is a native port (not an emulator) of *Digimon World* for
PlayStation 1 (USA version, SLUS-01032), built from the matching decompilation
project [`dw_decomp`](https://github.com/jype0/dw_decomp).

The game logic is in C (editable, from `dw_decomp`). Everything else — window,
graphics, audio, input, PS1 libraries — is in Rust.

This repository (`dw1-linux`) is a copy of `dw1-silicon` adapted to compile and
run natively on **Linux**, using Docker for build dependencies so the host
machine stays clean.

---

## Prerequisites (on the host)

You only need **Docker** installed and working. Everything else (Rust, clang,
SDL3, Vulkan, etc.) is installed inside the container.

---

## Step by step: compile and run

### 1. Clone the repository (if not done yet)

```bash
git clone --recurse-submodules https://github.com/loafykitten/dw1-silicon.git dw1-linux
cd dw1-linux
```

If you already have the directory, skip this step.

### 2. Initialize submodules

```bash
git submodule update --init decomp
git -C decomp submodule update --init external/psyq_headers
```

This downloads the `dw_decomp` code (the game decompilation) and its Psy-Q headers.

> **Note:** The second command initializes a nested submodule inside `decomp/`. If you skip it, the build will fail with "Psy-Q headers missing".

### 3. Place your game disc (legal copy required)

Place your own legal copy of *Digimon World* (USA) as a `.cue`/`.bin` pair in:

```
external/Digimon World (USA).cue
external/Digimon World (USA).bin
```

The `external/` directory is gitignored — game data is never committed.

### 4. Build the Docker image

From the project root:

```bash
./do
```

This builds and tags the image as `dw1-builder`. You only need to do this once
(or when the `Dockerfile` changes).

### 5. Compile the game for Linux

Make the build script executable, then run it inside the Docker container:

```bash
./do tools/build-linux.sh
```

This compiles the C from `dw_decomp` and all the Rust code, producing the
executable at `target/release/dw1`.

The first build may take several minutes (downloading and compiling Rust dependencies).

> Equivalent shortcut: `./do cargo build --release -p dw1`

### 6. Run the game

```bash
export DW1_DISC="./external/Digimon World (USA).cue"
./target/release/dw1
```

Or in one line:

```bash
DW1_DISC="./external/Digimon World (USA).cue" ./target/release/dw1
```

Inside a Docker container you also need `XDG_RUNTIME_DIR` set:

```bash
export XDG_RUNTIME_DIR=/tmp/runtime-root
mkdir -p /tmp/runtime-root
DW1_DISC="./external/Digimon World (USA).cue" ./target/release/dw1
```

> **Status:** The game builds, opens a Vulkan window, shows the title screen, skips the intro
> video, reaches the main menu, starts a new game, shows the Jijimon naming dialog, and loads
> the first map successfully. The `__DATA` segment limit crash on first map load has been fixed
> (uses `dl_iterate_phdr` for a precise ELF segment limit).
>
> **File locations (XDG Base Directory Specification):**
> - Saves: `$XDG_DATA_HOME/dw1-linux/saves/` (default `~/.local/share/dw1-linux/saves/`)
> - Settings: `$XDG_CONFIG_HOME/dw1-linux/settings.txt` (default `~/.config/dw1-linux/settings.txt`)
> - Reports: `$XDG_DATA_HOME/dw1-linux/reports/` (default `~/.local/share/dw1-linux/reports/`)
> - DuckStation cards: `~/.local/share/duckstation/memcards/Digimon World (USA)_1.mcd`
>
> `DW1_SAVE_DIR` overrides the save directory if set.

### 7. Enter the container to edit code (optional)

If you want to edit code and recompile without typing `./do` each time:

```bash
./do bash
```

Inside the container, the project is at `/dw1`:

```bash
cd /dw1
./tools/build-linux.sh
```

---

## Project structure (minimum)

```
dw1-linux/
├── do                  # Docker wrapper (build image / run commands)
├── Dockerfile          # Arch Linux image with build dependencies
├── decomp/             # Submodule: dw_decomp (game C source)
├── decomp/Dockerfile   # Ubuntu image with MIPS toolchain for dw_decomp
├── external/           # Gitignored: your legal .cue/.bin game disc
├── tools/
│   └── build-linux.sh  # Linux build script (run via ./do)
├── crates/             # Rust code (window, GPU, audio, PS1 SDK, etc.)
├── docs/linux-port/    # Detailed port plan (7 phases)
├── AGENTS.md           # Context for AI agents
├── LINUX_PORT_STATUS.md           # Phase progress checklist
└── LINUX_PORT_DECISIONS.md        # Design decisions made
```

---

## Useful commands

| Action | Command |
|---|---|
| Build Docker image | `./do` |
| Compile release | `./do tools/build-linux.sh` |
| Compile debug | `./do cargo build -p dw1` |
| Run the game | `DW1_DISC="./external/Digimon World (USA).cue" ./target/release/dw1` |
| Shell in container | `./do bash` |
| Check project status | `cat LINUX_PORT_STATUS.md` |

---

## Important notes

- **Personal use only.** Do not distribute executables, assets, or derived code.
- **Never commit game data** (`.bin`, `.cue`, BIOS, saves, captures). They are in `.gitignore` under `external/`, `disc/`, `dumps/`, `build/`, `captures/`, `ref/`.
- The game uses **Vulkan** by default on Linux. If you don't have Vulkan drivers,
  switch to OpenGL in `crates/render/Cargo.toml`.
- To edit the game logic, modify the C files in `decomp/src/` and recompile with
  `./do tools/build-linux.sh`.

---

## Port plan (7 phases)

The detailed plan is in `docs/linux-port/`:
1. Build system (Linux build script)
2. C compilation (remove xcrun, compile C on Linux)
3. Rendering backend (Metal → Vulkan/OpenGL)
4. File paths (XDG directories)
5. Crash handler (Linux signals)
6. Packaging (.desktop, install scripts)
7. Testing (PCSX-Redux oracle, 43 certified replays)

---

*End of README-linux.md*
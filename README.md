# dw1-linux — Linux Port of Digimon World (PS1)

## Project Summary

`dw1-linux` is a native port (not an emulator) of *Digimon World* for
PlayStation 1 (USA version, SLUS-01032), built from the matching decompilation
project [`dw_decomp`](https://github.com/jype0/dw_decomp).

The game logic is in C (editable, from `dw_decomp`). Everything else — window,
graphics, audio, input, PS1 libraries — is in Rust.

This repository (`dw1-linux`) is a fork of
[`dw1-silicon`](https://github.com/loafykitten/dw1-silicon), the original native
Apple Silicon macOS port. Here it is adapted to compile and run natively on
**Linux**, using Docker for build dependencies so the host machine stays clean.

---

## Prerequisites (on the host)

You only need **Docker** installed and working. Everything else (Rust, clang,
SDL3, Vulkan, etc.) is installed inside the container.

### Running outside Docker (optional)

The release binary (`target/release/dw1`) is **dynamically linked**, so if you
want to run it directly on your host instead of inside Docker, you need the
following runtime libraries installed:

| Category | Packages (Debian/Ubuntu) | Packages (Arch Linux) | For |
|----------|--------------------------|----------------------|-----|
| Graphics | `libsdl3-0`, `libvulkan1`, `mesa-vulkan-drivers` | `sdl3`, `vulkan-loader`, `mesa` | Window + rendering |
| X11 | `libx11-6`, `libxcursor1`, `libxrandr2`, `libxi6`, `libxinerama1`, `libxkbcommon0` | `libx11`, `libxcursor`, `libxrandr`, `libxi`, `libxinerama`, `libxkbcommon` | Window system |
| Audio | `libasound2`, `libpulse0` | `alsa-lib`, `libpulse` | Sound |
| X11 extensions | `libxss1`, `libxtst6` | `libxss`, `libxtst` | Screen, tests |

**Cross-distro compatibility:** The binary is compiled inside an Arch Linux
container. It runs on any x86_64 Linux distro as long as the host's `glibc` is
the same version or newer than Arch's. If your host has an older `glibc`
(e.g. Ubuntu 22.04 LTS), you may get a `GLIBC_2.xx not found` error. In that
case, either use Docker (recommended) or compile natively on your host.

To check whether all libraries resolve on your host:

```bash
ldd target/release/dw1
```

If any library shows `=> not found`, install it. If you see a `GLIBC_2.xx`
version error, compile natively instead.

```
Arch Linux:
sudo pacman -S sdl3 vulkan-loader mesa libx11 libxcursor libxrandr libxi libxinerama libxkbcommon alsa-lib libpulse libxss libxtst

Debian / Ubuntu:
sudo apt install libsdl3-0 libvulkan1 mesa-vulkan-drivers libx11-6 libxcursor1 libxrandr2 libxi6 libxinerama1 libxkbcommon0 libasound2 libpulse0 libxss1 libxtst6

Fedora:
sudo dnf install sdl3 vulkan-loader mesa-libGL libX11 libXcursor libXrandr libXi libXinerama libxkbcommon alsa-lib pulseaudio-libs libXScrnSaver libXtst
```

---

## Step by step: compile and run

### 1. Clone the repository with submodules

```bash
git clone --recurse-submodules https://github.com/oarsc/dw1-linux.git dw1-linux
cd dw1-linux
```

If you already cloned, you can initialize just the modules with
```bash
git submodule update --init
```

This downloads the `dw_decomp`'s Psy-Q headers.

### 2. Place your game disc (legal copy required)

Place your own legal copy of *Digimon World* (USA) as a `.cue`/`.bin` pair in:

```
disc/Digimon World (USA).cue
disc/Digimon World (USA).bin
```

The `disc/` directory is gitignored — game data is never committed.

### 3. Build the Docker image

From the project root:

```bash
./tools/do
```

This builds and tags the image as `dw1-builder`. You only need to do this once (or when the
`Dockerfile` changes). The image already contains the downloaded Rust crate registry (the
`Dockerfile` runs `cargo fetch` from the workspace manifests and `Cargo.lock`), so the first
build inside it does not have to download crates. Rebuild the image after adding a dependency
if you want it prefetched; otherwise cargo simply fetches the new crate on the next build.

### 4. Compile the game for Linux

Make the build script executable, then run it inside the Docker container with any of:

```bash
./compile
./tools/do tools/build-linux.sh
```

This compiles the C from `dw_decomp` and all the Rust code, producing the
executable at `target/release/dw1`.

Build artifacts stay in `target/` on the host, so incremental builds are fast.

<<<<<<< HEAD
=======
The crate registry is baked into the image itself (the `Dockerfile` runs `cargo fetch`), so
normal builds read it from there and download nothing: the container is disposable, but the
image it starts from already has everything. If you add a dependency and build without
rebuilding the image, cargo downloads it into the container's throwaway layer, so it would be
fetched again on the next run; rebuild the image (`./tools/do`) to make it part of the image.
For heavy dependency work you can also mount a named volume instead (see the comment in
`tools/do`).


>>>>>>> 9538bb7 (Assemble readable scene scripts at startup)
### 5. Run the game

You need your own legal copy of *Digimon World* (USA, SLUS-01032) as a `.cue`/`.bin` pair.
Place them in `disc/` (gitignored — game data is never committed):

```
disc/Digimon World (USA).cue
disc/Digimon World (USA).bin
```

Then run any of:

```bash
./run
./target/release/dw1
```

### 6. Package and install (optional)

`tools/make-linux.sh` builds the release binary and (with `--install`) installs it to your
system. It does **not** statically bundle libraries: the binary is dynamically linked, so the
host still needs SDL3 and Vulkan/OpenGL at run time (see above).

```bash
./tools/do tools/make-linux.sh --install
```

This installs:
- `dw1` binary to `/usr/local/bin/dw1`
- `.desktop` file to `/usr/local/share/applications/dw1.desktop`
- Icon to `/usr/local/share/icons/hicolor/1024x1024/apps/dw1.png`

You can then launch Digimon World from your desktop environment's application menu.

To install to a different prefix:

```bash
PREFIX=/opt/dw1 ./tools/do tools/make-linux.sh --install
```

### 7. Enter the container to edit code (optional)

If you want to edit code and recompile without typing `./do` each time:

```bash
./tools/do bash
```

Inside the container, the project is at `/dw1`:

```bash
cd /dw1
./tools/build-linux.sh
```

The shell runs as your own user (not `root`), so files you create there belong to you, but you
cannot install packages inside it; edit the `Dockerfile` and rebuild the image for that.

---

## Project structure (minimum)

```
dw1-linux/
├── Dockerfile          # Arch Linux image with build dependencies
├── decomp/             # Submodule: dw_decomp (game C source)
├── decomp/Dockerfile   # Ubuntu image with MIPS toolchain for dw_decomp
├── disc/               # Gitignored: your legal .cue/.bin game disc
├── tools/
│   ├── build-linux.sh  # Linux build script
│   ├── make-linux.sh   # Linux packaging script (build + --install)
│   ├── do              # Docker wrapper (build image / run commands)
│   └── dtb             # Distrobox wrapper (build container / run commands)
├── crates/             # Rust code (window, GPU, audio, PS1 SDK, etc.)
├── context/            # Project context, changelog, plan catalog, and detailed docs
├── compile             # Quick compilation of the code using Docker
├── run                 # Quick execution of the compiled game
└── AGENTS.md           # Agent instructions; links the maintained context pages
```

---

## Important notes

- **Personal use only.** Do not distribute executables, assets, or derived code.
- **Never commit game data** (`.bin`, `.cue`, BIOS, saves, captures). They are in `.gitignore` under `disc/`, `dumps/`, `build/`, `captures/`, `ref/`.
- The game uses **Vulkan** by default on Linux. If you don't have Vulkan drivers,
  switch to OpenGL in `crates/render/Cargo.toml`.

## Project context and history

Start at `AGENTS.md` for the project summary, build notes, C flag rules, settings,
canonical-state schema, and changelog.

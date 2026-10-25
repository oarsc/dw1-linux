# Build, run, and game data

## Main Linux build

The supported development environment is the root Docker image (`Dockerfile`, Arch Linux).
`tools/do` runs commands in that image; `./compile` builds the release executable at
`target/release/dw1`.

```sh
./tools/do                         # build the Docker image when needed
./compile                          # build the Linux game (using docker)
./run                              # run the game
```

The container includes Rust, the C compiler, SDL3, Vulkan, Python build tools, and binutils.
The output `target/` directory is shared with the host and should remain owned by the invoking
user. In a headless/containerized window run, configure `XDG_RUNTIME_DIR` for the session.
See the [README](../README.md) for host runtime packages and detailed setup.

## Disc and extracted files

Provide a legal US disc image as `disc/Digimon World (USA).cue` and its `.bin`. The `disc/`
directory is gitignored. Some disc-comparison and oracle workflows also need extracted files in
`decomp/disks/us`; see [README](../README.md) and the individual tool instructions.

Never put disc images, extracted assets, dumps, captures, or emulator fixtures in commits.

## Separate decomp build

The `decomp/Dockerfile` environment is for rebuilding the MIPS decompilation executable and
overlays. It is separate from the root Docker image used to build the native Linux application.

## Runtime paths

- Saves and reports: `$XDG_DATA_HOME/dw1-linux/` (default `~/.local/share/dw1-linux/`).
- Settings: `$XDG_CONFIG_HOME/dw1-linux/settings.txt` (default `~/.config/dw1-linux/settings.txt`).
- `DW1_SAVE_DIR` overrides the save directory.


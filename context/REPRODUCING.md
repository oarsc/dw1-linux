# Reproducing a run headless

The port takes recorded pad input from two places: a **certified replay** (a pad recording made in
PCSX-Redux, tracked in `oracle/replays/`, run by `tools/replay-check.sh`) and a **bug report**
(the `pad.txt` an F12 snapshot writes, replayed with `DW1_PAD_SCRIPT`). Both drive the headless
host in [`crates/dw1/src/headless.rs`](../crates/dw1/src/headless.rs) and run the same game C as
the window build. Neither is a save state: a replay pins every poll and detects divergence, a
report gives the last minute of input plus the save slots it was played from.

## Entering headless mode

`DW1_HEADLESS=1` runs without a window, or any one of `DW1_REPLAY`, `DW1_SHOTS`, `DW1_STOP_AT`,
`DW1_START_AT` or `DW1_MOVIE` implies it. `DW1_PAD_SCRIPT` alone does **not**: set
`DW1_HEADLESS=1` (or one of the others) with it.

A headless run reads the disc from `DW1_DISC`, else from the build-time repository path. A binary
built in the Docker image has `/dw1/disc/...` baked in, which doesn't exist on the host, so either
run it through `./tools/do` or set `DW1_DISC=/path/to/Digimon World (USA).cue`. `./run` sets it
for the window build; `./compile` builds `target/release/dw1`.

Output goes to `DW1_OUT`; the built-in default is the repository's `captures/native-runs/latest`
resolved at build time, so set it explicitly (or run through `./tools/do`) when using a binary
built in the image. A replay stops at its recorded final VBlank; a pad-script run does not stop by
itself, so give it `DW1_STOP_AT=<vblank>` (or `DW1_MOVIE`, which ends on its own). Screenshots are
native VBlanks: `DW1_SHOTS=first:last:step` writes `shot_<vblank>.png`, at the HD scale unless it
is 1 (`DW1_SCALE`), and `DW1_SHOTS_1X=1` also writes the 1x picture.

## Certified replays: `tools/replay-check.sh`

```sh
./tools/do tools/replay-check.sh                  # release build, every replay
./tools/do tools/replay-check.sh --debug NAME...  # debug build, named replays
```

The replay files are in `oracle/replays/<name>.txt` (pad states only, no game data). They are
recorded with `oracle/replay.lua` on PCSX-Redux: a header (`format`, game/disc/core hashes, the
route's initial card hashes or fixture, `final_vblank`, poll count) and one line per poll,
`seq vblank mask caller_ra`. The test's own card images and the emulator's canonical-state dumps
are local and gitignored:

- `captures/oracle-runs/<oracle-dump-dir>/` — the emulator's `ckpt_NNNN_*.bin/.txt` dumps;
- `captures/fixtures/<card>.mcd` — the memory cards the recording started from.

For each name in the script's table, `tools/replay-check.sh` builds the game (release unless
`--debug`), removes and recreates `captures/native-runs/check-<name>/`, and runs:

```sh
DW1_REPLAY=oracle/replays/<name>.txt
DW1_CARD1=captures/fixtures/<card>.mcd
DW1_CARD2=captures/fixtures/<card2>.mcd   # only for a two-card replay
DW1_OUT=captures/native-runs/check-<name>
target/release/dw1
```

then compares the checkpoints with `tools/oracle/compare_canon.py` (see
[CANONICAL_STATE.md](CANONICAL_STATE.md)). A replay that fails or differs exits non-zero and names
the log (`<out>/log.txt`). A replay with no oracle dumps or no card is printed as `SKIP` and does
not fail the run — **a green run where everything was skipped proves nothing**; check the lines.

Notes:

- The script unsets `DW1_CHECKPOINT_EVERY`: the oracle dumps were recorded at the default 600-poll
  interval, and a different interval inserts checkpoints, shifting the numbering the comparison
  pairs by. To find where a run diverges, run the binary yourself with
  `DW1_CHECKPOINT_EVERY=<polls>` and compare with
  `tools/oracle/compare_canon.py <native-dir> <oracle-dir> --allow-unpaired` (extra native
  checkpoints can then be left unpaired; the pairs that exist must still be identical).
- `DW1_CHECK_PREFIX=<prefix>` replaces the `check-` in the output directory, so parallel worktrees
  sharing `captures/` don't overwrite each other.
- `DW1_REPLAY_LOG=1` prints every poll with its recorded and native VBlank; it is the quickest way
  to see which poll first diverges.
- Replays are recorded with the cards they name: a replay refuses save slots, and a kept card in
  the save directory stops the run (`a replay starts from its recorded cards, but ... exists`).
  Use a scratch `DW1_SAVE_DIR` (or none) for replay runs.
- To certify a new route, add `name oracle-dump-dir card [card2]` to the `table` at the top of the
  script (`-` means a fresh card) and record the matching `oracle/replays/<name>.txt`. The replay
  and the script entries are committed; the dumps and cards are not.

## Bug reports: the `pad.txt` from F12

F12 writes a report to `$XDG_DATA_HOME/dw1-linux/reports/<UTC time>/` (default
`~/.local/share/dw1-linux/reports/`):

| File | Contents |
|---|---|
| `about.txt` | time, version, the VBlank of the snapshot, render settings |
| `screen.png`, `screen-hd.png` | the PS1 picture and the picture as shown (above scale 1) |
| `state.txt`, `state.bin` | the canonical state at the snapshot (same schema as a checkpoint) |
| `pad.txt` | the last 3,600 VBlanks (about a minute) of pad input |
| `settings.txt` | the picture settings |
| `saves/` | copies of the save slots (`slot-NN.dw1save`) |
| `log.txt` | what the app printed so far |

Reports hold game data (screenshots, saves, state). Ask the reporter for the folder, keep it
outside the repository, and never paste its contents into an issue or commit.

`pad.txt` is already in `DW1_PAD_SCRIPT` format: each non-comment line is
`<vblank> <mask in hex>`, and that mask is held from that native VBlank until the next line
(`0000` releases). Comments (`#`) and blank lines are ignored. The masks use the PS1 pad bits:
`8000` Left, `4000` Down, `2000` Right, `1000` Up, `0800` Start, `0100` Select, `0040` Cross,
`0020` Circle, `0080` Square, `0010` Triangle, `0008` R1, `0004` L1, `0002` R2, `0001` L2.

The report has the input's *tail*, not a starting state. Reproduce from a save the reporter had
near the bug (the report's `saves/` copies whatever slots existed when F12 was pressed, not the
moment itself), and copy the report before running: the game locks and writes its save directory.

```sh
./compile
cp -r ~/.local/share/dw1-linux/reports/<stamp> /tmp/report
mkdir -p captures/native-runs/report

DW1_DISC="$PWD/disc/Digimon World (USA).cue" \
DW1_HEADLESS=1 \
DW1_SAVE_DIR=/tmp/report \
DW1_SAVES=slots \
DW1_PAD_SCRIPT=/tmp/report/pad.txt \
DW1_CHECKPOINTS=1 \
DW1_SHOTS=2500:6000:100 \
DW1_STOP_AT=6000 \
DW1_OUT=captures/native-runs/report \
target/release/dw1
```

`DW1_SAVES=slots` is required: headless runs use the two emulator-style memory cards by default,
and a report's `saves/` are save slots. `DW1_SAVE_DIR=/tmp/report` makes the run read
`/tmp/report/saves/` and write there, so the original report stays intact. If the report has no
`saves/` (a fresh game), the same command still works with an empty directory.

That first run shows the boot and menu; to apply the report's input, shift it as below and pass
`DW1_PAD_SCRIPT=/tmp/report/pad-shifted.txt` instead.

### Aligning the input's VBlanks

`pad.txt` VBlanks are **absolute, counted from the reporter's `ResetCallback`**, exactly the clock
`DW1_PAD_SCRIPT` compares against. Loading the save puts the same game state at a much smaller
VBlank number, so the lines must usually be shifted by a constant, and a line shifted below 0 is
dropped. The window and headless hosts count the same clock, but while a menu polls `PadRead` the
window advances by wall time and headless advances a field after a burst of polls, so the shift is
approximate to a few fields. Each line holds its mask until the next one: use short holds (2–4
VBlanks) when writing menu input, because a longer hold can move a cursor more than once through
the game's repeat timer. The reporter's own `pad.txt` already has the right holds. Shift it with:

```sh
# SHIFT = the VBlank where the reproduction should start minus the first change's VBlank
SHIFT=-2500
awk -v d="$SHIFT" '
  /^[[:space:]]*#/ || NF < 2 { print; next }
  { v = $1 + d; if (v < 0) next; $1 = v; print }
' /tmp/report/pad.txt > /tmp/report/pad-shifted.txt
```

Use the shifted file as `DW1_PAD_SCRIPT`. Choose the shift so that the first change lands where the
reproduction has reached the state the reporter was in when the tail begins. After loading the
save, use `DW1_SHOTS` (or `DW1_CHECKPOINTS=1`, whose `screen<N>` checkpoints show screen changes)
to find the VBlank where the game has finished loading and shows that screen, then set
`SHIFT = that VBlank - the tail's first VBlank`. As a starting point in the current build, the
title accepts Start from about VBlank 1400 and the main menu appears about 1,000 VBlanks later;
`DW1_START_AT=<vblank>` holds Start and is a quicker way to reach it without writing the opening
lines. Treat these numbers as a starting point, not as contract: confirm with screenshots.

A report made without a save is only replayable from boot if the tail's first VBlank still finds
the game in the state the reporter was in; if the tail starts mid-gameplay, the earlier input
needed to get there was not recorded, so use the reporter's save or reproduce that part by hand.

### Checking the result

- Screenshots: `captures/native-runs/report/shot_<vblank>.png` (HD if the render scale is above 1;
  `DW1_SHOTS_1X=1` adds the 1x one). Use `DW1_SCALE=1` to compare pixels with `screen.png`.
- Checkpoints: with `DW1_CHECKPOINTS=1`, `ckpt_NNNN_<why>.txt` follows the same triggers as a
  replay (a MAIN_STATE, GAME_STATE or CURRENT_SCREEN change, every 600th poll, and `final` at
  `DW1_STOP_AT`). `DW1_CHECKPOINT_EVERY=<polls>` makes the periodic ones denser. Stale `ckpt_*`
  files in `DW1_OUT` are deleted at the start.
- Compare `ckpt_*_final.txt` with the report's `state.txt` (both are canonical records). Fields
  that depend on elapsed time (the clock, positions, RNG) only match when the shift made the run
  follow the report's timeline; screen, place, partner and progress fields are the useful ones.
- `DW1_CARD_DUMP=1` writes the run's cards as `card1.mcd`/`card2.mcd` next to the checkpoints.
- `DW1_HD_STATS=1` prints the HD drawing time of each field as
  `hdstat <vblank> <ns> <read_ns>`.

## Limits and gotchas

- A report cannot be turned into a replay by hand: a replay compares each poll's sequence and
  caller function, which `pad.txt` doesn't record. Use `DW1_PAD_SCRIPT` for reports.
- The report's pad log keeps at most a minute. If the input that caused the bug is older, the
  report is not enough; use the save the reporter points to and replay further.
- A replay run reads its recorded cards, not slots, and refuses a save directory that already
  holds cards. Keep report and replay runs in separate `DW1_SAVE_DIR` directories.
- A headless run does not read `settings.txt`; use `DW1_SCALE`, `DW1_PGXP`, `DW1_FULL_COLOUR` and
  `DW1_WIDE` (see [SETTINGS.md](SETTINGS.md)).
- `DW1_CRASH_TRACE=0` disables the crash handler that prints a native call stack (it is on by
  default).
- Never commit reports, cards, replay dumps or `captures/`; only the pad recordings under
  `oracle/replays/` are tracked.

## Environment quick reference

| Variable | Used by | Meaning |
|---|---|---|
| `DW1_HEADLESS=1` | binary | run without a window |
| `DW1_DISC=<cue>` | binary | disc image (headless has no disc picker) |
| `DW1_OUT=<dir>` | binary | checkpoints, screenshots and cards |
| `DW1_REPLAY=<file>` | binary | certified recording; implies headless |
| `DW1_PAD_SCRIPT=<file>` | binary | report input (headless only with another trigger) |
| `DW1_START_AT=<vblank>` | binary | hold Start from that VBlank (no replay) |
| `DW1_STOP_AT=<vblank>` | binary | stop and write `final` there |
| `DW1_SHOTS=<first:last:step>` | binary | screenshots at those VBlanks |
| `DW1_SHOTS_1X=1` | binary | also write the 1x screenshot above scale 1 |
| `DW1_SCALE=<1..8 or auto>` | binary | render scale for screenshots |
| `DW1_CHECKPOINTS=0/1` | binary | off, or on without a replay (a replay turns it on) |
| `DW1_CHECKPOINT_EVERY=<polls>` | binary | interval of `every<N>` checkpoints (default 600) |
| `DW1_REPLAY_LOG=1` | binary | log every recorded and native poll |
| `DW1_CARD_DUMP=1` | binary | write `card1.mcd`/`card2.mcd` with the checkpoints |
| `DW1_SAVE_DIR=<dir>` | binary | save directory to read and keep (slots or cards) |
| `DW1_SAVES=slots or cards` | binary | save backend (headless defaults to cards) |
| `DW1_CARD1=<mcd>`, `DW1_CARD2=<mcd>` | binary | initial cards when the backend is cards |
| `DW1_CHECK_PREFIX=<text>` | `tools/replay-check.sh` | output directory prefix (default `check-`) |

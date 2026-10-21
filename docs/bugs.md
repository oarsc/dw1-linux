# Bugs found in play (Phase 9)

Ember's playthrough (Phase 9.5, `docs/phase9-plan.md`). One entry per bug, newest first. When
something looks wrong, press **F12** in the game: a bug snapshot goes to
`~/Library/Application Support/dw1-silicon/reports/<time>/` (the screen, the game's state, the
last minute of input, the settings, copies of the save slots and the log). Say which snapshot,
and roughly what happened; the snapshot folders stay on the Mac (they hold game data and are
never committed).

For each bug:

- **What happened** and what should have happened (on the PS1 / DuckStation, if known).
- **Where:** place, day, what you were doing.
- **Snapshot:** `reports/<time>`; the save slot just before it, if there is one.
- **Status:** open / reproduced / fixed in `<commit>` / the original game does it too.

## Open

(none yet)

## Fixed

### The enemy's attack in Amida Forest killed the game with SIGFPE

- **What happened:** the enemy attacked in Amida Forest and the game died on the spot
  (`FPE`, call stack through `tickScriptedMovement` -> `tickMoveObjectTo`); the PS1 plays the
  same attack normally.
- **Where:** Amida Forest, during an enemy's attack.
- **Snapshot:** none; the crash came before one could be taken. The stack and the offsets are
  in the report that was sent.
- **Cause:** that attack's script runs `SCRIPT_OP_MOVE_OBJECT_TO` with a step count of 0, and
  `tickMoveObjectTo` (decomp `overworld.c`) divides by it. The R3000A's `DIV` doesn't trap:
  LO comes out as -1 for a non-negative dividend (1 for a negative one), and that sign points
  back at the target, so the clamps snap the object onto the target and finish the movement
  on the same tick. The host's `idiv` raised SIGFPE instead.
- **Fix:** `DW1_DIV` (`decomp/include/dw/types.h`) returns what the PS1's `DIV` returns,
  including the `INT32_MIN / -1` wrap. `tickMoveObjectTo`, `tickEntityMoveTo`,
  `tickEntityMoveToAxis` and the healing particles use it; the healing particles had a
  hand-written version of the same thing.
- **Status:** fixed

### The HD depth test made the 3D models flat-coloured (2026-10-21)

- **What happened:** with the depth test on (F6) and no wobble off, models were drawn with one
  texel of their texture instead of the texture itself (coloured silhouettes). A bug of the depth
  test below: the polygon now needed `1 / z`, and seeding the affine `u / v` interpolation was
  tied to `1 / z` *not* being needed, so every pixel sampled the texel at (0, 0).
- **Where:** in play, any scene with models.
- **Snapshot:** `reports/20261021-102956` (scale 5, wobble on, depth test on).
- **Status:** fixed on `feature/hd-depth-test`: the two are independent; a test draws a
  depth-tested smooth textured triangle and checks the texel at each end.

### A part of a model was drawn over the one in front of it (2026-10-21)

- **What happened:** above 1x render scale, part of a model showed through the part that lies in
  front of it. The PS1 draws it the same way: it has no depth buffer and sorts whole polygons by
  their average depth (`GsSortObject4J`), so a polygon behind another can be drawn after it. Not
  a port bug; the HD surfaces can do better.
- **Where:** in play, with the models in view.
- **Snapshot:** `reports/20261021-100145` (scale 3, wobble on).
- **Status:** fixed on `feature/hd-depth-test`: the HD surfaces test `1 / z` per pixel from the
  GTE's own view depths, behind a new `depth` setting (F6, `DW1_DEPTH`, on by default;
  `docs/phase8-plan.md` 8.7). The 1x picture, the saves and the replays are untouched. Polygons
  drawn as the 1x picture (2D and sprites) keep the PS1's order, a polygon without every corner
  projected this frame is drawn as before, and a hole painted into a texture is not separated.

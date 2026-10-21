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

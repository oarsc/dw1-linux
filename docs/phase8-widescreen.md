# Phase 8.6: widescreen feasibility (report)

2026-10-14, session 5. PLAN.md: "Widescreen is a feasibility milestone, not a promise". This is
the report; nothing is built. Evidence (file:line, every map's size from the disc's headers):
`docs/phase8-widescreen-survey.md` (gpt-6.1-sol, read-only; sampled against the code).

## Short answer

16:9 can be added faithfully for some scenes, never by just widening the picture, and the PS1
game must not notice. Best first: the 3D tournament and Battle Mode arenas. Ordinary maps work
in their middles but show black at their edges. Title screens, menus and movies should stay 4:3
(pillarboxed). Worth doing only scene by scene, after the rest of Phase 8.

## What 16:9 means here

At 240 lines, 16:9 is 426.67 PS1 pixels wide: 53.33 more on each side of the 320 the game
draws. The plan is DW2-PC's: the HD surfaces get those margins, the camera and every number the
game computes stay as they are, and only the HD side draws into the margins. The 1x VRAM, the
replays and the RNG must be identical with it on or off.

## What's in the way

- **Map backgrounds are pre-drawn 128x128 tiles.** 241 maps: 19 are 3 tiles wide (384 pixels,
  too narrow for 426 at any camera position), the rest 4 to 10 wide. The camera stops 320
  pixels from each map edge, so at the edges a 16:9 view has 53 pixels with no art at all
  (black, or pillarbox there).
- **The game keeps 4 tile columns in VRAM; 16:9 can need 5.** The HD side would have to draw the
  fifth itself, from the map's tile pixels captured when the map loads (the game's copy in RAM
  is overwritten by battles and sound loading). Possible without touching what the game writes.
- **"On screen" feeds the game.** The game's 320x240 visibility tests decide which NPCs join a
  battle (and so which random numbers are drawn), enemy AI charge modes (a `randomLimit` call),
  collisions that start scripts, the partner's off-screen catch-up, battle intro and exit
  timing, and effect targets. None of these may change. Extra actors in the margins would have
  to be drawn by the HD side from existing state, and they'd still vanish, teleport or stop at
  the original 4:3 edges, which 16:9 would make visible.
- **Full-screen effects are authored 320 wide:** fades, battle flashes, iris wipes, mist and
  snow, battle backdrops, the pause dim. Each needs its margins covered (without running the
  weather simulation more: snow uses the shared RNG).
- **Title screens and menus** are 320-wide pictures and layouts; **movies** are 320x176.
  Nothing more exists to show.

## Recommendation

1. Don't build widescreen now. Finish Phase 8 (HD fixes, Ember's look at scale and no wobble),
   then Phase 9's playthrough.
2. If Ember wants it later: start with the STD/VS arenas (real 3D stages, the margins fill
   naturally), then an allowlist of large maps with captured tiles, pillarboxing everything
   else and every unverified scene. Gate each scene on identical replays with it on.
3. Labelled an addition, off by default, with pillarbox as the fallback everywhere.

## 2026-10-21: first HD-margin prototype (F10)

The first step above is in: an HD-margin widescreen, labelled an addition and off by default.

- `settings.rs` has `widescreen` (F10, `DW1_WIDE=0/1`). It needs the HD surfaces, so it only
  acts at render scale 2x+ (`auto` keeps at least 2 while it is on; a fixed 1 leaves it off,
  and the corner note says so).
- `backend::hd` widens every HD surface by `WIDE_MARGIN = 53` VRAM pixels each side, draws the
  HD primitives at +53 and extends their horizontal clip to the whole surface, so the margins
  show what the game's 320-wide clip hid. The 1x VRAM, the game's calculations and the replays
  are untouched. A fill that spans the surface's whole VRAM width (the frame clear, a fade)
  clears the margins too, so nothing smears between frames.
- `render` has `Fit::WideInteger` and `Fit::Wide` for the 426x240 picture (426:240 is 16:9 to
  within 0.15%; it is not stretched). The window picks them from the picture's size, so a 4:3
  picture -- a movie, the splash, or render scale 1 -- stays 4:3 whatever the fit setting.
- Known to be unhandled, per the survey above: the 5th tile column, pre-culled actors at the
  edges, full-screen effects and the per-scene allowlist/pillarbox. Expect black or missing art
  at map edges; the arenas and the middles of the wider maps are the useful parts for now.

Checked with the `new-game` replay (headless, render scale 2, `DW1_WIDE=1` against `0`): the 75
1x screenshots and the 19 canonical-state checkpoints are byte-identical, each 852x480 HD
picture's centre 640x480 is identical to the 4:3 HD picture, and movie frames (which take the
1x fallback) stay 640x480. So the game and the 1x VRAM don't notice it, and the margins only
add pixels at the sides. In the window, `DW1_WINDOW_LOG=1` shows the display switching between
640x480 (4:3 scenes) and 852x480 (the margins) by itself.

## 2026-10-22: the 5th tile column and the pre-culled actors

The two things the prototype left black or missing at the picture's sides, fixed without changing
a single number the game computes. All of it is under `DW1_PLUS` (native build only, so the PS1
and the oracle replays run the vanilla game) and all of it reads `dw1_plus_margin()` at run time
(0 with the margins off or at render scale 1, `WIDE_MARGIN` = 53 with them on), so F10 turns the
whole thing on and off.

- **The extra map column.** The game keeps four 128x128 columns in VRAM and draws those, starting
  at `MAP_TILE_X`; normally the first one starts well left of the picture, but the camera brings
  the 4:3 edge past its right edge now and then (the column to its left is then the one the
  picture needs, and it was never cached). `setupMap` copies the map's tile pixels out of
  `GENERAL_BUFFER_PTR` (the game's copy is reused by battles and sound loading) and `renderMap`
  queues the column before `MAP_TILE_X` as a private `0xE7` packet at `ot[0xfff]`, at the
  position `setPosDataMapTile` gives the game's own tiles. `psyq::gpu::draw_chain` takes that
  opcode (the 1x picture and the command-boundary accounting never see it) and `Gpu::plus_tile`
  -> `Hd::native_rect` draws it on the HD surfaces only, texel by texel from RAM, through the live
  VRAM CLUT at (0, 480) so the day/night transition applies. `Hd::native_rect` drops it when it
  ends at or left of the 4:3 edge. Only the left column is ever needed: the four cached ones
  always cover the right margin.
  - The packet is five words, `tag, cmd, xy, wh, clut`, as plain `uint32_t`s: `P_TAG` is *eight*
    bytes (its second word is a real primitive's colour and code), so a `P_TAG tag;` field would
    shift the body by one word.
  - The position is a primitive's, not a screen coordinate: `Gpu::plus_tile` adds the GPU's
    drawing offset, exactly as `Gpu::rectangle` does for the game's own tiles.
- **Actors the game pre-culled.** The game's 320x240 tests decide what to draw and also feed the
  simulation (`isOnScreen`, battle joins, AI, scripts), so they are untouched. Instead the three
  draw-only tests retest against the widened picture: `renderDigimon` (only in the overworld --
  `GAME_STATE == 0`, not in a menu -- and only when the entity is off the 4:3 view but inside the
  widened one), `renderMapOverlays`' horizontal window, and `isBoxOffScreen`'s corner test
  (320 + 2 * margin). Nothing is added to the game's state, its flags, its RNG or the 1x VRAM.

Checked with the `new-game` replay (headless, render scale 2, `DW1_WIDE=1` against `0`, shots
every 1000 vblanks with the 1x copies): the 1x screenshots and every canonical-state checkpoint
are byte-identical, and each 852x480 picture's centre 640x480 is still identical to the 4:3 HD
picture (`max` pixel difference 0), so the additions are margin pixels and nothing else. With the
column disabled (the same build, the call removed) the left margin is black in the frames where it
is needed; with it, the art continues across the seam. Movie frames keep taking the 1x fallback
(640x480).

Still open, in the order they would show:

- **Full-screen effects** (fades, battle flashes, iris wipes, mist and snow, the pause dim) are
  320-wide pictures or quads: they leave the margins uncovered. Covering them means drawing their
  margins on the HD side without running their simulation more (snow uses the shared RNG).
- **Scenes that are 320 wide on purpose** (title screens, menus, movies, and every scene not
  checked yet) stay 4:3 and want the pillarbox the survey recommends per scene.
- **`isTileOffScreen` and the simulation-side windows** keep their ±200-pixel / 320-wide game
  meaning by design, so an actor that the game has stopped ticking (or that a script has not
  spawned) still appears or disappears at the 4:3 edge; only what the game draws was widened.

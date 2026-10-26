# Changes from the original game

This page lists selected player-visible differences from the original PS1 game. For the broader
technical history of the port, compatibility fixes, and additions, see the
[project changelog](CHANGELOG.md).

## Features

### Widescreen

F10 enables the optional 426×240 (about 16:9) HD picture. It can show more of wide maps using
neighboring map tiles and widened draw paths. Widescreen is off by default, requires a render scale
above 1, and remains a work in progress: unsupported scenes or narrow maps may have black margins.
Movies and other 4:3 pictures remain 4:3. See [picture settings](SETTINGS.md).

### Dialogue word spacing

The original game's textbox renderer advances a space by the previous glyph's width, so the word
gap follows the preceding letter: 16 px after `I` and 6 px after `.` or `,`. The native build
advances spaces by the usual 8 px letter width instead, which also removes the doubled gap after
wide letters. Fixed-width menus keep their 12 px cell. The PS1 build is unchanged.

## Mods

For information on creating and applying mods, see the [modding guide](MODDING.md).

### Koromon placement

`mods/move-koromon.maps.json` repositions NPC 0 in the Green Gym map (`TRAI00`) to
`(-100, 0, -3268)` and changes its rotation to `(0, -512, 0)`.

### Monochrome Shop rework

The mods in `mods/monochrome-shop/` rework the shop encounters for Goburimon, Gotsumon, Weedmon,
and Muchomon. For each encounter, players can keep the base price or try to charge 20% or 40% more.
The chance of making a sale depends on the customer and the markup; after failed negotiations, a
customer may leave. The scripts also update the shop dialogue and display the profit from each
sale and the running total.

`win-condition.scnmod` lowers the shop challenge's success target to 2,500 bits in profit. The
original game required 3,072 bits.

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

## Mods

### Koromon placement

`mods/move-koromon.maps.json` repositions NPC 0 in the Green Gym map (`TRAI00`) to
`(-100, 0, -3268)` and changes its rotation to `(0, -512, 0)`. See [modding](MODDING.md) for the MAP
field-mod format.

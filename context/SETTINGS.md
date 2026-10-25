# Picture settings and controls

Settings are saved at `$XDG_CONFIG_HOME/dw1-linux/settings.txt`, or
`~/.config/dw1-linux/settings.txt` when `XDG_CONFIG_HOME` is unset. Changes made in the game are
saved to this file. Boolean values accept `true`/`false`, `on`/`off`, or `1`/`0`.

## Hotkeys

| Key | Setting | Behavior |
|---|---|---|
| **F2** | `render_scale` | Cycles `auto → 1 → 2 → 3 → 4 → 6 → 8 → auto`. Auto selects a scale from the window size. |
| **F3** | `no_wobble` | Toggles precise HD model positions (PGXP-style). This is an addition and needs render scale above 1. |
| **F4** | `fit` | Toggles `integer` and `fill`. Integer uses whole multiples of the source picture; fill uses the largest matching 4:3 or widescreen picture that fits the window. |
| **F5** | `full_colour` | Toggles HD shading/blending without PS1 15-bit colour truncation and dithering. Addition; needs render scale above 1. |
| **F10** | `widescreen` | Toggles the 426×240 (about 16:9) HD picture. Addition; needs render scale above 1. In auto mode, widescreen keeps scale at least 2. |
| **F11** | `fullscreen` | Toggles fullscreen and windowed mode. |
| **Ctrl+Super+F** | `fullscreen` | Also toggles fullscreen. |
| **F12** | bug snapshot | Writes a report with screenshots, state, recent pad input, settings, save copies, and log under `$XDG_DATA_HOME/dw1-linux/reports/` (default `~/.local/share/dw1-linux/reports/`). |

No F1, F6, F7, F8, or F9 picture hotkeys are currently implemented.

## Settings file and environment overrides

```text
render_scale = auto
no_wobble = true
full_colour = true
widescreen = false
fit = integer
fullscreen = false
```

Defaults are `auto`, no wobble on, full colour on, widescreen off, integer fit, and windowed.
Movies and other 4:3 pictures remain 4:3 even while widescreen is enabled. With a fixed
`render_scale = 1`, HD-only additions including widescreen do not take effect.

Environment variables override the settings file for that run:

| Variable | Setting | Accepted values |
|---|---|---|
| `DW1_SCALE` | `render_scale` | `auto`, or `1` through `8` |
| `DW1_PGXP` | `no_wobble` | `0` / `1` |
| `DW1_FULL_COLOUR` | `full_colour` | `0` / `1` |
| `DW1_FIT` | `fit` | `integer` / `fill` |
| `DW1_WIDE` | `widescreen` | `0` / `1` |

There is no fullscreen environment override. Headless runs do not read the window settings file.
See [settings implementation](../crates/dw1/src/settings.rs) and the
[window hotkey handling](../crates/dw1/src/window.rs).


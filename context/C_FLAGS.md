# Decomp C build flags

`DW1_NATIVE` and `DW1_PLUS` have separate jobs. Treat the build with both undefined as the PS1
game's code path.

| Flag | Purpose | Typical use |
|---|---|---|
| `DW1_NATIVE` | Host adaptations needed to compile or run the decomp C on Linux x86_64: host ABI, pointer representation, and platform/library behavior. | Enabled for the native Linux port. |
| `DW1_PLUS` | New features that were not in the PS1 game, such as widescreen support. | Compiled into the native port; individual features may also have runtime toggles. It will enable `DW1_NATIVE` as this requires it. |

## PS1 parity rule

The PS1 build defines neither flag. Changes needed only by the Linux host belong under
`DW1_NATIVE`; additions belong under `DW1_PLUS`. Do not guard an added feature only with
`DW1_NATIVE`, because that mixes host compatibility with game extensions.

When neither flag is defined, retain the original expressions and control flow. The PS1 build
must generate code identical to the original decomp build. For example, if a `DW1_PLUS` camera
path calls a new helper, keep the original camera-bound calculations in the `#else` branch rather
than routing the PS1 path through the helper with a zero margin.

The flags are compile-time gates; they do not replace runtime settings. Widescreen is compiled
with `DW1_PLUS`, then F10 enables or disables it while the game runs. See the
[widescreen changelog entry](CHANGELOG.md#optional-presentation-and-tooling-additions) and
[settings guide](SETTINGS.md).



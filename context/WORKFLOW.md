# Workflow and repository safety

- Work on a feature branch; do not work directly on `main`.
- Check `git status` before committing.
- Never commit game disc data, extracted assets, dumps, captures, oracle runs, or fixture saves.
- Use `./tools/do` for the root Linux build environment and `decomp/Dockerfile` for MIPS
  decompilation builds.
- Preserve the `DW1_NATIVE` / `DW1_PLUS` distinction and the PS1 parity rule in
  [C_FLAGS.md](C_FLAGS.md).
- Implement PS1 SDK behavior from public documentation and emulator observation; do not translate
  SDK disassembly routine by routine.
- Keep feature toggles runtime-safe: disabling an optional feature should restore the expected
  base presentation/behavior.
- Do not assume a successful Linux build certifies behavior against the PS1. Linux replay and
  packaging verification gaps are summarized in [PROJECT.md](PROJECT.md).

Use the current project pages linked from [AGENTS.md](../AGENTS.md) for maintained guidance.

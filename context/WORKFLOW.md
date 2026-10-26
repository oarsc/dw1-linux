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
- Do not assume a successful Linux build certifies behavior against the PS1. Run the certified
  replays ([REPRODUCING.md](REPRODUCING.md)).

## Updating the vendored decomp

`decomp/` is vendored from `dw_decomp`; it is not a git submodule, and `git subtree` does not work
with it. To pull upstream changes while keeping local edits, use
[`tools/sync-decomp.sh`](../tools/sync-decomp.sh):

```sh
./tools/sync-decomp.sh                  # one commit per remote
./tools/sync-decomp.sh --single-commit  # fold every remote into one commit
./tools/sync-decomp.sh --continue       # finish after resolving conflicts
./tools/sync-decomp.sh --abort          # discard a conflicted merge
```

- Commit or stash local changes first; the script refuses a dirty worktree.
- Only the directories listed in `content=` in `decomp/module` are synced.
- If the upstream commit saved in `decomp/module` is missing from the clone, the script says so;
  fetch it or fix that file by hand rather than editing it preemptively.
- On conflicts: resolve the files, `git add` them, then run `--continue`. The merge leaves no
  `MERGE_HEAD`, so `git merge --continue` / `git merge --abort` do not apply.
- The resulting commit has a single parent, and the upstream author is credited with a
  `Co-authored-by:` trailer.
- Consider creating an alias and use `git update` instead:
  ```sh
  git config alias.update '!f() { ./tools/sync-decomp.sh "$@"; }; f'
  ```

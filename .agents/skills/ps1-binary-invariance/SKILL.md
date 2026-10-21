---
name: PS1 Binary Invariance
description: Review selected code changes and determine whether they alter the PS1 code path when DW1_NATIVE and DW1_PLUS are disabled.
---

# Review PS1 Code-Path Invariance

Review the change set specified by the caller and determine, by reading the changes and the resulting code, whether the PS1 path changes when `DW1_NATIVE` and `DW1_PLUS` are both disabled. This is a source-level review only: do not build, preprocess, run tests, or compare generated binaries/artifacts.

## 1. Establish Scope and Baseline

1. If the user supplies a diff, paths, or commit range, follow it exactly and record which tree is the candidate and which is the baseline.
2. Without an explicit scope, the candidate is the working tree and the baseline is `HEAD`; inspect `git diff HEAD` (this includes staged and unstaged changes).
3. Also inspect `git status --short`: `git diff HEAD` does not include untracked files. If relevant new files exist, read them and treat them as additions; do not silently omit them.
4. Do not switch branches, clean or restore user files, or modify files as part of the audit.
5. If the requested range does not identify an unambiguous baseline, ask for clarification before giving a verdict.

## 2. Review Changes Under `decomp/`

Inspect every hunk in every affected file under `decomp/`, along with enough surrounding context to resolve nested preprocessor directives.

Read every relevant hunk and enough surrounding source to understand the complete preprocessor structure and resulting code in both trees. Do not judge solely by whether added lines visibly appear inside an `#ifdef`: trace `#else`/`#elif`, enclosing conditions, macros, declarations, and changed call sites. Consider whether code outside a guard changes behavior or generated code even when a runtime value would make that behavior appear inert.

- Review C/C++ sources, headers, macros, assembly, linker/config/build files, and generated-code inputs as applicable.
- For each change, explain whether it is excluded when both flags are undefined, or whether it remains in the PS1 path and can change its behavior or generated code.
- Documentation-only and comment-only changes may be identified as non-executable; do not describe them as guarded.
- You may reason manually about the flag-disabled result. Do not invoke preprocessors or build tools as part of this skill; the determination must come from reading the diff and final source.

## 4. Report

Provide a concise report containing:

- exact scope and baseline;
- changed files under `decomp/` and per-hunk `DW1_NATIVE`/`DW1_PLUS` guard results;
- for every finding that may alter the flag-disabled PS1 path, the exact file path and candidate source line number(s); include the relevant baseline line number when helpful;
- a concise explanation of the resulting PS1 code path with both flags disabled;
- separate verdicts: **SOURCE REVIEW: PASS/FAIL** and **PS1 PATH UNCHANGED: YES/NO/UNCERTAIN**.

Use **SOURCE REVIEW: PASS** only when the inspected changes are excluded from the PS1 path with both flags disabled. If source context is insufficient to decide, report **UNCERTAIN** and state what is missing. For any reported error or potential PS1-path difference, cite exact source line numbers rather than only a file or function name. Never claim that builds or binaries were verified: they are outside this skill's scope.

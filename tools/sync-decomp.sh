#!/usr/bin/env bash
#
# sync-decomp.sh - Pull upstream changes into decomp/ and keep your local edits.
#
# Reads decomp/module (format: sync=<url>:<branch>:<saved_commit> plus a
# content=<dir1>,<dir2>,... line), fetches each remote, compares with the saved
# commit, and if there are new commits performs a real three-way merge that
# preserves your local changes inside decomp/.
#
# Why not `git subtree pull --squash`?
#   decomp/ was copied into this repo as a plain directory (see commit
#   "chore: add dw_decomp to this repo"), it was never imported with
#   `git subtree add`. git-subtree needs the `git-subtree-dir:` marker that
#   `add` leaves in history and otherwise dies with:
#       fatal: can't squash-merge: 'decomp' was never added.
#   Instead we rebuild the merge ourselves, using the saved upstream commit
#   from decomp/module as the merge base:
#
#       base   = saved upstream commit, re-rooted at decomp/
#       theirs = new upstream commit,   re-rooted at decomp/
#       ours   = HEAD
#
#   Only the directories listed in `content=` are synced, so upstream files
#   that were never copied in (Dockerfile, Makefile, .github, ...) stay out.
#
#   Each upstream is fetched through a temporary remote, which is removed again
#   when the script exits (also on errors and interruptions), so `git remote -v`
#   stays as you had it.
#
# About HEAD and conflicts:
#   HEAD never moves during the sync: "ours" is always your current code, and
#   the upstream commit is never added as a parent. The merge is done with
#   `git merge-recursive` (plumbing), which leaves unmerged entries in the
#   index and conflict markers in the files but creates no MERGE_HEAD, so
#   `git merge --continue` / `git merge --abort` do NOT apply: use
#   `--continue` / `--abort` below (or plain `git add` + `git commit`).
#   The finished commit has a single parent (your previous HEAD); the upstream
#   SHAs live only in decomp/module.
#
# Authorship:
#   The commit is authored by you, and the author of the upstream commit being
#   pulled is credited with a `Co-authored-by:` trailer, with the name and email
#   of that commit itself (nothing is hardcoded, no contributor list). A
#   per-remote commit has one such trailer; a --single-commit batch has one per
#   imported remote head (read back from the heads saved in the state file).
#
# Usage:
#   ./tools/sync-decomp.sh                  # one commit per remote (merge + reference)
#   ./tools/sync-decomp.sh --single-commit  # fold every remote into one commit
#   ./tools/sync-decomp.sh --continue       # finish after resolving conflicts
#   ./tools/sync-decomp.sh --abort          # discard a conflicted merge
#
# Exit status: 0 = done, 1 = error or conflicts left to resolve.
#
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_DIR"

MODULES_FILE="decomp/module"
PREFIX="decomp"
GIT_DIR_ABS="$(git rev-parse --absolute-git-dir)"
STATE_FILE="$GIT_DIR_ABS/sync-decomp.pending"

SINGLE=0          # 1 = fold all upstreams into a single commit
CHAIN=""          # single mode: commit standing in for the current index state
CONTENT_DIRS=""
SYNC_URL=""
SYNC_BRANCH=""
SYNC_SAVED=""
SYNC_HEAD=""
REF_UPDATES=()    # single mode: "url|branch|head" merged so far
CREATED_REMOTES=() # remotes added by this run, removed again on exit
CLEAN_CHECKED=0

die() { echo "Error: $*" >&2; exit 1; }
note() { echo "   $*"; }

# The remotes are only a way to fetch: drop the ones added by this run so
# `git remote -v` looks exactly as it did before, also when it fails or is
# interrupted. Remotes that already existed are left alone.
cleanup_remotes() {
    local remote
    for remote in ${CREATED_REMOTES[@]+"${CREATED_REMOTES[@]}"}; do
        git remote remove "$remote" 2>/dev/null || true
    done
}
trap cleanup_remotes EXIT

# ---------------------------------------------------------------------------
# Authorship
# ---------------------------------------------------------------------------
# The sync commit is authored by you; the author of the upstream commit being
# pulled is credited with a Co-authored-by trailer: one per commit (a per-remote
# commit has one; a --single-commit batch has one per imported remote head).
author_trailer() {
    local who
    who="$(git log -1 --format='%aN <%aE>' "$1" 2>/dev/null)"
    [[ -n "$who" ]] && printf 'Co-authored-by: %s\n' "$who"
}

# <message> plus one trailer per revision (duplicates dropped), after a blank line.
with_author_trailers() {
    local msg="$1" rev trailer t sep=$'\n\n'
    local -a trailers=()

    shift
    for rev in "$@"; do
        trailer="$(author_trailer "$rev")"
        [[ -n "$trailer" ]] || continue
        for t in ${trailers[@]+"${trailers[@]}"}; do
            [[ "$t" == "$trailer" ]] && continue 2
        done
        trailers+=("$trailer")
    done
    for t in ${trailers[@]+"${trailers[@]}"}; do
        msg+="${sep}${t}"
        sep=$'\n'
    done
    printf '%s\n' "$msg"
}

# https://github.com/jype0/dw_decomp(.git)  -> jype0/dw_decomp
# git@github.com:jype0/dw_decomp(.git)      -> jype0/dw_decomp
# https://gitlab.com/group/sub/repo(.git)   -> group/sub/repo
short_name() {
    local u="${1%.git}"
    u="${u#*://}"   # strip scheme (https://, ssh://, file://)
    u="${u#git@}"   # strip git@ (scp-like syntax)
    u="${u/:/\/}"   # github.com:owner -> github.com/owner
    case "$u" in
        */*) printf '%s\n' "${u#*/}" ;; # drop the host
        *) printf '%s\n' "$u" ;;
    esac
}

[[ -f "$MODULES_FILE" ]] || die "$MODULES_FILE not found"

# ---------------------------------------------------------------------------
# State file: remembers the sync in progress across invocations
# ---------------------------------------------------------------------------
write_state() {
    local e
    {
        echo "SINGLE=$SINGLE"
        echo "CHAIN=$(printf '%q' "$CHAIN")"
        echo "CONTENT_DIRS=$(printf '%q' "$CONTENT_DIRS")"
        echo "SYNC_URL=$(printf '%q' "$SYNC_URL")"
        echo "SYNC_BRANCH=$(printf '%q' "$SYNC_BRANCH")"
        echo "SYNC_SAVED=$(printf '%q' "$SYNC_SAVED")"
        echo "SYNC_HEAD=$(printf '%q' "$SYNC_HEAD")"
        echo "REF_UPDATES=()"
        for e in ${REF_UPDATES[@]+"${REF_UPDATES[@]}"}; do
            printf 'REF_UPDATES+=(%q)\n' "$e"
        done
    } > "$STATE_FILE"
}

load_state() {
    [[ -f "$STATE_FILE" ]] || die "no sync in progress (nothing to continue/abort)"
    # shellcheck disable=SC1090
    . "$STATE_FILE"
    CLEAN_CHECKED=1 # the merge is already in the index
}

clear_state() {
    rm -f "$STATE_FILE"
    git update-ref -d AUTO_MERGE >/dev/null 2>&1 || true
}

# ---------------------------------------------------------------------------
# Build a commit whose tree is <rev> re-rooted at decomp/.
# Restricted to $CONTENT_DIRS so that only the vendored directories are synced.
# The commit has no parents: it is only used as a merge input.
# ---------------------------------------------------------------------------
snapshot_commit() {
    local rev="$1" msg="$2"
    local idx tree d
    idx="$(mktemp "${TMPDIR:-/tmp}/dw1-sync-index.XXXXXX")"
    rm -f "$idx" # git wants a non-existent index file

    GIT_INDEX_FILE="$idx" git read-tree --empty
    if [[ -n "$CONTENT_DIRS" ]]; then
        for d in $CONTENT_DIRS; do
            if git cat-file -e "${rev}:${d}" 2>/dev/null; then
                GIT_INDEX_FILE="$idx" git read-tree --prefix="${PREFIX}/${d}/" "${rev}:${d}"
            fi
        done
    else
        note "warning: no content= line, syncing the whole upstream tree"
        GIT_INDEX_FILE="$idx" git read-tree --prefix="${PREFIX}/" "$rev"
    fi

    tree="$(GIT_INDEX_FILE="$idx" git write-tree)"
    rm -f "$idx"
    git commit-tree "$tree" -m "$msg"
}

# ---------------------------------------------------------------------------
# decomp/module bookkeeping
# ---------------------------------------------------------------------------
update_reference_line() {
    local url="$1" branch="$2" head="$3" expected repl
    expected="sync=${url}:${branch}:${head}"
    repl="${expected//&/\\&}"
    sed -i "s|^sync=${url}:${branch}:.*\$|${repl}|" "$MODULES_FILE"
    grep -qxF "$expected" "$MODULES_FILE" ||
        die "could not update '$expected' in $MODULES_FILE (edit it by hand)"
}

# ---------------------------------------------------------------------------
# Finishing: per-remote commit (default) or one batch commit (--single-commit)
# ---------------------------------------------------------------------------
require_no_conflicts() {
    if git ls-files -u | grep -q .; then
        echo "Error: unresolved conflicts remain:" >&2
        git diff --name-only --diff-filter=U | sed 's/^/   /' >&2
        echo "Resolve them, 'git add' the files, then run: tools/sync-decomp.sh --continue" >&2
        exit 1
    fi
}

finalize_one() {
    require_no_conflicts
    update_reference_line "$SYNC_URL" "$SYNC_BRANCH" "$SYNC_HEAD"
    git add "$MODULES_FILE"
    if git diff --cached --quiet; then
        note "nothing changed inside the synced directories."
    else
        git commit -q -m "$(with_author_trailers \
            "sync(decomp): sync $(short_name "$SYNC_URL")@${SYNC_HEAD:0:7}" \
            "$SYNC_HEAD")"
    fi
    clear_state
    echo "   updated to $SYNC_HEAD"
}

finalize_batch() {
    require_no_conflicts
    local e url branch head msg sep
    local -a heads=()
    msg="sync(decomp): update upstream references"
    sep=$'\n\n'
    for e in ${REF_UPDATES[@]+"${REF_UPDATES[@]}"}; do
        url="${e%%|*}"
        branch="${e#*|}"
        head="${branch##*|}"
        branch="${branch%%|*}"
        update_reference_line "$url" "$branch" "$head"
        msg+="${sep}- $(short_name "$url")@${head}"
        sep=$'\n'
        heads+=("$head")
    done

    git add "$MODULES_FILE"
    if git diff --cached --quiet; then
        note "nothing changed inside the synced directories."
    else
        git commit -q -m "$(with_author_trailers "$msg" \
            ${heads[@]+"${heads[@]}"})"
    fi
    clear_state
    for e in ${REF_UPDATES[@]+"${REF_UPDATES[@]}"}; do
        echo "   updated to ${e##*|}"
    done
}

require_clean_worktree() {
    [[ $CLEAN_CHECKED -eq 1 ]] && return 0
    if ! git diff --quiet || ! git diff --cached --quiet; then
        die "you have uncommitted changes; commit or stash them first"
    fi
    CLEAN_CHECKED=1
}

# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------
cmd_continue() {
    load_state
    echo "==> resuming sync of ${SYNC_URL} (${SYNC_BRANCH})"
    if [[ $SINGLE -eq 1 ]]; then
        REF_UPDATES+=("${SYNC_URL}|${SYNC_BRANCH}|${SYNC_HEAD}")
        finalize_batch
    else
        finalize_one
    fi
}

cmd_abort() {
    load_state
    echo "==> discarding merge of ${SYNC_URL} (${SYNC_BRANCH})"
    git reset -q --hard HEAD
    clear_state
    echo "   done (decomp/module untouched)"
}

usage() {
    cat <<'EOF'
Usage:
  tools/sync-decomp.sh                  one commit per remote (merge + reference)
  tools/sync-decomp.sh --single-commit  fold every remote into one commit
  tools/sync-decomp.sh --continue       finish after resolving conflicts
  tools/sync-decomp.sh --abort          discard a conflicted merge
EOF
}

# ---------------------------------------------------------------------------
# Read decomp/module: content= first (snapshot_commit needs it)
# ---------------------------------------------------------------------------
while IFS= read -r line || [[ -n "$line" ]]; do
    [[ -z "$line" || "$line" == \#* ]] && continue
    if [[ "${line%%=*}" == "content" ]]; then
        CONTENT_DIRS="${line#*=}"
        CONTENT_DIRS="${CONTENT_DIRS//,/ }"
    fi
done < "$MODULES_FILE"

# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
ACTION="run"
while [[ $# -gt 0 ]]; do
    case "$1" in
        --single-commit) SINGLE=1 ;;
        --continue) ACTION="continue" ;;
        --abort) ACTION="abort" ;;
        -h | --help)
            usage
            exit 0
            ;;
        *) die "unknown option '$1' (see --help)" ;;
    esac
    shift
done

case "$ACTION" in
    continue)
        cmd_continue
        exit 0
        ;;
    abort)
        cmd_abort
        exit 0
        ;;
esac

if [[ -f "$STATE_FILE" ]]; then
    die "a sync is in progress; run --continue (or --abort) first"
fi

# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------
synced_dirs=""
had_updates=0

while IFS= read -r line || [[ -n "$line" ]]; do
    # Skip blank lines and comments
    [[ -z "$line" || "$line" == \#* ]] && continue

    # Split on FIRST '=' only (URLs contain ':' so we cannot split on ':')
    key="${line%%=*}"
    value="${line#*=}"

    case "$key" in
        sync)
            # value: <url>:<branch>:<saved_commit>
            # Split from the end backwards so ':' inside URLs (https://, git@) don't break it.
            SYNC_SAVED="${value##*:}"           # after the last ':'
            rest="${value%:*}"                  # everything except the last ':saved'
            SYNC_BRANCH="${rest##*:}"           # after the second-to-last ':'
            SYNC_URL="${rest%:*}"               # everything before the second-to-last ':'

            # Derive a local remote name from the URL
            remote="decomp-upstream-$(echo "$SYNC_URL" \
                | sed 's|.*://||; s|git@||; s|:|-|; s|\.git$||; s|/|-|g')"

            echo "==> $remote ($SYNC_BRANCH)"

            # Add the remote if it does not exist yet (removed on exit)
            if ! git remote get-url "$remote" >/dev/null 2>&1; then
                git remote add "$remote" "$SYNC_URL"
                CREATED_REMOTES+=("$remote")
            fi

            git fetch "$remote" "$SYNC_BRANCH" --quiet
            SYNC_HEAD="$(git rev-parse "$remote/$SYNC_BRANCH")"

            # The saved commit is the merge base, so it must exist locally.
            # Resolve it to a full sha: decomp/module could hold a short one.
            if ! git cat-file -e "${SYNC_SAVED}^{commit}" 2>/dev/null; then
                note "saved commit missing locally, trying to fetch it..."
                git fetch "$remote" "$SYNC_SAVED" --quiet 2>/dev/null || true
            fi
            if ! git cat-file -e "${SYNC_SAVED}^{commit}" 2>/dev/null; then
                die "commit $SYNC_SAVED (from decomp/module) is not in this clone.
       Fetch it from $SYNC_URL ($SYNC_BRANCH) or fix decomp/module by hand."
            fi
            SYNC_SAVED="$(git rev-parse "${SYNC_SAVED}^{commit}")"

            echo "   saved : $SYNC_SAVED"
            echo "   remote: $SYNC_HEAD"

            if [[ "$SYNC_SAVED" == "$SYNC_HEAD" ]]; then
                echo "   already up to date."
                continue
            fi

            require_clean_worktree
            had_updates=1

            base_commit="$(snapshot_commit "$SYNC_SAVED" \
                "dw1-sync: upstream ${SYNC_URL}@${SYNC_SAVED}")"
            theirs_commit="$(snapshot_commit "$SYNC_HEAD" \
                "dw1-sync: upstream ${SYNC_URL}@${SYNC_HEAD}")"

            if git diff --quiet "$base_commit" "$theirs_commit" -- "$PREFIX"; then
                note "upstream only touched files outside [$CONTENT_DIRS]."
                write_state
                if [[ $SINGLE -eq 1 ]]; then
                    REF_UPDATES+=("${SYNC_URL}|${SYNC_BRANCH}|${SYNC_HEAD}")
                else
                    finalize_one
                fi
                continue
            fi

            echo "   new commits found. Running three-way merge..."
            write_state

            ours="${CHAIN:-HEAD}"
            if git merge-recursive "$base_commit" -- "$ours" "$theirs_commit"; then
                if [[ $SINGLE -eq 1 ]]; then
                    CHAIN="$(git commit-tree "$(git write-tree)" -p "$ours" \
                        -m "dw1-sync: batch after ${SYNC_URL}@${SYNC_HEAD}")"
                    REF_UPDATES+=("${SYNC_URL}|${SYNC_BRANCH}|${SYNC_HEAD}")
                    note "merged into the pending batch."
                else
                    finalize_one
                fi
            else
                echo
                echo "Conflicts (your local edits touch the same lines upstream changed):"
                git diff --name-only --diff-filter=U | sed 's/^/   /'
                echo
                echo "Resolve them, then:"
                echo "   git add <files> && tools/sync-decomp.sh --continue"
                echo "Note: this merge is not a git merge state (no MERGE_HEAD), so"
                echo "      'git merge --continue' does not apply."
                echo "To throw the merge away:"
                echo "   tools/sync-decomp.sh --abort"
                exit 1
            fi
            ;;

        content)
            synced_dirs="$value"
            ;;

        *)
            echo "   unknown key '$key', skipping"
            ;;
    esac
done < "$MODULES_FILE"

if [[ $SINGLE -eq 1 && $had_updates -eq 1 ]]; then
    finalize_batch
fi

if [[ -n "$synced_dirs" ]]; then
    echo "----------------------------------------"
    echo "Synced directories from decomp/module:"
    echo "   $synced_dirs"
    echo "----------------------------------------"
fi

echo "Done."

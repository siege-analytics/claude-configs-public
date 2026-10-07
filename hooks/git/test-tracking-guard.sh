#!/bin/bash
# Hook: test-tracking-guard
# Enforces: _writing-tests-rules.md (test files must be git-tracked, not silently ignored)
# Trigger: PreToolUse on Bash(git push *), Bash(gh pr create *), Bash(gh pr merge *),
#          Bash(glab mr create *), Bash(glab mr merge *)
#
# Rejects pushes/PR-creates/PR-merges when a test file under a tests/
# directory (basename test_*.py) is present on disk but silently
# git-ignored: untracked AND matched by a .gitignore rule. The canonical
# cause is a user-level ~/.gitignore `test_*.py` pattern that masks every
# tests/test_*.py from `git status` and `git add` without warning, so
# local pytest passes while the test never lands in git history.
#
# Scope is a tests/ path component only, so deliberately-ignored scratch
# files elsewhere (test_scratch.py, test_old.py in working dirs) are not
# flagged. Tracked files matching the pattern are never reported by
# `git ls-files --others --ignored` (verified), so there is no false
# positive on properly-tracked tests. A push with no silently-dropped
# test files is a warning-free exit 0.
#
# Remedy printed on rejection: add `!tests/test_*.py` to the repo
# .gitignore to override the global rule for that repo.
#
# Override: [test-track-skip: Reason: ...; Evidence: ...; Falsification: ...]
# in the latest commit message. The bare form is rejected (mirrors
# test-guard.sh / #579).
#
# Ref: claude-configs-public#931

set -uo pipefail
export PATH="/home/craftagents/bin:$PATH"

INPUT=$(cat)
HOOK_DIR="$(cd "$(dirname "$0")" && pwd)"
EXTRACT="$HOOK_DIR/../lib/extract-json.py"
COMMAND=$(printf '%s' "$INPUT" | python3 "$EXTRACT" tool_input.command 2>/dev/null || true)
CWD=$(printf '%s' "$INPUT" | python3 "$EXTRACT" cwd 2>/dev/null || true)

# Native git hook path: when called from .githooks/pre-push, stdin is the
# ref list (not PreToolUse JSON). Detect and set COMMAND/CWD so the rest
# of the hook works unchanged. Mirrors test-guard.sh (#411).
if [[ -z "$COMMAND" ]]; then
    if git rev-parse --git-dir >/dev/null 2>&1; then
        COMMAND="git push"
        CWD="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
    else
        exit 0
    fi
fi

# Trigger on git push, gh pr create / merge, or glab mr create / merge.
# Word boundaries via portable character-class form (not BSD-incompatible
# \b); mirrors self-review.sh / test-guard.sh (CCP#201 pattern).
TRIGGERS='(^|[^[:alnum:]])(git[[:space:]]+push|gh[[:space:]]+pr[[:space:]]+(create|merge)|glab[[:space:]]+mr[[:space:]]+(create|merge))([^[:alnum:]]|$)'
if ! echo "$COMMAND" | grep -qE "$TRIGGERS"; then
    exit 0
fi

# Multi-statement-with-cd yield (mirrors branch-guard.sh / test-guard.sh, #101).
CD_COUNT=$(echo "$COMMAND" | { grep -oE '(^|[^[:alnum:]])cd[[:space:]]' 2>/dev/null || true; } | wc -l | tr -d ' ')
if [[ "$CD_COUNT" -gt 0 ]]; then
    case "$COMMAND" in
        *$'\n'*|*';'*|*'||'*) exit 0 ;;
    esac
    if [[ "$CD_COUNT" -gt 1 ]]; then
        exit 0
    fi
fi

if [[ -z "$CWD" ]]; then
    exit 0
fi

# Resolve effective CWD when command starts with cd <path> (mirrors test-guard.sh).
EFFECTIVE_CWD="$CWD"
if [[ "$COMMAND" =~ ^[[:space:]]*cd[[:space:]]+([^[:space:];&]+) ]]; then
    CD_TARGET="${BASH_REMATCH[1]}"
    CD_TARGET="${CD_TARGET%\"}"; CD_TARGET="${CD_TARGET#\"}"
    CD_TARGET="${CD_TARGET%\'}"; CD_TARGET="${CD_TARGET#\'}"
    case "$CD_TARGET" in
        /*) ;;
        *) CD_TARGET="$CWD/$CD_TARGET" ;;
    esac
    if [[ -d "$CD_TARGET" ]]; then
        OUTER_TOP=$(git -C "$CWD" rev-parse --show-toplevel 2>/dev/null || echo "")
        TARGET_TOP=$(git -C "$CD_TARGET" rev-parse --show-toplevel 2>/dev/null || echo "")
        if [[ -z "$TARGET_TOP" ]]; then
            exit 0
        fi
        if [[ "$OUTER_TOP" != "$TARGET_TOP" ]]; then
            exit 0
        fi
        EFFECTIVE_CWD="$CD_TARGET"
    else
        exit 0
    fi
fi

REPO_ROOT=$(git -C "$EFFECTIVE_CWD" rev-parse --show-toplevel 2>/dev/null || echo "")
if [[ -z "$REPO_ROOT" ]]; then
    exit 0
fi

# --- Find test files that are present on disk but silently git-ignored ---
# `--others --ignored --exclude-standard` returns exactly the files that are
# untracked AND matched by a gitignore rule (tracked files are never listed).
# Filter to a `tests/` path component with a test_*.py basename, so scratch
# files outside tests/ are not flagged.
IGNORED_UNTRACKED=$(git -C "$REPO_ROOT" ls-files --others --ignored --exclude-standard 2>/dev/null || echo "")

OFFENDERS=""
while IFS= read -r f; do
    [[ -z "$f" ]] && continue
    base="${f##*/}"
    case "$base" in
        test_*.py) ;;
        *) continue ;;
    esac
    # Require a `tests` directory somewhere in the path.
    case "/$f" in
        */tests/*) OFFENDERS="${OFFENDERS}  - ${f}"$'\n' ;;
    esac
done <<< "$IGNORED_UNTRACKED"

# No silently-dropped test files — warning-free pass.
if [[ -z "$OFFENDERS" ]]; then
    exit 0
fi

# --- Offenders found: check for a structured [test-track-skip: ...] override ---
# Evidence-chain override accepted per writing-rules:4; bare form rejected (#579).
LATEST_MSG=$(git -C "$EFFECTIVE_CWD" log -1 --format=%B 2>/dev/null || echo "")
if echo "$LATEST_MSG" | grep -qE '\[test-track-skip:[[:space:]]+Reason:[^]]+;[[:space:]]*Evidence:[^]]+;[[:space:]]*Falsification:[^]]+\]'; then
    echo "WARNING: test-tracking-guard: [test-track-skip] override with evidence chain found in latest commit." >&2
    echo "Test-tracking verification skipped per structured override." >&2
    exit 0
fi
if echo "$LATEST_MSG" | grep -qE '\[test-track-skip(\]|:[[:space:]]*\]|:[[:space:]]+[^R])'; then
    cat >&2 <<'HOOKEOF'
BLOCKED: '[test-track-skip]' override requires an evidence chain.

Per writing-rules:4, every "this doesn't apply" claim requires the
evidence chain. Replace the bare form with:

  [test-track-skip: Reason: <falsifiable why this test is intentionally untracked>;
                    Evidence: <observable supporting the claim>;
                    Falsification: <what would prove it SHOULD be tracked>]
HOOKEOF
    exit 2
fi

cat >&2 <<HOOKEOF
BLOCKED: test file(s) present on disk but silently git-ignored (untracked).

The following test file(s) under a tests/ directory are matched by a
.gitignore rule and are NOT tracked by git. They will never be pushed;
local pytest passes while the test is absent from git history:

${OFFENDERS}
Most common cause: a user-level ~/.gitignore \`test_*.py\` pattern that
masks every tests/test_*.py from \`git status\` and \`git add\` with no
warning.

Remedy (per-repo override of the global rule):

  printf '!tests/test_*.py\n' >> "$REPO_ROOT/.gitignore"
  git add "$REPO_ROOT/.gitignore" <the test files>
  # verify: git check-ignore -v tests/test_*.py  (should print nothing)

Then re-stage the test file(s) and re-push. See [rule:writing-tests].

If a test file under tests/ is intentionally untracked, add a structured
override to the latest commit body:

  [test-track-skip: Reason: <why>; Evidence: <obs>; Falsification: <disproof>]

Ref: #931
HOOKEOF
exit 2

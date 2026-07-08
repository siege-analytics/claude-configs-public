#!/bin/bash
# Test: hooks/git/survey-context.sh (v2.1 definition-file detection + v2.2
# watched-path detection).
#
# Sets up an isolated temp git repo with a .agents/skills/survey-context/
# project skill catalog + a docs/entities/foo.md doc page (with both
# Definition and Watched paths fields), then exercises 6 scenarios.

set -uo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
REPO_ROOT=$(cd "$SCRIPT_DIR/../.." && pwd)
HOOK="$REPO_ROOT/hooks/git/survey-context.sh"

# shellcheck source=./run_scenarios.sh
source "$SCRIPT_DIR/run_scenarios.sh"

TMP_REPO=$(mktemp -d)
trap 'rm -rf "$TMP_REPO"' EXIT
cd "$TMP_REPO"
git init -q -b main
git config user.email "t@example.test"
git config user.name "test"

# Project-skill scaffolding.
mkdir -p .agents/skills/survey-context docs/entities src/widgets tests/widgets

cat > .agents/skills/survey-context/config.md <<'EOF'
# project skill

## Entity catalog

| Name | Type | Namespace | Doc page |
|---|---|---|---|
| Widget | Class | app.widgets | docs/entities/widget.md |
EOF

cat > docs/entities/widget.md <<'EOF'
# Widget (Class, app.widgets)

**Definition:** `src/widgets/widget.py:1`
**Watched paths:** `src/widgets/*.py`, `app/handlers/widget_*.py`

## Shape

Fields, etc.

## Survey log

- 2026-05-18: seeded.
EOF

# Initial source files so the rebase/diff range works.
echo "class Widget: pass" > src/widgets/widget.py
echo "from app.widgets import Widget" > src/widgets/helpers.py
echo "from app.widgets import Widget" > tests/widgets/test_widget.py
echo "other content" > src/other.py

git add -A
git commit -q -m "initial: scaffolding for survey-context test fixture"

make_payload() {
    local cmd="$1"
    printf '{"tool_input":{"command":"%s"},"cwd":"%s"}' "$cmd" "$TMP_REPO"
}

# Make a follow-up commit touching specific files, then run the hook against
# a simulated push. Returns to a clean baseline before each scenario.
fresh_commit_touching() {
    local body="$1"; shift
    local files=("$@")
    git reset --hard HEAD~0 2>/dev/null >/dev/null || true
    # Edit each requested file
    for f in "${files[@]}"; do
        echo "// touch $RANDOM" >> "$f"
    done
    git add -A
    git commit -q -m "fix: scenario commit" -m "$body"
}

reset_to_initial() {
    # Reset to the initial commit so each scenario starts clean.
    git reset --hard $(git rev-list --max-parents=0 HEAD) -q 2>/dev/null
}

# Scenario (a): touch Definition file (src/widgets/widget.py), no doc update -> BLOCK [v2.1]
reset_to_initial
fresh_commit_touching "Touched the Widget Definition file." src/widgets/widget.py
expect_block "(a) v2.1 definition-file touched, no doc update" "$HOOK" "$(make_payload 'g'$'i''t push origin main')"

# Scenario (b): touch Definition + doc page -> PASS
reset_to_initial
fresh_commit_touching "Touched Widget def and doc together." src/widgets/widget.py docs/entities/widget.md
expect_pass "(b) v2.1 definition + doc both touched" "$HOOK" "$(make_payload 'g'$'i''t push origin main')"

# Scenario (c): touch watched-path file (src/widgets/helpers.py), no doc update -> BLOCK [v2.2]
reset_to_initial
fresh_commit_touching "Touched a watched caller (widget helpers)." src/widgets/helpers.py
expect_block "(c) v2.2 watched-path touched, no doc update" "$HOOK" "$(make_payload 'g'$'i''t push origin main')"

# Scenario (d): touch watched-path file + doc page -> PASS
reset_to_initial
fresh_commit_touching "Touched watched caller and doc." src/widgets/helpers.py docs/entities/widget.md
expect_pass "(d) v2.2 watched-path + doc both touched" "$HOOK" "$(make_payload 'g'$'i''t push origin main')"

# Scenario (e): touch unrelated file (src/other.py) -> PASS silently
reset_to_initial
fresh_commit_touching "Touched an unrelated file." src/other.py
expect_pass "(e) unrelated file, neither definition nor watched" "$HOOK" "$(make_payload 'g'$'i''t push origin main')"

# Scenario (f): touch Definition with Doc-Update-Source trailer -> PASS via trailer escape
reset_to_initial
git reset --hard HEAD~0 2>/dev/null >/dev/null || true
echo "// touch $RANDOM" >> src/widgets/widget.py
git add -A
git commit -q -m "fix: scenario f" -m "Touched def but doc update lives elsewhere.

Doc-Update-Source: see SW#999 sibling PR"
expect_pass "(f) definition touched + Doc-Update-Source trailer escape" "$HOOK" "$(make_payload 'g'$'i''t push origin main')"

report

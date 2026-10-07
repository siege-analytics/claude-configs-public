#!/bin/bash
# Hook: decomposition-guard
# Enforces: wiki Testing-Cross-Layer §4.1 (one PR per touched layer).
# Trigger: PreToolUse on git push / gh pr create|merge / glab mr create|merge.
#
# Maps each touched SOURCE file to its layer via the testing.layers `source:`
# globs in PROJECT.md (longest-literal-prefix wins; each file -> exactly one
# layer), counts distinct layers touched within this repo, and BLOCKS when a
# single PR spans more than one layer.
#
# Scope notes:
# - SOURCE files only. Files matching no layer's source glob (scaffolding,
#   tests, docs, config) are layer-neutral and never counted — a pure-scaffolding
#   or docs-only push triggers nothing. Steps 1-2 of the §4.1 cascade
#   (hooks/harness plumbing) bundle by design and are not source files.
# - WITHIN-repo only. §4.2 makes a cross-repo ticket N>1 PRs by construction.
# - Projects without testing.layers `source:` globs are unaffected (exit 0).
#
# Override: [multi-layer-ok: <reason>] in the latest commit body (the mechanical
# surface for §4.1's explicit-waiver / explicit-cross-reference tolerance).
#
# V2: promoted from warn-only to blocking (exit 2). Ref: #575.

set -uo pipefail
export PATH="/home/craftagents/bin:$PATH"

INPUT=$(cat)
HOOK_DIR="$(cd "$(dirname "$0")" && pwd)"
EXTRACT="$HOOK_DIR/../lib/extract-json.py"
COMMAND=$(printf '%s' "$INPUT" | python3 "$EXTRACT" tool_input.command 2>/dev/null || true)
CWD=$(printf '%s' "$INPUT" | python3 "$EXTRACT" cwd 2>/dev/null || true)

[[ -z "$COMMAND" ]] && exit 0

# Trigger on git push / gh pr create|merge / glab mr create|merge (mirror test-guard).
TRIGGERS='(^|[^[:alnum:]])(git[[:space:]]+push|gh[[:space:]]+pr[[:space:]]+(create|merge)|glab[[:space:]]+mr[[:space:]]+(create|merge))([^[:alnum:]]|$)'
echo "$COMMAND" | grep -qE "$TRIGGERS" || exit 0

# Multi-statement-with-cd yield (mirror test-guard / branch-guard).
CD_COUNT=$(echo "$COMMAND" | { grep -oE '(^|[^[:alnum:]])cd[[:space:]]' 2>/dev/null || true; } | wc -l | tr -d ' ')
if [[ "$CD_COUNT" -gt 0 ]]; then
    case "$COMMAND" in
        *$'\n'*|*';'*|*'||'*) exit 0 ;;
    esac
    [[ "$CD_COUNT" -gt 1 ]] && exit 0
fi

[[ -z "$CWD" ]] && exit 0

# Resolve effective CWD when command starts with cd <path>.
EFFECTIVE_CWD="$CWD"
if [[ "$COMMAND" =~ ^[[:space:]]*cd[[:space:]]+([^[:space:];&]+) ]]; then
    CD_TARGET="${BASH_REMATCH[1]}"
    CD_TARGET="${CD_TARGET%\"}"; CD_TARGET="${CD_TARGET#\"}"
    CD_TARGET="${CD_TARGET%\'}"; CD_TARGET="${CD_TARGET#\'}"
    case "$CD_TARGET" in /*) ;; *) CD_TARGET="$CWD/$CD_TARGET" ;; esac
    if [[ -d "$CD_TARGET" ]]; then
        OUTER_TOP=$(git -C "$CWD" rev-parse --show-toplevel 2>/dev/null || echo "")
        TARGET_TOP=$(git -C "$CD_TARGET" rev-parse --show-toplevel 2>/dev/null || echo "")
        [[ -z "$TARGET_TOP" ]] && exit 0
        [[ "$OUTER_TOP" != "$TARGET_TOP" ]] && exit 0
        EFFECTIVE_CWD="$CD_TARGET"
    else
        exit 0
    fi
fi

REPO_ROOT=$(git -C "$EFFECTIVE_CWD" rev-parse --show-toplevel 2>/dev/null || echo "")
[[ -z "$REPO_ROOT" ]] && exit 0

# --- Locate the PROJECT.md that declares testing: (repo-root or projects/*/) ---
MANIFEST=""
if [[ -f "$REPO_ROOT/PROJECT.md" ]] && grep -qE '^[[:space:]]*testing:' "$REPO_ROOT/PROJECT.md" 2>/dev/null; then
    MANIFEST="$REPO_ROOT/PROJECT.md"
elif [[ -d "$REPO_ROOT/projects" ]]; then
    for pm in "$REPO_ROOT"/projects/*/PROJECT.md; do
        if [[ -f "$pm" ]] && grep -qE '^[[:space:]]*testing:' "$pm" 2>/dev/null; then
            MANIFEST="$pm"; break
        fi
    done
fi
[[ -z "$MANIFEST" ]] && exit 0

# --- [multi-layer-ok: reason] override ---
LATEST_MSG=$(git -C "$EFFECTIVE_CWD" log -1 --format=%B 2>/dev/null || echo "")
if echo "$LATEST_MSG" | grep -qE '\[multi-layer-ok:[[:space:]]'; then
    echo "WARNING: decomposition-guard: [multi-layer-ok] override present; layer-span check skipped." >&2
    exit 0
fi

# --- Touched files (merge-base resolver, mirror test-guard) ---
DEFAULT_REF=$(git -C "$EFFECTIVE_CWD" symbolic-ref --quiet --short refs/remotes/origin/HEAD 2>/dev/null || echo "")
MERGE_BASE=""
for ref in origin/develop origin/main origin/master "$DEFAULT_REF"; do
    [[ -z "$ref" ]] && continue
    MB=$(git -C "$EFFECTIVE_CWD" merge-base HEAD "$ref" 2>/dev/null || echo "")
    [[ -n "$MB" ]] && { MERGE_BASE="$MB"; break; }
done
[[ -z "$MERGE_BASE" ]] && exit 0

TOUCHED=$(git -C "$EFFECTIVE_CWD" diff --name-only "$MERGE_BASE"...HEAD 2>/dev/null || echo "")
[[ -z "$TOUCHED" ]] && exit 0

# --- Map touched source files -> layers; count distinct; WARN if >1 ---
TMP=$(mktemp 2>/dev/null) || exit 0
printf '%s\n' "$TOUCHED" > "$TMP"
python3 - "$MANIFEST" "$TMP" <<'PYEOF'
import sys, re
try:
    import yaml
except Exception:
    sys.exit(0)

manifest, touchedfile = sys.argv[1], sys.argv[2]
touched = [l.strip() for l in open(touchedfile, encoding='utf-8') if l.strip()]

# Parse YAML frontmatter (between the first '---' fence pair).
text = open(manifest, encoding='utf-8').read()
if not text.startswith('---'):
    sys.exit(0)
end = text.find('\n---', 3)
fm = text[3:end] if end != -1 else text
try:
    data = yaml.safe_load(fm) or {}
except Exception:
    sys.exit(0)

layers = (((data.get('testing') or {}).get('layers')) or [])

def glob_to_regex(g):
    out = ['^']; i = 0
    while i < len(g):
        if g[i:i+3] == '**/':
            out.append('(?:.*/)?'); i += 3
        elif g[i:i+2] == '**':
            out.append('.*'); i += 2
        elif g[i] == '*':
            out.append('[^/]*'); i += 1
        elif g[i] == '?':
            out.append('[^/]'); i += 1
        else:
            out.append(re.escape(g[i])); i += 1
    out.append('$')
    return ''.join(out)

def literal_prefix_len(g):
    m = re.search(r'[*?\[]', g)
    return len(g[:m.start()]) if m else len(g)

rules = []  # (compiled_regex, literal_prefix_len, layer_name)
for layer in layers:
    name = layer.get('name')
    for g in (layer.get('source') or []):
        rules.append((re.compile(glob_to_regex(g)), literal_prefix_len(g), name))

if not rules:
    sys.exit(0)

# Each touched file -> its best-match layer (longest literal prefix wins).
file_layer = {}
for f in touched:
    best = None
    for rx, plen, name in rules:
        if rx.match(f) and (best is None or plen > best[0]):
            best = (plen, name)
    if best:
        file_layer[f] = best[1]

layers_touched = sorted(set(file_layer.values()))
if len(layers_touched) > 1:
    sys.stderr.write(
        "WARNING: decomposition-guard: this push touches %d source layers (%s).\n"
        % (len(layers_touched), ", ".join(layers_touched)))
    by = {}
    for f, ln in sorted(file_layer.items()):
        by.setdefault(ln, []).append(f)
    for ln in layers_touched:
        sys.stderr.write("  %s:\n" % ln)
        for f in by[ln]:
            sys.stderr.write("    - %s\n" % f)
    sys.stderr.write(
        "BLOCKED: per Testing-Cross-Layer §4.1, production/test changes are one PR per layer.\n"
        "If intentional (Step-1/2 hooks/harness plumbing, or an explicit cross-referenced waiver),\n"
        "add [multi-layer-ok: <reason>] to the latest commit body.\n")
    sys.exit(1)
PYEOF
PYEXIT=$?
rm -f "$TMP"

if [[ "$PYEXIT" -ne 0 ]]; then
    exit 2
fi

exit 0

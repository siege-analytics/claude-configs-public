#!/bin/bash
# #1003 disposable-only wrapper: preserve the canonical resolver output, then
# inject the exact composed resident selected by the pinned project manifest.
set -euo pipefail
HOOK_DIR="$(cd "$(dirname "$0")" && pwd)"
WORKSPACE_ROOT="$(cd "$HOOK_DIR/../.." && pwd)"
BASE="$WORKSPACE_ROOT/hooks/resolver/inject-resolver.sh"
SELECTOR="$WORKSPACE_ROOT/bin/resolve-load-set.py"
PAYLOAD="$(cat || true)"
[[ -f "$BASE" && -f "$SELECTOR" ]] || {
  printf '%s\n' '<project-resident state="unavailable">canonical resolver or selector unavailable</project-resident>'
  exit 0
}
printf '%s' "$PAYLOAD" | bash "$BASE"
PROMPT="$(printf '%s' "$PAYLOAD" | python3 -c 'import json,sys; d=json.load(sys.stdin) if not sys.stdin.isatty() else {}; print(d.get("prompt") or d.get("tool_input",{}).get("prompt") or "")' 2>/dev/null || true)"
PROMPT_CWD="$(printf '%s' "$PAYLOAD" | python3 -c 'import json,sys; d=json.load(sys.stdin) if not sys.stdin.isatty() else {}; print(d.get("cwd") or "")' 2>/dev/null || true)"
[[ -n "$PROMPT_CWD" && -d "$PROMPT_CWD" ]] || PROMPT_CWD="$PWD"
RESULT="$(python3 "$SELECTOR" --prompt "$PROMPT" --cwd "$PROMPT_CWD" 2>/dev/null || true)"
RESIDENT_REL="$(printf '%s' "$RESULT" | python3 -c 'import json,sys; d=json.load(sys.stdin); print(d.get("kernel") or "")' 2>/dev/null || true)"
# This canary adapter is intentionally exact, not a general alternate-kernel
# mechanism. The compact safety kernel remains validated by BASE. Only the
# composition-declared resident path is accepted here.
[[ "$RESIDENT_REL" == "skills/RESIDENT.md" ]] || {
  printf '%s\n' '<project-resident state="not-selected"></project-resident>'
  exit 0
}
RESIDENT="$(python3 - "$WORKSPACE_ROOT" "$RESIDENT_REL" <<'PY'
from pathlib import Path
import sys
root=Path(sys.argv[1]).resolve(); rel=Path(sys.argv[2])
if rel.is_absolute() or '..' in rel.parts: raise SystemExit(2)
cur=root
for part in rel.parts:
    cur=cur/part
    if cur.is_symlink(): raise SystemExit(2)
resolved=cur.resolve()
try: resolved.relative_to(root)
except ValueError: raise SystemExit(2)
if not resolved.is_file(): raise SystemExit(2)
print(resolved)
PY
)" || {
  printf '%s\n' '<project-resident state="invalid">selected resident path is invalid</project-resident>'
  exit 0
}
printf '%s\n' '<project-resident state="selected" path="skills/RESIDENT.md">'
cat "$RESIDENT"
printf '%s\n' '</project-resident>'

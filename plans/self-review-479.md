## Self-Review: #479 — Fix safelist bypasses in universal-mutation-gate

## Assumptions
Working as: software engineer
Domain(s): software engineering
Geospatial cross-cut: no
Goal source: ticket #479
Plan reference: #479 ticket description (hostile review findings)
Pre-author-inventory: NONE
Investigate-artifact: plans/self-review-477.md (hostile review triage)
Pre-mortem-artifact: plans/pre-mortem-476.md

## Peer review

### Shell correctness
- `bash -n hooks/bash/universal-mutation-gate.sh` → exit 0 (syntax valid)
- Syntax check: N/A (no .py changes)

### Changes

1. **Removed `python3 -c` from SAFE_PATTERNS**: The pattern
   `'^python3? -c .*(import ast|import sys|import json|print\().*$'`
   allowed arbitrary Python with `python3 -c "import os; os.system('rm -rf /')"` 
   because it only checked for the presence of safe tokens, not the absence
   of unsafe ones. Removed entirely — `python3 -c` commands now require
   think-gate authorization.

2. **Narrowed `git config` in SAFE_PATTERNS**: Previously allowed all
   `git config` subcommands including `git config --global user.email`.
   Narrowed to `--get`, `--list`, `--get-regexp`, `--get-all` (read-only
   forms only).

3. **Added mutation indicators**: `sed -i`, `sed --in-place`, `awk -i inplace`,
   `patch`, plain `rm` (without flags), `git config --global/--system/--local/
   --unset/--add/--replace-all`.

4. **Fixed redirect pattern**: Added `>[^ ]` to catch `>file` (no space
   after redirect operator). The existing `> ` pattern only matched when
   a space followed the redirect.

## Lead review

Each fix addresses a confirmed finding from the hostile cross-review.
The Junior removed `python3 -c` entirely rather than trying to enumerate
safe patterns — correct, since any suffix-based allowlist for an
interpreter is fundamentally bypassable.

The `git config` narrowing is conservative — `git config user.name` (no
flag) is also a write, but it's covered by the fail-closed default: it
won't match the narrowed safelist pattern, so it falls through to the
think-gate check.

**Blast radius**: Commands that previously passed via `python3 -c` or
`git config` (write forms) will now be blocked. This is intentional.
The agent uses `python3 -c` for inline JSON extraction — those calls
will now require think-gate status. This may need a more targeted
safelist pattern in future if it creates friction.

## Findings

| ID | Priority | Description | Resolution |
|----|----------|-------------|------------|
| 1 | P3 | `python3 -c` removal may block legitimate inline data extraction | noted — monitor for friction, add targeted patterns if needed |

## Quantified claims
- "4 changes" — counted from diff sections above

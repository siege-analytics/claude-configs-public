# Self-review: rules bundle generator (#375)

## Lead

- **As tech lead:** Single file modified (`bin/build.py`) -- additive change
  only. New function `build_rules_bundle()` plus three helper functions.
  No existing functions changed in behavior. Bundle output is additive to
  `dist/` alongside existing `flat/` and `nested/`. Deploy copies one file
  to workspace. Fully reversible (remove the function and its call sites).

- **As domain expert:** Bundle concatenates all 24 `_*-rules.md` files in
  sorted order with `RULES.md` as entry point. Content is read from source
  (`skills/`), not from resolved `dist/` output -- no double-resolution of
  `[skill:slug]` tokens. Frontmatter is stripped so consumers get clean
  markdown. JSON variant includes per-rule keys for selective injection
  and a hash-friendly structure for staleness detection.

## Checklist

- [x] `build_rules_bundle()` reads from `SOURCE_SKILLS`, not `DIST`
- [x] All 24 `_*-rules.md` files included (verified via JSON `rule_count`)
- [x] `RULES.md` entry point included (verified via JSON `entry_point` key)
- [x] Banner includes version, commit hash, build timestamp, consumer instructions
- [x] `dist/RULES_BUNDLE.md` emitted on normal build
- [x] `dist/RULES_BUNDLE.json` emitted on normal build
- [x] `--check` mode does NOT emit bundle (verified: no bundle output in check)
- [x] `--deploy` copies `RULES_BUNDLE.md` to Craft Agent workspace
- [x] `build.py --check` still passes
- [x] `build.py` full build still succeeds
- [x] Python parse verified (`ast.parse`)
- [x] ASCII-only verified (perl check)
- [x] Module docstring updated to mention bundle

## Verification evidence

```
$ python bin/build.py --check 2>&1 | tail -1
Build check complete.

$ python bin/build.py 2>&1 | grep "Rules bundle"
  Rules bundle: 24 rules, 263344 chars

$ python3 -c "import json; d=json.load(open('dist/RULES_BUNDLE.json')); print(d['rule_count'])"
24

$ python bin/build.py --deploy 2>&1 | grep RULES_BUNDLE
  Copied RULES_BUNDLE.md to /Users/dheerajchand/.craft-agent/workspaces/my-workspace/
```

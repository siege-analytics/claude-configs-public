---
ticket_refs:
  - siege-analytics/claude-configs-public#1051: gates must be task-keyed
  - siege-analytics/claude-configs-public#1086: scale pre-mutation artifacts to the change's review tier
---

# Hostile review: slim #1051 (task-keyed gates + tiers + one read classifier)

**Reviewer:** an independent agent separate from the author. Its brief was read-only. It ran the real gate on crafted payloads in a temp workspace, and called `action()`/`task_tier()` directly.

## Confirmed (pre-fix)

1. **Tier C targets were evaluated at B when the shape recorded a directory or the repo toplevel.**
   - With only Tier B evidence, these exited 0: `rm -rf hooks/bash`, `cp -r src hooks/bash`, `git apply p.diff`, `git reset --hard`. The control `touch hooks/bash/x` exited 2.
   - At function level, B was also returned for `rm -r hooks`, `mv`, `tar -C`, `unzip -d`, `ln`, `find -delete`, `git rm -r`, `patch`, `git stash pop/am/cherry-pick/merge/pull/commit`, `make install`, `./install.sh`, `source` and `trap`.
   - Cause: the policy patterns end in `/`, so a bare directory falls through to "unclassified, B".
2. **Delegation proved a real mutation.**
   - `kubectl -n get delete pod x` and `kubectl --context get delete pod x` got verdict 0. The classifier took the flag's value as the subcommand.
   - Also proven: `kubectl -n logs exec`, `ss -K` and `gh search … --web`.

**Plausible:** a gate with no `repo_root`, or a different one, gave B for a C path ("outside classifier scope").

**Checked clean:**
- file-level shapes: `cd && touch`, `sed -i`, `perl -pi`, `git checkout --`, `git restore`, `cp`, `mv`, redirects, `tee`, `dd`, `install`, `rsync`, `chmod`, `truncate`, `ln -s`, and the bootstrap floor;
- Write/Edit `file_path` realpath;
- symlinks;
- case-insensitive matching;
- opaque inline execution, which is blocked;
- declared tier raises only;
- fail-closed when the tier JSON is missing or malformed.

## Resolution

1. **Tree-wide targets.** A directory or toplevel target is classified by `git ls-files` under it plus a probe path. A lone `git commit` uses the staged and modified files. No `repo_root`, a target outside it, or a failed listing now fails closed to C. Pinned by `test_tree_wide_targets_are_classified_by_their_contents`: `rm -rf hooks/bash`, `cp -r … hooks/bash`, `git apply` and `git reset --hard` are C. `rm -rf src` stays B. A docs-only commit passes, and a commit with a staged hook is C.
2. **Classifier holes.** Fixed upstream in #1089 (PR #1090): kubectl skips global options and their values, and `ss -K` and `gh --web` are vetoes. That classifier is carried here.

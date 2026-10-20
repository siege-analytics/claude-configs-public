---
ticket_refs:
  - siege-analytics/claude-configs-public#1100: hardlinks and link creation escape the session scratch rule
---

# Self-review: #1100 links cannot escape the session scratch rule

## Assumptions

Pre-author-inventory: in the electinfo#375 review, `cp -l ../../../plans/p.md h; echo x >> h` was allowed from `data/` with no gate, and it wrote to `plans/p.md`. Develop allows all 10 of the new escape cases.
Investigate-artifact: https://github.com/siege-analytics/claude-configs-public/issues/1100
Pre-mortem-artifact: plans/pre-mortem-1100-scratch-links.md
Hostile-review-artifact: https://github.com/siege-analytics/claude-configs-public/issues/1100#issuecomment-6289067161
Project-contribution: the scratch folder cannot be used to write files outside it.

- Canonical paths resolve symlinks, but no path check can see a hardlink, so the scratch rule now also looks at the file's link count.
- Both names of a link are targets in a link copy or `ln`, inside a task as well as in scratch, so a task's scope must cover both ends.

## Peer review

- **writing-code:**
  - `task_actions.py`: link copies keep every operand; `ln` gets its own branch; `rm` operands are reported as removals.
  - `resolve-think-gate.py`: `own_session_path` refuses a multi-link file for anything but removal.
- **writing-tests:** `read_allowlist.test.sh` gains 35 cases.
  - **Must-block:**
    - link copies, including GNU abbreviations (`--lin`, `--li`, `--sym`, `--symbolic`);
    - copies that carry a symlink across (`cp -P/-r/-a/--no-deref /proc/self/root r`);
    - writes, `tee`, `cp` and `chmod` onto an existing hardlink, including when an `rm` of the same name follows in the same command;
    - `ln` with relative escapes;
    - `ln` with an attached target directory (`--target-directory=d`, `--targ=d`, `-td`).
  - **Allow:**
    - reading, removing and copying from a hardlink;
    - links with both ends inside `data/` (`ln`, `ln -s`, `cp -l/-s/-a` between scratch files);
    - recursive copies of trees without symlinks.
- **Hostile review (first version: NOT-MERGE-SAFE), all fixed here:**
  - `ln`'s attached target directory had been dropped, which was looser than develop. It is now a target again; the gated probe gives develop's verdict on all four forms.
  - Abbreviated long options are matched by prefix.
  - A symlink-preserving copy turns its sources into targets when a source is, or contains, a symlink. The tree walk is capped at 2,000 entries, past which a symlink is assumed.
  - A removal excuses only a path that is never also written in the same command.
  - `ln` became a scratch verb, so links inside `data/` work.

  The reviewer's own attack matrix, re-run on this tree, changes no byte or mode outside `data/`.

- **Verification review:** a second reviewer confirmed all 32 attack rows now block, where develop allowed 23 of them, and nothing is looser than develop. A safety classifier stopped it before its new probes. I ran those myself, with execution and a byte check:
  - Every escape probe blocks and changes nothing outside `data/`: links outside then a write through them (`ln -s ../../../plans pl && echo x >> pl/p.md`, `ln -s / r`, `ln -s ..`/`.` then `..` traversal, a nested symlink then `..`), `ln -s ../../.. top; cp -P top t2; ...`, and `-sfn`/`-sT`/`--` forms.
  - A link inside `data/` written through is allowed and leaves outside files unchanged.
  - Accepted false positive: a write to a scratch file that has a second link inside `data/` blocks, because the link count cannot say where the other name lives.

## Test plan

- `bash hooks/_test/read_allowlist.test.sh`: 302/0 here.
- The reviewer's attack matrix (`attack1100.sh`), and the gated `ln` probe against develop.
- `python3 hooks/_test/task_keyed_gates.py`.
- The full CI validate job, run locally.

## Lead review

- **Solves #1100:** yes.
- **Out of scope:** links created by other programs (`python -c`, `install`). Those are opaque execution, which already needs a gate.

## Quantified claims

- `read_allowlist`: 302 cases, 0 failures.

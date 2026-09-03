---
ticket_refs:
  - siege-analytics/claude-configs-public#713: pre-mortem
---

# Pre-mortem: #713 run hooks/_test in CI

Design: `plans/design-713.md`

Premise: it is one week from now, the change shipped, and it went badly. This is
what went wrong, written before the fact.

## Tigers

### T1. Turning on a hook that has been dark for 458 commits blocks the epic

**Severity: CRITICAL.**

`detect-ai-fingerprints.sh` has not found its scanner since 2026-06-02. Fixing
the path does not add enforcement; it starts enforcement that the repository has
been writing against for 458 commits with no feedback. Every commit body in that
window was written under a hook that could not read it. If a meaningful fraction
of the epic's own commit bodies violate the scanner's rules, the first push
after this merges is refused, and so is the fix for it, because the fix is also
a push.

This is #703's T2 at a different surface, and #703 resolved it as a merge-order
dependency rather than a bypass. The same option may not exist here, because
there is no second ticket already open that fixes the corpus.

**Falsification before merge:** replay the scanner in `--message-file` mode
against the commit bodies of the epic's recent history and count refusals. If
the count is zero, the hook is safe to turn on. If it is not zero, the change
does not merge until the refused bodies are accounted for, and the accounting is
published rather than asserted.

**Rollback:** `git checkout HEAD~1 -- hooks/git/detect-ai-fingerprints.sh`
restores the dark hook. Single file, no state.

### T2. The CI step is added and cannot fail

**Severity: CRITICAL.**

A shell loop over test files discards each file's exit code unless the loop is
written to propagate it. `for f in ...; do bash "$f"; done` exits with the status
of the last file, so a failure in any file but the last is invisible. The step
appears in the job's step list, reports success, and the ticket ships a green
light for the exact condition it exists to detect.

This repository has now produced four instruments scoped to the set whose
absence they exist to detect: `MIN_HOOK_COUNT = 20`, the per-hook path
resolution, `validate-hooks.py`'s executability check, and a CI step that
compared a file to itself. A fifth on the same surface would be the strongest
evidence yet that the pattern is structural rather than incidental.

**Falsification before merge:** with the step in place, introduce a scenario
that is known to fail, push, and confirm the job goes red. Then confirm from the
Actions API step list that the step ran and reported failure, rather than
inferring it from the job colour. Remove the deliberate failure and confirm
green by the same method.

### T3. Correcting three fixtures makes them assert nothing

**Severity: HIGH.**

Three of the six are wrong fixtures, and the cheapest way to make a wrong
fixture pass is to rewrite its expectation to whatever the hook currently does.
That converts a failing test into a tautology and removes the only assertion in
the file that was still doing work. `test_guard` (c) is the most exposed: its
setup cannot reach the rule it names, and changing `expect_block` to
`expect_pass` would make it green while asserting the opposite of its own title.

**Falsification before merge:** each corrected fixture is run against a
knowingly broken hook and must fail. A fixture that passes both against the
hook and against a mutation of the hook is asserting nothing, and this is the
same check the #703 fixtures were held to.

## Paper cuts

### E1. The 9 passing files pass on macOS and fail on ubuntu-latest

Design assumption 2, and the one most likely to be wrong. Several files build
temporary git repositories, and `git init` default-branch behaviour, `mktemp`
argument handling and `grep -E` dialect all differ between the two platforms.
The failure is loud and lands on the branch rather than on `develop`, so it
costs a cycle rather than a rollback. Checked by pushing the branch and reading
the step result before the change is called done.

### E2. Scope grows from six scenarios to the whole hook surface

Settling scenario (e) already surfaced a message defect in the same file, and
settling (r) surfaced a stale comment. Each further pull is tempting and each
one adds a hook whose behaviour this ticket did not set out to change. The line:
a finding is in scope when the scenario cannot be settled without deciding it,
and out of scope otherwise. Anything out of scope is filed, not folded.

### E3. `dist/` artifacts from the investigation get committed

`bin/build.py` was run during the investigation to check the package layout.
Staging must name files, and `git status --untracked-files=all` is read before
staging rather than after CI complains.

## What would make me abandon the change

If T1's replay shows the scanner refusing a substantial fraction of the epic's
recent commit bodies, change 1 splits: the three fixture corrections and the CI
step ship, and the `detect-ai-fingerprints` path fix waits behind a ticket that
settles the corpus. That split is coherent here in a way #703's was not, because
the path fix is one line in one file and removing it from the commit leaves
nothing generated or hand-edited behind. The cost is that the CI step then ships
with `detect_ai_fingerprints.test.sh` still failing, so the step cannot be added
in the same commit, and the ticket's central sequencing argument would have to
be re-argued rather than assumed.

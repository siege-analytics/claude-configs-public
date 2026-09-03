---
ticket_refs:
  - siege-analytics/claude-configs-public#716: self-review for the exec-bit restoration
---

# Self-review: #716

Goal source: siege-analytics/claude-configs-public#716
Working as: software engineer

Unit under review: a single file-mode change, `hooks/bash/universal-mutation-gate.sh`
from 100644 back to 100755. No file content changes.

## Assumptions

1. **The mode change in `2cd567f` was incidental rather than intended.** Checked
   rather than carried: the blob content differs across that commit only in the
   regex anchor its message describes, and the message does not mention the
   mode. Nothing in the repository reads this hook in a way that would want it
   non-executable; `bin/validate-hooks.py` asserts the opposite.
2. **Restoring the bit changes no behaviour other than executability.** The blob
   is byte-identical before and after this commit; only the index mode moves.
3. **Not assumed: that this is the only mode regression.** The first audit
   covered `hooks/**/*.sh` only and was too narrow. Widened to `*.sh` across the
   repository it finds seven files at `develop`, which is the count #707 gives.
   The matrix is below. Six of the seven are invoked as `bash <file>` and the
   bit is cosmetic for them; one is executed by path. File types other than
   `.sh` remain unchecked.

## Quantified claims

| Claim | Value | How derived |
|---|---|---|
| non-executable `.sh` files on `develop` | 7 | `git ls-tree -r origin/develop`, mode not 100755 |
| of those, executed by path | 1 | audit matrix below |
| of those, invoked as `bash <file>` | 6 | audit matrix below |
| CI steps skipped because of this failure | 3 of 11 | steps 9, 10, 11 on run 33715422618 |
| days `develop` red before this was noticed | 2 | run 33558865629 dated 2026-09-01, filed 2026-09-03 |
| `validate-hooks.py` exit, mode 100644 | 1, naming the file | rebuilt and rerun |
| `validate-hooks.py` exit, mode 100755 | 0, all hooks valid | rebuilt and rerun |
| `universal_mutation_gate.test.sh` scenarios | 8 passed, 0 failed | run on this branch |
| test files failing on this branch | 3 | the pre-existing set #713 corrects |

## Audit matrix

Every `.sh` file committed non-executable on `origin/develop`, classified by how
the repository invokes it. Derived from
`git ls-tree -r origin/develop | grep '\.sh$' | awk '$1!="100755"'` and a
reference search for each basename.

| File | Class | Evidence | Action |
|---|---|---|---|
| `hooks/bash/universal-mutation-gate.sh` | executed by path | the agent runtime runs installed hooks by path; `bin/validate-hooks.py` asserts the bit | set 100755 |
| `bin/install.sh` | invoked as `bash <file>` | `README.md` Quick Start says `bash bin/install.sh`; `bin/harmonize.sh:72` runs `bash "$REPO_ROOT/bin/install.sh"` | leave 100644 |
| `bin/harmonize.sh` | invoked as `bash <file>` | `craft-agent/README.md:20` says `bash bin/harmonize.sh --workspace <slug>` | leave 100644 |
| `bin/verify-enforcement.sh` | invoked as `bash <file>` | `bin/install.sh:248` runs `bash "$REPO_ROOT/bin/verify-enforcement.sh"` | leave 100644 |
| `hooks/_test/ticket_required.test.sh` | invoked as `bash <file>` | the new CI step and the local runner both use `bash "$f"` | leave 100644 |
| `hooks/_test/universal_mutation_gate.test.sh` | invoked as `bash <file>` | same | leave 100644 |
| `hooks/_test/verify_enforcement.test.sh` | invoked as `bash <file>` | same | leave 100644 |

`README.md:27` lists `bin/install.sh` as the single-command install, which reads
as a claim that it is run directly. The Quick Start block four lines later gives
`bash bin/install.sh`, so the documented invocation does not need the bit. This
is the one row where a reader could reasonably disagree, and it is recorded
rather than resolved by preference.

## Findings

**S-1, P1: the defect was detected on 2026-09-01 and acted on 2026-09-03.**
`bin/validate-hooks.py` did its job. It named the exact file and the exact
reason on the first run after the regression landed. The gap is not detection,
it is that a red `develop` produced no consequence for two days while work
continued on branches that could not have gone green either.

**S-2, P2: the failure sits at step 8 of 11 and hides the three steps after it.**
Steps 9, 10 and 11 are reported `skipped`, not `failure`, so a reader checking
whether the `hooks/_test` runner from #713 works sees an absence rather than a
result. This is why #713's acceptance criterion 3 asks for the step list from
the API rather than the job colour: the colour would have said "red" and the
step list is what showed the new step existed and had never run.

**S-3, P3: the six other non-executable shell files are not the same defect and
are not fixed here.** All six are invoked as `bash <file>`, so the bit is not
load-bearing. See the matrix.

**S-4, P1: this ticket duplicates #707, and #707's own falsification clause is
the reason the audit above exists.** #716 was filed without searching the open
issue list. Its Falsification section reads "an existing open issue already
covering the exec bit on universal-mutation-gate.sh"; that check was written
down and not run. #707 covers the same file, the same mode, and the same
`validate-hooks.py` failure.

#707 is the better ticket. It asks for an audit matrix over all seven files
rather than a chmod on the one that is red, on the stated grounds that a
blanket `chmod +x` across a class of that size without classification is the
failure mode to avoid. It also carries a falsification clause: the ticket is
wrong if every one of the six remaining files is invoked only as `bash <file>`,
in which case the correct outcome is to close it with the matrix as evidence.

That clause fires. All six are `bash <file>`. So this PR closes #707 on #707's
own terms, and the matrix is the evidence rather than a courtesy. #707's third
acceptance criterion, that a check cover the directly-executed class and not
only wired hooks, is satisfied by a class of one that `validate-hooks.py`
already covers; if a future file joins that class the criterion returns.

Had the duplicate been found after merge instead of before, this unit would
have shipped a one-line chmod with the narrow `hooks/**` audit behind it and
left #707 open against a claim it had already been done.

## Peer review

writing-claims:3 -- every figure names its derivation. The before and after
validator exits are kept as separate rows rather than collapsed into a single
"fixed" claim, because the pair is the falsification and one row alone is not.

writing-tests:7 -- the fix was falsified rather than only confirmed. The mode
was set back to 100644, the tree rebuilt, and the validator returned to exit 1
naming the same file; then restored and rerun. Without that reversal the
passing validator would be consistent with the validator not checking the bit
at all.

writing-rules:7 -- N >= 3 requires an audit matrix. The Quantified claims table
carries it, including the out-of-scope rows.

## Lead review

Scope held to the mode change. The question of what should run `validate-hooks.py`
between an edit and a push is real and is named in the ticket's Design section
as out of scope; it is a hook-wiring decision of the same family as #713 and
should not be smuggled into a one-line unblock that every other branch is
waiting on.

The three failing test files on this branch are left failing. They are the
pre-existing set #713 corrects, and their failure here is corroboration that
the #713 measurement of "3 failing files on clean develop" was taken correctly.
Fixing them here would merge two units.

Scope grew by the audit matrix, which was not in the original plan. It is not
optional: #707 requires it, and without it this PR would be a chmod that closes
a ticket asking for a classification. The matrix is six rows of "leave alone"
and one row of "change", which is the outcome #707 anticipated and wanted
recorded rather than assumed.

Risk accepted: assumption 3 as narrowed. The audit covers `.sh` files. Other
file types that might need an exec bit, such as extensionless scripts or `.py`
files invoked by path, are unchecked. The bounded claim is that every `.sh`
file on `develop` is classified and that the validator passes on both packages.

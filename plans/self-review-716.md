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
3. **Not assumed: that this is the only mode regression.** The audit covered
   `hooks/**/*.sh` at `develop` and found one installed hook plus three files
   under `hooks/_test/`. The test files are invoked as `bash <file>` and do not
   need the bit. File types outside that glob are unchecked, and the honest
   statement is that they are unexamined rather than clean.

## Quantified claims

| Claim | Value | How derived |
|---|---|---|
| installed hooks with a missing exec bit | 1 | `git ls-files -s 'hooks/**/*.sh'`, mode not 100755 |
| non-exec files under `hooks/_test/` | 3 | same listing; out of scope, invoked via `bash` |
| CI steps skipped because of this failure | 3 of 11 | steps 9, 10, 11 on run 33715422618 |
| days `develop` red before this was noticed | 2 | run 33558865629 dated 2026-09-01, filed 2026-09-03 |
| `validate-hooks.py` exit, mode 100644 | 1, naming the file | rebuilt and rerun |
| `validate-hooks.py` exit, mode 100755 | 0, all hooks valid | rebuilt and rerun |
| `universal_mutation_gate.test.sh` scenarios | 8 passed, 0 failed | run on this branch |
| test files failing on this branch | 3 | the pre-existing set #713 corrects |

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

**S-3, P3: the three non-executable files under `hooks/_test/` are not the same
defect and are not fixed here.** They are invoked as `bash <file>` by both the
new CI step and the local runner, so the bit is not load-bearing for them.
Recorded because the audit surfaces them and a reviewer could reasonably ask.

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

Risk accepted: assumption 3. A wider mode audit across file types other than
`hooks/**/*.sh` has not been done. The bounded claim is that the one hook the
validator names is fixed and the validator now passes on both packages.

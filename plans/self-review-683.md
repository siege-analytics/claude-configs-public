# Self-review: ticket #683 (investigate the epic #682 executable path)

Working as: software engineer

Scope reviewed: `plans/investigate-682-executable-path.md` (894 lines) on branch
`feat/683-investigate-executable-path`, base `epic/682-python-executable-path`.
No source files are modified by this ticket; the deliverable is the fact sheet.

## What the ticket asked for, and whether it is there

| AC | Requirement | Mechanical check | Result |
|---|---|---|---|
| AC1 | `### <function_name>` header for every #682 checklist item | `grep -qx "### <name>"` for all 24 names | 24/24, 0 missing |
| AC2 | Each entry names File / Signature / Callers / Callees / Side effects / Known failures / Test coverage / Assumptions | `grep -c '^- \*\*<h>:\*\*'` per subheader | 24 for each of the 8 |
| AC3 | Embedded `verifiedShapes` block parses as JSON | extract `json` fence, `json.loads` | parses; 1 fence, 1 `verifiedShapes` key |
| AC4 | Call graph present | 2 `mermaid` fences, both `mermaid_validate` → valid | present |

Beyond the ACs, all 33 `file:line` citations in the `verifiedShapes` block were
resolved against the working checkout: every file exists and every line number is
within the file's length. 0 unresolved.

## Things I got wrong and fixed during the work

1. **Fabricated-adjacent line numbers.** I initially cited `_field` at
   `scaffold-test-stub.sh:133` (a comment line; the function is at `:135`) and the
   infra-ticket verification block at `templates/infra-ticket-tool-install.md:35`
   (it is `:34`). Both were caught only because I ran a citation-resolution pass
   rather than trusting the ranges I had written down earlier in the session.
   Corrected in place. This is the exact failure mode the guard's citation
   spot-check exists to catch, and I would have shipped it without the check.
2. **AC2 was failing on a literal grep** while looking fine to a reader: 15
   entries used `- **Assumptions to verify at rewrite time:**` and 2 used a
   combined `- **Callers / Callees:**`. The AC is falsifiable by grep, so
   "a reader can see it" is not compliance. Normalised to the eight exact
   subheaders; counts went 9→24 and 22→24.

## Claims I am making, and what would falsify each

- *24 checklist items are covered.* Falsified by any `### ` header in the file
  that does not match a checklist item, or any checklist item without one. The
  scripted check above enumerates the 24 names explicitly rather than counting.
- *Both suites are green while six P0 findings are live.* Falsified by a suite
  run that fails, or by a demonstration that any of F-N1, F-N11, F-N13, F-N14,
  F-N22 is not actually a defect. Two of the six (F-N1 trailing directory
  creation, F-N5 trailing-newline loss) have executed repros with byte-level
  evidence; F-N13 and F-N14 are read-level attestations, and I have recorded them
  as `SKIPPED` with reasons in the gate rather than claiming I ran them.
- *H2 is already falsified* — the rewrite cannot keep both suites byte-identical
  and be correct. Falsified if a correct implementation exists that preserves
  both `test_happy_path` and `test_path_traversal_rejected` unchanged; I do not
  believe one does, because correct behaviour changes observable output in both.

## What I deliberately did not do

- Did not re-derive findings already in the PR #668 and PR #672 hostile-review
  comments. They are cited by ID with a LIVE/REMEDIATED disposition established by
  same-turn repro, not re-litigated. Re-deriving them would have inflated the
  document and produced a second, drifting record of the same findings.
- Did not execute the k6 unsupported-OS `eval` path, a real playwright npm
  install, or a real `gh issue create`. Each is recorded as `SKIPPED` in the gate
  with a reason of the required length. Executing them would have mutated a shared
  machine or filed a public issue to prove something the source already shows.
- Did not propose a design. Ticket #683 is investigation only; the structural-vs-
  incidental classification of the 54 findings is named as the *first deliverable
  of the design ticket*, not smuggled in here.

## Weakest parts of this deliverable

1. **Severity assignment is mine alone.** The 6 P0 / 13 P1 / 7 P2 split for the 25
   new findings has had no second reader. F-N13 and F-N14 are P0 on the strength of
   "reaches `eval`" / "files a spurious public issue every run", but neither has an
   executed repro. A hostile reviewer should push hardest here.
2. **`_probe_resolve_policy` behaviour is inferred from a repo with no
   `PROJECT.md`.** `block` is the only path this repo can exercise. The `allow` and
   `prompt` branches — which contain every dangerous operation — are attested from
   source, never observed. That is a real gap and it is why finding F-N20
   (`probe_run` has zero coverage) is the one I would fix first.
3. **The 15-fixture port table maps fixtures to findings by my reading**, not by
   instrumenting the suite. A fixture I marked "—" could also be masking something.

## Standing-order compliance

- No AI or assistant attribution in the fact sheet, the self-review, or the commit.
- Commit authored as `Dheeraj Chand <dheeraj@siegeanalytics.com>` via explicit
  `-c user.name` / `-c user.email`.
- `Self-Review:`, `Self-Review-Source:`, `Design-Note-Source:` trailers present.
- No files under `hooks/` or `skills/` changed, so no `bin/build.py --deploy` run
  is required by this commit.
- Hostile review by a sibling on a different model is required before merge and
  has not happened yet at the time of writing.

---
ticket_refs:
  - siege-analytics/claude-configs-public#703: self-review for changes 1 and 2
---

# Self-review: #703 changes 1 and 2

Goal source: siege-analytics/claude-configs-public#703
Working as: software engineer

Unit under review: the `--relative` generator mode, the regeneration of
`.claude/settings.json`, `compare_settings_to_snippet` in
`bin/validate-hooks.py`, and the fixtures for both. Design:
`plans/design-703.md`. Pre-mortem: `plans/pre-mortem-703.md`.

## Assumptions

Roles named: software engineer, implementing the design's changes 1 and 2. The
reviewing roles the unit stands up to are software engineer, for the comparison
key and the fixtures, and tech lead, for the scope decision described under
Lead review.

1. **`hooks/settings-snippet.json` is the source of truth.** Carried from the
   design unit, where it was settled by history rather than assertion. Not
   re-derived here.
2. **The placeholder token is the only path-form difference.** `--relative`
   strips the `/path/to/claude-configs-public/` prefix and nothing else, which
   is the same normalisation the comparison uses. A consumer workspace with a
   third path form is out of scope and the design says so.
3. **Claude Code sends the NotebookEdit target as `tool_input.notebook_path`.**
   This is load-bearing for the guard fix below and is the one assumption here
   that is about the host rather than about this repository. It is asserted by
   the fixtures rather than proven: if the host sends some other key, the
   fixtures still pass and the guard still does not fire. That residual is
   stated rather than closed.

## Quantified claims

| Claim | Value | How derived |
|---|---|---|
| triples wired before regeneration | 27 over 24 hooks | comparison against the tree at `50ad7dd` |
| triples wired after regeneration | 35 over 29 hooks | same comparison, post-change |
| diff to `.claude/settings.json` | 57 insertions, 0 deletions | `git diff --stat`, and the zero confirms the strict-subset relation the design predicted |
| existing generator modes changed | 0 bytes | `diff` of default-mode and `--workspace`-mode output before and after |
| read-only corpus refused by the gate, develop | 6 of 20 | corpus replayed against `hooks/bash/universal-mutation-gate.sh` |
| read-only corpus refused by the gate, with PR #705 | 0 of 20 | same corpus, same script from `origin/fix/704-on-develop` |
| non-test hooks lacking the executable bit | 1 of 29 | `find hooks -name '*.sh' ! -perm -u+x` |
| drift fixtures | 9 | `bin/_test/settings_drift_test.py` |
| drift fixtures failing under a path-keyed comparison | 3 | same file, run against a mutated comparison |

## Findings

**S-5, P1: change 1 does not close the NotebookEdit bypass, and four published
artifacts said it does.** The design note, the PR #712 body, the previous
self-review and the correction posted to the ticket all state that the bypass is
fixed by change 1 without a separate ticket. Wiring the guards for
`NotebookEdit` was necessary and is not sufficient. All three write guards read
`tool_input.file_path` and `tool_input.path`; NotebookEdit supplies
`tool_input.notebook_path`, so each guard extracted an empty path and returned
its allow-early exit.

Measured on one guard and one target, varying only the payload key:

```
write-guard.sh, parsers/schemas/models.py
  before   file_path exit=2    notebook_path exit=0
  after    file_path exit=2    notebook_path exit=2
branch-guard.sh, a file on a protected branch
  before   file_path exit=2    notebook_path exit=0
  after    file_path exit=2    notebook_path exit=2
```

Shipping change 1 alone would have produced a settings file that wires three
guards against notebook writes, none of which can fire. That converts an open
gap into a believed-closed one, which is the L-35 shape the pre-mortem's T3
names, instantiated by the remedy rather than by the defect. The extractor
chains now list `notebook_path` and `bin/_test/notebook_edit_guards_test.py`
asserts both shapes against the same guard and target, so a guard that stops
blocking altogether fails the fixture rather than passing by symmetry.

The mechanism is the one this ticket keeps producing. The claim that change 1
fixes the bypass was an inference from the cause being shared, and it was
correct about the cause and wrong about the remedy. It read as measured because
the surrounding figures were.

**S-6, P1: the gate was wired and not executable, and the existing validator
could not see that.** `hooks/bash/universal-mutation-gate.sh` was committed at
mode 100644 and is the only non-test hook in the tree without the executable
bit. `validate-hooks.py` check 1 already asserted that every hook path resolves
to an existing executable file, and it iterates the hooks named in the settings
file, so a hook that is not wired is outside the set the check walks. The gate
was unwired and non-executable, and each condition hid the other. Wiring it is
what surfaced the mode bit. Fixed here as a mode change; `hooks/README.md`'s
`chmod` line also omitted `hooks/bash/` entirely and now includes it.

**S-7, P1: the CI step named "Validate repo hooks match snippet" did not compare
the two files.** Bare `validate-hooks.py` loaded the snippet as its settings
input and validated the snippet against itself. The step could not fail for the
reason its name gives. It now performs the comparison the name claims. This is
the third instrument on this surface whose name described a check it did not
run, after `MIN_HOOK_COUNT = 20` and the per-hook path resolution in T1.

**S-8, P1: T2's abandon-condition is met and the split it proposes is not
available.** The pre-mortem said that if the gate refuses a substantial fraction
of the epic's read-only corpus, change 1 splits and the gate is wired only after
the safelist gaps are fixed. Replaying 20 read-only commands this epic runs: the
gate on develop refuses 6, including `bash scripts/discipline/evaluate-ticket.sh`,
which every ticket must pass, and including `sed -n` and `awk`, the hazard the
#702 packet alleged and withdrew as unreproducible. The same corpus against the
gate on `origin/fix/704-on-develop` refuses 0.

The split the pre-mortem proposed would require hand-removing one triple from
the generated file, which change 2 then reports as drift on every build. A
settings file that is generated and then hand-edited is the behaviour this
ticket removes, and an exception list for the removed entry is T3's vacuous
check by another route. So the split takes the only coherent form available: a
merge-order dependency. **This branch must not merge before PR #705.** Recorded
here and on the ticket rather than resolved, because it is a sequencing
constraint and not a defect.

**S-9, P2: both fixture files were invisible to git.** A global gitignore
excludes `test_*.py` and `*_test.py`, so the two new test files were ignored
under either naming convention, and the CI steps referencing them would have run
against files not present in the repository. The repository now carries a
`!bin/_test/*.py` negation, which takes precedence over `core.excludesFile`, so
the fixtures are tracked regardless of a developer's global configuration. Found
by checking `git status --untracked-files=all` before staging rather than after
CI failed.

**S-10, P3: `hooks/_test/` holds 12 shell hook tests and no CI step runs any of
them.** This is E1's shape at repository scale. Not fixed here: turning them on
is a separate unit with its own failure surface, and folding it into this commit
would be the scope growth E2 warns about. The two fixtures added by this unit are
written in Python and wired into the workflow for that reason, so they run where
the drift they detect would be introduced. Reported on the ticket.

## Peer review

writing-claims:3 -- every figure in the table above names its derivation. The
before-and-after guard exit codes are reported as measurements on the same guard
and target with one variable changed, because the first version of that probe
used `/etc/hosts`, which neither guard blocks, and returned exit 0 on both
shapes. A probe that cannot distinguish the hypothesis from its negation reads
the same as one that can.

writing-tests:7 -- both fixture files were run against a knowingly broken
implementation before being trusted. The drift fixtures were run against a
comparison mutated to key on paths: 3 of 9 fail, and the one that fails first is
the single-matcher deletion, which returns an empty problem list. The notebook
fixtures were run against the committed guards: 4 of 7 fail. A fixture that has
never failed is an assertion about nothing.

writing-rules:7 -- N >= 3 requires an audit matrix. The Quantified claims table
carries it, and the two granularities stay separate rather than being reconciled
into one number.

## Lead review

Scope grew beyond the design's changes 1 and 2 by three items: the executable
bit, the `notebook_path` extractor chains, and the gitignore negation. Each was
found by executing the design rather than by reading it, and none is separable.
A hook that is wired and not executable is not wired. A guard wired for a matcher
whose payload it cannot read is not a guard. A fixture that git will not track is
not a fixture. Filing any of the three as its own ticket would leave this commit
shipping a settings file whose correctness claim is false, which is the failure
mode the ticket exists to remove. The isolate-one-at-a-time rule applies to
unrelated defects, and these are the same defect at three depths.

What this unit does not settle: why the live settings file changes mid-session,
and the terminal-status passthrough at `universal-mutation-gate.sh:211`, which
stays on #702. Assumption 3 above is the one live residual inside this unit.

Risk accepted: the merge-order dependency on PR #705. Until it lands, merging
this branch would turn on a gate that refuses 6 of 20 of the epic's own read-only
commands, and the pre-mortem is explicit that shipping a gate the operator has to
fight is how the bypass token got invented the first time.

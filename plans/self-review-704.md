---
ticket_refs:
  - siege-analytics/claude-configs-public#704: self-review
---

# Self-review: #704 mutation-gate read-only safelist

Working as: software engineer

Design: `plans/design-704.md`
Pre-mortem: `plans/pre-mortem-704.md`
Change: `hooks/bash/universal-mutation-gate.sh`, +33 lines, `SAFE_PATTERNS` only.

## Does this weaken enforcement?

This is the question the enforcement-fix guardrails at
`skills/_enforcement-contradiction-rules.md:214-215` require me to answer
directly, so I am answering it first rather than last.

**It adds three new ways for a command to skip the think-gate check.** That is
what a safelist entry is. The defensible version of this change is one where
each new entry admits only commands that cannot mutate, and I found two holes
in my own patterns while checking that, both of which are now closed and
tested.

**Hole 1, found during prototyping.** My first `sed` pattern allowed spaces in
the file argument. That admits `sed -n '1,2p' -i README.md`. GNU getopt
permutes options, so this edits the file in place, and `MUTATION_INDICATORS`
does not catch it because that array matches the literal substring `sed -i`,
which does not occur when the flag follows the script. The fix is a
single-bare-token file argument. Tested by
`sed with -i permuted after the script must block` and two siblings.

**Hole 2, found during prototyping.** Bare `^diff ` and `^comm ` admit
`diff <(id) <(id)`. Process substitution executes arbitrary commands and
contains no character that `MUTATION_INDICATORS` scans for; that array looks
for `>` but not `<`. The fix is the shared `_SAFE_ARG` grammar, which admits
only bare tokens without shell metacharacters or single-quoted strings that
cannot be closed early. Tested for `diff`, `comm` and `jq`.

Both holes would have shipped a silent mutation path into every workspace that
wires this gate, and neither would have been caught by this repo's own
sessions, because the gate is not wired here (#703).

**What I am still trusting rather than proving:** that `jq` has no write or
exec builtin, and that `diff` and `comm` write only to stdout. This rests on
documentation and the absence of a counterexample, not on an exhaustive audit
of those programs. `jq -f script.jq` passes, so a jq program file is trusted;
jq's language has no file-write or shell-exec operation, which is the property
the entry depends on. If that is wrong for some jq build, the entry is wrong.

## Was the fix minimal?

Guardrail 4 requires the narrowest change that resolves the contradiction.

The ticket as filed named five tools. Investigation removed two:

- `sed` cannot be safelisted by name because `sed -n '1w <path>'` writes a
  file. Only an anchored line-range-print form is admitted.
- `awk` is dropped entirely because `system()` and `"cmd" | getline` execute
  shell, both confirmed by running them.

So the shipped scope is smaller than the scope I published, and the ticket body
was corrected before implementation rather than after. `MUTATION_INDICATORS` is
untouched.

I did not widen to admit `python3 -c`, `python3 <script>` or `bash <script>`,
which were 3 of the 8 measured blocks. They execute arbitrary code. Leaving
them blocked means part of the observability problem remains, and that is the
correct trade.

## Are the tests real?

The pre-mortem's T2 was that preservation tests would pass via
`MUTATION_INDICATORS` rather than via the new patterns, proving nothing about
the code I wrote. That risk is real: `sed -i 's/a/b/' README.md` exits 2
whether or not my pattern is correct, because the indicator scan at `:117-123`
short-circuits before the safelist loop at `:126-132`.

The preservation cases that carry the weight are the ones with no indicator
match, which therefore reach the safelist loop: `sed -n '1w ...'`,
`sed -n '1e id'`, `sed -n '1r ...'`, `sed -n '1,2p' -i ...`, `diff <(id) <(id)`,
`comm -23 <(...) <(...)`. Each of those is refused only if my pattern refuses
it.

Three further guards against vacuous passes:

- A positive control (`head -3 README.md` passes) and a negative control
  (`curl -X POST` blocks), so a gate that was inert or blocking everything
  would fail the run rather than green it.
- An isolation proof: every scenario runs with `CRAFT_AGENT_WORKSPACE` pointed
  at an empty directory and a CWD outside any git repository, so no think-gate
  can resolve. Without this the gate exits 0 for everything and all 31
  scenarios pass for the wrong reason. The test asserts the CWD is not inside a
  repo and fails loudly if it is.
- A premise proof: the test actually runs `sed -n '1w <path>'` and asserts a
  file appeared. If a future platform makes that a no-op, the sed preservation
  scenarios become vacuous, and this assertion fails instead of quietly
  passing.

Evidence of the red-to-green transition: before the change, 6 failed and 19
passed. After, 31 passed and 0 failed. The 19 that passed before are the
controls and preservation cases, which is the right shape: the fix flipped only
the scenarios it was supposed to flip.

## Blast radius and regressions

- Full hook suite: 3 test files fail (`detect_ai_fingerprints` 3,
  `test_guard` 2, `ticket_required`). Verified pre-existing by stashing the
  change and re-running: identical counts. Not caused by this work and not
  fixed by it.
- `python3 bin/validate-hooks.py`: exit 0, 35 hook paths validated.
- Corpus of 26 read-only commands drawn from this epic: 18 passed before, 22
  after. The 4 still blocked are exactly the deliberately out-of-scope ones
  (`awk`, `python3 -c`, `python3 <script>`, `bash <script>`).

## Deployment path

Guardrail 6. The change is in `hooks/bash/universal-mutation-gate.sh` in this
repo. It reaches workspaces via `python3 bin/build.py --deploy`, which runs
after the commit. Deployed workspaces wire the gate by absolute path, so they
pick this up on the next deploy. This repo does not wire the gate at all, so
this change has no effect on this repo's own sessions until #703 lands. That
ordering is deliberate and is recorded in the pre-mortem as T3: #704 first,
verified by direct invocation, then #703 turns the gate on and gives these
patterns their first live exercise.

## What I would still call open

- The corpus bounds the fix to one epic's commands. Other work will hit other
  omissions. The claim that survives is "these four measured blocks are fixed",
  not "the safelist gap is closed".
- Double-quoted sed scripts (`sed -n "1,140p" file`) still block. Accepted:
  one quoting form covers the need, and admitting both doubles the surface.
  This surfaces as a block, which is the safe direction.
- `awk` remains blocked, so any diagnostic that genuinely needs awk is still
  in the Class 4 condition. I judged that better than safelisting a language
  with `system()`.

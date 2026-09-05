---
ticket_refs:
  - siege-analytics/claude-configs-public#704: pre-mortem posted
---

# Pre-mortem: #704 mutation-gate safelist gap

Design: `plans/design-704.md`

It is a month from now, the patterns shipped, and something went wrong.

## Tigers

### T1. The `sed` pattern admits a write after all

**Severity: CRITICAL.**

The whole safety argument for the `sed` entry is that its script body is an
allowlist over content: digits, an optional comma, and `p`, so `w`, `e`, `r`
and `s` are unreachable. If that argument has a hole, the gate gains a silent
file-write path in every workspace that wires it, and this repo will not notice
because the gate is not wired here (#703).

The specific way it fails is a bash `=~` subtlety rather than a logic error.
`SAFE_PATTERNS` entries are matched with `[[ "$COMMAND" =~ $pattern ]]`. If the
pattern is not anchored on both ends, or if a character class is wider than
intended, or if `+` and `?` are not supported as written by the local bash ERE,
the match can succeed on a string the author believed excluded. The existing
entries are anchored with `^` and terminated with a space or `$`; mine must be
anchored at both ends and I have to prove it rather than assert it.

This is also the failure the ticket already had once. The original body implied
`^sed -n `, which admits `sed -n '1w /path'`. The design caught it. A second
instance of the same mistake at a subtler level is the likely one.

**Falsification before merge:** the preservation test must feed the gate
`sed -n '1w /tmp/probe'`, `sed -n '1e id'`, `sed -n '1,2p' a; rm b`,
`sed -n '1,2p' $(id)`, and `sed -n '1,2p' a > out`, and assert exit 2 for every
one. Then confirm no file appeared at `/tmp/probe`, because asserting on exit
code alone tests the gate's opinion rather than the filesystem.

**Rollback:** revert the four array entries. No state, no migration.

### T2. The preservation test passes for the wrong reason

**Severity: HIGH.**

`MUTATION_INDICATORS` is scanned before the safelist. That means a test feeding
`sed -i 's/a/b/' README.md` will exit 2 whether or not my new pattern is
correct, because `sed -i` matches an indicator and the safelist loop is skipped
entirely. So the obvious preservation test proves nothing about the pattern I
added. It proves something about a line of code I did not touch.

This is the L-35 shape: a check satisfiable without the thing it detects. It is
worse than no check because it converts an open hole into a believed-closed
one, and the design's own safety argument rests on these tests.

**Falsification before merge:** the preservation cases must be ones that reach
the safelist loop. `sed -n '1w /tmp/probe'` contains no mutation indicator, so
it falls through to the safelist and is refused only if my pattern refuses it.
That is a real test of the pattern. Confirm the distinction by asserting that
`sed -n '1w /tmp/probe'` does not match any `MUTATION_INDICATORS` entry, so the
test cannot be passing via the earlier branch.

### T3. Fixing the gate's blindness while the gate is unwired

**Severity: MEDIUM, but it is the honest one.**

I am editing the primary enforcement gate in a repo where that gate does not
run. Every test I write is a direct hook invocation, not an observation of live
behaviour. That is the correct method here, and it is also exactly the
condition under which a mistake ships unnoticed. The four-commit drift in #703
happened the same way: changes to enforcement that nothing enforced.

**Mitigation:** do not merge #704 and #703 together. #704 first, verified by
direct invocation; #703 second, which turns the gate on and gives the #704
patterns their first live exercise. Merging them together means the first live
test of the new patterns is also the moment all enforcement changes at once.

## Elephants

### E1. The corpus bounds the fix to one epic

**Severity: MEDIUM.**

The 26-command corpus came from what this epic actually ran. It is evidence
that the gap is real; it is not evidence that four patterns close it. Other
work will hit other omissions, and each will look like a new Class 4 report.

**Mitigation:** say this in the ticket rather than closing #704 as "the
safelist gap is fixed". The claim that survives is "these four measured blocks
are fixed".

### E2. The asymmetry looks arbitrary without the comment

**Severity: LOW, high regret.**

`sed` gets one narrow form, `awk` gets nothing, `jq`/`diff`/`comm` get their
bare names. To a reader who has not run the probes, that is noise, and the
natural tidying instinct is to make it uniform. Uniform means either safelisting
`awk` (opens `system()`) or removing `sed` (reopens the contradiction).

**Mitigation:** the comment beside the entries names the two confirmed awk exec
vectors. It is the only thing standing between this design and a future
symmetry-motivated regression.

## Mice

- **M1.** `sed --version` fails on this machine (BSD). Any test that branches on
  sed flavour must not shell out to `--version`; the patterns are
  flavour-independent by design, so no test should need to.
- **M2.** The probe wrote `/tmp/e682/sed_w_probe` during investigation. Test
  fixtures must use a fresh temp path and assert non-existence before and after,
  or a leftover file makes the write test pass spuriously.
- **M3.** The ticket title said "sed, awk, jq, diff and comm" until the scope
  correction; anyone reading a cached copy will expect awk to be fixed.

## What would make me abandon this

If T1's falsification shows the anchored `sed` pattern admits any write or exec
form under any bash version in use, the `sed` entry is dropped and the ticket
ships with `jq`, `diff` and `comm` only. The blocked-observability
contradiction would then be partially unresolved, and I would say so on the
ticket rather than reaching for a looser pattern to close it.

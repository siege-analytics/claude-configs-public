---
ticket_refs:
  - siege-analytics/claude-configs-public#703: pre-mortem posted
---

# Pre-mortem: #703 hook-wiring drift

Design: `plans/design-703.md`

Premise: it is one week from now, the change shipped, and it went badly. This
document is what went wrong, written before the fact.

## Tigers

Things that kill the change outright.

### T1. The regenerated settings file disables all enforcement in this repo

**Severity: CRITICAL.**

`.claude/settings.json` is the live wiring for every agent session that runs
here. If the generated file is malformed, wires a wrong path, or drops a
matcher, sessions run with no gates and nothing announces it. The failure is
silent by construction: this ticket exists because a hook going dark produced
no signal for four commits.

The failure mode has a nasty second-order shape. If I break enforcement while
fixing enforcement, the broken state authorises the very commits that would
otherwise be blocked, including the commit that broke it.

**Falsification before merge:** after generating, for every (event, matcher,
path) triple in the generated file assert that the command path resolves to an
existing executable file relative to the repo root, and assert that the triple
set equals the snippet's under path normalisation. Per-hook assertion is not
enough, and the design's Step 1 says why: three of the eight missing entries
belong to hooks that were present, so an instrument that iterates hooks reports
clean while a whole matcher group is absent. Then fire at least one live block:
run a command the gate must refuse and confirm exit 2 with attribution naming
the relative path. A
generated file that parses as JSON is not evidence that it works; `install-
hooks.sh` already checks JSON parse and that check would have passed on every
day of the drift.

**Rollback:** `git checkout HEAD -- .claude/settings.json`. Single file, no
migration, no state. This is why the design keeps the changes separable.

### T2. Wiring universal-mutation-gate blocks this repo's own work

**Severity: HIGH.**

The gate has been effectively absent from repo-local sessions since #473
merged. Nobody has ever done sustained work in this repo with it on. It is
fail-closed and its `SAFE_PATTERNS` list was tuned in a workspace context, not
here. Turning it on could block routine commands across every in-flight ticket
in the epic.

Specific known hazard: the contradiction packet drafted for #702 alleged that
`sed -n` and `awk` are absent from `SAFE_PATTERNS` while `sed -i` is in
`MUTATION_INDICATORS`. That packet was **not published** because its
reproduction failed under test: `sed -n '1,3p' README.md` passed. So the
hazard is unconfirmed and must not be treated as established. But the general
shape stands: enabling a fail-closed gate that has never run here is the single
most likely way this change makes the library less functional rather than more.

**Falsification before merge:** replay a corpus of the read-only commands this
epic actually runs against the gate and count refusals. If the gate blocks
read-only diagnostics, that is a Class 4 "blocked observability" contradiction
under `skills/_enforcement-contradiction-rules.md:72-73` and it must be filed
and fixed before the gate is wired, not after.

**Rollback:** same single-file revert as T1.

### T3. The drift check is satisfiable without detecting drift

**Severity: HIGH.**

This is the L-35 shape: a check that can pass without the thing it detects
being absent is worse than no check, because it converts an open gap into a
believed-closed one. Concretely, `compare_settings_to_snippet` could return an
empty list because both files parsed to empty hook sets, because the
normalisation collapsed distinct entries onto the same key, or because the
function was never reached on the failing path.

The existing code already demonstrates this failure. `MIN_HOOK_COUNT = 20`
looks like a guard and passed happily at 24 while five hooks were missing.
Replacing one vacuous assertion with another is the default outcome here.

**Falsification before merge:** the true-positive preservation test must
delete exactly one hook from a fixture settings file and assert the validator
exits non-zero *and names that hook*. Asserting only on exit code admits a
validator that fails for an unrelated reason. A second fixture must delete a
single matcher from a hook that remains wired on its other matchers, which is
the live `NotebookEdit` case and the one a path-keyed comparison passes. Also
assert the computed set size, over triples and not over hooks, so an empty-set
comparison cannot masquerade as agreement; M3 is the reason that has to say
which number it means.

## Elephants

Large things in the room that will not kill the change but will be regretted.

### E1. The check runs somewhere nobody runs it

**Severity: MEDIUM.**

`validate-hooks.py` is called by `bin/build.py` and by CI. If the drift check
lands there but the actual regression path is "a hook is added to the snippet
in a commit that does not run the build", the check fires after the fact. The
four commits that caused this drift each touched the snippet. A check that runs
only on build would have caught them only if the build ran.

**Mitigation:** confirm the check runs on the same trigger that a snippet edit
takes. If the honest answer is that nothing runs on snippet edits, say so in
the ticket rather than shipping a check positioned where the historical
failures would have slipped past it.

### E2. Scope has already grown once and will grow again

**Severity: MEDIUM.**

Investigation falsified the assumption that `install-hooks.sh` could generate
the file, so Change 1 now includes a new `--relative` mode on a script that
consumers run. That is a behaviour change to the install path, which the design
listed under "what must keep working". The change is no longer the
low-risk-edit-plus-check that proposal A was scored as.

**Mitigation:** `--relative` must be additive and default-off, and the existing
default-mode and `--workspace`-mode outputs must be byte-identical before and
after. Diff them; do not reason about it.

### E3. The mid-session settings switch is still unexplained

**Severity: MEDIUM.**

The design scopes this out, on the argument that making the repo
file correct means it stops mattering which file wins. That argument holds only
if the two files converge. They will not: the workspace file carries
`ca-enforcement-gate.sh`, which the snippet does not have.

So after this change there are still two non-identical live settings files and
still no explanation for why the active one changes. The change reduces the
blast radius of that unknown; it does not remove it. Claiming otherwise in the
ticket would be the third false causal story on this surface.

**Mitigation:** state the residual on #703 rather than closing it as
resolved.

## Mice

Small, cheap to fix, easy to forget.

- **M1.** The audit matrix published on #703 lists `vergil-quote` as PreToolUse
  Bash; it is PostToolUse, and `spawn-guard` matches only
  `mcp__session__spawn_session`. The design note is corrected; the ticket body
  and the posted design-note comment still carry the error. Correct them
  publicly, since the whole point of this surface is that unverified claims
  have been published three times already.
- **M2.** `hooks/README.md` needs the line stating the snippet is canonical and
  `.claude/settings.json` is generated from it. Without it the next person
  hand-edits the generated file, which is exactly the behaviour being removed.
- **M3.** The 24-vs-29 counts in the ticket are distinct-hook counts, while the
  settings file has 27 entries because hooks repeat across matchers. Any test
  asserting a number must say which number it means.

## What would make me abandon this

If T2's falsification shows the gate blocks a substantial fraction of the
epic's read-only command corpus, Change 1 splits: wire the four low-risk hooks,
file the gate's safelist gaps as a blocking dependency, and wire the gate only
after those are fixed. Shipping a gate that forces the operator to fight it is
how `[mutation-acknowledged]` got invented in the first place, and #477 already
removed that once.

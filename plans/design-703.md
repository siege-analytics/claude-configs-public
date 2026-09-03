---
ticket_refs:
  - siege-analytics/claude-configs-public#703: design note posted
---

# Design note: the repo's own hook wiring has drifted from the canonical snippet

Ticket: siege-analytics/claude-configs-public#703

## Step 1: Context

### What prompted this

A `git push` was blocked by `universal-mutation-gate`. While diagnosing the
block the gate stopped enforcing mid-session, with no file on disk changing.
Investigating that produced the finding below. The originating push is not part
of this work and stays blocked.

### What is actually wrong

`hooks/settings-snippet.json` is the canonical hook wiring. `bin/install-hooks.sh`
generates settings files from it (`:2`, `:29`). It contains 29 distinct hooks
and it does include `hooks/bash/universal-mutation-gate.sh`.

The repository's own `.claude/settings.json` contains 24. Five hooks are absent
from it outright:

| Hook | Surface | What goes dark |
|---|---|---|
| `hooks/bash/universal-mutation-gate.sh` | PreToolUse Bash | the primary fail-closed mutation gate |
| `hooks/agent-comms/spawn-guard.sh` | PreToolUse `mcp__session__spawn_session` | constraints on spawning sibling sessions |
| `hooks/bash/coordinator-status-guard.sh` | PreToolUse Bash | coordinator status enforcement (#609) |
| `hooks/git/fix-shape-guard.sh` | PreToolUse Bash | fix-shape discipline |
| `hooks/git/vergil-quote.sh` | **PostToolUse** Bash | operator-visible cadence |

The matchers above are read out of the snippet, not assumed. An earlier
revision of this note listed `spawn-guard` as unqualified PreToolUse and
`vergil-quote` as PreToolUse Bash. Both were wrong: `spawn-guard` matches only
`mcp__session__spawn_session`, and `vergil-quote` is PostToolUse. The
correction matters for change 2, because a comparison keyed on hook path alone
would call the sets equal even if an entry migrated to the wrong event or
matcher. The comparison must be over (event, matcher, path) triples.

### Three more entries are missing, and this note found them by running its own rule

The paragraph above states the triple rule and the table above it was built by
comparing hook paths. Running the triple comparison the paragraph asks for gives
a different answer, and the difference is a live bypass rather than a
bookkeeping discrepancy:

```
snippet   35 (event, matcher, path) triples over 29 distinct hooks
repo      27 (event, matcher, path) triples over 24 distinct hooks
snippet-only triples  8      repo-only triples  0
```

Eight, not five. The five above account for five of the eight. The other three
are hooks the repo file **does** wire, on two of their three matchers:

| Triple | Wired for | Missing for |
|---|---|---|
| `hooks/write/write-guard.sh` | Write, Edit | **NotebookEdit** |
| `hooks/write/branch-guard.sh` | Write, Edit | **NotebookEdit** |
| `hooks/write/ticket-propagation-guard.sh` | Write, Edit | **NotebookEdit** |

The `NotebookEdit` matcher group is absent from `.claude/settings.json`
entirely, so in this repository a `NotebookEdit` call is a write that no write
guard sees: no write-guard, no branch-guard, no ticket-propagation-guard. That
is a hole in the same surface the rest of this note is about, and a path-keyed
comparison cannot see it, because all three hooks are present in the file.

This is the defect the note warns against, committed by the note. The warning
was written from a corrected claim -- two matchers had been wrong in an earlier
revision -- and a corrected claim is an argument. Executing the rule is a
measurement, and it was not done until the note was being committed. Recorded
here rather than folded into the table above, because change 2's whole
justification is that path-keyed comparison is insufficient, and this is now a
live instance rather than a hypothetical: the strongest evidence for the
requirement was sitting in the artifact that argued for it.

The relation is still a strict subset at both granularities: every triple in
`.claude/settings.json` is in the snippet, and nothing is repo-only. That is the
signature of an older generation of the generated file that was committed and
then never regenerated, rather than a deliberate local divergence.

`universal-mutation-gate.sh` declares at `:4` that it "MUST be FIRST in the Bash
hook list". In the repo's settings it is not in the list.

### Why the gate appeared to switch on and off

Two settings files are in play. The workspace file
`<workspace>/.claude/settings.json` wires 27 hooks by absolute path and does
include the gate. The repo file wires 24 by relative path and does not. Block
attribution echoes the path verbatim, so it identifies which file is live:

- 15:41:32 to 15:47:19, blocks attributed to the absolute workspace path.
- 16:19, `destructive-guard` fires attributed to `hooks/bash/destructive-guard.sh`,
  relative, so the repo file is live; `universal-mutation-gate` is silent
  because the repo file never wired it.

`destructive-guard` is in both files, which is why enforcement still felt
present while the mutation gate was gone.

### Sibling-grep gate

Required because this is a fix, not a feature.

- Same failure shape (wiring in canonical snippet, absent from live settings):
  **N = 8**, counted over (event, matcher, path) triples: the five wholly absent
  hooks and the three `NotebookEdit` triples. N = 5 was the path-keyed count and
  is the wrong instrument for this gate, since the gate asks how many instances
  of the failure exist and a hook wired on two of three matchers is an instance.
- Same drift shape (generated file committed, then source changed):
  `.claude/settings.json` is the only committed generated settings file;
  `.claude/settings.local.json` is generated and gitignored.

N = 8 is well past the N >= 2 threshold, so this is a class and the fix must be
class-level. Per `_writing-rules-rules.md` writing-rules:7, N >= 3 requires an
audit matrix, which is the pair of tables above.

Designing this as "add the mutation gate to settings.json" would be the
per-instance fix that the sibling gate exists to prevent. It would leave the
rest of the missing wiring dark and would not stop the next occurrence.

### What must keep working

- Consumers installing via `bin/install-hooks.sh` into their own workspaces.
- The workspace deployment path, which merges rather than replaces
  (`bin/build.py:1086`).
- Every hook currently wired in the repo file must stay wired.

### Blast radius

- `hooks/settings-snippet.json`: **LOW** as an edit target here, since this
  design does not modify it. It is the source of truth and is already correct.
- `.claude/settings.json`: **CRITICAL**. It is the live wiring for every agent
  session that runs in this repo. A malformed edit disables all enforcement.
- `bin/validate-hooks.py`: **MEDIUM**. Called by `bin/build.py` and by CI.

## Step 2: Questions and assumptions

**Assumption 1.** The snippet is the intended source of truth and the repo
settings file is meant to be a generated artifact of it. Evidence:
`install-hooks.sh:9` generates `.claude/settings.local.json` by default, and
the strict-subset relation. **If false**, the missing wiring was removed
by choice and this whole design is wrong. This is the single assumption the
design most depends on, and the one investigation must settle.

**Assumption 2.** No hook among the five is currently broken such that wiring
it would break every session in the repo. Untested. `validate-hooks.py` does
check `bash -n` and executability, which bounds but does not eliminate this.

**Assumption 3.** The five hooks going dark is the cause of the observed
enforcement gaps rather than merely correlated with them. Only the mutation
gate is directly evidenced.

**Open question.** Why does the live settings file change mid-session? This
design does not explain that and does not try to. It makes the repo file
correct so that it no longer matters which file wins. That is deliberate scope
limitation, not a claim that the switching is understood.

## Step 3: Proposals

| | A: regenerate + fail-closed drift check | B: hand-add the missing entries | C: runtime self-assertion |
|---|---|---|---|
| **What** | Regenerate `.claude/settings.json` from the snippet, then make drift a build error | Edit the missing entries into the settings file | Have each gate verify at run time that it is wired |
| **How** | `install-hooks.sh --target-file .claude/settings.json`, then extend `validate-hooks.py` with a settings-vs-snippet comparison that exits non-zero | Manual JSON edit preserving order | Each hook checks the live settings on invocation |
| **Tradeoffs** | Fixes the class and prevents recurrence; changes a CRITICAL file wholesale | Minimal diff; fixes nothing structurally | None, it does not work |
| **Risk** | Regeneration could reorder or drop an entry, or bake in a wrong path prefix | Sixth occurrence is a matter of time | n/a |

**C is impossible and I am recording why**, because I proposed it publicly on
#702 before thinking it through. A hook that is not wired is never
invoked, so it cannot assert its own absence. Self-presence checks can only be
performed by something guaranteed to run: an always-wired hook, the build, or
CI. Any design that asks the missing component to report itself missing is
circular. This is the same shape as the `_enforcement-contradiction-rules.md`
Class 4 "blocked observability" case and I walked into it.

**Recommendation: A.** B is the per-instance fix the sibling-grep gate exists
to reject. A is the only option that makes the sixth occurrence detectable.

## Step 4: Design

### Architecture

Two changes, kept separable so the risky one can be reverted alone.

**Change 1, corrective.** Regenerate `.claude/settings.json` from
`hooks/settings-snippet.json` with the repo-relative path prefix, restoring all
35 triples over 29 distinct hooks, with `universal-mutation-gate.sh` first in
the Bash chain per its header contract. Regeneration restores the `NotebookEdit`
group as a side effect of being a regeneration; the three triples were never
going to be found by anyone enumerating missing hooks by name, which is the
argument for regenerating rather than hand-adding.

**Change 1 needs a generator that does not exist yet.** The design originally
said "run `install-hooks.sh --target-file .claude/settings.json`". That does
not produce the required output. `install-hooks.sh:110` is:

```bash
sed "s|/path/to/claude-configs-public|$HOOKS_ROOT|g" "$SNIPPET" > "$TARGET"
```

`HOOKS_ROOT` is always an absolute directory path; the script has no mode that
emits relative hook paths. The committed `.claude/settings.json` is entirely
bare-relative (27 entries, 0 absolute, sample `hooks/bash/destructive-guard.sh`).
Regenerating with the existing tool would bake this machine's absolute
`/Users/...` prefix into a file that is committed and shared across checkouts,
which is worse than the drift it fixes.

So Change 1 becomes: add a `--relative` mode to `install-hooks.sh` that
substitutes the placeholder such that hook commands come out bare-relative,
then use it to generate `.claude/settings.json`. This keeps a single generator
and makes the repo's own settings file reproducible rather than hand-maintained,
which is the actual root cause. Hand-editing the file would leave it
regenerable-by-nobody, and that is how it drifted for four commits.

**Change 2, preventive.** Add a drift check to `bin/validate-hooks.py`:

```
compare_settings_to_snippet(settings_path, snippet_path) -> list[str]
```

Returns the symmetric difference of the two hook sets, normalised for the
`/path/to/claude-configs-public` token and for relative-vs-absolute prefixes.
Non-empty means exit non-zero with the missing and extra entries named.

The comparison key is the **(event, matcher, path) triple**, not the path
alone. This is not a precaution. Keying on path misses three of the eight
missing entries in this repository today, because the three `NotebookEdit`
triples belong to hooks the file already wires on other matchers, and a
path-keyed check reports the file clean on all three. Step 1 records how that
was found. A check that would have passed the artifact it is being written to
fix is the failure mode this ticket exists to remove, and the count assertion
`MIN_HOOK_COUNT` and the path-keyed reading fail it in the same direction.

**Known legitimate settings-only entry.** `bin/wire-enforcement.py` injects
`ca-enforcement-gate.sh` into a *workspace* `.claude/settings.json` after
`install-hooks.sh` runs, and it is not in the snippet. Confirmed present in the
workspace file and absent from both the snippet and the repo file. The repo's
own settings file is not a deploy target for `wire-enforcement.py`, so the
symmetric difference for the repo file should be exactly empty and this entry
does not need an exemption here. It does mean the check must not be reused
against a consumer workspace without one.

This must be an error, not a warning. `validate-hooks.py` already has a
warnings channel for "hook on disk but not in settings" (check 4), and that
channel is exactly why this drift survived: it was reportable and nobody was
required to act. A warning that has been ignored for months is not a check.

`MIN_HOOK_COUNT = 20` also failed to catch this, since 24 > 20. The count
assertion is not a substitute for set comparison and should stay as a separate,
weaker backstop.

### Interface

No public API changes. `validate-hooks.py` gains one function and one exit
condition. Invocation is unchanged.

### Edge cases

- **Path prefix forms.** The snippet uses a placeholder token, the repo file
  uses relative paths, the workspace file uses absolute. Comparison must
  normalise all three or it will report false drift on every run.
- **Deliberate local divergence.** A consumer may legitimately not want a hook.
  The check runs against this repo's own settings, not a consumer's, so this is
  out of scope here, but it is the reason the check should name what differs
  rather than silently rewriting.
- **Ordering.** The gate's header requires it first in the Bash list. Set
  comparison does not test order. Order needs its own assertion or the contract
  is unenforced.
- **Empty or unparseable settings.** Must fail loudly, not treat as no drift.

### Documentation plan

- `hooks/README.md` references `settings-snippet.json`; it needs a line stating
  the snippet is canonical and `.claude/settings.json` is generated from it.
- No skill or rule file changes.

## Investigation Dependencies

- **Assumption 1, snippet is canonical**: **RESOLVED, confirmed.** The two
  files share history through `b025631`. After that the snippet took four more
  commits and `.claude/settings.json` took none:

  | Commit | Ticket | Adds to snippet |
  |---|---|---|
  | `00a25a5` | #473 | `universal-mutation-gate.sh` |
  | `eafa008` | #188 | `fix-shape-guard.sh` |
  | `79d81be` | #482 | `vergil-quote.sh` |
  | `c3d9951` | #609/#611 | `coordinator-status-guard.sh`, `spawn-guard.sh` |

  `git log -S<hook>.sh -- .claude/settings.json` returns empty for all five,
  so the strings never appeared in that file. They were never removed because
  they were never added. This is drift by omission across four commits, each of
  which updated the source and not the generated artifact, which is a stronger
  result than the design assumed: there is no deliberate-divergence reading
  available, and Change 1 stands.

- **The five hooks are individually sound**: **RESOLVED, satisfied.** All five
  exist, are executable, and pass `bash -n`. Behavioural probe with a benign
  `ls -la` Bash payload: `coordinator-status-guard`, `fix-shape-guard` and
  `vergil-quote` all exit 0, so none is a block-everything hook.
  `spawn-guard` needs its own payload shape; on a `spawn_session` call missing
  `permissionMode`, `thinkingLevel` and `enabledSourceSlugs` it exits 2 with a
  named reason, and on a complete one it exits 0. That is correct behaviour,
  not a defect.

  Recording a near-miss: probing `spawn-guard` with the Bash payload produced
  exit 2 and briefly looked like a block-everything hook. It was the wrong
  payload shape for its matcher. A probe that does not match the hook's
  declared matcher tests nothing, and reading the matchers out of the snippet
  is what corrected both this and the audit-matrix error above.

- **Order contract**: **RESOLVED, satisfied.** Grepping the tree for
  position claims returns exactly one hook-order assertion,
  `universal-mutation-gate.sh:4`. The only other hit,
  `bin/wire-enforcement.py:6` ("must be the last writer to settings.json"), is
  a claim about tool sequencing, not about hook order inside the file. The
  order assertion therefore covers one hook, as the design assumed.

- **Change 1's generator exists**: **FALSIFIED.** `install-hooks.sh` cannot
  emit relative hook paths, so the regeneration step the design named does not
  work. Change 1 absorbs a `--relative` mode as described in Step 4. Recording
  this as a falsified dependency rather than silently widening scope: the
  change is now larger than the design's proposal-A tradeoff column assumed,
  and the pre-mortem must price that.

## Step 8: Downstream routing

- **investigate:** DONE. Assumption 1 was load-bearing; it is now settled
  above, and settling it also falsified two matcher claims in the audit matrix.
- **pre-mortem:** YES. The change touches a CRITICAL file that gates all work.
- **survey-context:** NO. No entity doc layer for hook wiring.

## Scope boundary

Explicitly not in scope: the `git push` of `fix/688-guard-pipefail-frontmatter`;
why the live settings file changes mid-session; and the terminal-status
passthrough at `universal-mutation-gate.sh:211`, which is a real second defect
on the same surface and stays on #702.

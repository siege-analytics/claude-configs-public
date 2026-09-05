---
ticket_refs:
  - siege-analytics/claude-configs-public#704: design note posted
---

# Design note: the read-only safelist gap is smaller than the ticket claimed

Ticket: siege-analytics/claude-configs-public#704

## Step 1: Context

### What prompted this

`universal-mutation-gate.sh` blocks `sed -n '1,140p' <file>` while allowing
`head -140 <file>`. The block message instructs the operator to inspect
`SAFE_PATTERNS` inside the gate file, and blocks the command that would do the
inspecting. That is a Class 4 blocked-observability contradiction under
`skills/_enforcement-contradiction-rules.md` lines 72-73, and the packet is on
the ticket.

### What the ticket got wrong

\#704 as filed named five tools as the gap: `sed`, `awk`, `jq`, `diff`, `comm`.
Two of those claims do not survive measurement.

**`sed -n` is not read-only.** The `w` command writes files, and `-n` does not
suppress it:

```
$ printf 'x\n' | sed -n '1w /tmp/e682/sed_w_probe'
$ ls -la /tmp/e682/sed_w_probe
-rw-r--r--@ 1 dheerajchand  wheel  2 Sep  2 20:21 /tmp/e682/sed_w_probe
```

A safelist entry of `^sed -n ` would have admitted `sed -n '1w /path'`, which
creates a file. GNU sed additionally has the `e` command, which executes a
shell command; BSD sed on this machine rejects it (`invalid command code e`),
but CI is not guaranteed to be BSD, so the pattern must not rely on that.

**`awk` executes shell.** Two independent vectors, both confirmed here:

```
$ awk 'BEGIN{system("echo AWK_SYSTEM_RAN")}'
AWK_SYSTEM_RAN
$ awk 'BEGIN{ "echo AWK_PIPE_RAN" | getline r; print r}'
AWK_PIPE_RAN
```

`awk` is a general-purpose language with `system()`, command pipes, and
`print > "file"`. It cannot be safelisted by tool name under any pattern I
would trust, and I am not going to write a regex that attempts to parse an awk
program for side effects.

So the honest gap is three provably-side-effect-free tools plus one narrow form
of `sed`, not five tools. The ticket's assumption 2 said "if false for any
tool, that tool is dropped from scope rather than the pattern being widened".
It is false for two, and this is that drop.

### Why the fail-open direction matters here

The gate is fail-closed, so an omission from `SAFE_PATTERNS` costs an operator
a blocked read. A pattern that is too permissive costs every workspace a silent
mutation path, and this repo would not notice, because the gate is not wired in
this repo's own `.claude/settings.json` (#703). Errors in the two directions are
not symmetric and the design should not treat them as if they were.

### Sibling-grep gate

Required because this is a fix, not a feature.

- Same failure shape (read-only tool absent from `SAFE_PATTERNS`, no path
  through): **N = 3** confirmed (`jq`, `diff`, `comm`) plus the `sed` paging
  form. Past the N >= 2 threshold, so the fix is class-level: add the class of
  provably-side-effect-free readers, not just the one that blocked me.
- Same failure shape in the opposite direction (tool safelisted despite having
  a side-effecting form): **N = 0** found. `SAFE_PATTERNS` entries were checked
  against their tools' write and exec forms; the existing entries are anchored
  with a trailing space or `$` and none admits a shell-exec form.

N = 3 means the audit is the table in Step 4 rather than a one-line patch.

### What must keep working

- `sed -i`, `sed --in-place`, `awk -i inplace` must still block.
- The 18 corpus commands that already pass must still pass.
- `python3 -c`, `python3 <script>`, `bash <script>` must still block.

### Blast radius

**HIGH.** `universal-mutation-gate.sh` is the primary fail-closed gate for every
workspace that wires it. A too-permissive pattern silently admits mutations
across all of them and the failure is not locally observable.

## Step 2: Questions and assumptions

**Assumption 1.** `MUTATION_INDICATORS` is scanned before `SAFE_PATTERNS`, so a
safelist entry cannot admit a form already named as a mutation. **Confirmed by
reading**: the compound scan is `:117-123` and sets `COMPOUND_MUTATION`; the
safelist loop at `:126-132` is guarded on that flag being false. This is why
`sed -i` cannot slip through a `sed` safelist entry.

**Assumption 2.** `jq`, `diff` and `comm` have no side-effecting invocation
reachable without a shell redirect. `jq` has no write or exec builtin; `diff`
and `comm` write only to stdout. Redirects are independently caught by the
indicator at `:107`. **If false for any of the three**, that tool is dropped,
not accommodated.

**Assumption 3.** The operator's actual blocked-observability need is "print a
line range of a file", which is what `sed -n '<range>p' <file>` serves. If the
need is broader, this fix is incomplete rather than wrong, and the remainder
surfaces as further blocks.

**Open question.** Whether `awk` should get a narrow safelisted form later
(for example an anchored `awk 'NR<[0-9]+'`). Not in scope. Every narrow awk
form I considered is one quote character away from admitting a program, and
`sed -n` range printing plus `head`/`tail` already covers the paging need.

## Step 3: Proposals

| | A: anchored narrow forms | B: safelist tool names | C: leave it, use the think gate |
|---|---|---|---|
| **What** | Add tightly anchored patterns admitting only provably-safe invocations | Add `^(sed\|awk\|jq\|diff\|comm) ` | No code change; produce a think gate before diagnosing |
| **How** | `sed` restricted to a digit/comma/`p` script; `jq`, `diff`, `comm` by name | One line per tool | n/a |
| **Tradeoffs** | Resolves the contradiction without widening; patterns are strict and may block legitimate variants | One line, and admits `sed -n '1w /path'` and `awk 'BEGIN{system(...)}'` | Zero risk of widening; does not fix the contradiction |
| **Risk** | A too-strict pattern is a nuisance, surfaced as a block | Silent mutation path in every workspace | Circular: the artifact set cannot be produced without the blocked read |

**C is what the gate currently tells you to do and it is the thing the rule
names as impossible.** Recording it because "just comply" is the default
objection to any Class 4 report, and the answer is at rule line 158-159: the
precondition is circular here, unlike the #688 push where it was merely
unmet.

**Recommendation: A.**

## Step 4: Design

### Architecture

Four additions to `SAFE_PATTERNS`, no changes to `MUTATION_INDICATORS`.

| Pattern | Admits | Rejects |
|---|---|---|
| `^sed -n '[0-9]+(,[0-9]+)?p'[[:space:]]+[^;&\|<>'"'"'"]+$` | `sed -n '1,140p' file` | `sed -n '1w /path'`, `sed -n '1e cmd'`, anything with `;`, `&`, pipe, redirect, or a second quoted script |
| `^jq( \|$)` | `jq . file`, `jq -r '.a' file` | `jq ... > out` via the `:107` redirect indicator |
| `^diff( \|$)` | `diff a b` | as above |
| `^comm( \|$)` | `comm -23 a b` | as above |

`awk` is deliberately absent. The reason is recorded in a comment beside the
`sed` entry so the next person does not add it by symmetry.

The `sed` pattern is anchored at both ends and its script body admits only
digits, an optional comma, and `p`. There is no character class in it that can
express `w`, `e`, `r` or `s`, so the write and exec commands are unreachable by
construction rather than by enumeration. That is the property that makes it
reviewable: it is an allowlist over the script content, not a denylist.

### Interface

No interface change. `SAFE_PATTERNS` is an internal array.

### Edge cases

- **Double-quoted sed script.** `sed -n "1,140p" file` will not match and will
  block. Accepted: one quoting form is enough for the diagnostic need, and
  admitting both doubles the surface for no gain. This will surface as a block,
  which is the correct direction for the error.
- **`sed -n` with no file argument** (reading stdin in a pipe). The `$`-anchored
  file argument makes this not match. Accepted; a pipeline is a compound
  command and the gate treats compounds separately.
- **`comm` and `diff` with process substitution** `<(...)`. The `<` is excluded
  by the redirect indicator at `:107` and by the pattern's own exclusion set.
  Blocked, correctly, since process substitution runs arbitrary commands.
- **GNU vs BSD sed.** The design does not depend on which is present, because
  the pattern never admits the commands that differ between them.

### Documentation plan

- A comment in `SAFE_PATTERNS` beside the new entries stating why `awk` is
  excluded, with the two confirmed exec vectors named. Without it the next
  reader sees an arbitrary asymmetry and removes it.
- No skill or rule file changes.

## Investigation Dependencies

- **Assumption 1, indicator-before-safelist**: RESOLVED by reading `:117-132`.
- **Assumption 2, the three tools are side-effect free**: partially resolved.
  `jq` has no write builtin and `diff`/`comm` write to stdout only. This rests
  on documentation and absence of a counterexample, not on an exhaustive proof.
  **If falsified:** drop the tool.
- **The corpus is representative**: unresolved and probably unresolvable. It is
  drawn from this epic's actual commands, which bounds it to one epic.

## Step 8: Downstream routing

- **investigate:** DONE. Investigation is what falsified the `sed` and `awk`
  claims in the ticket body.
- **pre-mortem:** YES. HIGH blast radius on the primary gate.
- **survey-context:** NO. No entity doc layer for hook safelists.

## Scope boundary

Not in scope: the `:211` terminal-status pass-through (#702); the hook wiring
drift (#703); a narrow `awk` form; and `python3 -c` / `python3 <script>` /
`bash <script>`, which execute arbitrary code and are correctly blocked.

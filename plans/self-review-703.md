---
ticket_refs:
  - siege-analytics/claude-configs-public#703: self-review for the design and pre-mortem unit
---

# Self-review: #703 design note and pre-mortem

Goal source: siege-analytics/claude-configs-public#703
Working as: software engineer

Unit under review: `plans/design-703.md` and `plans/pre-mortem-703.md`. No
executable change is in this commit. Change 1 (the `--relative` generator mode
and the regeneration of `.claude/settings.json`) and change 2
(`compare_settings_to_snippet`) are the next unit and are not started.

## Assumptions

Roles named: software engineer, writing the design and pre-mortem for a fix to
the repository's own hook wiring. The reviewing roles the artifacts stand up to
are tech lead, for the scope decision to regenerate rather than hand-patch, and
software engineer, for the comparison-key decision.

1. **`hooks/settings-snippet.json` is the source of truth.** Settled in the
   design's Investigation Dependencies section by history rather than by
   assertion: the two files share history through `b025631` and the snippet took
   four further commits that the settings file did not. Verified independently
   for this review by re-running the set comparison, which returns a strict
   subset in one direction and empty in the other.
2. **The placeholder token is the only path form difference.** The snippet
   writes `/path/to/claude-configs-public/<path>` and the settings file writes
   `<path>`. Every comparison in this review normalises that prefix and nothing
   else. If a third form exists in a consumer workspace, the figures here do not
   describe it, which the design's Edge cases section already states.
3. **This commit changes no behaviour.** Two new files under `plans/`. The
   assumption is load-bearing for the pre-mortem's rollback claim being about a
   later commit rather than this one.

## Quantified claims

Every figure below was derived by running the comparison against the tree at
`origin/develop`, which is this branch's base, and not carried in from the
session that drafted the note.

| Claim | Value | How derived |
|---|---|---|
| snippet hook wiring, triples | 35 | `(event, matcher, command)` tuples read from `hooks/settings-snippet.json` |
| snippet hook wiring, distinct hooks | 29 | distinct normalised command paths in the above |
| repo settings wiring, triples | 27 | same over `.claude/settings.json` |
| repo settings wiring, distinct hooks | 24 | distinct normalised command paths in the above |
| hooks absent from the repo file | 5 | set difference on command paths |
| triples absent from the repo file | 8 | set difference on triples |
| triples present in the repo file and not the snippet | 0 | reverse difference, so the relation is a strict subset at both granularities |

The two granularities disagree by three, and the three are the `NotebookEdit`
matcher group for `write-guard.sh`, `branch-guard.sh` and
`ticket-propagation-guard.sh`. The group is absent from `.claude/settings.json`
in its entirety. Confirmed by printing the Write, Edit and NotebookEdit matcher
groups from both files side by side: the snippet has three groups, the settings
file has two.

## Findings

**S-1, P1: the design stated the comparison rule and then published a figure
from a weaker one.** The note argues that change 2 must key on
`(event, matcher, path)` triples rather than on paths, and its own audit matrix
was built by comparing paths. Running the rule the note asks for returns 8
missing entries where the note said 5, and the three it missed are a live
bypass: `NotebookEdit` is unguarded in this repository.

The mechanism is worth naming because it is not carelessness. The triple
requirement was reached by *correcting* two matcher claims in an earlier
revision, so the note had an argument for the rule and never executed it. An
argument for a rule and an execution of it produce text that reads the same. The
correction is in the artifact rather than only here, because the strongest
evidence for change 2's central design decision was sitting inside the document
that argued for it, and a reader who does not see that reads the triple
requirement as caution rather than as necessity.

**S-2, P2: the sibling-grep count was the path-keyed count.** N moves from 5 to
8. The gate's threshold is N >= 2 and the recommendation does not turn on the
value, so nothing downstream moves. It is recorded because the gate asks how
many instances of the failure shape exist, and a hook wired on two of its three
matchers is an instance; counting hooks rather than wirings answers a different
question than the gate asks.

**S-3, P2: the pre-mortem's falsification would have passed on the defect.** It
asked for a per-hook assertion that each command path resolves to an executable
file. All 24 wired hooks resolve, and all three `NotebookEdit` triples were
missing, so the check returns clean on the state it is meant to catch. Rewritten
to assert set equality over triples. This is the same shape as S-1 one document
downstream, which is what a restatement does with a defect in its source.

**S-4, P2: four restatements named a destination.** "the five hooks", "the 29
hooks", "hand-add the five hooks" and "the five entries" all encode a count that
S-1 moved. Rewritten to name the direction (the missing wiring, the missing
entries) with the count kept in one place. This is the recurring L-6 shape from
this epic's other artifacts, and it is cheaper to avoid than to chase.

## Peer review

writing-claims:3 -- every quantified claim carries its derivation. The table
above names how each figure was produced rather than asserting it, and the two
granularities are reported separately rather than reconciled into one number,
because reconciling them is what hid S-1.

writing-prose:2 -- a correction is recorded where the defect is, not only where
it was found. S-1 sits in the design note's Step 1 as a subsection rather than
being folded into the corrected table, since the corrected table alone would
leave a reader unable to tell a measured claim from an argued one.

writing-rules:7 -- N >= 3 requires an audit matrix. There are now two, one per
granularity, and the second is the one that carries the bypass.

## Lead review

The scope decision holds and is strengthened. Option B, hand-adding the missing
entries, was already rejected as the per-instance fix. S-1 shows it was worse
than that: anyone hand-adding would have worked from the list of five missing
hook names, and no such list contains the `NotebookEdit` triples, because those
hooks are not missing. Regeneration restores them without anyone having to have
noticed them. That is now the design's strongest argument for A and it was not
available when A was chosen.

What this unit does not settle, and says so: why the live settings file changes
mid-session, and the terminal-status passthrough at
`universal-mutation-gate.sh:211`, which stays on #702. Both are named in the
design's Scope boundary. The `NotebookEdit` bypass is in scope and is fixed by
change 1 without a separate ticket, because it is the same drift with the same
cause and the same remedy; splitting it out would be the isolate-one-at-a-time
rule applied to a defect that is not unrelated.

Risk accepted: this commit adds two documents and changes nothing executable, so
the `NotebookEdit` bypass stays open until the next unit lands. Filing it as its
own ticket would close it no sooner and would fragment the fix.

---
name: self-review
description: "MANDATORY pre-push / pre-PR-open / pre-PR-merge gate. Produce a structured artifact with Assumptions (including roles + Goal source verification via evaluate-ticket + Pre-author-inventory link + Evidence-predates-work block), Peer review against the shelves, and Lead review naming affirmative standards. The pre-push hook enforces trailer presence, structural completeness, artifact-predates-work, and the writing-rules:4 evidence-chain on any Trivial-change / Exemption blocks. Do NOT skip this skill; the form is checkable but the discipline is what binds."
user-invocable: true
---

# Self Code-Review

Run this skill before any action that pushes work outward: `git push`,
`gh pr create`, `gh pr merge` (including admin-merge). The artifact
this skill produces is the durable thing; the diff inspection is
ephemeral. CodeRabbit, GitGuardian, and sibling-session validation
compensate but do not substitute.

**Gate target repository:** `repo_root` names the task's TARGET clone/worktree, never the session CWD or the Craft workspace merely because it is a configs checkout. Declare actual task paths in `scope_paths`; run target commands with explicit paths/`git -C` when the session CWD is elsewhere. Companion gates use the same target repo and exact session/task identity. Scope rejections must be corrected, not bypassed with root copies.

## Why a written artifact

A "look at the diff" reminder is a habit, not a rule -- under context
pressure it gets skipped. A structured artifact with required sections
makes the questions impossible to skip without producing visible
absence. The artifact also exposes content to operator scrutiny in a
way that a mental gesture cannot.

## When self-review applies

Required before:
- `git push` on any branch (including feature branches pushing to
  their own PR).
- `gh pr create`.
- `gh pr merge` (including `--admin`).

A user instruction to "merge it" authorizes the destination, not skipping
required review. Inspect the source-bound artifacts first. Produce missing
self-review material within your authorized role and obtain any required
independent review from its owner; hold the merge until readiness is proven.
Do not request a waiver as the default response to missing evidence. Do not
backdate artifacts or claim pre-work evidence existed when it did not;
follow the applicable recovery process for a genuinely missed prerequisite.
Ask the responsible owner only for missing facts or authority, and continue
independent authorized preparation. Once existing authorization and its
conditions are satisfied, merge without asking for the same approval again.

Trivial-change escape: review is still required, but a no-findings
review on a genuinely trivial change is one valid output of the
artifact. The artifact-existence floor is non-negotiable; the
artifact's content scales with the work's scope.

## Self-reviewed linear promotion PRs

In Gitflow repositories, a `promote/*` PR to `main` is allowed as a
self-reviewed promotion vehicle only when all of these are true:

1. The promoted content has already landed on the develop-role branch.
2. The promotion branch's final tree matches the intended develop
   snapshot (for example, `git diff --stat origin/develop..HEAD` is
   empty after resolving the promotion merge).
3. The PR body includes `Self-Review-Source: <artifact>` pointing at
   the durable self-review artifact.
4. Required CI checks are green.

This is not a shortcut around `develop`; it is a way to make a
conflict-resolved promotion branch auditable when direct `develop` ->
`main` PRs are blocked by squash-merge ancestry. Repository branch
protection may still require a human approval, but this repo's policy
and CI should treat such PRs as self-reviewed and promotion-ready.

## Proportional review tiers

Run `python3 bin/review-risk.py --staged` before committing. The classifier is authoritative for the minimum tier; authors may escalate but may not downgrade. Record `Review-Tier: A|B|C` in every non-merge commit.

- **Tier A — trivial:** prose, plans, or generated evidence with no runtime behavior. Required: a short `Self-Review:` trailer, syntax/reference validation, and focused diff check. `Self-Review-Source:` is optional; pre-mortem and hostile review are not required.
- **Tier B — standard:** normal skill/rule changes, non-critical code/hooks, and documentation behavior. Required: `Self-Review:`, `Self-Review-Source:`, a focused artifact with `## Assumptions` and `## Test plan`, and relevant regression tests. Investigation, pre-mortem, and cross-provider review are not mandatory unless the classifier escalates.
- **Tier C — high risk:** enforcement gates, branch/release/deployment policy, credentials/auth/permissions, destructive operations, and review-policy changes. Required: the full artifact below, pre-mortem, actual `Hostile-Review:` evidence, negative tests, full suite, and canary/rollback evidence.

Unknown paths default to Tier B. Mixed changes take the highest tier. Missing classifier/policy fails closed. `[no-review]` is accepted only for machine-validated Tier A changes.

## Artifact format

Before pre-implementation comprehension or authoring a Tier B/C artifact, read [the canonical template and field contract](artifact-contract.md#artifact-format). The complete fenced template and field requirements live there; this link is a required preparation step, not optional reference material. Tier A retains its short record; Tier B/C requirements and the selected project's procedure remain authoritative.

### Gate 1: Syntax check

Before the self-review artifact is considered complete, **every modified
file must pass its language's syntax check.** This is the non-negotiable
minimum -- a file that doesn't parse is worse than the bug it was fixing.

For Python changes:
```bash
git diff --name-only HEAD~1 | grep '\.py$' | xargs -I{} python3 -c "import ast; ast.parse(open('{}').read())"
```

For batch changes (>3 files), run this on ALL modified files, not just
the ones you think you changed meaningfully. Paste the output (or
"all N files parse") in the Peer review section.

**Evidence format in Peer review section:**
```
Syntax check: `ast.parse` on N changed `.py` files → all parse clean (exit 0)
```

If no `.py` files were modified, state "Syntax check: N/A (no .py changes)"
explicitly rather than omitting silently.

**Incident justification:** The SU-1 broad-except sweep (commit 31286bf,
2026-05-28) introduced a SyntaxError in `geocoding.py` that broke the
module's import. The self-review artifact existed, the trailers were
present, but nobody asked "does it parse?" The file was broken on develop
for 24+ hours. This floor exists because the most basic mechanical check
is also the most commonly skipped.

### Gate 2: Test suite execution

Before push, run the project's declared test suite. At minimum, run its smoke or
quick-pass checks. Use the actual project test runner; the pytest examples below
do not impose pytest on other projects. Paste the command, exit code and summary
in the Peer review section.

For siege_utilities:
```bash
pytest tests/ -x -q -o "addopts=" -m smoke 2>&1 | tail -5
```

For a project that uses pytest but has no `smoke` marker, run collect-only to verify imports:
```bash
pytest --co -q -o "addopts=" 2>&1 | tail -5
```

**The Junior's rationalization is the failure mode.** "It's doc-only,"
"it's config-only," "it's test-only" — these are exactly the categories
where skipping tests feels efficient and causes the most damage. A
config change to `pyproject.toml` can break the test runner. A new
notebook can import a renamed function. A test-only change can conflict
with existing fixtures. The gate applies to ALL pushes, not just code
pushes.

**Evidence format in Peer review section:**
```
Test suite: `pytest tests/ -x -q -o "addopts=" -m smoke` → N passed in Xs (exit 0)
```

An empty or missing test-suite line when a push is pending is a visible
absence — the same enforcement shape as Gate 1.

**Incident justification:** Session 260529-golden-shark merged 4 PRs to
main (tickets #816, #580, #970, #572) without a single `pytest`
invocation. Each was rationalized as doc-only or config-only. The
existing mechanical floor (Gate 1: syntax check) did not catch this
because it only verifies parse-ability, not import-ability or behavioral
correctness. Gate 2 closes the gap.

### Gate 3: Doc build verification

If ANY file under `docs/` was modified in the diff, run the project's declared
documentation builder before push. For a plain-Markdown repository without a
builder, run its actual documentation/reference validation instead; do not invent
a Sphinx dependency or a new approval request. Preserve verification and report
the real command, exit code and warning count in the Peer review section.

For Sphinx projects:
```bash
sphinx-build -q docs/source/ /tmp/docs-verify 2>&1 | tail -3
```

The gate is **"does it build"** (exit code 0), not "zero warnings."
Known noise (PEP 562 duplicate object descriptions, missing optional
intersphinx targets) does not block. New warnings introduced by THIS
diff should be noted.

**Evidence format in Peer review section:**
```
Doc build: `sphinx-build -q docs/source/ /tmp/docs-verify` → succeeded, N warnings (exit 0)
```

If no files under `docs/` were modified, this gate does not apply —
state "Doc build: N/A (no docs/ changes)" explicitly rather than
omitting silently.

**Incident justification:** Same session (260529-golden-shark) created 3
new RST files for #970 (conf.rst, development.rst, oss_unity_catalog.rst),
added toctree entries, and merged without running `sphinx-build`. A
toctree entry referencing a nonexistent file would have broken the
deployed GitHub Pages docs on the next main push.

### Gate 4: Notebook API verification

If ANY notebook (`.ipynb`) is in the diff, verify every library call
in the notebook against the actual source before push. This is not
"run the notebook" — it is "grep the library for the methods the
notebook calls."

For each `siege_utilities` function or method call in the notebook:
1. Identify the class or module being called
2. Grep the source for that method name on that class/module
3. Verify parameter names match the actual signature

For narrative claims (markdown cells describing what a function does):
1. Read the actual function's docstring and source
2. Confirm the narrative matches actual behavior
3. Check that cell outputs are consistent with the narrative

**Evidence format in Peer review section:**
```
Notebook API check: N calls verified against source in M notebooks (0 mismatches)
Per-call evidence (paste actual grep commands and output):
- `grep -rn "method_name" siege_utilities/module/` → file:line confirmation
- `grep -rn "other_call" siege_utilities/other/` → file:line confirmation
```

The per-call evidence is what distinguishes mechanical verification from
self-reported compliance. A summary count ("N calls verified") is necessary
but not sufficient -- the pasted grep commands make fabrication visible to
the Adversary.

If no notebooks are in the diff, state "Notebook API check: N/A (no
notebook changes)" explicitly.

**The failure mode is fabrication, not malice.** The Junior writes
a notebook narrative describing what a function *should* do based
on the function name, without reading the source. The narrative
becomes documentation. Users copy the pattern. The function doesn't
do what the notebook says. This is an SU-3 violation (demo code
ships with the package) compounded by SU-2 (does it do what it
says?).

**Incident justification:** Session 260603-golden-shark hostile review
found 3 S2 bugs in notebooks: `CredentialManager.get()` doesn't
exist (should be `get_credential()`); `normalize_name_v1` narrative
claims name reordering but function only lowercases; entity
identification outputs "All match: False" while narrative implies
matching. All three were written against imagined APIs.

### Gate 5: Review-gate check

Before push, resolve the owning task's `review-gate.json` beside
`$CRAFT_SESSION_DIR/tasks/<task-slug>/think-gate.json`. Use the full ticket
reference (or explicit task id) and matching session metadata. Do not inspect
workspace-root or another task's review signal. Multiple tasks in one session
have independent review/artifact state. Legacy session-level signals are
read during migration; new writes are task-keyed only.

If this task's branch has moved beyond `reviewed_commit` after a request-changes
review, re-fire review on the current code. Update only this task's signal;
approval does not clear other tasks' review requirements. Resolve targets by
`scope_paths` or explicit `CCP_TASK_ID`; unscoped mutations fail closed while
positively classified reads bypass gate lookup.

**Evidence format in Peer review section:**
```
Review-gate: no signal file (N/A) | cleared (approved) | re-reviewed at <commit>
```

If no review-gate signal exists, this gate does not apply — state
"Review-gate: N/A (no signal file)" explicitly.

## Pre-author-inventory field

Read [the artifact field contract](artifact-contract.md#pre-author-inventory-field) before filling this field. It retains the investigation, pre-mortem, hostile-review, declaration, exemption and adversarial-shape requirements and their actual applicability conditions.

## Investigate-artifact and Pre-mortem-artifact fields

Apply the [exact field conditions](artifact-contract.md#investigate-artifact-and-pre-mortem-artifact-fields).

## Trivial-investigation declaration

Use the [canonical declaration and default-deny categories](artifact-contract.md#investigate-artifact-and-pre-mortem-artifact-fields); moving the contract does not add an exemption.

## Hostile-review-artifact field

Apply the [independent review artifact contract](artifact-contract.md#hostile-review-artifact-field).

## Hostile-review-waiver

Only the [existing scoped waiver conditions](artifact-contract.md#hostile-review-artifact-field) apply; do not request a waiver by default.

## Trivial-change declaration (when no ticket cited)

Use the [existing declaration contract](artifact-contract.md#trivial-change-declaration-when-no-ticket-cited) where applicable.

## Exemption blocks

Apply the [Reason/Evidence/Falsification contract](artifact-contract.md#exemption-blocks), not a free-text escape.

## Adversarial shape audit

Read the [four-field audit contract and applicability](artifact-contract.md#adversarial-shape-audit) when the diff models external shapes.

## Domains and roles

Before a pre-implementation adversarial pass or Peer/Lead review, read [review methods and domain/role guidance](review-checklists.md#domains-and-roles). Use the actual target project and assigned role; selected project replacement procedures retain their own contract.

## Peer review uses the shelves

Apply the [canonical shelf review method](review-checklists.md#peer-review-uses-the-shelves), not an empty list of shelf names.

## Conditional review routing

Read [activation, routing and domain checklists](review-checklists.md#conditional-review-routing) and apply the sections activated by the actual diff. Unrelated domain detail is not a new requirement.

## Lead review: the Lead's adversarial pass

Read and perform the [Lead phases](review-checklists.md#lead-review-the-leads-adversarial-pass), including external verification and findings triage.

## Findings

Use the [canonical findings contract](review-checklists.md#phase-c-findings-triage): unresolved blocking findings stop their dependent operation; follow-up and evidence rules remain required.

## Recursion

The artifact makes claims about the diff ("no regressions," "all sites
fixed," "loop closed"). `_writing-claims-rules.md` 1-4 fire on those
claims as they would on any other agent-produced text:

- writing-claims:1 -- grep before declaring fix complete.
- writing-claims:2 -- countable claims need the falsifying grep in the
  same artifact.
- writing-claims:3 -- unquantified completeness claims grounded too.
- writing-claims:4 -- coining new framework names in the review
  requires existing artifact backing.

`_writing-prose-rules.md` applies to the artifact's typography. The
review's language is subject to the same discipline as any other
prose the agent produces.

This recursion prevents the artifact from becoming theater. An empty
"no concerns" verdict is itself a writing-claims violation, visible
to anyone reading the artifact.

## Quantified claims section is structural enforcement

The `## Quantified claims` section makes writing-claims:8 structurally
visible in the artifact. Every specific count in the PR body or commit
messages ("21 subpackages," "15 import sites," "all 4 engines") must
appear in this section with the command that produced the number.

The section catches two failure modes:

1. **Fabricated counts.** The agent recalls "about 20" and writes "21"
   without running `ls | wc -l`. The section forces the command to run.
   When the command returns 25, the claim must be revised before stating
   it.

2. **Scoping errors from wrong counts.** A migration PR claims "Updated
   all 15 internal import sites" -- true for source files, but the grep
   that produced 15 excluded test files. The section forces the full
   grep to appear, making the scope visible: "15 source sites updated;
   28 test-file sites remain (tracked in #NNN)."

An empty Quantified claims section is acceptable only when the PR body
and commit messages contain no specific integer counts. The hook
validates section presence; content completeness is operator-auditable.

## Post to ticket and continue (hard gate)

When the self-review artifact is complete, post it to the ticket NOW. Use `gh issue comment <number> --body "..."` or equivalent. The session copy is a working draft; the ticket comment is the canonical copy.

Do not push until the self-review is on the ticket. **Then push and create the PR.** The pipeline is self-driving: produce the artifact, post it, advance. Do not wait for external approval to push -- the self-review IS the approval gate.

## Cross-environment enforcement

Enforcement depends on the actual host, installed generation and invoked entrypoint. Source presence is not proof of delivery, and instruction prose alone is not a mechanical gate.

- Claude-compatible tool callbacks can run the installed `hooks/git/self-review.sh` through supported settings. CraftAgents requires its actual supported workspace/project registration and host callback delivery; installed routing may evaluate more than one hook stack. Verify the real host and operation instead of assuming universal delivery or zero enforcement.
- Native Git uses the configured `.githooks/commit-msg` and `.githooks/pre-push` adapters where installed. They check commit records and pushed commit ranges independently of an agent's tool callbacks. Local hook installation is not immutable protected acceptance or proof of every PR API route.
- Required protected checks and branch policy remain separate. A missing tool hook does not waive review, artifacts, trailers or any selected project requirement; perform the required procedure through the supported route and report the actual enforcement gap.

Historical reports of absent Craft/native hooks described earlier installations. They are not the current universal contract. Backend or provider parity still requires actual installed verification.

## Goal source is load-bearing

If the goal field is sourced from the diff itself (PR title, commit
subject), the artifact can structurally satisfy writing-claims while
substantively reviewing nothing -- "Goal: implement X. Diff implements
X. No concerns." is a tautology dressed as a claim. Sourcing the goal
from a pre-existing artifact (ticket filed before work began, design
note, user-request quote) makes "diff implements goal" a non-trivial
claim instead of a restatement.

Earlier callback implementation notes described field-presence and provenance checks as v1/v2 phases. Those labels are history, not proof of which checks today's installed tool callback or native adapters implement. Inspect the current installed owners named below, and provide the [required goal-source and artifact evidence](artifact-contract.md#artifact-format) regardless of a parser's narrower mechanical coverage.

## Trailers and hook enforcement

Every non-merge commit must carry its validated tier and review record. Tier B/C also require the artifact pointer; Tier C requires independent hostile-review evidence:

```
Review-Tier: <A | B | C>
Self-Review: <one-line summary of the review pass>
Self-Review-Source: <required for B/C; path or ticket pointing at the artifact>
Hostile-Review: <required for C; path or ticket pointing at independent review>
```

These match the existing `Verified-by:` trailer idiom that
writing-claims:2 already requires. The tool callback inspects the commit
visible before the command runs; the installed native pre-push adapter checks
the actual pushed commit range. These are different contracts. Missing required
records are blocking where the corresponding adapter is installed and invoked.

### Current enforcement owners

Inspect the actual installed `hooks/git/self-review.sh` tool callback, `.githooks/commit-msg`, and `.githooks/pre-push` with its native range adapter for the entrypoint being used. The [authored artifact contract](artifact-contract.md#artifact-format) remains required; an adapter checking fewer fields does not waive the rest. Protected policy is a separate acceptance boundary. Source files describe available mechanisms, not proof that a host invoked them.

### Historical implementation ledger

The v1/v2 notes below record earlier callback implementation stages and planned checks. They are retained as history, not a current universal coverage matrix or proof that a named check is implemented or absent in today's installed generation. Use the current owners above for that factual question and the canonical contract for what the author must provide.

**Historical v1 callback implementation notes:**

- `Review-Tier:` and `Self-Review:` are present; the declaration cannot be below the classifier's result.
- Tier A may stop at the short trailer record. Tier B/C require exactly one `Self-Review-Source:` value (multiple = ambiguous, blocked). Tier C also requires `Hostile-Review:`.
- If a Tier B source is a file path: it exists and has `## Assumptions`, `## Test plan`, and a non-empty `Goal source:`. Tier C retains the full four-section structure (`## Assumptions`, `## Peer review`, `## Lead review`, `## Quantified claims`).
- **v1.1**: If `Goal source:` value is itself a file path, its mtime
  must not be newer than the review artifact's mtime (catches goal-
  source-written-after-the-work post-hoc-justification pattern).
- **v1.2**: `Pre-author-inventory:` field present and non-empty
  in the Assumptions section. `NONE` accepted only when a
  `Trivial-against-state:` declaration is also present.
- **v1.3 (claude-configs-public#239)**: `Investigate-artifact:` and
  `Pre-mortem-artifact:` fields present and non-empty in the Assumptions
  section. `TRIVIAL` accepted only when a
  `## Trivial-investigation declaration` block is also present with all
  four required fields (Category / Cannot produce error / Evidence /
  Falsification). If the value is a file path, the file must exist.
- **v2 (claude-configs-public#146)**: If the artifact file lives in a
  git repo, the artifact's first-added commit must be an ancestor of
  the work commit being pushed (`git log --diff-filter=A --follow` +
  `git merge-base --is-ancestor`). Closes the retroactive-trailer
  loophole that lets agents push first, write the artifact later, and
  satisfy the form check while bypassing the discipline. Defense in
  depth alongside v1.1's mtime check; this one is touch-resistant.
- **v2 (claude-configs-public#146)**: If the artifact contains a
  `## Trivial-change declaration` or `## Exemption:` block, each block
  must have all three fields (Reason / Evidence / Falsification) AND
  the Evidence field must contain a verifiable observation token
  (fenced code block, file path with extension, git command, stat/
  count, or URL). Free-text assertions fail. Delegated to
  `scripts/discipline/check-trivial-claim.sh`.
- Assumptions section names at least one domain from the canonical
  set (software engineering / data engineering / data analysis &
  visualization) and declares geospatial cross-cut (yes / no).
- Peer review section cites at least one shelf
  (writing-code / writing-tests / writing-claims / writing-prose /
  writing-releases / writing-rules).

**Historical v2 follow-up list (not a current absence claim):**

- Goal source does NOT point at the commit being pushed AND was filed
  before the commit timestamp. **v1.1 lands the partial mtime-based
  check** for file-path-shaped goal sources (block if goal-source mtime
  > review-artifact mtime -- catches post-hoc-justification patterns).
  Heuristic: `touch` defeats it; stronger check needs git history which
  session-scoped plans/ files don't have. **v2 still owed:** ticket-
  shaped sources (`#NNN`) validated via `gh issue view --json createdAt`
  against the commit timestamp; SHA / commit-subject-quote source
  detection.
- Lead section's domain-tagged affirmative-standard format
  (`In <domain>: <standard> holds because <evidence>`).
- `detect-ai-fingerprints` scan against the source artifact.
- `Verified-by:` trailers (or grep-output equivalents) for any
  countable / completeness claim made inside the source artifact.
  (Tracked as separate issue -- see PR body for link.)
- Ticket-reference source values (e.g. `#123`) validated against the
  issue tracker (currently passes as-is; only file-path sources are
  structurally checked).
- Merge-time re-verification on `gh pr merge` -- the diff-since-last-
  review can change between push and merge if fixup commits land in
  between, so the merge command should re-check the trailer on the
  PR branch's latest commit at merge time.

These phase labels do not certify complete enforcement. Structural checks and human review quality are different; inspect actual adapter behavior and preserve the applicable artifact/review requirements.

## Known limitations (recoverable, document-the-workaround posture)

The tool-callback hook fires at PreToolUse -- BEFORE the bash command runs -- and inspects
the latest commit at that moment; the native range adapter is a different entrypoint. This produces several documented false
positives the agent can recover from by adjusting invocation shape:

- **Chained `git commit -m "..." && git push`.** The hook sees `git push`
  in the command and inspects HEAD. At that moment HEAD is the PRE-commit
  HEAD (the in-flight commit hasn't happened yet), so the trailer pair
  from the imminent commit isn't visible. The hook blocks. **Workaround:**
  split into two separate Bash invocations -- first `git commit -m "..."`,
  then `git push origin <branch>` as a separate call. Once the commit
  lands on HEAD, the push's hook check sees the trailers. Issue #107.
- **Quoted-data trigger diagnostics.** Some installed tool-callback parsers can overmatch `git push`, `gh pr create` or `gh pr merge` inside prose. Verify the actual parser in a bounded disposable fixture before claiming that case fixed. For ordinary ticket prose, use a supported body-file argument with the file in its actual task-owned artifact location. Use unambiguous separate invocations for real commands and preserve their target/task ownership. Do not relocate real scripts or artifacts outside the repository merely to escape branch or review checks.
- **Multi-statement commands with `cd`.** Mirrors branch-guard discipline
  (#101): if the command has more than one `cd` OR contains chained
  statements (newline / `;` / `||`) with at least one `cd`, the hook
  yields rather than risk evaluating the wrong repo. Same workaround:
  split into separate Bash invocations.
- **Host-specific callback gaps.** CraftAgents and other hosts require their actual supported registration and callback delivery; no generic host name proves that a hook ran or did not run. Follow the same applicable tier, ticket/artifact and trailer requirements even when a callback is unavailable. Verify installed delivery separately, and document a real gap without pretending that native Git checks cover every PR API operation.

These are conservative-bias trade-offs. The hook prefers a recoverable
false positive over a silent false negative; "split into separate calls"
is the standard recovery pattern across the hook family.

## Artifact destination

**If the work has a ticket, the self-review goes on the ticket. This is not optional.**

Post the self-review artifact as a comment on the ticket, or commit it to the repo and link from the ticket. The `Self-Review-Source:` trailer must point to the durable location (ticket comment URL or repo path), not a session plans folder. The local file is a working draft; the ticket is the canonical home.

The self-review is evidence that the work was reviewed. Evidence that can't be found from the ticket is evidence that doesn't exist.

## Three-layer separation

- **Hook says WHAT.** The pre-push hook enforces presence of the
  trailers and structural completeness of the artifact.
- **Memory says WHEN.** `feedback_self_code_review.md` is the always-on
  nudge: do self-review before push / PR / merge.
- **Skill says HOW.** This file is canonical. Memory and hook point
  at it.

## Origin

Designed across session 260502-vital-channel on 2026-05-16 with
sibling review from 260502-pure-vista. Operator-promoted from the
session's `plans/self-review-rule-design.md` v2.

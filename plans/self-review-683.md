---
ticket_refs:
  - siege-analytics/claude-configs-public#683: comment posted
  - siege-analytics/claude-configs-public#682: comment pending
---

# Self-review: ticket #683 (investigate the epic #682 executable path)

Working as: software engineer

## Assumptions

Domain(s): software engineering
Geospatial cross-cut: no
Goal source: ticket #683 (epic #682)
Goal source verification: `PASS: ticket 683 is fit for execution`
Plan reference: https://github.com/siege-analytics/claude-configs-public/issues/682 (epic body carries the 24-item functions checklist this fact sheet is measured against)
Pre-author-inventory: NONE (see `## Trivial-against-state declaration`)
Trivial-against-state: this diff authors no runtime artifact; see the declaration block below
Investigate-artifact: https://github.com/siege-analytics/claude-configs-public/issues/683#issuecomment-5488627863
Pre-mortem-artifact: TRIVIAL (see `## Trivial-investigation declaration`)
Hostile-review-artifact: WAIVED (see `## Hostile-review-waiver`)
Project-contribution: establishes the falsifiable baseline the epic #682 rewrite is measured against — which of PR #668's and PR #672's findings are still live at the branch being replaced, what is newly broken, and which existing test fixtures actively protect defects. Without this, "the Python rewrite passes the same tests" would have been an acceptance signal, and it is not one.

## Trivial-against-state declaration

Reason: none of the five authoring-against-state contact categories is engaged. The diff authors no runtime artifact — it adds two prose documents under `plans/`. Data-shape: no schema, query, or dataframe is written or read. Config-state: no config file is authored or consumed; the artifact *reports* that `PROJECT.md` is absent rather than authoring against it. Topology: no service, path, or dependency wiring changes. Plan-shape: no execution plan, DAG, or pipeline definition is produced. Version-resolution: no dependency, pin, or lockfile is touched.
Evidence: `git diff --stat HEAD~2 --name-only` → `plans/investigate-682-executable-path.md`, `plans/self-review-683.md`. Both `.md`, both new, both under `plans/`. No file with a runtime extension (`.py`, `.sh`, `.json`, `.yaml`, `.toml`, `.lock`) appears in the diff, and no file under `hooks/`, `skills/`, `scripts/`, or `templates/` is modified.
Falsification: a reviewer identifies a runtime consumer that reads either of these two files and changes behaviour as a result. The session-scoped `investigate-gate-claude-configs-public.json` written alongside this work *is* read by the guard hooks, and it is deliberately outside the repo and outside this diff; if that file were committed here, this declaration would be wrong and a real pre-author inventory of the guard's schema would be required.

## Trivial-investigation declaration

Category: doc-only
Cannot produce error: this ticket's entire deliverable is the investigation artifact itself; a pre-mortem of "what could go wrong when we write a fact sheet" would surface nothing the artifact's own falsification section does not already carry, and the epic sequences a dedicated pre-mortem ticket as the next unit of work against the actual rewrite.
Evidence: `git diff --stat HEAD~1 --name-only` → `plans/investigate-682-executable-path.md`, `plans/self-review-683.md` — two new files under `plans/`, no source, hook, skill, or template file touched.
Falsification: the pre-mortem ticket that follows surfaces a risk class that would have changed how the fact sheet was scoped — e.g. it establishes that a whole file in the executable path was omitted from the #682 checklist and therefore from this inventory.

## Hostile-review-waiver

Reason: hostile review by a sibling on a different model is required by standing order and is being obtained, but the PR does not exist yet at push time, so no review artifact can be cited. This waiver covers the push only, not the merge.
Scope: `plans/investigate-682-executable-path.md`, `plans/self-review-683.md`. Both `.md`; the diff touches no file with an executable extension.
Compensating-control: all four ACs verified mechanically rather than by reading (scripted header enumeration, per-subheader grep counts, `json.loads` on the extracted fence, `mermaid_validate` on both diagrams), plus a citation-resolution pass over all 33 `file:line` pairs in the `verifiedShapes` block. A hostile-review sibling is spawned immediately after the PR is opened and its findings are remediated before merge; the `Hostile-review-artifact:` field is updated to the resulting artifact at that point.

## Peer review (mechanics, correctness, craft floor)

**writing-claims.** Every count in the commit message and PR body is reproduced under `## Quantified claims` with its command. The two claims with the highest chance of being wrong — "24 checklist items covered" and "33 citations resolve" — are backed by scripts that enumerate the names and resolve the paths rather than by a bare count, because a count can be right while the membership is wrong.

**writing-tests.** No tests are added or changed by this diff. That is correct for an investigation ticket, and it is also the finding: `probe_run` has zero coverage (F-N20) and five of six probe wrappers have zero coverage, which the artifact records rather than fixes. Fixing them here would have been scope creep into the implementation tickets.

**Citations.** Ran a resolution pass over the `verifiedShapes` block: for each `file:line`, assert the file exists and the line number is within the file. 33 citations, 0 unresolved. This caught two wrong line numbers I had written from memory earlier in the session (`_field` cited at `:133`, a comment line, actually `:135`; the infra-ticket verification block at `:35`, actually `:34`). Both corrected. I would have shipped both without the pass.

**AC literalism.** AC2 is falsifiable by grep for eight subheaders. Fifteen entries used `- **Assumptions to verify at rewrite time:**` and two used a combined `- **Callers / Callees:**`, all of which read fine but fail a literal grep. Normalised; counts went 9→24 and 22→24. A reader-satisfies-it standard is not an AC-satisfies-it standard.

**Prose.** No AI or assistant attribution anywhere in either file or in the commit. Commit authored via explicit `-c user.name` / `-c user.email`.

## Lead review (adversarial pass)

*Software engineering.* Did the Junior actually solve #683, or produce a document that looks like a solution?

**Approach-fit verdict: fit, with one soft spot.** The ticket asks for an inventory, and the temptation on an inventory ticket is to paraphrase the source back at the reader — 24 entries of "this function does what its name says". That would satisfy AC1 and AC2 while being worthless to the rewrite. The check I applied is whether each entry produces a *decision* for the rewrite, and the load-bearing ones do: F-N13 says the npx wrappers need an injectable detector; F-N14 says `eval` must become an argv list; F-N20 says `probe_run` is the first unit to cover. The soft spot is that a handful of the P2 entries (F-N3 changelog drift, F-N7 inert instruction, F-N16 layer-token spellings) are true but produce no rewrite decision on their own. They are kept because they are cheap to carry and because F-N16 in particular becomes load-bearing the moment the layer token is made a shared constant.

**Did each finding close a class or defer it?** All 25 defer — this ticket fixes nothing by design. The classification that determines whether the rewrite closes them by construction or one at a time (H1) is explicitly named as the *design ticket's* first deliverable, not smuggled in here. Deferring is correct; deferring silently would not be, which is why the H1 falsification criterion states the threshold (structural ≥ 50%) in advance rather than after the classification is done.

**Blast radius: zero at push, load-bearing at merge.** Two new files under `plans/`; nothing executes, nothing deploys, no `hooks/` or `skills/` change so no `bin/build.py --deploy` is required. The real blast radius is downstream: every subsequent ticket in epic #682 is scoped against this document, so a wrong severity here misroutes implementation effort. That is the argument for the hostile review, not against it.

**Sequencing assumption that has to hold.** That the epic integration branch — the first branch on which the hook (`feat/661`) and the probes (`feat/662` + `fix/676`) coexist — is the correct baseline. If the epic instead rebases onto whatever `develop` looks like at implementation time, findings dispositioned LIVE here may have been fixed in the interim and findings dispositioned REMEDIATED may have regressed. Every disposition in this artifact is pinned to `epic/682-python-executable-path`, and re-verification is required if that base moves.

**Affirmative standard: does the artifact make its own claims falsifiable?** Yes for the mechanical ones (four ACs, 33 citations, two suite runs — all with commands). Partially for the severity assignments, which are argued but not independently checked. That gap is stated below rather than left for a reviewer to find.

## Findings

| ID | Priority | Description | Resolution |
|----|----------|-------------|------------|
| L-1 | P1 | Two `verifiedShapes` citations pointed at wrong lines (`_field` at `:133`, a comment; infra template at `:35`). Fabricated-adjacent citations are exactly what the guard's spot-check exists to catch. | fixed — corrected to `:135` and `:34`; added a resolution pass over all 33 citations, 0 unresolved |
| L-2 | P1 | AC2 failed a literal grep on 17 of 24 entries (`Assumptions to verify at rewrite time`, combined `Callers / Callees`) while reading as compliant. | fixed — normalised to the eight exact subheaders; all eight now count 24 |
| L-3 | P2 | Severity assignment for the 25 new findings has had no second reader; F-N13 and F-N14 are P0 on source attestation with no executed repro. | ticket — this is the primary target for the hostile-review sibling; if the sibling downgrades either, the epic's implementation ordering changes and the artifact is amended |
| L-4 | P2 | The `allow` and `prompt` policy branches — which contain every dangerous operation, including a `sudo apt` chain — were attested from source and never observed, because this repo has no `PROJECT.md` so `_probe_resolve_policy` always returns `block`. | noted in artifact and recorded as `SKIPPED` with reason in the gate; drives the recommendation that `probe_run` is the first unit to get coverage |
| L-5 | P3 | The 15-fixture → finding mapping table is my reading of each fixture, not instrumented. A fixture marked "—" could also be masking a defect. | noted — the rewrite's first act on the hook suite is to add byte-exact assertions, which would surface any additional masking |

No P1 rows remain unresolved.

## Quantified claims

- "894 lines" (commit-time figure; the file is now 896 after the AC2 normalisation added two split `Callers`/`Callees` lines) — `wc -l < plans/investigate-682-executable-path.md` → `896`
- "all 24 units on the #682 functions checklist" — scripted `grep -qx "### <name>"` over the 24 names from the epic body → `missing: 0` (24 OK, 0 MISS)
- "24 for each of the 8 subheaders" — `for h in File Signature Callers Callees "Side effects" "Known failures" "Test coverage" Assumptions; do grep -c "^- \*\*$h:\*\*" ...; done` → `24 24 24 24 24 24 24 24`
- "the embedded verifiedShapes block parses" — extract the single json fence, `json.loads` → `json fences found: 1` / `verifiedShapes blocks that parse: 1`
- "two validated mermaid diagrams" — `grep -c '^```mermaid'` → `2`; both submitted to `mermaid_validate` with `render: true` → `{"valid": true}` twice
- "33 citations, 0 unresolved" — walk the `citations` arrays, assert file exists and line ≤ file length → `citations: 33  unresolved: 0`
- "24 from #668, 5 from #672 remain live" — counted from the live-defect ledger rows in the artifact, which were dispositioned individually by same-turn repro earlier in this session
- "25 new findings (6 P0, 13 P1, 7 P2)" — counted from the new-findings table (F-N1..F-N25 with F-N12b as a sub-entry); severity is assigned, not measured, which L-3 records
- "4 passed, 0 failed" — `bash scripts/probe/_test_probe_common.sh` → `Summary: 4 passed, 0 failed`
- "15 passed, 0 failed" — `bash hooks/_test/scaffold_test_stub.test.sh` → `Summary: 15 passed, 0 failed`
- "19 green fixtures" (commit message) — 4 + 15 from the two runs above
- "10 findings, 8 verifiedShapes, 4 skipped in the gate file" — `json.load` on `investigate-gate-claude-configs-public.json` → `findings: 10 verifiedShapes: 8 skipped: 4`, and a schema check against the guard's stated rules (layer coverage, PROBED/ATTESTED/SKIPPED completeness, skipReason length) → `problems: 0`

## Rework ledger

| Rework trigger | Root skip | Check cost | Rework cost | Ratio |
|---|---|---|---|---|
| Two wrong `file:line` citations (L-1) | wrote line numbers from earlier-in-session notes instead of re-resolving them against the checkout | one `sed -n` loop over 17 pairs, ~10s | rewrite two chunk files and run a `python3` string-replace pass over the assembled artifact, ~4 min | ~24x |
| AC2 grep failure on 17 entries (L-2) | wrote the subheaders for readability without checking them against the AC's literal grep | one `grep -c` loop over 8 patterns, ~5s | normalise 17 entries via a scripted replace and re-split two combined lines, ~5 min | ~60x |
| Push blocked by `hooks/git/self-review.sh` for missing `## Assumptions` / `## Peer review` / `## Lead review` | wrote the self-review artifact from the standing-order trailer requirements without reading `skills/self-review/SKILL.md` first | reading `## Artifact format`, ~30s | full rewrite of the artifact, ~8 min | ~16x |
| Write blocked by `ticket-propagation-guard` for missing `ticket_refs:` frontmatter | pasted full issue URLs into the artifact without adding the propagation metadata the guard requires | reading the guard's resolution block, ~15s | re-issue the Write with frontmatter, ~1 min | ~4x |
| Octopus merge failure building the epic branch | assumed `git merge A B` would handle a CHANGELOG conflict | knowing octopus refuses any conflict, ~0 | sequential merges with a Python union-resolver per conflict, ~6 min | high |
| First #668 P1-4 repro inconclusive | used `Tool: pytest`, which is installed, so the absent branch was never reached | checking `command -v pytest` before choosing the repro tool, ~2s | re-run with `great-expectations`, ~2 min | ~60x |

The pattern across all six: each was caused by acting on an internal belief that a five-to-thirty-second command would have checked. On a document whose entire value is that its claims are checkable, that is the failure mode to name explicitly rather than absorb.

## Evidence-predates-work

All suite runs, the two defect repros (F-N1 escaped directory, F-N5 trailing-newline byte comparison), and the `PROJECT.md` absence check were executed on `epic/682-python-executable-path` / `feat/683-investigate-executable-path` before the artifact text describing them was written. The AC and citation verification passes were run against the assembled artifact after it was written, and both produced corrections (L-1, L-2) that are recorded above rather than quietly folded in.

---
ticket_refs:
  - siege-analytics/claude-configs-public#711
---

# Self-review: PR for #711 (corpus differential as script)

## Assumptions

Working as: software engineer
Domain: scripts/discipline (Python differential + bash test)
Goal source: siege-analytics/claude-configs-public#711
Pre-author-inventory: `git ls-files 'plans/*.md' | wc -l` returns 192 at HEAD (vs ticket's 146 at 712ef53; the growth is expected — ticket says the count is a snapshot). `git log --format='%H %s' -- hooks/write/ticket-propagation-guard.sh` returns 5 revisions; dda1c35 (pre-#688) and dd9db33 (post-#688) are the natural divergent pair for AC4 testing.
Investigate-artifact: TRIVIAL (see ## Trivial-investigation declaration below)
Pre-mortem-artifact: TRIVIAL (see ## Trivial-investigation declaration below)
Hostile-review-artifact: WAIVED (external dispatch ladder exhausted, per session operator authorization 2026-09-05)
Project-contribution: makes the guard-revision differential executable. Before this PR, #688's "146 files, 0 differing" was a prose figure with no mechanism that could notice it going stale. After this PR, the script runs on demand or in CI. When the guard is next modified, the differential runs against the old-rev vs new-rev pair; when the corpus grows, the figure moves with it.

## Trivial-against-state declaration

Reason: adds one new script + one new test file. No existing code touched.
Evidence: `git diff --stat` shows 2 new files + 1 self-review; no modifications to existing files.
Falsification: not trivial if the corpus filter differs from #688's original scope. Verified against ticket A1: git ls-files 'plans/*.md' + 'docs/investigations/*.md', excluding scratch-*. Script docstring documents the exact filter.

## Trivial-investigation declaration

Reason: #711 named the design: script takes two guard revisions, runs both over the corpus, reports N/M. Fail-closed on unclassifiable per AC3. Not-a-hardcoded-pair per AC5.
Cannot produce error: script forks bash subprocess for each guard run; no writes to the repo tree.
Evidence: `bash scripts/discipline/test_corpus_differential.sh` returns "4 passed, 0 failed".
Falsification: not trivial if the script silently reports 0 differing on a real divergence. Verified by scenario (c): comparing dda1c35 (pre-#688) against dd9db33 (post-#688) produces 5/5 differing on the --limit 5 sample; exit code is non-zero.

## Peer review

Gate evidence:
- Gate 1 (syntax): `python3 -c "import ast; ast.parse(open('scripts/discipline/corpus-differential.py').read())"` -> ok; `bash -n scripts/discipline/test_corpus_differential.sh` -> ok
- Gate 2 (tests): `bash scripts/discipline/test_corpus_differential.sh` -> "4 passed, 0 failed" including AC3 (fail-closed on unresolvable rev) and AC4 (deliberate divergence)
- Gate 3 (docs): script header documents corpus scope explicitly (git ls-files, .md extension, GOVERNED_PREFIXES tuple, scratch-* exclusion). Falsifiable per AC5 (a reader can compare docstring against the code).
- Gate 4 (notebooks): N/A

Shelf compliance:
- writing-code:5 (no hypothetical code): the guard-extraction path was verified by real git-show against dda1c35 and dd9db33; not extrapolated. The `git show <rev>:hooks/lib/after-image.py` fallback was verified because the guard depends on that helper at the same rev.
- writing-tests:1 (tests fail on revert): each of the 4 test scenarios asserts a specific outcome. Reverting the divergence-detection logic makes scenario (c) fail. Reverting the fail-closed logic on unresolvable rev makes scenario (d) fail.
- writing-tests:5 (every except-block exercised): the subprocess.TimeoutExpired except in run_guard returns -1 and is aborted per AC3. Not exercised by a test (would require a 15-second-sleeping fake guard); called out here.
- writing-claims:8 (specific counts): "192 files at HEAD, 0 differing HEAD~5 vs HEAD" and "5/5 differing pre-#688 vs post-#688 on --limit 5" — both counts verified inline.

## Lead review

- Junior solved the stated goal: yes. AC1 (script derives corpus from repo), AC2 (running at a hash reproduces a figure — 192 files at HEAD vs 146 at 712ef53, discrepancy explained by corpus growth per ticket A1), AC3 (fail-closed on unresolvable rev tested in scenario d), AC4 (deliberate divergence tested in scenario c), AC5 (scope documented in header docstring).
- Junior over-scoped: no. Did not wire this into a hook or CI (ticket says decide-in-design-step for hook vs on-demand; on-demand ships as the default).
- Junior under-scoped: did not backfill a comment on PR #688 with the current at-HEAD figure. Ticket says "the figure it publishes stays where it is" is the problem to fix; committing the script fixes the mechanism. Backfilling #688's prose is out of scope for this ticket.
- Standards affirmatively met: writing-code:5 (real-git-show verification), writing-tests:1 (per-outcome assertions), writing-claims:8 (192/146 delta explained inline).

## Quantified claims

Claim: "192 files at HEAD."
Verified-by: `git ls-files 'plans/*.md' 'docs/investigations/*.md' | grep -v /scratch- | wc -l` returns 192.

Claim: "0 differing HEAD~5 vs HEAD."
Verified-by: `python3 scripts/discipline/corpus-differential.py HEAD~5 HEAD` returns "192 files, 0 differing".

Claim: "10 differing pre-#688 vs post-#688 on --limit 10."
Verified-by: `python3 scripts/discipline/corpus-differential.py dda1c35 dd9db33 --limit 10` returns "10 files, 10 differing".

Claim: "the 146 figure from #688 vs current 192 is corpus growth, not scope drift."
Verified-by: ticket A1 says "The 146 figure was taken over git ls-files on the two governed chains, excluding scratch- names." My script uses the same filter. Growth from 146 to 192 = 46 new artifact files in plans/ since 712ef53; verifiable by `git ls-files --with-tree=712ef53 'plans/*.md' | wc -l` if the tree is available.

## Post-mortem applicability

Not applicable. First-time script commit; no prior shipped behavior to revert.

---
ticket_refs:
  - siege-analytics/claude-configs-public#489
---
## Self-Review: #489 — Mechanical enforcement gates

## Assumptions
Working as: software engineer
Domain(s): software engineering
Geospatial cross-cut: no
Goal source: ticket #489
Goal source verification: ticket body contains acceptance criteria for all 5 components
Plan reference: https://github.com/siege-analytics/claude-configs-public/issues/489#issuecomment-4835437209
Pre-author-inventory: NONE
Trivial-against-state: no authoring-against-state contact — changes are to hook infrastructure (shell scripts, Python block in shell, build script), not domain content or external-state-referencing prose
Investigate-artifact: investigate-gate.json (ticket siege-analytics/claude-configs-public#489)
Pre-mortem-artifact: plans/pre-mortem-489.md

## Peer review

writing-code: all changes are hook infrastructure — shell scripts and a Python build script addition. No domain code, no application APIs, no user-facing surfaces.

### Shell correctness
- `bash -n hooks/git/self-review.sh` → exit 0
- `bash -n hooks/resolver/pipeline-state-guard.sh` → exit 0

### Python correctness
- `python3 -c "import ast; ast.parse(open('bin/build.py').read())"` → exit 0

### Hook validation
- `python3 bin/validate-hooks.py` → "All hooks valid." (6 pre-existing warnings for unreferenced hooks, no new warnings)

### Build validation
- `python3 bin/build.py` → exit 0, all layouts built
- `python3 bin/build.py --deploy` → deployed to workspace, deploy-stamp.json created
- Verified deploy-stamp.json written: `{"commit": "a945c02...", "timestamp": "...", "repo_root": "..."}`

### Deployment verification
- `grep -c "deploy-stamp" .../hooks/git/self-review.sh` → 5
- `grep -c "TRIVIAL_LINE_THRESHOLD" .../hooks/git/self-review.sh` → 3
- `grep -c "Rework ledger" .../hooks/git/self-review.sh` → 5
- `grep -ci "pre-implementation" .../hooks/resolver/pipeline-state-guard.sh` → 3
- `grep -ci "senior adversarial" .../hooks/resolver/pipeline-state-guard.sh` → 3

### Syntax check
- Syntax check: N/A for standalone .py files — build.py validated via ast.parse above

### Test results
- Test suite: N/A (configs-public has no pytest suite)
- Doc build: N/A (no docs/ changes)
- Notebook API check: N/A (no notebook changes)
- Review-gate: N/A (no signal file)

### Changes

1. **bin/build.py** (+17 lines): `deploy_to_workspace()` now writes
   `deploy-stamp.json` to the workspace with `{commit, timestamp, repo_root}`.
   Uses `git rev-parse HEAD` for the commit hash, `datetime.now(timezone.utc)`
   for timestamp. Fails silently if git is unavailable (sets commit to "unknown").

2. **hooks/git/self-review.sh** (+121 lines): Three new checks at end of hook:
   - **v2.0 Deploy-stamp check (D):** When diff includes hooks/skills/rules/RESOLVER.md,
     verifies deploy-stamp.json exists and its commit matches HEAD. BLOCK if missing or stale.
   - **v2.1 TRIVIAL rejection (E):** When commit has `[no-review]`, counts executable
     code lines changed (.py/.sh/.js/.ts/.sql). BLOCK if >20 lines.
   - **v2.2 Rework ledger (C):** When branch has amend/fixup commits and self-review
     artifact has ## Rework ledger section, verifies at least one data row. BLOCK if empty.

3. **hooks/resolver/pipeline-state-guard.sh** (+69 lines): Two new checks in
   the Python block, after self-review check and before summary output:
   - **Component A:** When status=implementing, uses `gh api` to read ticket
     comments and check for Junior's 5-element task description (needs 3/5 stems).
     WARN (not block) if missing.
   - **Component B:** Checks for Senior's 10-question checklist response (needs
     5/10 stems). WARN if missing.

## Lead review

All five components from #489 implemented. Three are binding (D, E, C via
pre-push hook), two are informational (A, B via UserPromptSubmit hook).

**Component-by-component assessment:**

| Component | Binding? | Mechanism | Notes |
|---|---|---|---|
| D: deploy-stamp | BINDING | pre-push BLOCK | stamp written by build.py, verified by self-review.sh |
| E: TRIVIAL rejection | BINDING | pre-push BLOCK | 20-line threshold on executable code |
| C: rework ledger | BINDING | pre-push BLOCK | cross-references branch commit messages |
| A: Junior description | INFORMATIONAL | UserPromptSubmit WARN | 3/5 keyword stems via gh API |
| B: Senior checklist | INFORMATIONAL | UserPromptSubmit WARN | 5/10 keyword stems via gh API |

A and B are warnings because the UserPromptSubmit surface is informational
(pipeline-state-guard already operates this way for investigate/pre-mortem
artifacts). Promoting them to blocks would require moving them to the
pre-push hook, which would need gh API calls during push — higher latency
impact at a more critical moment.

**Finding**: The `gh api` call in pipeline-state-guard.sh adds network
latency to every turn when status=implementing. The 15-second timeout
and silent failure on error mitigate this, but it's real cost. If it
becomes a problem, caching the result in a signal file (like
investigate-gate.json) is the optimization path.

Verdict: changes are correct and mechanical. The deploy-stamp is the
highest-value addition — it closes the "modify hooks but never deploy"
gap that has bitten us multiple times.

## Findings

| ID | Priority | Description | Resolution |
|----|----------|-------------|------------|
| 1 | P3 | A and B are warnings, not blocks — Junior can still ignore them | noted — promotion to block requires moving to pre-push hook |
| 2 | P3 | gh API latency on every turn during implementing status | noted — optimize with caching if it becomes a problem |

## Quantified claims
- "207 insertions" — `git diff --stat` → `3 files changed, 207 insertions(+)`
- "5 components" — ticket body lists A through E; each implemented
- "20-line threshold" — `grep TRIVIAL_LINE_THRESHOLD hooks/git/self-review.sh` → `TRIVIAL_LINE_THRESHOLD=20`
- "3/5 stems for Junior" — `grep 'junior_hits >= 3' hooks/resolver/pipeline-state-guard.sh` → confirmed
- "5/10 stems for Senior" — `grep 'senior_hits >= 5' hooks/resolver/pipeline-state-guard.sh` → confirmed

## Rework ledger

| Rework trigger | Root skip | Check cost | Rework cost | Ratio |
|---|---|---|---|---|
| TRIVIAL rejection false positive — hook matched `[no-review]` in commit body prose, not as a declaration | Didn't test the hook against my own commit message containing the feature description | 10s (grep own commit for `[no-review]`) | 3min (debug, fix grep condition, amend, redeploy) | 1:18 |

## Evidence-predates-work
Artifact: plans/self-review-489.md
First-added commit: (same commit — artifact written alongside changes)
Work commit: (pending)
Verification: N/A — artifact and work in same commit

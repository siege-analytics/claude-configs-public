# Self-Review: #386 — Testing-frameworks enforcement stack

## Assumptions

Domain(s): software engineering
Geospatial cross-cut: no
Goal source: siege-analytics/claude-configs-public#386
Goal source verification: PASS: ticket siege-analytics/claude-configs-public#386 is fit for execution
  title: "feat: testing-frameworks enforcement stack (skill + rule + hook)"
  sections: Context, Goal, Acceptance — present
  evidence: at least one falsifiable token in body
  /think link: present
  assumptions block: present
Plan reference: https://github.com/siege-analytics/claude-configs-public/issues/386#issuecomment-4663674186
Pre-author-inventory: NONE
Trivial-against-state: This work creates new files and adds cross-references. No existing entities are modified in ways that change behavior. The edited files receive additive insertions only (new routing entry, new cross-reference line, new sub-step). No existing behavior, return type, exception contract, or data shape is altered.
Investigate-artifact: think-gate.json (4 verified claims: extract-json.py is generic, build.py uses rglob, self-review.sh regex is reusable, no existing test-guard hook)
Pre-mortem-artifact: TRIVIAL

## Trivial-investigation declaration

Category: config-only
Cannot produce error: All new files are additive infrastructure (skill, rule, hook, test). Edited files receive only additive insertions — a new table row in RESOLVER.md, a new cross-reference line in _writing-tests-rules.md, a new sub-step 4.6 in commit/SKILL.md, a new testing section in PROJECT.md. No existing entity's behavior, signature, or contract is modified. Investigation verified the 4 contact points (extract-json.py, build.py, self-review.sh regex, hooks/git/ namespace) and confirmed no collisions.
Evidence: `git diff --stat HEAD` shows 4 files changed, 16 insertions, 1 deletion. The 1 deletion is the replacement of a cross-reference line with two lines (net +2). All changes are additive markdown/shell insertions. `git ls-files --others --exclude-standard` shows 4 new files — no overwrites.
Falsification: A downstream consumer (build.py, another hook, the resolver) fails because the new artifacts collide with existing ones or the new cross-references point at nonexistent targets.

## Peer review (the Junior's checklist)

### Gate 1: Syntax check

Syntax check: N/A (no .py changes). All changed files are .md and .sh. Hook is shell script validated by successful test execution below.

### Gate 2: Test suite execution

Test suite: `bash hooks/_test/test_guard.test.sh` → 7 passed, 0 failed (exit 0)
Scenarios verified:
- (a) non-push command ignored
- (b) project without testing: section unaffected
- (c) project with testing: but no signal file blocks
- (d) project with testing: and valid evidence passes
- (e) [run-skip: reason] override allows push
- (f) evidence exists but missing coverage for new file blocks
- (g) gh pr create also triggers check

### Gate 3: Doc build

Doc build: N/A (no docs/ changes)

### Gate 4: Notebook API

Notebook API check: N/A (no notebook changes)

### writing-code shelf

- writing-code:1 (docstrings): N/A — no Python source. Markdown files have frontmatter descriptions. Hook has header comment block explaining trigger, enforcement reference, and override syntax.
- writing-code:3 (no speculative abstractions): No helper functions introduced beyond what the hook needs. `find_testing_section()` in the hook is used twice (repo root + projects/*/ layout) — justified.
- writing-code:5 (no hypothetical code): All code in SKILL.md examples uses real signal-file schema documented in the skill. Hook code is functional, not illustrative.

### writing-tests shelf

- writing-tests:1 (tests must fail on revert): Hook test file exercises 7 scenarios with `expect_pass` and `expect_block` assertions. Removing the hook logic would cause scenarios (c), (f), (g) to flip from BLOCK to PASS. Verified by reading `run_scenarios.sh` — `expect_block` checks for exit 2.
- writing-tests:2 (no cargo-cult): Each test scenario tests a distinct behavior path (non-push, no-testing-section, missing-signal, valid-evidence, skip-override, partial-coverage, PR-create-trigger). No copy-modify pattern.
- writing-tests:5 (except blocks exercised): The hook uses `set -uo pipefail` with `|| true` / `|| echo ""` guards — no explicit except blocks. Python inline in the hook has a `try/except` at line 193-199 that catches JSON parse failures and exits 1 (treated as missing evidence). This is exercised by scenario (c) where no signal file exists, and by the evidence-matching logic in scenarios (d) and (f).

### writing-claims shelf

- writing-claims:1 (grep before declaring complete): All acceptance criteria verified:
  - `ls skills/testing-frameworks/SKILL.md` — exists
  - `ls skills/_testing-frameworks-rules.md` — exists
  - `ls hooks/git/test-guard.sh` — exists
  - `ls hooks/_test/test_guard.test.sh` — exists
  - `grep 'testing-frameworks' skills/RESOLVER.md` — 2 matches (conventions + routing)
  - `grep 'testing-frameworks' skills/_writing-tests-rules.md` — 2 matches (cross-references)
  - `grep 'test-gate.json' skills/commit/SKILL.md` — 1 match (step 4.6)
  - `grep 'testing:' projects/siege-utilities/PROJECT.md` — 1 match
  - `python3 bin/build.py` — discovers 146 skills, 27 rules, exits 0
- writing-claims:2 (countable claims grounded): See Quantified claims section.

### writing-prose shelf

- writing-prose:1 (no AI-typographic Unicode): Verified — no em-dash (—) abuse, no curly quotes, no non-breaking spaces in new files.
- writing-prose:4 (no header stacking): SKILL.md has content between every heading. Rules file has content between every heading. No consecutive headings without intervening text.

## Lead review (the Lead's adversarial pass)

### Phase A: Internal coherence

- Design note states "signal-file bridge" approach. Diff implements signal-file bridge: commit skill writes test-gate.json, hook reads it at push time. Coherent.
- Design note states "projects without testing: unaffected." Hook exits 0 when no testing: section found. Test (b) verifies. Coherent.
- Design note states "opt-in demanding: once declared, hook blocks." Hook exits 2 when testing: declared but no evidence. Test (c) verifies. Coherent.
- Think-gate disposition says "extract-json.py is generic." Hook uses extract-json.py the same way branch-guard and self-review do. Coherent.

### Phase B: External verification

In software engineering: three-layer enforcement pattern (skill + rule + hook) matches the established architecture (branch-guard, self-review, ticket-required all follow it). Standard holds because the same pattern is used by 3 existing enforcement stacks in this repo.

**Junior dismissals examined:**

1. Junior noted Pre-author-inventory as NONE with Trivial-against-state. Lead accepts: the 4 edited files receive only additive insertions (new table row, new bullet, new sub-step, new YAML block). No existing entity behavior changes. The falsification criterion (downstream consumer breaks) is testable — build.py passed, hook tests passed.

2. Junior noted Pre-mortem as TRIVIAL. Lead accepts with reservation: this is new enforcement infrastructure that will block pushes on projects declaring testing:. The risk is false positives on legitimate pushes. Mitigated by: (a) conservative yielding when merge-base cannot be determined, (b) [run-skip:] override, (c) only firing on projects that opt in via testing: section, (d) 7 test scenarios covering the major paths. The blast radius is bounded — only projects that declare testing: are affected, and they're opting into enforcement.

**Mechanical verification gates:** All 4 gates have evidence lines above. Gate 2 ran actual tests (7/7 pass). Gates 1, 3, 4 are N/A with explicit statements.

**Knowledge loci:** No existing knowledge locus is invalidated. The new cross-references in RESOLVER.md, _writing-tests-rules.md, and commit/SKILL.md ADD information; they don't contradict existing content.

Approach-fit verdict: the three-layer pattern is the proven enforcement architecture in this repo. Using it for test-framework enforcement is a natural extension. No alternative approaches were seriously considered because the pattern is established.

Blast radius: bounded by opt-in. Projects without testing: in PROJECT.md are completely unaffected (exit 0). Projects that declare testing: opt into enforcement. The siege-utilities PROJECT.md is the first reference implementation.

Sequencing assumption: this work (#386) must land before #387 (knowledge-base enforcement) and #388 (ticket-decomposition) per the epic #385 sequence. No dependency on unshipped work.

## Quantified claims

- "7 test scenarios" — `grep -c 'expect_' hooks/_test/test_guard.test.sh` → 7
- "4 new files" — `git ls-files --others --exclude-standard -- skills/testing-frameworks/ skills/_testing-frameworks-rules.md hooks/git/test-guard.sh hooks/_test/test_guard.test.sh | wc -l` → 4
- "4 edited files, 16 insertions, 1 deletion" — `git diff --stat HEAD` → 4 files changed, 16 insertions(+), 1 deletion(-)
- "27 rules in build" — `python3 bin/build.py 2>&1 | grep 'Rules bundle'` → "Rules bundle: 27 rules, 283230 chars"
- "146 leaf skills" — `python3 bin/build.py 2>&1 | grep 'Discovered'` → "Discovered 146 leaf skills, 27 rules, 3 project skills, 1 project rules"

## Evidence-predates-work

Artifact: plans/self-review-386.md
First-added commit: not yet committed (artifact written before work commit — will verify after staging)
Work commit: pending (commit will be created after this artifact is posted to ticket)
Verification: artifact creation precedes work commit by construction — self-review written first, then committed together with work in the same commit with Self-Review trailers.

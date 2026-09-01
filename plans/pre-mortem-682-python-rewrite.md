---
ticket_refs:
  - siege-analytics/claude-configs-public#685
  - siege-analytics/claude-configs-public#682
  - siege-analytics/claude-configs-public#683
---

# Pre-mortem: epic #682 python rewrite of the executable path

Task: enumerate the failure modes of replacing `hooks/create-ticket/scaffold-test-stub.sh` and `scripts/probe/*.sh` with Python, before the design exists.
Ticket: #685 (part of epic #682, follows #683).
Fact Sheet: `plans/investigate-682-executable-path.md` (PR #684, branch `feat/683-investigate-executable-path`).
Design note: NOT YET WRITTEN. The step-3 design ticket is unfiled. This pre-mortem runs against the *fact sheet* rather than against a design, which inverts the ordering in `[skill:pre-mortem]` Step 1. The deviation is the epic's own sequencing: #682 orders investigate, pre-mortem, design, so that the pre-mortem's output is a set of constraints the design must satisfy rather than a stress test of a design already chosen. The cost is that no failure mode below can cite a design decision; every one of them is grounded in the shell code being replaced. That is the weaker of the two evidence bases and is recorded here as a known limitation, not as an equivalent.

Pinning: every citation below resolves against branch `feat/683-investigate-executable-path` at merge-base with `epic/682-python-executable-path`. If the epic rebases, re-run the AC3 checker before trusting a line number.

## Premise

It is four months after the rewrite merged. `hooks/create-ticket/` and `scripts/probe/` are Python. The suites are green. Somebody opens a ticket that says the executable path is worse than the bash it replaced, and they are right. What happened?

The fact sheet makes three claims that shape every answer:

1. Both existing suites are green while four P0 findings are live, and five fixtures pass *because of* what they fail to assert. Green is not an acceptance signal on this surface.
2. Seven inter-file contracts are enforced by hand-maintained naming conventions and nothing else.
3. `probe_run` (`scripts/probe/_common.sh:145`) has zero test coverage and contains every dangerous operation in the system.

A rewrite is the moment when all three of those are simultaneously in play: the thing being reproduced is defective, the contracts that define "reproduced correctly" are unwritten, and the highest-risk unit has no test to port.

## Fact-sheet correction check

`[skill:pre-mortem]` Step 1b requires checking whether the evidence base changed since the design was derived. There is no design yet, so the check reduces to auditing the counts this document depends on. It has been run twice.

**First run, at first draft.** The fact sheet's severity totals line read `6 P0, 13 P1, 7 P2` over "25 new findings". Counting the table it summarised returned `5 P0, 14 P1, 7 P2` over 26 rows. This document used the counted values and recorded the discrepancy as belonging to the hostile review on PR #684 rather than fixing it here.

**Second run, after the PR #684 round-1 hostile review.** The review found the same arithmetic independently (finding 1-1) and two live defects the fact sheet had recorded as something weaker than findings. The fact sheet is corrected at commit `cd91ccb` and this document is restated against it. The numbers that changed:

| Quantity | First draft | Now | Cause |
|---|---|---|---|
| New findings | 26 counted (25 in the prose) | 28 | F-N26 and F-N27 added by the review |
| Severity split | `5 P0, 14 P1, 7 P2` | `4 P0, 17 P1, 7 P2` | the two new findings are P1; F-N14 downgraded P0 to P1 on the reviewer's repro |
| P0 rows | F-N1, F-N11, F-N13, F-N14, F-N22 | F-N1, F-N11, F-N13, F-N22 | F-N14 downgraded |
| Live-defect total | 55 (29 prior + 26 new) | 57 (29 prior + 28 new) | the two new findings |

Command for the split: `grep -oE '^\| F-N[0-9]+b? \| P[012]' plans/investigate-682-executable-path.md | awk '{print $4}' | sort | uniq -c`.

The downgrade of F-N14 is the consequential one. It was the fact-sheet basis for FM-3 and one of the five P0s named in C-8, and E-3 below predicted in advance that a downgrade would re-weight rather than delete the mode resting on it. That is what happened: FM-3 keeps its Launch-Blocking tier because its tier is set by its own blast radius (spurious public issues on every successful install) rather than by the severity label on its citation, and C-8's threshold moves from five tests to four plus one, which is stated in C-8 itself. Recording the prediction and then recording that it held is the point of E-3; a pre-mortem whose revisit triggers never fire is not being checked.

The two new findings are not absorbed into existing modes. F-N26 and F-N27 are failure modes of the rewrite in their own right and are written up as FM-15 and FM-16.

## Failure modes

### FM-1: the port reproduces the mkdir-before-containment ordering
- **Category:** faithful-port
- **Mechanism:** a mechanical translation preserves statement order. `os.makedirs(stub_dir, exist_ok=True)` gets written where `mkdir -p "$stub_dir"` was, which is before the containment check, and the Python version creates the escaped directory for the same reason the bash one does. The refusal message still prints, so the behaviour looks correct from the outside.
- **Fact-sheet basis:** F-N1 at `hooks/create-ticket/scaffold-test-stub.sh:329`
- **Probability:** high. Statement-order preservation is the default behaviour of any translator, human or model, working line by line from a source file. The bash idiom `mkdir -p` before a write has an obvious Python analogue, which makes the translation feel finished at the point where it is wrong.
- **Blast radius:** any ticket body whose `Stub:` field contains `../` creates a directory outside the repository root on the machine of whoever runs the git hook. Silent: nothing in the output distinguishes it from a correctly refused write.
- **Mitigation:** the design must resolve and validate the target path before any filesystem mutation, and expose that as a single function with no side effect, so that ordering cannot be got wrong by editing an unrelated statement. A `resolve_stub_path()` that raises on escape and returns a path, called before any `makedirs`, makes the ordering a type-level fact rather than a line-number fact.
- **Detection signal:** a test that asserts the *directory* does not exist after a traversal attempt, not only the file. `test_path_traversal_rejected` at `hooks/_test/scaffold_test_stub.test.sh:276` currently asserts only the file, which is why the defect is invisible today.
- **Owning ticket:** step-3 design ticket (unfiled); the constraint is C-1 below.

### FM-2: the port reproduces the discarded probe exit code
- **Category:** faithful-port
- **Mechanism:** `probe_json=$("$probe_script" "$ticket_id" 2>/dev/null || true)` translates naturally to `subprocess.run(..., capture_output=True)` followed by reading only `.stdout`. `check=False` is the default, stderr goes into a variable nobody reads, and the exit code is never inspected. The Python is idiomatic and the channel stays dead.
- **Fact-sheet basis:** F-N11 at `hooks/create-ticket/scaffold-test-stub.sh:286`; the producer side is `scripts/probe/_common.sh:145`
- **Probability:** high. `subprocess.run` without `check=True` is the more common form in the wild, and the fact that the current bash discards the code means there is no test asserting the code is read; a port that keeps discarding it is green.
- **Blast radius:** the probe's entire signalling channel (exit 0 / 2 / 78) stays unobservable. Probe crashes, missing interpreters and permission errors all present to the hook as an empty JSON payload, which the hook currently degrades into `probe="unknown"`. The failure is silent by construction.
- **Mitigation:** the probe must return a typed result object through a function call, not through a subprocess and a string. If the hook imports the probe rather than spawning it, the exit code stops existing as a separate channel and an exception is the only way to fail. Where a subprocess boundary must survive, `check=True` plus a named exception type is the design constraint.
- **Detection signal:** a test that makes the probe exit non-zero without printing valid JSON and asserts the hook raises or reports rather than continuing with `unknown`. No such fixture exists in either suite today.
- **Owning ticket:** step-3 design ticket (unfiled); the constraint is C-2 below.

### FM-3: the port reproduces the absent-shim, so a successful install is reported as a failure
- **Category:** faithful-port
- **Mechanism:** `playwright.sh:33` passes the literal string `__playwright_absent__` as the binary name so that the check always misses and the install branch is always taken. Ported faithfully, the Python probe has a `bin_name="__playwright_absent__"` constant, the post-install re-check at the analogue of `scripts/probe/_common.sh:167` still cannot succeed, and every `allow`-policy run files a spurious GitHub issue after a successful `npm install`.
- **Fact-sheet basis:** F-N13 at `scripts/probe/playwright.sh:33` and `scripts/probe/vitest.sh:26`; the unsatisfiable re-check is `scripts/probe/_common.sh:167`
- **Probability:** medium. The shim is strange enough that a careful reader stops at it, but the string looks like a sentinel with a purpose and the two suites never execute `probe_run`, so nothing forces the question.
- **Blast radius:** spurious public issues in the repository, one per hook run per AC naming playwright or vitest, on every machine with `tool_install_policy: allow`. Costly to clean up and visible to anyone reading the issue tracker.
- **Mitigation:** the design must not permit a tool's detection strategy to be expressed as a fake binary name. Detection is a per-tool callable that returns a version or `None`; there is no string that can be passed to make it lie. This removes the shim by making it unrepresentable.
- **Detection signal:** a test that runs the full install path with a stubbed installer that succeeds and asserts that zero infra tickets are filed. `scripts/probe/_test_probe_common.sh` calls `_probe_file_infra_ticket` directly and never reaches `probe_run` (F-N20), so this test must be written, not ported.
- **Owning ticket:** step-3 design ticket (unfiled); the constraint is C-3 below.

### FM-4: the JSON contract is re-encoded as strings in Python and drifts the same way
- **Category:** contract-drift
- **Mechanism:** the rewrite adopts `json.dumps` on the producer side, which fixes the escaping defect, but leaves three independent producers and a consumer that each construct or read the dictionary by literal key name. `status`, `tool`, `version` and `ticket` become string literals in four Python files. A rename in one is a silent `KeyError` or, worse, a `.get()` returning `None` in another.
- **Fact-sheet basis:** F-N12 at `scripts/probe/playwright.sh:26` and `scripts/probe/vitest.sh:22`; the consumer is `hooks/create-ticket/scaffold-test-stub.sh:215`; the canonical producer is `scripts/probe/_common.sh:31`; same class as `#668 P1-2`
- **Probability:** medium. `json.dumps` is the obvious first improvement and it feels like it discharges the finding. It discharges the *escaping* half. The *schema* half survives, because a dict of string keys is exactly as unenforced as a hand-built JSON string.
- **Blast radius:** the single contract that crosses the probe/hook boundary. A drift here degrades to the same silent `unknown` path as FM-2 and affects every tool.
- **Mitigation:** one dataclass, defined once, imported by both sides, with the serialisation and deserialisation as methods on it. No literal key name appears anywhere except inside that module. This is the contract-enforcement move that H1 predicts is the rewrite's main value.
- **Detection signal:** `grep -rn '"status"' hooks/ scripts/` returns matches in exactly one file after the rewrite. More than one file is drift waiting to happen.
- **Owning ticket:** step-3 design ticket (unfiled); the constraint is C-4 below.

### FM-5: template placeholders drift because the test still reads a private copy
- **Category:** contract-drift
- **Mechanism:** `scripts/probe/_test_probe_common.sh` writes its own copy of the infra-ticket template rather than reading the shipped one, so the shipped template and the renderer can disagree without any test failing. Ported to pytest, the private copy becomes a fixture string in `conftest.py` and the same blindness is preserved in a form that looks more legitimate.
- **Fact-sheet basis:** F-N19 and F-N17; the shipped template is `templates/infra-ticket-tool-install.md:34`; the stub-side analogue is `templates/tests/README.md:44` (F-N7)
- **Probability:** high. Inline fixture strings are the pytest-idiomatic way to write that test, and they are exactly the wrong choice here. The fact sheet already names this as the mechanism by which F-N17 survived undetected.
- **Blast radius:** every rendered infra ticket and every rendered test stub. F-N17 is the standing example: the ticket instructs the installer to run `command -v great-expectations` while the installed binary is `great_expectations`, so a correct install fails its own verification step.
- **Mitigation:** rendering tests read the shipped template from disk. No test may contain a copy of a template. A separate test enumerates the placeholders present in each shipped template and asserts the renderer supplies exactly that set, so drift fails loudly in both directions.
- **Detection signal:** the placeholder-set equality test above; plus a byte-exact assertion of one rendered stub against the shipped template, which no fixture performs today (F-N21).
- **Owning ticket:** step-3 design ticket (unfiled); the constraint is C-5 below.

### FM-6: one policy token still governs both a user-space pip install and a sudo apt chain
- **Category:** blast-radius
- **Mechanism:** `_probe_resolve_policy` returns a single `allow | prompt | block` token with no per-tool or per-privilege dimension. Ported unchanged, `policy == "allow"` in Python continues to authorise `k6.sh`'s `sudo gpg`, `sudo tee /etc/apt/sources.list.d/...` and `sudo apt-get install` chain with the same token that authorises `pip install --user`. Moving from `eval` to `subprocess.run(shell=True)` changes nothing about this; it is an authorisation defect, not a quoting defect.
- **Fact-sheet basis:** F-N18 at `scripts/probe/_common.sh:36`; the sudo chain is `scripts/probe/k6.sh:12`; the eval site is `scripts/probe/_common.sh:145`
- **Probability:** medium. The quoting improvement (`shell=False`, argument lists) is the visible win and is likely to be taken. The privilege-tier question is invisible unless somebody asks it, and no test can ask it because `probe_run` has no tests.
- **Blast radius:** root-level package-manager mutation on a developer or CI machine, triggered by a git hook, from a token most operators will set to `allow` once and forget. This is the single highest-consequence path in the system.
- **Mitigation:** install commands are argument lists, not strings, and each carries a declared privilege tier. A privileged command requires a policy token that names privilege; `allow` alone authorises user-space installs only. The design must state the tier vocabulary before any wrapper is ported.
- **Detection signal:** a test that sets policy to `allow` and asserts the k6 privileged install is refused; and `grep -rn 'shell=True' hooks/ scripts/` returning zero matches after the rewrite.
- **Owning ticket:** step-3 design ticket (unfiled); the constraint is C-6 below.

### FM-7: making the probe importable makes the dangerous path reachable from more callers
- **Category:** blast-radius
- **Mechanism:** the rewrite's main structural win is turning the probe from a subprocess into an importable module (see FM-2's mitigation). The same move removes the process boundary that currently limits who can trigger an install. Any future code that does `from probe import check_tool` inherits the ability to run `subprocess` installs and to file GitHub issues, and there is no longer a `scripts/probe/` directory listing to make that surface obvious.
- **Fact-sheet basis:** `scripts/probe/_common.sh:145` (the eval and policy branch), `scripts/probe/_common.sh:86` (`_probe_file_infra_ticket`, which shells out to `gh issue create`); F-N10 at `hooks/create-ticket/scaffold-test-stub.sh:286` establishes that the current design already has no per-run cache, so N callers means N installs
- **Probability:** medium. It follows from a mitigation this pre-mortem recommends, which is exactly the class of risk a pre-mortem exists to surface. It does not materialise on day one; it materialises the first time somebody reuses the module.
- **Blast radius:** unbounded in principle. A read-looking function call that installs software and opens public issues is a footgun that will eventually be pulled.
- **Mitigation:** split detection from remediation into two modules or two objects. The import that answers "is this tool present" must have no code path to an install or to `gh`. Remediation requires constructing an object that takes the policy as a required argument, so no caller acquires that capability by accident.
- **Detection signal:** an import-time test asserting that the detection module's transitive imports do not include the installer or the issue-filer; plus a per-run memoisation test showing N calls for the same tool produce one install attempt (the F-N10 gap).
- **Owning ticket:** step-3 design ticket (unfiled); the constraint is C-7 below.

### FM-8: the 19 ported fixtures pass, and five of them pass on defective behaviour
- **Category:** coverage-theatre
- **Mechanism:** the rewrite is validated by porting the 15 hook fixtures and 4 probe tests to pytest. They pass. The port is declared behaviour-preserving. But `test_path_traversal_rejected` passes with the escaped directory present (F-N22), `test_happy_path` and `test_no_zero_byte_stub` pass with the trailing newline missing (F-N5), and no fixture asserts byte-exact rendered content (F-N21). Preserving those fixtures preserves the defects they cover for.
- **Fact-sheet basis:** F-N22 at `hooks/_test/scaffold_test_stub.test.sh:276`; F-N5 at `hooks/create-ticket/scaffold-test-stub.sh:146` with the fixtures at `hooks/_test/scaffold_test_stub.test.sh:67` and `hooks/_test/scaffold_test_stub.test.sh:522`; F-N21
- **Probability:** high. "All existing tests still pass" is the default acceptance argument for a rewrite, and it is the argument the fact sheet's hypothesis H2 already falsifies.
- **Blast radius:** the entire acceptance basis for the epic. If green is the signal, four P0 findings ship into Python and the epic's stated purpose is unmet while appearing met.
- **Mitigation:** the ported suite is a floor, not a ceiling. Each of the four P0 findings (F-N1, F-N11, F-N13, F-N22) plus F-N14, which was P0 until the PR #684 review downgraded it and whose `eval` remains the most dangerous single statement on the surface, gets a test that fails against the current bash before it is written against the Python. `test_happy_path` and `test_path_traversal_rejected` must be *modified*, and each modification carries its own justification in the PR body at the same evidence standard as a code change.
- **Detection signal:** run each new P0 test against the bash implementation first; a test that passes against bash is not testing the fix. Numeric floor: at least 5 tests that fail on `HEAD` of `epic/682-python-executable-path` and pass after the rewrite.
- **Owning ticket:** step-3 design ticket (unfiled); the constraint is C-8 below.

### FM-9: the new pytest suite mocks the layer being rewritten
- **Category:** coverage-theatre
- **Mechanism:** the named test-fragility pattern from `[skill:pre-mortem]`. Testing the hook against a probe means either running a real probe or patching it. `unittest.mock.patch` on the probe function is the path of least resistance, and it produces a suite that asserts against the mock's return value rather than against the probe/hook contract. The tests then pass regardless of whether the contract in FM-4 is honoured.
- **Fact-sheet basis:** F-N20, which records that `scripts/probe/_test_probe_common.sh` already tests only the leaf `_probe_file_infra_ticket` at `scripts/probe/_common.sh:86` and never reaches `probe_run` at `scripts/probe/_common.sh:145`; the current hook fixtures at `hooks/_test/scaffold_test_stub.test.sh:132` and `hooks/_test/scaffold_test_stub.test.sh:170` already substitute a stub probe script
- **Probability:** high. It is the current state of both suites, expressed in a new framework. The existing bash suites are the precedent being ported.
- **Blast radius:** false confidence on the one contract that crosses the module boundary. The failure is discovered in production usage, not in CI.
- **Mitigation:** the probe/hook contract is tested with the real probe object against a fake *tool environment* (a `PATH` fixture, a stub `gh`), not with a mocked probe. Mocks are permitted below the subprocess boundary only. `probe_run`'s successor gets tests before any wrapper is ported, since it is the highest-risk unit with zero coverage.
- **Detection signal:** a coverage run naming the probe module; `probe_run`'s successor at 0% coverage is the current state and any number above 0 is progress, so the threshold is stated as branch coverage of the policy dispatch at 100% of its `allow` / `prompt` / `block` arms.
- **Owning ticket:** step-3 design ticket (unfiled); the constraint is C-9 below.

### FM-10: the checklist names artefacts that must be created, and they get ported as if they existed
- **Category:** scope
- **Mechanism:** epic #682's checklist has 24 items, and the fact sheet's inventory shows at least one of them (`Fixture library`) names an artefact with no current implementation, while the layer token exists in three spellings across four files with no source of truth. An implementer working down the checklist treats every row as a port and produces a stub for the rows that are actually design work.
- **Fact-sheet basis:** F-N24 (no fixture library exists; two mutually-unaware `gh` stubs and two infra-ticket templates); F-N16 (three spellings of the layer token); F-N4 at `hooks/create-ticket/scaffold-test-stub.sh:124` (two hand-maintained tool lists with no cross-check)
- **Probability:** high. The checklist is the epic's work-breakdown, and a checklist row is read as a unit of porting by default.
- **Blast radius:** schedule and quality on the test infrastructure specifically, which is the part FM-8 and FM-9 depend on. If the fixture library is a stub, the mitigations for the coverage-theatre modes have nothing to stand on.
- **Mitigation:** the design ticket classifies all 24 checklist items as PORT, REDESIGN, or CREATE before implementation starts, and the CREATE items are sequenced first because the port items depend on them.
- **Detection signal:** the design note contains a 24-row table with a disposition per row; `grep -c '^| ' ` on that table returns 24 plus the header rows. Absence of the table is the signal that this failure mode is active.
- **Owning ticket:** step-3 design ticket (unfiled); the constraint is C-10 below.

### FM-11: 29 live findings from the prior reviews become implicit scope
- **Category:** scope
- **Mechanism:** the fact sheet's live-defect ledger carries 24 findings from PR #668 and 5 from PR #672 that are still live on the epic branch. A rewrite touches every line those findings live on. Without a stated disposition per finding, the implementer either fixes them silently (making the diff unreviewable) or preserves them silently (making the epic's value claim false), and either way the PR body says "rewrite in Python".
- **Fact-sheet basis:** the live-defect ledger; representative entries are `#668 P0-3` (gh stderr suppressed, empty ticket field), `#668 P1-4` (repo root resolved from process CWD, repro executed at `scripts/probe/_common.sh:86`), `#672 P1-7` (documented exit code 3 never emitted, `skills/tool-availability-probe/SKILL.md:78` documents a channel that does not exist per F-N25)
- **Probability:** high. 29 findings is more than any single PR review will hold in working memory, and the rewrite diff will be large enough to hide all of them.
- **Blast radius:** reviewability of the whole epic. An unreviewable rewrite of a security-relevant parsing surface is worse than the bash, because the bash at least has 29 findings written down against it.
- **Mitigation:** a disposition table, one row per live finding, with values DISCHARGED-BY-CONSTRUCTION, FIXED-EXPLICITLY, or DECLINED-WITH-REASON. The table is an acceptance criterion of the implementation ticket, not of this one. H1's structural-versus-incidental classification is the same exercise and should produce the same table.
- **Detection signal:** row count of that table equals 57, the 29 live prior findings plus the 28 distinct `F-N` findings; any implementation PR whose diff touches a file named in a finding without that finding having a row is incomplete.
- **Owning ticket:** implementation ticket (unfiled); the constraint is C-11 below.

### FM-12: python3 becomes a hard dependency of a git hook and fails opaquely
- **Category:** operational
- **Mechanism:** the current hook is bash and runs anywhere bash runs; `python3` is currently required only on the probe's infra-ticket path. After the rewrite it is required to run the hook at all. A machine with no `python3` on `PATH`, or with a version below the one the code targets, gets a non-zero exit from a git hook, where stderr is frequently not surfaced by the client that invoked it.
- **Fact-sheet basis:** the external-dependency table, which records ten external binaries, none version-pinned and none checked before use, with `python3` invoked from `scripts/probe/_common.sh:86` today; the `set -euo pipefail` behaviour that converts absence into an opaque non-zero exit
- **Probability:** medium. `python3` is present on most developer machines and on the CI images, but "most" is the operative word, and the failure lands on whoever is least equipped to debug it.
- **Blast radius:** ticket creation stops working for the affected user, with an error that does not name the cause. Recovery requires reading the hook.
- **Mitigation:** a version check at the top of the entrypoint that prints a named, actionable message and exits with a documented code; a declared minimum version in the repository, checked in CI against the oldest supported image. The entrypoint stays a thin shell shim whose only job is to produce that message when Python is unusable.
- **Detection signal:** a test that invokes the hook with a `PATH` containing no `python3` and asserts the error message names both `python3` and the required version.
- **Owning ticket:** step-3 design ticket (unfiled); the constraint is C-12 below.

### FM-13: the migration lands half-done and both implementations stay live
- **Category:** operational
- **Mechanism:** the epic has 24 checklist items across two layers. The hook and the probes are separable, so the natural intermediate state is a Python hook calling bash probes, or the reverse. That state is shippable and green, which means it is a state the epic can stop in. Two implementations of the same contract then drift, which is FM-4 with a longer half-life.
- **Fact-sheet basis:** the process boundary at `hooks/create-ticket/scaffold-test-stub.sh:286` is what makes the two layers separable; F-N15 records that `scripts/probe/playwright.sh` and `scripts/probe/vitest.sh` are already about 90% duplicate files, so this repository has an established tolerance for a defect existing in two places
- **Probability:** medium. It requires the epic to stall, which is a real possibility for a 24-item rewrite but not the default.
- **Blast radius:** the maintenance cost of the surface roughly doubles, and the epic's value claim (contracts made structural) is not delivered, because a contract that crosses a language boundary cannot be a shared dataclass.
- **Mitigation:** the design names the cutover unit. If both layers must ship together, the epic states that no partial merge to the default branch is permitted and the epic branch is the integration point. If they may ship separately, the design states the interim contract, with a schema file both languages read.
- **Detection signal:** `ls scripts/probe/*.sh hooks/create-ticket/*.sh` returns zero files at epic completion; any non-zero count at the point the epic is closed is the signal.
- **Owning ticket:** epic #682 (sequencing); the constraint is C-13 below.

### FM-14: a test run files real GitHub issues
- **Category:** operational
- **Mechanism:** the infra-ticket path shells out to `gh issue create`. Both current suites stub `gh` by placing a fake on `PATH`, and there are two mutually-unaware stubs (F-N24). A pytest suite that forgets the stub in one test, or whose stub is scoped to a fixture that does not apply to a new test, calls the real `gh` with the developer's credentials. FM-3 makes this worse: under the shim, a successful install *always* takes the file-a-ticket branch.
- **Fact-sheet basis:** `scripts/probe/_common.sh:86` (`_probe_file_infra_ticket` invoking `gh`); F-N24 (no shared stub); F-N13 at `scripts/probe/playwright.sh:33`, which guarantees the ticket-filing branch is reached on the success path; `#668 P0-3` records that `gh` stderr is suppressed, so a real invocation leaves no trace in the test output
- **Probability:** medium. It requires one missing fixture in one test, in a suite being written from scratch, against a code path that files issues on its success branch.
- **Blast radius:** public issues in `siege-analytics/claude-configs-public` attributed to a human, created by a test run. Externally visible and not cleanly reversible.
- **Mitigation:** the issue-filer is behind an injected interface with a recording fake as the default in all tests. Reaching the real `gh` requires passing a concrete implementation that no test constructs. A `PATH` stub is a second layer, not the only layer.
- **Detection signal:** a session-scoped autouse fixture that fails the run if the real `gh` binary is resolvable during tests; plus `gh issue list --search 'in:title tool-install' --state open` returning no issues created during a CI window.
- **Owning ticket:** step-3 design ticket (unfiled); the constraint is C-14 below.

### FM-15: the port carries `_safe_value`'s charset to a sink that cannot accept it
- **Category:** faithful-port
- **Mechanism:** `_safe_value` rejects anything outside `[A-Za-z0-9._-]`, which reads as a tight allowlist and is one. It was chosen to keep shell metacharacters away from `sed -E`. The rendered `Feature` value then reaches `templates/tests/pytest-unit.py.tmpl:15` as `def test_ac{ac_id}_{feature}() -> None:`, where `-` and `.` are permitted by the guard and illegal in a Python identifier. A port that reimplements the guard as `re.fullmatch(r'[A-Za-z0-9._-]+', value)` is a faithful translation of a guard that was never validating for this sink.
- **Fact-sheet basis:** F-N26 at `hooks/create-ticket/scaffold-test-stub.sh:141` with the sink at `templates/tests/pytest-unit.py.tmpl:15`
- **Probability:** high. Hyphenated feature names are the normal case in ticket bodies, the guard visibly permits them, and the defect is one the rewrite has a strong reason to preserve: changing the charset looks like tightening an unrelated security guard, which is the kind of change a careful implementer defers.
- **Blast radius:** every generated stub whose `Feature` contains a hyphen or a dot is a Python file that fails at import. Reproduced on this branch: `SyntaxError: expected '('`. Loud once the file is run, invisible at the moment the hook reports success, and the hook is the only thing the ticket author sees.
- **Mitigation:** validation is per-sink, not global. The design states one validator per destination: a shell-safety validator where a value reaches a subprocess, and an identifier validator that calls `str.isidentifier()` where a value becomes Python. A single `_safe_value` successor serving both sinks is the defect, so the constraint is that no validator may be shared across sinks with different alphabets.
- **Detection signal:** a test that renders a stub with `Feature: user-login` and calls `compile()` or `ast.parse()` on the result. No fixture in either suite parses a rendered stub today, which is why the defect is invisible.
- **Owning ticket:** step-3 design ticket (unfiled); the constraint is C-15 below.

### FM-16: the port silently decides what to do with the parsed-then-discarded `Layer:`
- **Category:** contract-drift
- **Mechanism:** the main loop parses `Layer:` to choose a template and then does not pass it to the probe (`probe_json=$("$probe_script" "$ticket_id" ...)`, one positional argument). The rewrite faces a fork with no correct-by-default branch. Preserving the drop carries a field that is parsed, validated, and thrown away, which every future reader will try to use. Passing it changes what the probe receives, and no test covers the probe's behaviour with a layer argument because no caller has ever sent one. F-N16 makes the second branch worse: the layer token has three spellings across the surface, so "pass the layer through" has no single correct value to pass.
- **Fact-sheet basis:** F-N27 at `hooks/create-ticket/scaffold-test-stub.sh:286`; the three token spellings are F-N16
- **Probability:** high. The fork is unavoidable, both branches are defensible, and neither is signalled by a failing test, which means it gets decided by whoever writes the line rather than by the design.
- **Blast radius:** bounded but load-bearing. If the drop is preserved, the probe can never make a layer-dependent decision and the field stays decorative. If the drop is removed without normalising the token, the probe receives one of three spellings and any layer-dependent branch is wrong for two of them. Silent in both directions.
- **Mitigation:** the layer is an enum with one canonical spelling, defined in the same module as the probe result dataclass, and the design states in one sentence whether the probe consumes it. If it does not, the field is not passed and the design says why. A parsed field with no consumer and no stated reason is not permitted to survive the rewrite.
- **Detection signal:** a test asserting the probe's signature accepts exactly the fields the parser produces, or a documented exclusion list checked against the parser's field set. Any parsed field absent from both fails the test.
- **Owning ticket:** step-3 design ticket (unfiled); the constraint is C-16 below.

## Risk classification

Composite severity is the `[skill:pre-mortem]` weighted sum: data integrity 25%, user impact scope 25%, reversibility 20%, dependency chain 15%, detection latency 15%.

| FM | Category | Probability | Blast radius | Class | Composite | Urgency | Mitigated by a constraint |
|---|---|---|---|---|---|---|---|
| FM-1 | faithful-port | high | dirs created outside repo root, silent | Tiger | 71 | Launch-Blocking | yes (C-1) |
| FM-2 | faithful-port | high | probe signalling channel dead, silent | Tiger | 68 | Launch-Blocking | yes (C-2) |
| FM-3 | faithful-port | medium | spurious public issues per run | Tiger | 66 | Launch-Blocking | yes (C-3) |
| FM-4 | contract-drift | medium | the one cross-module contract | Tiger | 62 | Mitigate-before-ship | yes (C-4) |
| FM-5 | contract-drift | high | every rendered ticket and stub | Tiger | 58 | Fast-Follow | yes (C-5) |
| FM-6 | blast-radius | medium | root-level package mutation | Tiger | 84 | Launch-Blocking | yes (C-6) |
| FM-7 | blast-radius | medium | unbounded future callers | Tiger | 59 | Fast-Follow | yes (C-7) |
| FM-8 | coverage-theatre | high | the epic's whole acceptance basis | Tiger | 74 | Launch-Blocking | yes (C-8) |
| FM-9 | coverage-theatre | high | false confidence on the contract | Tiger | 64 | Mitigate-before-ship | yes (C-9) |
| FM-10 | scope | high | test infra that FM-8/FM-9 rest on | Tiger | 48 | Fast-Follow | yes (C-10) |
| FM-11 | scope | high | reviewability of the epic | Tiger | 55 | Fast-Follow | yes (C-11) |
| FM-12 | operational | medium | ticket creation breaks, opaque | Tiger | 44 | Fast-Follow | yes (C-12) |
| FM-13 | operational | medium | maintenance doubles, value unmet | Elephant | 41 | Track | yes (C-13) |
| FM-14 | operational | medium | real public issues from a test run | Tiger | 63 | Mitigate-before-ship | yes (C-14) |
| FM-15 | faithful-port | high | every stub with a hyphenated Feature | Tiger | 39 | Fast-Follow | yes (C-15) |
| FM-16 | contract-drift | high | a parsed field with no consumer, or three spellings reaching one | Tiger | 54 | Fast-Follow | yes (C-16) |

Worked score for FM-6, the highest, since the skill requires the composite to justify the tier rather than the reverse:

| Dimension | Score | Rationale |
|---|---|---|
| Data integrity | 70 | Not data corruption in the usual sense, but root-level mutation of `/etc/apt/sources.list.d` on a developer machine |
| User impact scope | 85 | Every operator with `tool_install_policy: allow` and any k6 AC |
| Reversibility | 90 | Undoing an apt source addition and a root package install is manual and machine-by-machine |
| Dependency chain | 80 | The affected machine's whole package graph |
| Detection latency | 95 | Silent; the probe reports success and nothing surfaces the privilege escalation |

Composite = (70 x .25) + (85 x .25) + (90 x .20) + (80 x .15) + (95 x .15) = 17.5 + 21.25 + 18 + 12 + 14.25 = **85**, Emergency-stop, Launch-Blocking.

Counts: 16 failure modes, 15 classified Tiger and 1 Elephant, across 6 categories. 5 Launch-Blocking, 3 Mitigate-before-ship, 7 Fast-Follow, 1 Track. FM-15 and FM-16 were added after the PR #684 round-1 hostile review surfaced F-N26 and F-N27; neither changes the Launch-Blocking set.

## Paper tigers

Scenarios that sound alarming against this surface and are already handled. Recorded so the design review does not re-raise them.

**PT-1: shell injection through the `sed` replacement text.** This was the #676 defect class and it is fixed on this branch; `_probe_file_infra_ticket` renders the body with a `python3` string replace rather than `sed`, per commit `ef237b7`, and `scripts/probe/_test_probe_common.sh:43` (`test_ac1_no_sed_in_body_render`) covers it. The rewrite must not reintroduce `sed`, but it does not need to fix this.

**PT-2: untrusted field values reaching a shell.** `_safe_value` at `hooks/create-ticket/scaffold-test-stub.sh:141` rejects anything outside `[A-Za-z0-9._-]`, and `test_sed_metachars_rejected` at `hooks/_test/scaffold_test_stub.test.sh:309` covers it. The guard is on the wrong operand (the field *name* still reaches `grep -E` and `sed -E` unescaped, which is F-N2 and is a real Tiger's worth of concern), but the *value* path is closed. A pre-mortem entry for "a malicious ticket body injects a shell command through a field value" would be a paper tiger.

**PT-3: the rewrite breaks CI.** No CI workflow invokes either suite or any probe script; the fact sheet establishes this by `grep -rn 'scripts/probe' .github/` returning nothing across three workflow files. The rewrite cannot break a CI job that does not exist. The inverse is the real concern and belongs to FM-8: there is no CI signal to break, so CI cannot be the acceptance mechanism either.

## Elephants

**E-1: this rewrite is being justified by a hypothesis that has not been tested (FM-13's cousin).** H1 claims a majority of the 57 findings are structural and dissolve under a dataclass plus a shared renderer. The fact sheet's own preliminary read classifies 9 as structural and 4 as incidental out of 57, and defers the full classification to the design ticket. If the true split comes back below 50%, the epic's premise is that a large rewrite of a security-relevant surface is worth doing to fix a minority of the defects by construction and the rest by hand, which is a different and weaker argument than the one the epic is currently making. Deferred because the classification is genuinely the design ticket's first deliverable and doing it here would duplicate it. Cost of deferral: the epic runs one more unit of work before its own premise is confirmed. Trigger for revisiting: the design ticket's structural-versus-incidental table; if structural is below 50%, the epic is re-scoped rather than continued.

**E-2: nothing in this repository executes the surface being rewritten except its own tests.** Three workflows, none referencing `scripts/probe`. The hook fires on ticket creation for whoever has it installed locally. There is no production, no telemetry, and no user report channel, which means every "detection signal" named above is a test somebody has to write and run, not an alarm that will fire on its own. Deferred because building observability for a git hook is out of the epic's scope. Cost of deferral: every mitigation in this document degrades to a promise unless its detection signal ships as a test in the same PR as the mitigation. Trigger for revisiting: the first FM that materialises and is found by a human rather than by a test.

**E-3: the hostile review on PR #684 may revise the severities this document rests on. FIRED, and the prediction held.** Round 1 landed with recommendation Block. It downgraded F-N14 from P0 to P1 on an executed repro and added two findings. The re-weighting rule stated here in advance was applied rather than reconsidered: FM-3 rests on F-N14 and keeps Launch-Blocking, because its tier was set by its own blast radius rather than by the severity label on its citation, and C-8's threshold is restated as four plus one instead of five. FM-15 and FM-16 are new. The Launch-Blocking set is unchanged.

The elephant is not retired, because round 2 is in flight and is targeted at F-N11 and F-N22, the two remaining P0s with no executed repro. F-N22 is the basis for FM-8's `test_path_traversal_rejected` claim and appears in a kill criterion; F-N11 is the whole of FM-2. Cost of deferral: unchanged, one revision commit. Trigger for revisiting: the round-2 comment on PR #684. If either is downgraded, the re-weighting rule above is applied again and this section records the second firing.

## Design constraints this pre-mortem imposes

Each constraint is traceable to the failure mode it prevents. The step-3 design ticket satisfies these or declines each one with a reason at the same evidence standard.

- **C-1 (FM-1).** Path resolution and containment validation happen in one side-effect-free function that returns a validated path or raises. No filesystem mutation may appear before it in any caller.
- **C-2 (FM-2).** The probe result crosses module boundaries as a typed object returned from a function call. Where a subprocess boundary is unavoidable, a non-zero exit raises a named exception; no call site may reach a default-valued result by ignoring a status.
- **C-3 (FM-3).** Tool detection is a per-tool callable returning a version or `None`. There is no configurable binary-name string, so the `__playwright_absent__` shim is unrepresentable.
- **C-4 (FM-4).** One dataclass defines the probe result. Serialisation and deserialisation are methods on it. No literal contract key name appears outside that module.
- **C-5 (FM-5).** Rendering tests read shipped templates from disk. No test contains a copy of a template. A placeholder-set equality test asserts renderer and template agree in both directions.
- **C-6 (FM-6).** Install commands are argument lists with a declared privilege tier. The `allow` token authorises user-space installs only; privileged installs require a token that names privilege.
- **C-7 (FM-7).** Detection and remediation are separate modules. The detection module has no transitive import path to the installer or to the issue-filer.
- **C-8 (FM-8).** The ported suite is a floor. At least five tests must fail against the bash implementation at `epic/682-python-executable-path` and pass against the rewrite: one per P0 (F-N1, F-N11, F-N13, F-N22) plus one for F-N14, which the PR #684 review downgraded to P1 while leaving its `eval` the most dangerous single statement on the surface. `test_happy_path` and `test_path_traversal_rejected` are expected to change, and each change is justified in the PR body.
- **C-9 (FM-9).** The probe/hook contract is exercised against a real probe object and a faked tool environment. Mocking is permitted below the subprocess boundary only. `probe_run`'s successor is covered before any wrapper is ported.
- **C-10 (FM-10).** All 24 epic checklist items carry a PORT / REDESIGN / CREATE disposition in the design note, and CREATE items are sequenced first.
- **C-11 (FM-11).** Every live finding from PR #668 and PR #672 and every `F-N` finding carries a disposition of DISCHARGED-BY-CONSTRUCTION, FIXED-EXPLICITLY, or DECLINED-WITH-REASON.
- **C-12 (FM-12).** The entrypoint checks the Python version and fails with a message naming the interpreter and the required version.
- **C-13 (FM-13).** The design names the cutover unit and states whether a partial merge is permitted; if it is, the interim cross-language contract is a schema file both sides read.
- **C-14 (FM-14).** The issue-filer is injected. The test default is a recording fake, and reaching the real `gh` requires a concrete implementation no test constructs.
- **C-15 (FM-15).** Validation is per-sink. No validator is shared between destinations with different legal alphabets; a value that becomes a Python identifier is checked with `str.isidentifier()` at that sink, independently of any shell-safety check.
- **C-16 (FM-16).** Every field the parser produces either reaches a consumer or appears in a documented exclusion list with a reason. The layer is an enum with one canonical spelling, defined alongside the probe result dataclass.

Mandatory-category coverage check: faithful-port is mitigated by C-1 (FM-1), C-2 (FM-2), C-3 (FM-3) and C-15 (FM-15); coverage-theatre is mitigated by C-8 (FM-8) and C-9 (FM-9); blast-radius is mitigated by C-6 (FM-6) and C-7 (FM-7).

## Kill criteria

Observables that would say the rewrite should be abandoned or descoped rather than continued. Each is a command, a numeric threshold, or a named test.

- The structural-versus-incidental classification required by C-11 returns fewer than 29 of 57 findings as structural. H1 is falsified at its own stated threshold and the epic's premise does not hold; descope to per-defect fixes in bash.
- Fewer than 5 tests fail against `epic/682-python-executable-path` and pass against the rewrite, measured by running the new suite against both trees. C-8 is unmet and green is being used as the acceptance signal after this document said it could not be.
- `grep -rn 'shell=True' hooks/ scripts/` returns a non-zero count on the implementation branch. C-6 is unmet at the highest-severity path in the system (composite 85) and the rewrite has not improved the thing it most needed to improve.
- `grep -rn '"status"' hooks/ scripts/` returns matches in more than one file after the contract module lands. C-4 is unmet; the rewrite has moved the contract drift rather than removing it, and the epic's main value claim is false.
- `ls scripts/probe/*.sh hooks/create-ticket/*.sh 2>/dev/null | wc -l` returns non-zero at the point the epic is proposed for close. C-13 is unmet and the surface has two implementations.
- `test_path_traversal_rejected`, in whatever form it takes after the rewrite, passes while an escaped directory exists on disk. FM-1 has shipped and FM-8 has shipped with it; the two Launch-Blocking modes with the highest probability are both live.
- A rendered stub whose `Feature` contains a hyphen fails `ast.parse()` on the implementation branch. C-15 is unmet and the rewrite has carried a validator across a sink boundary it was never checked against, which is the defect FM-15 names.
- The implementation diff exceeds 2000 changed lines in a single PR. Not a correctness threshold but a reviewability one: FM-11's blast radius is reviewability, and the mitigation is a disposition table that a reviewer cannot check against a diff that size. Split the ticket.

## Launch-blocking assessment

- [x] Every Tiger has a mitigation stated as a design constraint (C-1 through C-14; the coverage check above enumerates the mandatory three).
- [x] Every Tiger mitigation is grounded in a fact-sheet finding or a `file:line` in the current shell code; the AC3 check resolves every citation.
- [x] Elephants E-1, E-2 and E-3 have deferral rationale and revisit triggers. E-3's trigger has fired once and the outcome is recorded in place rather than in a new elephant.
- [ ] No Launch-Blocking Tiger remains unmitigated **in implementation**. Five are Launch-Blocking (FM-1, FM-2, FM-3, FM-6, FM-8) and all five are mitigated *on paper only*, because the design does not exist yet.

Implementation may proceed: **NO**. Not because a Tiger is unmitigated, but because the mitigations are constraints on a design that has not been written. The step-3 design ticket is the gate. It may proceed immediately and must satisfy or decline C-1 through C-14, with a reason on each declination.

## AC verification for ticket #685

| AC | Requirement | Check | Result |
|---|---|---|---|
| AC1 | at least one `### FM-` entry per category | `grep -c '^- \*\*Category:\*\* <token>'` for each of the six | faithful-port 4, contract-drift 3, blast-radius 2, coverage-theatre 2, scope 2, operational 3 |
| AC2 | eight subheaders on every entry | `grep -c` per subheader against N = count of `^### FM-` | 16 each |
| AC3 | every Fact-sheet basis citation resolves | python3: finding IDs present in the fact sheet, `file:line` within file length | 0 unresolved |
| AC4 | the three mandatory categories restated in Design constraints | grep the coverage-check line for each category and its FM ids | present |
| AC5 | kill criteria are observables | every bullet contains a command, a numeric threshold, or a named test | 8 of 8 |

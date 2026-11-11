---
ticket_refs:
  - siege-analytics/claude-configs-public#1152: tar/venv explicit destinations, own-session data/ scratch tier floor (existence-independent, non-Git safe), unowned-target denial text
---

# Self-review: explicit tar/venv destinations and own-session data/ scratch tier (#1152)

Refs #1152

## Assumptions

Domain(s): software engineering
Working as: software engineer (author of the change)
Geospatial cross-cut: no
Goal source: ticket siege-analytics/claude-configs-public#1152. The ticket predates this work; addenda arrived on 11-05 and 11-10. The scope grew per Root issuecomment-6785389467 (non-Git own-data floor, the same case as operator outbox entry 235).
Goal source verification: PASS: ticket siege-analytics/claude-configs-public#1152 is fit for execution (`./scripts/discipline/evaluate-ticket.sh siege-analytics/claude-configs-public#1152`, after Context/Goal/Acceptance/Design/Assumptions were appended; the original report text is unchanged)
Plan reference: https://github.com/siege-analytics/claude-configs-public/issues/1152#issuecomment-6780585319
Pre-author-inventory: https://github.com/siege-analytics/claude-configs-public/issues/1152#issuecomment-6780585319 (fact sheet F1-F6 against origin/develop 8043c583 before any edit)
Investigate-artifact: https://github.com/siege-analytics/claude-configs-public/issues/1152#issuecomment-6780585319
Pre-mortem-artifact: https://github.com/siege-analytics/claude-configs-public/issues/1152#issuecomment-6780585319
Hostile-review-artifact: https://github.com/siege-analytics/claude-configs-public/issues/1152#issuecomment-6786044258
- Cross-family FINAL SOURCE ACCEPTANCE: Root's Codex/OpenAI review (issuecomment-6786044258, 03:23:14Z, Root entry 244). It pins resolver 9f549d94, task_actions ec991a45 and nongit tests ce3aa0cb, and says "All named findings in this independent review are closed." Its earlier blocker review (issuecomment-6785744722, S3-7) is fixed.
- SAME-FAMILY recovery reviews (claude-opus-5-5, provider fallback under Root entry 236; independence degraded): REJECT issuecomment-6785742465 (2×S1, both fixed); addendum issuecomment-6785835146; re-review issuecomment-6786062860 ACCEPTED cf5943b2 (the variant with discovery-limit pops). On the final bytes (635c28bb) it reports no S1 and reopens the bare-repo ceiling case as R-1 (S3), disclosed below.
- The committed runtime and test bytes EQUAL the accepted snapshot: resolver 9f549d94, task_actions ec991a45, nongit tests ce3aa0cb, explicit tests cafdcb6e. A ceiling control test (kept in the author's scratch) and the discovery-limit pops are deferred to a follow-up after Root rules on the bare-repo residual.
- The first dispatched cross-family reviewer never started (expired OAuth token).
Project-contribution: workers can extract archives and create isolated venvs at their explicit in-scope destination without cwd workarounds. Own-session scratch gets Tier A whether or not the directory exists, including in non-Git workspaces. Every unmodelled shape and every cwd standing in for unknown writes keeps the conservative classification.

## Disclosure: repo-relative hook registration

This worktree's `.claude/settings.json` (lines 23 and 59) registers repo-relative hooks. Both the installed workspace gate and the repo-relative gate evaluate in the authoring session. After the first `hooks/lib` edit, the author's own modified hook code made some of the local gate decisions. The INTERIM record (issuecomment-6785147479) said all of them; that was overbroad. Evidence: one refusal lacked the new `Unowned target:` line, so the installed stack made it.

One intermediate edit made the repo-relative gate deny every gated mutation: the caller passed `scratch_root=` before `task_tier` accepted it. The author stopped. `recover_ready_binding` repaired the signature outside the session (receipt `core1152-runtime-recovery-20261111/receipt.json`). That signature/caller seam was not edited again. The S1-2 fix derives what it needs inside `task_tier` instead. Hosted CI runs the committed hooks independently of the authoring session.

## Gate metadata for scratch execution (guidance gap, Root disposition entry 234)

Root ruling: `repo_root` follows the actual physical target or execution base; exact scratch scope is retained; the workspace operational base is not a made-up Git identity.

Actual case: SU worker B3, gate `b3-1807-reconcile`. The worker kept `repo_root` at the SU checkout, needed for the read-only `git -C <SU> archive`, then switched it to the workspace for scratch edits and pytest. The scope was the scratch directory throughout. The refusals came in this order:
1. "Mutation spans multiple tasks"
2. "Unscoped ... expected target repo=.../siege_utilities"
3. "... expected target repo=.../my-workspace"
4. the tier-B investigate-gate requirement

This PR adds a "Gate metadata for scratch execution" paragraph to `skills/think/task-evidence.md`, and a pointer clause in `skills/think/SKILL.md`. Both are prose only, were added after the first hostile-review pin, and change no enforcement. In particular, a read-only source operand is no reason to widen write scope, and a repository nested inside `data/` needs its own clone-rooted gate.

## Pre-implementation comprehension

The Junior task description is posted on the ticket (issuecomment-6780585319). Reproduced on unmodified 8043c583 before any source edit:
- `tar -xzf <scope>/src.tar.gz -C <scope>` from an outside cwd: rc=2 `Unscoped mutation`, with the cwd in `action()` paths.
- `python3 -m venv <scope>/v1` from an outside cwd: rc=2.
- Own data/ scratch declared tier A: floor B (`unclassified defaults to standard`).
- Non-Git workspace, same own-data directory: B before mkdir, C after (Root's case).

## Senior adversarial checklist

Posted on the ticket (same comment). The parsers are allow-lists that return None, so the generic model applies, for anything unlisted. The scratch floor applies only to explicit, untracked targets in the host-bound own data/.

## Peer review

writing-code:
- `_tar_targets` is an allow-list:
  - flags `zjJvkmp`; value letters `f`/`C`;
  - long options `--extract --create --gzip --bzip2 --xz --verbose --keep-old-files --no-same-owner --no-same-permissions --file --directory --strip-components= --exclude=`;
  - exactly one mode and at most one `-f`; `host:` archives refused;
  - extract: at most one `-C`, and no member operand before it;
  - create: a real `-f` file and no `-C` at all.
- `_venv_targets` models only `python|python3|/abs/pythonX[.Y] -I -m venv [listed flags | --prompt V] DIR...`. Plain `-m venv`, `-Im`, `-P`, `--upgrade-deps`, abbreviations, `--` and `-h` keep the cwd.
- `bounded_write_targets` runs after every existing modelled branch, immediately before the generic fallback. The slash-operand pass still runs first.
- `fallback_paths` records each cwd standing in for unknown writes: the 3 generic sites, the empty-paths cwd default and the `action()` veto path.
- `task_tier` scratch branch. Every one of these must hold for a target to be scratch:
  - `own_session_data_root` is host-bound, symlink-free, and its basename equals the session id;
  - the target is inside it and `repo_root` is not;
  - `git ls-files` runs with the established `_metadata_git_environment()` scrub, and its listing is empty;
  - the target is not a multiply-linked file;
  - the target is not a cwd fallback; the fallback set is derived from `action(command, cwd)`, and failure means no floor;
  - no `.git` entry sits on the path up to own data or beneath a directory target;
  - the path's own policy class is not C.
  Otherwise the target is classified normally. In a non-Git workspace a failed listing counts as empty only if `_outside_git` holds for both `repo_root` and the target. `_outside_git` requires no `.git` entry on or above the path, and Git's exact discovery message under the `_metadata_git_environment()` probe environment.
- Both new Git observations use exactly Root entry 242's contract: `_metadata_git_environment()`, plus `LC_ALL=C` for the probe's diagnostics. Nothing else is popped or scrubbed.
- KNOWN OPEN residual (low likelihood, pending Root's ruling): a BARE repository under own data/ has no `.git` entry, so the ancestor walk cannot see it. With an inherited `GIT_CEILING_DIRECTORIES`, `git rev-parse` there can print the accepted discovery message (the recovery reviewer observed rc 128 with that message; the non-Git-workspace half is inferred, not executed). Popping the two discovery-limit variables in the probe would close it, but that goes beyond Root 242's literal contract and was not taken. If Root wants it, it is a follow-up commit. A non-bare nested repository under an inherited ceiling is covered by the `.git` ancestor walk. The author verified this with a scratch control that passed on these source bytes; that control test is deferred to the follow-up with the pops, so the committed tests equal the accepted snapshot.
- The `Unscoped mutation` denial adds `Unowned target: <path>`.

writing-tests: `hooks/_test/explicit_target_operands.py` (17 tests) and `hooks/_test/nongit_own_data_floor.py` (16 tests, truthful non-Git fixture in the system temp directory). They drive the real `universal-mutation-gate.sh` and `task_tier`, plus real tar and venv runs.

Syntax check: `python3 -m py_compile` on the 4 changed `.py` files reports "compile-ok" (exit 0); `bash -n` passes on both `.test.sh` files.
Test suite: see Test plan.
Doc build: N/A (no docs/ changes)
Notebook API check: N/A (no notebook changes)
Review-gate: N/A (no signal file)

## Lead review

In software engineering, "no widening" holds:
- tar/venv either replace the cwd with an explicit destination they cannot write outside of, or return None.
- `python -I` removes the cwd from `sys.path`. A real-run test shows a cwd `types.py` does not execute.
- The A floor applies only to explicit untracked own-data scratch. A cwd fallback stays B, and C patterns, tracked files, nested repositories, links, foreign sessions and an unbound identity keep normal classification.
- Every Git observation the floor relies on is scrubbed of location/config overrides, and every failure is strict.

Blast radius: `action()` consumers `destructive-guard.sh:61` and `git_command.py:20` see a narrower path list only for tar/venv shapes, plus a new `fallback_paths` key they ignore. The #1166 Git-parser regions and the repaired `task_tier` seam are untouched.

## Findings

| ID | Priority | Description | Resolution |
|----|----------|-------------|------------|
| F-1 | P2 | Self-found (issuecomment-6785504146): in a non-Git workspace, an absent own-data directory regressed from B to C. | fixed |
| F-2 | P1 | Self-found: own-data scratch skipped high-risk path patterns in a Git workspace. | fixed |
| R-1 | P2 | Root issuecomment-6785389467: the floor depended on directory existence in non-Git workspaces. | fixed |
| S1-1 | P1 | Recovery review: cwd module shadowing beyond `venv` under `python -m`. | fixed (-I only) |
| S1-2 | P1 | Recovery review: the cwd fallback was floored as scratch. | fixed (fallback_paths) |
| S3-7 | P1 | Codex review (cross-family) and Root entry 241: the scratch `ls-files` inherited GIT_DIR/GIT_WORK_TREE. | fixed (`_metadata_git_environment()` scrub for this observation only) |
| S3-6 | P2 | `_outside_git` was spoofable by a dangling `gitdir:` file and by an inherited ceiling over a nested repository. | fixed: `.git` ancestor walk and exact discovery message; 3 tests including the ceiling control |
| S3-6b | P3 | Bare repository (no `.git` entry) under own data/ with an inherited `GIT_CEILING_DIRECTORIES`. | KNOWN OPEN residual pending Root's ruling; the discovery-limit pops would close it (follow-up commit) |
| S3-4 | P3 | GNU tar create-mode `-C` ordering was not pinned. | fixed (refused) |
| S3-3 | P3 | Nested clone under a workspace-rooted gate. | test added; workspace-rooted not-yet-cloned case is a residual |
| S3-1, S3-2, S3-5 | P3 | Hardlinks inside a scratch directory; APFS case-variants; interpreter shims. | follow-ups |
| L1 | P3 | `TAR_OPTIONS` is invisible to the hook. | noted: same as the `cd X && tar` route |
| L2 | P3 | `unzip -d`, `curl -o`, `pip --target`, `npm --prefix` and `make -C` still use the cwd fallback. | noted: follow-ups |
| L3 | P3 | `pipeline_state.py:338` session-plans lookup differs from the mutation gate's. | noted: out of scope |

## Adversarial shape audit

Shape space: argv shapes of `tar` (bsdtar/GNU; dash, bundled and traditional) and `python -I -m venv` as mutation-target sources, plus own-data scratch classification under Git, non-Git and redirected-Git conditions.

Fixture-covered shapes:
- tar extract positives: 8 forms + 1 relative `-C`
- tar create positive: 1
- tar refused: 24 forms
- venv isolated positives: 6
- venv refused: 13
- unisolated cwd-module cases: 6
- own-data floor: 33 test methods across the two files

Prose-vs-implementation gap: N/A. No SKILL.md prose claims tar/venv coverage. Sibling commands are follow-ups (L2).

Adversarial frame this round: security engineer
Adversarial fixtures from frame:
- `test_isolated_venv_does_not_run_cwd_modules` (marker-writing cwd `types.py`)
- `test_dangling_gitdir_file_cannot_spoof_outside_git`
- `test_redirected_git_cannot_hide_a_tracked_own_data_file`

## Test plan

- `explicit_target_operands.py`: 17 OK. `nongit_own_data_floor.py`: 16 OK.
- Red before / revert proof:
  - Against baseline 8043c583 libs: explicit fails 21 subtests (all positives); nongit fails 4 plus 2 errors (new API).
  - The S1-1/S1-2 red on the reviewed diff was reproduced with `debug/repro_s1.py`.
  - The S3-6/S3-7 tests discriminate: the old rule accepted "not a git repository: (null)", and the unscrubbed listing floored a tracked file to A.
- Official receipt, bound to the FINAL bytes (resolver 9f549d94, task_actions ec991a45): the focused affected checks, `nongit_own_data_floor` 16 OK and `explicit_target_operands` 17 OK. Also Root's independent acceptance issuecomment-6786044258, and the required hosted CI on the PR head.
- HYBRID run, discovery only and NOT a final-bytes full-suite pass (corrected per Root entry 251): `debug/run_suite.sh` over all 78 `hooks/_test/*.test.sh` in the authoring session gave 74 PASS, 4 FAIL.
  - That run started BEFORE the last runtime edits. While it ran, the resolver toggled between 93651c94 (with discovery-limit pops) and 9f549d94 (final), and a ceiling control test was added to and later removed from `nongit_own_data_floor.py`.
  - An earlier full run was stopped and not restarted.
  - The run's output is kept in the author's scratch.
  - Its 4 failures are triaged as environmental below; the 3 leakage cases also PASS on the final bytes in a CI-like environment (`debug/rerun_clean.sh . real ...`).
  - The `Full-Suite:` trailers of e76445f6 and d6c0e2e describe this run less precisely: the merge commit's "pre-merge full run on e76445f6 bytes" is inaccurate. This section is the corrected record; pushed history is not rewritten.
- Environmental failures proven independent of the diff, by the same failure on baseline in the same environment and a pass in a CI-like environment:
  - `ca_enforcement_manifest` and `verify_enforcement` (no `dist/` until built);
  - `session_signal_resolution`, `universal_mutation_gate` (n0) and `universal_mutation_gate_empty_reporoot` (session `CRAFT_*` environment leakage);
  - `ca_enforcement_runtime` F4/ancestry (fails identically on baseline once its `dist/` is built; the inferred cause is the real Craft parent process).
- Build: `bin/build.py`, `bin/skill-inventory.py` and `bin/generated-source-authority.py` regenerated catalogs. `bin/validate-local.py --mode check` passed end to end (exit 0) before the final source changes; it is re-run before the commit.

## Quantified claims

- "17 / 16 tests OK": from the unittest summary lines of each file.
- "21 subtests; 4 F + 2 E": revert runs against the `debug/revert` baseline copy.
- "24 / 13 / 8 / 6 shapes": counted from the `shapes`/`forms` lists in `explicit_target_operands.py` (one entry per line).
- "+290/-9 in 2 files; +323/-25 in 7 tracked files": `git diff --stat 8043c583 [-- the two libs]`.

## Rework ledger

| Rework trigger | Root skip | Check cost | Rework cost | Ratio |
|---|---|---|---|---|
| Claim regex ERE under BRE grep | did not run the claim's grep first | 1 grep | 3 edits | 1:3 |
| Self-inflicted gate lockout | edited the caller before the callee in a live, repo-relative hook | 1 ordering decision | outside repair plus a multi-hour hold | 1:many |
| Premature self-review draft in repo plans/ | did not check pipeline_state's local-artifact rule | 1 code read | a stop plus the INTERIM record | 1:many |
| F-1/F-2 self-found regressions | tested only Git fixtures; scratch skipped the policy class | non-Git fixture plus a policy check | one rework cycle | 1:3 |
| S1-1/S1-2 review REJECT | shadow check scoped to `venv` only; did not separate fallback cwd from explicit targets | sys.path reasoning; fallback audit | one rework cycle plus a re-review | 1:5 |
| S3-6/S3-7 review findings | trusted the Git message text and the ambient environment | ancestor walk; established scrub | one rework cycle | 1:3 |

## Evidence-predates-work

Artifact: plans/self-review-tar-venv-targets-1152.md, added in the same commit as the work. The first-added commit equals the work commit, so `git merge-base --is-ancestor` gives 0.

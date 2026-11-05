# Review: own-session input and output operands

## Assumptions

Goal source: https://github.com/siege-analytics/claude-configs-public/issues/1166
Plan reference: plans/own-session-operands-1166.md
Pre-mortem-artifact: plans/own-session-operands-1166.md#risks-and-test-plan
Hostile-review-artifact: root and independent source acceptance of task_actions SHA256 af7a232ba8a0039f72127df8a5a5c2ae9cbc32a8b687a39e864efb2e6c1ca330 and focused test SHA256 ab581d0ebf6d9a9f644f2dace884afcb45f3666f56e1586fdcdf422438c50d42.

Only the operand classifier changes runtime behavior. The resolver, installed settings and Git message/protected-operation guards are unchanged. Ordinary cp sources remain reads; mv, link copies and preserved-symlink source cases retain source ownership. Existing copied destinations are inspected within a fixed bound, with aliases and hardlinks still subject to the normal ownership checks. Unsupported --parents copies require explicit destinations.

## Peer review

Root and independent source review accepted the frozen implementation and focused tests. The short-cluster no-target-directory alias case was red before its fix. Commit-plus-file mutation remains rejected with a supported split form; no message-provenance rule is relaxed. The change is limited to issue1166, not tar, venv, clone or generic execution from issue1152.

## Lead review

In software engineering: mutation ownership is based on actual copied names rather than the parent destination operand. The own data/plans root remains a directory, and copied descendants remain checked. Git commit retains its repository target while -F/--file inputs cease to be invented mutation targets; pathspecs after -- remain operands. mkdir mode values cease to be invented paths.

Actual disposable-file effects confirmed cp -p into own data and cp -pR predecessor handoff copying. Source and destination inodes differ for the ordinary copy. Cross-session writes, source-removing mv, destination symlinks/hardlinks, link copies and the no-target-directory alias case are denied by the hook. No live protected Git mutation or installed-session repair is claimed.

Protected combined CI supplies the full hook-suite proof before merge. No local full workflow was started for this slice. Rollback is reverting the operand-classifier change through the normal reviewed path; no installation has occurred.

## Quantified claims

The focused log /tmp/own-session-1166-focused-final.log reports 9 tests passing. The initial red log /tmp/own-session-1166-red.log reports 5 failures before implementation; /tmp/own-session-1166-cluster-red.log records the additional hostile short-cluster failure before its fix. Native test-evidence producer will rerun the focused tests at committed HEAD for exact source content before push.

## Scanner

The first selected staged scan completed non-clean: a new prose adverb was removed. Its remaining AST findings are the existing task_actions handlers already reviewed in the parent1161 artifact. The Python-reader handler returns False, preserving denial; the test locator expects pytest.raises although the suites observe hook status and diagnostics. This is a heuristic disposition, not a claim that every exception branch is covered. Final selected scan completed with exit1 and the same 11 AST heuristic findings, with no new lexical findings. These handlers and the narrowed false-positive interpretation are documented in the parent plans/self-review-github-project-1161.md; source review accepted this bounded change.

## Additional focused checks

The selected existing ownership/option tests passed (4 tests, /tmp/own-session-1166-existing-focused.log); the existing real GNU cp abbreviation control passed (1 test, /tmp/own-session-1166-cp-existing.log). No full local workflow was launched.

## Final selected raw scanner output

```text
hooks/lib/task_actions.py:219:writing-code-7-silent-swallow(Return): except (ValueError, SyntaxError): <Return>
hooks/lib/task_actions.py:219:writing-tests-5: except ValueError: no matching pytest.raises(ValueError) in task_keyed_gates.py
hooks/lib/task_actions.py:219:writing-tests-5: except SyntaxError: no matching pytest.raises(SyntaxError) in task_keyed_gates.py
hooks/lib/task_actions.py:437:writing-tests-5: except SubprocessError: no matching pytest.raises(SubprocessError) in task_keyed_gates.py
hooks/lib/task_actions.py:437:writing-tests-5: except OSError: no matching pytest.raises(OSError) in task_keyed_gates.py
hooks/lib/task_actions.py:571:writing-tests-5: except Exception: no matching pytest.raises(Exception) in task_keyed_gates.py
hooks/lib/task_actions.py:635:writing-tests-5: except OSError: no matching pytest.raises(OSError) in task_keyed_gates.py
hooks/lib/task_actions.py:691:writing-tests-5: except OSError: no matching pytest.raises(OSError) in task_keyed_gates.py
hooks/lib/task_actions.py:691:writing-tests-5: except ValueError: no matching pytest.raises(ValueError) in task_keyed_gates.py
hooks/lib/task_actions.py:826:writing-tests-5: except UnknownShape: no matching pytest.raises(UnknownShape) in task_keyed_gates.py
hooks/lib/task_actions.py:1093:writing-tests-5: except UnknownShape: no matching pytest.raises(UnknownShape) in task_keyed_gates.py

scanned: writing-prose:1-4 (stylistic; broader Unicode class), writing-code:2 (history references in code comments), writing-code:4 (Django ORM kwarg validation, same-file models; AST), writing-code:7 (silent error swallowing; AST), writing-code:8 (optional-import callsite guards; AST), writing-code:9 (silently-dropped parameters; AST scoped visitor), writing-code:15 (unbounded blocking I/O; AST, incl. Popen chains, Session/Client instance methods, invalid literal timeouts), writing-tests:3 (skip messages must be actionable), writing-tests:5 (untested named exception handlers, cross-file; AST), writing-claims:2 (countable claims need Verified-by trailer), rule citations in messages require Rule-executed evidence (#282), writing-releases:3 (deprecation messages need version+removal-keyword anchors; AST). Not mechanized (judgment-bound): writing-code:1/3/5/6, writing-tests:1/2/4, writing-claims:1/3, writing-releases:1/2.
violations: 11
```

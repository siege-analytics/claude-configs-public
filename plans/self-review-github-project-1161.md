# Review: task-owned project item-add

## Assumptions

Goal source: https://github.com/siege-analytics/claude-configs-public/issues/1161
Plan reference: plans/github-project-task-scope-1161.md
Pre-mortem-artifact: plans/github-project-task-scope-1161.md#risks-and-test-plan
Hostile-review-artifact: Root source review identified API aliases, canonical identity conflicts, literal task_id-only compatibility and source-policy risk floor; corrected with negative controls. Independent final source review accepted the runtime snapshot.

Core ships no ElectInfo grant. The client source owner delivers its existing standing board instruction through a fixed installed policy. The exact current task issue must match; task fields cannot choose policy or extend permission. Remote-only administrative additions use no invented filesystem target or code-edit evidence. Mixed writes retain normal gate requirements. Item-edit and GraphQL remain unmodeled; issue1161 stays open.

## Peer review

Root review corrections are incorporated. The actual client assembled-hook fixture passed using immutable source tree4a5723a911fcbfab330ed04a0332a0b90adba0e9, including the reporter's canonical task_id-only gate and conflicting identity rejection. Independent source review accepted the runtime snapshot and reran the focused suite successfully. Independent scanner disposition accepted the narrowed heuristic interpretation; exact-head protected CI remains pending at candidate publication; no merge or release acceptance is claimed.

## Lead review

In software engineering: supported item-add is modeled as a remote operation, fixed standing policy is separate from task identity, and every mixed local target still passes its own scoped gate. Tests invoke hooks as classifiers, never gh. Source and isolated consumer hook validators passed. Focused project tests, existing task-keyed tests and reader safety tests passed. Local full hook execution remains in progress; its early CA-manifest failure came from missing repository dist, was repaired by the normal build, and that suite reran successfully. Protected full CI is required before merge. Review-risk regression execution passed after refreshing the stale inventory reported by its first run.

Canary/rollback: isolated installed hook fixtures and actual client overlay parity prove the intended decision without a board write. Default policy grants nothing. No installation performed; reverting this feature restores the previous hook behavior. Root owns live installation and the original authorized board operation receipt.

## Quantified claims

The test logs report 13 focused project tests, 77 task-keyed tests and 16 reader safety tests passing. Evidence: /tmp/github-project-1161-focused-final6.log, /tmp/github-project-1161-task-gates.log, /tmp/github-project-1161-reader.log. Source is staged without unrelated test fixtures; git diff --cached --stat records the file scope.

## Scanner disposition proposal

Full selected staged snapshot scan completed with exit1, not clean. Raw output is retained below. No --ignore or source exclusion was used. Scanner snapshot tree: 4a5723a911fcbfab330ed04a0332a0b90adba0e9. Base: f004df3c66cf6374548cfc49d0e49c375aa4376c. Source hashes: task_actions0b0ee6306d3e04b1f6e2db5fc2ad12f988eee18f7f32c98107e9234f2b938bdb; resolvercb86c3f8e620e7b19ca41ccda94e380647050a057a2167ff5910b2a5458d87a8. Scanner/config identity is the unchanged source in that tree.

Each row records a false-positive disposition proposal, not an inherited-defect waiver or a claim of exception-branch coverage. The scanner expects a matching pytest.raises idiom in task_keyed_gates.py; the tests use hook exit status/diagnostic and scope decisions instead. This locator mismatch does not prove every exception branch is covered. The code-7 return sites signal denial, non-reader, unavailable evidence or no gate; they do not turn failure into success. A new project-policy handler reports its cause through the visible hook error. Falsification for every row: the cited exception path returns authority/success, loses its diagnostic where one is required, or the stated negative controls fail. Root and independent review accepted the row-level scanner dispositions with the explicit limitation that the locator mismatch is not exception-branch coverage; no blanket clean-scan claim is made.

| Location | Rule | Enclosing behavior | Base line | Evidence |
|---|---|---|---|---|
| hooks/lib/resolve-think-gate.py:393 | writing-code-7-silent-swallow(Return) | _within | 392 | task_keyed_gates.py hostile scope/session/unknown-shape controls and reader_git_safety.py; helper returns a denial/non-reader/unavailable sentinel rather than claiming success |
| hooks/lib/resolve-think-gate.py:632 | writing-code-7-silent-swallow(Return) | find_gate_for_repo | 631 | task_keyed_gates.py hostile scope/session/unknown-shape controls and reader_git_safety.py; helper returns a denial/non-reader/unavailable sentinel rather than claiming success |
| hooks/lib/resolve-think-gate.py:896 | writing-code-7-silent-swallow(Return) | _git_lines | 805 | task_keyed_gates.py hostile scope/session/unknown-shape controls and reader_git_safety.py; helper returns a denial/non-reader/unavailable sentinel rather than claiming success |
| hooks/lib/resolve-think-gate.py:909 | writing-code-7-silent-swallow(Return) | _lone_git_commit | 818 | task_keyed_gates.py hostile scope/session/unknown-shape controls and reader_git_safety.py; helper returns a denial/non-reader/unavailable sentinel rather than claiming success |
| hooks/lib/resolve-think-gate.py:987 | writing-code-7-silent-swallow(Return) | _load | 896 | task_keyed_gates.py hostile scope/session/unknown-shape controls and reader_git_safety.py; helper returns a denial/non-reader/unavailable sentinel rather than claiming success |
| hooks/lib/resolve-think-gate.py:118 | writing-tests-5 | host_binding_present | 117 | task_keyed_gates.py hostile scope/session/unknown-shape controls and reader_git_safety.py; helper returns a denial/non-reader/unavailable sentinel rather than claiming success |
| hooks/lib/resolve-think-gate.py:118 | writing-tests-5 | host_binding_present | 117 | task_keyed_gates.py hostile scope/session/unknown-shape controls and reader_git_safety.py; helper returns a denial/non-reader/unavailable sentinel rather than claiming success |
| hooks/lib/resolve-think-gate.py:164 | writing-tests-5 | session_id_from_env | 163 | task_keyed_gates.py hostile scope/session/unknown-shape controls and reader_git_safety.py; helper returns a denial/non-reader/unavailable sentinel rather than claiming success |
| hooks/lib/resolve-think-gate.py:227 | writing-tests-5 | _git_origin | 226 | task_keyed_gates.py hostile scope/session/unknown-shape controls and reader_git_safety.py; helper returns a denial/non-reader/unavailable sentinel rather than claiming success |
| hooks/lib/resolve-think-gate.py:242 | writing-tests-5 | _target_repo | 241 | task_keyed_gates.py hostile scope/session/unknown-shape controls and reader_git_safety.py; helper returns a denial/non-reader/unavailable sentinel rather than claiming success |
| hooks/lib/resolve-think-gate.py:314 | writing-tests-5 | _project_repo_field | 313 | task_keyed_gates.py hostile scope/session/unknown-shape controls and reader_git_safety.py; helper returns a denial/non-reader/unavailable sentinel rather than claiming success |
| hooks/lib/resolve-think-gate.py:335 | writing-tests-5 | _same_repo | 334 | task_keyed_gates.py hostile scope/session/unknown-shape controls and reader_git_safety.py; helper returns a denial/non-reader/unavailable sentinel rather than claiming success |
| hooks/lib/resolve-think-gate.py:335 | writing-tests-5 | _same_repo | 334 | task_keyed_gates.py hostile scope/session/unknown-shape controls and reader_git_safety.py; helper returns a denial/non-reader/unavailable sentinel rather than claiming success |
| hooks/lib/resolve-think-gate.py:335 | writing-tests-5 | _same_repo | 334 | task_keyed_gates.py hostile scope/session/unknown-shape controls and reader_git_safety.py; helper returns a denial/non-reader/unavailable sentinel rather than claiming success |
| hooks/lib/resolve-think-gate.py:393 | writing-tests-5 | _within | 392 | task_keyed_gates.py hostile scope/session/unknown-shape controls and reader_git_safety.py; helper returns a denial/non-reader/unavailable sentinel rather than claiming success |
| hooks/lib/resolve-think-gate.py:393 | writing-tests-5 | _within | 392 | task_keyed_gates.py hostile scope/session/unknown-shape controls and reader_git_safety.py; helper returns a denial/non-reader/unavailable sentinel rather than claiming success |
| hooks/lib/resolve-think-gate.py:632 | writing-tests-5 | find_gate_for_repo | 631 | task_keyed_gates.py hostile scope/session/unknown-shape controls and reader_git_safety.py; helper returns a denial/non-reader/unavailable sentinel rather than claiming success |
| hooks/lib/resolve-think-gate.py:632 | writing-tests-5 | find_gate_for_repo | 631 | task_keyed_gates.py hostile scope/session/unknown-shape controls and reader_git_safety.py; helper returns a denial/non-reader/unavailable sentinel rather than claiming success |
| hooks/lib/resolve-think-gate.py:858 | writing-tests-5 | select_project_task | new | github_project_scope.py:test_policy_is_fixed_strict_and_not_a_symlink and test_gate_and_policy_absence_are_explained; CLI returns a visible remote-scope denial |
| hooks/lib/resolve-think-gate.py:858 | writing-tests-5 | select_project_task | new | github_project_scope.py:test_policy_is_fixed_strict_and_not_a_symlink and test_gate_and_policy_absence_are_explained; CLI returns a visible remote-scope denial |
| hooks/lib/resolve-think-gate.py:858 | writing-tests-5 | select_project_task | new | github_project_scope.py:test_policy_is_fixed_strict_and_not_a_symlink and test_gate_and_policy_absence_are_explained; CLI returns a visible remote-scope denial |
| hooks/lib/resolve-think-gate.py:896 | writing-tests-5 | _git_lines | 805 | task_keyed_gates.py hostile scope/session/unknown-shape controls and reader_git_safety.py; helper returns a denial/non-reader/unavailable sentinel rather than claiming success |
| hooks/lib/resolve-think-gate.py:896 | writing-tests-5 | _git_lines | 805 | task_keyed_gates.py hostile scope/session/unknown-shape controls and reader_git_safety.py; helper returns a denial/non-reader/unavailable sentinel rather than claiming success |
| hooks/lib/resolve-think-gate.py:909 | writing-tests-5 | _lone_git_commit | 818 | task_keyed_gates.py hostile scope/session/unknown-shape controls and reader_git_safety.py; helper returns a denial/non-reader/unavailable sentinel rather than claiming success |
| hooks/lib/resolve-think-gate.py:972 | writing-tests-5 | task_tier | 881 | task_keyed_gates.py hostile scope/session/unknown-shape controls and reader_git_safety.py; helper returns a denial/non-reader/unavailable sentinel rather than claiming success |
| hooks/lib/resolve-think-gate.py:987 | writing-tests-5 | _load | 896 | task_keyed_gates.py hostile scope/session/unknown-shape controls and reader_git_safety.py; helper returns a denial/non-reader/unavailable sentinel rather than claiming success |
| hooks/lib/resolve-think-gate.py:987 | writing-tests-5 | _load | 896 | task_keyed_gates.py hostile scope/session/unknown-shape controls and reader_git_safety.py; helper returns a denial/non-reader/unavailable sentinel rather than claiming success |
| hooks/lib/resolve-think-gate.py:987 | writing-tests-5 | _load | 896 | task_keyed_gates.py hostile scope/session/unknown-shape controls and reader_git_safety.py; helper returns a denial/non-reader/unavailable sentinel rather than claiming success |
| hooks/lib/resolve-think-gate.py:444 | writing-tests-5 | _remember_canonical | 443 | task_keyed_gates.py hostile scope/session/unknown-shape controls and reader_git_safety.py; helper returns a denial/non-reader/unavailable sentinel rather than claiming success |
| hooks/lib/resolve-think-gate.py:732 | writing-tests-5 | own_session_path | 731 | task_keyed_gates.py hostile scope/session/unknown-shape controls and reader_git_safety.py; helper returns a denial/non-reader/unavailable sentinel rather than claiming success |
| hooks/lib/resolve-think-gate.py:734 | writing-tests-5 | own_session_path | 733 | task_keyed_gates.py hostile scope/session/unknown-shape controls and reader_git_safety.py; helper returns a denial/non-reader/unavailable sentinel rather than claiming success |
| hooks/lib/resolve-think-gate.py:1021 | writing-tests-5 | main | 930 | task_keyed_gates.py hostile scope/session/unknown-shape controls and reader_git_safety.py; helper returns a denial/non-reader/unavailable sentinel rather than claiming success |
| hooks/lib/resolve-think-gate.py:773 | writing-tests-5 | resolve_action | 764 | task_keyed_gates.py hostile scope/session/unknown-shape controls and reader_git_safety.py; helper returns a denial/non-reader/unavailable sentinel rather than claiming success |
| hooks/lib/resolve-think-gate.py:773 | writing-tests-5 | resolve_action | 764 | task_keyed_gates.py hostile scope/session/unknown-shape controls and reader_git_safety.py; helper returns a denial/non-reader/unavailable sentinel rather than claiming success |
| hooks/lib/resolve-think-gate.py:487 | writing-tests-5 | _session_thinks | 486 | task_keyed_gates.py hostile scope/session/unknown-shape controls and reader_git_safety.py; helper returns a denial/non-reader/unavailable sentinel rather than claiming success |
| hooks/lib/resolve-think-gate.py:487 | writing-tests-5 | _session_thinks | 486 | task_keyed_gates.py hostile scope/session/unknown-shape controls and reader_git_safety.py; helper returns a denial/non-reader/unavailable sentinel rather than claiming success |
| hooks/lib/task_actions.py:219 | writing-code-7-silent-swallow(Return) | _python_read | 219 | task_keyed_gates.py hostile scope/session/unknown-shape controls and reader_git_safety.py; helper returns a denial/non-reader/unavailable sentinel rather than claiming success |
| hooks/lib/task_actions.py:219 | writing-tests-5 | _python_read | 219 | task_keyed_gates.py hostile scope/session/unknown-shape controls and reader_git_safety.py; helper returns a denial/non-reader/unavailable sentinel rather than claiming success |
| hooks/lib/task_actions.py:219 | writing-tests-5 | _python_read | 219 | task_keyed_gates.py hostile scope/session/unknown-shape controls and reader_git_safety.py; helper returns a denial/non-reader/unavailable sentinel rather than claiming success |
| hooks/lib/task_actions.py:381 | writing-tests-5 | _git_toplevel | 381 | task_keyed_gates.py hostile scope/session/unknown-shape controls and reader_git_safety.py; helper returns a denial/non-reader/unavailable sentinel rather than claiming success |
| hooks/lib/task_actions.py:381 | writing-tests-5 | _git_toplevel | 381 | task_keyed_gates.py hostile scope/session/unknown-shape controls and reader_git_safety.py; helper returns a denial/non-reader/unavailable sentinel rather than claiming success |
| hooks/lib/task_actions.py:515 | writing-tests-5 | released_read_verdict | 515 | task_keyed_gates.py hostile scope/session/unknown-shape controls and reader_git_safety.py; helper returns a denial/non-reader/unavailable sentinel rather than claiming success |
| hooks/lib/task_actions.py:579 | writing-tests-5 | _test_receipt_record | 579 | task_keyed_gates.py hostile scope/session/unknown-shape controls and reader_git_safety.py; helper returns a denial/non-reader/unavailable sentinel rather than claiming success |
| hooks/lib/task_actions.py:635 | writing-tests-5 | _metadata_file | 635 | task_keyed_gates.py hostile scope/session/unknown-shape controls and reader_git_safety.py; helper returns a denial/non-reader/unavailable sentinel rather than claiming success |
| hooks/lib/task_actions.py:635 | writing-tests-5 | _metadata_file | 635 | task_keyed_gates.py hostile scope/session/unknown-shape controls and reader_git_safety.py; helper returns a denial/non-reader/unavailable sentinel rather than claiming success |
| hooks/lib/task_actions.py:770 | writing-tests-5 | _action | 738 | task_keyed_gates.py hostile scope/session/unknown-shape controls and reader_git_safety.py; helper returns a denial/non-reader/unavailable sentinel rather than claiming success |
| hooks/lib/task_actions.py:1027 | writing-tests-5 | _action | 975 | task_keyed_gates.py hostile scope/session/unknown-shape controls and reader_git_safety.py; helper returns a denial/non-reader/unavailable sentinel rather than claiming success |

## Raw scan output

```text
hooks/lib/resolve-think-gate.py:393:writing-code-7-silent-swallow(Return): except (ValueError, TypeError): <Return>
hooks/lib/resolve-think-gate.py:632:writing-code-7-silent-swallow(Return): except (ValueError, TypeError): <Return>
hooks/lib/resolve-think-gate.py:896:writing-code-7-silent-swallow(Return): except (OSError, SubprocessError): <Return>
hooks/lib/resolve-think-gate.py:909:writing-code-7-silent-swallow(Return): except UnknownShape: <Return>
hooks/lib/resolve-think-gate.py:987:writing-code-7-silent-swallow(Return): except (OSError, ValueError, TypeError): <Return>
hooks/lib/resolve-think-gate.py:118:writing-tests-5: except ValueError: no matching pytest.raises(ValueError) in task_keyed_gates.py
hooks/lib/resolve-think-gate.py:118:writing-tests-5: except TypeError: no matching pytest.raises(TypeError) in task_keyed_gates.py
hooks/lib/resolve-think-gate.py:164:writing-tests-5: except Exception: no matching pytest.raises(Exception) in task_keyed_gates.py
hooks/lib/resolve-think-gate.py:227:writing-tests-5: except Exception: no matching pytest.raises(Exception) in task_keyed_gates.py
hooks/lib/resolve-think-gate.py:242:writing-tests-5: except Exception: no matching pytest.raises(Exception) in task_keyed_gates.py
hooks/lib/resolve-think-gate.py:314:writing-tests-5: except Exception: no matching pytest.raises(Exception) in task_keyed_gates.py
hooks/lib/resolve-think-gate.py:335:writing-tests-5: except OSError: no matching pytest.raises(OSError) in task_keyed_gates.py
hooks/lib/resolve-think-gate.py:335:writing-tests-5: except TypeError: no matching pytest.raises(TypeError) in task_keyed_gates.py
hooks/lib/resolve-think-gate.py:335:writing-tests-5: except ValueError: no matching pytest.raises(ValueError) in task_keyed_gates.py
hooks/lib/resolve-think-gate.py:393:writing-tests-5: except ValueError: no matching pytest.raises(ValueError) in task_keyed_gates.py
hooks/lib/resolve-think-gate.py:393:writing-tests-5: except TypeError: no matching pytest.raises(TypeError) in task_keyed_gates.py
hooks/lib/resolve-think-gate.py:632:writing-tests-5: except ValueError: no matching pytest.raises(ValueError) in task_keyed_gates.py
hooks/lib/resolve-think-gate.py:632:writing-tests-5: except TypeError: no matching pytest.raises(TypeError) in task_keyed_gates.py
hooks/lib/resolve-think-gate.py:858:writing-tests-5: except OSError: no matching pytest.raises(OSError) in task_keyed_gates.py
hooks/lib/resolve-think-gate.py:858:writing-tests-5: except ValueError: no matching pytest.raises(ValueError) in task_keyed_gates.py
hooks/lib/resolve-think-gate.py:858:writing-tests-5: except TypeError: no matching pytest.raises(TypeError) in task_keyed_gates.py
hooks/lib/resolve-think-gate.py:896:writing-tests-5: except OSError: no matching pytest.raises(OSError) in task_keyed_gates.py
hooks/lib/resolve-think-gate.py:896:writing-tests-5: except SubprocessError: no matching pytest.raises(SubprocessError) in task_keyed_gates.py
hooks/lib/resolve-think-gate.py:909:writing-tests-5: except UnknownShape: no matching pytest.raises(UnknownShape) in task_keyed_gates.py
hooks/lib/resolve-think-gate.py:972:writing-tests-5: except Exception: no matching pytest.raises(Exception) in task_keyed_gates.py
hooks/lib/resolve-think-gate.py:987:writing-tests-5: except OSError: no matching pytest.raises(OSError) in task_keyed_gates.py
hooks/lib/resolve-think-gate.py:987:writing-tests-5: except ValueError: no matching pytest.raises(ValueError) in task_keyed_gates.py
hooks/lib/resolve-think-gate.py:987:writing-tests-5: except TypeError: no matching pytest.raises(TypeError) in task_keyed_gates.py
hooks/lib/resolve-think-gate.py:444:writing-tests-5: except FileExistsError: no matching pytest.raises(FileExistsError) in task_keyed_gates.py
hooks/lib/resolve-think-gate.py:732:writing-tests-5: except FileNotFoundError: no matching pytest.raises(FileNotFoundError) in task_keyed_gates.py
hooks/lib/resolve-think-gate.py:734:writing-tests-5: except OSError: no matching pytest.raises(OSError) in task_keyed_gates.py
hooks/lib/resolve-think-gate.py:1021:writing-tests-5: except Exception: no matching pytest.raises(Exception) in task_keyed_gates.py
hooks/lib/resolve-think-gate.py:773:writing-tests-5: except OSError: no matching pytest.raises(OSError) in task_keyed_gates.py
hooks/lib/resolve-think-gate.py:773:writing-tests-5: except ValueError: no matching pytest.raises(ValueError) in task_keyed_gates.py
hooks/lib/resolve-think-gate.py:487:writing-tests-5: except OSError: no matching pytest.raises(OSError) in task_keyed_gates.py
hooks/lib/resolve-think-gate.py:487:writing-tests-5: except ValueError: no matching pytest.raises(ValueError) in task_keyed_gates.py
hooks/lib/task_actions.py:219:writing-code-7-silent-swallow(Return): except (ValueError, SyntaxError): <Return>
hooks/lib/task_actions.py:219:writing-tests-5: except ValueError: no matching pytest.raises(ValueError) in task_keyed_gates.py
hooks/lib/task_actions.py:219:writing-tests-5: except SyntaxError: no matching pytest.raises(SyntaxError) in task_keyed_gates.py
hooks/lib/task_actions.py:381:writing-tests-5: except SubprocessError: no matching pytest.raises(SubprocessError) in task_keyed_gates.py
hooks/lib/task_actions.py:381:writing-tests-5: except OSError: no matching pytest.raises(OSError) in task_keyed_gates.py
hooks/lib/task_actions.py:515:writing-tests-5: except Exception: no matching pytest.raises(Exception) in task_keyed_gates.py
hooks/lib/task_actions.py:579:writing-tests-5: except OSError: no matching pytest.raises(OSError) in task_keyed_gates.py
hooks/lib/task_actions.py:635:writing-tests-5: except OSError: no matching pytest.raises(OSError) in task_keyed_gates.py
hooks/lib/task_actions.py:635:writing-tests-5: except ValueError: no matching pytest.raises(ValueError) in task_keyed_gates.py
hooks/lib/task_actions.py:770:writing-tests-5: except UnknownShape: no matching pytest.raises(UnknownShape) in task_keyed_gates.py
hooks/lib/task_actions.py:1027:writing-tests-5: except UnknownShape: no matching pytest.raises(UnknownShape) in task_keyed_gates.py

scanned: writing-prose:1-4 (stylistic; broader Unicode class), writing-code:2 (history references in code comments), writing-code:4 (Django ORM kwarg validation, same-file models; AST), writing-code:7 (silent error swallowing; AST), writing-code:8 (optional-import callsite guards; AST), writing-code:9 (silently-dropped parameters; AST scoped visitor), writing-code:15 (unbounded blocking I/O; AST, incl. Popen chains, Session/Client instance methods, invalid literal timeouts), writing-tests:3 (skip messages must be actionable), writing-tests:5 (untested named exception handlers, cross-file; AST), writing-claims:2 (countable claims need Verified-by trailer), rule citations in messages require Rule-executed evidence (#282), writing-releases:3 (deprecation messages need version+removal-keyword anchors; AST). Not mechanized (judgment-bound): writing-code:1/3/5/6, writing-tests:1/2/4, writing-claims:1/3, writing-releases:1/2.
violations: 47
```

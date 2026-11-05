# Review: verified own-task Status updates

## Assumptions

Goal source: https://github.com/siege-analytics/claude-configs-public/issues/1193
Plan reference: plans/github-project-status-1193.md
Pre-author-inventory: reviewed d4feed parent1185 and actual1161/client authority, parser/resolver and bounded runner before code; issue1193 and design/investigation/pre-mortem comment6652737011 preceded implementation.
Investigate-artifact: plans/github-project-status-1193.md#design-and-investigation
Pre-mortem-artifact: plans/github-project-status-1193.md#pre-mortem
Hostile-review-artifact: https://github.com/siege-analytics/claude-configs-public/issues/1193

This feature is stacked on reviewed d4feed parent1185, not a deployment of that parent. Original item-add delivery remains independent. Core's installed standing policy remains empty; client publication of a separate Status grant is necessary and outside this feature. No task or response supplies authority. Official GitHub Projects schema was checked for the actual item/field/project relations.

## Peer review

Root found and corrected a new global task-ambiguity precondition. Live proof now yields an exact issue before reusing existing per-issue owner selection, preserving unrelated task independence. Root independently accepted final source, forward cases and all62 bounded scanner dispositions, verifying the three runtime hashes,56 pinned-parent unchanged handler rows and6 new visible-denial handler rows. This is not hosted CI, installed-runtime or exhaustive exception coverage acceptance. No live board write, installation or protected merge occurred.

## Lead review

The only new supported shape is literal item-edit with four unique ID flags and a fixed single-select Status grant. A single source query proves project/item/content/field/option relations; no supplied GraphQL, attestation or stale cache can substitute. Done and resetting existing Done remain operator-owned. Other field types/reset/admin/destructive operations remain denied.

One Status edit per invocation bounds amplification. Reused selector/process-group runner bounds query time, stream output and cleanup; malformed/partial/paginated/oversized responses fail closed. The live read and later CLI mutation are not an atomic GitHub transaction; concurrent remote schema edits and network availability remain practical limitations. Positive tests use a controlled gh process under the real hook, never a production test exemption.

Mixed local writes need the same task and its local tier evidence; remote permission cannot replace those requirements. The new helper has an explicit TierC policy floor and audited enforcement dependency. Rollback reverts this new lane through reviewed source publication; existing add-only behavior remains.

## Quantified claims

Red-first baseline newpositive failed because item-edit was unsupported. Final11 focused real-hook tests passed19.156s; existing add13 passed13.633s. Focused dependency audit and explicit helperC floor passed. A descendant heartbeat stops after timeout, rather than merely observing a denied parent. Final current-head native producer and protected CI are separate evidence. No full local suite or live callback acceptance is claimed.

## Scanner dispositions

Selected scan exits1 with62 AST heuristic findings and no lexical findings. The new helper catches KeyError/TypeError/AttributeError only to translate malformed relationships into visible denial with preserved cause. Actual null/missing/malformed-owner hook cases exercise those failure shapes; a pytest.raises locator does not recognize internally handled hook errors. This does not prove every exception branch is covered. New resolver boundary catches lookup/validation failure and returns an explicit remote-scope denial. Its test locator points at task_keyed_gates instead of the composition fixture.

The remaining findings are inherited task_actions/resolver sentinel-denial or unavailable-evidence handlers and matching test-locator expectations. Each raw row, pinned-parent AST provenance and handler-specific disposition is recorded in plans/project-status-1193-scanner-ledger.json (62 rows;6 new-handler rows); no blanket clean-scan claim or exception-coverage waiver is made. Rejection would be required if a sentinel granted authority, a new failure became silent success or its cited negative control failed.

## Raw selected scanner output

```text
hooks/lib/github-project-status.py:105:writing-tests-5: except KeyError: no matching pytest.raises(KeyError) in github_project_status.py
hooks/lib/github-project-status.py:105:writing-tests-5: except TypeError: no matching pytest.raises(TypeError) in github_project_status.py
hooks/lib/github-project-status.py:105:writing-tests-5: except AttributeError: no matching pytest.raises(AttributeError) in github_project_status.py
hooks/lib/resolve-think-gate.py:393:writing-code-7-silent-swallow(Return): except (ValueError, TypeError): <Return>
hooks/lib/resolve-think-gate.py:632:writing-code-7-silent-swallow(Return): except (ValueError, TypeError): <Return>
hooks/lib/resolve-think-gate.py:916:writing-code-7-silent-swallow(Return): except (OSError, SubprocessError): <Return>
hooks/lib/resolve-think-gate.py:929:writing-code-7-silent-swallow(Return): except UnknownShape: <Return>
hooks/lib/resolve-think-gate.py:993:writing-code-7-silent-swallow(Return): except (UnknownShape, OSError, SubprocessError): <Return>
hooks/lib/resolve-think-gate.py:1006:writing-code-7-silent-swallow(Return): except UnknownShape: <Return>
hooks/lib/resolve-think-gate.py:1163:writing-code-7-silent-swallow(Return): except (OSError, ValueError, TypeError): <Return>
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
hooks/lib/resolve-think-gate.py:864:writing-tests-5: except OSError: no matching pytest.raises(OSError) in task_keyed_gates.py
hooks/lib/resolve-think-gate.py:864:writing-tests-5: except ValueError: no matching pytest.raises(ValueError) in task_keyed_gates.py
hooks/lib/resolve-think-gate.py:864:writing-tests-5: except TypeError: no matching pytest.raises(TypeError) in task_keyed_gates.py
hooks/lib/resolve-think-gate.py:916:writing-tests-5: except OSError: no matching pytest.raises(OSError) in task_keyed_gates.py
hooks/lib/resolve-think-gate.py:916:writing-tests-5: except SubprocessError: no matching pytest.raises(SubprocessError) in task_keyed_gates.py
hooks/lib/resolve-think-gate.py:929:writing-tests-5: except UnknownShape: no matching pytest.raises(UnknownShape) in task_keyed_gates.py
hooks/lib/resolve-think-gate.py:993:writing-tests-5: except UnknownShape: no matching pytest.raises(UnknownShape) in task_keyed_gates.py
hooks/lib/resolve-think-gate.py:993:writing-tests-5: except OSError: no matching pytest.raises(OSError) in task_keyed_gates.py
hooks/lib/resolve-think-gate.py:993:writing-tests-5: except SubprocessError: no matching pytest.raises(SubprocessError) in task_keyed_gates.py
hooks/lib/resolve-think-gate.py:1006:writing-tests-5: except UnknownShape: no matching pytest.raises(UnknownShape) in task_keyed_gates.py
hooks/lib/resolve-think-gate.py:1148:writing-tests-5: except Exception: no matching pytest.raises(Exception) in task_keyed_gates.py
hooks/lib/resolve-think-gate.py:1163:writing-tests-5: except OSError: no matching pytest.raises(OSError) in task_keyed_gates.py
hooks/lib/resolve-think-gate.py:1163:writing-tests-5: except ValueError: no matching pytest.raises(ValueError) in task_keyed_gates.py
hooks/lib/resolve-think-gate.py:1163:writing-tests-5: except TypeError: no matching pytest.raises(TypeError) in task_keyed_gates.py
hooks/lib/resolve-think-gate.py:444:writing-tests-5: except FileExistsError: no matching pytest.raises(FileExistsError) in task_keyed_gates.py
hooks/lib/resolve-think-gate.py:732:writing-tests-5: except FileNotFoundError: no matching pytest.raises(FileNotFoundError) in task_keyed_gates.py
hooks/lib/resolve-think-gate.py:734:writing-tests-5: except OSError: no matching pytest.raises(OSError) in task_keyed_gates.py
hooks/lib/resolve-think-gate.py:1197:writing-tests-5: except Exception: no matching pytest.raises(Exception) in task_keyed_gates.py
hooks/lib/resolve-think-gate.py:773:writing-tests-5: except OSError: no matching pytest.raises(OSError) in task_keyed_gates.py
hooks/lib/resolve-think-gate.py:773:writing-tests-5: except ValueError: no matching pytest.raises(ValueError) in task_keyed_gates.py
hooks/lib/resolve-think-gate.py:880:writing-tests-5: except OSError: no matching pytest.raises(OSError) in task_keyed_gates.py
hooks/lib/resolve-think-gate.py:880:writing-tests-5: except ValueError: no matching pytest.raises(ValueError) in task_keyed_gates.py
hooks/lib/resolve-think-gate.py:880:writing-tests-5: except TypeError: no matching pytest.raises(TypeError) in task_keyed_gates.py
hooks/lib/resolve-think-gate.py:487:writing-tests-5: except OSError: no matching pytest.raises(OSError) in task_keyed_gates.py
hooks/lib/resolve-think-gate.py:487:writing-tests-5: except ValueError: no matching pytest.raises(ValueError) in task_keyed_gates.py
hooks/lib/task_actions.py:220:writing-code-7-silent-swallow(Return): except (ValueError, SyntaxError): <Return>
hooks/lib/task_actions.py:220:writing-tests-5: except ValueError: no matching pytest.raises(ValueError) in task_keyed_gates.py
hooks/lib/task_actions.py:220:writing-tests-5: except SyntaxError: no matching pytest.raises(SyntaxError) in task_keyed_gates.py
hooks/lib/task_actions.py:438:writing-tests-5: except SubprocessError: no matching pytest.raises(SubprocessError) in task_keyed_gates.py
hooks/lib/task_actions.py:438:writing-tests-5: except OSError: no matching pytest.raises(OSError) in task_keyed_gates.py
hooks/lib/task_actions.py:572:writing-tests-5: except Exception: no matching pytest.raises(Exception) in task_keyed_gates.py
hooks/lib/task_actions.py:643:writing-tests-5: except OSError: no matching pytest.raises(OSError) in task_keyed_gates.py
hooks/lib/task_actions.py:643:writing-tests-5: except ValueError: no matching pytest.raises(ValueError) in task_keyed_gates.py
hooks/lib/task_actions.py:643:writing-tests-5: except TypeError: no matching pytest.raises(TypeError) in task_keyed_gates.py
hooks/lib/task_actions.py:653:writing-tests-5: except OSError: no matching pytest.raises(OSError) in task_keyed_gates.py
hooks/lib/task_actions.py:709:writing-tests-5: except OSError: no matching pytest.raises(OSError) in task_keyed_gates.py
hooks/lib/task_actions.py:709:writing-tests-5: except ValueError: no matching pytest.raises(ValueError) in task_keyed_gates.py
hooks/lib/task_actions.py:856:writing-tests-5: except UnknownShape: no matching pytest.raises(UnknownShape) in task_keyed_gates.py
hooks/lib/task_actions.py:1123:writing-tests-5: except UnknownShape: no matching pytest.raises(UnknownShape) in task_keyed_gates.py

scanned: writing-prose:1-4 (stylistic; broader Unicode class), writing-code:2 (history references in code comments), writing-code:4 (Django ORM kwarg validation, same-file models; AST), writing-code:7 (silent error swallowing; AST), writing-code:8 (optional-import callsite guards; AST), writing-code:9 (silently-dropped parameters; AST scoped visitor), writing-code:15 (unbounded blocking I/O; AST, incl. Popen chains, Session/Client instance methods, invalid literal timeouts), writing-tests:3 (skip messages must be actionable), writing-tests:5 (untested named exception handlers, cross-file; AST), writing-claims:2 (countable claims need Verified-by trailer), rule citations in messages require Rule-executed evidence (#282), writing-releases:3 (deprecation messages need version+removal-keyword anchors; AST). Not mechanized (judgment-bound): writing-code:1/3/5/6, writing-tests:1/2/4, writing-claims:1/3, writing-releases:1/2.
violations: 62
```

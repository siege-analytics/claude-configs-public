# Review: registered receipt provider across hook stacks

## Assumptions

Goal source: https://github.com/siege-analytics/claude-configs-public/issues/1180
Plan reference: plans/registered-receipt-provider-1180.md
Pre-mortem-artifact: plans/registered-receipt-provider-1180.md#risks-and-test-plan
Hostile-review-artifact: https://github.com/siege-analytics/claude-configs-public/issues/1180

The host registration is source-owned authority, not a task-selected provider path. The standard registered workspace producer is selected only after generation hashes, global registration ownership and exact payload/session binding validate. Existing literal command, repository/source, own task and adjacent output checks remain. No live settings were modified.

## Peer review

Independent source and scanner review requested against the four frozen runtime/test hashes. Acceptance will be recorded before candidate publication. Protected exact-head CI supplies the complete suite before merge.

## Lead review

Two hook generations previously demanded different sibling producers. Valid external enrollment now identifies one hash-pinned physical workspace producer for both stacks. Missing or invalid expected enrollment fails closed. A policy file alone is not enrollment: Linux/headless direct hooks and native CLI retain their exact local-generation producer. Existing v3.5.84 receipts remain valid for legacy routing but cannot grant the new provider lane until normal installation publishes its digest.

The actual old f004 helper/router bytes and no-pin receipt are exercised in a disposable fixture, followed by normal installer upgrade. Operator settings and unknown hooks survive. The two real Bash hook roots both accept the same registered command, and the actual producer then runs a bounded real test and writes successful evidence. This is fixture proof, not installed-session re-entry proof. Root owns installation and live verification.

## Quantified claims

New provider8 tests passed11.685s; existing router31 passed17.046s; scoped evidence7 passed11.613s; producer17 passed15.243s. The initial red fixture exposed the two-stack exact-path contradiction and missing provider-integrity checks. The current diagnostic retains the existing 'exact' contract. The standard hook wrapper also ran the new8 tests successfully11.128s, so the protected hook glob includes them. No full local workflow was launched; protected CI remains required.

The extra review-risk check passed its dependency-graph checks and stopped at a stale inherited catalog/skills-inventory.json detected by generated-source-authority. No skill source changed in this slice, and the shared catalog was not regenerated. Root authorized an isolated mechanical refresh; its diff adds inherited own-session test references and, after staging the new files, the new provider-test evidence references to catalog/skills-inventory.json. Generated-source-authority regeneration produced no byte change. The risk check is being rerun; this is not yet a passing risk-suite claim.

## Scanner

Selected AST scan exits1 with28 findings. The new narrow OSError/ValueError/TypeError handler translates failure to visible UnknownShape with cause. Missing pin, corrupt enrollment and forged SDK are denied by actual-hook tests; this does not prove every listed exception class is raised. The scanner maps task_actions to task_keyed_gates rather than the new composition test. Existing sentinel return/pass/continue sites are unchanged: task_actions reader parse failure returns non-reader; router path-relative failure preserves an operator hook rather than retiring it; ProcessLookupError means a killed child already exited and wait still executes; optional audit failure does not select authority or a fallback directory. These bounded dispositions require independent review. No clean-scan or exhaustive exception-branch coverage is claimed.

### Selected raw output

```text
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
hooks/lib/task_actions.py:844:writing-tests-5: except UnknownShape: no matching pytest.raises(UnknownShape) in task_keyed_gates.py
hooks/lib/task_actions.py:1111:writing-tests-5: except UnknownShape: no matching pytest.raises(UnknownShape) in task_keyed_gates.py
hooks/lib/craft-settings-router.py:576:writing-code-7-silent-swallow(Pass): except (OSError, ValueError): <Pass>
hooks/lib/craft-settings-router.py:372:writing-code-7-silent-swallow(Pass): except ProcessLookupError: <Pass>
hooks/lib/craft-settings-router.py:138:writing-code-7-silent-swallow(Continue): except ValueError: <Continue>
hooks/lib/craft-settings-router.py:251:writing-tests-5: except TypeError: no matching pytest.raises(TypeError) in craft_hook_router_test.py
hooks/lib/craft-settings-router.py:576:writing-tests-5: except OSError: no matching pytest.raises(OSError) in craft_hook_router_test.py
hooks/lib/craft-settings-router.py:603:writing-tests-5: except Exception: no matching pytest.raises(Exception) in craft_hook_router_test.py
hooks/lib/craft-settings-router.py:599:writing-tests-5: except Exception: no matching pytest.raises(Exception) in craft_hook_router_test.py
hooks/lib/craft-settings-router.py:372:writing-tests-5: except ProcessLookupError: no matching pytest.raises(ProcessLookupError) in craft_hook_router_test.py
hooks/lib/craft-settings-router.py:350:writing-tests-5: except BrokenPipeError: no matching pytest.raises(BrokenPipeError) in craft_hook_router_test.py
bin/install-craft-hook-router.py:244:writing-tests-5: except TypeError: no matching pytest.raises(TypeError) in craft_hook_router_test.py
bin/install-craft-hook-router.py:299:writing-tests-5: except OSError: no matching pytest.raises(OSError) in craft_hook_router_test.py
bin/install-craft-hook-router.py:299:writing-tests-5: except TypeError: no matching pytest.raises(TypeError) in craft_hook_router_test.py
bin/install-craft-hook-router.py:299:writing-tests-5: except ImportError: no matching pytest.raises(ImportError) in craft_hook_router_test.py
bin/install-craft-hook-router.py:299:writing-tests-5: except SubprocessError: no matching pytest.raises(SubprocessError) in craft_hook_router_test.py
```

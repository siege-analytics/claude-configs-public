---
ticket_refs:
  - siege-analytics/claude-configs-public#1166
---

# Git file operands: implementation review

## Assumptions and scope

The existing Git configuration and attributes trust boundary remains in force. This classifier is not a sandbox: ordinary configured Git filters may execute just as they do for previously supported status. Explicit custom archive formats, remote/helper selection and unknown options do not acquire reader authority. No Task, branch, lifecycle or protected-source permission is added.

## Peer review

Root independently inspected both runtime files and the original nine-method fixture, then ran that fixture successfully in 13.501 seconds. Exact source acceptance: https://github.com/siege-analytics/claude-configs-public/issues/1166#issuecomment-6785048661 . A subsequent test-only cyclic-symlink assertion covers the new output-inspection error branch; runtime bytes did not change. Final source-bound producer results are recorded separately rather than attributed to Root.

## Lead review and chronology

The design plan preceded runtime edits. Baseline counterexamples were executed after the initial implementation; this was not a red-first development sequence. Baseline parser tests failed fourteen assertions and its full configured chain rejected the legitimate archive output. The implemented fixture covers actual Git archive/apply effects and the full configured hook chain, including foreign output denial. Original failure logs remain under /private/tmp/core1166-baseline-*.log.

The scanner is nonclean: its complete raw findings and per-item handler comparison/disposition are retained externally. Exception handlers returning a non-reader or structured denial do not raise to pytest. New output handlers have actual fresh-file and cyclic-alias behavioral controls. An unchanged handler is not, by itself, proof of complete historical test coverage; unaffected findings remain qualified in the disposition record.

## Negative tests and rollback

Foreign destinations, symlink/hardlink/cyclic aliases, mixed mutations, custom formats, remote helpers, apply overrides and unknown options retain denial or mutation classification. Actual plain apply modifies its private repository while check/stat/numstat/summary do not. No installed configuration or live source repository was changed. Rollback is a normal revert of this source repair; the temporary operator archive workaround is independent.

## Quantified claims

Pre-mortem-artifact: plans/git-read-output-targets-1166.md
Hostile-review-artifact: https://github.com/siege-analytics/claude-configs-public/issues/1166#issuecomment-6785048661

The external native producer log and content-bound receipt support author test totals. Root independently ran the original nine methods, not the subsequent full affected suite. Baseline assertion counts and scanner totals describe retained logs, not protected CI or consumer adoption.

## Validation

Genuine native test evidence is content-bound in the ignored worktree test-gate.json. Focused Git, existing reader/allowlist and full negative review-risk checks must pass before normal native commit/push. Hosted exact-head checks remain separate; this artifact does not claim a whole-repository or installed-consumer pass.

## Complete nonclean scanner dispositions

Protected base: `19506a4559fa3525b6e897ea27e313ae199aed2f`. Staged source tree at scan preparation: `c89a01d6c5807fcdc0a0e8cb877ad9197c01799a`. Full initial raw result: `/private/tmp/core1166-scan-initial.log`, exit1. The final staged scan is retained as `/private/tmp/core1166-scan-final.log`; tests and CI are separate. Root accepted every disposition with the module-loading wording correction: https://github.com/siege-analytics/claude-configs-public/issues/1166#issuecomment-6785199505 . Final PR rebind will preserve that qualification. No finding is suppressed or described as clean.

- `skills/detect-ai-fingerprints/scan.sh`: SHA256 `e7fc8ef0ab0c77a5e196fbbe26ae2a718463f49a168e90d5fe1de7526896b939`.
- `skills/detect-ai-fingerprints/scan_ast.py`: SHA256 `27e0960e2ee767ff8573d4c02ed0d72e7f92fc37382a63b325fbe11971ae7b44`.
- `skills/detect-ai-fingerprints/scan_snapshot.py`: SHA256 `64745818e514113d12a9ac58264546316fd47f7918af1b03a0b3291edfd4257d`.
- `hooks/lib/task_actions.py`: SHA256 `4b982b11ef30e68a9db8e32c1a3e16582eda545aecba3f43e798180a0d42dc0c`; blob `b87a567ade4274508c707be501cc6233715dc5c5`.
- `hooks/lib/read-only-command.py`: SHA256 `6f7c115ec90a14c7a47ec797982645dc449994b6ee82da28a8d04a4feb89e29f`; blob `e46adc42387d632f7c6037e93889dd8473ffc8cc`.
- `hooks/_test/git_file_operands_1166.py`: SHA256 `c77dfd932e32680a2513b3e74e71a1194b61f928d5619e752e20f2a2da0dc8ee`; blob `2a419ffb4e5abf2af72f43b7534ce96858460d13`.

### Finding 1: hooks/lib/read-only-command.py:340

Rule: `writing-code-7-silent-swallow(Return)`. except (ValueError, TypeError, KeyError): <Return>

Reason: Enclosing function and handler are AST-identical to base; new archive/apply grammar does not alter this operation-specific path. Named-exception pytest.raises heuristic does not recognize structured classifier return/deny assertions.

Evidence: Exact base/current enclosing-function AST equality recorded here; existing reader/allowlist and new focused controls are affected validation, not a claim of historical exhaustive handler coverage. Enclosing function: `gh_ok`; function AST unchanged: True; handler AST unchanged: True.

Falsification: Any enclosing AST delta invalidates this unaffected disposition; a changed caller that newly admits this handler requires separate behavior proof.

### Finding 2: hooks/lib/read-only-command.py:545

Rule: `writing-tests-5`. source has 5 except block(s) but no test file found (looked in tests/, hooks/lib/tests/, ...)

Reason: Test-discovery heuristic misses hooks/_test/reader_git_safety.py and read_allowlist.test.sh; new Git fixture also imports this exact classifier.

Evidence: Existing reader safety and readallowlist in final native producer; new git_file_operands_1166 tests. Enclosing function: `lead_verbs`; function AST unchanged: True; handler AST unchanged: True.

Falsification: Remove or break classifier behavior: reader and full-chain negatives must fail.

### Finding 3: hooks/lib/task_actions.py:221

Rule: `writing-code-7-silent-swallow(Return)`. except (ValueError, SyntaxError): <Return>

Reason: Enclosing function and handler are AST-identical to base; new archive/apply grammar does not alter this operation-specific path. Named-exception pytest.raises heuristic does not recognize structured classifier return/deny assertions.

Evidence: Exact base/current enclosing-function AST equality recorded here; existing reader/allowlist and new focused controls are affected validation, not a claim of historical exhaustive handler coverage. Enclosing function: `_python_read`; function AST unchanged: True; handler AST unchanged: True.

Falsification: Any enclosing AST delta invalidates this unaffected disposition; a changed caller that newly admits this handler requires separate behavior proof.

### Finding 4: hooks/lib/task_actions.py:221

Rule: `writing-tests-5`. except ValueError: no matching pytest.raises(ValueError) in task_keyed_gates.py

Reason: Enclosing function and handler are AST-identical to base; new archive/apply grammar does not alter this operation-specific path. Named-exception pytest.raises heuristic does not recognize structured classifier return/deny assertions.

Evidence: Exact base/current enclosing-function AST equality recorded here; existing reader/allowlist and new focused controls are affected validation, not a claim of historical exhaustive handler coverage. Enclosing function: `_python_read`; function AST unchanged: True; handler AST unchanged: True.

Falsification: Any enclosing AST delta invalidates this unaffected disposition; a changed caller that newly admits this handler requires separate behavior proof.

### Finding 5: hooks/lib/task_actions.py:221

Rule: `writing-tests-5`. except SyntaxError: no matching pytest.raises(SyntaxError) in task_keyed_gates.py

Reason: Enclosing function and handler are AST-identical to base; new archive/apply grammar does not alter this operation-specific path. Named-exception pytest.raises heuristic does not recognize structured classifier return/deny assertions.

Evidence: Exact base/current enclosing-function AST equality recorded here; existing reader/allowlist and new focused controls are affected validation, not a claim of historical exhaustive handler coverage. Enclosing function: `_python_read`; function AST unchanged: True; handler AST unchanged: True.

Falsification: Any enclosing AST delta invalidates this unaffected disposition; a changed caller that newly admits this handler requires separate behavior proof.

### Finding 6: hooks/lib/task_actions.py:494

Rule: `writing-tests-5`. except SubprocessError: no matching pytest.raises(SubprocessError) in task_keyed_gates.py

Reason: Enclosing function and handler are AST-identical to base; new archive/apply grammar does not alter this operation-specific path. Named-exception pytest.raises heuristic does not recognize structured classifier return/deny assertions.

Evidence: Exact base/current enclosing-function AST equality recorded here; existing reader/allowlist and new focused controls are affected validation, not a claim of historical exhaustive handler coverage. Enclosing function: `_git_toplevel`; function AST unchanged: True; handler AST unchanged: True.

Falsification: Any enclosing AST delta invalidates this unaffected disposition; a changed caller that newly admits this handler requires separate behavior proof.

### Finding 7: hooks/lib/task_actions.py:494

Rule: `writing-tests-5`. except OSError: no matching pytest.raises(OSError) in task_keyed_gates.py

Reason: Enclosing function and handler are AST-identical to base; new archive/apply grammar does not alter this operation-specific path. Named-exception pytest.raises heuristic does not recognize structured classifier return/deny assertions.

Evidence: Exact base/current enclosing-function AST equality recorded here; existing reader/allowlist and new focused controls are affected validation, not a claim of historical exhaustive handler coverage. Enclosing function: `_git_toplevel`; function AST unchanged: True; handler AST unchanged: True.

Falsification: Any enclosing AST delta invalidates this unaffected disposition; a changed caller that newly admits this handler requires separate behavior proof.

### Finding 8: hooks/lib/task_actions.py:516

Rule: `writing-tests-5`. except OSError: no matching pytest.raises(OSError) in task_keyed_gates.py

Reason: Enclosing function and handler are AST-identical to base; new archive/apply grammar does not alter this operation-specific path. Named-exception pytest.raises heuristic does not recognize structured classifier return/deny assertions.

Evidence: Exact base/current enclosing-function AST equality recorded here; existing reader/allowlist and new focused controls are affected validation, not a claim of historical exhaustive handler coverage. Enclosing function: `_git_bootstrap_read`; function AST unchanged: True; handler AST unchanged: True.

Falsification: Any enclosing AST delta invalidates this unaffected disposition; a changed caller that newly admits this handler requires separate behavior proof.

### Finding 9: hooks/lib/task_actions.py:516

Rule: `writing-tests-5`. except SubprocessError: no matching pytest.raises(SubprocessError) in task_keyed_gates.py

Reason: Enclosing function and handler are AST-identical to base; new archive/apply grammar does not alter this operation-specific path. Named-exception pytest.raises heuristic does not recognize structured classifier return/deny assertions.

Evidence: Exact base/current enclosing-function AST equality recorded here; existing reader/allowlist and new focused controls are affected validation, not a claim of historical exhaustive handler coverage. Enclosing function: `_git_bootstrap_read`; function AST unchanged: True; handler AST unchanged: True.

Falsification: Any enclosing AST delta invalidates this unaffected disposition; a changed caller that newly admits this handler requires separate behavior proof.

### Finding 10: hooks/lib/task_actions.py:625

Rule: `writing-tests-5`. except UnicodeError: no matching pytest.raises(UnicodeError) in task_keyed_gates.py

Reason: Enclosing function and handler are AST-identical to base; new archive/apply grammar does not alter this operation-specific path. Named-exception pytest.raises heuristic does not recognize structured classifier return/deny assertions.

Evidence: Exact base/current enclosing-function AST equality recorded here; existing reader/allowlist and new focused controls are affected validation, not a claim of historical exhaustive handler coverage. Enclosing function: `_git_clone_effective_source`; function AST unchanged: True; handler AST unchanged: True.

Falsification: Any enclosing AST delta invalidates this unaffected disposition; a changed caller that newly admits this handler requires separate behavior proof.

### Finding 11: hooks/lib/task_actions.py:640

Rule: `writing-tests-5`. except UnicodeError: no matching pytest.raises(UnicodeError) in task_keyed_gates.py

Reason: Enclosing function and handler are AST-identical to base; new archive/apply grammar does not alter this operation-specific path. Named-exception pytest.raises heuristic does not recognize structured classifier return/deny assertions.

Evidence: Exact base/current enclosing-function AST equality recorded here; existing reader/allowlist and new focused controls are affected validation, not a claim of historical exhaustive handler coverage. Enclosing function: `_git_clone_effective_source`; function AST unchanged: True; handler AST unchanged: True.

Falsification: Any enclosing AST delta invalidates this unaffected disposition; a changed caller that newly admits this handler requires separate behavior proof.

### Finding 12: hooks/lib/task_actions.py:922

Rule: `writing-tests-5`. except Exception: no matching pytest.raises(Exception) in task_keyed_gates.py

Reason: Enclosing function and handler are AST-identical to base; new archive/apply grammar does not alter this operation-specific path. Named-exception pytest.raises heuristic does not recognize structured classifier return/deny assertions.

Evidence: Exact base/current enclosing-function AST equality recorded here; existing reader/allowlist and new focused controls are affected validation, not a claim of historical exhaustive handler coverage. Enclosing function: `ssh_allowlist`; function AST unchanged: True; handler AST unchanged: True.

Falsification: Any enclosing AST delta invalidates this unaffected disposition; a changed caller that newly admits this handler requires separate behavior proof.

### Finding 13: hooks/lib/task_actions.py:1000

Rule: `writing-tests-5`. except ValueError: no matching pytest.raises(ValueError) in task_keyed_gates.py

Reason: Enclosing function and handler are AST-identical to base; new archive/apply grammar does not alter this operation-specific path. Named-exception pytest.raises heuristic does not recognize structured classifier return/deny assertions.

Evidence: Exact base/current enclosing-function AST equality recorded here; existing reader/allowlist and new focused controls are affected validation, not a claim of historical exhaustive handler coverage. Enclosing function: `_command_string`; function AST unchanged: True; handler AST unchanged: True.

Falsification: Any enclosing AST delta invalidates this unaffected disposition; a changed caller that newly admits this handler requires separate behavior proof.

### Finding 14: hooks/lib/task_actions.py:1227

Rule: `writing-tests-5`. except Exception: no matching pytest.raises(Exception) in task_keyed_gates.py

Reason: Handler AST is unchanged; enclosing Git dispatch or lazy classifier loader changed. Its conservative return/error behavior remains explicit, rather than an exception escaping to pytest.

Evidence: Exact handler AST equality; new unknown/archive/helper/apply-override and alias denials exercise the affected dispatch. main(command) exceptions return1; module loading is outside that try and propagates to the outer fail-closed action/host boundary. No module-load failure execution-coverage claim is made. Enclosing function: `released_read_verdict`; function AST unchanged: False; handler AST unchanged: True.

Falsification: A load/parse failure producing reader allow or unsupported Git target admission invalidates this disposition.

### Finding 15: hooks/lib/task_actions.py:1532

Rule: `writing-tests-5`. except OSError: no matching pytest.raises(OSError) in task_keyed_gates.py

Reason: Enclosing function and handler are AST-identical to base; new archive/apply grammar does not alter this operation-specific path. Named-exception pytest.raises heuristic does not recognize structured classifier return/deny assertions.

Evidence: Exact base/current enclosing-function AST equality recorded here; existing reader/allowlist and new focused controls are affected validation, not a claim of historical exhaustive handler coverage. Enclosing function: `_test_receipt_record`; function AST unchanged: True; handler AST unchanged: True.

Falsification: Any enclosing AST delta invalidates this unaffected disposition; a changed caller that newly admits this handler requires separate behavior proof.

### Finding 16: hooks/lib/task_actions.py:1532

Rule: `writing-tests-5`. except ValueError: no matching pytest.raises(ValueError) in task_keyed_gates.py

Reason: Enclosing function and handler are AST-identical to base; new archive/apply grammar does not alter this operation-specific path. Named-exception pytest.raises heuristic does not recognize structured classifier return/deny assertions.

Evidence: Exact base/current enclosing-function AST equality recorded here; existing reader/allowlist and new focused controls are affected validation, not a claim of historical exhaustive handler coverage. Enclosing function: `_test_receipt_record`; function AST unchanged: True; handler AST unchanged: True.

Falsification: Any enclosing AST delta invalidates this unaffected disposition; a changed caller that newly admits this handler requires separate behavior proof.

### Finding 17: hooks/lib/task_actions.py:1532

Rule: `writing-tests-5`. except TypeError: no matching pytest.raises(TypeError) in task_keyed_gates.py

Reason: Enclosing function and handler are AST-identical to base; new archive/apply grammar does not alter this operation-specific path. Named-exception pytest.raises heuristic does not recognize structured classifier return/deny assertions.

Evidence: Exact base/current enclosing-function AST equality recorded here; existing reader/allowlist and new focused controls are affected validation, not a claim of historical exhaustive handler coverage. Enclosing function: `_test_receipt_record`; function AST unchanged: True; handler AST unchanged: True.

Falsification: Any enclosing AST delta invalidates this unaffected disposition; a changed caller that newly admits this handler requires separate behavior proof.

### Finding 18: hooks/lib/task_actions.py:1542

Rule: `writing-tests-5`. except OSError: no matching pytest.raises(OSError) in task_keyed_gates.py

Reason: Enclosing function and handler are AST-identical to base; new archive/apply grammar does not alter this operation-specific path. Named-exception pytest.raises heuristic does not recognize structured classifier return/deny assertions.

Evidence: Exact base/current enclosing-function AST equality recorded here; existing reader/allowlist and new focused controls are affected validation, not a claim of historical exhaustive handler coverage. Enclosing function: `_test_receipt_record`; function AST unchanged: True; handler AST unchanged: True.

Falsification: Any enclosing AST delta invalidates this unaffected disposition; a changed caller that newly admits this handler requires separate behavior proof.

### Finding 19: hooks/lib/task_actions.py:1598

Rule: `writing-tests-5`. except OSError: no matching pytest.raises(OSError) in task_keyed_gates.py

Reason: Enclosing function and handler are AST-identical to base; new archive/apply grammar does not alter this operation-specific path. Named-exception pytest.raises heuristic does not recognize structured classifier return/deny assertions.

Evidence: Exact base/current enclosing-function AST equality recorded here; existing reader/allowlist and new focused controls are affected validation, not a claim of historical exhaustive handler coverage. Enclosing function: `_metadata_file`; function AST unchanged: True; handler AST unchanged: True.

Falsification: Any enclosing AST delta invalidates this unaffected disposition; a changed caller that newly admits this handler requires separate behavior proof.

### Finding 20: hooks/lib/task_actions.py:1598

Rule: `writing-tests-5`. except ValueError: no matching pytest.raises(ValueError) in task_keyed_gates.py

Reason: Enclosing function and handler are AST-identical to base; new archive/apply grammar does not alter this operation-specific path. Named-exception pytest.raises heuristic does not recognize structured classifier return/deny assertions.

Evidence: Exact base/current enclosing-function AST equality recorded here; existing reader/allowlist and new focused controls are affected validation, not a claim of historical exhaustive handler coverage. Enclosing function: `_metadata_file`; function AST unchanged: True; handler AST unchanged: True.

Falsification: Any enclosing AST delta invalidates this unaffected disposition; a changed caller that newly admits this handler requires separate behavior proof.

### Finding 21: hooks/lib/task_actions.py:1831

Rule: `writing-tests-5`. except UnknownShape: no matching pytest.raises(UnknownShape) in task_keyed_gates.py

Reason: Handler AST is unchanged; enclosing Git dispatch or lazy classifier loader changed. Its conservative return/error behavior remains explicit, rather than an exception escaping to pytest.

Evidence: Exact handler AST equality; new unknown/archive/helper/apply-override and alias denials exercise the affected dispatch. main(command) exceptions return1; module loading is outside that try and propagates to the outer fail-closed action/host boundary. No module-load failure execution-coverage claim is made. Enclosing function: `_action`; function AST unchanged: False; handler AST unchanged: True.

Falsification: A load/parse failure producing reader allow or unsupported Git target admission invalidates this disposition.

### Finding 22: hooks/lib/task_actions.py:2180

Rule: `writing-tests-5`. except UnknownShape: no matching pytest.raises(UnknownShape) in task_keyed_gates.py

Reason: Handler AST is unchanged; enclosing Git dispatch or lazy classifier loader changed. Its conservative return/error behavior remains explicit, rather than an exception escaping to pytest.

Evidence: Exact handler AST equality; new unknown/archive/helper/apply-override and alias denials exercise the affected dispatch. main(command) exceptions return1; module loading is outside that try and propagates to the outer fail-closed action/host boundary. No module-load failure execution-coverage claim is made. Enclosing function: `_action`; function AST unchanged: False; handler AST unchanged: True.

Falsification: A load/parse failure producing reader allow or unsupported Git target admission invalidates this disposition.

### Finding 23: hooks/lib/task_actions.py:417

Rule: `writing-tests-5`. except OSError: no matching pytest.raises(OSError) in task_keyed_gates.py

Reason: Enclosing function and handler are AST-identical to base; new archive/apply grammar does not alter this operation-specific path. Named-exception pytest.raises heuristic does not recognize structured classifier return/deny assertions.

Evidence: Exact base/current enclosing-function AST equality recorded here; existing reader/allowlist and new focused controls are affected validation, not a claim of historical exhaustive handler coverage. Enclosing function: `inspect`; function AST unchanged: True; handler AST unchanged: True.

Falsification: Any enclosing AST delta invalidates this unaffected disposition; a changed caller that newly admits this handler requires separate behavior proof.

### Finding 24: hooks/lib/task_actions.py:784

Rule: `writing-tests-5`. except OSError: no matching pytest.raises(OSError) in task_keyed_gates.py

Reason: Enclosing function and handler are AST-identical to base; new archive/apply grammar does not alter this operation-specific path. Named-exception pytest.raises heuristic does not recognize structured classifier return/deny assertions.

Evidence: Exact base/current enclosing-function AST equality recorded here; existing reader/allowlist and new focused controls are affected validation, not a claim of historical exhaustive handler coverage. Enclosing function: `_git_bootstrap_destination`; function AST unchanged: True; handler AST unchanged: True.

Falsification: Any enclosing AST delta invalidates this unaffected disposition; a changed caller that newly admits this handler requires separate behavior proof.

### Finding 25: hooks/lib/task_actions.py:796

Rule: `writing-tests-5`. except OSError: no matching pytest.raises(OSError) in task_keyed_gates.py

Reason: Enclosing function and handler are AST-identical to base; new archive/apply grammar does not alter this operation-specific path. Named-exception pytest.raises heuristic does not recognize structured classifier return/deny assertions.

Evidence: Exact base/current enclosing-function AST equality recorded here; existing reader/allowlist and new focused controls are affected validation, not a claim of historical exhaustive handler coverage. Enclosing function: `_git_bootstrap_destination`; function AST unchanged: True; handler AST unchanged: True.

Falsification: Any enclosing AST delta invalidates this unaffected disposition; a changed caller that newly admits this handler requires separate behavior proof.

### Finding 26: hooks/lib/task_actions.py:796

Rule: `writing-tests-5`. except SubprocessError: no matching pytest.raises(SubprocessError) in task_keyed_gates.py

Reason: Enclosing function and handler are AST-identical to base; new archive/apply grammar does not alter this operation-specific path. Named-exception pytest.raises heuristic does not recognize structured classifier return/deny assertions.

Evidence: Exact base/current enclosing-function AST equality recorded here; existing reader/allowlist and new focused controls are affected validation, not a claim of historical exhaustive handler coverage. Enclosing function: `_git_bootstrap_destination`; function AST unchanged: True; handler AST unchanged: True.

Falsification: Any enclosing AST delta invalidates this unaffected disposition; a changed caller that newly admits this handler requires separate behavior proof.

### Finding 27: hooks/lib/task_actions.py:1306

Rule: `writing-tests-5`. except UnicodeError: no matching pytest.raises(UnicodeError) in task_keyed_gates.py

Reason: Enclosing function and handler are AST-identical to base; new archive/apply grammar does not alter this operation-specific path. Named-exception pytest.raises heuristic does not recognize structured classifier return/deny assertions.

Evidence: Exact base/current enclosing-function AST equality recorded here; existing reader/allowlist and new focused controls are affected validation, not a claim of historical exhaustive handler coverage. Enclosing function: `__init__`; function AST unchanged: True; handler AST unchanged: True.

Falsification: Any enclosing AST delta invalidates this unaffected disposition; a changed caller that newly admits this handler requires separate behavior proof.

### Finding 28: hooks/lib/task_actions.py:741

Rule: `writing-tests-5`. except OSError: no matching pytest.raises(OSError) in task_keyed_gates.py

Reason: Enclosing function and handler are AST-identical to base; new archive/apply grammar does not alter this operation-specific path. Named-exception pytest.raises heuristic does not recognize structured classifier return/deny assertions.

Evidence: Exact base/current enclosing-function AST equality recorded here; existing reader/allowlist and new focused controls are affected validation, not a claim of historical exhaustive handler coverage. Enclosing function: `_git_bootstrap_destination`; function AST unchanged: True; handler AST unchanged: True.

Falsification: Any enclosing AST delta invalidates this unaffected disposition; a changed caller that newly admits this handler requires separate behavior proof.

### Finding 29: hooks/lib/task_actions.py:761

Rule: `writing-tests-5`. except ValueError: no matching pytest.raises(ValueError) in task_keyed_gates.py

Reason: Enclosing function and handler are AST-identical to base; new archive/apply grammar does not alter this operation-specific path. Named-exception pytest.raises heuristic does not recognize structured classifier return/deny assertions.

Evidence: Exact base/current enclosing-function AST equality recorded here; existing reader/allowlist and new focused controls are affected validation, not a claim of historical exhaustive handler coverage. Enclosing function: `_git_bootstrap_destination`; function AST unchanged: True; handler AST unchanged: True.

Falsification: Any enclosing AST delta invalidates this unaffected disposition; a changed caller that newly admits this handler requires separate behavior proof.

### Finding 30: hooks/lib/task_actions.py:1998

Rule: `writing-tests-5`. except FileNotFoundError: no matching pytest.raises(FileNotFoundError) in task_keyed_gates.py

Reason: FileNotFoundError means a fresh destination, not an ignored failure. Ownership proof then applies to the canonical output.

Evidence: Fresh own output positive and foreign fresh output negative, plus actual archive effects. Enclosing function: `finish`; function AST unchanged: False; handler AST unchanged: False.

Falsification: Treat foreign new destination as allowed or discard output target; full-chain foreign-output test fails.

### Finding 31: hooks/lib/task_actions.py:2000

Rule: `writing-tests-5`. except OSError: no matching pytest.raises(OSError) in task_keyed_gates.py

Reason: Output-inspection OSError becomes UnknownShape with actionable denial, not success.

Evidence: Cyclic symlink output regression asserts gate2 and cannot-inspect diagnostic. Enclosing function: `finish`; function AST unchanged: False; handler AST unchanged: False.

Falsification: Swallow the OSError or certify output; cyclic alias assertion fails.

# Independent metadata integration scanner review

ACCEPT each of the eleven findings in the complete non-clean exit-1 raw scan /private/tmp/ticket-metadata-merge-scan.log. This is per-handler evidence acceptance, not a count baseline, clean-scan claim, or blanket exception-coverage waiver. Reviewed staged tree at observation: 378202b240cf56a84ec6ec9b00a7c9b1fdb317ad. Runtime ticket approval remains separate.

| Finding | Reason and independent evidence | Falsification |
| --- | --- | --- |
| task_actions.py:215 silent Return | Parse failure returns false: no Python read proof. Actual-module ValueError and SyntaxError controls passed. | Failed parse supplying read authority. |
| :215 ValueError test heuristic | Actual-module injected ValueError returned false; assertion-style test need not use pytest.raises when exception is handled. | Error escaping as success/read. |
| :215 SyntaxError test heuristic | Same negative proof with real SyntaxError injection passed. | Invalid syntax receives read proof. |
| :377 SubprocessError test heuristic | Git toplevel failure raises UnknownShape; direct actual-module control passed. | Unresolved repository yields trusted root. |
| :377 OSError test heuristic | Same conversion with OSError passed. | Missing Git permits mutation lane. |
| :511 Exception test heuristic | Classifier RuntimeError becomes unproven verdict1, never proven-read0; direct control passed. action calls _action for nonzero verdict. | Classifier outage becomes read authority. |
| :575 OSError test heuristic | Producer stat failure becomes UnknownShape, removing execution lane; direct control passed. | Missing producer accepted. |
| :631 OSError test heuristic | Body-file open failure becomes UnknownShape; direct control and actual unreadable-metadata hook fixture passed. | Unreadable body gains metadata exemption. |
| :631 ValueError test heuristic | Actual-module invalid-path control becomes UnknownShape. | Invalid body gains exemption. |
| :734 UnknownShape test heuristic | Initial parser/producer failure returns read_only false, cwd target and error; direct control passed. | Failure returns read/exemption or loses target. |
| :971 UnknownShape test heuristic | Segment failure returns nonread/error with cwd target and no metadata_only; direct control passed. | Unknown segment grants metadata exemption. |

Independent commands: python3 -B /private/tmp/ticket-metadata-handler-controls.py (ten controls PASS); python3 -B hooks/_test/task_keyed_gates.py Gates.test_remote_metadata_unreadable_inputs_are_clear_failures Gates.test_no_gate_reads_and_hostile_unknown_shapes (two methods PASS, 12.703s). Commands used Homebrew Python, TMPDIR=/private/tmp and disabled bytecode. Controls exercised imported production functions, not copied decisions. All six affected function ASTs also compare equal to b3c560b. Equality is corroboration, not the reason for accepting an unsafe handler.

Source/caller review: _python_read false feeds unproven handling; Git resolution and producer/body validation failures raise UnknownShape; _action catches retain nonread scoped error results. The named-exception heuristic requires pytest.raises despite these handlers consuming the exceptions, so direct outcome assertions are the suitable evidence here. This review does not claim all possible fault contexts or all module handlers are tested. The incoming positional URL guard rejects colon or leading // only after canonical GitHub URL handling; it narrows metadata eligibility.

hooks/lib/task_actions.py SHA256 aae2d8c1e3d50ba880acf63e5bd091cf6f1df9355321f18159e8a74346eb0b81

hooks/_test/task_keyed_gates.py SHA256 233d4c4222741e30c63cca454dbbfa7b2cd9a937b0fc07e140b5571c8bfa3960

.claude/scanner-test-map.json SHA256 3c26d5ac8d85f83b78ef6e552eeed67866ae68a71b00cc12a2264b1856bf3dd7

/private/tmp/ticket-metadata-merge-scan.log SHA256 d5607f842cae6d2fa526c3f21a573b93d2525696db097143a4c6b35a8f6bbd26

/private/tmp/ticket-metadata-handler-controls.py SHA256 f5409d80fbee3781a3106b39e851f3c30fc0771a8c20c0b13224c96ddad2bed2

Evidence-only additions require final selection reconciliation; changed source/test/scanner/map bytes require renewed review. No install, live host or protected-CI approval is conveyed.

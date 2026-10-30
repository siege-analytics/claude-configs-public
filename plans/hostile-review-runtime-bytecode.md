# Independent runtime bytecode fix review

ACCEPT the three-file HEAD-to-index delta reviewed in /private/tmp/claude-runtime-integration-20261029: hooks/lib/git_command.py, bin/native_git.py, hooks/_test/reader_git_safety.py. Source was already staged when reviewed; unstaged diff was empty. No source edits or live deployment performed.

Independent full reader_git_safety.py suite: 9 tests PASS in 29.408s. This includes an unflagged real git_command.py CLI invocation with exact before/after package bytes inventory equality, and native settings adapter -> shell -> fresh Python child import with parent -B but no inherited bytecode environment flag. The child prints True for dont_write_bytecode and fixture inventory stays identical. Registration inputs are stubbed in that propagation fixture; it does not claim immutable registration or complete selected-case proof.

Source mechanism: git_command sets sys.dont_write_bytecode before importing task_actions. native_git sets it before importing selected_registration. All five subprocess execution sites now pass a fresh copy of the current environment overriding only PYTHONDONTWRITEBYTECODE=1: selected entry, generation settings vector, compatibility settings vector, prompt renderer, compatibility Git hook. Existing argv, stdin inheritance, timeout, result propagation and unrelated environment variables are preserved. This closes the shell/fresh-interpreter inheritance gap that parent -B alone does not address.

No inventory exclusions, removal of unexpected files, relaxed pins or changed policy authority are introduced. Other test-file changes are bounded subprocess timeouts, actionable skips and reader syntax controls; no negative assertion was removed.

The diagnosis records exactly one extra task_actions.pyc and diagnostic subtraction restoring the expected inventory digest; this is consistent with the mechanism. Full Git-object component workflow must rerun after committing the candidate because its source snapshot excludes uncommitted fixes. Prior failed workflow remains failed evidence until that rerun passes. No push, merge or install approval is implied by this bounded source acceptance.

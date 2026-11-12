# Literal env/command project execution review

## Assumptions

The reported native PREEXEC refusal is tool `1794507402081-ncdv8z`, electinfo/sites#584. Its sanitized environment invokes Bun but `task_actions._action` treats every env/command mutation as Git and rejects `git_command.prefix(...) == None`. The source is byte-identical at fresh develop fb3416d6 and the pending Core integrated head 67e326ca. Relevant source consulted: `_action` ordering, `ssh_invocation` wrapper detection, `git_command.prefix` and its SAFE_ENV, generic explicit operands/fallback paths, and real Task hook fixtures. These facts motivate mutation-only normalization after remote/SSH detection, without reader reclassification.

The recorded toolInput normalizes absolute paths into relative spellings. It is not proof of the actual executed argv or a relative-path defect. The operator corrected the earlier path interpretation; no original command is replayed here. The regression uses the observed env/Bun/options grammar with fixture-owned paths, including a unit check of relative resolution after cd.

The supported executable family includes Bun, Node, Python, pytest, Make and npm/pnpm/yarn, not a single Bun exception. Unknown executables/wrappers and startup-code overrides remain refused because general redispatch here would skip earlier typed GitHub/remote policies. Supported calls reuse ordinary project-code execution: CWD is an unknown-write proxy, not an OS sandbox or authority for arbitrary external effects. Explicit HOME/XDG/cache/temp/PYTHONPATH and output paths remain ownership targets; PATH is a literal executable search list, not a write destination. Git dispatch is returned to its original normalizer before project-environment validation.

## Test plan

Initial isolated regression: five assertion failures with the real unsupported-Git-options error, over five test methods. No candidate Bun/Python/npm/Git mutation command was executed; fixtures call the actual UMG/classifier only. The candidate regression has six methods with positive runner/Git controls and negative foreign targets, absent/designing/narrow Task, unknown wrapper/options/startup overrides, inline Python/Node/Bun and wrapped SSH controls. Project execution remains a mutation with CWD fallback and a non-A risk floor.

An isolated archive of exact pending Core 67e326ca, overlaid with only the candidate production helper and the focused tests, also runs through the actual UMG using lean Tasks without preparation companions. Final candidate results: the six-method regression passed in 13.536 seconds; the controlled pending-Core/lean-Task composition passed six methods in 10.414 seconds. Adjacent SSH suite passed 179 cases with zero failures. No hosted CI, installed runtime acceptance or dependency installation is claimed.

## Findings

The independent reviewer found that early project-environment validation accidentally rejected three previously supported Git SAFE_ENV variables. The helper now identifies Git dispatch first and delegates all of its environment/option semantics unchanged. Permanent positive GIT_OPTIONAL_LOCKS/GIT_TERMINAL_PROMPT/PAGER controls and forbidden GIT_DIR/env-i Git controls cover that correction. No general GitHub redispatch or read-only promotion was introduced.

## Independent review

Root independently inspected and accepted the final source and six-method tests after the reported integration results. The separate reviewer then accepted exact production blob `a068d930f8a54aec7b9d8e981897372e0d9bb562` and test blob `70ae3dc350b798deb15e4168f246dca6b789010a`: eleven independent base/candidate Git classifier controls match, including the three SAFE_ENV cases and forbidden GIT_DIR/env-i/unknown options. Absolute wrapper Git behavior is inherited, not repaired here. The reviewer independently confirmed all 21 handler ASTs match and rebound the 29 existing findings to the earlier #1327/#1329 dispositions. The enclosing action function changes, but the new wrapper uses its existing fail-closed UnknownShape handler, exercised by actual negative hook decisions. Author test logs were inspected without being claimed as independent reruns.

Final selected scan completed with exit 1 and 29 existing task_actions handler findings (raw SHA256 `fe1a6da98483c56e31eaac6c1ee0e3f6cfb141b30cff518a59a2ecf84de4e86d`). All 21 exception-handler ASTs exactly match the develop base. The new helper adds no handler; actual unknown-shape negatives pass through the existing fail-closed action handler and deny the hook. Existing per-finding review and #1329 debt are retained, not represented as a clean scan.

The adjacent execution-risk suite also passed 13 tests in 13.298 seconds. Publication metadata is validated manually with the target pending Core compact commit-msg adapter, not the develop-base legacy role-artifact parser. This isolated branch is committed locally for integration; no publication or pre-push protocol is fabricated here.

Independent rebind evidence: `env-project-final-independent-rebind-20261112.json`, SHA256 `25ac4bb6394a4d8ef968eaf67de0e160f191e6e6aa078a591f0b7ab5e8a119fc`.

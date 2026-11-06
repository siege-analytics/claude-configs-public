# Own-session copy destinations and Git message reads

Goal source: https://github.com/siege-analytics/claude-configs-public/issues/1166; related #1152. Baseline c4d2f8afa6d9d446cb7bff2f0058cca75ba9e076. Recorded before source/test edits in isolated fix/own_session_operands_1166.

## Investigation and design

The existing parser already treats ordinary cp sources as reads and permits own-session file writes. However it represents a directory copy destination as the directory operand rather than actual copied names; the own lifecycle checker rejects data/plans root directories as file writes. The copy fix must resolve actual destination names, not broadly exempt directory contents. Preserve source mutation targets for mv and link/preserved-symlink copies. Inspect existing destination aliases/hardlinks within bounded recursive targets so copy cannot overwrite a foreign file through an own-directory name. mkdir option values such as -m must not become fake mutation paths.

Git target inference currently adds every slash-bearing argument, including commit -F/--file message input. Remove only modeled message-file read operands from commit mutation inference; keep the repository toplevel target and all actual pathspec/output targets. Existing ticket/message and protected-Git policy remain authoritative. Do not relax configuration/file mutation composition around commits; return a clear supported split form for cleanup rather than misleading cross-task ownership.

No tar/venv/clone/pip generalization from #1152 is included. No fake scope paths, source tier waivers, installed settings changes or protected operation bypass.

## Risks and test plan

Launch-blocking Tiger: allowing a destination directory without resolving children can overwrite a symlink or multiply-linked target. Add negatives for destination symlink/descendant symlink/hardlink, cross-session destination, cp link/preserved-link modes and source-removing mv. Bound recursive inspection; unknown copy shapes remain guarded.

Red-first actual hook fixtures compare Write with cp -p into own data directory, cp -pR predecessor data into own fresh data, mkdir mode options, and scoped Git commit -F own-session message. Assert other-session writes deny, mv cannot borrow source read authority, and commit-plus-cleanup gives a supported split diagnostic. Classify hooks without live protected Git mutations. Then focused tests and existing related parser/ownership tests; genuine native producer receipt at committed head before push. Root owns publication, integration and installation; do not edit frozen1173.

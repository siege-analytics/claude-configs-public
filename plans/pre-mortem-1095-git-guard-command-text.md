---
ticket_refs:
  - siege-analytics/claude-configs-public#1095: git guards match their verbs in prose; spawn-guard accepts empty labels
---

## Pre-Mortem
Task: port electinfo's command-text helper and its guard fixes (commit/add verbs matched as code, staged targets only, explicit spawn labels) upstream.
Ticket: siege-analytics/claude-configs-public#1095

### Tigers

#### Tiger 1: A real commit or add stops being caught (Severity: high)

Mitigation:
- `ct_is_git_commit` and `ct_code_only` strip only heredoc bodies and quoted spans. Code outside them is unchanged.
- The helpers fail closed: without python3 they return the raw text.
- `commit_detector` (24) and `broad_staging` (9) assert the real forms still block: chained `cd && git commit`, `git -C`, and `git add -A/./--all`.
- The fast-skip oracle suite (213) still matches the pre-#1083 verdicts with the new guards.

#### Tiger 2: no-attribution loses the quoted message (Severity: high)

Mitigation: the attribution scan reads the RAW text after the verb, never `ct_code_only`. The `commit_detector` cases from 2934a87 pin `Co-Authored-By` in a quoted message.

#### Tiger 3: spawn-guard rejects legitimate spawns (Severity: medium)

Mitigation: only a missing or empty label array is rejected. The `spawn_guard` suite (14) covers explicit labels passing.

### Launch-Blocking Assessment

None identified, provided the suites stay green at the head.

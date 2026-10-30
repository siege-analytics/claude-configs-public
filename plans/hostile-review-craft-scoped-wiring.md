# Normal Craft scoped wiring review

Read-only review of the unstaged normal-wiring slice in /private/tmp/claude-config-craft-wiring against the staged, previously accepted skill-ownership baseline, 2026-10-30. Includes new orchestration test and wiring plans. Verdict: approved after the corrections below; no remaining must-fix findings in this slice.

Normal install/sync consistently target workspace/.claude/craft-settings.json across base installation, wrapper wiring and local verification. Missing bootstrap helper refuses before deployment. Failed local verification prevents apply. Successful local checks precede mandatory apply and read-only registration verification; shell failure handling prevents a false completion claim. Receipt presence selects only a fixed non-autoload filename; no unverified receipt field chooses a path or grants authority. Legacy low-level defaults remain explicit compatibility behavior. Router authority and actual SDK callback delivery are separate review/UAT concerns, not established here.

Corrections from independent review:
- Wrapper retirement initially removed foreign same-basename commands. Both build and wire merges now use exact generated command token identity, preserve foreign command/text/malformed entries and metadata, and avoid accumulating empty groups.
- Verifier initially selected a foreign same-basename wrapper before the actual managed entry. It now selects the exact deployed wrapper while retaining missing/external/malformed diagnostics when no managed registration exists.
- Touched shell JSON/manifest probes interpolated paths into Python source. They now pass paths as argv, and quoted/apostrophe HOME fixtures pass. Generated wrapper paths are shell-quoted.
- Build merge initially reset malformed existing JSON. It now refuses without overwriting those bytes; direct temporary regression covers this preservation rule.

Independent final checks all passed: craft_installer_wiring_test.py (fake HOME, no actual global changes), wire_enforcement_automations_test.py (actual CLI, explicit destinations/idempotence), progressive_mount_test.py (real temporary deploy/verifier, receipt filename routing, foreign preservation, malformed policy refusal). Earlier independent native20/20 checked the predecessor verifier, and author reports final native20/20 after managed-selection correction; no independent claim of that later full native run. Frontmatter/inventory and scanner inherited debt are separately recorded rather than described as passing.

No live workspace/global/user configuration was changed by reviewer. The helper implementation is separately reviewed; this receipt approves its bounded orchestration, not arbitrary global policy. Exact aggregate commit, generated checks, protected CI and real backend canary remain separate acceptance gates.

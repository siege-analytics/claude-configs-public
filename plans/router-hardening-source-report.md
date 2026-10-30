# Router hardening implementation report

Author-side handoff, not independent approval. No commits, global apply or live
workspace changes were performed. The coordinator owns final independent review,
source binding, generated artifacts, complete scanner rerun, protected CI and
actual host canaries. Installer publication/CAS and legacy project env retirement
are a separate implementer's slice.

## Implemented boundaries

N1: command_for emits a constant /bin/sh -c program with router/workspace/event
transported as separate positional arguments. A callback with neither supported
Craft marker returns zero before Python/router-file loading. A marked callback
with a missing router fails with status two and an actionable repair message.
Canonical command text is the strict ownership identity, including shell program
and quoting, rather than approximate token equality. A separate exact canonical
legacy recognizer exists only for safe installer migration; runtime verification
rejects legacy direct Python registrations. The installer author integrated that
migration rule without retiring unknown/operator commands.

M1: PreToolUse top-level decision=block and continue=false normalize to the
permissionDecision=deny channel. An explicit top-level denial combined with
allow/ask fails closed in either order. A deny result does not retain top-level
approve or continue=true fields. Explicit SDK JSON denial retains exit-zero JSON
protocol semantics; actual failed hook exit codes retain status-two blocking.

M2: tool matcher selection uses re.fullmatch. Write does not select TodoWrite,
and Edit does not select MultiEdit/NotebookEdit unless listed.

M3: workspace_policy_commands is the shared exact physical workspace/hooks
ownership parser, preserving the former installer semantics. Runtime registration
loads the pinned policy and passes it to verify_global. Verification refuses an
exact known workspace-policy command directly registered in global settings;
it does not auto-delete or classify unrelated operator commands as ours.
The installer author delegates its managed_commands compatibility function to
this helper and passes policy through both pre-write global merges and final
verification. Fixture preflight proves refusal before settings/receipt publication.

M5: markerless native callbacks return before path resolution or policy reads.
Marked enrollment path resolution is now inside the fail-closed main exception
boundary. Resolution errors produce status two plus SDK denial, not an unhandled
exit-one error. Existing supported ancestry boundaries were not broadened.

Env follow-up: verify_global refuses only the exact known legacy user-global
CLAUDE_CA_ENFORCE string value '1', with native CLI cleanup guidance, without
modifying it. Altered/operator values survive. The wire helper copies only that
known generated key when its generated value is '1' into its selected policy;
unknown generated env is not copied and operator env remains. Missing/other
source values leave an operator value alone. Malformed source/target env objects
are rejected without replacing target bytes. No env flag was made a required
trust/authority condition; the wrapper remains active independently of this
legacy flag. Project legacy-flag retirement belongs to the installer author.

## unchanged scope

N2: only the observed canonical /Applications/Craft Agents.app host executable is
supported. Marker-only native spoofing remains out of scope; no broad host trust
or deny-all-native rule was added. The coordinator owns its final documentation
and acceptance decision. M4: a synthetic unconfigured/unresolved workspace cannot
select policy merely from a template marker. M6: proven allowed reads remain
allowed without granting mutation authority. Neither local files nor these
fixtures establish Pi/Codex parity or actual SDK callback delivery.

## Verification

Actual bin/_test/craft_hook_router_test.py: 25 tests passed in 6.105 seconds.
Log /private/tmp/router-hardening-tests.log. New controls cover markerless missing
router skip versus marked missing router deny, exact old registration migration,
known global policy duplicate refusal before writes, global legacy env refusal
and altered env preservation, whole-name tool matching, mixed JSON denials in
both orders and guarded enrollment resolution failure/native cheap no-op.

Actual bin/_test/wire_enforcement_automations_test.py passed. Log
/private/tmp/wire-owned-env-tests.log. Controls cover known generated env copying,
unknown/operator preservation, missing/altered generated flag behavior, malformed
source/target env byte preservation, prior path selection/idempotence and optional
automation behavior. Scoped diff whitespace check passed. These were disposable
fixtures; no actual user settings were applied.

Final independent review is pending. Publication/CAS tests and source changes
made by the installer author require that slice's own review. The complete final
scanner must be rerun: ownership parsing moved to the shared router helper, and
old raw source locations/counts must not be silently reused.

## Working source identities at author handoff

```json
{
  "hooks/lib/craft-settings-router.py": "20975b1477a4375c5169f6566911d9b2fe3f98b6eabbc62d1bd9b2f6c5398719",
  "bin/_test/craft_hook_router_test.py": "75acb741252e221ad8304bea76fbc9dc83de863ff1deeaa3aed59df385a85de5",
  "bin/wire-enforcement.py": "7a720c8aa71ced35fee76d7c886ea05802e519a6d7f3dfd9526064916fc4077f",
  "bin/_test/wire_enforcement_automations_test.py": "68b00f885e2ba1ed239d183fa14c760abdd3907743ddb12056f1ee783dc83225"
}
```

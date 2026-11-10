# Bind clone transport checks to destination configuration

Refs #1252. The reviewed fresh-repository source from #1242 is retained in full. A private actual-Git counterexample showed that a destination `includeIf gitdir` URL rewrite can select an external helper after neutral preflight. Conditional template settings did not reproduce an escape; unconditional template positive controls did, so this repair adds no conditional-template restriction.

Git parses include files and resolves the exact destination condition. Only potentially transport-affecting gitdir includes require an existing empty destination for the read-only context lookup. Create that directory within the existing Task scope and retry; no extra owner approval is needed. Ordinary cloning without those settings still creates a missing destination. Remote name, configured remote URL and URL rewrites use the same destination context. No transport runs during preflight, no persistent configuration changes, and existing Task ownership/path/role requirements remain.

Focused controls cover absent/existing normal and mirror destinations, the actual private helper counterexample, relative nested includes, missing includes, harmless conditional settings, safe SSH rewrites, unrelated gitdir conditions, conditional remote selection, and actual mkdir/retry cloning with independent objects. Full source tests and generated closure results will be recorded with the normal commit receipt. Hosted exact-head CI remains required.

## Assumptions

System/global Git configuration is read with Git itself, outside enclosing repository configuration. A bounded graph of include files is inspected without executing transport. Destination conditions are evaluated by Git, not by a hand-written glob matcher. Configuration mutation races retain the same limitation as existing preflight checks; no claim of atomic configuration pinning is made.

## Peer review

Root independently read the complete exact source/test diff and accepted source preparation at https://github.com/siege-analytics/claude-configs-public/issues/1252#issuecomment-6758296031. The separate configured Claude v4 review remains pending at this checkpoint.

## Lead review

Actual Git showed destination-conditioned clone.defaultRemoteName changes the selected remote. The repair therefore inspects and resolves both remote selection and URL values in destination context. No new permission, persistent config, blanket conditional-include restriction or template restriction was added.

## Quantified claims

The source bootstrap suite passed all 31 methods in 45.726 seconds, including two actual configured 16-hook creation chains. These are source/local results, not hosted exact-head CI or publication proof.

## Test plan

Run the public test-evidence producer against the exact two Python source paths, executing the full bootstrap suite and canonical closure checks; strictly validate receipt after the normal native-hooked commit. Preserve any failures. Required hosted CI and independent peer disposition remain necessary before publication.

Pre-mortem-artifact: plans/git-clone-conditional-context-1252.md
Hostile-review-artifact: https://github.com/siege-analytics/claude-configs-public/issues/1252#issuecomment-6758296031

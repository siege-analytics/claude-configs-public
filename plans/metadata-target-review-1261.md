# Metadata target review followup (#1261, #1245)

Actual isolated full-hook probes confirmed that numeric GitHub selectors with leading zeros or `#` could reach a legacy Task-free reporting shortcut. Independent read-only GitHub CLI probes confirmed that upstream/default remotes and URL rewrites can make implicit posts target a different repository from raw origin. No candidate remote mutation was executed.

## Assumptions

New posts require the existing own active Task and actual target proof. Existing text edits retain their existing checks. Descriptive prose does not require implementation artifacts or status keywords. Explicit repository selection remains available for multi-remote workspaces; no network, configuration mutation or additional owner approval is required by this repair.

## Pre-mortem

- Removing a second allow path could affect existing text edits. Preserve the typed resolver's metadata-only route and exercise edit, state and mixed-command controls.
- Numeric normalization could alter exact command authorization. Normalize only the parsed target identity; preserve actual command bytes and Task binding.
- Implicit GitHub remote selection could borrow origin scope. Allow only the proven sole-origin case with no resolved-default override and an effective URL identifying that same repository; require literal `--repo` or a canonical URL otherwise.
- Transport rewrites to the same GitHub repository are ordinary configuration. Preserve the same-identity HTTPS/SSH positive alongside foreign-rewrite negatives.

## Peer review

An independent reviewer read the four-file delta and found no remaining source blocker. Actual read-only GitHub CLI probes confirmed remote precedence, resolved defaults, numeric selectors and inherited GH_REPO behavior; the existing ambient GH_REPO/GH_HOST checks are retained. An alternate origin push URL alone did not change the observed issue target. Probe commands changed no fixture configuration and executed no remote mutation.

## Lead review

The resolver remains the single authority for new posts. The shared recognizer changes only parsed identity, and the conservative implicit-target proof adds no network call, configuration write or new grant. Explicit repository selection remains the actionable route when GitHub defaults cannot be proven.

## Quantified claims

The two focused methods passed in 15.702 seconds, including all16 configured hooks for numeric aliases, own-Task positives and foreign/no-Task negatives. All12 metadata methods then passed in 49.236 seconds with existing preparation, text-edit, state and compound controls intact. Full affected suites, canonical closure, genuine native source evidence and hosted checks remain separate predicates.

Pre-mortem-artifact: plans/metadata-target-review-1261.md#pre-mortem
Hostile-review-artifact: https://github.com/siege-analytics/claude-configs-public/pull/1261

The genuine four-input producer passed coordinator80 (including all12 metadata methods), destructive32, seven existing Task-scope compatibility methods, all six canonical closure checks and three changed runtime files in each of four package layouts. Independent full12 metadata methods also passed. No limits, credentials, Git configuration or production state changed.

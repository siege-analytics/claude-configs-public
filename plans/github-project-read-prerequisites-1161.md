# Project read prerequisites for task-owned Status updates

Goal source: siege-analytics/claude-configs-public#1193
Related: #1161
Pre-author-inventory: isolated8a8ccae7bb12cb47de3bb829d70b450c50ddf057; inspected gh_ok generic read verb list and typed project mutation fallthrough. Root live producer tree is untouched.

## Design and investigation

Official CLI references https://cli.github.com/manual/gh_project_field-list and https://cli.github.com/manual/gh_project_item-list document listing fields/items, including owner, JSON, limit and formatting. These are prerequisite reads, not board mutations. Current gh_ok omits both verbs, so literal reads fall into unsupported typed mutation rejection. Add only those two project subcommands beneath the existing browser guard; retain unsupported global host switches and reject late hostname flags. Existing list/view and general API policy remain unchanged. No new helper or grammar.

## Pre-mortem

Launch-Blocking Tiger: a shared verb extension inadvertently permits issue/other-service mutation or arbitrary GraphQL. Mitigate project-specific exact subcommand check, no global GH_READ_VERBS expansion, mutation/browser/host/shell-composition negatives under actual gate.
Paper Tiger: tests perform real board reads/writes. Classifier and hook decision fixtures never execute gh or call the network.
Falsification: project edits/deletes, mutation GraphQL, browser/host switches or composed writes gain ungated authority.

## Acceptance and test plan

Red-first pure classifier and real universal gate no-task positive checks for field-list/item-list with owner/JSON and safe pipe formatting. Preserve project list/view. Deny edits/deletes/--web/host switches/arbitrary mutation GraphQL/redirects/chained writes. Run the appropriate354 reader controls. Root source peer review precedes leaf commit/publication; no new PR, protected merge or installation by author. Native evidence/commit uses the true CLI context, no fabricated task artifacts.

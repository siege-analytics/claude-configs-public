# Discipline scripts

Canonical implementations of the discipline checks called by local
hooks and (optionally) skills. Single source of truth so the
local-hook and skill-internal versions cannot drift.

Originating plan: claude-configs-public#146. Per the plan's
writing-rules:1 / :3 / :4 framing, every "always-do-X" rule needs
paired automated enforcement that doesn't depend on per-actor
installation state, and every "this doesn't apply" claim needs an
evidence chain.

## Scripts

| Script | Inputs | Exit codes | Purpose |
|---|---|---|---|
| `check-self-review.sh <commit-sha> <artifact-path>` | work-commit SHA + path to review artifact | 0 OK / 2 BLOCK | Trailer presence + structural sections + artifact-predates-work (git-history check; closes retroactive-trailer loophole). |
| `evaluate-ticket.sh <ticket-ref>` | ticket reference (`#NNN`, `owner/repo#NNN`, `PROJ-NNN`, or local file path) | 0 PASS / 2 BLOCK | Ticket structural fitness rubric: title shape, required sections, investigated facts, `/think` link, Assumptions block, falsification criterion for behavior-change tickets. |
| `check-trivial-claim.sh <artifact-path>` | path to artifact with `## Trivial-change declaration` and/or `## Exemption:` blocks | 0 OK / 2 BLOCK | Each block has Reason / Evidence / Falsification fields; Evidence contains command output or verifiable observation token, not free text. |

## How callers invoke

### Local hooks

Already in this repo at `hooks/git/`. Hooks call the scripts via
absolute path resolved at hook-install time. Hook-internal fallback
implementations exist for workspaces that don't have a cloned
`claude-configs-public/scripts/discipline/` directory available.

### Skills

`thinking/think/SKILL.md` Step 0 invokes `evaluate-ticket.sh`.
`self-review/SKILL.md` references `check-self-review.sh` and
`check-trivial-claim.sh` in its discipline body.
`coding/code-review/SKILL.md` Pre-review section invokes
`evaluate-ticket.sh`.

## Why three scripts, not one

Each script answers one falsifiable question, exits with a clean
status code, and produces a focused error message. Combining them
into one would either explode the input surface or smear the failure
mode across multiple concerns. Per writing-code:5 (no premature
abstraction), keep them separate until a real consolidation case
appears.

## External tracker support

`evaluate-ticket.sh` v1 supports GitHub via `gh issue view`. Linear
and Jira fetcher hooks are stubbed (defined but not enabled). Per
user direction (session 260502-vital-channel): "Allow linear and
jira but I don't use them in any significant way right now."

To enable a stubbed fetcher, edit the `fetch_ticket` function in
`evaluate-ticket.sh` to remove the `# TODO(linear)` / `# TODO(jira)`
guards and ensure the corresponding CLI (`linear-cli` / `jira-cli`)
is installed in the calling environment.

## Rubric configurability

Per user direction, the rubric is **canonical across all repos** —
no per-repo `.claude/ticket-template.md` override. Update the
canonical rubric in `evaluate-ticket.sh` and the change propagates
to every consuming repo. Avoids drift between projects.

## License

Same as the rest of `claude-configs-public`.

# Attribution recovery and authorized continuation (#1215)

## Goal and scope

Implement the user's instruction: prevent agent/tool co-author attribution, and treat an existing prohibited trailer as candidate-history cleanup rather than a reason to stop the authorized objective. Source owners are `skills/_output-rules.md`, `skills/commit/SKILL.md` and the attribution hook diagnostic. Root owns generation, commit and publication. Attribution detection, exit status, credentials and identity defaults are unchanged; the hook message explicitly scopes rejection to the bad command.

## Investigation before edits

- Output's Attribution section already bans AI/tool markers (including Craft Agent) and requires stripping automatic additions before push.
- Its Diffs section contradicts recovery: amend is restricted to unpublished commits, yet published branch rewriting uses force-with-lease; it also prescribes unscoped filter-branch/filter-repo.
- Commit's mistake section always requires a new commit after push. A new commit cannot remove a trailer from an earlier candidate commit.
- Both source owners are packaged skill/rule content. Existing fingerprint and protected Git guards remain the enforcement owners; prose changes do not waive them.
- User-level AGENTS requires direct PR review comments. Repository AGENTS is absent. Read the existing Think/Investigate entry contracts; this behavioral rule edit is not a trivial-doc exemption.

## Design and alternatives

Keep the ban canonical in Output; Commit links to its bounded recovery rule. Continue implementation, design and verification that remain within the grant while history cleanup is pending. Own unpublished candidate commits can be amended/reworded through scoped rebase. Published owned feature branches require current writer coordination and project-authorized force-with-lease; never bare force, protected branch history, or another owner's history. If rewrite authority is missing, park that rewrite and prepare a clean candidate through the allowed project path. Preserve legitimate human authorship and human co-author records.

Reject: relaxing the ban, appending a new commit that leaves the old trailer, blanket new approval, disabling a hook, or automatic whole-repository history filtering. Prevention of automatic attribution is a separate host preference check owned by Root, not this source change.

## Pre-mortem

- Tiger: recovery guidance authorizes rewriting shared/protected history. Mitigation: limit to the agent's own candidate history, coordinate active writers, preserve project/role authority and protected branches.
- Tiger: discovered trailer becomes a global task hold. Mitigation: hold only publication/history action that lacks readiness or authority; continue independent authorized work.
- Tiger: cleanup erases real human credit or transfers exact-head acceptance silently. Mitigation: preserve human authorship and rebind required evidence after rewritten history.
- Paper tiger: instructions imply new permission for an already-authorized owned-branch repair. Mitigation: apply existing grant and actual project conditions; ask only for genuinely missing authority.

## Review and validation plan

Root independent source review before generation/publication. Check cases: prevent new automatic AI trailer; amend owned unpublished tip; reword older candidate; coordinate authorized published feature cleanup; protected/shared history refuses rewrite while safe work continues; missing authority parks only rewrite; legitimate human credit retained. Preserve required review/CI/hooks and exact-head evidence. Do not claim native history rewrite or installed behavior from this prose change. The initial authoring slice performed no commit, generator, push or live activation. Root later applied the user-authorized host opt-outs with preservation snapshots and added the command-scoped diagnostic after the operator explicitly requested consistency at every level.

## Host and diagnostic evidence added during review

Local CraftAgents includeCoAuthoredBy changed from absent/default-on to false with all other preference values preserved; remote was already false. Local terminal Claude attribution.commit/pr set to empty strings, preserving hooks and all other settings. Official settings reference: https://code.claude.com/docs/en/settings-reference#attribution. Existing-session prompt pinning is not retroactively changed and no running app/session was restarted. The canonical rule documents the distinct host options without making their configuration another implementation gate. Attribution hook logic remains identical; its rejection explains correcting the current commit message and continuing other work. Existing commit-detector scenarios verify rejection of the attributed commit and acceptance of unrelated commands.

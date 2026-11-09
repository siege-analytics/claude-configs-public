---
ticket_refs:
  - siege-analytics/claude-configs-public#1218
---

# Mechanical coordinator transitions

Ticket: siege-analytics/claude-configs-public#1218

## Pre-implementation investigation

The coordinator guard currently requires owner wording for every ready/close.
GitHub login alone cannot establish agent ownership because agents share the
operator account. The existing resolver binds a host session to task gates,
scope paths and implementing lifecycle. Existing session labels distinguish
reviewers/observers; those roles cannot acquire implementation through this fix.
The mutation gate remains the lifecycle authority; this helper adds no new
implementing-only phase requirement.

## Design

Add one bounded reader for literal `gh pr ready` and issue/PR close commands.
Ready requires the selected own task, its canonical ticket, local Git
branch/head and live PR author/head/issue relationship. Close requires the
same task binding and live landed fixing/superseding PR, merge commit reachable
from its actual base, and exact item relationship. Issue fixes must also reach
the repository default integration branch. Existing rollout evidence/N/A
remains required; the proof replaces invented owner wording. A PR supersession also
requires equal base branches. Wording nominates evidence; it never proves it.
No reopen/review/merge/queue/protection exemption is added. Ordinary task gates
and explicit holds remain separate requirements.

## Pre-mortem

Shared credentials could authorize another agent's PR: bind ready to local head
and task issue as well as viewer/author. Compound shell commands could smuggle
an unrelated action: no mechanical allowance for wrappers/operators/expansion.
Network failures or malformed/oversized/partial responses could create an
allowance: bounded fixed reads fail closed. Wrong-base or unrelated merged PRs
could close an item: verify base ancestry and exact relationship from GitHub.

## Validation and canonical refresh

First run actual coordinator-hook fixtures against unchanged source and retain
the expected red result. Add positive and adversarial live-read fixture cases,
then run the original coordinator suite and relevant task/merge queue checks.
Author and stage source, tests and documentation before generating canonical
outputs. Freeze the final diff for parent source review; no commit/push here.

## Red-first observations

The unchanged coordinator hook failed exactly the three positive behaviors
(own draft review request, landed issue close, landed PR supersession); its
negative fixtures passed. The initial coordinator-only implementation passed
nine methods. A subsequent full configured 16-hook Bash-chain fixture exposed
a second real blocker: destructive-guard still classified mechanical closes
as generic GitHub shared-resource writes. It now reuses only the same literal
close proof; no merge/enqueue/API or other GitHub-write allowance was added.
The old coordinator suite also caught a diagnostic wording mismatch; its
existing lack-of-evidence prefix is retained. Final checks follow below.

## Source validation

- Focused suite: 12 methods pass; includes 48 actual configured Bash-hook
  invocations for own ready, integrated fixed close and superseded PR close.
- Existing coordinator suite: 79 pass, zero failures.
- Existing destructive suite: 32 pass, zero failures.
- Existing pinned queue suite: 17 methods pass.
- Both-layout build, source/Claude/Craft hook validators and generated source
  authority write/check pass. Validators report existing unreferenced hooks.
- The first authority attempt failed because the authoritative skill inventory
  had not been refreshed. Running skill-inventory before authority generation
  corrected that ordering; no error was relabeled as a pass.

## Review and limits

Parent source review remains required. This branch is prepared locally and
uncommitted; no source was installed and no remote ready/close operation was
performed. Fixed GitHub-read fixtures validate admission, not successful remote
mutation. Reads are bounded to three seconds each and eight seconds total,
inside the existing ten-second hook budget; proof/execution are not atomic.
Normal required default-branch integration, explicit holds, applicable
verification, actual role authority and server protections remain in force.

## Corrective source review and composition

Root reproduced two invented evidence requirements in the first candidate:
ready required a Fixes keyword instead of normal Refs, and an integrated fixing
PR had to share the current actor. Two red-first methods reproduced them.
Canonical Refs/References lists now supply the exact item relationship for
ready and issue close; close still requires actual landed/default-integrated
proof and explicit rollout evidence. Only the target own PR needs current
actor ownership. Issue close performs no gratuitous /user lookup.

Peer inspection found fenced/example relation laundering. Actual hook cases
now reject code fences (including nested shorter fence markers), quoted/lazy
blockquote paragraphs, foreign references, other items, negations and examples.
A malformed helper import now gives exit 2 rather than advisory exit 1.

A literal `cd /absolute/bound/task/worktree && gh ...` prefix works from native
session cwd through all 16 configured Bash hooks. The helper resolves the sole
bound task repository rather than treating session cwd as the source worktree.
No UMG exception was needed. Numeric selectors and same-repository PRs are
modeled; arbitrary wrappers/extra commands, URL/default selectors and fork
worktrees retain the existing evidence path. An ambiguous task needs its
existing binding, not another operator approval.

The 1210 pure `github_review_reply` interface is consumed when present. Its
reply BODY is not evaluated as workflow status; UMG retains all grant/network
verification. An isolated actual-hook composition with immutable 1210
snapshot 9c75ce55e3a56e0c4293a8499fc03b62c9f6869b passed valid completion-like
reply prose and denied malformed/nonreply controls without a GitHub call.
The task_actions snapshot SHA is
6ac73538eb21d0dfe12d17999b2b0929489a948f36e84cdf568993a438c5e833.

Corrected focused validation: 17 methods passed in 28.086 seconds with the
immutable 1210 composition (no skips), plus the new explicit-role/verifier
method passed in 1.330 seconds. Existing explicit read-only/review-only,
comment-only and observer constraints stay denied; a verifier label alone is
not a new phase/permission ceremony. Prior 79 coordinator, 32 destructive and
17 queue regression passes above predate these focused source corrections.

Reconciled to actual develop 6cae44ad3c09c3cf6fb980428bbc5ca5ee330c31 via a
private binary patch and retained reversible stash. The existing eight-line
1222 read-only change is unchanged. Final generation follows staged authored
source; parent/peer acceptance still precedes commit or publication.

## Joint 1210/1218 parser ownership

Root's actual native-fit cases require Refs lists and a central ticket such as
electinfo/enterprise#3304 linked from a different code repository's PR. The
reviewed relationship parser now has one owner in `task_actions.py` as
`github_ticket_reference(body, number, repo, kind='fix', item='issues',
source_repo=...)`. Mechanical proof imports it rather than retaining duplicate
grammar. The source repository is the actual PR repository: relative #N never
becomes a foreign central issue, while explicit canonical references may cross
repository boundaries. The parser performs no I/O or authorization.

The mechanical hosted tests now require the actual tracked joint classifier
and shared parser. The earlier private snapshot override and skip were removed.
Root combines both features before hosted validation; standalone 1218 does not
claim to provide the missing 1210 source dependency. A pure cross-repository
matrix adds same-repo compatibility and foreign-relative denial alongside the
existing actual-hook cases. Final joint validation follows the immutable 1210
source handoff; no mutable sibling worktree is copied.

## Final actual joint-source validation

The immutable 1210 tree `57fa081db506d647339500c65fe6bfd94a74ce0f` supplied
only its seven owned source paths, each hash-verified, to an isolated copy of
the staged 1218 source. All 19 mechanical methods passed in 97.485 seconds.
The hosted test itself used actual tracked helpers: no private snapshot
environment override, alternate parser or skipped composition case remained.
Coverage includes 48 configured Bash-hook positive invocations, shared central
versus relative repository references, implicit-POST/jq replies and their
GET/duplicate-jq/nonreply denials, with no coordinator authorization lookup.

Evidence: `coordinator-1218-joint-validation.json` and its log in the private
release-prep evidence directory. This is source admission validation, not a
remote mutation or installed-runtime claim. Root owns the final joint canonical
refresh and publication; the three stale component catalogs are excluded from
the authored-only handoff.

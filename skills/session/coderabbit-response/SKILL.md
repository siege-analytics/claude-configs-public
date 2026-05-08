---
name: coderabbit-response
description: "Triage and respond to CodeRabbit (or similar bot) review findings on a PR. Decides which comments to fix, which to resolve-with-reply, and which to dismiss; manages the stale-review-blocks-merge problem."
disable-model-invocation: true
allowed-tools: Bash Read Grep Glob Edit Write
argument-hint: [pr-number]
---

# CodeRabbit Response

Use this skill to triage a CodeRabbit (or similar bot) review on a pull request. See [reference.md](reference.md) for GraphQL command templates and GitHub review-decision rules.

## When to Use

After CodeRabbit posts CHANGES_REQUESTED on a PR and you need to decide: fix, reply, or dismiss.

Runs from the repo root with the PR checked out (or the PR number as `$1`).

## Decision Tree

```
START: CodeRabbit posted N threads
  │
  ├─ For each thread, classify severity (CR marks 🔴/🟠/🟡/🔵):
  │   🔴 Critical — likely a real bug or security issue
  │   🟠 Major    — code quality / correctness concern worth fixing
  │   🟡 Minor    — nit that might matter
  │   🔵 Trivial  — preference, not correctness
  │
  ├─ For each thread, decide:
  │
  │   FIX if:
  │     - It's a 🔴 Critical (never skip these; validate the claim)
  │     - It's 🟠 Major AND the fix is < 30 min
  │     - It reveals something you'd catch in self-review anyway
  │
  │   RESOLVE-WITH-REPLY if:
  │     - You disagree with the suggestion (document why)
  │     - The context makes the suggestion wrong (e.g. "use async" on
  │       sync code that must stay sync)
  │     - It's a style preference the project explicitly rejects
  │
  │   DISMISS if:
  │     - CR's stale review is blocking merge because GitHub doesn't
  │       treat COMMENTED as replacing CHANGES_REQUESTED
  │     - The thread is outdated (file changed substantively)
  │
  └─ Never:
      - Blindly apply autofix without reading the diff
      - Dismiss a review just because it's inconvenient
      - Mix "resolve" with "dismiss" — resolve = thread, dismiss = review
```

## The stale-review trap

GitHub's review decision rule: a reviewer's latest *non-COMMENTED, non-DISMISSED* review is what counts. A later COMMENTED review does NOT replace an earlier CHANGES_REQUESTED from the same reviewer.

**This means:** after you fix CR's concerns and push, CR may re-review with COMMENTED. Its CHANGES_REQUESTED persists. Your PR stays blocked.

**The fix:** dismiss the stale CHANGES_REQUESTED explicitly. Then your own APPROVED can stand alone.

Check what GitHub considers active:
```bash
gh api "repos/OWNER/REPO/pulls/$PR/reviews" \
  --jq '.[] | {user: .user.login, state, commit: (.commit_id[0:7]), submitted_at}'
```

Look for any `coderabbitai[bot]` entry with `state: CHANGES_REQUESTED` that hasn't been dismissed. That's the one blocking you.

## Severity vs. action matrix

| CR says | Severity | Default action | Exception |
|---|---|---|---|
| "bare except catches too much" | 🟠 | Fix (see python-exceptions skill) | — |
| "hardcoded password in test" | 🟠 | Replace with fixture const + `# noqa: S105` | Real secret → rotate NOW |
| "F401 unused import" | 🔵 | Fix | Re-export intentional → `__all__` or `# noqa: F401` |
| "missing regression test" | 🟡 | Add one if it's in diff | Skip if test infra for that path is broken |
| "consider renaming X to Y" | 🔵 | Reply "style preference; deferring" | — |
| "this function is too long" | 🟡 | Fix if < 30 min refactor | Reply + linear ticket if it's >30 min |
| "potential SQL injection" | 🔴 | **Fix immediately**; verify the fix | Rare case where it's a mock / test stub |
| "this will break existing callers" | 🔴 | Audit callers (see library-api-evolution) | Confirmed no callers → reply + fix forward |
| "consider async here" | 🔵 | Reply "not async-first" | — |

## Phases

### 1. Pull the review state

```bash
gh pr view $PR --repo OWNER/REPO --json reviewDecision,mergeStateStatus
gh api graphql -f query='query {
  repository(owner:"OWNER", name:"REPO") {
    pullRequest(number: '$PR') {
      reviewThreads(first:30) {
        nodes {
          id isResolved isOutdated path line
          comments(first:1) { nodes { body author { login } } }
        }
      }
    }
  }
}' --jq '.data.repository.pullRequest.reviewThreads.nodes[] |
    select(.isResolved == false and .isOutdated == false) |
    {id, path, line, severity: (.comments.nodes[0].body | .[0:80])}'
```

### 2. Classify each open thread

Load the full file the thread is on. Read the CR comment body. Apply the decision tree. Mark each thread in a scratchpad:

```
[FIX] thread#PRRT_xxx — boundary_providers.py:368 — format kwarg dropped
[FIX] thread#PRRT_xxx — polling_analyzer.py:265 — silent except
[REPLY] thread#PRRT_xxx — style: _LEVELS as tuple (fine either way)
[DISMISS-REVIEW] CR CHANGES_REQUESTED review id=41xxxx on old commit
```

### 3. Execute FIXes

One commit per concern is ideal; bundled is fine if tightly related. Commit messages name the CR concern, not just "fix lint":

```
fix(#386): propagate format kwarg to get_enacted_plans
fix(#386): make RDH credential precedence deterministic (explicit None check)
fix(#386): is_available requires both username AND password
```

Cross-reference: the python-exceptions skill for except-pattern fixes; the library-api-evolution skill for signature changes.

### 4. Resolve threads for FIXed and REPLY items

```bash
# Resolve (closes the thread; no merge-block effect)
gh api graphql -f query='mutation {
  resolveReviewThread(input:{threadId:"PRRT_xxx"}) {
    thread { isResolved }
  }
}'

# Reply-then-resolve (for REPLY items)
# There's no single mutation for "add reply then resolve"; do it as two calls.
# Use mcp__github__add_reply_to_pull_request_comment or gh api with the REST
# comments endpoint, then resolveReviewThread.
```

### 5. Dismiss stale CHANGES_REQUESTED reviews

```bash
gh api --method PUT \
  "repos/OWNER/REPO/pulls/$PR/reviews/$REVIEW_ID/dismissals" \
  -f message="Addressed in <commit-sha>. See resolved threads above."
```

### 6. Re-approve if your own approval got dismissed by force-push

Force-push dismisses existing reviews on the old commit. If you previously approved, you need to re-approve on the new head commit.

### 7. Verify

```bash
gh pr view $PR --repo OWNER/REPO --json reviewDecision,mergeStateStatus
# Goal: reviewDecision = "APPROVED" (or ""), mergeStateStatus = "CLEAN" or "BEHIND"
```

If still BLOCKED, check:
- Remaining open threads
- Other reviewers with pending CHANGES_REQUESTED
- Required status checks (CI) failing
- Branch behind base

### 8. Feed the lessons-learned ledger

For each FIXed thread, ask: "is this a recurring pattern, or a one-off?" If recurring (you've seen it before in this repo, or it points at a project-wide invariant), invoke [skill:lessons-learned] to log or bump the corresponding entry in `LESSONS.md`.

Heuristic — log when **any** of these are true:

- The same CR rule has fired on 2+ prior PRs in this repo
- The fix touches a hot file (one with frequent CR findings)
- The finding is 🔴 Critical (security, data loss) — log even at recurrence 1
- Your own intuition says "we keep getting this"

Do NOT log:
- 🔵 Trivial style nits
- One-off bugs with no underlying pattern
- Findings already covered by an existing ledger entry — bump that entry's recurrence instead

## When you disagree with CR

Reply once, substantively, with the reason. Then resolve. Example:

> CR suggests replacing `except Exception` with `except (ValueError,
> KeyError)`. In this specific function the library-under-test can
> raise anything from `botocore.exceptions.ClientError` down to
> `socket.timeout`. Cataloguing them is worse than the broad catch +
> log-and-reraise pattern. Keeping as-is.

Don't explain the same disagreement to CR twice. If CR flags it again after your reply, dismiss the new review with a pointer to the thread.

## Anti-patterns

- **Autofix without reading.** CR's autofix branch can introduce its own bugs. Always review the proposed diff before pushing.
- **"Fix everything CR says."** Bots have systematic blind spots. A 🔵 trivial on unused `_` prefix in a deliberately-underscored arg is wrong.
- **Dismissing without a message.** Leaves future readers without context.
- **Mixing resolve and dismiss.** *Resolve* closes a specific thread. *Dismiss* removes a review from the merge-decision calculation. Different purposes.
- **Force-pushing to amend and forgetting to re-approve.** Your own approval got invalidated; re-add it.

## Attribution Policy

NEVER include AI or agent attribution in code, commits, or documentation.

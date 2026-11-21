# Hostile review: #181 selected commit-msg path

## Review source

CodeRabbit review on PR #1480: https://github.com/siege-analytics/claude-configs-public/pull/1480#discussion_r4649224951

## Findings and disposition

1. **Selected-path bypass, fixed:** `.githooks/commit-msg --selected` delegated to `native_git.py` before checking the final message. The selected path now checks the single message file before delegation. A regression invokes that path with a human co-author trailer and requires the explicit prohibition diagnostic.
2. **SIGPIPE false negative, fixed:** The old `printf "$COMMIT_MSG" | grep -q` check could make `grep -q` exit before `printf` finished writing, causing `pipefail` to mask a match. The hook now runs `grep` against the message file through input redirection. A 2 MB message test exercises an early trailer followed by a large payload.

## Adversarial verification

- Focused hook suite: 16 passed, 0 failed.
- Selected registration suite in the pinned validation environment: 14 passed.
- Bash syntax and diff whitespace checks passed.
- CI on the follow-up PR remains the final integration check.

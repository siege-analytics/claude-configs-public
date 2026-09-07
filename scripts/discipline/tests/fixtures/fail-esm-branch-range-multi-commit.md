# Fixture — FAIL (multi-commit branch-range: ESM touch upstream of HEAD)

Simulates the reviewer's finding #2 scenario: a two-commit branch where
commit 1 touches `hooks/git/foo-hook.sh` (external-shape-modeling code)
and commit 2 adds this self-review artifact with a valid-vocabulary
Trivial-investigation declaration. When the delegated checker is invoked
with a branch-range diff-list (union of merge-base..HEAD, HEAD, working
tree, staged), the ESM-touching path from commit 1 IS included and the
never-trivial trigger fires — regardless of the Category value.

Corresponding diff-list: `diff-list-branch-range-multi-commit.txt`.
Contains an ESM file (`hooks/git/foo-hook.sh`) alongside non-ESM files
(`plans/self-review-example.md`, `docs/context.md`, `README.md`) — the
pattern a real branch-range diff would produce.

Reviewer intent: `hooks/git/self-review.sh` must compute the diff list
via `git diff <merge-base> HEAD` so this scenario blocks. Before PR A's
fix, this fixture would still PASS at the checker level (checker just
processes whatever's in the list) — the bug was at the HOOK level where
the list was only `HEAD` + working + staged, so commit 1's touch never
entered the list at all.

## Trivial-investigation declaration

Category: test-only
Cannot produce error: Adds a fixture case only.
Evidence: `git diff --stat` shows one test file changed, 8 insertions.
Falsification: If a non-test file is modified.

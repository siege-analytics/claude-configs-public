# Hostile review: issue reporting gate carve-out

Reviewer source: independent secondary model, Sonnet-class with extended reasoning.

## Scope

Reviewed `gh issue create/comment` carve-out across `hooks/bash/destructive-guard.sh` and `hooks/bash/universal-mutation-gate.sh`, plus regression tests.

## Findings

Initial review found over-broad flag acceptance, duplicate flag ambiguity, stdin body-file ambiguity, and destructive/universal PR-write alignment gaps. Those were fixed before commit.

Final review findings: none.

## Verdict

PASS.

## Final reviewed properties

- Known flags only.
- Duplicate flags blocked.
- Stdin-like body files blocked.
- Shell chaining/metacharacters blocked.
- Issue close/edit/delete/reopen/label blocked.
- PR create/merge blocked in both destructive and universal gates.
- Evidence-bearing issue create/comment with inspectable body allowed as governance reporting.

# Hostile review: Siege Utilities review shelf grounding

Frame: grumpy Scala/JVM reviewer. The prior Python worker got excited, pushed code, and then apologized. That is exactly the failure mode this patch must prevent.

## Surface reviewed

- `skills/code-review/SKILL.md`
- `skills/hostile-review/SKILL.md`
- `skills/_siege-utilities-rules.md`

## Findings

PASS with watch item.

- The code-review skill now requires function contracts, chains, shelf/general-guide evidence, and fixture evidence before approving utility-library changes.
- The hostile-review skill now requires chain-level findings and requires DDIA/data-intensive for caches, derived data, data validation, persisted API results, and geocoding correctness.
- Siege Utilities rules now explicitly say a PR comment, local tests, or fixed configs checkout is not authorization to push code.

Watch item: this is guidance, not a mechanical push gate. If agents keep violating it, convert the workflow into a check or PR template requirement.

## Verdict

PASS. This is the correct precondition before asking an agent to redo the Siege Utilities hostile review and Python implementation.

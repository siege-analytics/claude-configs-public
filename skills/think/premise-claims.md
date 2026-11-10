# Verifiable premise claims

Use this reference when writing or updating signal claims, and for every class-of-bug fix. See [task evidence](task-evidence.md) for ownership and lifecycle.

### Schema A claims for class-of-bug fixes

When a fix addresses a class of bug (the same pattern in multiple
files), the signal file MUST include at least one Schema A claim
(machine-verifiable: file + grep + expected) that asserts zero
remaining unguarded instances. The hook checks this every turn.

Example: fixing unguarded `grep` in pipelines across hook scripts:
```json
{
  "claims": [
    {
      "assertion": "No unguarded CD_COUNT grep patterns remain in hooks/",
      "file": "hooks/",
      "grep": "CD_COUNT=.*grep.*[^}].*|.*wc",
      "expected": false
    }
  ]
}
```

A class-of-bug fix is identified structurally: if the same pattern
appears in more than one file, it is a class. This is not a judgment
call. The definition is: N >= 2 files with the same pattern = class.
See #338.

Positive verification ("these N instances are fixed") is necessary
but not sufficient. Negative verification ("zero remaining instances,
verified by grep") is required. The distinction: positive verification
confirms what you did; negative verification confirms what's left.

### Writing robust claims: grep for the invariant, not the mechanism

Claims must grep for the **invariant** (the condition that must hold)
rather than the **mechanism** (the specific implementation chosen).
A claim tied to a mechanism breaks when the implementation changes
even though the invariant still holds.

**Brittle claim** (greps for the mechanism):
```json
{
  "assertion": "base_template.py has _require_reportlab guard",
  "file": "siege_utilities/reporting/templates/base_template.py",
  "grep": "_require_reportlab",
  "expected": true
}
```
This fails if the guard is an inline `if not REPORTLAB_AVAILABLE: raise`
instead of a named function: the invariant holds but the claim breaks.

**Robust claim** (greps for the invariant):
```json
{
  "assertion": "base_template.py guards against missing reportlab",
  "file": "siege_utilities/reporting/templates/base_template.py",
  "grep": "REPORTLAB_AVAILABLE",
  "expected": true
}
```
This verifies the condition that must hold regardless of whether the
guard is a function call, an inline check, or a decorator.

**The test:** if the developer chose a different implementation that
satisfies the same requirement, would this claim still pass? If the
answer is "only if they used my exact function name," the claim is
brittle. Grep for the flag, the condition, the import, or the error
string: not the wrapper function or class name you expect to find.

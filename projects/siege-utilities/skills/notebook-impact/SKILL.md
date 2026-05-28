---
name: "Notebook Impact Check (siege-utilities)"
description: "Checks whether library changes affect notebooks. Enforces the notebook coverage invariant (SU-4)."
globs: ["siege_utilities/**/*.py"]
---

# Notebook Impact Check — siege-utilities

When a library function's contract changes, this skill checks whether any notebook in the repository calls that function and whether the notebook needs updating.

## When to run

Run this skill on every PR that changes:
- A function signature (new/removed/renamed parameters, changed defaults)
- A return type or return shape
- Exception behavior (new exceptions raised, old exceptions removed)
- Import paths (module renamed, function moved)
- A function's existence (added or removed)

## Procedure

### Step 1: Identify changed functions

From the diff, list every function whose public contract changed. A contract change is:
- Parameter added, removed, renamed, or retyped
- Default value changed
- Return type changed
- New exception raised or old exception no longer raised
- Function renamed, moved, or deleted

Internal-only changes (implementation detail, private helper, logging) are not contract changes.

### Step 2: Search notebooks

For each changed function, search the `notebooks/` directory:

```bash
grep -rl "function_name" notebooks/ --include="*.ipynb"
```

Also search for the module path:
```bash
grep -rl "from siege_utilities.module import" notebooks/ --include="*.ipynb"
grep -rl "siege_utilities.module.function_name" notebooks/ --include="*.ipynb"
```

### Step 3: Classify impact

For each (function, notebook) pair found:

| Situation | Action |
|---|---|
| Notebook calls the function with the old signature | **Update required** — notebook will break or produce wrong results |
| Notebook catches an exception the function no longer raises | **Update required** — dead exception handler misleads readers |
| Notebook demonstrates a capability that was removed | **Update required** — notebook is now misleading documentation |
| Notebook imports the module but doesn't call the changed function | **No action** — but note for awareness |

### Step 4: Check for coverage gaps

For each changed function NOT found in any notebook:

- If the function is part of the public API → note as a **coverage gap**
- If the function is internal/private → no action needed
- If the function is new → recommend whether a notebook should demonstrate it

### Step 5: Report

Output a table:

| Function | Contract change | Notebooks affected | Action needed |
|---|---|---|---|
| `module.func_name` | Added `timeout` param | `notebooks/demo.ipynb` | Update call site |
| `module.other_func` | Now raises ValueError | *(none)* | Coverage gap — no notebook exercises this function |

## What "update the notebook" means

The notebook update must:
1. Use the new calling convention
2. Actually run successfully (not just syntactically correct)
3. Demonstrate the new behavior if the change adds a capability

If the notebook update is non-trivial, file a ticket instead of blocking the library PR. The ticket must reference the library PR and the specific contract change.

## Edge cases

- **Notebook only uses the function in a markdown cell** (documentation, not code) → still flag if the documentation is now wrong
- **Notebook is marked as deprecated or archived** → note but don't block on updating it
- **Function is only used transitively** (notebook calls A, A calls changed function B) → not a direct notebook impact, but note if the transitive change affects notebook output

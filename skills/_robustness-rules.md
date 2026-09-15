---
description: Always-on robustness standards from Robust Python (Viafore). Apply when writing or reviewing Python code that must survive unexpected input, evolving requirements, or team turnover.
---

# Robust Python Standards

Apply these principles from *Robust Python* (Patrick Viafore) to all Python code.

## Type safety as communication

- Type annotations are for humans first, tools second. Annotate to make intent visible, not to satisfy a linter.
- Use `Union` types and `Literal` only when the domain genuinely has multiple valid shapes. If you're reaching for `Union[str, int, None]`, the interface is probably too loose.
- Prefer `Protocol` over inheritance when the contract is "has these methods," not "is a kind of."

## Exhaustive handling

- When branching on an enum or literal type, handle every member. Use `assert_never()` (Python 3.11+) or an explicit `raise` in the default branch to catch drift.
- Never silently ignore a new variant. If a Census geography type or overlay kind is added, code that dispatches on it must fail visibly until updated.

## Invariant enforcement

- State invariants at construction time. A `DataConfig` that requires `host` and `port` should reject missing fields in `__init__`, not at first use.
- Use `@dataclass(frozen=True)` or `__post_init__` validation for value objects. If a GEOID must be 2-15 digits, enforce it at creation.
- Prefer failing fast over defensive fallbacks. A function that receives an unexpected CRS should raise, not silently reproject.

## Constraining mutability

- Default to immutable. Use `tuple` over `list`, `frozenset` over `set`, `MappingProxyType` over `dict` when the collection should not change after construction.
- If a function accepts a mutable collection and doesn't intend to modify it, annotate it as `Sequence` or `Mapping`, not `list` or `dict`.

## Making illegitimate states unrepresentable

- Use the type system to eliminate invalid combinations. If a geocoding result can be "matched" (with coordinates) or "unmatched" (without), use two distinct types, not one type with optional fields.
- Avoid `Optional` fields that are "always set after initialization." If the field is always set, make construction require it.


---

## Attribution

Principles distilled from *Robust Python* by Patrick Viafore (O'Reilly, 2022). No code reproduced.

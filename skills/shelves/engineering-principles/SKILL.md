---
name: shelf-engineering-principles
description: Router for engineering-principles book skills. Dispatches to clean-code, clean-architecture, design-patterns, domain-driven-design, refactoring-patterns, pragmatic-programmer, or software-design-philosophy based on task signals. Read this when the task involves code quality, design, refactoring, architecture rationale, or principles arguments — it will tell you which book to read in full.
disable-model-invocation: false
---

# Engineering Principles — Shelf

Books on writing and structuring code well. Load the book that matches your task signal and read its full `SKILL.md` plus relevant `references/` files.

## Trigger table

| Task signal | Book to read |
|---|---|
| Naming, function size, comment discipline, code-smell vocabulary, "is this readable?" | [skill:clean-code] |
| Service / module boundary, dependency direction, hexagonal/onion, plugin architecture | [skill:clean-architecture] |
| GoF pattern selection — Factory, Strategy, Observer, Decorator, Adapter, Visitor, etc. | [skill:design-patterns] |
| Modeling a problem domain, aggregates, bounded contexts, ubiquitous language, event storming | [skill:domain-driven-design] |
| "How do I refactor this safely?", named refactoring catalog (Extract Method, Move Field, Replace Conditional with Polymorphism) | [skill:refactoring-patterns] |
| Career-craft principles, DRY, orthogonality, broken-window theory, tracer bullets | [skill:pragmatic-programmer] |
| Module depth, complexity as cost, design for change, "is this too shallow?", red flags from Ousterhout | [skill:software-design-philosophy] |

## Books in this shelf

- [skill:clean-code] — Robert C. Martin. Naming, small functions, error handling, comment discipline, the Boy Scout Rule.
- [skill:clean-architecture] — Robert C. Martin. The Dependency Rule, layered/hexagonal architecture, screaming architecture.
- [skill:design-patterns] — *Head First Design Patterns* (Freeman & Robson). 23 GoF patterns with use-cases and counter-indications.
- [skill:domain-driven-design] — Eric Evans. Aggregates, bounded contexts, strategic design, event storming.
- [skill:refactoring-patterns] — Martin Fowler. Catalog of refactorings with mechanics and code smells.
- [skill:pragmatic-programmer] — Hunt & Thomas. Career-spanning craft principles.
- [skill:software-design-philosophy] — John Ousterhout. *A Philosophy of Software Design* — complexity as the central problem.

## Disambiguation

- **Clean Code vs. Refactoring Patterns:** Clean Code tells you *what* good code looks like. Refactoring Patterns tells you the *named transformation* to get there safely. Use Clean Code for review rationale, Refactoring Patterns when actually changing code.
- **Clean Architecture vs. DDD:** Clean Architecture is about dependency direction across layers. DDD is about modeling the business problem. They compose; load both for greenfield service design.
- **Design Patterns vs. Software Design Philosophy:** GoF gives you named solutions to recurring problems. Ousterhout gives you the meta-rule (minimize complexity) — sometimes the answer is "no pattern, just a deeper module."

## Always-on companions

These are loaded by the resolver as `_*-rules.md` always-on files, not via this shelf:

- `_principles-rules.md` — short version of clean-code maxims, applies to every code task.
- `_python-rules.md`, `_jvm-rules.md`, `_typescript-rules.md`, `_rust-rules.md` — language idiom rules, applied when files of that language are touched.

## Source attribution

Books in this shelf are imported verbatim from upstream MIT-licensed skill libraries. See per-book `SKILL.md` footers and the repo-root [`THIRD_PARTY_NOTICES.md`](../../../THIRD_PARTY_NOTICES.md) for commit pins and copyright.

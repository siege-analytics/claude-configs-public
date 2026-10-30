# Pre-mortem: reader and protected Git safety

Ticket: #1122
Goal source: #1122
Plan reference: plans/read-and-protected-git-safety.md
Severity: 80
Implementation may proceed: YES

- Tiger: normalization checks the caller's branch rather than the actual -C target. Resolve repeated directories in one shared boundary, and test protected targets from another cwd.
- Tiger: alias inspection executes an alias. Only read configuration; reject shell/dynamic/recursive aliases; prove a sentinel remains absent.
- Tiger: a valid task becomes a waiver for a protected operation. Run operation guards with complete task artifacts and compare actual refs before/after.
- Tiger: a global Authorized trailer from another repository lends permission. Read the trailer at each resolved operation target.
- Tiger: output abbreviations introduce another cp bypass. Match the option class using the shared prefix helper; exercise real GNU outcomes for suffix and target-directory forms.
- Tiger: reader hardening blocks routine investigation. Keep base64 decoding to stdout, reflog inspection, pure filter pipelines and isolated AST/JSON reads as explicit positives; require scoped runner authority for executable tests.
- Elephant: policy fixtures pass but actual host delivery is unknown. Keep local proof separate from backend canaries and native registration.
- Paper tiger: a shared parser requires a general shell interpreter. Reuse the existing literal shell token boundary and emit unresolved instead of implementing arbitrary expansion.

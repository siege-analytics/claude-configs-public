# Hostile review: epic #962 remediation

Initial independent verdicts at `4c17aaaf72ef9a5c337bf93ccde50e4323d8effe`: **CHANGES_REQUIRED**.

Reviewers independently established:

- arbitrary `CLAUDE_KERNEL_PATH` content and mixed global mounts;
- project-scope bypass for explicit project slugs and shelf bypass in `project.always`;
- Tier B kernel/control surfaces and lossy Git pathname parsing;
- reusable lifecycle approvals;
- missing deployed selector/manifest;
- unbounded explicit selected sets;
- lost collaboration timing semantics;
- stale Craft mount documentation and metrics wording.

## Remediation mapping

- Kernel content/path and mixed-mount rejection: #986.
- Exact project scope and `project.always` shelf validation: #983.
- Review path/control-surface floors: #987.
- Exact lifecycle approval gaps: #985.
- Selected content limits and metrics: #984.
- Deployment parity: progressive mount fixture under epic #962.
- Coordination cadence restoration: #972 finding thread.

## Residual hostile questions

- Does any packaged form omit size metadata? Fresh package build and deployment fixture must prove source/package parity.
- Can over-budget selection partially leak `load:` lines? Hook fixture requires zero load lines.
- Can an operator mount broad policy using pasted bytes or an alias not containing `RULES_BUNDLE`? Exact-content allowlisting across CLAUDE.md and AGENTS.md closes this class; arbitrary non-kernel operator prose intentionally fails verification.
- Can non-UTF-8 Git names evade regex classification? Surrogateescape preserves bytes; high-risk directory prefixes remain ASCII and anchored.
- Can exact approval sets become stale after remediation? Any changed current set fails until a new explicit approval record is supplied.

No reviewer has accepted the remediation yet. Targeted exact-SHA re-review is required after commit and hosted checks.

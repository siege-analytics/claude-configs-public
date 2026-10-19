---
ticket_refs:
  - siege-analytics/claude-configs-public#1046: findings and dispositions summarized in the draft PR
---

# Hostile review: #1046 real-YAML frontmatter validation

Reviewer: an adversarial pass the implementer commissioned over the uncommitted v1 diff, using an isolated read-only reviewer that ran its probes on a `/tmp` copy. It is **not** the independent, different-family, exact-SHA review that #1046 requires. That review runs separately against the pushed head, and no verdict from it is implied here.

## Checked and found not defective

- **Missing PyYAML fails closed** in `build.py` (both build and `--check`), `skill-inventory.py`, `compose-project.py`, the CLI (exit 2), and the API. Probed under system Python 3.9 without PyYAML.
- **Rejected inputs:** BOM, CRLF, unclosed block, empty block, and a trailing-space closing delimiter.
- **Duplicate keys** are rejected in nested mappings and across quoted/plain, `true`/`True`, `1`/`1.0`, and `~`/`null` forms. Unhashable keys produce a clean error, and error line numbers are correct.
- **The lint compares real resolver tags**, so `yes`, `08`, `1_000`, `1:20`, `0o17`, `1e3`, and timestamps are all caught.
- **Python 3.9:** every touched module parses. Inventory `--check` and build `--check` pass with pure-Python PyYAML.
- **Discovery coverage:** the build validates every packaged path (routers, shelves, nested project skills), and the `--selection` path is validated through `compose-project`.
- **Registry changes:** the `SCAFFOLD_FILES`, `CORE_FILES`, and package-generation dependency additions are required, because `build.py` imports the validator. The CI install step covers both jobs that run the gates.

## Findings and dispositions

1. **MEDIUM (fail-open):** a rule whose opening delimiter is a near miss (`--- `, or `---` after blank lines) was treated as having no frontmatter. **Fixed.** `split_frontmatter` now rejects a near-miss first delimiter for every kind. Covered by unit cases for both skills and rules.
2. **MEDIUM (fail-open):** `skill-inventory.make_item` validated text from `read_text()`, which turns undecodable files into `""`, so an undecodable rule passed. **Fixed.** The inventory now calls `validate_file` (strict UTF-8 read), and an inventory fixture covers it.
3. **MEDIUM (catalog truth):** catalog `name`/`description` come from the hand parser, so valid YAML forms (flow mapping, explicit key, anchors, multi-line plain, `|+`) could be recorded differently from what was validated. **Fixed without changing catalog values.** The inventory now refuses any header whose hand-parsed `name`/`description` differ from the YAML values. Inventory fixtures cover flow, explicit-key, multi-line plain, and `|+` headers. Catalog `name`/`description` are identical to base for all 198 items.
4. **MEDIUM (coverage):** `skills/KERNEL.md`, `RULES.md`, and `_coverage.md` are packaged support files that Phase 3b does not validate. `KERNEL.md` has an unquoted `last-reviewed` date. **Not in the approved D2 corpus.** It has been escalated to the coordinator as a scope decision, and the default is deferral to a follow-up ticket.
5. **LOW (deploy transforms):** `inject_project_frontmatter` writes the project slug unquoted, and `strip_craft_incompatible_keys` removes single lines, so the transformed output is not re-validated. **Deferred.** No current project slug or key shape triggers either problem: the dist sweep over all 796 generated skill and rule files in 4 layouts reports 0 failures.
6. **LOW (lint gaps):** `!!set`, `!!omap`, merge keys, and anchors passed. **Fixed.** Anchors, aliases, explicit tags, and merge keys are now rejected, with unit cases.
7. **LOW:** the exact version pin is enforced only by the `install.sh`/`sync-workspace-hooks.sh` preflights and CI. The gates accept any PyYAML. **Accepted.** CI and installs pin 6.0.3. I tested only 6.0.3 (on CPython 3.9, 3.12, and 3.14). I assume other versions resolve tags the same way, but that is untested inference.
8. **LOW (tests):** coverage was missing for the cases above, for "no output before rejection", and for byte-level wording equality of the committed files. **Fixed.** `gate_cases` now asserts that no `dist` exists after a rejected build, and `committed_content_cases` checks that each committed header differs from the v3.5.66 header only by the added quotes, with parsed value equal to the original raw text.

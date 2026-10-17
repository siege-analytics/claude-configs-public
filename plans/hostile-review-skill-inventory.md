# Hostile review: Phase 0 skill inventory

Three independent adversarial passes reviewed the reporting-only inventory generator, fixtures, CI check, and observed catalog summary.

## Findings and resolutions

| Severity | Finding | Resolution |
|---|---|---|
| S1 | Generated catalog could supply its own inbound-reference evidence after being tracked. | Configured catalog outputs are always excluded from evidence scanning; fixture tracks outputs and proves no self-reference. |
| S1 | CI freshness check would fail if generated outputs were omitted. | Both JSON and Markdown generated outputs are included in this PR and checked locally before commit. |
| S2 | Skill and rule items with the same slug could collapse in evidence maps. | Separate skill and rule namespaces are used; fixture covers same-slug skill/rule references. |
| S2 | Duplicate shelf/project slugs could silently collapse. | Each namespace has explicit uniqueness validation; duplicate shelf-book fixture fails. |
| S2 | Reserved `--` skills and nested rule files were silently omitted. | Discovery is checked against `build.py`; intentionally unsupported sources are listed under `ignored_sources` with reasons. |
| S2 | Project-rule generated destinations were incorrect. | All effective destinations are derived from `build.py` mappings; project-rule fixture asserts both layouts. |
| S2 | `--root` retained output defaults from the script repository. | Defaults are repository-relative and tested with a temporary root. |
| S2 | Catalog discovery could diverge from authoritative build inputs. | Source-path equality with `build.py` is mandatory; current parity is 198/198. |
| S2 | Archived/retired project overlays could be treated as active or break parity. | Only active projects enter the catalog/output plan; excluded project sources remain visible in diagnostics. |
| S2 | Two sources could claim one generated destination while still being marked verified. | Explicit destination-collision validation runs before outputs receive `generated_outputs_verified: true`; negative fixture included. |

## Verdict

No unresolved S1 or S2 findings remain. The catalog is evidence, not a retirement oracle: unknown owner/lifecycle/use fields remain unknown, missing tracked references are explicitly not equated with runtime non-use, and quality grades reproduce the existing rubric rather than introducing a new one.

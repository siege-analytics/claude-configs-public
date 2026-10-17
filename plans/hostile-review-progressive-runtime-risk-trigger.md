# Hostile review: progressive runtime risk trigger

## Attack

Attempt to change each progressive-loading control surface while declaring Tier B:

- `catalog/resolver-manifest.json`
- `bin/resolve-load-set.py`
- `hooks/resolver/inject-resolver.sh`

## Result

All now compute Tier C. The fix covers data, selection code, and injection code. Changing the policy to remove these entries still changes `catalog/review-risk-policy.json`, protected by the independent bootstrap floor. No routing or runtime load-set behavior changes.

## Verdict

No unresolved S1/S2 finding for this trigger gap. Merge remains conditional on complete checks.

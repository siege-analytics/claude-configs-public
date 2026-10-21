# Siege flat package

Flat skill layout.

Source revision: `bcbb013f5edd42c92b156b8bae9c8bbb81e7be0e`. Consumer tag: `vX.Y.Z-flat`.
Use the release manifest and its exact archive digest to select a version.

## Included files

- [build-info.json](build-info.json)
- [skills/KERNEL.md](skills/KERNEL.md)
- [catalog/resolver-manifest.json](catalog/resolver-manifest.json)
- [catalog/review-risk-policy.json](catalog/review-risk-policy.json)
- [bin/resolve-load-set.py](bin/resolve-load-set.py)
- [bin/review-risk.py](bin/review-risk.py)
- [hooks/settings-snippet.json](hooks/settings-snippet.json)
- [hooks/resolver/inject-resolver.sh](hooks/resolver/inject-resolver.sh)
- [CHANGELOG.md](CHANGELOG.md)
- [LICENSE](LICENSE)
- [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)

The skill tree and resolver catalog form one unit. Keep the package directory
structure intact when extracting or copying it to a new consumer location.
Each resolver result reports the actual package-relative load path.

## Package-local diagnostics

From this package root, with Python 3, run these read-only diagnostics:

```sh
python3 bin/resolve-load-set.py --prompt "review this Python diff" --repo other/repo
python3 bin/review-risk.py --paths README.md
```

The first command reports selected content; the second classifies a sample
path. Neither command grants permission or proves host hook registration.

## Integration boundary

The runtime prompt hook reads `skills/KERNEL.md` and loads selected skills
on demand. This output does not ship root `RESOLVER.md` or
`RULES_BUNDLE.*`, and does not require them for that prompt path.
Do not mount a global compatibility bundle alongside the compact kernel.

Hook snippets are unregistered configuration with path placeholders.
Extracting this archive does not install an enforcement stack. The source
installer, wiring tools, drift tooling and generation-management tools
are not part of this package. Use the separately reviewed source workflow
for host-specific registration and upgrade; preserve existing operator
settings and project declarations there. Never replace a live workspace
with an unchecked copy of a new archive.

The presence of a hook, manifest, procedure or model label establishes
no live capability. Verify the exact host/backend, registered path and
allowed/denied behavior before calling enforcement live. A required
unsupported capability remains a failed acceptance condition.

[Source integration and development documentation](https://github.com/siege-analytics/claude-configs-public/tree/bcbb013f5edd42c92b156b8bae9c8bbb81e7be0e/README.md).
[Report or review changes in the source repository](https://github.com/siege-analytics/claude-configs-public/tree/bcbb013f5edd42c92b156b8bae9c8bbb81e7be0e/CONTRIBUTING.md).

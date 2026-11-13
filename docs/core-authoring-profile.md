# Stable Core authoring hooks

Stage A ships the inert `.claude/settings.authoring.json` template and enrollment
API. Active `.claude/settings.json` retains the existing relative profile. This
keeps develop-derived worktrees usable while the API reaches released Main.
Install verified policy before Stage B activates the prepared profile.
Missing enrollment or bootstrap execution failure blocks with exit2. Candidate
guard files are never a failure-time fallback.

Use a clean checkout of the reviewed, released Main containing this installer.
The installer verifies actual remote Main and immutable tracked bytes, resolves
the already adopted `github.com/siege-analytics/claude-configs-public`
`strict-release` policy, and uses the existing canonical compatibility exporter.
It retains all four source hook events, including failure callbacks omitted from
the ordinary Claude Code consumer snippet. It does not compose another skill
corpus or accept project-supplied policy, command or identity selectors.

Prepare a physical versioned package parent outside the authoring repository.
For the actual authoring primary repository and host home, run:

```sh
python3 -B "$MAIN_SOURCE/bin/core-authoring-profile.py" install \
  --repo "$ACTUAL_PRIMARY_REPOSITORY" \
  --package "$EXTERNAL_PACKAGE_PARENT/$VERIFIED_MAIN_SHA" \
  --home "$ACTUAL_HOST_HOME"
```

`MAIN_SOURCE` and `VERIFIED_MAIN_SHA` must identify the verified released Main,
not a feature checkout. Use the qualified host Python at enrollment. After the independent package
hash, the bootstrap selects that enrolled interpreter when SDK Python differs,
and qualifies child Python only for that callback. Global PATH stays unchanged. The source revision must already exist in
the authoring repository's Git object store. Install from its actual primary
repository once; Git-listed linked worktrees reuse that common-directory anchor.
Core forks and local remotes are supported through shared Core history and
canonical root identity/layout at target HEAD. Fetching Core objects or importing
Core under a vendor prefix does not adopt Core authoring policy. Candidate
working-file edits do not select that identity. An existing package must match the deterministic Main export exactly. Use a new
versioned path for an upgrade.

For qualified headless Linux Craft, run the same command with that host's actual
primary repository, physical home and external package, and add
`--workspace "$VERIFIED_POLICY_WORKSPACE"`. The workspace must be physical and
outside the authoring repository. It receives its own anchor; native CLI and
other workspace enrollments remain usable. Environment values alone do not
authenticate Craft: dispatch also requires the qualified Bun/server ancestry and
the existing strict SDK UUID, session header and physical witness.

Repeat the identical arguments with the `verify` action to check the existing
externally pinned generation without rebuilding, upgrading or writing settings.
A newer Main alone does not invalidate a healthy enrolled generation. Install
and upgrade still require clean exact Main; desired release rollout is separate
from existing-generation health. `enrollment_ready` describes the external
anchor. `project_profile_files` reports file state; `sdk_profile_active` and
`host_invocation` remain unobserved until a real callback proves them. Installation publishes
`HOME/.claude/hooks/siege-project-bootstrap.py` and an external profile anchor.
A per-home common-ABI integrity receipt verifies shared helper bytes without
pinning every workspace to the same Main revision. Publication uses bounded
serialization and snapshot comparisons; health reads do not rewrite state.
It preserves global CLI settings, project/operator hooks, local Git config and
`core.hooksPath`. Audit data is separate from immutable policy code. Existing
selected consumers keep their existing installer and registration contracts;
they are not required to enroll this authoring profile.

After successful enrollment on each authoring host, use a normal Stage B PR to
activate the exact prepared template. That PR changes the tracked active profile
and its phase-specific regression assertion. Preserve unrelated project/operator
hooks; inspect SDK project/local settings for remaining managed mutable vectors
before claiming the repair is active. Stage A does not activate SDK hooks. The
legacy relative installer retains its existing behavior until the prepared
profile is active, then preserves stable dispatch during reinstall. Existing Mac
Craft workspace/router registration remains separate; upgrade its actual
installed workspace policy through the normal qualified Main rollout. The
project profile alone does not replace an old global workspace policy, and the
API does not register native Git hooks or add a Craft session binding to global
CLI settings. Observe the actual callback path before attributing a refusal to
SDK or native enforcement.

Deployment acceptance still requires a real callback canary: observe the loaded
profile and source paths, an owned repair while candidate guard modules are
malformed, foreign-owner/target/lifecycle refusals, independent owned
continuation, linked-worktree CLI publication and operator deny preservation.
Controlled fixtures are not deployed acceptance. The headless ancestry fixture
and deployed SDK default-source contract do not establish actual SDK project
discovery outside its workspace; observe that path in the canary. No provider
settings-source suppression or runtime restoration is part of this change.

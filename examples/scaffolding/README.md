# Effective-policy resolver pilot

The #848 pilot resolves the three typed fields declared by `catalog/gate-contracts.json` from one approved source, `catalog/effective-policy.json`.

## Precedence and authority

1. Parent defaults come directly from the sealed gate contract.
2. A declared organization profile may change only `organization_profile_paths`.
3. The exact matched project may change only `project_paths`.
4. `locked_paths` cannot be changed by either layer.

Repository selection requires exact canonical `host/owner/repository` data. Missing, foreign, or disagreeing identity remains `unknown`/`ambiguous`; basename and ambient current-directory guesses are not inputs to the pure evaluator.

Capability states, installation metadata, task evidence, and candidate working-tree policy are separate inputs. They appear in `explain`, but cannot change precedence or authorize themselves. Even caller-supplied `verified` capability states leave final enforcement `unknown` in this configured-only slice; #1002/#1003 must provide a trusted protected adapter. Generated manifest metadata is explicitly `configured`, never proof of live or protected enforcement.

## Commands

Validate source and generated agreement:

```bash
python3 bin/effective_policy.py validate --generated-root dist
```

Explain `feature -> main` for the strict profile (policy denial):

```bash
python3 bin/effective_policy.py explain \
  --identity github.example.invalid/synthetic-org/strict-release \
  --operation examples/scaffolding/feature-to-main-operation.json \
  --capability native-branch-pre-push=verified \
  --capability protected-range-validation=verified
```

Explain the same operation for the synthetic trunk profile (policy decision `allow`; final enforcement remains `unknown` until trusted adapter proof):

```bash
python3 bin/effective_policy.py explain \
  --identity github.example.invalid/synthetic-org/synthetic-trunk \
  --operation examples/scaffolding/feature-to-main-operation.json \
  --capability native-branch-pre-push=verified \
  --capability protected-range-validation=verified
```

Use `check` instead of `explain` for process semantics: final allow would exit 0, deny/unknown exits 1, and malformed/error exits 2. #848 deliberately cannot produce final allow because it has no trusted protected/live adapter; a caller cannot obtain exit 0 merely by passing `verified`. `explain` always exits 0 for a well-formed explanation, including policy denial.

## Migration from existing workspaces

1. Record the consumer's exact canonical remote identity. Do not migrate basename-only or live-tip guesses.
2. Select a reviewed organization profile or add one in a separately reviewed policy revision.
3. Translate only fields explicitly permitted by the gate contract. Existing copied hooks, resident overlays, environment flags, and task artifacts are not project-policy layers.
4. Compare the candidate catalog with `--candidate`. The resolver reports its proposed digest and path changes while continuing to decide under the approved catalog.
5. Integrate instructions and guards with the same resolver output in #1002. Until that acceptance exists, this pilot is configuration-valid/configured evidence only.
6. Preserve pinned compatibility exceptions until #1002/#1003 prove equivalent protected and live behavior; retire copies only under #1004 rollback evidence and #849 parity measurement.

Resident workflow text is generated from the same resolved values and returned as `resident_workflow`. The common kernel's current strict topology remains in place until #1002 consumes this output at an actual enforcement boundary; #848 does not weaken or deploy runtime policy.

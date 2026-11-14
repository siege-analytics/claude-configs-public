---
name: claude-configs-public
repo: siege-analytics/claude-configs-public
description: Shared agent instructions, policy tooling, exporters and installers.
---

# Claude configs

This repository owns the shared configuration source and generated distributions.
Descriptors under `projects/` describe consumers; they do not set this repository's testing policy.

## Testing

```yaml
testing:
  layers:
    - name: policy-and-tooling
      framework: unittest
      test_dir: bin/_test/
      source: ["bin/**", "hooks/**"]
    - name: hook-behavior
      framework: shell
      test_dir: hooks/_test/
      source: ["hooks/**"]
```

Run the maintained suites affected by the source change and the required build and freshness checks.
Record genuine test evidence using the documented native or bound-task producer route.
The required hosted pipeline verifies the complete composition before acceptance.

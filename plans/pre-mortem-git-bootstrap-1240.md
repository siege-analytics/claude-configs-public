---
propagation-deferred: true
---
# Pre-mortem: Git bootstrap targets (#1240)

Tiger / Severity: 80 — A destination/model mistake could let init or clone write outside its task. Restrict explicit clone destinations, existing parent and physical destination identity; reject alternate metadata/templates/config/helpers, reinit and unmodeled transports. Verify actual hook-denied negatives and no created target.

Tiger / Severity: 70 — A new nested repository could keep borrowing enclosing workspace identity. Test initial scoped creation and the subsequent real index mutation; reject the stale enclosing-root gate until the same own task/artifacts reflect the new repository.

Tiger / Severity: 60 — Treating an absent repository as trivial might bypass review preparation. Keep the existing effective-risk classifier and C fallback for an unknown new tree; lower declarations cannot win. Test missing artifacts and foreign/incorrect tasks.

Elephant / Severity: 40 — A parser-only pass could hide another configured PreToolUse denial. Use actual native-shaped payloads through all configured Bash guards, then execute Git only after acceptance. Protected CI is still required; no live hook delivery is claimed.

Rollback: revert this source feature through normal review. No live state, installed hook, session gate or global setting is changed here. Concurrent copy/bundle work remains a separate owned source region.

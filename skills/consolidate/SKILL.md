---
name: consolidate
description: Find and consolidate redundant documentation. Identifies duplicates, moves canonical content to docs/, replaces copies with links.
disable-model-invocation: true
allowed-tools: Read Grep Glob Bash Edit Write
---

# Consolidate Skill

## Purpose

Reduce documentation redundancy across repositories by:
- Centralizing core concepts in `docs/`
- Replacing duplicate content with cross-references
- Maintaining detailed, repo-specific material in each repository

## Instructions

### 1. Gather Recent Markdown Changes

Scan the last 10 commits touching markdown files across all project repositories:

```bash
cd ~/git/electinfo
for repo in */; do
  if [ -d "$repo/.git" ]; then
    echo "=== $repo ==="
    git -C "$repo" log --oneline -10 --all -- '*.md' 2>/dev/null
  fi
done
```

For each commit, examine the changed content:

```bash
git -C <repo> show <commit>:path/to/file.md
git -C <repo> diff <commit>~1..<commit> -- '*.md'
```

### 2. Identify Redundant Content

Look for:
- **Duplicate paragraphs**: Same or near-identical text in multiple files
- **Repeated configuration snippets**: Vault paths, kubectl commands, service URLs
- **Overlapping concept explanations**: Architecture, naming conventions, common patterns
- **Copy-pasted tables**: Node specs, service ports, credential references

Flag content as redundant if it appears in 2+ locations with >80% similarity.

### 3. Determine Canonical Location

Apply these rules to decide where content belongs:

| Content Type | Canonical Location |
|-------------|-------------------|
| Cluster architecture, node specs | `docs/` |
| Service naming conventions | `docs/` |
| Shared credentials/Vault paths | `docs/` |
| Cross-service integration patterns | `docs/` |
| Repo-specific implementation details | That repo's `CLAUDE.md` or `README.md` |
| Runbook/operational procedures | `rundeck/` or `docs/` depending on scope |

**If non-obvious, ask the user:**
- "This content about X appears in both A and B. Which should be the canonical source?"
- Present the conflicting snippets for review

### 4. Consolidate Content

For each redundancy:

1. **Move to canonical location** (if not already there):
   - Copy the most complete/accurate version to the proper file
   - Ensure proper markdown structure and context

2. **Replace duplicates with links**:
   ```markdown
   <!-- Before -->
   The cluster runs on 5 nodes: cyberpower, aegis-blue, aegis-red...
   [full node table repeated]

   <!-- After -->
   See [Cluster Nodes](../docs/index.md#cluster-nodes) for node specifications.
   ```

3. **Add context where needed**:
   - Brief summary before the link if helpful
   - Repo-specific notes that don't belong in docs/

### 5. Update docs/ as Central Reference

Ensure `docs/` contains:
- **Core concepts**: Architecture decisions, design patterns
- **Infrastructure details**: Node specs, networking, storage
- **Service catalog**: Complete list with links to detailed docs
- **Common procedures**: Shared across multiple repos

Add liberal cross-references from `docs/` into repo-specific material:

```markdown
## Spark Deployment

For detailed Spark cluster configuration, see:
- [ops/app-spark/](https://github.com/electinfo/ops/tree/main/app-spark) - Kubernetes manifests
- [zeppelin/CLAUDE.md](../zeppelin/CLAUDE.md) - Spark interpreter configuration
```

### 6. Verify and Report

After consolidation:
- Run a final grep to confirm no redundant blocks remain
- List all files modified
- Summarize changes made

## Checklist

- [ ] Scanned last 10 commits across all repos
- [ ] Identified redundant content snippets
- [ ] Determined canonical location for each (asked user if unclear)
- [ ] Updated canonical source with complete content
- [ ] Replaced duplicates with cross-reference links
- [ ] Added docs/ references into detailed repo material
- [ ] Verified no redundancy remains

## Attribution policy

**NEVER** include AI or agent attribution in consolidated documentation, commits, or any content produced. No "Generated with Claude Code", "Made with Cursor", "Built with Codex", Co-Authored-By lines referencing AI tools, or any other AI/agent markers.

## Notes

- Prefer relative links (`../docs/`) over absolute URLs when possible
- Keep repo-specific `CLAUDE.md` files focused on that repo's concerns
- The `docs/` repo should be readable standalone as an architecture guide
- Don't consolidate content that is intentionally duplicated for discoverability (e.g., quick-reference tables)
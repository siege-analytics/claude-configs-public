# Untracked workspace hygiene

Ref: claude-configs-public#617

## Rule

Do not use broad `git clean -fd` in this repository by default. The working tree can contain operator-created scratch artifacts, copied skill trees, and stale generated outputs. Treat untracked paths as data until classified.

## Workflow

1. Run the inventory tool:

   ```bash
   python3 scripts/discipline/untracked-hygiene.py
   ```

2. Review categories:

   - `IDE local config`, `python cache`, `stale generated output`: local/generated. These are ignored by `.gitignore`.
   - `number-suffixed duplicate/copy`: likely accidental copies such as `file 2.md`, but still require explicit review before deletion.
   - `plan artifact`, `skill/rule tree`, `hook artifact`, `other`: ambiguous. Decide whether each is intentional work, local scratch, or disposable.

3. For duplicate/copy paths only, generate a dry-run deletion template:

   ```bash
   python3 scripts/discipline/untracked-hygiene.py --emit-delete-script
   ```

   The output prefixes every removal with `echo` as a safety barrier. Remove `echo` only after reviewing the exact path list.

## Policy

- Never delete ambiguous untracked artifacts without explicit review evidence.
- Prefer adding narrow `.gitignore` entries for generated/local artifacts over hiding broad source trees.
- Do not ignore `skills/`, `hooks/`, `plans/`, `projects/`, or `scripts/` wholesale; those directories can contain real product changes.
- Commit the inventory/policy changes separately from any actual cleanup deletion.

---
ticket_refs:
  - siege-analytics/claude-configs-public#1079: read-only-command.py allowlist gaps block common verification reads
---

## Pre-Mortem
Task: prove `shasum` and write-free `git hash-object` as reads in `hooks/lib/read-only-command.py`.
Ticket: siege-analytics/claude-configs-public#1079

### Tigers

#### Tiger 1: `git hash-object` admitted with a hidden write

`-w` writes the object into the repository's object store. Mitigation:
- `hash_object_writes()` rejects any abbreviation of `--write`, and any short cluster containing `w` before a `t`. `-t` takes an argument, so `-tw` sets the type to "w" and does not write, while `-wt blob` writes.
- `unsafe()` returns a veto (exit 3), so neither the legacy safelist nor a designing gate admits a write form.
- Must-block cases: `-w f`, `-wt blob f`, `--write f`, `--stdin-paths -w`, and `git -C /tmp hash-object -w f`.

#### Tiger 2: `shasum` writes

`shasum` (Perl Digest::SHA) has no option that writes a file. `-c` reads a checksum file. Its siblings `sha256sum`, `sha1sum` and `md5sum` are already plain reads.

### Launch-Blocking Assessment

None identified.

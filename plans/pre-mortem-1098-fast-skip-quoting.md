---
ticket_refs:
  - siege-analytics/claude-configs-public#1098: fast skip misses quoted, backslashed and multi-space triggers
---

## Pre-Mortem
Task: the fast skip in 13 hooks matches each trigger against both the raw command and a copy with quotes and backslashes dropped and blanks squeezed. It takes the full path for long commands, ANSI-C `$'...'`, and quotes or backslashes between alphanumerics.
Ticket: siege-analytics/claude-configs-public#1098

### Tigers

#### Tiger 1: the skip disagrees with the full guard (Severity: high)

The first version dropped quotes only, so `git commit"x"` and `x\git` glued words together and the skip missed what the full guard catches. That was a hostile-review finding.

Mitigation:
- The raw text is matched as well.
- A quote or backslash between two alphanumerics forces the full path.
- The oracle suite compares every case with the hook minus its fast skip, now in a repository every guard governs (siege-analytics origin, `.env`).

#### Tiger 2: cost (Severity: high)

Bash substitutions are superlinear under a UTF-8 locale. The first version let a 300 KB command run past the 10 s hook timeout.

Mitigation:
- Over 16 KiB the full path is taken before any substitution.
- The suite runs under `C.UTF-8` and times a 300 KB case. It now takes 0.57 s; develop takes 4.2 s.

#### Tiger 3: the skip still misses a spelling (Severity: medium)

Command substitution, variables, brace expansion, line continuations and `git -C`/`-c` prefixes are not covered. The full guards cannot see through them either, so the skip agrees with the oracle there.

#### Tiger 4: bash 3.2 (Severity: medium)

The new lines decide the same on docker `bash:3.2` and on bash 5.

### Launch-Blocking Assessment

None identified, provided the oracle suite stays green under UTF-8.

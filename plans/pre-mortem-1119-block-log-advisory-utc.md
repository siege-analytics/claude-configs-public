---
ticket_refs:
  - siege-analytics/claude-configs-public#1119: enforcement-blocks.jsonl counts prompt-time advisories as blocks, in local time
---

## Pre-Mortem
Task: write block-log timestamps in UTC with an offset, flag advisory audit records, and make block-classifier-guard skip advisories and compare times on one clock.
Ticket: siege-analytics/claude-configs-public#1119

### Tigers

#### Tiger 1: mixed naive and aware timestamps break the classifier silently (Severity: high)

Existing logs hold naive local timestamps, and new lines carry `+00:00`. Comparing a naive with an aware datetime raises `TypeError`. The old per-line `except` did not catch `TypeError`; the outer `except Exception: pass` would swallow it, and the guard would then report no blocks at all.

Mitigation:
- Naive timestamps are read as local time (`astimezone()`), and the cutoff is aware UTC.
- `TypeError` is also caught per line, so one bad line is skipped and does not hide the rest.
- The test mixes naive and aware, recent and old, advisory and real lines in one log.

#### Tiger 2: a real block is mislabelled advisory (Severity: medium)

The flag is set only when the invariant ends with the literal `(advisory)`. Only `pre-action-guard` and `branch-state-guard` write that suffix, and both are prompt-time narration. No blocking gate uses it.

#### Tiger 3: classification ids change (Severity: low)

`block_id` is `gate_id:timestamp`. New lines have a new timestamp format, so their ids differ in form, but ids are only ever compared with themselves. Existing classifications still match the existing lines.

#### Tiger 4: something else reads the log (Severity: low)

The only reader in the scaffold is `block-classifier-guard.sh`. `workaround-tally` keeps its own file. External metrics scripts gain an `advisory` field and an explicit offset, which makes them more accurate, not less.

### Rollback

Revert the commit, and also remove or rewrite the new-format lines in each workspace's `enforcement-blocks.jsonl`. Develop's classifier compares naive datetimes. On the first `+00:00` line it raises `TypeError` in its outer handler and reports nothing after that line. Code-only rollback therefore silently empties the classifier (hostile review). Example: `python3 -c` that rewrites every timestamp with `datetime.fromisoformat(t).astimezone().replace(tzinfo=None).isoformat()`.

### Launch-Blocking Assessment

None identified, provided the suites stay green and the hostile review finds no way for a real block to drop out of the classifier.

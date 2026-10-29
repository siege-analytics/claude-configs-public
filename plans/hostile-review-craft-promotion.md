# Independent review: Craft promotion follow-up

Verdict: PASS for the bounded promotion follow-up, reviewed 2026-10-29 against base `e589059eb5f88e7a7678f3be6917d746f36ffd20` and the source hashes below. No source changes, UI actions or external publication were performed by this reviewer.

## Scope and findings disposition

- `ca-enforcement-gate.sh::_ca_has_craft_ancestor` invokes `/bin/ps` directly, so the new mixed-marker recovery decision cannot be supplied by a PATH-injected ps. `/bin/ps` exists on the reviewed macOS host. Unsupported hosts still fail closed. The test first exercises production bytes with a forged PATH ps and expects a block, then substitutes only the disposable copy's process-observation boundary for deterministic ancestor cases. Production contains no override. Resolved.
- `ticket-required.sh` checks effective-message patterns using here-strings. This eliminates producer SIGPIPE under pipefail without changing the accepted patterns. Resolved.
- `commit-message-source.py::comment_prefix` reads both configured values and explicitly rejects disagreement. This conservative failure is limited to edited scissors cleanup, where a wrong delimiter could retain a ticket that Git drops. Identical values and single settings remain supported. Resolved.
- Ticket fixture exports global/system Git isolation before repository creation; repository-local configuration controls remain tested. Resolved.
- Changelog has one Unreleased heading. Previously shipped notes are preserved in an explicitly historical cumulative 3.5.73 section. Both release tools recognize that as a separate versioned section, keeping the new release body free of old entries. Resolved.

## Independent validation

- Runtime hook suite: **16 passed, zero failed**, including production-copy PATH spoof negative, three nested backend marker positives through the fixture, unrelated process, lookalike path, failed observation and child hard-stop controls.
- Full ticket hook suite: **138 passed, zero failed**. Log: `/private/tmp/promotion-review-ticket.log`.
- Independent before/after file-message experiment: six approximately 609 KB files. Base hook incorrectly blocked all four valid forms (ticket, task, structured override, URL); current hook permits all four. Bare override and missing reference still block. Evidence: `/private/tmp/promotion-review-vst3d52r/results.json`.
- Independent Git 2.54 prefix controls: conflicting settings in either config order block with the conflict diagnostic. Equal settings and each single-prefix case agree with three actual commit results, whose below-scissors ticket was removed. Evidence: `/private/tmp/promotion-prefix-review-jnugra04/results.json`.
- Release roundtrip: unique Unreleased; synthetic new version gets exactly the current Unreleased body; archived 3.5.73 body stays unchanged; Unreleased resets empty; repeat promotion is idempotent. Tested in memory, without changing the changelog.
- `git diff --check` passed.

## Boundaries and follow-ups

This verdict covers the five named promotion threads and regression changes, not a full fresh audit of the 3,501-line classifier or every backend event. The separately recorded historical audit findings remain separate work. The reported eval-variable classifier limitation predates this promotion and is not resolved here. Positive ancestry fixture checks establish decision logic, not actual Craft delivery; production UAT remains the coordinator's post-install responsibility.

## Reviewed source hashes

- `CHANGELOG.md`: `7bd6a8621894c13317be358fa6b57b757678e67409b75b528e90375c2ed53a3e`
- `hooks/resolver/ca-enforcement-gate.sh`: `4129b00b64f913a04e3f92c7cdb704b7cad9c53df6219821f923c2c85bbef8b4`
- `hooks/git/ticket-required.sh`: `faabb3ae14fde4bb9fe33969ae9e256fbcf02df0f8a16e5c0e406ccaf76d034c`
- `hooks/lib/commit-message-source.py`: `694ed5946a51ad84b66d351cf6100ecd31aedc6b70a81b3e5a7bf2e0a7bb6355`
- `hooks/_test/ca_enforcement_runtime.test.sh`: `5643fbe16be790fed37148f23adfbfd20c5edaee409cf752965139b0937020a0`
- `hooks/_test/ticket_required.test.sh`: `351f91f9e45d6e9374780d0b555f319cf3e5041da79ca79d417ecf6742401a5a`

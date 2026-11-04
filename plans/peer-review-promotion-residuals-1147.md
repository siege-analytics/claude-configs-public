# Independent promotion residual closure

Verdict: ACCEPT the six PR1147 findings at source tree61166bb541cd94ef254ee421d02ed311fce8cb80, base863abba1a6d9f01c699f8d220f16da6918141fb8. No remaining must-fix found in this bounded review. This is native independent review, not CodeRabbit or CA service approval. The original six findings were reproduced against the old source and remain historical evidence; green service status is not their closure evidence.

-4462865223 ACCEPT: a nonzero selector result now clears captured stdout before any envelope is published. Successful selectors retain prior behavior. Independent actual inline suite16PASS covers failed-selector output below budget, composed/generic limits and existing fallback contracts.
-4462865225 ACCEPT: each structured no-ticket field must have non-whitespace content after stripping. Blank fields no longer supply a ticket override; meaningful fields remain accepted. Actual marker and callback controls exercise both outcomes.
-4462865244 ACCEPT: a task marker must contain non-whitespace identifier text. Empty spaces/tabs no longer satisfy traceability, while meaningful task markers retain support. Existing other ticket formats are unchanged.
-4462865254 ACCEPT: opaque literal Git payload inspection now uses normalized prefix parsing, including global options and effective target cwd. Opaque watch with --no-pager, -c or -C cannot hide an owned ticketless commit. Proven non-commit options and foreign targets retain paired positives.
-4462865262 ACCEPT: ticket inspection accepts shell comments only through an opt-in inspection flag, preserving executed commands before comments and continuing after newlines. Parsed target scope follows Git -C; unknown target overrides cannot borrow foreign payload cwd to gain acceptance. Default shell_tokens/action authorization behavior remains unchanged and its real reader fixture asserts ordinary comments still fail unproved action parsing. Unknown owned shell groups remain conservative, not a claim that every owned grouped read is supported.
-4462865269 ACCEPT: only Bash commands receive the64KiB command-specific bound; the96KiB metadata cap remains for all tools. Independent payload suite10PASS covers the scoped size behavior and retained metadata boundaries.

Additional closure: the intermediate opaque helper missed unknown grouped aliases. Final fallback treats unresolved literal Git candidates as potentially committing under known owned scope. Independent actual-hook probes verify owned aliasci=commit denial and foreign acceptance, plus foreign grouped status/diff acceptance. Direct and opaque absolute git-commit owned denial/foreign acceptance remain preserved.

Independent executions: inline_delivery_test.py16PASS4.261s; hook_payload_test.py10PASS10.094s; reader_git_safety.py two focused methods PASS (redirect/prose/comment boundary and per-message/scope-failure controls). Retained logs: independent-inline.log, independent-payload.log, independent-reader-focused.log. The six unchanged source/test pins let earlier inline/payload executions apply to the final two-pin alias update. A separate sixteen-case actual-hook probe passed final alias, dashed Git, opaque global options, comment, spaced owned/foreign target and ticketed positive pairs. Eight working/tree SHA256 pins were checked before and after those final probes. No candidate command was executed; synthetic repositories only were used. Full author331ticket/aggregate producer remains author/coordinator evidence until its actual completion is recorded.

Falsification: changed source pins, an owned opaque/alias commit returning allow, unproved target scope granting authority, blank marker authorization, nonzero selector content publication, weakening shared default parser authorization or loss of paired foreign/read positives requires renewed review. Protected CI, final evidence-only selection, publication and live installation are separate coordinator checks. No deployment or live-host success is claimed.

{
  "base": "863abba1a6d9f01c699f8d220f16da6918141fb8",
  "source_tree": "61166bb541cd94ef254ee421d02ed311fce8cb80",
  "sources": {
    "bin/_test/hook_payload_test.py": "728bda74169212ee036774a06c8317cccf3438ba8e5b4cc13865873e45f284db",
    "bin/_test/inline_delivery_test.py": "35aad1c73eb8fe9212225c862fc31b71d22aa3f1c5ee616b5e4e01b873824bc1",
    "hooks/_test/reader_git_safety.py": "a9336efa31f7b67078ccdd68db5e31b541a28ee93bc66eec124d8c855c12f524",
    "hooks/_test/ticket_required.test.sh": "73a206a7c628019594a27f281c160b7849d415e7eb241898b836ea8867d6c87e",
    "hooks/lib/git_command.py": "73322bd1c37fd3e7ede19893db12602dc69e80fd7df17ae61a43685252eaa08a",
    "hooks/lib/hook_payload.py": "7cebe680865d03f6b77d5495b8c6b37a099948f7eb2e40f91e7982cf07d76efc",
    "hooks/lib/task_actions.py": "2951928794552a01720b9024dfab9ea7aaa312942727e1d14d40ca286c6fa92f",
    "hooks/resolver/inject-resolver.sh": "68f3def3d6a555627f1f3435ab0eb9570ff68c511b9feb079451cb5b0bcba953"
  }
}

Verified-by: independent actual inline16 and payload10 suites; reader focused two-method run; sixteen final actual-hook paired controls; eight source/tree SHA256 checks before and after probes.

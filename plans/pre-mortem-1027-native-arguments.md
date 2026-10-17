# Pre-mortem: native argument boundary correction (#1027)

Baseline: 5fc925026190fa5493c4dc7b1a96a3cc0f28746d.
Finding: PR #1032 comment 6228927453; stop: issue #1027 comment 6228931118.

The posted copied build/install/wire/verify and actual push probe was reproduced
before product edits. Exit 1 is expected red evidence: --selected rejects trunk;
--help creates release. Logs and result remain in cache/selected-registration/
argv-correction/evidence and cache/coherent-selected/evidence.

Failure predictions: argparse help bypasses binding verification; appended options
replace a binding or command; a second forwarding boundary reinterprets --selected;
arity errors reach the compatibility adapter; a message path becomes a cat option.

Use a required -- boundary for native events, with no native dispatcher options.
Load native authority only from repository configuration; verify it before payload
execution. Keep settings controls separate, required, unique and event-specific.
Exercise complete native call chains and all settings vectors, pending journals,
wrong repository/backend bindings and destination refs. Preserve effective-policy
semantics and retained compatibility feedback. No generation work is included.

Old exact-head findings and verdicts remain historical. The 5fc9250 green ledger
is obsolete as acceptance evidence after the reproduced bypass; a replacement
commit requires the complete matrix and fresh independent review.

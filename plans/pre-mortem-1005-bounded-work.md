# #1005 bounded checkpoint failure analysis

The bounded slice adds local coordination metadata to the existing drive and
recovery skills. The journal is neither an authorization record nor a host
enforcement mechanism. It does not create another prerequisite for #848.

Expected failures and probes:

- A changed candidate inherits an accepted verdict: reset current review and
  checks on candidate change; retain invalidated history and unresolved findings.
- Green CI erases a reproduced falsification: keep findings independent of check
  status; require resolution evidence and a fresh review receipt.
- Duplicate deliveries exhaust the budget: deduplicate stable event IDs and
  identical review receipts; count recurring classes across distinct heads.
- A lost worker and successor both write: coordinator assigns one owner and a
  new generation; lock plus optimistic revision serializes local writers.
- Resume manufactures acceptance: replay the journal, preserve pending review,
  and require a reconciliation checkpoint. The host still controls authority.
- Polling appears to be progress: read-only polls do not write; queued/active
  review and heartbeat updates do not reset the last-progress timestamp.
- Timestamp-only detection declares a healthy slow session dead: report only
  checkpoint/chunk due; actual diagnosis uses the coherent transcript.
- New machinery increases enforcement complexity: one stdlib helper shipped
  with an on-demand skill, no daemon, network transport, scheduler or gate.

Trust limits: callers supply actor IDs, clock values, failure classes and receipt
references. This is an accidental-conflict/recovery mechanism on a local POSIX
filesystem, not an adversarial security boundary. A malicious writer can edit
the journal. Host timing, message visibility and predecessor cancellation must
be proved separately in #1003. The pilot does not claim these capabilities.

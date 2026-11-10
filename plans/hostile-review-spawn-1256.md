# Independent review — #1256 item 3

## Evidence and scope

The assigned peer ran an actual authenticated official Claude CLI static review
of an immutable five-file copy and diff. Snapshot SHA256:
`bd7c0493fa33e5cd30e8e31ec7f1d5616d1a7702eb18926eb976b4c39658c6a1`.
The peer reported no blocking runtime finding on that snapshot and found a real
documentation contradiction: the parent-side setup example still changed into
the child directory. That `cd` was removed; child workingDirectory is explicit.
It also noted cwd-dependent fixtures; both shell payload helpers now bind cwd.
This is a record of actual reviewer results, not an inferred pass from startup.

Root independently read source and ran the full spawn fixture suite. Author and
Root identified the unbounded backpointer open; Root reviewed and accepted the
nonblocking/regular-file/bounded-read delta after actual FIFO/oversize negatives.

Root then tested the actual Craft 0.15.8 path-normalization contract and found
relative-parent and absolute HOME/symlink ordering mismatches. These were fixed
with exact host-recognized HOME matching and lexical normalization before
filesystem identity. Literal dollar names outside the host rewrite grammar stay
supported. Final remaining delta is recorded below for Root's direct review.

## Disposition

- Parent cwd documentation and fixture context: fixed.
- FIFO/oversize backpointer read: fixed; Root accepted the bounded delta.
- Host target normalization: fixed in candidate; accepted by Root after actual final fixture execution; see the durable review receipt below.
- Live host installation: not performed or claimed.

Final normalization delta SHA256:
`e89fcdbe56cae9edcdb05aa2f2c29eb56439b269d5023b59678216b7083459e0`.

Root durable independent acceptance: https://github.com/siege-analytics/claude-configs-public/issues/1256#issuecomment-6759510706 .
Root independently verified the final e89 delta digest, ran the 14 contract and
15 structural cases successfully, and ran the actual Craft host normalization
suite. The earlier Claude static review applies to its stated frozen snapshot;
the later bounded/source-normalization deltas are qualified as Root review.

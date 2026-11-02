# Ticket and metadata integration

The automatic merge combines ticket head 7afe5fb with metadata head 602c748.
It preserves the ten reviewed ticket source/test byte identities. The metadata
change rejects foreign URL-like PR selectors and restores coordinator evidence
checks for reopened artifacts. No release, protected-branch merge or deployment
is part of this local integration.

The complete selected scanner returned exit 1, not a clean result. The new
scanner test mapping exposes named-exception heuristics in task_actions.py.
The retained raw output, selected tree, protected base, source/scanner/test
identities and executable controls are in
[ticket-metadata-integration-evidence-1107.json](ticket-metadata-integration-evidence-1107.json).

Each disposition below is proposed for independent approval. All six enclosing
functions have equal ASTs against protected base b3c560b. That equality alone is
not acceptance: the direct failure controls exercise each handler's promised
result, including helpers reached through metadata maintenance and ticket reads.

| ID | Rule and source line | Reason | Evidence | Falsification |
| --- | --- | --- | --- | --- |
| M01 | code7 Return, 215 | Parse failure means the command is not an approved Python reader. | ValueError and SyntaxError controls return False. | Either error grants reader authority. |
| M02 | tests5 ValueError, 215 | A returned denial is the expected contract, not a propagated exception. | Direct parse ValueError control returns False. | Malformed source becomes a reader. |
| M03 | tests5 SyntaxError, 215 | Invalid syntax must return reader denial. | Direct parse SyntaxError control returns False. | Malformed source becomes a reader. |
| M04 | tests5 SubprocessError, 377 | Repository discovery failure becomes UnknownShape. | Failed Git query control raises UnknownShape. | Failed discovery selects a repository. |
| M05 | tests5 OSError, 377 | Unavailable Git cannot grant repository authority. | OSError query control raises UnknownShape. | Failed discovery selects a repository. |
| M06 | tests5 Exception, 511 | Released classifier failure remains unproven verdict 1. | RuntimeError control returns 1. Normal action dispatch then requires mutation classification and gates. | Classifier failure returns proved-read verdict 0. |
| M07 | tests5 OSError, 575 | Missing producer cannot grant the execution lane. | Producer-stat OSError control raises UnknownShape. | Missing producer gains an execution lane. |
| M08 | tests5 OSError, 631 | Unreadable metadata input cannot receive the text-edit exception. | Metadata-open OSError control raises UnknownShape; segment failure retains mutation target. | Unreadable body becomes metadata_only. |
| M09 | tests5 ValueError, 631 | Invalid metadata path cannot receive the text-edit exception. | Metadata-open ValueError control raises UnknownShape. | Invalid body becomes metadata_only. |
| M10 | tests5 UnknownShape, 734 | Initial syntax/producer failure retains a non-reader mutation target. | Initial UnknownShape control asserts error, read_only False and target cwd. | Unknown syntax obtains a read or metadata exception. |
| M11 | tests5 UnknownShape, 971 | Segment failure retains a non-reader mutation target. | Metadata segment UnknownShape control asserts error, cwd target and no metadata_only. | Failed segment obtains a read or metadata exception. |

The controls are isolated fault injection against the actual imported module;
they do not claim exhaustive handler coverage or live Craft callback verification.
The combined comprehensive producer run follows the committed merge at stable HEAD.

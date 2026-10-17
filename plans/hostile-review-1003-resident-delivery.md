# Resident delivery hostile review — #1003

The receipt is not a trust root. An attacker changing both installed content
and its receipt can make them agree. This adapter checks consistency inside an
already verified package; it cannot authenticate installed code or authorize
any protected operation. Documentation and code state this limit explicitly.

The original missing-inventory fallback was reproducibly unsafe for the new
contract: the selector could reconstruct inventory from the manifest and still
emit composed content. Hook rendering now requires the composed inventory;
ordinary JSON callers retain their existing fallback behavior. A regression
removes each mandatory input and requires no partial project output.

The initial positive containment assertion also encountered macOS’s
`/var` → `/private/var` alias. The test now compares resolved package roots;
runtime containment still rejects actual symlink components below that root.

The first broad run caught the verifier's old code-owned canonical kernel
digest after the scoped K5 correction. That digest is refreshed to the exact
generated kernel bytes; it is not derived from a mutable installation target.
The same run also rejected uncommitted selector bytes against immutable Git
release inputs. It was stopped rather than treated as a pass; full validation
will run on the clean committed source so those identities agree.

One render invocation validates identity, the receipt, all selected files and
resident bytes before emitting any project content. Tests instrument the real
hook’s selector call and inject an invalid selector state through its real
renderer, verifying one invocation and no partial project output. Canonical
kernel checks remain outside that renderer and unchanged.

Independent exact-head review and terminal hosted checks remain required before
integration. Plan acceptance is recorded on #1003 comment 6212099758; it is not
an implementation verdict. Live host capability remains unverified.

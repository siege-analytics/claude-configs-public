#!/usr/bin/env python3
"""Separate the executable part of a shell command from its data.

Reads a command on stdin.

    (no args)      write the command with data regions removed
    --is-commit    exit 0 if the command invokes `git commit`, else 1

Guards that block on command shape must answer "does this command DO x", and the
naive answer - grep the raw text for the literal string - cannot tell doing from
talking about. Observed live: a read-only grep whose pattern contained the
string, and a `gh issue create` whose heredoc body documented commit shapes,
which then tripped a second guard into reporting attribution in a commit message
that did not exist (#55).

Removing the regions where text is data rather than code fixes those. The danger
is removing too much: a first attempt stripped every quoted span, which silently
disabled the guards for `bash -c "git commit ..."` and `eval "git commit ..."`.
A guard that fails open is worse than the false positives it was fixing.

So the rules here are asymmetric, and deliberately so:

  * Shell-interpreter arguments are CODE. `bash -c '...'`, `sh -c`, `zsh -c`,
    `dash -c` and `eval` have their argument unwrapped and scanned, not dropped.
  * Anything ambiguous is KEPT. Unbalanced quotes, a heredoc whose terminator
    never appears, recursion past a sane depth - all return the text unchanged,
    so the guard still sees the string and blocks. A false positive costs one
    retry; a false negative costs an unguarded commit.

This is a heuristic, not a shell parser. It decides WHERE to look; each guard's
own patterns decide WHAT counts, unchanged. Ref: #55, #106.
"""

import re
import sys

_MAX_DEPTH = 3

# <<TAG, <<-TAG, <<'TAG', <<"TAG" - and NOT the left-shift operator. The opener
# must be followed by an identifier, and `$((1 << 2))` therefore does not match
# because a digit cannot start one. Requiring a word character after the tag to
# be absent keeps `<<EOF2` intact as its own tag rather than matching `EOF`.
_HEREDOC_OPEN = re.compile(r"<<-?\s*(['\"]?)([A-Za-z_][A-Za-z0-9_]*)\1")

# A shell interpreter given code as an argument, or eval. The argument is code.
_SHELL_ARG = re.compile(
    r"""(?<![0-9A-Za-z_/])              # not part of a longer word (lookbehind:
                                    # the boundary char is kept, #1109)
        (?:(?:ba|z|da|a)?sh\s+-c|eval)  # bash -c, sh -c, zsh -c, dash -c, ash -c, eval
        \s+
        (?:"((?:\\.|[^"\\])*)"         # its argument: double-quoted, escapes honoured
          |'([^']*)')                   # or single-quoted (no escapes in sh)
    """,
    re.VERBOSE | re.DOTALL,
)


def _shell_payload(match):
    """The code an interpreter argument runs, with double-quote escapes undone."""
    if match.group(1) is not None:
        return re.sub(r'\\(["\\$`])', r"\1", match.group(1))
    return match.group(2)

# Identical to the regex the guards used inline, so this changes where we look,
# never what counts as a commit once found.
_COMMIT = re.compile(r"(?:^|[^0-9A-Za-z])git commit(?:[^0-9A-Za-z]|$)")


def _quotes_balanced(text):
    """True when every quote in the text closes.

    Unbalanced quoting means the tail cannot be reasoned about, so callers keep
    the text rather than stripping it. `echo don't && git commit` is the shape
    that matters: the lone apostrophe would otherwise swallow the real command.
    """
    i, n = 0, len(text)
    while i < n:
        c = text[i]
        if c == "\\":
            i += 2
            continue
        if c in ("'", '"'):
            quote = c
            i += 1
            while i < n:
                if text[i] == "\\" and quote == '"':
                    i += 2
                    continue
                if text[i] == quote:
                    break
                i += 1
            else:
                return False
        i += 1
    return True


def strip_heredocs(command):
    """Drop heredoc bodies, keeping the line that opens them.

    The opener stays because `git commit -F - <<'MSG'` is still an invocation;
    only the body is data. A heredoc whose terminator never appears is left
    intact - an unterminated body is indistinguishable from ordinary text, and
    dropping the remainder of the command would hide whatever followed.
    """
    lines = command.split("\n")
    out, pending = [], []
    for line in lines:
        if pending:
            if line.strip() == pending[0]:
                pending.pop(0)
            continue
        out.append(line)
        for match in _HEREDOC_OPEN.finditer(line):
            pending.append(match.group(2))
    if pending:
        return command  # terminator never arrived: keep everything
    return "\n".join(out)


def _strip_quoted(text):
    """Remove quoted data; keep what the shell would run. Balanced text only.

    A quoted span with whitespace in it is prose (a message, a body) and is
    dropped. A quoted single word is a word the shell runs with its quotes
    removed - `git "commit"`, `g''it`, `git 'add'` - so its content is kept.
    Dropping it hid the verb (#1109). A backslash outside quotes escapes the
    next character, which the shell keeps; an escaped newline joins lines.
    """
    out, i, n = [], 0, len(text)
    while i < n:
        c = text[i]
        if c == "\\" and i + 1 < n:
            nxt = text[i + 1]
            if nxt == "\n":
                pass                      # line continuation
            elif nxt.isspace():
                out.append("\\" + nxt)   # an escaped blank joins one word
            else:
                out.append(nxt)
            i += 2
            continue
        if c in ("'", '"'):
            quote = c
            i += 1
            span = []
            while i < n:
                if text[i] == "\\" and quote == '"' and i + 1 < n:
                    span.append(text[i + 1])
                    i += 2
                    continue
                if text[i] == quote:
                    i += 1
                    break
                span.append(text[i])
                i += 1
            word = "".join(span)
            if word and not any(ch.isspace() for ch in word):
                out.append(word)
        else:
            out.append(c)
            i += 1
    return "".join(out)


def code_only(command, depth=0):
    if depth > _MAX_DEPTH:
        return command
    text = strip_heredocs(command)
    if not _quotes_balanced(text):
        return text

    # Unwrap shell-interpreter arguments before anything is dropped, so that
    # `bash -c "git commit"` keeps its payload as code.
    def _unwrap(match):
        return " " + code_only(_shell_payload(match), depth + 1) + " "

    unwrapped = _SHELL_ARG.sub(_unwrap, text)
    if unwrapped != text:
        return code_only(unwrapped, depth + 1)
    return _strip_quoted(text)


def _segments(text):
    """Split into command segments on ; && || | and newlines, honouring quotes.

    Needed because a guard asking "what is this command staging" must not read
    the arguments of a different command in the same line. `git add a.py && git
    commit -m "..."` has one staging segment; the message belongs to the other.
    """
    out, cur, i, n = [], [], 0, len(text)
    while i < n:
        c = text[i]
        if c in ("'", '"'):
            quote = c
            cur.append(c)
            i += 1
            while i < n:
                cur.append(text[i])
                if text[i] == "\\" and quote == '"' and i + 1 < n:
                    cur.append(text[i + 1]); i += 2; continue
                if text[i] == quote:
                    i += 1; break
                i += 1
            continue
        if c in (";", "\n") or text[i:i + 2] in ("&&", "||"):
            out.append("".join(cur)); cur = []
            i += 2 if text[i:i + 2] in ("&&", "||") else 1
            continue
        if c == "|":
            out.append("".join(cur)); cur = []; i += 1
            continue
        cur.append(c); i += 1
    out.append("".join(cur))
    return [s.strip() for s in out if s.strip()]


def _unquote(tok):
    if len(tok) >= 2 and tok[0] == tok[-1] and tok[0] in ("'", '"'):
        return tok[1:-1]
    return tok


def _tokens(segment):
    out, cur, i, n = [], [], 0, len(segment)
    while i < n:
        c = segment[i]
        if c.isspace():
            if cur: out.append("".join(cur)); cur = []
            i += 1; continue
        if c == "\\" and i + 1 < n:
            cur.append(segment[i + 1]); i += 2  # the shell drops the backslash
            continue
        if c in ("'", '"'):
            quote = c; i += 1
            while i < n and segment[i] != quote:
                cur.append(segment[i]); i += 1
            i += 1
            continue
        cur.append(c); i += 1
    if cur: out.append("".join(cur))
    return out


def git_add_targets(command):
    """Paths a `git add` in this command would stage.

    Only the staging segment's own arguments, flags dropped. Reading the whole
    command instead made every word after the verb a candidate filename, so a
    commit message in the same line was scanned as paths - which is how a message
    mentioning a config file was refused as an attempt to stage one (#67).
    """
    raw = strip_heredocs(command)
    # Interpreter arguments are code (see the module docstring): stage targets
    # inside `bash -c "git add .env"` or `eval "..."` count too (#1109). The
    # unwrapped text is scanned IN ADDITION to the raw text, and only when its
    # quotes still balance: a payload such as `echo it's` would otherwise turn
    # the rest of the line into one quoted span and hide a later `git add`.
    texts = [raw]
    text = raw
    for _ in range(_MAX_DEPTH):
        unwrapped = _SHELL_ARG.sub(_splice, text)
        if unwrapped == text or not _quotes_balanced(unwrapped):
            break
        text = unwrapped
        texts.append(text)
    targets = []
    for t in texts:
        for path in _add_targets(t):
            if path not in targets:
                targets.append(path)
    return targets


def _splice(match):
    """Replace `bash -c '<code>'` with `; <code> ;` so it splits as code."""
    return " ; " + _shell_payload(match) + " ; "


def _add_targets(text):
    targets = []
    for seg in _segments(text):
        toks = _tokens(seg)
        for i in range(len(toks) - 1):
            if toks[i] == "git" and toks[i + 1] == "add":
                for tok in toks[i + 2:]:
                    if tok.startswith("-"):
                        continue
                    targets.append(_unquote(tok))
                break
    return targets


def is_git_commit(command):
    return bool(_COMMIT.search(code_only(command)))


def main():
    command = sys.stdin.read()
    if "--stage-args" in sys.argv[1:]:
        for path in git_add_targets(command):
            print(path)
        return 0
    if "--is-commit" in sys.argv[1:]:
        # The verdict is printed as well as returned: exit 1 alone cannot be
        # told from a crash that never reached here (#1109 review).
        verdict = is_git_commit(command)
        print("commit" if verdict else "none")
        return 0 if verdict else 1
    sys.stdout.write(code_only(command))
    return 0


if __name__ == "__main__":
    # An internal error must not read as "not a commit" (exit 1) or "no
    # targets" (empty output): exit 3 so the shell helpers fall back to their
    # over-matching path (#1109).
    try:
        sys.exit(main())
    except Exception as exc:  # noqa: BLE001 - any failure fails closed
        print(f"command-text.py: {type(exc).__name__}: {exc}", file=sys.stderr)
        sys.exit(3)

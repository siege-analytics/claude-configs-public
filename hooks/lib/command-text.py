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
    r"""(?:^|[^0-9A-Za-z_/])            # not part of a longer word
        (?:(?:ba|z|da|a)?sh\s+-c|eval)  # bash -c, sh -c, zsh -c, dash -c, ash -c, eval
        \s+
        (['"])(.*?)\1                   # its quoted argument
    """,
    re.VERBOSE | re.DOTALL,
)

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
    """Remove quoted spans. Only ever called on balanced text."""
    out, i, n = [], 0, len(text)
    while i < n:
        c = text[i]
        if c == "\\" and i + 1 < n:
            out.append(text[i:i + 2])
            i += 2
            continue
        if c in ("'", '"'):
            quote = c
            i += 1
            while i < n:
                if text[i] == "\\" and quote == '"' and i + 1 < n:
                    i += 2
                    continue
                if text[i] == quote:
                    i += 1
                    break
                i += 1
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
        return " " + code_only(match.group(2), depth + 1) + " "

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
    targets = []
    for seg in _segments(strip_heredocs(command)):
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
        return 0 if is_git_commit(command) else 1
    sys.stdout.write(code_only(command))
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Separate the executable part of a shell command from its data.

Reads a command on stdin.

    (no args)      write the command with data regions removed
    --is-commit    exit 0 if the command invokes `git commit`, else 1
    --publication CWD  emit direct publication trigger/target data for adapters

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

import fnmatch
import json
import os
import re
import shlex
import sys

# Trigger inspection must not write bytecode into the installed hook package.
sys.dont_write_bytecode = True

_MAX_DEPTH = 3
_PUBLICATION_DYNAMIC = "__ccp_publication_dynamic__"

# <<TAG, <<-TAG, <<'TAG', <<"TAG" - and NOT the left-shift operator. The opener
# must be followed by an identifier, and `$((1 << 2))` therefore does not match
# because a digit cannot start one. Requiring a word character after the tag to
# be absent keeps `<<EOF2` intact as its own tag rather than matching `EOF`.
_HEREDOC_OPEN = re.compile(r"<<-?\s*(['\"]?)([A-Za-z_][A-Za-z0-9_]*)\1")

# A shell interpreter given code as an argument, or eval. The argument is code.
_SHELL_ARG = re.compile(
    r"""(?<![0-9A-Za-z_/])              # not part of a longer word (lookbehind:
                                    # the boundary char is kept, #1109)
        (?:/[^\s'";|&]+/)?            # literal absolute interpreter path
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


def _publication_cli(args):
    """Locate literal CLI resource/verb and repo flags across their valid positions.

    GitHub reuses the metadata recognizer's [github.com/]OWNER/REPO spelling.
    GitLab retains literal nested/host-qualified selectors for the existing
    owner-prefix policy. These boundaries never authorize the CLI action.
    """
    values = set("--title -t --body -b --body-file -F --head -H --base -B --reviewer -r --assignee -a --label -l --milestone -m --project -p -P --template -T --subject --author-email -A --match-head-commit --hostname".split())
    gitlab = os.path.basename(args[0]) == 'glab'
    if gitlab:
        values = set("--title -t --description -d --description-file --source-branch -s --target-branch -b --reviewer -r --assignee -a --label -l --milestone -m --related-issue --target-project --source-project".split())
    repositories, positionals, help_flag, literal, index = [], [], False, False, 1
    while index < len(args):
        word = args[index]
        flag, equal, value = word.partition('=')
        if not literal and word == '--':
            literal = True
        elif not literal and (flag in {'--repo', '-R'} or flag.startswith('-R')):
            if flag.startswith('-R') and flag != '-R':
                value = flag[2:]
            elif not equal:
                index += 1
                value = args[index] if index < len(args) else ''
            repositories.append(value)
        elif not literal and flag in values:
            if not equal:
                index += 1  # Free text stays one value, including '--help'/'--repo'.
        elif not literal and word in {'--help', '-h'}:
            help_flag = True
        elif literal or not word.startswith('-'):
            positionals.append(word)
        index += 1
    resource = 'pr' if os.path.basename(args[0]) == 'gh' else 'mr'
    if len(positionals) < 2 or help_flag:
        return None
    if any(_PUBLICATION_DYNAMIC in word for word in positionals[:2]):
        return ''
    if positionals[0] != resource:
        if any(char in positionals[0] for char in '*?[') and fnmatch.fnmatchcase(resource, positionals[0]) and positionals[1] in {'create', 'merge'}:
            return ''
        return None
    if positionals[1] not in {'create', 'merge'}:
        return '' if any(char in positionals[1] for char in '*?[') else None
    repository = ''
    for value in repositories:
        pattern = r'((?:https?://)?[A-Za-z0-9_.:-]+(?:/[A-Za-z0-9_.-]+)+)' if gitlab else r'(?:github\.com/)?([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)'
        match = re.fullmatch(pattern, value, re.I)
        if not match or repository and repository != match[1]:
            return ''  # Known publication, unresolved selector: never "no trigger".
        repository = match[1]
    return os.path.basename(args[0]) + ' ' + ' '.join(positionals[:2]) + (' --repo ' + repository if repository else '')


def _publication_help(args, values):
    """A real help option, excluding option values and post-- operands."""
    index = 0
    while index < len(args):
        word = args[index]
        flag, equal, _value = word.partition('=')
        if word == '--':
            return False
        if flag in values and not equal:
            index += 1
        elif word in {'--help', '-h'}:
            return True
        index += 1
    return False


def publication_effects(command, cwd, depth=0, state=None):
    """Find direct publication argv; never inspect literal metadata as code.

    Reuse the released shell token and Git/global-option boundaries. This is
    trigger selection only: ordinary external programs are not presumed to
    publish, and task/target/body authority remains with its owning guards.
    """
    from task_actions import UnknownShape, shell_tokens
    from git_command import literal_prefix, prefix, directory_target
    if depth > 4:
        raise UnknownShape("publication wrapper exceeds inspection limit")
    command, expansion_effects = _publication_mask(command, cwd, depth)
    parsed = shell_tokens(command, inspection_comments=True)
    groups, words, redirected = [], [], False
    for word, operator, globs in parsed:
        if redirected:
            if operator:
                raise UnknownShape("unresolved publication redirect")
            redirected = False
            continue
        if operator:
            if re.fullmatch(r"[0-9]*(?:>>|>&|<&|>\||>|<)|&>>|&>", word):
                redirected = True
            elif word in {";", "&&", "||", "|", "&"}:
                groups.append(words); words = []
            else:
                raise UnknownShape("unsupported publication shell operator")
        else:
            words.append((word, globs))
    if redirected:
        raise UnknownShape("missing publication redirect target")
    groups.append(words)
    effects = list(expansion_effects)
    for group in groups:
        if not group:
            continue
        args = [word for word, _ in group]
        if group[0][1] or _PUBLICATION_DYNAMIC in args[0]:
            raise UnknownShape("unresolved executable expansion")
        original = list(args)
        args, _environment = literal_prefix(args, strict=True)
        if not args:
            continue
        name = os.path.basename(args[0])
        if name == "cd":
            target = directory_target(original)
            if any(operator and word != "&&" for word, operator, _ in parsed):
                raise UnknownShape("unresolved publication directory control flow")
            cwd = target
            continue
        if name in {"git", "gh", "glab"} and any(globs for _, globs in group[:3]):
            raise UnknownShape("unresolved publication verb expansion")
        if name in {"bash", "sh", "zsh", "dash", "ksh", "ash"}:
            index = 1
            while index < len(args) and args[index].startswith('-'):
                flag = args[index]
                if re.fullmatch(r'-[A-Za-z]*c[A-Za-z]*', flag):
                    if index + 1 >= len(args):
                        raise UnknownShape("missing publication shell program")
                    if index == 1 and flag == '-c':
                        effects.extend(publication_effects(args[index + 1], cwd, depth + 1))
                    else:
                        # Login/startup flags can change cwd. Inspect literal
                        # program code, but never borrow the caller's HEAD.
                        nested = publication_trigger(args[index + 1], cwd, depth + 1)
                        if nested['kind'] != 'none':
                            effects.append({'kind': 'git', 'cwd': cwd, 'scope': ''})
                    break
                index += 2 if flag in {'-o', '--rcfile', '--init-file'} else 1
            continue
        if name == "eval":
            nested = {}
            effects.extend(publication_effects(" ".join(args[1:]), cwd, depth + 1, nested))
            cwd = nested["cwd"]
        elif name == "git":
            item = prefix(original, cwd)
            if item and item['args'][0] == "push" and not _publication_help(item['args'][1:], {'--repo', '--receive-pack', '--exec', '--push-option', '-o'}):
                effects.append({'kind': 'git', 'cwd': item['cwd'], 'scope': '' if any(_PUBLICATION_DYNAMIC in word for word in original) else 'git push'})
        elif name in {"gh", "glab"}:
            scope = _publication_cli(args)
            if scope is not None:
                effects.append({'kind': name, 'cwd': cwd, 'scope': scope})
        elif name == "exec" and len(args) > 1 and not args[1].startswith('-'):
            effects.extend(publication_effects(shlex.join(args[1:]), cwd, depth + 1))
        elif name == "timeout" and len(args) > 2 and re.fullmatch(r"[0-9]+(?:\.[0-9]+)?[smhd]?", args[1]):
            effects.extend(publication_effects(shlex.join(args[2:]), cwd, depth + 1))
        elif name in {"sudo", "nice", "command", "env", "exec", "timeout", "if", "then", "for", "do", "while", "until", "!"}:
            raise UnknownShape("unresolved publication dispatch")
    if state is not None:
        state["cwd"] = cwd
    return effects


def _publication_mask(command, cwd, depth):
    """Mark dynamic operands while separately inspecting substitution programs.

    The shared lexer still owns quotes/operators. Marked executable/verb/target
    positions remain unresolved; ordinary data operands do not become code.
    """
    from task_actions import UnknownShape
    output, effects, quote, index = [], [], '', 0
    while index < len(command):
        char = command[index]
        if char == "\\" and quote != "'" and index + 1 < len(command):
            output.extend(command[index:index + 2]); index += 2
            continue
        if char == "'" and quote != '"':
            quote = '' if quote == "'" else "'"
        elif char == '"' and quote != "'":
            quote = '' if quote == '"' else '"'
        elif quote != "'" and (command.startswith('$(', index) or char == '`'):
            start = index + (2 if char == '$' else 1)
            end = command.find(')' if char == '$' else '`', start)
            if end < 0 or '(' in command[start:end]:
                raise UnknownShape("unresolved nested publication substitution")
            nested = publication_trigger(command[start:end], cwd, depth + 1)
            if nested['kind'] == 'unknown':
                raise UnknownShape("unresolved publication substitution")
            effects.extend(nested.get('effects', []))
            output.append(_PUBLICATION_DYNAMIC); index = end + 1
            continue
        elif quote != "'" and char == '$':
            match = re.match(r'\$(?:[A-Za-z_][A-Za-z0-9_]*|[0-9@*#?$!-]|\{[^{}]*\})', command[index:])
            if match:
                if '$(' in match[0] or '`' in match[0]:
                    raise UnknownShape("unresolved publication parameter substitution")
                output.append(_PUBLICATION_DYNAMIC); index += len(match[0])
                continue
        output.append(char); index += 1
    return ''.join(output), effects


def publication_trigger(command, cwd, depth=0):
    """A resolved effect, proven non-trigger, or plausible unresolved trigger."""
    from task_actions import UnknownShape
    try:
        effects = publication_effects(command, os.path.realpath(cwd or os.getcwd()), depth)
        targets = set(item['cwd'] for item in effects)
        if any(not item['scope'] for item in effects):
            return {'kind': 'unknown', 'error': 'literal publication selector is unresolved'}
        if len(targets) > 1:
            return {'kind': 'unknown', 'error': 'publish different repositories in separate tool calls'}
        return {'kind': 'publication', 'cwd': next(iter(targets)), 'effects': effects, 'fingerprint': any(item['kind'] != 'glab' for item in effects)} if effects else {'kind': 'none'}
    except (UnknownShape, OSError, ValueError) as exc:
        # Never use legacy code_only's quote-stripping heuristic as a proof of
        # absent publication. Only the released reader may discharge unknown
        # syntax; plausible executable publication stays unresolved.
        from task_actions import released_read_verdict
        if released_read_verdict(command) == 0:
            return {'kind': 'none'}
        normalized = re.sub(r"[\\\"']", "", command)
        plausible = re.search(r"(?:^|[^A-Za-z0-9_])(?:git(?:\s+[^;|&]*?\bpush)|(?:gh|glab)\s+[^;|&]*?\b(?:pr|mr)\s+[^;|&]*?\b(?:create|merge))\b", normalized)
        dynamic = re.search(r"(?:^|[;&|]\s*)[^\s]*[$`*?\[][^\s]*\s+(?:push|pr|mr)\b", normalized) or re.search(r"\b(?:git|gh(?:\s+pr)?|glab(?:\s+mr)?)\s+[^\s]*[$`*?\[]", normalized)
        return {'kind': 'unknown', 'error': str(exc)} if plausible or dynamic or 'Git alias' in str(exc) else {'kind': 'none'}


def main():
    command = sys.stdin.read()
    if "--publication" in sys.argv[1:]:
        index = sys.argv.index("--publication")
        print(json.dumps(publication_trigger(command, sys.argv[index + 1] if index + 1 < len(sys.argv) else "")))
        return 0
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

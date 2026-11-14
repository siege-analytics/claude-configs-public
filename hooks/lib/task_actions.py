"""Bounded shell classification and canonical action paths (#1051).

Pure readers and explicitly approved diagnostics have separate early-allow
flags. Candidate commands are never executed; Git ownership uses a bounded
read-only toplevel query. Unknown syntax remains mutation-gated or fails closed.
Substitutions, subshells, eval and executable reader options are not pure reads.
Only bounded pure-reader/pytest grammars admit pathname globs, with a literal
non-option prefix or a genuine -- terminator; quoted patterns do not expand.
"""
from __future__ import annotations
from pathlib import Path

import ast
import fnmatch
import json
import os
import re
import shlex
import stat
import subprocess
import sys
import time


class UnknownShape(ValueError):
    pass


def shell_tokens(command: str, *, inspection_comments=False, inspection_expansions=False, quoted_words=None, assignment_words=None) -> list[tuple[str, bool, tuple[int, ...]]]:
    """Preserve operators and positions of unquoted glob characters.

    Reader/diagnostic classification decides whether a glob word is safe;
    mutation operands still require explicit concrete paths.
    """
    tokens = []
    word = ""
    globs = []
    active = False
    assignment_literal = False
    fd_literal = True  # only adjacent, wholly unquoted ASCII digits are IO_NUMBER
    quote = ""
    def emit_word():
        if quoted_words is not None and not fd_literal:
            quoted_words.add(len(tokens))
        if assignment_words is not None and assignment_literal:
            assignment_words.add(len(tokens))
        tokens.append((word, False, tuple(globs)))

    i = 0
    while i < len(command):
        c = command[i]
        if quote == "'":
            if c == quote:
                quote = ""
            else:
                word += c
        elif c == "\\" and quote != "'":
            i += 1
            if i >= len(command):
                raise UnknownShape("escaped newline or incomplete escape")
            if command[i] == "\n":
                if inspection_expansions:
                    i += 1
                    continue
                raise UnknownShape("escaped newline or incomplete escape")
            word += command[i]
            active = True
            fd_literal = False
        elif c in "$`" and quote != "'":
            if not inspection_expansions:
                raise UnknownShape("shell expansion requires mutation handling")
            word += '__ccp_publication_dynamic__'
            active = True
        elif quote == '"':
            if c == quote:
                quote = ""
            else:
                word += c
        elif c in "'\"":
            quote = c
            active = True
            fd_literal = False
        elif (inspection_expansions and command.startswith('{}', i) and not active
              and (i + 2 == len(command) or command[i + 2].isspace() or command[i + 2] in ';&|<>')):
            word, active = '{}', True  # literal find placeholder, not a shell group
            i += 1
        elif c in "(){}":
            if not inspection_expansions:
                raise UnknownShape("shell group requires mutation handling")
            if quote:
                word += c
                active = True
            elif c in '()' or not active:
                if active:
                    emit_word()
                tokens.append((';', True, ()))
                word, active, globs, fd_literal, assignment_literal = '', False, [], True, False
            else:
                word += '__ccp_publication_dynamic__'
                active = True
        elif c in "*?[" and not (c == "[" and not active and i + 1 < len(command) and command[i + 1].isspace()):
            globs.append(len(word))
            word += c
            active = True
        elif c.isspace() or c in ";&|<>":
            fd = ""
            if active:
                if c in "<>" and fd_literal and re.fullmatch(r"[0-9]+", word):
                    fd = word
                else:
                    emit_word()
                word, active, globs, fd_literal, assignment_literal = "", False, [], True, False
            if c == "\n":
                tokens.append((";", True, ()))
            elif not c.isspace():
                # Longest redirect first: &>> is not background + append,
                # and >&/<& consume their ampersand, not a shell separator.
                if c in "<>" or command.startswith("&>", i):
                    op = next(op for op in ("&>>", "&>", ">>", ">&", "<&", ">|", "<<", ">", "<")
                              if command.startswith(op, i))
                    i += len(op) - 1
                    op = fd + op
                else:
                    op = c
                    if i + 1 < len(command) and command[i + 1] == c:
                        op += c
                        i += 1
                tokens.append((op, True, ()))
        elif c == "#" and not active:
            if inspection_comments:
                end = command.find("\n", i)
                i = len(command) if end < 0 else end
                continue
            # This documented final comment is syntax only, never task authority.
            # Every executed prefix still needs its own scope and artifacts.
            approval = re.fullmatch(
                r"[ \t]*\[destructive-ok:[ \t]+Reason:([^\]\r\n]+);[ \t]*"
                r"Evidence:([^\]\r\n]+);[ \t]*Falsification:([^\]\r\n]+)\]"
                r"[ \t]*(?:\n[ \t]*)*", command[i + 1:])
            if approval and all(field.strip() for field in approval.groups()):
                break
            raise UnknownShape("shell comment requires mutation handling")
        else:
            if c == '=' and fd_literal and re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', word):
                assignment_literal = True  # value quoting does not quote NAME=
            word += c
            active = True
        i += 1
    if quote:
        raise UnknownShape("unclosed quote")
    if active:
        emit_word()
    return tokens


def _reader_globs(args: list[str], positions: list[tuple[int, ...]]) -> None:
    """V2: expansion only in bounded pure-reader/pytest argument grammars.

    Mixed commands (find/tree/sort, interpreters, fixing linters, etc.) keep
    concrete paths even when their write/exec switch is absent. The bounded
    options below also distinguish a real -- from an option VALUE of --.
    Quoted patterns have no expansion positions and retain existing handling.
    """
    if not any(positions):
        return
    cmd, start = args[0], 1
    if cmd == 'git':
        while start + 1 < len(args) and args[start] == '-C':
            if positions[start + 1]:
                raise UnknownShape('Git targeting requires an explicit concrete path')
            start += 2
        if start >= len(args) or args[start] not in {'diff', 'log'}:
            raise UnknownShape('globbed Git arguments require pure diff/log paths')
        cmd = 'git-' + args[start]
        start += 1
    elif cmd in {'python', 'python3'} and args[1:3] == ['-m', 'pytest']:
        cmd, start = 'pytest', 3
    elif cmd == 'gh' and args[1:2] == ['api']:
        cmd, start = 'gh-api', 2
    grammars = {
        'ls': ('-a -A -l -h -d -R -t -r -S -1 -F -p -i -n -s --all --almost-all --human-readable --recursive --directory --color --group-directories-first', '--color --sort --format --time --time-style --quoting-style --block-size --ignore --hide'),
        'cat': ('-n -b -s -v -e -E -t -T -u -A --number --number-nonblank --squeeze-blank --show-all --show-ends --show-tabs --show-nonprinting', ''),
        'head': ('-q -v --quiet --silent --verbose', '-n --lines -c --bytes'),
        'tail': ('-q -v -f -F --quiet --silent --verbose --follow --retry', '-n --lines -c --bytes --follow --pid --sleep-interval --max-unchanged-stats'),
        'grep': ('-n -r -R -i -l -L -c -v -w -x -q -s -h -H -E -F -G -P -o -a -I -z -Z --line-number --recursive --ignore-case --files-with-matches --count --invert-match --only-matching --no-messages --fixed-strings --extended-regexp --quiet', '-e --regexp -f --file -m --max-count -A -B -C --after-context --before-context --context --include --exclude --exclude-dir --binary-files --color --colour --directories --devices --label'),
        'rg': ('-n -i -l -L -c -v -w -x -q -s -o -a -u -F -P --hidden --files --no-ignore --json --line-number --count --invert-match --quiet --ignore-case --fixed-strings --pcre2 --only-matching --no-line-number --no-heading --heading', '-e --regexp -f --file -m --max-count -A -B -C --after-context --before-context --context -g --glob --iglob -t --type -T --type-not --color --colors -r --replace'),
        'wc': ('-l -w -c -m -L --lines --words --bytes --chars --max-line-length', ''),
        'file': ('-b -i -L -h -k -N --brief --mime --mime-type --mime-encoding --dereference --no-dereference --keep-going --no-pad', '-m --magic-file -f --files-from -F --separator -e --exclude --exclude-quiet -P --parameter'),
        'stat': ('-l -x -n -q -r -s -L --dereference --file-system --terse', '-f -t -c --format --printf --cached'),
        'diff': ('-u -q -r -s -N -a -b -B -w -i -y --unified --brief --recursive --report-identical-files --new-file --text --ignore-space-change --ignore-all-space --side-by-side', '-U -C -I --ignore-matching-lines --exclude --exclude-from --label --unified'),
        'git-diff': ('-p -u --patch --stat --name-only --name-status --check --cached --staged --no-index --no-ext-diff --no-textconv --exit-code --quiet --raw --numstat --shortstat --color --no-color --full-index --binary', '-U --unified --src-prefix --dst-prefix --word-diff-regex'),
        'git-log': ('--oneline --stat --name-only --name-status --no-merges --first-parent --all --graph --decorate --no-decorate --no-color --date-order --reverse --abbrev-commit', '-n --max-count --since --until --author --grep --format --pretty --date'),
        'pytest': ('-q -qq -v -vv -x -s --collect-only --disable-warnings --strict-markers --strict-config --no-header --no-summary', '-k -m --maxfail --tb --color'),
        'gh-api': ('--paginate --slurp --silent --include --verbose', '-H --header --hostname -q --jq -t --template'),
    }
    if cmd in {'egrep', 'fgrep'}:
        cmd = 'grep'
    if cmd not in grammars:
        raise UnknownShape('this command keeps the explicit concrete-path rule for glob expansions')
    flags, values = (set(s.split()) for s in grammars[cmd])
    literal, expecting = False, ''

    def shape(word, globs, offset=0, *, pattern=False):
        if not globs:
            return
        if not word or any(p < offset for p in globs):
            raise UnknownShape('globbed option key: prefix ./ or quote the pattern')
        # An attached fixed grep --include= key survives expansion verbatim.
        if pattern:
            return
        forbidden = '-*?[{$`~' if not literal else '{$`~'
        if word[0] in forbidden:
            raise UnknownShape('leading glob argument: prefix ./ or quote the pattern')

    for index in range(start, len(args)):
        word, globs = args[index], positions[index]
        if expecting:
            if cmd == 'pytest' and globs:
                raise UnknownShape('pytest globs are selection paths, not option values')
            shape(word, globs)
            expecting = ''
        elif not literal and word == '--':
            literal = True
        elif not literal and word.startswith('-') and word != '-':
            key, equals, value = word.partition('=')
            if equals and key in values:
                if cmd == 'pytest' and globs:
                    raise UnknownShape('pytest globs are selection paths, not option values')
                shape(value, globs, len(key) + 1, pattern=cmd == 'grep' and key == '--include')
            elif word in flags:
                pass
            elif word in values:
                expecting = word
            elif word.startswith('-') and not word.startswith('--') and len(word) > 2 and all('-' + c in flags for c in word[1:]):
                pass  # known no-value short flag cluster, never -e/-f/etc.
            elif not word.startswith('--') and word[:2] in values and len(word) > 2:
                shape(word[2:], globs, 2)
            else:
                raise UnknownShape('unbounded glob reader option: prefix ./ or quote the pattern')
        else:
            shape(word, globs)
    if expecting:
        raise UnknownShape('missing glob reader option value')


def _python_read(args: list[str]) -> bool:
    # Isolation prevents local json.py / ast.py from executing on import.
    if not args or args[0] not in {"python", "python3"}:
        return False
    if "-I" not in args or "-c" not in args:
        return False
    pos = args.index("-c")
    if set(args[1:pos]) - {"-I", "-B"} or pos + 2 != len(args):
        return False
    try:
        tree = ast.parse(args[pos + 1])
    except (ValueError, SyntaxError):
        return False
    bound = set()
    modules = set()
    reserved = {"open", "print", "len", "str", "int", "sorted", "list", "dict", "tuple", "bool"}

    def expr(n):
        if isinstance(n, ast.Constant):
            return isinstance(n.value, (str, bytes, int, float, bool, type(None)))
        if isinstance(n, ast.Name):
            return n.id in bound  # callable/module values cannot be passed around
        if isinstance(n, (ast.List, ast.Tuple, ast.Set)):
            return all(expr(x) for x in n.elts)
        if isinstance(n, ast.Dict):
            return all(k is not None and expr(k) and expr(v) for k, v in zip(n.keys, n.values))
        if isinstance(n, ast.Subscript):
            return expr(n.value) and expr(n.slice)
        if isinstance(n, ast.Slice):
            return all(x is None or expr(x) for x in (n.lower, n.upper, n.step))
        if not isinstance(n, ast.Call) or any(k.arg is None for k in n.keywords):
            return False
        if not all(expr(x) for x in n.args) or not all(expr(k.value) for k in n.keywords):
            return False
        f = n.func
        if isinstance(f, ast.Name):
            if f.id == "open":
                return (1 <= len(n.args) <= 2 and isinstance(n.args[0], ast.Constant)
                        and isinstance(n.args[0].value, str)
                        and (len(n.args) == 1 or isinstance(n.args[1], ast.Constant)
                             and n.args[1].value in {"r", "rb", "rt"})
                        and all(k.arg in {"encoding", "errors"} for k in n.keywords))
            return f.id in reserved - {"open"} and not n.keywords
        if isinstance(f, ast.Attribute) and isinstance(f.value, ast.Name):
            allowed = {"json": {"load", "loads", "dumps"}, "ast": {"parse", "literal_eval", "dump"}}
            return f.value.id in modules and f.attr in allowed.get(f.value.id, set()) and not n.keywords
        if isinstance(f, ast.Attribute) and f.attr in {"read", "readline", "readlines"}:
            return isinstance(f.value, ast.Call) and isinstance(f.value.func, ast.Name) and f.value.func.id == "open" and expr(f.value) and not n.keywords
        return False

    for n in tree.body:
        if isinstance(n, ast.Import):
            if any(a.name not in {"json", "ast"} or a.asname for a in n.names):
                return False
            modules.update(a.name for a in n.names)
        elif isinstance(n, ast.Assign):
            if not expr(n.value) or any(not isinstance(t, ast.Name) or t.id in reserved | modules for t in n.targets):
                return False
            bound.update(t.id for t in n.targets)
        elif not isinstance(n, ast.Expr) or not expr(n.value):
            return False
    return bool(tree.body)


def _options(args: list[str], flags=(), values=(), *, minimum=0, maximum=None) -> bool:
    """Bounded CLI grammar: unknown switches/option values are not certified."""
    operands, i, literal = 0, 0, False
    while i < len(args):
        token = args[i]
        if not literal and token == "--":
            literal = True
        elif not literal and token.startswith("-") and token != "-":
            option, equals, value = token.partition("=")
            if option in values:
                if not equals:
                    i += 1
                    if i >= len(args) or args[i].startswith("-"):
                        return False
                elif not value:
                    return False
            elif token not in flags:
                return False
        else:
            operands += 1
        i += 1
    return operands >= minimum and (maximum is None or operands <= maximum)


def investigation(args: list[str]) -> bool:
    """Approved diagnostic execution, NOT a proof of side-effect-free code.

    Only bounded diagnostic forms qualify. Test modules/plugins and compilers
    can execute code or write files and require a separately scoped runner;
    their executable names alone are not investigation authority.
    """
    if not args:
        return False
    cmd, rest = args[0], args[1:]
    # Test modules and plugins execute arbitrary project code; py_compile writes
    # bytecode. A command-line selection is not a scoped execution authority.
    if cmd == "pytest" or cmd in {"python", "python3"} and rest[:1] == ["-m"]:
        return False
    if cmd in {"bash", "sh", "zsh", "dash", "ksh"}:
        return bool(rest) and rest[0] == "-n" and _options(rest[1:], minimum=1)
    if cmd == "shellcheck":
        return _options(rest, flags={"-x", "--external-sources", "--norc", "--check-sourced"}, values={"-s", "--shell", "-S", "--severity", "-f", "--format", "-e", "--exclude", "-i", "--include"}, minimum=1)
    if cmd == "ruff":
        return bool(rest) and rest[0] == "check" and _options(rest[1:], flags={"--no-fix", "--no-cache", "-q", "--quiet", "-v", "--verbose", "--statistics", "--diff"}, values={"--select", "--ignore", "--extend-select", "--extend-ignore", "--output-format"})
    if cmd in {"flake8", "mypy", "pylint"}:
        return _options(rest, flags={"-q", "--quiet", "-v", "--verbose", "--show-error-codes", "--strict", "--ignore-missing-imports"}, values={"--select", "--ignore", "--disable", "--enable", "--max-line-length"}, minimum=1)
    if cmd in {"black", "isort"}:
        checks = {"--check"} if cmd == "black" else {"--check", "--check-only"}
        return bool(set(rest) & checks) and _options(rest, flags=checks | {"--diff", "-q", "--quiet", "--no-cache"}, values={"--line-length"}, minimum=1)
    if cmd == "git":
        while len(rest) >= 2 and rest[0] == "-C":
            rest = rest[2:]
        return (bool(rest) and rest[0] == "fetch"
                and _options(rest[1:], flags={"--all", "--prune", "--tags", "--no-tags", "--dry-run", "-q", "--quiet", "-v", "--verbose", "--no-recurse-submodules"}, values={"--depth", "--deepen"}, maximum=1)
                and all(t.startswith('-') or re.fullmatch(r'[A-Za-z0-9_./-]+', t) for t in rest[1:]))  # no destination refspecs/helper URLs
    return False


def _long_option_matches(token: str, names) -> bool:
    """GNU accepts any unambiguous prefix of a long option (`--lin` is --link)."""
    name = token.split('=', 1)[0]
    return len(name) > 2 and any(full.startswith(name) for full in names)


def _cp_link_copy(tokens) -> bool:
    """cp -l/-s and their long forms make the destination another name (#1100)."""
    skip = False
    for t in tokens:
        if skip:
            skip = False
            continue
        if t == '--':
            break
        if t == '--suffix' or t.startswith('-') and not t.startswith('--') and t.find('S') == len(t) - 1:
            skip = True
        if t.startswith('--'):
            if _long_option_matches(t, ('--link', '--symbolic-link')):
                return True
        elif t.startswith('-') and t != '-' and any(c in t[1:].split('S', 1)[0] for c in 'ls'):
            return True
    return False


def _cp_option(token):
    """Modeled flags: c/reflink clone independent bytes; X omits metadata, not scope.

    Destination-changing forms stay separately rejected.
    """
    if token.startswith('--'):
        name, sep, value = token.partition('=')
        plain = {'--archive', '--recursive', '--dereference', '--no-dereference',
                 '--link', '--symbolic-link', '--force', '--interactive', '--no-clobber',
                 '--verbose', '--one-file-system', '--no-target-directory', '--backup'}
        valued = {'--suffix', '--preserve', '--no-preserve', '--reflink', '--sparse', '--backup'}
        if name not in plain | valued or sep and name not in valued:
            raise UnknownShape('unsupported copy option; use explicit source/destination and modeled flags')
    elif any(c not in 'abcdfHilLnpPRruvxTX' for c in token[1:].split('S', 1)[0]):
        raise UnknownShape('unsupported copy option; use explicit source/destination and modeled flags')


def _cp_symlink_mode(tokens):
    """Follow-all creates no symlink aliases; H follows only command-line links."""
    mode, recursive, skip = None, False, False
    for token in tokens:
        if skip:
            skip = False
            continue
        if token == '--':
            break
        if token == '--suffix' or token.startswith('-') and not token.startswith('--') and token.find('S') == len(token) - 1:
            skip = True
        if token.startswith('--'):
            name = token.split('=', 1)[0]
            if name in {'--archive', '--no-dereference'}:
                mode = 'P'
            elif name == '--dereference':
                mode = 'L'
            recursive |= name in {'--archive', '--recursive'}
        elif token.startswith('-'):
            for flag in token[1:].split('S', 1)[0]:
                if flag in 'aRr':
                    recursive = True
                if flag in 'ad':
                    mode = 'P'
                elif flag in 'HLP':
                    mode = flag
    return mode if mode is not None else ('P' if recursive else 'L')


def _copy_alias_targets(sources, options, cwd):
    """Preserved symlink endpoints are aliases; ordinary source entries are reads."""
    mode = _cp_symlink_mode(options)
    if mode == 'L':
        return []
    targets, seen, deadline = [], 0, time.monotonic() + 10
    def inspect(path):
        nonlocal seen
        seen += 1
        if seen > 100000 or time.monotonic() > deadline:
            raise UnknownShape('copy source alias inspection budget exceeded; split the copy or use cp -RL '
                               '(dereferences symlinks, changing preservation semantics); source reads need no write scope')
        try:
            link = stat.S_ISLNK(os.lstat(path).st_mode)
        except OSError as error:
            raise UnknownShape('cannot inspect preserved copy alias entry; source is not proven safe') from error
        if link:
            targets.append(canonical(path))
        return link
    def unreadable(error):
        raise UnknownShape('cannot inspect preserved copy aliases; use a readable source or explicit cp -RL') from error
    for source in sources:
        path = os.path.join(cwd, source)
        if mode != 'H' and inspect(path):
            continue  # preserving the root symlink copies no target descendants
        if os.path.isdir(path):
            for root, dirs, files in os.walk(path, onerror=unreadable, followlinks=False):
                for name in dirs + files:
                    inspect(os.path.join(root, name))
    return targets


def _copy_destinations(sources, destination, options, cwd):
    """Actual copied names plus bounded existing descendants, never just a parent."""
    raw = os.path.join(cwd, destination)
    options = options[:options.index('--')] if '--' in options else options
    no_directory = any((t.startswith('-') and not t.startswith('--') and 'T' in t[1:])
                       or _long_option_matches(t, ('--no-target-directory',)) for t in options)
    if any(_long_option_matches(t, ('--parents',)) for t in options if t.startswith('--')):
        raise UnknownShape('copy --parents needs explicit destination modeling; use explicit source/destination names')
    targets = [raw]
    if os.path.isdir(raw) and not no_directory:
        targets = [os.path.join(raw, os.path.basename(os.path.normpath(source))) for source in sources]
        # Recursive trailing-slash and /. semantics differ across cp versions.
        # Count the merge destination as well as the named child, conservatively.
        if any(source.endswith(('/', '/.', '/..')) for source in sources):
            targets.append(raw)
    directories = []
    result = []
    def unreadable(error):
        raise UnknownShape('cannot inspect existing copy destination') from error
    for target in targets:
        result.append(canonical(target))
        if os.path.isdir(target) and not os.path.islink(target):
            directories.append(canonical(target))
            for root, dirs, files in os.walk(target, onerror=unreadable, followlinks=False):
                for name in dirs + files:
                    child = os.path.join(root, name)
                    result.append(canonical(child))
                    if len(result) > 2000:
                        raise UnknownShape('copy destination inspection exceeds bounded scope; split the copy')
                    if os.path.isdir(child) and not os.path.islink(child):
                        directories.append(canonical(child))
    return result, directories


def _commit_write_operands(args):
    """Commit message files are input, not worktree mutation targets."""
    result = []
    i = 0
    while i < len(args):
        token = args[i]
        if token == '--':
            result.extend(args[i:])
            break
        if token in {'-F', '--file'}:
            if i + 1 >= len(args):
                raise UnknownShape('Git commit message option needs a file')
            i += 2
            continue
        if token.startswith('--file=') or token.startswith('-F') and len(token) > 2:
            i += 1
            continue
        result.append(token)
        i += 1
    return result


def _git_toplevel(directory: str) -> str:
    try:
        return canonical(subprocess.check_output(["git", "-C", directory, "rev-parse", "--show-toplevel"], text=True, stderr=subprocess.DEVNULL, timeout=3).strip())
    except (subprocess.SubprocessError, OSError):
        raise UnknownShape("cannot resolve repository toplevel for Git mutation")




def _git_bootstrap_read(arguments: list[str], config: tuple = (), *, git_dir: str | None = None):
    """Fixed read-only Git lookup without enclosing-repository configuration."""
    import tempfile
    try:
        with tempfile.TemporaryDirectory(prefix='git-bootstrap-read-') as scratch:
            neutral = os.path.realpath(scratch)
            environment = dict(os.environ)
            environment['GIT_CEILING_DIRECTORIES'] = os.path.dirname(neutral)
            if config:
                environment['GIT_CONFIG_COUNT'] = str(len(config))
                for index, (key, value) in enumerate(config):
                    environment['GIT_CONFIG_KEY_' + str(index)] = key
                    environment['GIT_CONFIG_VALUE_' + str(index)] = value
            context = ['--git-dir=' + git_dir] if git_dir is not None else []
            result = subprocess.run(['git', '-C', neutral, *context, *arguments], env=environment,
                                    capture_output=True, timeout=3)
    except (OSError, subprocess.SubprocessError) as error:
        raise UnknownShape('cannot inspect clone-equivalent Git configuration') from error
    if len(result.stdout) > 8192:
        raise UnknownShape('Git bootstrap lookup output exceeds bounded metadata')
    return result


def _git_clone_local_kind(source: str, cwd: str) -> str | None:
    """Git clone's two local-path searches, including gitfiles and suffixes.

    Repository candidates precede regular bundle candidates. Git's own bounded
    resolve-git-dir reader recognizes bare metadata and gitfile indirection;
    no candidate clone, transport or helper executes during this lookup.
    """
    base = os.path.abspath(os.path.join(cwd, source))
    for suffix in ('/.git', '', '.git/.git', '.git'):
        candidate = base + suffix
        if not (os.path.isdir(candidate) or os.path.isfile(candidate)):
            continue
        resolved = _git_bootstrap_read(['rev-parse', '--resolve-git-dir', candidate])
        if resolved.returncode == 0:
            if base != canonical(base):
                raise UnknownShape('Git clone local source has a symlink alias')
            return 'repository'
        if resolved.returncode not in {1, 128}:
            raise UnknownShape('cannot establish Git clone local metadata')
    for suffix in ('.bundle', ''):
        candidate = base + suffix
        if os.path.isfile(candidate):
            if candidate != canonical(candidate):
                raise UnknownShape('Git clone local bundle has a symlink alias')
            return 'bundle'
    return None


def _git_clone_conditional_transport() -> bool:
    """Discover potentially relevant transport includes; Git evaluates their conditions.

    Read inactive include files as data only, using Git's own config/path parser.
    No glob matching is implemented here: when a gitdir include can affect the
    selected remote or its URL, the lookup uses the exact destination context.
    """
    pattern = r'^(include\.path|includeif\..*\.path|url\..*\.insteadof|remote\..*\.(url|vcs)|clone\.defaultremotename)$'
    visited = set()

    def inspect(path=None, conditional=False, depth=0):
        if depth > 10 or len(visited) > 64:
            raise UnknownShape('Git clone conditional configuration exceeds bounded inspection')
        if path is not None:
            identity = (path, conditional)
            if identity in visited or not os.path.exists(path):
                return False
            visited.add(identity)
        args = ['config', *(['--file', path] if path is not None else []),
                '--null', '--path', '--no-includes', '--show-origin', '--get-regexp', pattern]
        result = _git_bootstrap_read(args)
        if result.returncode not in {0, 1}:
            raise UnknownShape('cannot inspect Git clone conditional URL configuration')
        fields = result.stdout.split(b'\0')
        if fields[-1] != b'' or (len(fields) - 1) % 2:
            raise UnknownShape('unsupported Git clone configuration records')
        for index in range(0, len(fields) - 1, 2):
            origin, record = fields[index:index + 2]
            key, separator, value = record.partition(b'\n')
            if not separator:
                raise UnknownShape('unsupported Git clone configuration value')
            if key.startswith((b'url.', b'remote.')) or key == b'clone.defaultremotename':
                if conditional:
                    return True
                continue
            if not origin.startswith(b'file:'):
                raise UnknownShape('unsupported Git clone include origin')
            include = os.fsdecode(value)
            if not os.path.isabs(include):
                include = os.path.join(os.path.dirname(os.fsdecode(origin[5:])), include)
            gitdir = key.startswith((b'includeif.gitdir:', b'includeif.gitdir/i:'))
            if inspect(os.path.abspath(include), conditional or gitdir, depth + 1):
                return True
        return False

    return inspect()


def _git_clone_config_value(key: str, git_dir: str | None, config: tuple = ()) -> bytes | None:
    if git_dir is None:
        result = _git_bootstrap_read(['config', '--get', key], config)
        if result.returncode not in {0, 1}:
            raise UnknownShape('cannot inspect Git clone transport configuration')
        return (result.stdout[:-1] if result.stdout.endswith(b'\n') else result.stdout) if result.returncode == 0 else None
    # Unlike the config builtin, var initializes the explicit destination Git
    # context even before metadata exists. Capture only; never log user config
    # or identity values. This retains the existing trusted-user-config boundary
    # (including user hooks/SSH commands), rather than claiming a sandbox.
    result = _git_bootstrap_read(['var', '-l'], config, git_dir=git_dir)
    if result.returncode:
        raise UnknownShape('cannot inspect destination Git clone transport configuration')
    prefix = key.encode('utf-8') + b'='
    values = [line[len(prefix):] for line in result.stdout.split(b'\n') if line.startswith(prefix)]
    return values[-1] if values else None


def _git_clone_effective_source(source: str, *, git_dir: str | None = None) -> str:
    # Clone assigns its literal repository argument to the new remote; it does
    # not interpret that argument as a remote name in the caller's repository.
    # An invocation-only remote URL models this assignment while retaining the
    # real system/global config ordering (including a configured default name).
    raw_name = _git_clone_config_value('clone.defaultremotename', git_dir)
    try:
        remote_name = raw_name.decode('utf-8') if raw_name is not None else 'origin'
    except UnicodeError as error:
        raise UnknownShape('unsupported Git clone remote name') from error
    valid = _git_bootstrap_read(['check-ref-format', 'refs/remotes/' + remote_name + '/probe'])
    if not remote_name or valid.returncode:
        raise UnknownShape('unsupported Git clone remote name')
    if _git_clone_config_value('remote.' + remote_name + '.vcs', git_dir,
                               (('remote.' + remote_name + '.url', source),)) is not None:
        raise UnknownShape('unsupported Git clone custom remote transport')
    resolved = _git_bootstrap_read(['ls-remote', '--get-url', '--', remote_name],
                                   (('remote.' + remote_name + '.url', source),), git_dir=git_dir)
    if resolved.returncode:
        raise UnknownShape('cannot resolve effective Git clone source')
    value = resolved.stdout[:-1] if resolved.stdout.endswith(b'\n') else resolved.stdout
    try:
        return value.decode('utf-8')
    except UnicodeError as error:
        raise UnknownShape('effective Git clone source is not supported UTF-8') from error


def _git_bootstrap_destination(operation: dict) -> str | None:
    """Bound fresh repository creation; all other Git mutations keep toplevel ownership.

    No candidate command executes here. Creation cannot borrow a containing
    repository, reinitialize existing metadata or redirect writes through options.
    """
    command, *args = operation['args']
    if command not in {'init', 'clone'}:
        return None
    if operation.get('config'):
        raise UnknownShape('Git bootstrap configuration overrides are unmodeled')
    redirecting = {'GIT_DIR', 'GIT_WORK_TREE', 'GIT_COMMON_DIR', 'GIT_INDEX_FILE',
                   'GIT_OBJECT_DIRECTORY', 'GIT_ALTERNATE_OBJECT_DIRECTORIES',
                   'GIT_CONFIG', 'GIT_CONFIG_PARAMETERS',
                   'GIT_CONFIG_COUNT', 'GIT_EXEC_PATH', 'GIT_SSH', 'GIT_SSH_COMMAND'}
    if any(name in os.environ for name in redirecting):
        raise UnknownShape('environment-dependent Git bootstrap targeting is unresolved')
    cwd = operation['cwd']
    if not os.path.isdir(cwd):
        raise UnknownShape('Git bootstrap cwd must already exist')
    flags = ({'-q', '--quiet', '--bare'} if command == 'init' else
             {'-q', '--quiet', '-v', '--verbose', '--bare', '--mirror', '--no-checkout',
              '--no-hardlinks', '--no-local', '--local', '--single-branch', '--no-single-branch', '--no-tags'})
    values = {'-b', '--initial-branch', '--template'} if command == 'init' else {'-b', '--branch', '--depth', '--template'}
    operands, seen_flags = [], set()
    empty_template = False
    i, terminated = 0, False
    while i < len(args):
        token = args[i]
        if not terminated and token == '--':
            terminated = True
        elif not terminated and token.startswith('-'):
            if token in flags:
                seen_flags.add(token)
            elif token in values or any(token.startswith(x + '=') for x in values if x.startswith('--')):
                if '=' in token:
                    option, value = token.split('=', 1)
                else:
                    option = token
                    i += 1
                    if i >= len(args):
                        raise UnknownShape('Git bootstrap option needs a value')
                    value = args[i]
                if option == '--template':
                    if value != '':
                        raise UnknownShape('Git bootstrap supports only an empty per-command --template= override')
                    empty_template = True
                elif not value or value.startswith('-') or (option == '--depth' and not re.fullmatch(r'[1-9][0-9]*', value)):
                    raise UnknownShape('invalid Git bootstrap option value')
            else:
                raise UnknownShape('unsupported Git bootstrap option: ' + token)
        else:
            operands.append(token)
        i += 1
    # A custom template may copy symlinked objects/refs and cause writes outside
    # the destination. An exact empty command override copies none, without
    # changing persistent configuration or requiring another authorization.
    if not empty_template:
        template = _git_bootstrap_read(['config', '--path', '--get', 'init.templateDir'])
        template_value = template.stdout[:-1] if template.stdout.endswith(b'\n') else template.stdout
        if template.returncode not in {0, 1} or template_value != b'' or 'GIT_TEMPLATE_DIR' in os.environ:
            raise UnknownShape('configured Git bootstrap template has unmodeled write aliases; use --template= for this invocation')
    if command == 'init':
        if len(operands) > 1:
            raise UnknownShape('Git init needs at most one explicit destination')
        destination = operands[0] if operands else '.'
    else:
        if len(operands) != 2:
            raise UnknownShape('Git clone needs an explicit source and destination')
        source, destination = operands
        if source.startswith('-') or not source:
            raise UnknownShape('invalid Git clone source')
        raw_kind = _git_clone_local_kind(source, cwd)
        independent = '--no-local' in seen_flags and '--local' not in seen_flags
        if raw_kind and '://' in source:
            raise UnknownShape('local Git source shadows a transport URL; use an explicit filesystem path with --no-local')
        if raw_kind == 'repository' and not independent:
            raise UnknownShape('local repository or gitfile clone needs unambiguous --no-local for independent objects')
        if raw_kind:
            # Git absolute_pathdup preserves the literal suffix/slashes, unlike
            # realpath/normpath. Resolve initial relative input in the real cwd,
            # before entering the neutral configuration lookup.
            clone_argument = source if os.path.isabs(source) else os.path.join(cwd, source)
        else:
            if ':' not in source:
                raise UnknownShape('Git clone source is neither a local candidate nor a transport')
            clone_argument = source
        git_dir = None
        if _git_clone_conditional_transport():
            target = os.path.abspath(os.path.join(cwd, destination))
            if target != canonical(target):
                raise UnknownShape('Git bootstrap destination has a symlink alias')
            if not os.path.isdir(target):
                raise UnknownShape('conditional Git clone URL lookup needs an existing empty destination; create that directory within the same Task scope, then retry')
            try:
                if os.listdir(target):
                    raise UnknownShape('Git clone requires an empty destination')
            except OSError as error:
                raise UnknownShape('cannot inspect Git clone destination') from error
            git_dir = target if seen_flags & {'--bare', '--mirror'} else os.path.join(target, '.git')
        source = _git_clone_effective_source(clone_argument, git_dir=git_dir)
        if not source or '\n' in source or '\r' in source or source.startswith('-'):
            raise UnknownShape('invalid effective Git clone source')
        effective_kind = _git_clone_local_kind(source, cwd)
        if effective_kind and '://' in source:
            raise UnknownShape('effective local Git source has ambiguous transport syntax; use an explicit filesystem path')
        if effective_kind == 'repository' and not independent:
            raise UnknownShape('effective local repository or gitfile needs unambiguous --no-local for independent objects')
        # Only built-in network transports or existing local inputs, never
        # remote helpers, file URLs, option-like sources or inferred targets.
        if effective_kind:
            pass  # The real local-path lookup precedes transport interpretation.
        elif '://' in source:
            from urllib.parse import urlsplit
            try:
                url = urlsplit(source)
                host, port = url.hostname, url.port
            except ValueError as error:
                raise UnknownShape('invalid Git clone URL') from error
            if (url.scheme not in {'https', 'ssh'} or not host or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9.-]*', host)
                    or not url.path or url.password or url.query or url.fragment
                    or url.username and not re.fullmatch(r'[A-Za-z0-9_][A-Za-z0-9_.-]*', url.username)):
                raise UnknownShape('unsupported Git clone transport')
        elif re.match(r'[^/]+:', source) and not os.path.isabs(source):
            if not re.fullmatch(r'[A-Za-z0-9_.-]+@[A-Za-z0-9_.-]+:[A-Za-z0-9_./-]+', source):
                raise UnknownShape('unsupported Git clone transport')
        else:
            raise UnknownShape('effective Git clone local source does not exist')
    if not destination or destination.startswith('-'):
        raise UnknownShape('invalid Git bootstrap destination')
    target = os.path.abspath(os.path.join(cwd, destination))
    if target != canonical(target):
        raise UnknownShape('Git bootstrap destination has a symlink alias')
    if not os.path.isdir(os.path.dirname(target)):
        raise UnknownShape('Git bootstrap destination parent must already exist')
    if os.path.lexists(target) and not os.path.isdir(target):
        raise UnknownShape('Git bootstrap destination must be a directory')
    if command == 'clone' or '--bare' in seen_flags:
        try:
            nonempty = os.path.isdir(target) and bool(os.listdir(target))
        except OSError as error:
            raise UnknownShape('cannot inspect Git bootstrap destination') from error
        if nonempty:
            raise UnknownShape('Git clone and bare init require an empty destination')
    else:
        # Ordinary nonempty project files are not overwritten by git init.
        # Existing metadata at this target is a separate mutation, not
        # bootstrap authority. An enclosing workspace does not own new .git.
        probe = target if os.path.isdir(target) else os.path.dirname(target)
        try:
            existing = subprocess.run(['git', '-C', probe, 'rev-parse', '--absolute-git-dir'],
                                      capture_output=True, timeout=3)
        except (OSError, subprocess.SubprocessError) as error:
            raise UnknownShape('cannot inspect Git bootstrap metadata') from error
        existing_value = existing.stdout[:-1] if existing.stdout.endswith(b'\n') else existing.stdout
        if existing.returncode == 0 and not existing_value:
            raise UnknownShape('cannot establish Git bootstrap metadata identity')
        existing_metadata = canonical(os.fsdecode(existing_value)) if existing.returncode == 0 else ''
        if existing_metadata in {target, os.path.join(target, '.git')} or os.path.lexists(os.path.join(target, '.git')):
            raise UnknownShape('Git init bootstrap cannot reinitialize existing repository metadata')
        if existing.returncode not in {0, 128}:
            raise UnknownShape('cannot establish absent Git bootstrap metadata')
    return target
# ssh contacts another machine and writes nothing local by itself, so it is
# gated by destination, not by the cwd (#1160). Only hosts on the operator-owned
# allowlist pass, and only with options whose effects stay remote. Anything
# else is denied even under a covering task gate: options that run or write
# locally (ProxyCommand, LocalCommand, -F, -E, -S/-M, forwards, -f) and ssh run
# through another path, an assignment or a command wrapper. The one wrapped
# form modeled is the bounded literal `timeout <N> ssh ...`. scp, rsync and
# sftp keep their local operands and are not handled here.
# Fixed canonical policy path beside the installed hook library; the final
# component is opened without following links (#1160).
SSH_ALLOWLIST = os.path.join(os.path.realpath(os.path.dirname(os.path.abspath(__file__))), "ssh-host-allowlist.json")
SSH_ALLOWLIST_MAX_BYTES = 4096
SSH_EXECUTABLES = {"ssh", "/usr/bin/ssh"}
_SSH_TIMEOUT = re.compile(r"[0-9]+(?:\.[0-9]+)?[smhd]?")  # GNU timeout DURATION
# Command wrappers and how to find the command each one runs: options that
# take a separate value, and positional words before the command. Only the
# wrapped executable is classified; other argument text is never searched.
_WRAPPER_VALUES = {
    "timeout": {"-k", "--kill-after", "-s", "--signal"},
    "gtimeout": {"-k", "--kill-after", "-s", "--signal"},
    "nohup": set(), "setsid": set(), "unbuffer": set(), "builtin": set(), "nocorrect": set(), "noglob": set(),
    "nice": {"-n", "--adjustment"},
    "time": {"-f", "--format", "-o", "--output"},
    "xargs": {"-a", "--arg-file", "-d", "--delimiter", "-E", "--eof", "-I", "--replace", "-L", "--max-lines",
              "-n", "--max-args", "-P", "--max-procs", "-s", "--max-chars"},
    "sudo": {"-u", "--user", "-g", "--group", "-h", "--host", "-p", "--prompt", "-C", "--close-from",
             "-R", "--chroot", "-D", "--chdir", "-T", "--command-timeout", "-r", "--role", "-t", "--type",
             "-U", "--other-user"},
    "doas": {"-u", "-C"},
    "stdbuf": {"-i", "--input", "-o", "--output", "-e", "--error"},
    "caffeinate": {"-t", "-w"},
    "watch": {"-n", "--interval", "-q", "--equexit"},
    "flock": {"-w", "--wait", "--timeout", "-E", "--conflict-exit-code"},
    "script": {"-t", "-T", "--log-timing", "-I", "--log-in", "-O", "--log-out", "-B", "--log-io", "-E", "--echo",
               "-m", "--logging-format", "-o", "--output-limit"},
    "ionice": {"-c", "--class", "-n", "--classdata"},
    "taskset": set(),
    "chrt": {"-T", "--sched-runtime", "-P", "--sched-period", "-D", "--sched-deadline"},
    "arch": {"-arch", "-e", "-d"},
    "env": {"-u", "--unset", "-C", "--chdir"},
    "command": set(),
    "exec": {"-a"},
}
_WRAPPER_POSITIONALS = {"timeout": 1, "gtimeout": 1, "taskset": 1, "chrt": 1, "flock": 1}
_WRAPPER_NO_COMMAND = {  # options after which the wrapper runs no command
    "command": {"-v", "-V"}, "ionice": {"-p", "--pid", "-P", "--pgid", "-u", "--uid"},
    "taskset": {"-p", "--pid"}, "chrt": {"-p", "--pid"}, "sudo": {"-e", "--edit", "-l", "--list", "-v", "--validate"},
}
_WRAPPER_STRINGS = {"env": {"-S", "--split-string"}, "flock": {"-c", "--command"}, "script": {"-c", "--command"}}
_SSH_LABEL = r"[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?"
_SSH_HOST = re.compile(_SSH_LABEL + r"(?:\." + _SSH_LABEL + r")*")
_SSH_LOGIN = re.compile(r"[A-Za-z0-9_][A-Za-z0-9_.-]*")
_SSH_FLAGS = set("46aCnqTtvx")  # no-value flags with no local effect
_SSH_VALUES = set("lop")         # -l login, -o option, -p port
_SSH_CONFIG = {  # -o keys whose effects stay remote, and their accepted values
    "batchmode": r"yes|no",
    "compression": r"yes|no",
    "connecttimeout": r"[0-9]{1,5}",
    "connectionattempts": r"[0-9]{1,3}",
    "serveraliveinterval": r"[0-9]{1,5}",
    "serveralivecountmax": r"[0-9]{1,3}",
    "loglevel": r"quiet|fatal|error|info|verbose|debug|debug1|debug2|debug3",
    "requesttty": r"yes|no|force|auto",
    "port": r"[0-9]{1,5}",
    "user": _SSH_LOGIN.pattern,
}


def _unique_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate key {key!r}")
        result[key] = value
    return result


def ssh_allowlist():
    """Allowed ssh hosts and the allowlist source. Any defect admits no host.

    The grant comes only from the fixed policy file itself: a symlink, a hard
    link, a FIFO or other non-regular file, an oversized file, duplicate or
    unknown keys, or a malformed host list all deny every host. The open is
    non-blocking, so a FIFO cannot stall the hook (#1160).
    """
    try:
        flags = os.O_RDONLY | os.O_NONBLOCK | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_CLOEXEC", 0)
        if os.path.islink(SSH_ALLOWLIST):
            raise ValueError("is a symbolic link; it must be the policy file itself")
        fd = os.open(SSH_ALLOWLIST, flags)  # O_NOFOLLOW still refuses a link swapped in after the check
        try:
            info = os.fstat(fd)  # inspect the opened descriptor before any read
            if not stat.S_ISREG(info.st_mode):
                raise ValueError("not a regular file")
            if info.st_nlink != 1:
                raise ValueError(f"has {info.st_nlink} hard links; it must have exactly one")
            if info.st_size > SSH_ALLOWLIST_MAX_BYTES:
                raise ValueError(f"larger than {SSH_ALLOWLIST_MAX_BYTES} bytes")
            raw = os.read(fd, SSH_ALLOWLIST_MAX_BYTES + 1)
        finally:
            os.close(fd)
        if len(raw) > SSH_ALLOWLIST_MAX_BYTES:
            raise ValueError(f"larger than {SSH_ALLOWLIST_MAX_BYTES} bytes")
        data = json.loads(raw.decode("utf-8"), object_pairs_hook=_unique_keys)
        if not isinstance(data, dict) or set(data) != {"hosts"}:
            raise ValueError('the policy must be exactly {"hosts": [...]}')
        hosts = data["hosts"]
        if not isinstance(hosts, list) or not all(isinstance(h, str) and _SSH_HOST.fullmatch(h) for h in hosts):
            raise ValueError('"hosts" must be a list of hostnames')
        return frozenset(h.lower() for h in hosts), SSH_ALLOWLIST
    # Broad on purpose. A defect surfaces as OSError (missing file, symlink),
    # ValueError (checks above, malformed JSON, bad UTF-8) or RecursionError
    # (deeply nested JSON inside the size cap; /usr/bin/python3 3.9.6 raises it
    # for a 4090-byte policy). Every one must deny all hosts, so the gate exits
    # 2 and names the reason.
    except Exception as exc:
        return frozenset(), f"{SSH_ALLOWLIST} (unusable: {exc})"


def _ssh_option(flag: str, value: str) -> None:
    if flag == "p" and re.fullmatch(r"[0-9]{1,5}", value):
        return
    if flag == "l" and _SSH_LOGIN.fullmatch(value):
        return
    if flag == "o":
        # ssh reads `-o` as one config line: `Key=Value` or `Key Value`.
        match = re.fullmatch(r"\s*([A-Za-z]+)(?:\s*=\s*|\s+)(\S+)\s*", value)
        if match and re.fullmatch(_SSH_CONFIG.get(match[1].lower(), r"(?!)"), match[2], re.IGNORECASE):
            return
        raise UnknownShape(f"ssh -o {value!r} is not allowed: only {', '.join(sorted(_SSH_CONFIG))} "
                           "with plain values stay remote (#1160)")
    raise UnknownShape(f"ssh -{flag} {value!r} is not a plain {'port' if flag == 'p' else 'login'} (#1160)")


def _ssh_host(destination: str) -> str:
    if destination.startswith("ssh://"):
        match = re.fullmatch(r"ssh://(?:([^@/?#]+)@)?([^@:/?#]+)(?::[0-9]{1,5})?/?", destination)
        user, host = (match[1], match[2]) if match else ("", "")
    else:
        user, _, host = destination.rpartition("@")  # ssh splits at the last @
    if not _SSH_HOST.fullmatch(host) or user and not re.fullmatch(r"[A-Za-z0-9_.@-]+", user):
        raise UnknownShape(f"ssh destination {destination!r} is not a plain [user@]host (#1160)")
    return host.lower()


def ssh_destination(args: list[str]) -> str:
    """Destination host of a literal `ssh` argv, or UnknownShape.

    Like ssh.c, options are parsed before the destination and again after it
    until `--` or the first other word; the rest is the remote command, which
    runs remotely and names no local target.
    """
    words, host, index, ended = args[1:], None, 0, False
    while index < len(words):
        word = words[index]
        if not ended and word == "--":
            ended = True
            index += 1
            if host is not None:
                break
            continue
        if not ended and word.startswith("-") and word != "-":
            position = 1
            while position < len(word):
                flag = word[position]
                if flag in _SSH_FLAGS:
                    position += 1
                    continue
                if flag not in _SSH_VALUES:
                    raise UnknownShape(f"ssh option -{flag} is not allowed: it has local effects or is not "
                                       "modeled by the mutation gate (#1160)")
                value = word[position + 1:]
                if not value:
                    index += 1
                    if index >= len(words):
                        raise UnknownShape(f"ssh option -{flag} is missing its value")
                    value = words[index]
                _ssh_option(flag, value)
                break
            index += 1
            continue
        if host is not None:
            break
        host = _ssh_host(word)
        index += 1
    if host is None:
        raise UnknownShape("ssh requires a literal destination host (#1160)")
    return host


def _command_string(text: str) -> list[str]:
    try:
        return shlex.split(text)
    except ValueError:
        return text.split()


_ENV_DYNAMIC_WORD = '__ccp_env_dynamic__'
_ENV_OPTIONAL_WORD = _ENV_DYNAMIC_WORD + 'optional_word__'


def _env_split_string(text):
    """Inspect GNU env -S argv without executing it or reading variable values."""
    args, word, quote, active, index = [], [], '', False, 0
    literal = False

    def emit_word():
        args.append(''.join(word) if literal else _ENV_OPTIONAL_WORD)
    escapes = {'f': '\f', 'n': '\n', 'r': '\r', 't': '\t', 'v': '\v',
               '#': '#', '$': '$', '"': '"', "'": "'", '\\': '\\'}
    while index < len(text):
        char = text[index]
        if char == '\\':
            if index + 1 == len(text):
                return None  # GNU env rejects incomplete escapes before execution.
            following = text[index + 1]
            if quote == "'" and following not in {"'", '\\'}:
                word.append(char); active = literal = True; index += 1
                continue
            if following == 'c':
                if quote == '"':
                    return None
                break
            if following == '_':
                if quote == '"':
                    word.append(' '); active = literal = True
                elif active:
                    emit_word(); word, active, literal = [], False, False
            elif following in escapes:
                word.append(escapes[following]); active = literal = True
            else:
                return None  # Unsupported GNU escapes execute no command.
            index += 2
            continue
        if char in {"'", '"'}:
            if not quote:
                quote, active, literal = char, True, True
            elif quote == char:
                quote = ''
            else:
                word.append(char); literal = True
        elif not quote and char in ' \t\r\n\v\f':
            if active:
                emit_word(); word, active, literal = [], False, False
        elif not quote and char == '#' and not active:
            break
        elif char == '$' and quote != "'":
            variable = re.match(r'\$\{[A-Za-z0-9_]+\}', text[index:])
            if variable is None:
                return None
            word.append(_ENV_DYNAMIC_WORD); active = True
            index += len(variable[0])
            continue
        else:
            word.append(char); active = literal = True
        index += 1
    if quote:
        return None
    if active:
        emit_word()
    return args


def _wrapped_command(args: list[str], *, preserve_shell=False):
    """Argv that a supported command wrapper runs: None when args[0] is not a
    wrapper, [] when the wrapper runs no command."""
    name = os.path.basename(args[0])
    if name not in _WRAPPER_VALUES:
        return None
    def command_string(text):
        # env -S splits argv; unlike flock/script/watch it does not run a shell.
        if preserve_shell and name in {'flock', 'script', 'watch'}:
            return ['sh', '-c', text]
        if preserve_shell and name == 'env':
            split = _env_split_string(text)
            return ['env'] + split if split is not None else None
        return _command_string(text)

    values, strings = _WRAPPER_VALUES[name], _WRAPPER_STRINGS.get(name, set())
    stops, exec_mode, index = _WRAPPER_NO_COMMAND.get(name, set()), False, 1
    while index < len(args):
        token = args[index]
        if token == "--":
            index += 1
            break
        if name in {"env", "sudo"} and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*=.*", token, re.S):
            index += 1
            continue
        if not token.startswith("-") or token == "-":
            break
        index += 1
        if token.startswith("--") or name == "arch":  # arch options are whole words (-x86_64, -arch NAME)
            option, equal, attached = token.partition("=")
            if option in stops:
                return []
            if option in strings:
                text = attached if equal else (args[index] if index < len(args) else "")
                split = command_string(text)
                return split + (args[index + (0 if equal else 1):] if name == "env" else []) if split is not None else []
            exec_mode = exec_mode or option == "--exec"
            if option in values and not equal:
                index += 1
            continue
        for position in range(1, len(token)):  # a short-option cluster such as -nu root or -oL
            option = "-" + token[position]
            rest = token[position + 1:]
            if option in stops:
                return []
            if option in strings:
                text = rest or (args[index] if index < len(args) else "")
                split = command_string(text)
                return split + (args[index + (0 if rest else 1):] if name == "env" else []) if split is not None else []
            exec_mode = exec_mode or (name == "watch" and option == "-x")
            if option in values:
                if not rest:
                    index += 1
                break
    index += _WRAPPER_POSITIONALS.get(name, 0) + (1 if name == "script" else 0)
    rest = args[index:]
    if rest and rest[0].partition("=")[0] in strings:  # flock FILE -c CMD, script FILE -c CMD
        option, equal, attached = rest[0].partition("=")
        split = command_string(attached if equal else (rest[1] if len(rest) > 1 else ""))
        return split if split is not None else []
    if name == "watch" and not exec_mode:  # watch runs its words as one sh -c string
        return command_string(" ".join(rest))
    return rest


def ssh_invocation(args: list[str]):
    """Host of a direct `ssh` command, None when argv does not run ssh.

    ssh run through another path, an environment assignment or a command
    wrapper cannot be host-checked here, so it is refused. The exception is
    the bounded literal `timeout <N> ssh ...`, which goes through the same
    argv model. A wrapper is unwrapped to the command it runs; an argument
    that merely names ssh (a service, a path) does not make a command ssh.
    """
    assignment = re.compile(r"[A-Za-z_][A-Za-z0-9_]*=.*", re.S)
    head = 0
    while head < len(args) and assignment.fullmatch(args[head]):
        head += 1
    if head >= len(args):
        return None
    word = args[head]
    if head == 0 and word in SSH_EXECUTABLES:
        return ssh_destination(args)
    if head == 0 and word == "timeout" and len(args) > 2 and _SSH_TIMEOUT.fullmatch(args[1]) \
            and args[2] in SSH_EXECUTABLES:
        return ssh_destination(args[2:])
    if word in SSH_EXECUTABLES or os.path.basename(word) == "ssh":
        raise UnknownShape("run ssh directly as `ssh` or /usr/bin/ssh, without environment assignments, "
                           "so its host can be checked against the ssh host allowlist (#1160)")
    command = args[head:]
    while True:
        command = _wrapped_command(command)
        while command and assignment.fullmatch(command[0]):
            command = command[1:]
        if not command:
            return None
        if os.path.basename(command[0]) == "ssh":
            raise UnknownShape("ssh behind a command wrapper cannot be host-checked; run ssh directly, "
                               "or as `timeout <N> ssh ...` (#1160)")


def reader(args: list[str]) -> bool:
    if not args:
        return False
    cmd, rest = args[0], args[1:]
    if cmd == "curl":
        # Reuse the shared exact diagnostic grammar when another segment has
        # effects; curl's version component contributes no guessed cwd write.
        return _released_read_classifier().simple_ok(args)
    if cmd in {"cat", "head", "tail", "less", "more", "wc", "file", "stat", "du", "df", "which", "readlink", "realpath", "md5", "sha256sum", "shasum", "xxd", "od", "hexdump", "ls", "cmp", "comm", "pwd", "dirname", "basename", "uname", "whoami", "id", "true", "false", "test", "[", "echo", "printenv"}:
        # xxd -r reverses into an output file; file -C compiles a database.
        if cmd == "xxd":
            return _options(rest, flags={"-a", "-b", "-e", "-p", "-ps", "-u", "-v"}, values={"-c", "-g", "-l", "-o", "-s"}, maximum=1)
        if cmd == "file" and any(a.startswith('--compile') or a.startswith('-') and not a.startswith('--') and 'C' in a for a in rest):
            return False
        if cmd in {"less", "more"}:  # interactive shell escapes / LESSOPEN
            return False
        return True
    if cmd == "hostname":
        return _options(rest, flags={"-f", "-s", "-d", "-i", "-I", "-a", "-A", "--fqdn", "--short", "--domain", "--ip-address", "--all-ip-addresses", "--all-fqdns", "--alias", "--help", "--version"}, maximum=0)
    if cmd == "type":
        return _options(rest, flags={"-a", "-t", "-p", "-P", "-f"}, minimum=1)
    if cmd == "tree":
        return _options(rest, flags={"-a", "-d", "-f", "-i", "-l", "-n", "-N", "-q", "-p", "-u", "-g", "-s", "-h", "-D", "-F", "-t", "-r", "-U", "-C", "--noreport", "--dirsfirst"}, values={"-L", "-P", "-I", "--sort", "--filelimit"})
    if cmd == "markitdown":
        return _options(rest, flags={"--help", "--version"}, minimum=1, maximum=1)
    if cmd in {"pdf-tool", "xlsx-tool", "pptx-tool", "ical-tool"}:
        forms = {"pdf-tool": {"info", "extract"}, "xlsx-tool": {"read", "info"}, "pptx-tool": {"info"}, "ical-tool": {"read"}}
        return bool(rest) and rest[0] in forms[cmd] and _options(rest[1:], flags={"--json", "--text"}, values={"--pages", "--sheet", "--range"}, minimum=1, maximum=1)
    if cmd == "doc-diff":
        return _options(rest, flags={"--json"}, minimum=2, maximum=2)
    if cmd in {"npm", "yarn", "pnpm"}:
        if not rest or rest[0] not in {"list", "ls", "info", "view", "outdated", "audit"}:
            return False
        return _options(rest[1:], flags={"--json", "--global", "-g", "--all", "--long", "--parseable", "--production", "--dev"}, values={"--depth"}, maximum=0 if rest[0] == "audit" else None)
    if cmd in {"brew", "apt", "dnf", "yum"}:
        return bool(rest) and rest[0] in {"list", "info", "search", "show"} and _options(rest[1:], flags={"--versions", "--formula", "--cask", "--installed", "--available", "--pinned", "-l", "-1", "-r"})
    if cmd == "printf":
        fmt = rest[1] if len(rest) > 1 and rest[0] == '--' else rest[0] if rest else ''
        # Bash printf also assigns through -vNAME and the %n conversion.
        return not any(a.startswith('-v') for a in rest) and not re.search(r'%[^%a-zA-Z]*[hlLjztq]*n', fmt)
    if cmd == "date":
        flags = {'-u', '--utc', '--universal', '-j', '-R', '--rfc-email', '--rfc-2822', '--help', '--version', '--debug', '-I', '--iso-8601'}
        flags |= {'--iso-8601=' + unit for unit in ('date', 'hours', 'minutes', 'seconds', 'ns')}
        values = {'-d', '--date', '-r', '--reference', '-f', '--file'}
        if not _options(rest, flags=flags, values=values, maximum=2):
            return False
        i, literal = 0, False
        while i < len(rest):
            token = rest[i]
            if not literal and token == '--':
                literal = True
            elif not literal and token.partition('=')[0] in values:
                if '=' not in token:
                    i += 1
            elif not literal and token.startswith('-'):
                pass
            elif not token.startswith('+') and '-j' not in rest:
                return False  # bare dates can set the BSD clock
            i += 1
        return True
    if cmd == "env":
        return not rest  # env COMMAND executes; never certify that wrapper
    if cmd in {"grep", "egrep", "fgrep", "rg", "ag", "ack", "ripgrep"}:
        return not any(a.startswith(("--pre", "--hostname-bin", "--pager", "--output")) for a in rest)
    if cmd == "find":
        return not any(a in {"-exec", "-execdir", "-ok", "-okdir", "-delete", "-fprint", "-fprint0", "-fprintf", "-fls"} for a in rest)
    if cmd == "diff":
        return not any(a.startswith(("--output", "--from-file")) for a in rest)
    if cmd == "jq":
        return True
    if cmd == "sed":
        return len(rest) == 3 and rest[0] == "-n" and bool(re.fullmatch(r"\d+(,\d+)?p", rest[1])) and not rest[2].startswith("-")
    if cmd in {"python", "python3"}:
        return (_python_read(args) or len(rest) >= 3 and rest[:2] == ["-m", "pip"] and reader(["pip"] + rest[2:]))
    if cmd in {"pip", "pip3"}:
        if not rest or rest[0] not in {"list", "show", "freeze", "check"}:
            return False
        return _options(rest[1:], flags={"--all", "--outdated", "--uptodate", "--editable", "--local", "--user", "--not-required", "--include-editable", "--exclude-editable", "--pre", "--files", "-f", "-v", "--verbose", "-q", "--quiet", "--disable-pip-version-check", "--no-cache-dir"}, values={"--format", "--exclude", "--path"}, maximum=0 if rest[0] == "check" else None)
    if cmd == "git":
        while rest:
            if rest[0] == "--no-optional-locks":
                rest = rest[1:]  # Inert global flag, never a mutation exemption.
            elif rest[0] == "-C" and len(rest) >= 2:
                rest = rest[2:]
            else:
                break
        if not rest:
            return False
        sub, opts = rest[0], rest[1:]
        if sub == "diff-files":
            # Reuse the authoritative bounded grammar for companion mutations.
            return _released_read_classifier().git_ok(args[1:])
        if any(a.startswith(("--output", "--ext-diff", "--textconv", "--exec", "-o")) for a in opts):
            return False
        if sub == "reflog":
            return not any(a in {"expire", "delete", "drop", "write"} for a in opts)
        if sub in {"log", "status", "diff", "show", "rev-parse", "merge-base", "describe", "rev-list", "shortlog", "blame", "ls-tree", "ls-files", "cat-file", "name-rev", "for-each-ref"}:
            return True
        if sub == "branch":
            if opts == ["--show-current"]:
                return True
            list_flags = {"--list", "-l", "-v", "-vv", "--verbose", "-a", "--all", "-r", "--remotes"}
            return _options(opts, flags=list_flags, maximum=None if set(opts) & {"--list", "-l"} else 0)
        if sub == "tag":
            return not opts or opts[0] in {"--list", "-l"} and _options(opts, flags={"--list", "-l"})
        if sub == "remote":
            if not opts or opts in (["-v"], ["--verbose"]):
                return True
            if opts[0] == "show":
                return _options(opts[1:], flags={"-n", "--no-query"}, minimum=1, maximum=1)
            return opts[0] == "get-url" and _options(opts[1:], flags={"--push", "--all"}, minimum=1, maximum=1)
        if sub == "config":
            return bool(opts) and opts[0] in {"--get", "--get-all", "--get-regexp", "--list", "-l"} and not any(a.startswith(("--unset", "--add", "--replace", "--edit")) for a in opts)
        return sub in {"stash", "worktree"} and bool(opts) and opts[0] == "list"
    if cmd == "gh" and rest:
        if rest[0] == "api":
            return _released_read_classifier().gh_ok(rest)
        return len(rest) >= 2 and (rest[0], rest[1]) in {(x, y) for x in {"issue", "pr", "release", "run"} for y in {"view", "list", "checks", "diff", "status"}} | {("repo", "view")}
    return False


def canonical(path: str, cwd: str = "") -> str:
    return os.path.realpath(path if os.path.isabs(path) else os.path.join(cwd or os.getcwd(), path))


_RELEASED_READS = None


def _released_read_classifier():
    """Load the existing single released reader/operand grammar once."""
    global _RELEASED_READS
    if _RELEASED_READS is None:
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "read_only_command", os.path.join(os.path.dirname(os.path.abspath(__file__)), "read-only-command.py"))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        _RELEASED_READS = module
    return _RELEASED_READS


def released_read_verdict(command: str) -> int:
    """0 proven read, 3 write/exec veto, 1/4 unproven; one released grammar."""
    module = _released_read_classifier()
    try:
        return int(module.main(command))
    except Exception:
        return 1


def github_ticket_reference(body, number, repo, kind='fix', item='issues', *, source_repo=None):
    """Require an explicit relation in the independently read live PR body.

    Relative #N belongs to source_repo (the actual PR repository), never to a
    foreign target ticket repository. Explicit canonical cross-repository refs
    are valid. This pure parser grants no authority and performs no I/O.
    """
    if not isinstance(body, str) or len(body) > 65536:
        return False
    repo_pattern = r'[A-Za-z0-9][A-Za-z0-9-]*/[A-Za-z0-9_][A-Za-z0-9_.-]*'
    source_repo = repo if source_repo is None else source_repo
    if (type(number) is not int or number < 1 or not isinstance(repo, str)
            or not re.fullmatch(repo_pattern, repo) or not isinstance(source_repo, str)
            or not re.fullmatch(repo_pattern, source_repo)
            or kind not in {'fix', 'reference', 'supersede'} or item not in {'issues', 'pull'}):
        return False
    path = item
    relative = rf'\#{number}|' if source_repo.lower() == repo.lower() else ''
    target = rf'(?:{relative}{re.escape(repo)}\#{number}|https://github\.com/{re.escape(repo)}/{path}/{number})(?![0-9])'
    if kind == 'reference':
        verb = r'(?:refs?|references)[ \t]*:?'
    elif kind == 'fix':
        verb = r'(?:fix(?:es|ed)?|clos(?:es|ed)|resolv(?:es|ed))'
    else:
        verb = r'supersed(?:es|ed)(?:[ \t]+issue)?' if item == 'issues' else r'supersed(?:es|ed)(?:[ \t]+PR)?'
    # Whole declaration clauses only, rather than a substring in a quotation,
    # conditional, negation or example. Relative references retain their source repository.
    fence = None; hypothetical = False; quote = False
    for raw in body.splitlines():
        line = raw.strip()
        marker = re.match(r'(`{3,}|~{3,})', line)
        if marker:
            if not fence:
                fence = (marker[1][0], len(marker[1]))
            elif marker[1][0] == fence[0] and len(marker[1]) >= fence[1] and not line[marker.end():].strip():
                fence = None
            continue
        if not line:
            quote = False
            continue
        if line.startswith('>'):
            quote = True
            continue
        if fence or quote or raw.startswith(('    ', '\t')):
            continue
        if re.match(r'#{1,6}\s', line):
            hypothetical = bool(re.search(r'\b(example|hypothetical|scenario|conditional)\b', line, re.I))
            continue
        if re.match(r'(?:example|hypothetical|scenario|conditional)\s*:', line, re.I):
            hypothetical = True
            continue
        if hypothetical:
            continue
        for clause in re.split(r'\.[ \t]+', line):
            if kind != 'reference':
                if re.fullmatch(rf'{verb}[ \t]+{target}[.!]?', clause.strip(), re.I):
                    return True
                continue
            declaration = re.fullmatch(rf'{verb}[ \t]+(.+?)[.!]?', clause.strip(), re.I)
            if not declaration:
                continue
            refs = [value.strip() for value in declaration[1].split(',')]
            canonical = rf'(?:\#[1-9][0-9]*|{repo_pattern}\#[1-9][0-9]*|https://github\.com/{repo_pattern}/issues/[1-9][0-9]*)'
            if all(re.fullmatch(canonical, value) for value in refs) and any(re.fullmatch(target, value, re.I) for value in refs):
                return True
    return False


class GraphQLDocument:
    """Bounded GraphQL executable subset; no schema or program execution."""
    def __init__(self, text):
        if not isinstance(text, str):
            raise UnknownShape('One literal GraphQL query field is required')
        try:
            size = len(text.encode('utf-8'))
        except UnicodeError as error:
            raise UnknownShape('GraphQL document must be valid UTF-8') from error
        if size > 65536:
            raise UnknownShape('GraphQL document exceeds the supported bound')
        pattern = re.compile(r'\s+|#[^\r\n]*|"(?:[^"\\\r\n]|\\["\\/bfnrt]|\\u[0-9a-fA-F]{4})*"|-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?|[_A-Za-z][_0-9A-Za-z]*|[$!():{},\[\]=]')
        self.tokens, end = [], 0
        for match in pattern.finditer(text):
            if match.start() != end:
                raise UnknownShape('Unsupported GraphQL syntax; use one literal query or bounded review mutation')
            word = match.group(); end = match.end()
            if not word.isspace() and not word.startswith('#') and word != ',':
                self.tokens.append(word)
        if end != len(text) or len(self.tokens) > 4096:
            raise UnknownShape('Malformed or over-bound GraphQL document')
        self.index, self.depth = 0, 0
        self.variables = {}
        self.used = set()

    def peek(self):
        return self.tokens[self.index] if self.index < len(self.tokens) else ''

    def take(self, expected=None):
        word = self.peek()
        if not word or expected is not None and word != expected:
            raise UnknownShape('Malformed GraphQL document')
        self.index += 1
        return word

    def name(self):
        word = self.take()
        if not re.fullmatch(r'[_A-Za-z][_0-9A-Za-z]*', word):
            raise UnknownShape('GraphQL name required')
        return word

    def value(self):
        self.depth += 1
        if self.depth > 32:
            raise UnknownShape('GraphQL nesting exceeds bound')
        try:
            word = self.peek()
            if word == '$':
                self.take(); name = self.name(); self.used.add(name)
                return ('variable', name)
            if word == '{':
                self.take(); result = {}
                while self.peek() != '}':
                    key = self.name(); self.take(':')
                    if key in result:
                        raise UnknownShape('Duplicate GraphQL input field')
                    result[key] = self.value()
                self.take('}'); return result
            if word == '[':
                self.take(); result = []
                while self.peek() != ']': result.append(self.value())
                self.take(']'); return result
            self.take()
            if word.startswith('"'):
                return json.loads(word)
            if re.fullmatch(r'-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?', word):
                return json.loads(word)
            if word in {'true', 'false', 'null'}: return json.loads(word)
            if re.fullmatch(r'[_A-Za-z][_0-9A-Za-z]*', word): return ('enum', word)
            raise UnknownShape('Unsupported GraphQL value')
        finally:
            self.depth -= 1

    def arguments(self):
        values = {}
        if self.peek() != '(': return values
        self.take('(')
        while self.peek() != ')':
            key = self.name(); self.take(':')
            if key in values: raise UnknownShape('Duplicate GraphQL argument')
            values[key] = self.value()
        self.take(')'); return values

    def selection(self):
        self.depth += 1
        if self.depth > 32: raise UnknownShape('GraphQL selection exceeds bound')
        try:
            self.take('{'); fields = []
            while self.peek() != '}':
                name = self.name()
                if self.peek() == ':': self.take(':'); name = self.name()
                arguments = self.arguments()
                children = self.selection() if self.peek() == '{' else []
                fields.append((name, arguments, children))
            self.take('}')
            if not fields: raise UnknownShape('Empty GraphQL selection')
            return fields
        finally:
            self.depth -= 1

    def parse(self):
        kind = 'query'
        if self.peek() != '{':
            kind = self.name()
            if kind not in {'query', 'mutation'}:
                raise UnknownShape('Only one GraphQL query or modeled mutation is supported')
            if self.peek() not in {'(', '{'}: self.name()
            if self.peek() == '(':
                self.take('(')
                while self.peek() != ')':
                    self.take('$'); name = self.name(); self.take(':'); typ = self.name()
                    if self.peek() == '!': typ += self.take('!')
                    if name in self.variables: raise UnknownShape('Duplicate GraphQL variable')
                    self.variables[name] = typ
                self.take(')')
        fields = self.selection()
        if self.peek(): raise UnknownShape('Exactly one GraphQL operation required; fragments/directives are unsupported')
        if not self.used <= self.variables.keys(): raise UnknownShape('Undeclared GraphQL variable')
        return kind, fields


def github_graphql(args):
    """Literal transport only. Mutable --input documents cannot prove read scope."""
    if args[:3] != ['gh', 'api', 'graphql']: return None
    fields, index, method, seen = {}, 3, 'POST', set()
    while index < len(args):
        flag = args[index]; index += 1
        if flag not in {'-f', '--raw-field', '-F', '--field', '-q', '--jq', '-X', '--method', '--hostname'} or index >= len(args):
            raise UnknownShape('Unsupported GraphQL transport; use literal -f query=... and -f/-F variables, not --input or executable wrappers')
        value = args[index]; index += 1
        if flag in {'-q', '--jq', '-X', '--method', '--hostname'}:
            key = {'-q': 'jq', '--jq': 'jq', '-X': 'method', '--method': 'method', '--hostname': 'host'}[flag]
            if key in seen: raise UnknownShape('Duplicate GraphQL transport option')
            seen.add(key)
            if key == 'method': method = value
            if key == 'host' and value != 'github.com': raise UnknownShape('GraphQL host must be github.com')
            continue
        key, equal, value = value.partition('=')
        if not equal or not re.fullmatch(r'[_A-Za-z][_0-9A-Za-z]*', key) or key in fields:
            raise UnknownShape('One literal value per GraphQL field required')
        if flag in {'-F', '--field'}:
            if value.startswith('@'): raise UnknownShape('GraphQL file-valued fields are unsupported; use literal values')
            if value in {'true', 'false', 'null'} or re.fullmatch(r'-?(?:0|[1-9][0-9]*)', value): value = json.loads(value)
        fields[key] = value
    if method not in {'GET', 'POST'}: raise UnknownShape('Unsupported GraphQL method')
    document = GraphQLDocument(fields.pop('query', None)); kind, selections = document.parse()
    if set(fields) != set(document.variables): raise UnknownShape('GraphQL variables must match the declared operation exactly')
    if kind == 'query': return {'kind': 'query'}
    if method != 'POST': raise UnknownShape('GraphQL review mutation requires POST')
    if len(selections) != 1 or selections[0][0] != 'resolveReviewThread':
        return {'kind': 'other-mutation', 'fields': [x[0] for x in selections]}
    _, arguments, children = selections[0]
    if set(arguments) != {'input'} or not isinstance(arguments['input'], dict) or set(arguments['input']) != {'threadId'}:
        raise UnknownShape('Review resolution requires only input.threadId')
    thread = arguments['input']['threadId']
    if isinstance(thread, tuple) and thread[0] == 'variable':
        if document.variables.get(thread[1]) != 'ID!': raise UnknownShape('Review thread variable must be ID!')
        thread = fields[thread[1]]
    if not isinstance(thread, str) or not re.fullmatch(r'PRRT_[A-Za-z0-9_-]+', thread):
        raise UnknownShape('Literal review-thread ID required')
    # Response selection is data-only, but keep the modeled shape explicit.
    if not children or any(x[0] not in {'thread', 'clientMutationId'} for x in children):
        raise UnknownShape('Unsupported review mutation result selection')
    return {'kind': 'resolve-review-thread', 'thread_id': thread}


def action(command: str, cwd: str) -> dict:
    """Classify before gate lookup, and conservatively collect mutation targets."""
    verdict = released_read_verdict(command)
    if verdict == 0:
        return {"read_only": True, "investigation": False, "self_management": False, "paths": [],
                "binding": "", "proven_by": "read-only-command"}
    result = _action(command, cwd)
    if verdict == 3:
        # A veto is never a read or an investigation, whatever the local reader
        # thinks; the targets found below still pick the owning task's gate.
        result.update(read_only=False, investigation=False, self_management=False,
                      veto="read-only-command: option writes or runs a program")
        result["paths"] = result.get("paths") or ([] if result.get("metadata_only") or result.get('remote_actions') or result.get('review_actions') or result.get('metadata_posts') or result.get('remote_contact_only') else [canonical(cwd)])
        # A vetoed command writes or runs a program: its cwd is unknown writes (#1152).
        result["fallback_paths"] = list(dict.fromkeys(list(result.get("fallback_paths") or []) + [canonical(cwd)]))
    return result


TEST_RECEIPT_READER_SHA256 = 'e7381f43669d846112fda4028a0fbdc351927fdefe6668431acc77f39578cb69'

SCANNER_CAPABILITY_SHA256 = '9be4696157fdafbf8646ff3545375db6bb792f0bd99ecf10041134a822ea7908'
SCANNER_ADAPTER_SHA256 = 'df44acc0800577539abcf2d66097c76936036f3949dfa3567925c47f0ec62b9e'

def _scanner_code(path, expected):
    import hashlib
    if not path.is_absolute() or os.path.realpath(path) != str(path):
        raise ValueError('scanner code cannot use symlink aliases')
    fd = os.open(path,os.O_RDONLY|os.O_NONBLOCK|getattr(os,'O_NOFOLLOW',0))
    with os.fdopen(fd,'rb') as source:
        info=os.fstat(source.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_size > 1024*1024:
            raise ValueError('scanner code must be bounded and singly linked')
        raw=source.read(1024*1024+1)
    if hashlib.sha256(raw).hexdigest() != expected:
        raise ValueError('installed scanner code differs: '+str(path))
    return raw

def _scanner_module(root):
    import types
    path = root/'hooks/lib/scanner_capability.py'
    raw = _scanner_code(path,SCANNER_CAPABILITY_SHA256)
    module=types.ModuleType('verified_scanner_capability');module.__file__=str(path)
    exec(compile(raw,str(path),'exec'),module.__dict__)
    return module

def scanner_owned_plan(plan, gate_path, gate_data, session):
    return _scanner_module(Path(plan['scanner_root'])).owned_plan(plan,gate_path,gate_data,session)

def _scanner_execution(tokens, cwd: str):
    words = [word for word, _, _ in tokens]
    invocation = list(words)
    while invocation and invocation[0].startswith('CCP_TASK_ID='):
        invocation.pop(0)
    script = 1
    while script < len(invocation) and invocation[script] in {'-I','-B'}:
        script += 1
    candidate = bool(invocation) and (os.path.basename(invocation[0]) == 'scanner-exec.py' or
                os.path.basename(invocation[0]) in {'python','python3'} and script < len(invocation)
                and os.path.basename(invocation[script]) == 'scanner-exec.py')
    if not candidate:
        return None
    if any(operator or glob for _, operator, glob in tokens):
        raise UnknownShape('scanner requires one literal argv command')
    binding = ''
    while words and words[0].startswith('CCP_TASK_ID='):
        value = words.pop(0).split('=',1)[1]
        if binding and binding != value: raise UnknownShape('conflicting scanner Task bindings')
        binding = value
    if len(words) < 4 or words[0] != 'python3' or words[1:3] != ['-I','-B']:
        raise UnknownShape('scanner requires python3 -I -B and the installed entry')
    try:
        root = Path(__file__).resolve().parents[2]
        import importlib.util
        spec = importlib.util.spec_from_file_location('scanner_registration',str(Path(__file__).with_name('craft-settings-router.py')))
        router = importlib.util.module_from_spec(spec); spec.loader.exec_module(router)
        payload = json.loads(os.environ.get('CCP_HOOK_INPUT_JSON') or '{}')
        provider = router.registered_test_provider(os.environ,payload)
        if provider is not None: root = Path(provider).parents[2]
        producer = root/'hooks/lib/scanner-exec.py'
        if words[3] != str(producer): raise ValueError('scanner requires the exact selected installed entry')
        _scanner_code(producer,SCANNER_ADAPTER_SHA256)
        policy = _scanner_module(root)
        plan = policy.validate_files(policy.parse_arguments(words[4:]),producer)
        return {'read_only':False,'investigation':False,'self_managed_shape':False,
                'paths':[plan['repo'],plan['tmp'],*([plan['message']] if plan['message'] else []),*([plan['index']] if plan.get('index') else []),*([plan['log_dir']] if plan.get('log_dir') else [])],
                'binding':binding,'scanner_execution':plan}
    except (OSError,ValueError,subprocess.SubprocessError) as error:
        raise UnknownShape('scanner execution denied: '+str(error)) from error


def _test_receipt_record(tokens, cwd: str):
    """Typed selected-provider operations, with isolated check/sources readers.

    Record test argv remains opaque computation, never an own-scratch reader;
    repository-wide implementing authority and receipt ownership are checked
    after task selection. Diagnostic reads do not establish publication authority.
    """
    words = [word for word, _, _ in tokens]
    invocation = list(words)
    while invocation and invocation[0].startswith("CCP_TASK_ID="):
        invocation.pop(0)
    script = 1
    while script < len(invocation) and invocation[script] in {"-I", "-B"}:
        script += 1
    python = bool(invocation) and (os.path.basename(invocation[0]) in {"python", "python3"}
                                   or os.path.isabs(invocation[0]) and os.path.realpath(invocation[0]) == os.path.realpath(sys.executable))
    executable_producer = bool(invocation) and os.path.basename(invocation[0]) == "test-evidence.py"
    script_producer = python and script < len(invocation) and os.path.basename(invocation[script]) == "test-evidence.py"
    option_names = {word.partition("=")[0] for word in words}
    candidate = executable_producer or script_producer or (
        python and "record" in words and {"--think-gate", "--output", "--repo"} <= option_names)
    if not candidate:
        return None
    if any("\0" in word for word in words) or any(operator or glob for _, operator, glob in tokens):
        raise UnknownShape("test receipt producer requires one literal argv command")
    binding = ""
    while words and words[0].startswith("CCP_TASK_ID="):
        value = words.pop(0).split("=", 1)[1]
        if binding and value != binding:
            raise UnknownShape("conflicting test receipt task bindings")
        binding = value
    if not words or not (words[0] == "python3" or os.path.isabs(words[0]) and
                          os.path.realpath(words[0]) == os.path.realpath(sys.executable)):
        raise UnknownShape("test receipts require the known Python interpreter and packaged producer")
    index = 1
    while index < len(words) and words[index] in {"-I", "-B"}:
        index += 1
    owned = os.path.join(os.path.realpath(os.path.dirname(__file__)), "test-evidence.py")
    # Both registered host and project stacks must select the same pinned
    # provider. An unregistered context keeps its exact local producer.
    import importlib.util
    provider_module = os.path.join(os.path.dirname(__file__), 'craft-settings-router.py')
    spec = importlib.util.spec_from_file_location('receipt_provider_registration', provider_module)
    module = importlib.util.module_from_spec(spec)
    sys.dont_write_bytecode = True
    spec.loader.exec_module(module)
    try:
        payload = json.loads(os.environ.get('CCP_HOOK_INPUT_JSON') or '{}')
        if not isinstance(payload, dict):
            raise ValueError('hook metadata must be an object')
        registered = module.registered_test_provider(os.environ, payload)
    except (OSError, ValueError, TypeError) as error:
        raise UnknownShape('cannot verify the registered test receipt provider: ' + str(error)) from error
    if registered is not None:
        owned = str(registered)
    if index >= len(words) or os.path.abspath(os.path.join(cwd, words[index])) != owned:
        raise UnknownShape('use the exact selected test receipt provider: ' + owned)
    if os.path.realpath(owned) != owned:
        raise UnknownShape("test receipt producer cannot be a symlink")
    try:
        info = os.stat(owned, follow_symlinks=False)
    except OSError as error:
        raise UnknownShape("this policy generation's test receipt producer is unavailable") from error
    if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
        raise UnknownShape("test receipt producer must be an owned regular singly linked file")
    index += 1
    if words[index:index + 1] in (["check"], ["sources"]):
        if set(words[1:3]) != {'-I', '-B'} or index != 4:
            raise UnknownShape('test receipt reads require the known Python with unique -I and -B')
        try:
            _scanner_code(Path(owned), TEST_RECEIPT_READER_SHA256)
        except (OSError, ValueError) as error:
            raise UnknownShape('selected test receipt provider is not the qualified read version; upgrade normally') from error
        import shutil
        interpreter = shutil.which(words[0]) if words[0] == 'python3' else words[0]
        if not interpreter or os.path.realpath(interpreter) != os.path.realpath(sys.executable):
            raise UnknownShape('test receipt reader interpreter differs from the policy interpreter')
        mode = words[index]
        fields = {}
        report_only = False
        index += 1
        allowed = {'--repo', '--base', '--receipt'} if mode == 'check' else {'--repo', '--base'}
        while index < len(words):
            flag = words[index]
            if flag == '--report-only' and mode == 'check' and not report_only:
                report_only = True
                index += 1
                continue
            if flag not in allowed or flag in fields or index + 1 >= len(words):
                raise UnknownShape('test receipt reads require exact unique named fields')
            value = words[index + 1]
            if not value or value.startswith('-'):
                raise UnknownShape('test receipt read field requires a literal value')
            fields[flag] = value
            index += 2
        if set(fields) != allowed or not re.fullmatch(r'(?:[0-9a-f]{40}|[0-9a-f]{64})', fields.get('--base', '')):
            raise UnknownShape('test receipt reads require a full canonical base object ID')
        repo = fields['--repo']
        if not os.path.isabs(repo) or canonical(repo) != os.path.abspath(repo):
            raise UnknownShape('test receipt read repo must be physical and absolute')
        environment = {key: value for key, value in os.environ.items() if not key.startswith('GIT_')}
        environment.update(GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM='1')
        try:
            top = subprocess.check_output(['/usr/bin/git', '-c', 'core.fsmonitor=false', '-c',
                                           'core.hooksPath=/dev/null', '-C', repo, 'rev-parse', '--show-toplevel'],
                                          env=environment, text=True, stderr=subprocess.DEVNULL, timeout=3).strip()
        except (OSError, subprocess.SubprocessError) as error:
            raise UnknownShape('cannot resolve test receipt read repository') from error
        if canonical(top) != repo:
            raise UnknownShape('test receipt read repo must be the physical Git root')
        if mode == 'check':
            receipt = fields['--receipt']
            if not os.path.isabs(receipt) or canonical(receipt) != os.path.abspath(receipt):
                raise UnknownShape('test receipt read path must be physical and absolute')
        return {'read_only': True, 'investigation': False, 'self_managed_shape': False,
                'paths': [], 'binding': binding, 'proven_by': 'fixed-test-receipt-' + mode}
    if words[index:index + 1] != ["record"]:
        raise UnknownShape("only the fixed test receipt record command has an execution lane")
    index += 1
    fields, sources = {}, []
    while index < len(words) and words[index] != "--":
        flag = words[index]
        if flag not in {"--repo", "--source", "--output", "--think-gate", "--framework"} or index + 1 >= len(words):
            raise UnknownShape("test receipt record requires exact named options and -- before test argv")
        value = words[index + 1]
        if not value or value.startswith("--"):
            raise UnknownShape("test receipt record option requires a nonempty literal value")
        if flag == "--source":
            if value.startswith("/") or any(part in {"", ".", ".."} for part in value.split("/")):
                raise UnknownShape("test receipt source must be an exact repository-relative path")
            sources.append(value)
        elif flag in fields:
            raise UnknownShape("duplicate test receipt option: " + flag)
        else:
            fields[flag] = value
        index += 2
    if set(fields) != {"--repo", "--output", "--think-gate", "--framework"} or not sources or len(set(sources)) != len(sources):
        raise UnknownShape("test receipt record requires repo, unique sources, framework, own think gate and output")
    if index >= len(words) or not words[index + 1:] or not words[index + 1]:
        raise UnknownShape("test receipt record requires actual test argv after --")
    for flag in ("--repo", "--output", "--think-gate"):
        if not os.path.isabs(fields[flag]):
            raise UnknownShape("test receipt paths must be explicit absolute paths")
    repo = fields["--repo"]
    if canonical(repo) != os.path.abspath(repo) or _git_toplevel(repo) != os.path.abspath(repo):
        raise UnknownShape("test receipt --repo must be the canonical target Git root")
    paths = [canonical(repo)] + [canonical(source, repo) for source in sources]
    if any(os.path.commonpath([path, paths[0]]) != paths[0] for path in paths):
        raise UnknownShape("test receipt source escapes the target repository")
    return {"read_only": False, "investigation": False, "self_managed_shape": False,
            "paths": list(dict.fromkeys(paths)), "binding": binding,
            "test_receipt_repo": paths[0], "test_receipt_gate": fields["--think-gate"],
            "test_receipt_output": fields["--output"]}


def _metadata_file(path: str, cwd: str):
    """Validate an inspectable body input without executing or reading unbounded data."""
    if path in {"", "-", "/dev/stdin", "/dev/fd/0", "/proc/self/fd/0"}:
        raise UnknownShape("metadata body file must be a readable regular file, not stdin")
    try:
        fd = os.open(canonical(path, cwd), os.O_RDONLY | os.O_NONBLOCK)
        try:
            info = os.fstat(fd)
            if not stat.S_ISREG(info.st_mode):
                raise UnknownShape("metadata body file must be a readable regular file")
        finally:
            os.close(fd)
    except (OSError, ValueError) as exc:
        raise UnknownShape("cannot read metadata body file: " + path) from exc


def github_review_reply(args, cwd: str):
    """Only a reply to an existing PR review comment, not comment creation APIs."""
    if args[:2] != ['gh', 'api'] or len(args) < 3: return None
    endpoint = args[2]
    match = re.fullmatch(r'repos/([A-Za-z0-9][A-Za-z0-9-]*/[A-Za-z0-9_.-]+)/pulls/([1-9][0-9]*)/comments/([1-9][0-9]*)/replies', endpoint)
    if not match: return None
    method, body, index, seen = None, None, 3, set()
    while index < len(args):
        flag = args[index]; index += 1
        if flag not in {'-X', '--method', '-f', '--raw-field', '-F', '--field', '-q', '--jq'} or index >= len(args):
            raise UnknownShape('Review reply supports only POST, one body field and optional literal --jq; --input is unsupported')
        value = args[index]; index += 1
        if flag in {'-q', '--jq'}:
            if 'jq' in seen: raise UnknownShape('Duplicate review reply output filter')
            seen.add('jq')
            continue
        if flag in {'-X', '--method'}:
            if method is not None: raise UnknownShape('Duplicate review reply method')
            method = value
        else:
            key, equal, value = value.partition('=')
            if not equal or key != 'body' or key in seen: raise UnknownShape('Review reply requires exactly one body field')
            seen.add(key); body = value
            if flag in {'-F', '--field'} and value.startswith('@'):
                _metadata_file(value[1:], cwd)
    if method not in {None, 'POST'} or body is None or not body:
        raise UnknownShape('Review reply requires explicit or body-implied POST and a nonempty body')
    return {'kind': 'reply-review-comment', 'repository': match[1], 'number': int(match[2]), 'comment_id': int(match[3])}


def github_metadata_target(args, cwd: str):
    """Existing artifact text edits only; no authorship or task authority claim."""
    if args[:1] != ["gh"]:
        return None
    fields, number, repo = {}, "", ""
    if args[1:2] == ["api"]:
        method, endpoint, i = "", "", 2
        while i < len(args):
            word = args[i]
            flag, equal, value = word.partition("=")
            if flag in {"-X", "--method", "-f", "--raw-field"}:
                if not equal:
                    i += 1
                    if i >= len(args):
                        return None
                    value = args[i]
                if flag in {"-X", "--method"}:
                    if method:
                        return None
                    method = value
                else:
                    key, sep, text = value.partition("=")
                    if not sep or key not in {"body", "title"} or key in fields:
                        return None
                    fields[key] = text
            elif not word.startswith("-") and not endpoint:
                endpoint = word
            else:
                return None
            i += 1
        match = re.fullmatch(r"repos/([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)/(issues|pulls)/(?:comments/)?([0-9]+)", endpoint)
        if method != "PATCH" or not match or not match[3].strip("0") or not fields:
            return None
        if "/comments/" in endpoint and set(fields) != {"body"}:
            return None
        repo = match[1]
    else:
        if args[1:2] not in (["pr"], ["issue"]) or args[2:3] not in (["edit"], ["comment"]):
            return None
        comment = args[2] == "comment"
        edit_last = False
        aliases = {"-R": "--repo", "-b": "--body", "-t": "--title", "-F": "--body-file"}
        i = 3
        while i < len(args):
            word = args[i]
            if word == "--edit-last" and comment and not edit_last:
                edit_last = True
                i += 1
                continue
            # A canonical GitHub artifact URL is itself an explicit remote target.
            url = re.fullmatch(r"https://github\.com/([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)/(pull|issues)/([0-9]+)", word)
            if url and not number and not repo and url[2] == ("pull" if args[1] == "pr" else "issues"):
                repo, number = url[1], url[3]
                i += 1
                continue
            if not word.startswith("-") and not number:
                # A URL for another host is not a branch selector. Git refs
                # cannot contain a colon or start with //; canonical GitHub
                # artifact URLs were handled above.
                if ":" in word or word.startswith("//"):
                    return None
                number = word  # Literal number/branch; gh resolves its remote selector.
                i += 1
                continue
            flag, equal, value = word.partition("=")
            flag = aliases.get(flag, flag)
            if flag not in {"--repo", "--body", "--title", "--body-file"} or flag in fields:
                return None
            if not equal:
                i += 1
                if i >= len(args):
                    return None
                value = args[i]
            fields[flag] = value
            i += 1
        if comment and (not edit_last or "--title" in fields) or not comment and edit_last:
            return None
        if "--repo" in fields and not fields["--repo"]:
            return None
        explicit = fields.pop("--repo", "")
        if repo and explicit and repo.lower() != explicit.lower():
            return None
        repo = repo or explicit
        if (not number and args[1] == "issue") or not fields or {"--body", "--body-file"} <= fields.keys():
            return None
        if "--body-file" in fields:
            _metadata_file(fields["--body-file"], cwd)
    if repo and (not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repo)
                 or any(x in {".", ".."} for x in repo.split("/"))):
        return None
    return repo.lower()


def github_project_action(args):
    """Literal typed project mutations; unsupported remote writes never become cwd writes."""
    if os.path.basename(args[0]) in {'timeout', 'nice', 'time'} and any(os.path.basename(word) == 'gh' for word in args[1:]):
        raise UnknownShape('Wrapped GitHub mutations are not modeled; use the literal scoped gh operation')
    if args[:1] != ['gh']:
        wrapped = os.path.basename(args[0]) == 'gh' or (
            re.match(r'[A-Za-z_][A-Za-z0-9_]*=', args[0]) and 'gh' in args[1:])
        if wrapped and any(word in {'project', 'api'} for word in args[1:]):
            raise UnknownShape('GitHub project operations require literal gh without executable aliases or environment prefixes')
        return None
    if args[1:2] == ['api']:
        raise UnknownShape('Unsupported GitHub API mutation requires explicit remote authority; GraphQL is not modeled')
    if args[1:2] != ['project']:
        if len(args) > 1 and args[1].startswith('-') and any(word in {'project', 'api'} for word in args[2:]):
            raise UnknownShape('GitHub project global options are not supported; use the literal scoped operation')
        return None
    if args[2:3] == ['item-edit']:
        names = {'--project-id':'project_id', '--id':'item_id', '--field-id':'field_id', '--single-select-option-id':'option_id'}
        if len(args) != 11:
            raise UnknownShape('GitHub project item-edit requires exactly project/item/field/single-select IDs')
        fields = {}
        for index in (3, 5, 7, 9):
            if args[index] not in names or names[args[index]] in fields or not re.fullmatch(r'[A-Za-z0-9_-]{1,200}', args[index + 1]):
                raise UnknownShape('GitHub project item-edit has unknown/duplicate flags or invalid literal IDs')
            fields[names[args[index]]] = args[index + 1]
        if len(fields) != 4:
            raise UnknownShape('GitHub project item-edit is missing a required ID')
        return dict(operation='item-edit', host='github.com', **fields)
    if args[2:3] != ['item-add']:
        raise UnknownShape('Unsupported GitHub project mutation; only task-owned item-add and verified Status item-edit are modeled')
    if len(args) not in {8, 10} or not re.fullmatch(r'[1-9][0-9]*', args[3]):
        raise UnknownShape('GitHub project item-add requires a literal project, --owner, --url and optional --format json')
    fields = {}
    for i in range(4, len(args), 2):
        if args[i] not in {'--owner', '--url', '--format'} or args[i] in fields:
            raise UnknownShape('GitHub project item-add has unknown or duplicate flags')
        fields[args[i]] = args[i + 1]
    if ('--owner' not in fields or '--url' not in fields
            or '--format' in fields and fields['--format'] != 'json'
            or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9-]*', fields['--owner'])):
        raise UnknownShape('GitHub project item-add requires an explicit owner and canonical issue URL')
    issue = re.fullmatch(r'https://github\.com/([A-Za-z0-9][A-Za-z0-9-]*)/([A-Za-z0-9_.-]+)/issues/([1-9][0-9]*)', fields['--url'])
    if not issue or issue[2] in {'.', '..'}:
        raise UnknownShape('GitHub project item-add requires a canonical https://github.com/owner/repository/issues/number target')
    return dict(operation='item-add', host='github.com', owner=fields['--owner'],
                project=int(args[3]), issue_owner=issue[1], repository=issue[2], issue=int(issue[3]))


def _literal_operand_family(args: list[str]) -> bool:
    """Known commands whose quoted glob characters are literal operand data.

    This changes target parsing only, never reader status or task authority.
    Git is excluded because its own pathspec language can expand quoted input.
    Unknown executable families retain the conservative operand check.
    """
    if args[0] in {'touch', 'mkdir', 'rm', 'rmdir', 'cp', 'mv', 'tee', 'chmod', 'chown'}:
        return True
    executable = args[0]
    name = os.path.basename(executable)
    if executable == 'pytest' or os.path.isabs(executable) and name == 'pytest':
        return True
    python = executable in {'python', 'python3'} or (os.path.isabs(executable)
             and re.fullmatch(r'python(?:3(?:\.[0-9]+)?)?', name) is not None)
    return python and args[1:3] == ['-m', 'pytest']


# gh command groups that call cli/cli cmdutil.EnableRepoOverride: there -R/--repo
# is a persistent `[HOST/]OWNER/REPO` repository selector, never a local path
# (#1347). gh never reads it as a path, so a same-named local directory is
# irrelevant. Extensions, other groups and absolute gh paths keep the generic model.
_GH_REPO_OVERRIDE_GROUPS = frozenset({'issue', 'pr', 'release', 'run', 'workflow', 'label',
                                      'secret', 'variable', 'cache', 'ruleset'})
_GH_REPO_SELECTOR = re.compile(r'(?:' + _SSH_HOST.pattern + r'/)?[A-Za-z0-9][A-Za-z0-9_-]*/(?!\.\.?$)[A-Za-z0-9_.-]+')


def _gh_repo_selector_width(args: list[str], i: int) -> int:
    """Tokens taken by a grammar-valid -R/--repo selector at args[i], else 0."""
    arg = args[i]
    if arg in ('-R', '--repo'):
        return 2 if i + 1 < len(args) and _GH_REPO_SELECTOR.fullmatch(args[i + 1]) else 0
    for prefix in ('--repo=', '-R=', '-R'):
        if arg.startswith(prefix):
            return 1 if _GH_REPO_SELECTOR.fullmatch(arg[len(prefix):]) else 0
    return 0


# Flag kinds for the gh subcommands whose complete flag set was read from
# cli/cli v2.104.0 pkg/cmd/<group>/<subcommand>/<subcommand>.go (#1355).
# 'text': a string gh sends to the API or keeps in memory, never a local file.
# 'path': a local file gh reads; it stays a target. 'bool': takes no value
# (pflag NoOptDefVal, including cmdutil.NilBoolFlag). Every other flag, every
# other subcommand and aliases such as `release new` are unknown and keep the
# conservative #1347 model. The table is pinned to that release: a flag added
# later is unknown (conservative), but a later change of a 'bool' flag to one
# that takes a value would need this table updated.
_GH_FLAG_KINDS = {
    ('issue', 'close'): {'-c': 'text', '--comment': 'text', '-r': 'text', '--reason': 'text',
                         '--duplicate-of': 'text'},
    ('issue', 'reopen'): {'-c': 'text', '--comment': 'text'},
    ('pr', 'close'): {'-c': 'text', '--comment': 'text', '-d': 'bool', '--delete-branch': 'bool'},
    ('pr', 'reopen'): {'-c': 'text', '--comment': 'text'},
    # '--admin' is listed for completeness against upstream only: any command
    # carrying it is never modelled (see _gh_path_scan_args).
    ('pr', 'merge'): {'--admin': 'bool', '-d': 'bool', '--delete-branch': 'bool', '-b': 'text', '--body': 'text',
                      '-F': 'path', '--body-file': 'path', '-t': 'text', '--subject': 'text',
                      '-m': 'bool', '--merge': 'bool', '-r': 'bool', '--rebase': 'bool', '-s': 'bool',
                      '--squash': 'bool', '--auto': 'bool', '--disable-auto': 'bool',
                      '--match-head-commit': 'text', '-A': 'text', '--author-email': 'text'},
    ('release', 'create'): {'-d': 'bool', '--draft': 'bool', '-p': 'bool', '--prerelease': 'bool',
                            '--target': 'text', '-t': 'text', '--title': 'text', '-n': 'text', '--notes': 'text',
                            '-F': 'path', '--notes-file': 'path', '--discussion-category': 'text',
                            '--generate-notes': 'bool', '--notes-start-tag': 'text', '--latest': 'bool',
                            '--verify-tag': 'bool', '--notes-from-tag': 'bool', '--fail-on-no-commits': 'bool'},
}
# gh's root command registers a persistent bool --help with no shorthand, so
# it never takes a value. A bare -h stays unknown (conservative).
_GH_HELP_FLAGS = {'--help': 'bool'}


def _gh_bare_option(arg: str) -> bool:
    """An option token that may take the next token as its value."""
    return arg.startswith('-') and '=' not in arg


def _gh_option_effect(flags: dict, arg: str):
    """(keep the token, pending state for the next token) under pflag rules.

    pending: None, 'text' (drop the next token), 'keep' (keep it) or
    'unknown' (keep it; it may itself be a bare option).
    """
    if arg == '-' or not arg.startswith('-'):
        return True, ('unknown' if arg == '-' else None)
    if arg.startswith('--'):
        kind = flags.get(arg.split('=', 1)[0])
        if kind == 'text':
            return (True, 'text') if '=' not in arg else (False, None)
        if kind == 'path':
            return True, ('keep' if '=' not in arg else None)
        if kind == 'bool':
            return True, None
        return True, ('unknown' if _gh_bare_option(arg) else None)
    for k in range(1, len(arg)):
        kind = flags.get('-' + arg[k])
        if kind == 'bool':
            continue
        rest = arg[k + 1:]
        if kind == 'text':
            # The rest of the token (after one optional '=') is the value.
            return (False, None) if rest else (True, 'text')
        if kind == 'path':
            return True, (None if rest else 'keep')
        # Unknown letter, or R inside a cluster: conservative.
        return True, ('unknown' if _gh_bare_option(arg) else None)
    return True, None  # all-bool cluster


def _gh_path_scan_args(args: list[str]) -> list[str]:
    """Drop gh values that are never local paths before path scanning (#1347, #1355).

    #1347: grammar-valid -R/--repo selector values in the repo-override
    groups; the group may follow leading selectors (`gh -R o/r issue close
    5`), and any other leading token keeps the generic model. #1355: for the
    subcommands in _GH_FLAG_KINDS, the values of 'text' flags, and a
    selector right after a known zero-arity flag. Any unknown flag may own
    the next token, so that token is kept (fail closed). Scanning stops at
    `--`. A command with an `--admin` token anywhere (including option
    values and after `--`) is never modelled: gh_merge_refusal owns the
    admin-merge refusal in every spelling (#1371), and no target may be
    removed from a form it does not refuse. The cwd fallback is
    unchanged, so this never grants authority.
    """
    if not args or args[0] != 'gh':
        return args

    def width_at(i: int, after_selector: bool) -> int:
        # pflag gives a value-taking flag the next token even when it starts
        # with '-', so a selector right after a bare option may be that
        # option's value (`-D -Ro/r` writes to ./-Ro/r). Keep it: fail closed.
        prev = args[i - 1]
        if not after_selector and prev.startswith('-') and prev != '--' and '=' not in prev:
            return 0
        return _gh_repo_selector_width(args, i)

    i, after_selector = 1, False
    while i < len(args) and (width := width_at(i, after_selector)):
        i, after_selector = i + width, True
    if i >= len(args) or args[i] not in _GH_REPO_OVERRIDE_GROUPS:
        return args
    group = args[i]
    kept = ['gh', group]
    i += 1
    # The subcommand follows the group, optionally after grammar-valid selectors.
    j, after_selector = i, False
    while j < len(args) and (width := width_at(j, after_selector)):
        j, after_selector = j + width, True
    modelled = _GH_FLAG_KINDS.get((group, args[j])) if j < len(args) else None
    if any(a == '--admin' or a.startswith('--admin=') for a in args):
        modelled = None  # admin bypass is never modelled (pinned merge-queue policy)
    flags = {**_GH_HELP_FLAGS, **modelled} if modelled else {}
    # With no modelled flags every option is unknown, which reproduces the
    # #1347 rule: never drop a selector directly after a bare option.
    pending = None
    while i < len(args):
        arg = args[i]
        if arg == '--':
            kept.extend(args[i:])
            break
        if pending == 'text':
            pending = None  # pflag hands this token to the text flag
        elif pending == 'keep':
            kept.append(arg)
            pending = None
        elif pending == 'unknown':
            kept.append(arg)
            pending = 'unknown' if _gh_bare_option(arg) else None
        elif width := _gh_repo_selector_width(args, i):
            i += width
            continue
        else:
            keep, pending = _gh_option_effect(flags, arg)
            if keep:
                kept.append(arg)
        i += 1
    return kept


# Inspect executable GH argv, not aliases, metadata or arbitrary interpreter programs.
UNPARSEABLE_MERGE_REFUSAL = 'unresolved executable gh admin merge'
_MERGE_COMMAND_SYNTAX = None


def _merge_command_syntax():
    global _MERGE_COMMAND_SYNTAX
    if _MERGE_COMMAND_SYNTAX is None:
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            'merge_command_syntax', str(Path(__file__).with_name('command-text.py')))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        _MERGE_COMMAND_SYNTAX = module
    return _MERGE_COMMAND_SYNTAX


def _env_word_matches(word, literal):
    return re.fullmatch('.*'.join(re.escape(part) for part in word.split(_ENV_DYNAMIC_WORD)), literal) is not None


def _env_short_value_possible(word, flags):
    booleans = {flag[1] for flag, kind in flags.items() if len(flag) == 2 and kind == 'bool'}
    values = {flag[1] for flag, kind in flags.items() if len(flag) == 2 and kind == 'text'}
    states = {0}  # start, boolean-prefix, final value-taking flag
    for index, part in enumerate(word.split(_ENV_DYNAMIC_WORD)):
        if index:
            states |= ({1, 2} if 0 in states else {2} if 1 in states else set())
        for char in part:
            following = set()
            if 0 in states and char == '-':
                following.add(1)
            if 1 in states and char in booleans:
                following.add(1)
            if 1 in states and char in values:
                following.add(2)
            states = following
    return 2 in states


def _gh_env_admin_argv(args, globs):
    # GNU words are single argv entries; unquoted variable-only entries may
    # disappear even while a flag is waiting for its value. Keep only the two
    # command positions, so optional words do not expand an argv power set.
    flags = {**_GH_HELP_FLAGS, **_GH_FLAG_KINDS[('pr', 'merge')]}
    value_flags = {key: ('text' if kind == 'path' else kind) for key, kind in flags.items()}
    value_flags.update({'--repo': 'text', '-R': 'text'})
    states = {((), None, False, False, False, False)}
    for index, word in enumerate(args[1:], 1):
        optional = word == _ENV_OPTIONAL_WORD
        if optional:
            word = _ENV_DYNAMIC_WORD
        following = set()
        for positional, pending, enabled, uncertain, help_requested, ended in states:
            if optional:
                following.add((positional, pending, enabled, uncertain, help_requested, ended))
            if pending in {'text', 'keep'}:
                value_glob = bool(globs and globs[index] and fnmatch.fnmatchcase('--admin', word))
                following.add((positional, None, enabled, uncertain or value_glob, help_requested, ended))
                continue
            dynamic = _ENV_DYNAMIC_WORD in word
            if dynamic and not ended and _env_short_value_possible(word, value_flags):
                following.add((positional, 'text', enabled, uncertain, help_requested, False))
            if not dynamic and (ended or (not word.startswith('-') and '__ccp_publication_dynamic__' not in word)):
                following.add(((positional + (word,))[:2], None, enabled, uncertain, help_requested, ended))
            elif dynamic and not ended and _gh_option_effect(value_flags, word) == (False, None):
                following.add((positional, None, enabled, uncertain, help_requested, False))
            elif dynamic and not ended and word.startswith(('--help=', '--admin=')):
                option = word.partition('=')[0]
                for wanted, values in ((True, ('1', 't', 'T', 'true', 'TRUE', 'True')),
                                       (False, ('0', 'f', 'F', 'false', 'FALSE', 'False'))):
                    if any(_env_word_matches(word, option + '=' + value) for value in values):
                        following.add((positional, None, wanted if option == '--admin' else enabled,
                                       uncertain, wanted if option == '--help' else help_requested, False))
            elif dynamic:
                for value in ('pr', 'merge'):
                    if _env_word_matches(word, value):
                        following.add(((positional + (value,))[:2], None, enabled, uncertain, help_requested, ended))
                following.add(((positional + ('',))[:2], None, enabled, uncertain, help_requested, ended))
                if not ended:
                    if _env_word_matches(word, '--'):
                        following.add((positional, None, enabled, uncertain, help_requested, True))
                    # A GNU expansion is one argument. Keep its possible flag
                    # roles distinct so a later literal boolean can override it.
                    following.add((positional, None, enabled, uncertain, help_requested, False))
                    for option in ('--admin', '--help'):
                        for wanted, spellings in ((True, ('', '=1', '=t', '=T', '=true', '=TRUE', '=True')),
                                                  (False, ('=0', '=f', '=F', '=false', '=FALSE', '=False'))):
                            if any(_env_word_matches(word, option + spelling) for spelling in spellings):
                                following.add((positional, None, wanted if option == '--admin' else enabled,
                                               uncertain, wanted if option == '--help' else help_requested, False))
                    for option in (*flags, '--repo', '-R'):
                        if _env_word_matches(word, option):
                            kind = 'text' if option in {'--repo', '-R'} else flags[option]
                            if kind in {'text', 'path'}:
                                following.add((positional, 'text', enabled, uncertain, help_requested, False))
            elif word == '--':
                following.add((positional, None, enabled, uncertain, help_requested, True))
            elif word in {'--help', '-h'} or word.startswith('--help='):
                wanted = '=' not in word or word.partition('=')[2] in {'1', 't', 'T', 'true', 'TRUE', 'True'}
                following.add((positional, None, enabled, uncertain, wanted, False))
            elif '__ccp_publication_dynamic__' in word:
                following.add((positional, None, enabled, True, help_requested, False))
            elif globs and globs[index] and fnmatch.fnmatchcase('--admin', word):
                following.add((positional, None, enabled, True, help_requested, False))
            elif word == '--admin' or word.startswith('--admin='):
                wanted = '=' not in word or word.partition('=')[2] in {'1', 't', 'T', 'true', 'TRUE', 'True'}
                following.add((positional, None, wanted, uncertain, help_requested, False))
            elif word in {'--repo', '-R'}:
                following.add((positional, 'text', enabled, uncertain, help_requested, False))
            elif word.startswith(('--repo=', '-R')):
                following.add((positional, None, enabled, uncertain, help_requested, False))
            else:
                _keep, next_pending = _gh_option_effect(flags, word)
                following.add((positional, next_pending, enabled, uncertain, help_requested, False))
        states = {state for state in following
                  if state[0] == ('pr', 'merge')[:len(state[0])]}
    possible = [state for state in states if state[0] == ('pr', 'merge') and not state[4]]
    return (['pr', 'merge'], any(state[2] or state[3] for state in possible)) if possible else (None, False)


def _gh_admin_argv(args, globs=()):
    """pflag values stay data; return whether actual built-in pr/merge enables admin."""
    if any(_ENV_DYNAMIC_WORD in word for word in args):
        return _gh_env_admin_argv(args, globs)
    flags = {**_GH_HELP_FLAGS, **_GH_FLAG_KINDS[('pr', 'merge')]}
    positional, pending, enabled, uncertain, help_requested, index = [], None, False, False, False, 1
    while index < len(args):
        word = args[index]
        if pending in {'text', 'keep'}:
            if globs and globs[index] and fnmatch.fnmatchcase('--admin', word):
                uncertain = True  # A value glob can supply additional flag argv.
            pending = None
        elif word == '--':
            positional.extend(args[index + 1:])
            break
        elif word in {'--help', '-h'} or word.startswith('--help='):
            help_requested = '=' not in word or word.partition('=')[2] in {'1', 't', 'T', 'true', 'TRUE', 'True'}
        elif '__ccp_publication_dynamic__' in word or _ENV_DYNAMIC_WORD in word:
            uncertain = True
        elif globs and globs[index] and fnmatch.fnmatchcase('--admin', word):
            uncertain = True
        elif word == '--admin' or word.startswith('--admin='):
            enabled = '=' not in word or word.partition('=')[2] in {'1', 't', 'T', 'true', 'TRUE', 'True'}
        elif word in {'--repo', '-R'}:
            index += 1
        elif word.startswith(('--repo=', '-R')):
            pass
        elif not word.startswith('-'):
            positional.append(word)
        else:
            _keep, pending = _gh_option_effect(flags, word)
        index += 1
    if help_requested:
        return None, False
    shape = positional[:2]
    return shape, shape == ['pr', 'merge'] and (enabled or uncertain)


def _env_executable_argv(args):
    # An unquoted variable-only word may disappear in GNU env. Inspect that
    # possible executable position without assigning it an environment value.
    while args and args[0] == _ENV_OPTIONAL_WORD:
        if _gh_admin_argv(['gh', *args[1:]])[1]:
            return args, True
        args = args[1:]
    suffix = args[0].rsplit(_ENV_DYNAMIC_WORD, 1)[-1] if args else ''
    possible_gh = suffix.rsplit('/', 1)[-1] == 'gh' if '/' in suffix else 'gh'.endswith(suffix)
    if (args and _ENV_DYNAMIC_WORD in args[0] and possible_gh
            and _gh_admin_argv(['gh', *args[1:]])[1]):
        return args, True
    return args, False


_GH_SHELL_KEYWORDS = {'!', 'if', 'then', 'elif', 'else', 'do', 'while', 'until', 'coproc'}


def _gh_inspection_groups(command, *, fallback=False):
    quoted, assignments = set(), set()
    parsed = shell_tokens(command, inspection_comments=fallback,
                          inspection_expansions=fallback, quoted_words=quoted,
                          assignment_words=assignments)
    groups, words, redirect = [], [], False
    for index, (word, operator, globs) in enumerate(parsed):
        if redirect:
            redirect = False
        elif operator and re.fullmatch(r'[0-9]*(?:<<|>>|>&|<&|>\||>|<)|&>>|&>', word):
            redirect = True
        elif operator:
            groups.append(words); words = []
        else:
            words.append((word, globs, index in quoted, index in assignments))
    groups.append(words)
    for group in groups:
        # Reserved words are syntax only before a command, never argv passed by
        # a wrapper. Quoted/escaped keywords remain ordinary program or data.
        while group and group[0][0] in _GH_SHELL_KEYWORDS and not group[0][2]:
            group = group[1:]
        yield group


def _gh_find_refusal(args, depth, inspect):
    values = {'-name', '-iname', '-path', '-ipath', '-wholename', '-iwholename',
              '-regex', '-iregex', '-lname', '-ilname', '-type', '-xtype', '-uid',
              '-gid', '-user', '-group', '-size', '-perm', '-links', '-inum',
              '-samefile', '-newer', '-anewer', '-cnewer', '-amin', '-cmin', '-mmin',
              '-atime', '-ctime', '-mtime', '-used', '-maxdepth', '-mindepth',
              '-context', '-fstype', '-printf', '-fprint', '-fprint0', '-fls',
              '-regextype', '-D', '-O', '-f'}
    index = 1
    while index < len(args):
        if args[index] == '-fprintf':
            index += 3  # output path and format are data
            continue
        if args[index] in values or re.fullmatch(r'-newer[acmBt][acmBt]', args[index]):
            index += 2
            continue
        if args[index] not in {'-exec', '-execdir', '-ok', '-okdir'}:
            index += 1
            continue
        start = index = index + 1
        while index < len(args) and args[index] != ';' and not (args[index] == '+' and index > start and args[index - 1] == '{}'):
            index += 1
        action = args[start:index]
        if action:
            # Find executes argv. Quote every word when re-entering inspection:
            # literal 'if' and shell punctuation are not shell syntax here.
            command = ' '.join("'" + word.replace("'", "'\"'\"'") + "'" for word in action)
            reason = inspect(command, _depth=depth + 1, _supplied=True)
            if reason:
                return reason
        index += 1
    return None


def unparseable_merge_refusal(command, _depth=0, _supplied=False):
    # Inspection-only tokens never authorize execution. Preserve command positions
    # and quoted data even when the publication syntax helper is unavailable.
    if _depth > 4:
        return None
    try:
        groups = list(_gh_inspection_groups(command, fallback=True))
    except UnknownShape:
        return None  # Incomplete shell syntax is not executable.
    for group in groups:
        while group and group[0][3]:
            group = group[1:]
        args = [word for word, _globs, _quoted, _assignment in group]
        supplied = _supplied
        for _ in range(5):
            args, ambiguous_env = _env_executable_argv(args)
            if ambiguous_env:
                return UNPARSEABLE_MERGE_REFUSAL
            if not args:
                break
            supplied = supplied or os.path.basename(args[0]) in {'xargs', 'parallel'}
            wrapped = _wrapped_command(args, preserve_shell=True)
            if wrapped is None:
                break
            args = wrapped
        if not args:
            continue
        name = os.path.basename(args[0]).casefold()
        if name == 'find':
            reason = _gh_find_refusal(args, _depth, unparseable_merge_refusal)
            if reason:
                return reason
        elif name == 'gh':
            original = [word for word, _globs, _quoted, _assignment in group]
            flags = ([positions for _word, positions, _quoted, _assignment in group][-len(args):]
                     if original[-len(args):] == args else [()] * len(args))
            shape, admin = _gh_admin_argv(args, flags)
            if admin or shape == ['pr', 'merge'] and (supplied or any('__ccp_publication_dynamic__' in word for word in args)):
                return UNPARSEABLE_MERGE_REFUSAL
        elif name in {'sh', 'bash', 'zsh', 'dash', 'ksh', 'ash'}:
            for index in range(1, len(args) - 1):
                if re.fullmatch(r'-[A-Za-z]*c[A-Za-z]*', args[index]):
                    if unparseable_merge_refusal(args[index + 1], _depth=_depth + 1):
                        return UNPARSEABLE_MERGE_REFUSAL
                    break
        elif name == 'eval' and unparseable_merge_refusal(' '.join(args[1:]), _depth=_depth + 1):
            return UNPARSEABLE_MERGE_REFUSAL
    return None


def gh_merge_refusal(command, _depth=0, _supplied=False):
    """Refuse actual GH admin merge argv through fixed wrappers and literal shells.

    Argument suppliers are unresolved only when their GH publication domain is
    visible. Alias definitions, ordinary programs and stdin processing are not
    treated as execution of their data. Existing task and server policy remain.
    """
    if _depth > 4:
        return unparseable_merge_refusal(command, _supplied=_supplied)
    try:
        syntax = _merge_command_syntax()
        command = syntax._publication_continuations(command)
        command, substitutions = syntax._publication_mask(command, os.getcwd(), _depth)
    except (OSError, ImportError, SyntaxError):
        substitutions = []  # The existing literal lexer still proves direct argv.
    except UnknownShape:
        return unparseable_merge_refusal(command, _supplied=_supplied)
    for _marker, program in substitutions:
        reason = gh_merge_refusal(program, _depth + 1)
        if reason:
            return reason
    try:
        groups = list(_gh_inspection_groups(command, fallback=False))
    except UnknownShape:
        return unparseable_merge_refusal(command, _supplied=_supplied)
    for group in groups:
        while group and group[0][3]:
            group = group[1:]
        args = [word for word, _globs, _quoted, _assignment in group]
        supplied = _supplied
        for _ in range(5):
            args, ambiguous_env = _env_executable_argv(args)
            if ambiguous_env:
                return 'argument-supplied gh merge executable is unresolved'
            if not args:
                break
            name = os.path.basename(args[0]).casefold()
            supplied = supplied or name in {'xargs', 'parallel'}
            wrapped = _wrapped_command(args, preserve_shell=True)
            if wrapped is None:
                break
            args = wrapped
        if not args:
            continue
        name = os.path.basename(args[0]).casefold()
        if name == 'find':
            reason = _gh_find_refusal(args, _depth, gh_merge_refusal)
            if reason:
                return reason
        elif name == 'gh':
            original = [word for word, _positions, _quoted, _assignment in group]
            flags = ([positions for _word, positions, _quoted, _assignment in group][-len(args):]
                     if original[-len(args):] == args else [()] * len(args))
            shape, admin = _gh_admin_argv(args, flags)
            if admin:
                return 'admin bypass is not supported'
            if supplied and (shape == ['pr', 'merge'] or shape == [] and re.search(r'\bpr\s+merge\b', command)):
                return 'argument-supplied gh merge flags are unresolved'
        elif name in {'sh', 'bash', 'zsh', 'dash', 'ksh', 'ash'}:
            for index in range(1, len(args) - 1):
                if re.fullmatch(r'-[A-Za-z]*c[A-Za-z]*', args[index]):
                    reason = gh_merge_refusal(args[index + 1], _depth + 1)
                    if reason:
                        return reason
                    break
        elif name == 'eval':
            reason = gh_merge_refusal(' '.join(args[1:]), _depth + 1)
            if reason:
                return reason
    return None


# Bounded write destinations (#1152). A shape modelled here writes only under
# its explicit destination operand, so that operand replaces the cwd as the
# mutation target. Any option or form not listed returns None, and the caller
# keeps the generic model (cwd plus slash operands). Options are limited to
# those with the same meaning in bsdtar and GNU tar.
_TAR_FLAGS = set('zjJvkmp')
_TAR_VALUES = set('fC')
_TAR_LONG_FLAGS = {'--extract', '--create', '--gzip', '--bzip2', '--xz', '--verbose',
                   '--keep-old-files', '--no-same-owner', '--no-same-permissions'}
_TAR_LONG_VALUES = {'--file': 'f', '--directory': 'C', '--strip-components': '', '--exclude': ''}


def _tar_targets(args: list[str], cwd: str):
    """(directories, files) written by a modelled tar extract/create, else None.

    Extract writes under its single -C directory (default: cwd) and reads the
    archive. Create writes only its -f archive and reads its sources. Both
    tars refuse absolute and `..` members without -P, which is not modelled;
    `tar -C DIR` therefore has the authority of the existing `cd DIR && tar`.
    """
    if os.path.basename(args[0]) not in {'tar', 'bsdtar', 'gtar'} or len(args) < 2:
        return None
    modes, values, operands = [], {'f': [], 'C': []}, []
    pending = []  # value letters waiting for their following argument
    operand_before_directory = False

    def letters(cluster: str, traditional: bool) -> bool:
        for index, letter in enumerate(cluster):
            if letter in 'xc':
                modes.append(letter)
            elif letter in _TAR_VALUES:
                rest = cluster[index + 1:]
                if rest and not traditional:
                    values[letter].append(rest)  # -fARCHIVE / -Cdir
                    return True
                pending.append(letter)
            elif letter not in _TAR_FLAGS:
                return False
        return True

    rest = args[1:]
    if not rest[0].startswith('-'):
        # Traditional bundle (`tar xzf A`): each value letter takes the next arguments in order.
        if not re.fullmatch(r'[A-Za-z]+', rest[0]) or not letters(rest[0], True):
            return None
        rest = rest[1:]
    for token in rest:
        if pending:
            values[pending.pop(0)].append(token)
        elif token.startswith('--'):
            name, has_value, value = token.partition('=')
            if name in _TAR_LONG_FLAGS and not has_value:
                if name in {'--extract', '--create'}:
                    modes.append('x' if name == '--extract' else 'c')
            elif name in _TAR_LONG_VALUES:
                letter = _TAR_LONG_VALUES[name]
                if not has_value:
                    if not letter:
                        return None  # keep value forms of the other options unambiguous
                    pending.append(letter)
                elif letter:
                    values[letter].append(value)
            else:
                return None
        elif token.startswith('-') and token != '-':
            if not letters(token[1:], False):
                return None
        else:
            operands.append(token)
            if not values['C']:
                operand_before_directory = True
    if pending or len(modes) != 1 or len(values['f']) > 1:
        return None
    archive = values['f'][0] if values['f'] else None
    if archive is not None and (':' in archive or not archive):
        return None  # host:file is a remote (rsh) archive
    if modes[0] == 'x':
        if len(values['C']) > 1 or values['C'] and operand_before_directory:
            return None  # member operands before -C are order-sensitive in GNU tar
        if any(not v for v in values['C']):
            return None
        return [canonical(values['C'][0] if values['C'] else '.', cwd)], []
    if archive is None or archive == '-':
        return None  # default device or stdout: no modelled file target
    if values['C']:
        return None  # create-mode -C only changes the read side; archive resolution order is not pinned for GNU tar
    return [], [canonical(archive, cwd)]


_VENV_FLAGS = {'--system-site-packages', '--symlinks', '--copies', '--clear', '--upgrade',
               '--without-pip', '--without-scm-ignore-files'}


def _venv_targets(args: list[str], cwd: str):
    """(directories, files) for `python -I -m venv [listed options] DIR...`, else None.

    Only the isolated form is modelled. Without -I, `-m` puts the cwd first on
    sys.path for every import venv makes (types, shutil, argparse, logging, ...),
    so cwd code can run and write anywhere; plain `python -m venv` therefore
    keeps the generic cwd target. -I also ignores PYTHON* variables and the
    user site directory (Python 3.4+).
    """
    executable = args[0]
    name = os.path.basename(executable)
    python = executable in {'python', 'python3'} or (os.path.isabs(executable)
             and re.fullmatch(r'python(?:3(?:\.[0-9]+)?)?', name) is not None)
    if not python or args[1:4] != ['-I', '-m', 'venv']:
        return None
    directories = []
    expect_prompt = False
    for token in args[4:]:
        if expect_prompt:
            expect_prompt = False
        elif token == '--prompt':
            expect_prompt = True
        elif token.startswith('--prompt='):
            pass
        elif token in _VENV_FLAGS:
            pass
        elif token.startswith('-'):
            return None  # --upgrade-deps (network, pip cache), abbreviations, --, -h
        else:
            directories.append(canonical(token, cwd))
    if expect_prompt or not directories:
        return None
    return directories, []


def bounded_write_targets(args: list[str], cwd: str):
    """Explicit destinations for a fully modelled bounded command, else None."""
    return _tar_targets(args, cwd) if os.path.basename(args[0]) in {'tar', 'bsdtar', 'gtar'} else _venv_targets(args, cwd)



def task_branch_preparation(args, cwd):
    """Bound only the shipped branch helper's declared repository/worktree.

    This remains a mutation and needs its ordinary owning task. Arbitrary
    Python scripts and copied helpers keep the existing opaque-script boundary.
    """
    script = 0
    if os.path.basename(args[0]) in {'python', 'python3'}:
        script = 1
        while script < len(args) and args[script] == '-B':
            script += 1
    if script >= len(args):
        return None
    expected = os.path.realpath(os.path.join(os.path.dirname(__file__), '../../bin/prepare-task-branch.py'))
    if canonical(args[script], cwd) != expected:
        return None
    values = {}
    rest = args[script + 1:]
    while rest:
        option = rest.pop(0)
        if '=' in option:
            option, value = option.split('=', 1)
        else:
            if not rest:
                raise UnknownShape('branch preparation option is missing its value')
            value = rest.pop(0)
        if option not in {'--repo', '--branch', '--worktree', '--remote'} or option in values or not value:
            raise UnknownShape('unsupported branch preparation options')
        values[option] = value
    if not {'--branch', '--worktree'} <= values.keys():
        raise UnknownShape('branch preparation needs a unique branch and worktree')
    if values['--branch'].startswith('-') or values.get('--remote', 'origin').startswith('-'):
        raise UnknownShape('invalid branch preparation name')
    return [canonical(values.get('--repo', cwd), cwd), canonical(values['--worktree'], cwd)]


def _project_execution_wrapper(args: list[str]):
    """Literal env/command project execution; retain mutation and environment targets.

    This is not a reader or a general wrapper parser. Git keeps its existing
    stricter normalizer; shell/remote/unknown dispatch cannot borrow cwd scope.
    """
    wrapper = os.path.basename(args[0])
    if wrapper not in {'env', 'command'}:
        return None
    index, targets, environment = 1, [], []
    if wrapper == 'env':
        if args[index:index + 1] in (['-i'], ['--ignore-environment']):
            index += 1
        if args[index:index + 1] == ['--']:
            index += 1
        while index < len(args) and re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*=.*', args[index], re.S):
            environment.append(args[index].split('=', 1))
            index += 1
    elif args[index:index + 1] == ['--']:
        index += 1
    dispatch = args[index:]
    if dispatch and os.path.basename(dispatch[0]) == 'git':
        return None  # all Git environment/options remain with its existing normalizer
    for name, value in environment:
        if name == 'PATH':
            if not value or any(not os.path.isabs(part) for part in value.split(':')):
                raise UnknownShape('project execution PATH needs literal absolute search directories')
        elif name == 'PYTHONPATH':
            targets.extend(part or '.' for part in value.split(':'))
        elif name in {'HOME', 'XDG_CONFIG_HOME', 'XDG_CACHE_HOME', 'TMPDIR', 'BUN_RUNTIME_TRANSPILER_CACHE_PATH'}:
            if not value:
                raise UnknownShape('project execution environment target is empty')
            if name != 'BUN_RUNTIME_TRANSPILER_CACHE_PATH' or value != '0':
                targets.append(value)
        elif name not in {'NODE_ENV', 'CI', 'DO_NOT_TRACK', 'LANG', 'LC_ALL', 'LC_CTYPE'}:
            raise UnknownShape('unsupported project execution environment override: ' + name)
    if not dispatch or dispatch[0].startswith('-'):
        raise UnknownShape('unsupported project execution wrapper options or missing executable')
    executable = os.path.basename(dispatch[0])
    if executable not in {'bun', 'node', 'python', 'python3', 'pytest', 'make', 'npm', 'pnpm', 'yarn'}:
        raise UnknownShape('unsupported project execution wrapper executable')
    inline = ('-c',) if executable in {'python', 'python3'} else ('-e', '-p') if executable in {'bun', 'node'} else ()
    if inline and any(word.startswith(inline) or executable in {'python', 'python3'}
                      and word.startswith('-') and not word.startswith('--') and 'c' in word[1:]
                      for word in dispatch[1:]):
        raise UnknownShape('opaque inline execution has unbounded mutation targets')
    if executable in {'bun', 'node'} and any(word.partition('=')[0] in {'--eval', '--print'} for word in dispatch[1:]):
        raise UnknownShape('opaque inline execution has unbounded mutation targets')
    return dispatch, targets

def _action(command: str, cwd: str) -> dict:
    try:
        tokens = shell_tokens(command)
        scanner = _scanner_execution(tokens, cwd)
        if scanner is not None:
            return scanner
        receipt = _test_receipt_record(tokens, cwd)
        if receipt is not None:
            return receipt
    except UnknownShape as e:
        return {"read_only": False, "paths": [canonical(cwd)], "error": str(e)}
    paths = []
    reads = True
    diagnostic = False
    self_managed = True
    directory_paths = []
    directory_removals = []
    file_removals = []  # rm operands: unlinking a name never writes the file (#1100)
    file_paths = []
    # #1152: cwd proxies for writes the parser cannot model ("unknown writes"),
    # as opposed to explicit targets. Tier floors for own-session scratch must
    # never apply to these.
    fallback_paths = []
    remote_repos = []
    remote_actions = []
    review_actions = []
    metadata_posts = []
    remote_hosts = []  # allowlisted ssh destinations (#1160)
    mutation_commands = 0
    commit_commands = 0
    unproven_companions = []
    args = []
    arg_globs = []
    effective = canonical(cwd)
    binding = ""

    def finish():
        nonlocal args, arg_globs, effective, reads, binding, diagnostic, self_managed, mutation_commands, commit_commands
        if not args:
            return
        while args and args[0].startswith("CCP_TASK_ID="):
            if arg_globs.pop(0):
                raise UnknownShape('globbed task binding requires an explicit identity')
            value = args.pop(0).split("=", 1)[1]
            if binding and value != binding:
                raise UnknownShape("conflicting command task bindings")
            binding = value
        if not args:
            raise UnknownShape("missing command")
        if arg_globs[0]:
            raise UnknownShape('globbed command requires an explicit executable')
        if args[0] == "cd":
            if len(args) != 2 or args[1].startswith("-") or arg_globs[1]:
                raise UnknownShape("unsupported cd; use an explicit concrete path")
            effective = canonical(args[1], effective)
        elif args[:3] == ['gh', 'api', 'graphql']:
            target = github_graphql(args)
            if target['kind'] == 'query':
                pass
            elif target['kind'] == 'resolve-review-thread':
                reads = False
                review_actions.append(target)
            else:
                raise UnknownShape('Unsupported GraphQL mutation; only separately modeled queue, project or review actions may proceed')
            self_managed = False
            args, arg_globs = [], []
            return
        elif args[:2] == ['gh', 'api'] and released_read_verdict(shlex.join(args)) != 0:
            # Existing text metadata is the only modeled API write. Unknown API
            # operations cannot borrow cwd/file authority, regardless of endpoint.
            reply = github_review_reply(args, effective)
            remote = github_metadata_target(args, effective) if reply is None else None
            if reply is None and remote is None:
                raise UnknownShape('Unsupported GitHub API mutation requires explicit remote authority; use a modeled review, project or metadata operation')
            reads = False
            if reply is not None:
                review_actions.append(reply)
            else:
                remote_repos.append(remote)
            self_managed = False
            args, arg_globs = [], []
            return
        elif (effect := _released_read_classifier().git_file_effects(args)) and effect.get('read_only'):
            _reader_globs(args, arg_globs)
            if released_read_verdict(shlex.join(args)) != 0:
                unproven_companions.append(effective)
        elif investigation(args):
            _reader_globs(args, arg_globs)
            diagnostic = True
            if released_read_verdict(shlex.join(args)) != 0:
                unproven_companions.append(effective)
        elif reader(args):
            _reader_globs(args, arg_globs)
            # A whole-command reader verdict can stop at the metadata write.
            # Re-prove each companion before granting the metadata exception.
            if released_read_verdict(shlex.join(args)) != 0:
                unproven_companions.append(effective)
        elif args[:2] == ['gh', 'project'] and released_read_verdict(shlex.join(args)) == 0:
            pass
        else:
            if any(arg_globs):
                raise UnknownShape('expanded mutation targets require explicit concrete paths')
            reads = False
            mutation_commands += 1
            branch_paths = task_branch_preparation(args, effective)
            if branch_paths is not None:
                paths.extend(branch_paths)
                self_managed = False
                args, arg_globs = [], []
                return
            project = github_project_action(args)
            if project is not None:
                remote_actions.append(project)
                self_managed = False
                args, arg_globs = [], []
                return
            remote = github_metadata_target(args, effective)
            if remote is not None:
                remote_repos.append(remote)
                self_managed = False
                args, arg_globs = [], []
                return
            if args[:2] in (['gh', 'issue'], ['gh', 'pr']) and (
                    args[2:3] == ['comment'] or args[1:3] == ['issue', 'create'] or args[2:3] == ['review'] and '--comment' in args[3:]):
                from github_metadata_comment import metadata_comment
                post = {}
                if metadata_comment(shlex.join(args), effective, details=post) is not True:
                    raise UnknownShape('unproven GitHub metadata post shape or target; use literal repository/target and body')
                metadata_posts.append({**post, 'cwd': effective})
                self_managed = False
                args, arg_globs = [], []
                return
            # ssh names no local target; its destination is checked instead
            # (#1160). This precedes the operand pass below, which would read
            # remote text such as 'cat /etc/x' as local paths.
            host = ssh_invocation(args)
            if host is not None:
                allowed, source = ssh_allowlist()
                if host not in allowed:
                    raise UnknownShape(f"ssh host {host!r} is not on the ssh host allowlist {source} "
                                       f"(allowed: {', '.join(sorted(allowed)) or 'none'}); "
                                       "only the operator can add a host (#1160)")
                remote_hosts.append(host)
                self_managed = False
                args, arg_globs = [], []
                return
            wrapped = _project_execution_wrapper(args)
            if wrapped is not None:
                args, environment_targets = wrapped
                paths.extend(canonical(value, effective) for value in environment_targets)
                # This branch is already a mutation; do not rerun reader admission.
            self_managed = self_managed and args[0] in {"touch", "mkdir", "rm", "rmdir", "cp", "mv", "tee", "chmod", "chown", "ln"}
            if args[0] in {'eval', 'exec', 'bash', 'sh', 'zsh', 'dash', 'ksh'} or args[0] in {'python', 'python3'} and any(x == '-c' or x.startswith('-c') for x in args[1:]):
                raise UnknownShape('opaque inline execution has unbounded mutation targets')
            local = effective
            # gh -R/--repo selector values (#1347) and modelled free-text
            # option values (#1355) are not local paths; the glob/tilde checks
            # below still see every original operand.
            scanned = _gh_path_scan_args(args)
            operands = [x.split('=', 1)[-1] if '=' in x else x for x in args[1:]]
            # Unquoted glob positions were rejected above. Retain that lexical
            # proof for known literal operands; do not reinterpret quoted data.
            if (any(x.startswith('~') for x in operands)
                    or not _literal_operand_family(args)
                    and any(any(c in x for c in '*?[') for x in operands)):
                raise UnknownShape('expanded mutation targets require explicit concrete paths')
            if args[0] not in {'touch', 'mkdir', 'rm', 'rmdir', 'cp', 'mv', 'tee', 'chmod', 'chown', 'git'}:
                path_operands = [x.split('=', 1)[-1] if '=' in x else x for x in scanned[1:]]
                paths.extend(canonical(x, effective) for x in path_operands if '/' in x and '://' not in x and not x.startswith('-'))
            if os.path.basename(args[0]) == "git" or args[0] in {"env", "command"}:
                # The operation-policy guards use this same literal boundary.
                # A valid task does not turn an unresolved alias into authority.
                from git_command import prefix
                operation = prefix(args, local)
                if not operation:
                    raise UnknownShape("unsupported Git mutation options")
                if any(_long_option_matches(a, ('--textconv', '--ext-diff', '--exec', '--open-files-in-pager',
                                                   '--upload-pack', '--receive-pack')) for a in operation["args"][1:]):
                    raise UnknownShape("Git helper execution has unbounded effects; use --no-textconv/--no-ext-diff for inspection")
                local = operation["cwd"]
                effect = _released_read_classifier().git_file_effects(args)
                if effect and effect.get('error'):
                    raise UnknownShape(effect['error'])
                bootstrap = _git_bootstrap_destination(operation)
                if effect and effect['kind'] == 'archive':
                    if effect['output'] is None:
                        raise UnknownShape('unproven archive reader normalization')
                    target = canonical(effect['output'], local)
                    try:
                        info = os.stat(target)
                    except FileNotFoundError:
                        info = None
                    except OSError as exc:
                        raise UnknownShape('cannot inspect archive output; use a fresh explicit file') from exc
                    if info is not None and (not stat.S_ISREG(info.st_mode) or info.st_nlink != 1):
                        raise UnknownShape('archive output has unproven write aliases; use a fresh single-link file')
                    paths.append(target)
                    file_paths.append(target)
                elif bootstrap is not None:
                    paths.append(bootstrap)
                    directory_paths.append(bootstrap)
                else:
                    paths.append(_git_toplevel(local))
                    rest = operation['args'][1:]
                    if operation['args'][0] == 'commit':
                        commit_commands += 1
                        rest = _commit_write_operands(rest)
                    git_operands = [x.split('=', 1)[-1] if '=' in x else x for x in rest]
                    paths.extend(canonical(x, local) for x in git_operands if '/' in x and '://' not in x and not x.startswith('-'))
            elif args[0] in {"touch", "mkdir", "rm", "rmdir", "cp", "mv", "tee", "chmod", "chown", "patch"}:
                # Options that take the next token as their value. Without this,
                # `cp SRC DST -S .bak` made `.bak` the copy destination (#1051
                # review): GNU tools permute options, so values can trail.
                value_options = {
                    'touch': {'-r', '--reference', '-d', '--date', '-t'},
                    'mkdir': {'-m', '--mode'},
                    'cp': {'-S', '--suffix'}, 'mv': {'-S', '--suffix'},
                    'chmod': {'--reference'}, 'chown': {'--reference'},
                }.get(args[0], set())
                operands = []
                option_paths = []
                has_reference = False
                skip = False
                end_of_options = False
                for token in args[1:]:
                    if skip:
                        skip = False
                        continue
                    if end_of_options or not token.startswith('-') or token == '-':
                        operands.append(token)
                        continue
                    if token == '--':
                        end_of_options = True
                        continue
                    if args[0] in {'cp', 'mv'} and (token == '-t' or _long_option_matches(token, ('--target-directory',))
                                                   or (not token.startswith('--') and 't' in token[1:])):
                        raise UnknownShape('use explicit final copy destination')
                    if args[0] == 'cp':
                        _cp_option(token)
                    if token == '--reference' or token.startswith('--reference='):
                        has_reference = True
                    elif '/' in token:
                        # A path attached to an option (`-o/abs`, `--out=/abs`)
                        # is a potential target: count it, never drop it.
                        option_paths.append(token.split('=', 1)[1] if token.startswith('--') and '=' in token else token[token.index('/'):])
                    if token in value_options or args[0] in {'cp', 'mv'} and _long_option_matches(token, ('--suffix',)) and '=' not in token:
                        skip = True
                    elif not token.startswith('--') and (args[0] == 'cp' and token.find('S') == len(token) - 1
                                                           or args[0] == 'mv' and token.endswith('S')):
                        skip = True  # only a final option S consumes the next token for cp
                copied_directories = []
                if args[0] in {'cp', 'mv'} and len(operands) >= 2:
                    sources, destination = operands[:-1], operands[-1]
                    targets, copied_directories = _copy_destinations(sources, destination, args[1:], effective)
                    source_writes = args[0] == 'mv' or _cp_link_copy(args[1:])
                    aliases = [] if source_writes else _copy_alias_targets(sources, args[1:], effective)
                    operands = (sources if source_writes else aliases) + targets
                    directory_paths.extend(copied_directories)
                elif args[0] in {'chmod', 'chown'} and not has_reference:
                    operands = operands[1:]  # the first operand is the mode/owner
                operands = operands + option_paths
                paths.extend(canonical(x, effective) for x in operands)
                if args[0] in {"mkdir", "rmdir"}:
                    directory_paths.extend(canonical(x, effective) for x in operands)
                    if args[0] == 'rmdir':
                        directory_removals.extend(canonical(x, effective) for x in operands)
                else:
                    file_paths.extend(canonical(x, effective) for x in operands if canonical(x, effective) not in copied_directories)
                    if args[0] == 'rm':
                        file_removals.extend(canonical(x, effective) for x in operands)
                if not operands:
                    paths.append(local); fallback_paths.append(local)
            elif args[0] == 'ln':
                # Both ends of a link are targets (#1100): writing through the
                # link writes the source.
                # A target directory can ride on an option (`--target-directory=d`,
                # `--targ=d`, `-td`), so option values count as operands too.
                link_operands = []
                target_dir = None  # -t DIR / -tDIR / --target-directory=DIR
                ended = False
                expect_dir = False
                for x in args[1:]:
                    if expect_dir:
                        target_dir = x
                        link_operands.append(x)
                        expect_dir = False
                    elif ended or not x.startswith('-') or x == '-':
                        link_operands.append(x)
                    elif x == '--':
                        ended = True
                    elif x.startswith('--'):
                        if '=' in x:
                            link_operands.append(x.split('=', 1)[1])
                            if '--target-directory'.startswith(x.split('=', 1)[0]):
                                target_dir = x.split('=', 1)[1]
                        elif len(x) > 2 and '--target-directory'.startswith(x):
                            expect_dir = True
                    elif 't' in x[1:]:
                        rest = x[x.index('t', 1) + 1:]
                        if rest:
                            target_dir = rest
                            link_operands.append(rest)
                        else:
                            expect_dir = True
                if not link_operands:
                    paths.append(local); fallback_paths.append(local)
                # A relative symlink target resolves from the link's directory,
                # not the cwd (#1109): `ln -s x sub/link` points at sub/x. Count
                # both readings of every relative operand.
                # With -t the links live in that directory, so every source
                # resolves from it.
                if target_dir is not None:
                    tdir = os.path.join(effective, target_dir)
                    for t in [x for x in link_operands if x != target_dir]:
                        if not t.startswith('/'):
                            link_operands.append(os.path.join(tdir, t))
                elif len(link_operands) >= 2:
                    link_dir = os.path.join(effective, link_operands[-1])
                    for t in link_operands[:-1]:
                        if not t.startswith('/'):
                            for base in (os.path.dirname(link_dir), link_dir):
                                link_operands.append(os.path.join(base, t))
                paths.extend(canonical(x, effective) for x in link_operands)
                file_paths.extend(canonical(x, effective) for x in link_operands)
            elif (bounded := bounded_write_targets(args, effective)) is not None:
                # #1152: a fully modelled tar/venv shape writes only under its
                # explicit destination, so the cwd is not a target. Slash
                # operands (archives, sources) were already counted above.
                directories, files = bounded
                paths.extend(directories + files)
                directory_paths.extend(directories)
                file_paths.extend(files)
            else:
                paths.append(local); fallback_paths.append(local)
                # Explicit paths cannot escape a task by borrowing CWD scope.
                paths.extend(canonical(x, effective) for x in scanned[1:] if x.startswith(("/", "./", "../")))
                # Paths attached to options (`-o/abs`, `--out=/abs`) cannot
                # escape either.
                for x in scanned[1:]:
                    if x.startswith('-') and '/' in x:
                        value = x.split('=', 1)[1] if x.startswith('--') and '=' in x else x[x.index('/'):]
                        if value.startswith(("/", "./", "../")):
                            paths.append(canonical(value, effective))
        args = []
        arg_globs = []

    try:
        i = 0
        while i < len(tokens):
            value, op, globs = tokens[i]
            if not op:
                args.append(value)
                arg_globs.append(globs)
            elif re.fullmatch(r"[0-9]*(?:>>|>&|<&|>\||>|<)|&>>|&>", value):
                redirect = re.sub(r"^[0-9]+", "", value)
                i += 1
                if i >= len(tokens) or tokens[i][1]:
                    raise UnknownShape("missing redirect target")
                target = tokens[i][0]
                if tokens[i][2] or target.startswith('~'):
                    raise UnknownShape('redirection requires an explicit concrete path')
                if redirect in {">&", "<&"} and (re.fullmatch(r"[0-9]+", target) or target == "-"):
                    pass  # duplicate/close descriptors; no filesystem target
                elif redirect == "<&":
                    raise UnknownShape("input fd duplication requires a descriptor or -")
                elif redirect != "<" and target != "/dev/null":
                    # Only the literal sink is exempt: aliases/symlinks still
                    # require ownership. Earlier file writes are never erased
                    # by a later duplication or /dev/null redirect.
                    reads = False
                    paths.append(canonical(target, effective))
                    file_paths.append(canonical(target, effective))
            elif value in {"&&", ";", "|", "||"}:
                finish()
            else:
                raise UnknownShape("unsupported shell operator")
            i += 1
        finish()
        if commit_commands and mutation_commands > commit_commands:
            raise UnknownShape('separate configuration/file mutations from commit calls; run git commit -F FILE first, then a separately scoped cleanup command')
    except UnknownShape as e:
        return {"read_only": False, "paths": list(dict.fromkeys(paths + [effective])), "error": str(e), "binding": binding}
    if remote_repos or remote_actions or review_actions or metadata_posts or remote_hosts:
        paths.extend(unproven_companions)
    # Remote-only: no local target and no diagnostic companion. ssh gets its
    # own flag; metadata_only lets other guards skip their checks (#1160).
    # A project or review action beside ssh keeps its task-owned authorization:
    # remote_contact_only never short-circuits remote_actions or review_actions.
    remote_only = not paths and not diagnostic
    return {"read_only": reads and not diagnostic and bool(tokens), "investigation": reads and diagnostic,
            "self_managed_shape": self_managed and not diagnostic, "directory_paths": [p for p in directory_paths if p not in file_paths], "directory_removals": directory_removals,
            # A path only removed, never also written in the same command (#1100).
            "file_removals": [p for p in file_removals if paths.count(p) == file_removals.count(p)],
            "paths": list(dict.fromkeys(paths or ([] if (remote_repos or remote_actions or review_actions or remote_hosts or metadata_posts) and not (remote_hosts and not remote_only) else [effective]))),
            # The cwd default used when nothing explicit was found is also a fallback.
            "fallback_paths": list(dict.fromkeys(fallback_paths + ([] if paths else [effective]))),
            "remote_repos": list(dict.fromkeys(remote_repos)),
            "remote_actions": remote_actions, "review_actions": review_actions, "metadata_posts": metadata_posts,
            "remote_hosts": list(dict.fromkeys(remote_hosts)),
            "metadata_only": bool(remote_repos) and not remote_actions and not review_actions and not metadata_posts and not remote_hosts and remote_only,
            "remote_contact_only": bool(remote_hosts) and not remote_actions and not review_actions and not metadata_posts and remote_only, "binding": binding}


if __name__ == '__main__' and len(sys.argv) == 3 and sys.argv[1] == '--merge-fallback':
    reason = unparseable_merge_refusal(sys.argv[2])
    if reason:
        print(reason)
    sys.exit(3 if reason else 0)

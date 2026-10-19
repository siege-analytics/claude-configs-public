"""Bounded shell classification and canonical action paths (#1051).

Pure readers and explicitly approved diagnostics have separate early-allow
flags. Candidate commands are never executed; Git ownership uses a bounded
read-only toplevel query. Unknown syntax remains mutation-gated or fails closed.
Expansions, subshells, eval and executable reader options are not pure reads.
"""
from __future__ import annotations

import ast
import os
import re
import subprocess


class UnknownShape(ValueError):
    pass


def shell_tokens(command: str) -> list[tuple[str, bool]]:
    """Return (value, is_operator), preserving quoted operator literals."""
    tokens = []
    word = ""
    active = False
    quote = ""
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
            if i >= len(command) or command[i] == "\n":
                raise UnknownShape("escaped newline or incomplete escape")
            word += command[i]
            active = True
        elif c in "$`" and quote != "'":
            raise UnknownShape("shell expansion requires mutation handling")
        elif quote == '"':
            if c == quote:
                quote = ""
            else:
                word += c
        elif c in "'\"":
            quote = c
            active = True
        elif c in "(){}":
            raise UnknownShape("shell group requires mutation handling")
        elif c in "*?[" and not (c == "[" and not active and i + 1 < len(command) and command[i + 1].isspace()):
            raise UnknownShape("unquoted glob expansion requires mutation handling")
        elif c.isspace() or c in ";&|<>":
            if active:
                tokens.append((word, False))
                word, active = "", False
            if c == "\n":
                tokens.append((";", True))
            elif not c.isspace():
                op = c
                if i + 1 < len(command) and command[i + 1] == c:
                    op += c
                    i += 1
                tokens.append((op, True))
        elif c == "#" and not active:
            # Comments/markers are deliberately not interpreted as authorization.
            raise UnknownShape("shell comment requires mutation handling")
        else:
            word += c
            active = True
        i += 1
    if quote:
        raise UnknownShape("unclosed quote")
    if active:
        tokens.append((word, False))
    return tokens


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

    Tests may execute project code/write caches. This preserves the base's
    investigation allowance without labelling test runners pure readers.
    Explicit source-edit, output-file and arbitrary execution options remain
    gated; arbitrary scripts/clones are not investigation exceptions.
    """
    if not args:
        return False
    cmd, rest = args[0], args[1:]
    if cmd in {"python", "python3"} and len(rest) >= 2 and rest[0] == "-m":
        if rest[1] == "pytest":
            cmd, rest = "pytest", rest[2:]
        elif rest[1] == "py_compile":
            return _options(rest[2:], flags={"-q"}, minimum=1)
        else:
            return False
    if cmd == "pytest":
        return _options(rest, flags={"-q", "-qq", "-v", "-vv", "-x", "-s", "--collect-only", "--disable-warnings", "--strict-markers", "--strict-config", "--no-header", "--no-summary"}, values={"-k", "-m", "--maxfail", "--tb", "--color"})
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


def _git_toplevel(directory: str) -> str:
    try:
        return canonical(subprocess.check_output(["git", "-C", directory, "rev-parse", "--show-toplevel"], text=True, stderr=subprocess.DEVNULL, timeout=3).strip())
    except (subprocess.SubprocessError, OSError):
        raise UnknownShape("cannot resolve repository toplevel for Git mutation")


def reader(args: list[str]) -> bool:
    if not args:
        return False
    cmd, rest = args[0], args[1:]
    if cmd in {"cat", "head", "tail", "less", "more", "wc", "file", "stat", "du", "df", "which", "readlink", "realpath", "md5", "sha256sum", "shasum", "xxd", "od", "hexdump", "ls", "cmp", "comm", "pwd", "dirname", "basename", "uname", "hostname", "whoami", "id", "true", "false", "test", "[", "echo", "printenv"}:
        # xxd -r reverses into an output file; file -C compiles a database.
        if cmd == "xxd":
            return _options(rest, flags={"-a", "-b", "-e", "-p", "-ps", "-u", "-v"}, values={"-c", "-g", "-l", "-o", "-s"}, maximum=1)
        if cmd == "file" and any(a.startswith('--compile') or a.startswith('-') and not a.startswith('--') and 'C' in a for a in rest):
            return False
        if cmd in {"less", "more"}:  # interactive shell escapes / LESSOPEN
            return False
        return True
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
        while rest and rest[0] == "-C" and len(rest) >= 2:
            rest = rest[2:]
        if not rest:
            return False
        sub, opts = rest[0], rest[1:]
        if any(a.startswith(("--output", "--ext-diff", "--textconv", "--exec", "-o")) for a in opts):
            return False
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
            return not any(a in {"-X", "--method", "--input", "--raw-field", "--field", "-f", "-F"} or a.startswith(("-X", "-f", "-F", "--method=", "--input=", "--field=", "--raw-field=")) for a in rest[1:])
        return len(rest) >= 2 and (rest[0], rest[1]) in {(x, y) for x in {"issue", "pr", "release", "run"} for y in {"view", "list", "checks", "diff", "status"}} | {("repo", "view")}
    return False


def canonical(path: str, cwd: str = "") -> str:
    return os.path.realpath(path if os.path.isabs(path) else os.path.join(cwd or os.getcwd(), path))


def action(command: str, cwd: str) -> dict:
    """Classify before gate lookup, and conservatively collect mutation targets."""
    try:
        tokens = shell_tokens(command)
    except UnknownShape as e:
        return {"read_only": False, "paths": [canonical(cwd)], "error": str(e)}
    paths = []
    reads = True
    diagnostic = False
    self_managed = True
    directory_paths = []
    directory_removals = []
    file_paths = []
    args = []
    effective = canonical(cwd)
    binding = ""

    def finish():
        nonlocal args, effective, reads, binding, diagnostic, self_managed
        if not args:
            return
        while args and args[0].startswith("CCP_TASK_ID="):
            value = args.pop(0).split("=", 1)[1]
            if binding and value != binding:
                raise UnknownShape("conflicting command task bindings")
            binding = value
        if not args:
            raise UnknownShape("missing command")
        if args[0] == "cd":
            if len(args) != 2 or args[1].startswith("-"):
                raise UnknownShape("unsupported cd")
            effective = canonical(args[1], effective)
        elif investigation(args):
            diagnostic = True
        elif not reader(args):
            reads = False
            self_managed = self_managed and args[0] in {"touch", "mkdir", "rm", "rmdir", "cp", "mv", "tee", "chmod", "chown"}
            if args[0] in {'eval', 'exec', 'bash', 'sh', 'zsh', 'dash', 'ksh'} or args[0] in {'python', 'python3'} and any(x == '-c' or x.startswith('-c') for x in args[1:]):
                raise UnknownShape('opaque inline execution has unbounded mutation targets')
            local = effective
            operands = [x.split('=', 1)[-1] if '=' in x else x for x in args[1:]]
            if any(any(c in x for c in '*?[') or x.startswith('~') for x in operands):
                raise UnknownShape('expanded mutation targets require explicit concrete paths')
            if args[0] not in {'touch', 'mkdir', 'rm', 'rmdir', 'cp', 'mv', 'tee', 'chmod', 'chown', 'git'}:
                paths.extend(canonical(x, effective) for x in operands if '/' in x and '://' not in x and not x.startswith('-'))
            if args[0] == "git":
                i = 1
                while i + 1 < len(args) and args[i] == "-C":
                    local = canonical(args[i + 1], local)
                    i += 2
                if i >= len(args) or args[i].startswith("-"):
                    raise UnknownShape("unsupported Git mutation options")
                # Index/refs/worktree commands are conservatively repo-wide,
                # even with a pathspec: a nested task cannot lend authority.
                paths.append(_git_toplevel(local))
                git_operands = [x.split('=', 1)[-1] if '=' in x else x for x in args[i + 1:]]
                paths.extend(canonical(x, local) for x in git_operands if '/' in x and '://' not in x and not x.startswith('-'))
            elif args[0] in {"touch", "mkdir", "rm", "rmdir", "cp", "mv", "tee", "chmod", "chown", "patch"}:
                operands = []
                skip = False
                for token in args[1:]:
                    if skip:
                        skip = False
                        continue
                    if args[0] == 'touch' and token in {'-r', '--reference', '-d', '--date', '-t'}:
                        skip = True
                        continue
                    if not token.startswith('-'):
                        operands.append(token)
                if args[0] == 'cp':
                    # Common copy form: source(s) are reads, final operand writes.
                    if any(x in {'-t', '--target-directory'} or x.startswith('--target-directory=') for x in args):
                        raise UnknownShape('use explicit final copy destination')
                    operands = operands[-1:]
                elif args[0] in {'chmod', 'chown'}:
                    operands = operands[1:]
                paths.extend(canonical(x, effective) for x in operands)
                if args[0] in {"mkdir", "rmdir"}:
                    directory_paths.extend(canonical(x, effective) for x in operands)
                    if args[0] == 'rmdir':
                        directory_removals.extend(canonical(x, effective) for x in operands)
                else:
                    file_paths.extend(canonical(x, effective) for x in operands)
                if not operands:
                    paths.append(local)
            else:
                paths.append(local)
                # Explicit paths cannot escape a task by borrowing CWD scope.
                paths.extend(canonical(x, effective) for x in args[1:] if x.startswith(("/", "./", "../")))
        args = []

    try:
        i = 0
        while i < len(tokens):
            value, op = tokens[i]
            if not op:
                args.append(value)
            elif value in {">", ">>"}:
                reads = False
                i += 1
                if i >= len(tokens) or tokens[i][1]:
                    raise UnknownShape("missing redirect target")
                paths.append(canonical(tokens[i][0], effective))
                file_paths.append(canonical(tokens[i][0], effective))
            elif value == "<":
                i += 1
                if i >= len(tokens) or tokens[i][1]:
                    raise UnknownShape("missing input target")
            elif value in {"&&", ";", "|", "||"}:
                finish()
            else:
                raise UnknownShape("unsupported shell operator")
            i += 1
        finish()
    except UnknownShape as e:
        return {"read_only": False, "paths": list(dict.fromkeys(paths + [effective])), "error": str(e), "binding": binding}
    return {"read_only": reads and not diagnostic and bool(tokens), "investigation": reads and diagnostic,
            "self_managed_shape": self_managed and not diagnostic, "directory_paths": [p for p in directory_paths if p not in file_paths], "directory_removals": directory_removals,
            "paths": list(dict.fromkeys(paths or [effective])), "binding": binding}

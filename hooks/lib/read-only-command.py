#!/usr/bin/env python3
"""Positive read-only classifier for the electinfo mutation gate.

Exit 0 when every simple command in argv[1] is a known read with read-safe
arguments; exit 1 otherwise. This is an allowlist: anything it does not
recognise is "not proven read-only" and the gate falls back to its normal
behaviour. It never authorizes a mutation; it only spares a read the cost of
a task gate (siege#1051, #1057; electinfo#348).
"""
import re
import shlex
import sys

# Bare read verbs whose arguments cannot make them write.
PLAIN = {
    "ls", "cat", "head", "tail", "wc", "grep", "egrep", "fgrep", "rg", "which", "type", "file",
    "stat", "du", "df", "ps", "pgrep", "printenv", "echo", "printf", "pwd", "id", "whoami",
    "uname", "cut", "tr", "diff", "cmp", "comm", "sha256sum", "sha1sum",
    "md5sum", "base64", "od", "nl", "tac", "rev", "column", "true", "false", "test", "[", "sleep",
    "readlink", "realpath", "basename", "dirname", "seq", "expr", "strings",
    "hexdump", "getent", "free", "uptime", "lsof", "nproc", "findmnt", "lsblk", "ss", "dig", "host",
    "nslookup", "ping",
}
SHELL_WORDS = {"do", "done", "then", "else", "fi", "!", "{", "}", "while", "until", "if", "elif"}
GIT_READ = {"log", "show", "diff", "status", "rev-parse", "rev-list", "ls-files", "ls-remote",
            "ls-tree", "describe", "blame", "grep", "cat-file", "for-each-ref", "merge-base",
            "shortlog", "reflog", "show-ref", "name-rev", "count-objects", "whatchanged"}
GH_READ_VERBS = {"view", "list", "checks", "diff", "status"}
KUBECTL_READ = {"get", "describe", "logs", "top", "explain", "version", "api-resources", "api-versions",
                "cluster-info", "events"}
DOCKER_READ = {"ps", "images", "logs", "inspect", "version", "info", "top", "port", "history"}
SAFE_REDIRECT = re.compile(r"^(?:[12]?>{1,2}/dev/null|2>&1|>&2|1>&2)$")


def git_ok(args):
    i = 0
    while i < len(args) and args[i] == "-C" and i + 1 < len(args):
        i += 2
    if i >= len(args) or args[i].startswith("-"):
        return False
    sub, rest = args[i], args[i + 1:]
    if any(a.startswith(("--output", "-o")) for a in rest) and sub in {"log", "diff", "show"}:
        return False
    if sub in GIT_READ:
        return True
    if sub == "fetch":   # remote-tracking refs only: no refspec that names a local ref
        return all(":" not in a and not a.startswith("+") for a in rest)
    if sub == "branch":
        return all(a in {"-a", "-r", "-v", "-vv", "--list", "--show-current", "--contains", "--merged",
                         "--no-merged", "--all", "--remotes"} or not a.startswith("-") and rest and rest[0] in
                   {"--list", "--contains", "--merged", "--no-merged"} for a in rest)
    if sub == "remote":
        return not rest or rest[0] in {"-v", "show", "get-url"}
    if sub == "worktree":
        return rest[:1] == ["list"]
    if sub == "tag":
        return not rest or rest[0] in {"-l", "--list", "--contains"}
    if sub == "config":
        return bool(rest) and rest[0] in {"--get", "--get-all", "--list", "-l", "--get-regexp"}
    if sub == "stash":
        return rest[:1] in (["list"], ["show"])
    return False


def gh_ok(args):
    if len(args) >= 2 and args[0] in {"pr", "issue", "run", "repo", "release", "workflow", "label", "project", "search"}:
        return args[1] in GH_READ_VERBS or args[0] == "search"
    if args[:1] == ["api"]:
        bad = {"-X", "--method", "-f", "-F", "--field", "--raw-field", "--input"}
        if any(a in bad or a.startswith(("-X", "--method=", "-f", "-F", "--field=", "--raw-field=", "--input="))
               for a in args[1:]):
            return False
        return not (len(args) > 1 and args[1] == "graphql")   # graphql may carry a mutation body
    return args[:2] in (["auth", "status"],)


def sed_ok(args):
    # Exactly `sed -n Np [FILE]`. GNU sed permutes options, so a trailing or
    # interleaved -i edits in place (siege#1057 safelist suite).
    if len(args) < 2 or args[0] != "-n" or re.fullmatch(r"[0-9]+(,[0-9$]+)?p", args[1]) is None:
        return False
    rest = args[2:]
    return len(rest) <= 1 and not any(a.startswith("-") for a in rest)


def find_ok(args):
    bad = {"-exec", "-execdir", "-ok", "-okdir", "-delete", "-fprint", "-fprint0", "-fprintf", "-fls"}
    return not any(a in bad for a in args)


def simple_ok(words):
    while words and re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", words[0]):
        return False   # an env prefix can change what a tool does; not proven read-only
    if not words:
        return True
    w, args = words[0], words[1:]
    if w in SHELL_WORDS:
        return simple_ok(args)
    if w == "for":   # for NAME in WORDS  (the loop body is a later simple command)
        return True
    if w in {"timeout", "nice", "time"}:
        rest = [a for a in args if not re.match(r"^-|^[0-9.]+[smhd]?$", a)]
        return simple_ok(rest)
    if w in PLAIN:
        return True
    if w == "sort":
        return not any(a in {"-o", "--output"} or a.startswith(("-o", "--output=")) for a in args)
    if w == "uniq":
        return len([a for a in args if not a.startswith("-")]) <= 1   # a second operand is an output file
    if w == "jq":
        flags = {"-r", "-c", "-e", "-s", "-S", "-M", "-C", "-j", "-a", "--raw-output", "--compact-output",
                 "--exit-status", "--slurp", "--sort-keys", "--monochrome-output", "--color-output", "--join-output"}
        opts = [a for a in args if a.startswith("-")]
        return all(o in flags for o in opts) and len([a for a in args if not a.startswith("-")]) <= 2
    if w == "yq":
        return not any(a in {"-i", "--inplace"} or re.match(r"^-[A-Za-z]*i", a) for a in args)
    if w == "date":
        return not any(a in {"-s", "--set"} or a.startswith("--set") for a in args)
    if w == "sed":
        return sed_ok(args)
    if w == "find":
        return find_ok(args)
    if w == "git":
        return git_ok(args)
    if w == "gh":
        return gh_ok(args)
    if w == "kubectl":
        sub = [a for a in args if not a.startswith("-")]
        return bool(sub) and (sub[0] in KUBECTL_READ or sub[:2] in (["config", "view"], ["config", "get-contexts"],
                                                                   ["config", "current-context"]))
    if w == "docker":
        return bool(args) and args[0] in DOCKER_READ
    if w == "env":
        return not args
    return False


def main(command):
    if not command.strip():
        return 1
    if re.search(r"\$\(|`|<\(|>\(|<<", command):
        return 1
    if "\n" in command.strip("\n") or "\r" in command:
        return 1   # multi-line commands are not proven read-only (siege#1057 safelist policy)
    try:
        # A newline separates commands in bash; it must here too (#349 re-review:
        # `ls<newline>bash evil.sh` was proven read-only by its first line).
        lex = shlex.shlex(command, posix=True, punctuation_chars=";&|<>\n")
        lex.whitespace = " \t\r"   # keep newlines as tokens, not whitespace
        lex.whitespace_split = True
        lex.commenters = ""
        tokens = list(lex)
    except ValueError:
        return 1
    words = []
    i = 0
    while i < len(tokens):
        t = tokens[i]
        if t and set(t) <= set(";\n"):
            t = ";"   # any run of ; and newlines separates commands
        if t in {";", "&&", "||", "|", "&", ";;"}:
            if t == "&":
                return 1   # backgrounding is not investigation
            if not simple_ok(words):
                return 1
            words = []
        elif set(t) <= set("<>&|"):
            # Redirection operator: the operator plus its target must be a safe sink.
            target = tokens[i + 1] if i + 1 < len(tokens) else ""
            joined = (words.pop() if words and words[-1] in {"1", "2"} else "") + t + target
            if t == "<" and target:   # reading a file is fine
                i += 2
                continue
            if not SAFE_REDIRECT.match(joined):
                return 1
            i += 2
            continue
        elif "\n" in t:
            return 1   # a newline inside a word (quoting or a \ continuation): not proven
        else:
            words.append(t)
        i += 1
    return 0 if simple_ok(words) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else ""))

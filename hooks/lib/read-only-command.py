#!/usr/bin/env python3
"""Positive read-only classifier for the electinfo mutation gate.

Exit 0 when every simple command in argv[1] is a known read with read-safe
arguments. Exit 3 (veto) when a known verb is used in a way that writes or runs
a program (e.g. `rg --pre`, `sort -o`, `env CMD`); the gate then treats the command as a mutation, so neither the
regex safelist nor a designing gate can admit it. Exit 4 (unproven) for a
compound command (`;` `&&` `||` `|`) not proven read-only, or a guarded verb fed
an unquoted expansion: the first-word safelist must not admit it, since `cat f;
bash evil.sh` starts with a read. Exit 1 otherwise (unknown). This is an allowlist: anything it does not
recognise is "not proven read-only" and the gate falls back to its normal
behaviour. It never authorizes a mutation; it only spares a read the cost of
a task gate (siege#1051, #1057; electinfo#348).
"""
import re
import shlex
import sys

# Bare read verbs whose arguments cannot make them write.
PLAIN = {
    "ls", "cat", "head", "tail", "wc", "grep", "egrep", "fgrep", "which", "type",
    "stat", "du", "df", "ps", "pgrep", "echo", "pwd", "id", "whoami",
    "uname", "cut", "tr", "diff", "cmp", "comm", "sha256sum", "sha1sum",
    "md5sum", "od", "nl", "tac", "rev", "column", "true", "false", "test", "[", "sleep",
    "readlink", "realpath", "basename", "dirname", "seq", "expr", "strings",
    "hexdump", "getent", "free", "uptime", "lsof", "nproc", "findmnt", "lsblk", "dig", "host",
    "nslookup", "cd", "shasum",
}
# Verbs whose options can write or run programs: their arguments must reach the
# per-tool check exactly as bash will see them, so no unquoted expansion.
GUARDED = {"sed", "find", "sort", "uniq", "jq", "yq", "date", "rg", "git", "gh", "kubectl", "docker",
           "timeout", "nice", "time", "base64"}
SHELL_WORDS = {"do", "done", "then", "else", "fi", "!", "{", "}", "while", "until", "if", "elif"}
GIT_READ = {"log", "show", "diff", "status", "rev-parse", "rev-list", "ls-files", "ls-remote",
            "ls-tree", "describe", "blame", "grep", "cat-file", "for-each-ref", "merge-base",
            "shortlog", "show-ref", "name-rev", "count-objects", "whatchanged"}
REMOTE_WRITE = {"add", "set-url", "rename", "remove", "rm", "set-head", "set-branches", "prune", "update"}
GH_READ_VERBS = {"view", "list", "checks", "diff", "status"}
KUBECTL_READ = {"get", "describe", "logs", "top", "explain", "version", "api-resources", "api-versions",
                "cluster-info", "events"}
DOCKER_READ = {"ps", "images", "logs", "inspect", "version", "info", "top", "port", "history"}
# Management-command form (`docker image ls`): the object, then one of its read
# verbs. Every other verb under these objects writes or runs something (#1116).
DOCKER_MGMT_READ = {
    "image": {"ls", "list", "inspect", "history"},
    "container": {"ls", "list", "ps", "inspect", "logs", "top", "port"},
    "volume": {"ls", "list", "inspect"},
    "network": {"ls", "list", "inspect"},
}
SAFE_REDIRECT = re.compile(r"^(?:[12]?>{1,2}/dev/null|2>&1|>&2|1>&2)$")


def long_opt(a, *names):
    """True when `a` is any unambiguous prefix (3+ chars) of one of `names`,
    with or without =VALUE: getopt_long accepts abbreviations."""
    if not a.startswith("--"):
        return False
    n = a.split("=", 1)[0]
    return len(n) >= 3 and any(full.startswith(n) for full in names)


def short_has(a, letters, takes_arg=""):
    """True when `a` is a short-option cluster containing any of `letters`.
    Scanning stops at a letter in `takes_arg`: the rest of the cluster is that
    option's argument (`date -Iseconds` is -I with "seconds", not -s; #1071)."""
    if not (a.startswith("-") and not a.startswith("--") and len(a) > 1):
        return False
    for c in a[1:]:
        if c in letters:
            return True
        if c in takes_arg:
            return False
    return False


def hash_object_writes(args):
    """`git hash-object` writes only with -w/--write. -t takes an argument, so
    `-tw` sets the type to "w" and does not write, while `-wt blob` does (#1079)."""
    return any(long_opt(a, "--write") or short_has(a, "w", "t") for a in args)


def date_sets(args):
    """`date -s X`, `date --set=X`, or a bare MMDDhhmm operand sets the clock (#1087);
    only +FORMAT operands and the values of -d/-r/-f read."""
    takes = {"-d", "--date", "-r", "--reference", "-f", "--file"}
    i = 0
    while i < len(args):
        a = args[i]
        if long_opt(a, "--set") or short_has(a, "s", "dfIr"):
            return True
        if a in takes:
            i += 2
            continue
        if not a.startswith(("-", "+")):
            return True
        i += 1
    return False


def printf_unsafe(args):
    """printf -v NAME assigns a shell variable (`printf -v PATH /x; ls` changes
    what runs next); %n writes through an argument (#1087)."""
    return any(a.startswith("-v") for a in args[:1]) or any("%n" in a for a in args)


def base64_ok(args):
    """Both Darwin and GNU forms are readers only when output stays on stdout.

    Darwin -i takes an input path; GNU -i ignores garbage. Treating it as a
    value option conservatively is safe on both, unlike Darwin's -o output.
    Unknown switches are not certified, including future output options.
    """
    flags = {"-d", "-D", "--decode", "--ignore-garbage", "-h", "--help", "--version"}
    values = {"-i", "--input", "-b", "--break", "-w", "--wrap"}
    i, operands, ended = 0, 0, False
    while i < len(args):
        a = args[i]
        if ended or not a.startswith("-") or a == "-":
            operands += 1
        elif a == "--":
            ended = True
        elif a in flags:
            pass
        elif a.partition("=")[0] in values:
            if "=" not in a:
                i += 1
                if i >= len(args):
                    return False
        elif len(a) > 2 and a[:2] in {"-i", "-b", "-w"}:
            pass
        else:
            return False
        i += 1
    return operands <= 1


def git_ok(args):
    i = 0
    while i < len(args) and args[i] == "-C" and i + 1 < len(args):
        i += 2
    if i >= len(args) or args[i].startswith("-"):
        return False
    sub, rest = args[i], args[i + 1:]
    # Options that run a program or write a file, for any subcommand.
    if any(long_opt(a, "--upload-pack", "--receive-pack", "--exec", "--open-files-in-pager", "--output",
                    "--ext-diff", "--textconv", "--help") for a in rest):
        return False   # --ext-diff runs the configured diff program; --help can launch a pager or browser
    if sub == "grep" and any(short_has(a, "O", "efABCm") for a in rest):
        return False   # -O<prog> runs <prog> on the matches
    if sub in {"ls-remote", "fetch"} and any(short_has(a, "u", "jo") for a in rest):
        return False   # -u <cmd> is --upload-pack
    if sub in {"log", "diff", "show"} and any(short_has(a, "o", "nSGLUMCB") for a in rest):
        return False
    if sub == "reflog":
        return not any(a in {"expire", "delete", "drop", "write"} for a in rest)
    if sub in GIT_READ:
        return True
    if sub == "hash-object":   # computes object names; only -w writes into the object store
        return not hash_object_writes(rest)
    if sub == "fetch":   # remote-tracking refs only: no refspec that names a local ref
        return all(":" not in a and not a.startswith("+") for a in rest)
    if sub == "branch":
        return all(a in {"-a", "-r", "-v", "-vv", "--list", "--show-current", "--contains", "--merged",
                         "--no-merged", "--all", "--remotes"} or not a.startswith("-") and rest and rest[0] in
                   {"--list", "--contains", "--merged", "--no-merged"} for a in rest)
    if sub == "remote":
        # `git remote [-v]`, `git remote [-v] show|get-url ...`. A leading -v does
        # not make what follows a listing: `git remote -v add|set-url ...` writes (#1087).
        r = [a for a in rest if a not in {"-v", "--verbose"}]
        return not r or (r[0] in {"show", "get-url"} and not any(a in REMOTE_WRITE for a in r))
    if sub == "worktree":
        return rest[:1] == ["list"]
    if sub == "tag":
        # List mode only, and no creating/signing/deleting option anywhere:
        # `git tag --list -a x` is not a listing (#1087).
        return (not rest or rest[0] in {"-l", "--list", "--contains"}) and not any(
            long_opt(a, "--annotate", "--sign", "--local-user", "--force", "--delete", "--message", "--file",
                     "--edit", "--create-reflog") or short_has(a, "asufdmFe", "n") for a in rest)
    if sub == "config":
        return bool(rest) and rest[0] in {"--get", "--get-all", "--list", "-l", "--get-regexp"} and not any(
            long_opt(a, "--add", "--unset", "--unset-all", "--replace-all", "--rename-section", "--remove-section",
                     "--edit") or a == "-e" for a in rest)
    if sub == "stash":
        return rest[:1] in (["list"], ["show"])
    return False


KUBECTL_VALUE_FLAGS = {"-n", "--namespace", "--context", "--cluster", "--user", "-s", "--server", "--kubeconfig",
                       "--token", "--as", "--as-group", "--request-timeout", "--certificate-authority",
                       "--client-certificate", "--client-key", "--tls-server-name", "-v", "--v"}
KUBECTL_BOOL_FLAGS = {"--insecure-skip-tls-verify", "-A", "--all-namespaces"}


def kubectl_ok(args):
    """The subcommand is the first word that is not a global option or its value:
    in `kubectl -n get delete pod x`, `get` is the namespace and kubectl runs
    `delete` (#1089). An unknown option before the subcommand is not proven."""
    i = 0
    while i < len(args):
        a = args[i]
        if a.startswith("--") and "=" in a:
            i += 1
        elif a in KUBECTL_VALUE_FLAGS:
            i += 2
        elif a in KUBECTL_BOOL_FLAGS:
            i += 1
        elif a.startswith("-"):
            return False
        else:
            break
    rest = args[i:]
    return bool(rest) and (rest[0] in KUBECTL_READ or rest[:2] in (["config", "view"], ["config", "get-contexts"],
                                                                   ["config", "current-context"]))


def ss_kills(args):
    # -K kills sockets (#1089); -D/--diag=FILE writes raw socket data to FILE (#1092 review).
    return any(long_opt(a, "--kill", "--diag") or short_has(a, "KD", "fAFN") for a in args)


def gh_ok(args):
    if any(long_opt(a, "--web") or short_has(a, "w", "HpqtRJLSB") for a in args[1:]):
        return False   # --web/-w launches a browser (#1089)
    if len(args) >= 2 and args[0] in {"pr", "issue", "run", "repo", "release", "workflow", "label", "project", "search"}:
        return args[1] in GH_READ_VERBS or args[0] == "search"
    if args[:1] == ["api"]:
        for a in args[1:]:
            if long_opt(a, "--method", "--field", "--raw-field", "--input") or short_has(a, "XfF", "Hpqt"):
                return False   # pflag accepts clusters: -iXDELETE is -i -X DELETE
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
        # Only `timeout DURATION CMD...`, `nice CMD...`, `time CMD...`: no wrapper
        # options, and the wrapped command is checked exactly as given.
        rest = args
        if w == "timeout":
            if not rest or re.fullmatch(r"[0-9.]+[smhd]?", rest[0]) is None:
                return False
            rest = rest[1:]
        if not rest or rest[0].startswith("-"):
            return False
        return simple_ok(rest)
    if w in PLAIN:
        return True
    if w == "base64":
        return base64_ok(args)
    if w == "printf":
        return not printf_unsafe(args)
    if w == "sort":
        return not any(long_opt(a, "--output", "--compress-program") or short_has(a, "o", "kStT") for a in args)
    if w == "uniq":
        return len([a for a in args if not a.startswith("-")]) <= 1   # a second operand is an output file
    if w == "jq":
        flags = {"-r", "-c", "-e", "-s", "-S", "-M", "-C", "-j", "-a", "--raw-output", "--compact-output",
                 "--exit-status", "--slurp", "--sort-keys", "--monochrome-output", "--color-output", "--join-output"}
        opts = [a for a in args if a.startswith("-")]
        return all(o in flags for o in opts) and len([a for a in args if not a.startswith("-")]) <= 2
    if w == "yq":
        return not any(long_opt(a, "--inplace", "--split-exp") or short_has(a, "is", "poI") for a in args)
    if w == "date":
        return not date_sets(args)
    if w == "rg":
        return not any(long_opt(a, "--pre", "--pre-glob") for a in args)   # --pre CMD runs CMD per file
    if w == "sed":
        return sed_ok(args)
    if w == "find":
        return find_ok(args)
    if w == "git":
        return git_ok(args)
    if w == "gh":
        return gh_ok(args)
    if w == "kubectl":
        return kubectl_ok(args)
    if w == "ss":
        return not ss_kills(args)
    if w == "docker":
        if len(args) >= 2 and args[0] in DOCKER_MGMT_READ:
            return args[1] in DOCKER_MGMT_READ[args[0]]
        return bool(args) and args[0] in DOCKER_READ
    return False   # env/printenv are not admitted: they print credentials into the transcript


EXPANDS = set("$_{(@*#?!-0123456789'") | set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ")


def segment_expansions(command):
    """Split `command` at unquoted ; & | ( ) and newlines and return, for each
    simple command, (text, expansions): what bash will expand into extra or
    option-shaped words. That is `$` starting a real expansion outside single
    quotes (word splitting / ${X:--delete} / $'..'; a bare `$` before `"` or at a
    word's end is literal), an unquoted glob character that starts a word or sits
    in a word whose first character is `-` (only then can it produce an option:
    `*` matching `-delete`, `--pre*=x` matching `--pre=x`; #1087), and brace
    expansion in unquoted text. Quoted text is literal, so `--jq '{a,b}'` and
    `contents/f.py?ref=x` are not expansions."""
    segs, cur, bare, found, q, i, word_start = [], [], [], set(), None, 0, True
    fresh, dash = True, False   # no content in the current word yet; word starts with "-"

    def close():
        if re.search(r"\{[^{}\s]*(,|\.\.)[^{}\s]*\}", "".join(bare)):
            found.add("{")
        segs.append(("".join(cur), set(found)))

    def content(ch):
        nonlocal fresh, dash
        if fresh:
            fresh, dash = False, ch == "-"

    while i < len(command):
        c = command[i]
        nxt = command[i + 1] if i + 1 < len(command) else ""
        if q is None and c in ";&|()\n":
            close()
            cur, bare, found, word_start, fresh, dash = [], [], set(), True, True, False
            i += 1
            continue
        cur.append(c)
        if q == "'":
            if c == "'":
                q = None
            else:
                content(c)
            bare.append("x")
            word_start = False
        elif q == '"':
            if c == "\\":
                cur.append(nxt)
                content(nxt)
                i += 1
            elif c == '"':
                q = None
            else:
                content(c)
                if c == "$" and nxt in EXPANDS and nxt != "'":
                    found.add("$")
            bare.append("x")
            word_start = False
        else:
            if c == "\\":
                cur.append(nxt)
                content(nxt)
                i += 1
                bare.append("x")
                word_start = False
            elif c in "'\"":
                q = c
                bare.append("x")
                word_start = False
            elif c in " \t<>":
                bare.append(c)
                word_start, fresh, dash = True, True, False
            else:
                content(c)
                if c == "$" and (nxt in EXPANDS or nxt == '"'):   # $"…" is a locale string: bash drops the $
                    found.add("$")
                elif c in "*?[" and (word_start or dash):
                    found.add(c)
                bare.append(c)
                word_start = False
        i += 1
    close()
    return segs


def lead_verbs(text):
    """The verb a simple command runs, plus the one a wrapper runs."""
    try:
        words = shlex.split(text)
    except ValueError:
        return {"?"}
    words = [w for w in words if w not in SHELL_WORDS]
    out = set()
    while words:
        out.add(words[0])
        if words[0] in {"timeout", "nice", "time"}:
            words = words[2:] if words[0] == "timeout" else words[1:]
            continue
        break
    return out


# Verbs only the legacy regex safelist admits, with the options that make them
# write or run a program. The classifier never proves these read-only; it only
# vetoes the unsafe forms so the safelist cannot admit them.
VETO_ONLY = {"env", "file", "tree", "xxd", "ag", "ack"}


def veto_only_unsafe(w, args):
    if w == "env":
        return bool(args)   # env OPTS / env NAME=V CMD runs a program
    if w == "file":
        return any(long_opt(a, "--compile") or short_has(a, "C", "mfFeP") for a in args)
    if w == "tree":
        return any(short_has(a, "o", "LPI") for a in args)   # -o FILE writes FILE
    if w == "xxd":
        return any(short_has(a, "r", "cglos") for a in args)   # -r, -revert: patch a file back
    if w in {"ag", "ack"}:
        return any(long_opt(a, "--pager") for a in args)   # --pager CMD runs CMD
    return False




def main(command):
    if not command.strip():
        return 1
    if re.search(r"\$\(|`|<\(|>\(|<<", command):
        return 1
    # A verb whose options can write must not receive anything bash will expand
    # into an option: $VAR / ${X:--delete} / $'..' / a glob matching `-delete` /
    # brace expansion. Not provable either way, so "unproven" (4), never 0.
    for text, exp in segment_expansions(command):
        if exp and lead_verbs(text) & (GUARDED | VETO_ONLY | {"?"}):
            return 4
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
    compound = False
    i = 0
    while i < len(tokens):
        t = tokens[i]
        if t and set(t) <= set(";\n"):
            t = ";"   # any run of ; and newlines separates commands
        if t in {";", "&&", "||", "|", "&", ";;"}:
            if t == "&":
                return 1   # backgrounding is not investigation
            compound = True
            if not simple_ok(words):
                return compound_verdict(verdict(words), True)
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
    return 0 if simple_ok(words) else compound_verdict(verdict(words), compound)


def compound_verdict(rc, compound):
    return 4 if rc == 1 and compound else rc


def verdict(words):
    """3 when the failing simple command carries an option known to write or run
    a program; else 1 (merely not proven). Unproven is not a mutation: a known
    verb outside the allowlist (`git hash-object`) must not be blocked harder
    than an unknown one."""
    return 3 if unsafe([x for x in words if x not in SHELL_WORDS]) else 1


def unsafe(words):
    if not words:
        return False
    w, args = words[0], words[1:]
    if w in {"timeout", "nice", "time"}:
        rest = args[1:] if w == "timeout" else args
        return unsafe(rest)
    if w in VETO_ONLY:
        return veto_only_unsafe(w, args)
    if w == "rg":
        return any(long_opt(a, "--pre", "--pre-glob") for a in args)
    if w == "sort":
        return any(long_opt(a, "--output", "--compress-program") or short_has(a, "o", "kStT") for a in args)
    if w == "yq":
        return any(long_opt(a, "--inplace", "--split-exp") or short_has(a, "is", "poI") for a in args)
    if w == "date":
        return date_sets(args)
    if w == "base64":
        return not base64_ok(args)
    if w == "printf":
        return printf_unsafe(args)
    if w == "ss":
        return ss_kills(args)
    if w == "sed":
        return any(long_opt(a, "--in-place") or short_has(a, "i", "efl") for a in args)
    if w == "find":
        return not find_ok(args)
    if w == "uniq":
        return len([a for a in args if not a.startswith("-")]) > 1
    if w == "git":
        if any(long_opt(a, "--upload-pack", "--receive-pack", "--exec", "--open-files-in-pager", "--output")
               for a in args):
            return True
        i = 0
        while i < len(args) and args[i] in {"-C", "-c"}:
            i += 2
        sub = next((a for a in args[i:] if not a.startswith("-")), "")
        rest = args[args.index(sub) + 1:] if sub in args else []
        if any(long_opt(a, "--ext-diff", "--textconv", "--help") for a in args):
            return True
        if sub == "remote" and any(a in REMOTE_WRITE for a in rest):
            return True   # `git remote -v add|set-url ...` (#1087)
        if sub == "tag" and (any(long_opt(a, "--annotate", "--sign", "--local-user", "--force", "--delete",
                                          "--message", "--file", "--edit", "--create-reflog")
                                 or short_has(a, "asufdmFe", "n") for a in rest)
                             or (rest and not rest[0].startswith("-"))):
            return True   # creating, signing or deleting a tag, or `git tag NAME`
        if sub == "config" and any(long_opt(a, "--add", "--unset", "--unset-all", "--replace-all", "--rename-section",
                                            "--remove-section", "--edit") or a == "-e" for a in rest):
            return True
        return (sub == "grep" and any(short_has(a, "O", "efABCm") for a in args)
                or sub in {"ls-remote", "fetch"} and any(short_has(a, "u", "jo") for a in args)
                or sub == "hash-object" and hash_object_writes(args))
    if w == "gh" and any(long_opt(a, "--web") or short_has(a, "w", "HpqtRJLSB") for a in args[1:]):
        return True   # --web/-w launches a browser (#1089)
    if w == "gh" and args[:1] == ["api"]:
        return any(long_opt(a, "--method", "--field", "--raw-field", "--input") or short_has(a, "XfF", "Hpqt")
                   for a in args[1:])
    return False


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else ""))

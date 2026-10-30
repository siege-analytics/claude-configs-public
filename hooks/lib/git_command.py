#!/usr/bin/env python3
"""Bounded literal Git normalization for operation policy, never execution.

Reuse the action parser's shell token boundary, resolve -C and -c once, and
read aliases without running them. Unknown global options, dynamic wrappers and
shell aliases are unresolved operations, not authorization from a task gate.
"""
from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys

# Read-only guards must not mutate their installed package when importing.
sys.dont_write_bytecode = True

from task_actions import UnknownShape, shell_tokens

PROTECTED = {"main", "master", "develop", "dev", "development", "staging", "next", "integration"}
BUILTINS = set("add am annotate apply archive bisect blame branch bundle cat-file check-attr check-ignore check-mailmap check-ref-format checkout checkout-index cherry cherry-pick clean clone column commit config count-objects credential describe diff diff-files diff-index diff-tree difftool fast-export fast-import fetch filter-branch fmt-merge-msg for-each-ref format-patch fsck gc get-tar-commit-id grep hash-object help index-pack init instaweb interpret-trailers log ls-files ls-remote ls-tree mailinfo mailsplit maintenance merge merge-base merge-file merge-index merge-one-file merge-tree mergetool mktag mktree multi-pack-index mv name-rev notes pack-objects pack-redundant pack-refs patch-id prune prune-packed pull push range-diff read-tree rebase reflog remote repack replace request-pull rerere reset restore rev-list rev-parse revert rm send-email send-pack shortlog show show-branch show-index show-ref sparse-checkout stage stash status stripspace submodule subtree switch symbolic-ref tag unpack-file unpack-objects update-index update-ref update-server-info var verify-commit verify-pack verify-tag version whatchanged worktree write-tree".split())
SAFE_ENV = {"LANG", "LC_ALL", "LC_CTYPE", "GIT_PAGER", "PAGER", "GIT_TERMINAL_PROMPT", "GIT_OPTIONAL_LOCKS"}


def inspect_git(cwd, *args, config=()):
    """Only fixed read-only Git queries; candidate executable/aliases never run."""
    result = subprocess.run(["git", "-C", cwd, *config, *args], text=True,
                            capture_output=True, timeout=3, check=False)
    if result.returncode not in (0, 1):
        raise UnknownShape("Git repository metadata could not be read")
    return result.stdout.strip() if result.returncode == 0 else ""


def prefix(words, cwd):
    """Resolve literal executable/global options, preserving command -c aliases."""
    args = list(words)
    environment = []
    while args and re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", args[0]):
        environment.append(args.pop(0).split("=", 1)[0])
    if args and os.path.basename(args[0]) in {"command", "env"}:
        wrapper = os.path.basename(args.pop(0))
        if wrapper == "command" and args[:1] == ["--"]:
            args.pop(0)
        while args and re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", args[0]):
            environment.append(args.pop(0).split("=", 1)[0])
        if args and args[0].startswith("-") and any(os.path.basename(a) == "git" for a in args):
            raise UnknownShape("environment wrapper options are unresolved")
    if not args or os.path.basename(args[0]) != "git":
        if args and os.path.basename(args[0]) in {"sudo", "exec", "nice", "timeout"} and any(os.path.basename(a) == "git" for a in args[1:]):
            raise UnknownShape("Git executable wrapper is unresolved")
        return None
    if any(key not in SAFE_ENV for key in environment):
        raise UnknownShape("environment-dependent Git targeting is unresolved")
    args.pop(0)
    config = []
    while args and args[0].startswith("-"):
        option = args.pop(0)
        if option in {"-C", "-c"}:
            if not args:
                raise UnknownShape("Git global option is missing its value")
            value = args.pop(0)
        elif option.startswith(("-C", "-c")) and len(option) > 2:
            value, option = option[2:], option[:2]
        elif option in {"--no-pager", "--paginate", "--no-optional-locks"}:
            continue
        elif option in {"--version", "-v", "--help", "-h"} and not args:
            return {"cwd": cwd, "args": ["version"], "config": config}
        else:
            raise UnknownShape("unsupported Git global option: " + option)
        if option == "-C":
            if value:
                cwd = os.path.realpath(os.path.join(cwd, value))
        else:
            if not re.match(r"^[A-Za-z][A-Za-z0-9.-]*(?:=.*)?$", value):
                raise UnknownShape("invalid literal Git configuration")
            key = value.partition("=")[0].lower()
            safe_keys = {"user.name", "user.email", "core.abbrev", "core.quotepath", "log.date",
                         "diff.algorithm", "diff.renames", "commit.gpgsign", "core.hookspath"}
            if key not in safe_keys and not key.startswith(("color.", "advice.", "alias.")):
                raise UnknownShape("Git configuration override is not proven target/execution safe: " + key)
            config.extend(["-c", value])
    if not args:
        return None
    for _ in range(8):
        if args[0] in BUILTINS:
            return {"cwd": cwd, "args": args, "config": config}
        alias = inspect_git(cwd, "config", "--get", "alias." + args[0], config=config)
        if not alias or alias.startswith("!"):
            raise UnknownShape("unknown or executable Git alias: " + args[0])
        parsed = shell_tokens(alias)
        if any(operator or glob for _, operator, glob in parsed):
            raise UnknownShape("dynamic Git alias cannot be normalized")
        args = [word for word, _, _ in parsed] + args[1:]
        if not args or args[0].startswith("-"):
            raise UnknownShape("Git alias has unsupported global options")
    raise UnknownShape("recursive Git alias cannot be normalized")


def invocations(command, cwd, depth=0):
    """Literal commands only. Preserve quote boundaries through shell_tokens."""
    if depth > 4:
        raise UnknownShape("nested Git wrapper exceeds inspection limit")
    parsed = shell_tokens(command)
    groups, words = [], []
    for word, operator, glob in parsed:
        if glob:
            raise UnknownShape("Git pathname expansion requires explicit operands")
        if operator:
            if word not in {";", "&&", "||", "|"}:
                raise UnknownShape("Git redirection/background shape is unresolved")
            groups.append(words)
            words = []
        else:
            words.append(word)
    groups.append(words)
    if any(g[:1] == ["cd"] for g in groups) and any(op and word != "&&" for word, op, _ in parsed):
        raise UnknownShape("Git directory changes require an explicit && chain")
    found = []
    for words in groups:
        if not words:
            continue
        if words[0] == "cd" and len(words) == 2:
            cwd = os.path.realpath(os.path.join(cwd, words[1]))
            continue
        if os.path.basename(words[0]) in {"bash", "sh", "zsh", "dash"} and words[1:2] == ["-c"]:
            if len(words) < 3:
                raise UnknownShape("shell Git wrapper is missing code")
            found.extend(invocations(words[2], cwd, depth + 1))
            continue
        if words[0] == "eval":
            found.extend(invocations(" ".join(words[1:]), cwd, depth + 1))
            continue
        item = prefix(words, cwd)
        if item:
            found.append(item)
    return found


def in_scope(cwd):
    origin = inspect_git(cwd, "config", "--get", "remote.origin.url")
    match = re.search(r"(?:[:/])([^/:]+)/[^/]+(?:\.git)?$", origin)
    return bool(match and match[1] in os.environ.get("CLAUDE_SCOPED_OWNERS", "siege-analytics").split(":"))


def destructive_reason(item):
    args, config = item["args"], item["config"]
    sub, rest = args[0], args[1:]
    if any(value.partition("=")[0].lower() == "core.hookspath" for value in config[1::2]):
        return "hook registration bypass via -c core.hooksPath"
    if any(value.lower() == "commit.gpgsign=false" for value in config[1::2]):
        return "sign bypass via -c commit.gpgsign=false"
    if any(a == "--no-gpg-sign" for a in rest):
        return "sign bypass via --no-gpg-sign"
    if sub in {"commit", "push", "merge", "rebase"} and "--no-verify" in rest:
        return "hook bypass via --no-verify"
    if sub != "push":
        return ""
    force, mirror, all_refs = False, False, False
    operands, remote, uncertain = [], None, False
    i = 0
    value_flags = {"-o", "--push-option", "--repo", "--receive-pack", "--exec"}
    bool_flags = {"--dry-run", "--porcelain", "--verbose", "--quiet", "--progress", "--tags",
                  "--prune", "--atomic", "--follow-tags", "--no-follow-tags", "--set-upstream",
                  "--delete", "--no-thin", "--thin", "--ipv4", "--ipv6", "--signed", "--no-signed",
                  "--verify", "--force-if-includes", "--no-force-if-includes"}
    while i < len(rest):
        arg = rest[i]
        flag, equals, attached = arg.partition("=")
        if arg == "--":
            operands.extend(rest[i + 1:])
            break
        if flag in value_flags:
            if not equals:
                i += 1
                if i >= len(rest):
                    return "push option is missing its value"
                attached = rest[i]
            if flag == "--repo":
                remote = attached
        elif arg.startswith("-o") and not arg.startswith("--"):
            pass  # attached push-option value is not a short flag cluster
        elif flag == "--force" or flag == "--force-with-lease":
            force = True
        elif arg == "--mirror":
            mirror = True
        elif arg in {"--all", "--branches"}:
            all_refs = True
        elif flag in bool_flags or flag in {"--recurse-submodules", "--signed"} and equals:
            pass
        elif arg.startswith("-") and not arg.startswith("--"):
            force = force or "f" in arg[1:]
            uncertain = uncertain or bool(set(arg[1:]) - set("fuvqnd46"))
        elif arg.startswith("-"):
            uncertain = True
        else:
            operands.append(arg)
        i += 1
    if mirror:
        return "mirror push can replace protected refs"
    refs = operands if remote is not None else operands[1:]
    force = force or any(ref.startswith("+") for ref in refs)
    if not force:
        return ""
    if all_refs or uncertain or not refs:
        return "force-push destination is not explicit"
    for ref in refs:
        destination = ref.rsplit(":", 1)[-1].lstrip("+")
        if any(char in destination for char in "*?["):
            return "force-push destination is not explicit"
        if destination.removeprefix("refs/heads/") in PROTECTED:
            return "force-push to protected branch"
    return ""


def authorized(cwd):
    message = inspect_git(cwd, "log", "-1", "--format=%B")
    parsed = subprocess.run(["git", "-C", cwd, "interpret-trailers", "--parse", "--no-divider"],
                            input=message, text=True, capture_output=True, timeout=3, check=False)
    if parsed.returncode != 0:
        raise UnknownShape("Git authorization trailers could not be read")
    return bool(re.search(r"^Authorized:[ \t]+\S", parsed.stdout, re.MULTILINE))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cwd", required=True)
    parser.add_argument("--policy", choices=("branch", "destructive"), required=True)
    options = parser.parse_args()
    command = sys.stdin.read()
    try:
        items = invocations(command, os.path.realpath(options.cwd or os.getcwd()))
        for item in items:
            if options.policy == "branch":
                if item["args"][0] == "commit" and in_scope(item["cwd"]):
                    branch = inspect_git(item["cwd"], "symbolic-ref", "--quiet", "--short", "HEAD")
                    if branch in PROTECTED:
                        print("BLOCKED: Direct commit to '" + branch + "' is not allowed (resolved Git target).")
                        return 2
            else:
                reason = destructive_reason(item)
                if reason and not authorized(item["cwd"]):
                    print("BLOCKED: " + reason + " (resolved Git operation).")
                    return 2
        print("handled" if items else "none")
        return 0
    except (UnknownShape, OSError, subprocess.SubprocessError) as exc:
        # Unrelated shell computation is outside this specialized policy, but
        # quote/backslash spelling must not hide a literal Git candidate.
        bare = re.sub(r"[\\\"']", "", command)
        if not re.search(r"(?:^|[/\s])git(?:\s|$)", bare):
            print("none")
            return 0
        print("BLOCKED: Git operation cannot be resolved safely: " + str(exc))
        return 2


if __name__ == "__main__":
    sys.exit(main())

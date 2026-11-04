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
import shlex
import subprocess
import sys

# Read-only guards must not mutate their installed package when importing.
sys.dont_write_bytecode = True

from task_actions import UnknownShape, shell_tokens, released_read_verdict, action as classify_action

PROTECTED = {"main", "master", "develop", "dev", "development", "staging", "next", "integration"}
BUILTINS = set("add am annotate apply archive bisect blame branch bundle cat-file check-attr check-ignore check-mailmap check-ref-format checkout checkout-index cherry cherry-pick clean clone column commit config count-objects credential describe diff diff-files diff-index diff-tree difftool fast-export fast-import fetch filter-branch fmt-merge-msg for-each-ref format-patch fsck gc get-tar-commit-id grep hash-object help index-pack init instaweb interpret-trailers log ls-files ls-remote ls-tree mailinfo mailsplit maintenance merge merge-base merge-file merge-index merge-one-file merge-tree mergetool mktag mktree multi-pack-index mv name-rev notes pack-objects pack-redundant pack-refs patch-id prune prune-packed pull push range-diff read-tree rebase reflog remote repack replace request-pull rerere reset restore rev-list rev-parse revert rm send-email send-pack shortlog show show-branch show-index show-ref sparse-checkout stage stash status stripspace submodule subtree switch symbolic-ref tag unpack-file unpack-objects update-index update-ref update-server-info var verify-commit verify-pack verify-tag version whatchanged worktree write-tree".split())
SAFE_ENV = {"LANG", "LC_ALL", "LC_CTYPE", "GIT_PAGER", "PAGER", "GIT_TERMINAL_PROMPT", "GIT_OPTIONAL_LOCKS"}


class UnresolvedLiteralDispatch(UnknownShape):
    """A known executable wrapper is not a proof of absent Git code."""


def inspect_git(cwd, *args, config=()):
    """Only fixed read-only Git queries; candidate executable/aliases never run."""
    result = subprocess.run(["git", "-C", cwd, *config, *args], text=True,
                            capture_output=True, timeout=3, check=False)
    if result.returncode not in (0, 1):
        raise UnknownShape("Git repository metadata could not be read")
    return result.stdout.strip() if result.returncode == 0 else ""


def literal_prefix(words, *, strict=False):
    """Unwrap only the existing literal assignment/command/env boundary."""
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
        if args and args[0].startswith("-") and (strict or any(os.path.basename(a) == "git" for a in args)):
            error = UnresolvedLiteralDispatch if strict else UnknownShape
            raise error("environment wrapper options are unresolved")
    return args, environment


def prefix(words, cwd):
    """Resolve literal executable/global options, preserving command -c aliases."""
    args, environment = literal_prefix(words)
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


def invocations(command, cwd, depth=0, *, strict=False, companions=None, redirect_probe=False):
    """Literal commands only. Preserve quote boundaries through shell_tokens."""
    if depth > 4:
        raise UnknownShape("nested Git wrapper exceeds inspection limit")
    parsed = shell_tokens(command)
    groups, words = [], []
    pending_redirect = False
    for word, operator, glob in parsed:
        if glob:
            raise UnknownShape("Git pathname expansion requires explicit operands")
        if pending_redirect:
            if operator:
                raise UnknownShape("Git redirection target is unresolved")
            pending_redirect = False
            continue
        if operator:
            if redirect_probe and re.fullmatch(r"[0-9]*(?:>>|>&|<&|>\||>|<)|&>>|&>", word):
                pending_redirect = True
                continue
            if word not in {";", "&&", "||", "|"}:
                raise UnknownShape("Git redirection/background shape is unresolved")
            groups.append(words)
            words = []
        else:
            words.append(word)
    groups.append(words)
    if pending_redirect:
        raise UnknownShape("Git redirection target is missing")
    if any(g[:1] == ["cd"] for g in groups) and any(op and word != "&&" for word, op, _ in parsed):
        raise UnknownShape("Git directory changes require an explicit && chain")
    found = []
    for words in groups:
        if not words:
            continue
        if words[0] == "cd" and len(words) == 2:
            cwd = os.path.realpath(os.path.join(cwd, words[1]))
            continue
        dispatch, environment = literal_prefix(words, strict=True) if strict else (words, [])
        if strict and dispatch:
            base = os.path.basename(dispatch[0])
            if base in {"sudo", "exec", "nice", "timeout", "time", "command", "env"}:
                raise UnresolvedLiteralDispatch("literal executable wrapper is unresolved")
            if base in {"bash", "sh", "zsh", "dash", "ksh", "ash", "eval"}:
                if any(name not in SAFE_ENV for name in environment):
                    raise UnresolvedLiteralDispatch("shell environment targeting is unresolved")
                if base != "eval" and (base in {"ksh", "ash"} or dispatch[1:2] != ["-c"]):
                    raise UnresolvedLiteralDispatch("literal shell flags are unresolved")
                if base == "eval" and dispatch[1:2] and dispatch[1].startswith("-"):
                    raise UnresolvedLiteralDispatch("eval flags are unresolved")
        if dispatch and os.path.basename(dispatch[0]) in {"bash", "sh", "zsh", "dash"} and dispatch[1:2] == ["-c"]:
            if len(dispatch) < 3:
                raise UnknownShape("shell Git wrapper is missing code")
            if strict and dispatch[2].startswith("-"):
                raise UnresolvedLiteralDispatch("shell command/options boundary is unresolved")
            found.extend(invocations(dispatch[2], cwd, depth + 1, strict=strict, companions=companions, redirect_probe=redirect_probe))
            continue
        if dispatch and (dispatch[0] == "eval" or strict and os.path.basename(dispatch[0]) == "eval"):
            found.extend(invocations(" ".join(dispatch[1:]), cwd, depth + 1, strict=strict, companions=companions, redirect_probe=redirect_probe))
            continue
        if strict and dispatch and (os.path.basename(dispatch[0]).startswith("git-") or
                       dispatch[0] in {"!", "if", "then", "elif", "while", "until"} and
                       any(os.path.basename(word) == "git" for word in dispatch[1:])):
            raise UnknownShape("unsupported Git control or dashed builtin; use literal git commit")
        item = prefix(words, cwd)
        if item:
            found.append(item)
        elif companions is not None:
            companions.append(words)
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


def ticket_reference(message):
    """The existing platform-neutral traceability grammar, applied per message."""
    if re.search(r"\[no-ticket:[ \t]+Reason:[^]]+;[ \t]*Evidence:[^]]+;[ \t]*Falsification:[^]]+\]", message):
        return True
    if re.search(r"\[no-ticket\]|\[no-ticket:[ \t]*\]", message):
        raise UnknownShape("'[no-ticket]' override now requires evidence chain")
    return bool(re.search(r"\[task:[ \t]+[^]]+\]|#[0-9]+|[A-Z]+-[0-9]+|https?://[^\s]+/(?:issues|browse|tickets|merge_requests|pull|stories|tasks)/[^\s]+", message))



def unresolved_commit_candidate(command, cwd, companions, *, scoped=None):
    """Keep opaque executable payloads as possible code, not presumed prose."""
    import importlib.util
    from pathlib import Path
    spec = importlib.util.spec_from_file_location("ticket_backstop_text", Path(__file__).with_name("command-text.py"))
    text = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(text)
    if companions is None:
        candidates = [text.strip_heredocs(command)]
    else:
        candidates = []
        for words in companions:
            literal = shlex.join(words)
            shape = classify_action(literal, cwd)
            if released_read_verdict(literal) == 0 or shape.get("read_only") or shape.get("metadata_only"):
                continue
            # Plain in-place substitutions contain data, not sed execution flags.
            sed = words[3:] if words[:3] == ["sed", "-i", ""] else words[2:] if words[:2] == ["sed", "-i"] else []
            if len(sed) >= 2 and sed[0].startswith("s") and len(sed[0]) >= 2:
                expression = sed[0]
                delimiter = expression[1]
                parts = expression[1:].split(delimiter)
                if (not delimiter.isalnum() and not delimiter.isspace() and delimiter != "\\"
                        and "\\" not in expression and "\n" not in expression and len(parts) == 4
                        and not parts[0] and all(flag in "gpI0123456789" for flag in parts[3])
                        and all(not filename.startswith("-") for filename in sed[1:])):
                    continue
            if words[:3] in (["gh", "issue", "create"], ["gh", "pr", "create"],
                            ["gh", "issue", "comment"], ["gh", "pr", "comment"]):
                # Built-in content bodies are data; opaque executors stay code.
                candidates.append(text.code_only(literal))
            else:
                candidates.append(" ".join(words))
    candidate = any(re.search(r"(?:^|[^0-9A-Za-z])git\s+commit(?:[^0-9A-Za-z]|$)", value)
                    for value in candidates)
    return bool(candidate and (in_scope(cwd) if scoped is None else scoped))


def ticket_policy(command, cwd):
    """Check effective messages after typed Git dispatch, never incidental argv."""
    import importlib.util
    from pathlib import Path
    if released_read_verdict(command) == 0:
        return
    helper = Path(__file__).with_name("commit-message-source.py")
    spec = importlib.util.spec_from_file_location("ticket_message_source", helper)
    source = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(source)
    try:
        # Preserve direct/heredoc grammar; ordinary compound commands instead
        # use structured invocations so each effective message is independent.
        try:
            direct_tokens = shell_tokens(command)
        except UnknownShape:
            direct_tokens = None  # The released bounded heredoc parser may know it.
        if source.DIRECT_COMMIT_RE.match(command) and not (direct_tokens and any(op for _, op, _ in direct_tokens)):
            if not in_scope(cwd):
                return
            message = source.resolve(command, cwd, forbid_edit=True)
            if message is not None:
                if not ticket_reference(message):
                    raise UnknownShape("effective commit message has no ticket reference or structured task override")
                return
        companions = []
        items = invocations(command, cwd, strict=True, companions=companions)
        commits = [item for item in items if item["args"][0] == "commit" and in_scope(item["cwd"])]
        if not commits:
            if unresolved_commit_candidate(command, cwd, companions):
                raise UnknownShape("literal Git commit remains unresolved; use a supported direct commit form")
            return
        # Earlier mutation can replace an alias/configuration or message file
        # after the hook reads it. Split such work from commit inspection.
        other_commands = companions + [["git", *item["args"]] for item in items if item["args"][0] != "commit"]
        if any(released_read_verdict(shlex.join(words)) != 0 for words in other_commands):
            raise UnknownShape("separate configuration/file mutations from commit calls so message provenance is stable")
        for item in commits:
            message = source.resolve(shlex.join(["git", *item["args"]]), item["cwd"], forbid_edit=True)
            if message is None or not ticket_reference(message):
                raise UnknownShape("effective commit message has no ticket reference or structured task override")
    except source.MessageSourceError as error:
        raise UnknownShape(str(error)) from error


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cwd", required=True)
    parser.add_argument("--policy", choices=("branch", "destructive", "ticket"), required=True)
    options = parser.parse_args()
    command = sys.stdin.read()
    try:
        if command.strip() and released_read_verdict(command) == 0:
            print("handled")
            return 0
        if options.policy == "ticket":
            ticket_policy(command, os.path.realpath(options.cwd or os.getcwd()))
            print("handled")
            return 0
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
        if options.policy == "ticket":
            try:
                scoped = in_scope(os.path.realpath(options.cwd or os.getcwd()))
            except (UnknownShape, OSError, subprocess.SubprocessError):
                scoped = True  # Unavailable scope cannot authorize a Git candidate.
            try:
                probed_companions = []
                probed = invocations(command, os.path.realpath(options.cwd or os.getcwd()), strict=True,
                                     redirect_probe=True, companions=probed_companions)
            except (UnknownShape, OSError, subprocess.SubprocessError) as probe_error:
                if isinstance(probe_error, UnresolvedLiteralDispatch):
                    # Its argument may be code that the data heuristic cannot
                    # unwrap. Preserve the existing conservative candidate test.
                    candidate = re.sub(r"[\\\"']", "", command)
                    if re.search(r"(?:^|[^0-9A-Za-z_.-])git(?:[-\s]|$)", candidate) and scoped:
                        print("BLOCKED: Cannot safely determine ticketed Git commit: " + str(exc))
                        return 2
                    print("handled")
                    return 0
                # Other ambiguous shapes retain the shared conservative boundary.
            else:
                if not any(item["args"][0] == "commit" for item in probed):
                    if unresolved_commit_candidate(command, os.path.realpath(options.cwd or os.getcwd()), probed_companions, scoped=scoped):
                        print("BLOCKED: Cannot safely determine ticketed Git commit: " + str(exc))
                        return 2
                    print("handled")  # No code-only commit candidate remains.
                    return 0
                print("BLOCKED: Cannot safely determine ticketed Git commit: " + str(exc))
                return 2
            if unresolved_commit_candidate(command, os.path.realpath(options.cwd or os.getcwd()), None, scoped=scoped):
                print("BLOCKED: Cannot safely determine ticketed Git commit: " + str(exc))
                return 2
            # Use the shared code/data boundary, including shell/eval payload
            # unwrapping. Quoted PR prose is not a Git invocation.
            import importlib.util
            from pathlib import Path
            spec = importlib.util.spec_from_file_location("ticket_command_text", Path(__file__).with_name("command-text.py"))
            command_text = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(command_text)
            try:
                parsed = shell_tokens(command)
            except UnknownShape:
                normalized = command  # Keep ambiguous code for conservative inspection.
            else:
                # Candidate inspection only: never execute this reconstruction.
                normalized = " ".join(word if operator else shlex.quote(word)
                                      for word, operator, _ in parsed)
            candidate = command_text.code_only(normalized)
            if not re.search(r"(?:^|[^0-9A-Za-z_.-])git(?:[-\s]|$)", candidate) or not scoped:
                print("handled")  # Unrelated shell computation is not a ticket event.
                return 0
            print("BLOCKED: Cannot safely determine ticketed Git commit: " + str(exc))
            return 2
        try:
            probed = invocations(command, os.path.realpath(options.cwd or os.getcwd()), strict=True, redirect_probe=True)
        except (UnknownShape, OSError, subprocess.SubprocessError):
            pass  # A Git operation or unresolved shape keeps the existing policy fallback.
        else:
            if not probed:
                print("none")
                return 0
        bare = re.sub(r"[\\\"']", "", command)
        if not re.search(r"(?:^|[/\s])git(?:\s|$)", bare):
            print("none")
            return 0
        print("BLOCKED: Git operation cannot be resolved safely: " + str(exc))
        return 2


if __name__ == "__main__":
    sys.exit(main())

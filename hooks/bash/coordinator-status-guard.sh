#!/usr/bin/env bash
# Hook: coordinator-status-guard
# Enforces: coordinator lane/status transitions must carry evidence.
# Trigger: PreToolUse on Bash commands that update GitHub issues/PRs.
#
# Standalone literal issue/PR comments, body-only edits and comment-mode reviews
# describe work; their vocabulary does not authorize a workflow transition.
# This hook leaves Task/target authorization to UMG and artifact validation to
# its existing consumers. Unsupported/compound posts cannot borrow this lane.
# Actual close/reopen/ready, approval and API state changes retain their proof.
# Ref: claude-configs-public#609, #1164, #1245

set -uo pipefail
source "$(f="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/../lib/hook-path.sh"; [[ -f "$f" ]] && printf '%s' "$f" || printf /dev/null)"

INPUT=$(cat)
# Fast skip (#1083): exit before starting python3 when the tool payload's
# command cannot match this hook's trigger. Only taken when tool_input's first
# key is a non-empty "command" (an empty or missing command keeps the git-push
# fallback) and the command uses no JSON escape other than \n \t \r \" \\ \/
# (\u, \f, \b could hide letters or whitespace). \n \t \r become spaces, so an
# escaped newline before the trigger still counts as a boundary. Git-hook
# invocations (refs on stdin, no JSON) take the full path.
_FAST_CMDS=$(printf '%s' "$INPUT" | grep -oE '"command"[[:space:]]*:[[:space:]]*"(\\.|[^"\\])*"' 2>/dev/null || true)
# A long command takes the full path (#1098): bash substitutions slow down
# superlinearly under a UTF-8 locale, and past the hook timeout a skip check
# would let the command through. 16 KiB keeps the check in milliseconds.
_FAST_FULL=0; (( ${#_FAST_CMDS} > 16384 )) && { _FAST_FULL=1; _FAST_CMDS=""; }
_FAST_ESC="${_FAST_CMDS//'\\'/}"; _FAST_ESC="${_FAST_ESC//'\"'/}"; _FAST_ESC="${_FAST_ESC//'\/'/}"
_FAST_ESC="${_FAST_ESC//'\n'/}"; _FAST_ESC="${_FAST_ESC//'\t'/}"; _FAST_ESC="${_FAST_ESC//'\r'/}"
_FAST_CMDS="${_FAST_CMDS//'\n'/ }"; _FAST_CMDS="${_FAST_CMDS//'\t'/ }"; _FAST_CMDS="${_FAST_CMDS//'\r'/ }"
# The shell rebuilds words from quotes and backslashes (#1098): `git "add"`,
# `g\it add` and `git  add` all run git add. Match the trigger against the text
# as written and against a copy with quote and backslash characters dropped and
# blanks squeezed; skip only if neither matches. A command containing ANSI-C
# $'...' (which can spell any byte) takes the full path.
[[ "$_FAST_CMDS" == *"\$'"* ]] && _FAST_FULL=1
# A quote or backslash between two letters or digits (`pr"x"`, `x\git`) joins
# words; only the full path's quote handling decides what that runs. In the
# JSON text a shell `"` or `\` is itself escaped, hence the leading backslash.
[[ "$_FAST_CMDS" == *[[:alnum:]]\\[\"\\][[:alnum:]]* || "$_FAST_CMDS" == *[[:alnum:]]\'[[:alnum:]]* ]] && _FAST_FULL=1
_FAST_BUILT="${_FAST_CMDS//[\"\'\\]/}"
while [[ "$_FAST_BUILT" == *"  "* ]]; do _FAST_BUILT="${_FAST_BUILT//  / }"; done
# shlex joins quoted pieces (g''h, "g"h, g\h -> gh): also test with quotes removed.
_FAST_BARE="${_FAST_CMDS//[\"\'\\]/}"

_FAST_FIRST='"tool_input"[[:space:]]*:[[:space:]]*[{][[:space:]]*"command"[[:space:]]*:[[:space:]]*"[^"]'
_FAST_RE='gh'
if [[ $_FAST_FULL == 0 && "$INPUT" =~ $_FAST_FIRST && "$_FAST_ESC" != *'\'* ]] && ! [[ "$_FAST_CMDS" =~ $_FAST_RE || "$_FAST_BUILT" =~ $_FAST_RE || "$_FAST_BARE" =~ $_FAST_RE ]]; then exit 0; fi
HOOK_DIR="$(cd "$(dirname "$0")" && pwd)"
EXTRACT="$HOOK_DIR/../lib/extract-json.py"
COMMAND=$(printf '%s' "$INPUT" | python3 "$EXTRACT" tool_input.command 2>/dev/null || true)

if [[ -z "$COMMAND" ]]; then
    exit 0
fi

CWD=$(printf '%s' "$INPUT" | python3 "$EXTRACT" cwd 2>/dev/null || true)
# The existing host/session resolver, rather than the shared GitHub login,
# supplies own-task identity to the narrow mechanical transition proof.
_HOOK_METADATA=$(printf '%s' "$INPUT" | python3 "$HOOK_DIR/../lib/hook_payload.py") || exit 2
export CCP_HOOK_INPUT_JSON="$_HOOK_METADATA"
python3 -B - "$COMMAND" "$HOOK_DIR/../lib" "$CWD" <<'PY'
import re
import shlex
import sys
from pathlib import Path

command = sys.argv[1]
sys.path.insert(0, sys.argv[2])
import task_actions
from task_actions import action as classify_action
import os
# Standalone descriptive CLI posts are metadata, not workflow transitions.
# UMG owns task/target authority; this lane grants no permission to execute gh.
from github_metadata_comment import metadata_comment

metadata = metadata_comment(command, sys.argv[3])
# Preserve the existing whole-command typed metadata proof, including its
# supported cd/edit-last forms. A comment member cannot donate this verdict.
if metadata is False and classify_action(command, sys.argv[3] or os.getcwd()).get('metadata_only'):
    sys.exit(0)
if metadata is not None:
    if metadata:
        sys.exit(0)
    print('BLOCKED: metadata-comment lane requires one literal supported body-only command; state operations and shell composition retain their own checks.', file=sys.stderr)
    sys.exit(2)

# A PR-creation description is not an existing lane's status transition.
# This is only a status-text exemption: do not add PR creation to the shared
# metadata-post lane. UMG, review, topology and destructive-action guards still
# authorize the operation. A composed command cannot borrow this verdict.
try:
    from git_command import SAFE_ENV, literal_prefix
    create_tokens = task_actions.shell_tokens(command)
    create_words, create_environment = literal_prefix(
        [word for word, _, _ in create_tokens], strict=True)
    if (not any(operator or globs for _, operator, globs in create_tokens)
            and not any(name not in SAFE_ENV for name in create_environment)
            and len(create_words) >= 3
            and create_words[0].rsplit('/', 1)[-1] == 'gh'
            and create_words[1:3] == ['pr', 'create']):
        sys.exit(0)
except ValueError:
    pass  # Unresolved syntax retains the existing conservative checks.

# Text edits to existing artifacts are not coordinator state transitions.
shape = classify_action(command, sys.argv[3] or os.getcwd())
if shape.get("read_only") or shape.get("metadata_only"):
    sys.exit(0)
# File-output effects belong to UMG, not status-claim inspection. Prove the
# entire reader chain with literal output destinations replaced ONLY in this
# in-memory proof. Keep real operators/data; never execute or rewrite the command.
def reader_chain_with_outputs(text):
    try:
        parts = task_actions.shell_tokens(text)
    except ValueError:
        return False, []
    proof, words, github_reads = [], [], []

    def finish_reader():
        from git_command import literal_prefix
        invocation = list(words)
        # Detect the executable behind supported wrappers, never gh-looking
        # argument data. This unwrap is NOT a reader/permission verdict: the
        # complete original chain still needs the canonical proof below.
        # Literal wrapper nesting cannot exceed its input character count.
        for _ in range(len(text) + 1):
            while invocation and re.match(r'^[A-Za-z_][A-Za-z0-9_]*=', invocation[0]):
                invocation.pop(0)
            if not invocation:
                return
            name = invocation[0].rsplit('/', 1)[-1]
            if name == 'gh':
                github_reads.append(task_actions.released_read_verdict(shlex.join(invocation)) == 0)
                return
            try:
                if name == 'command':
                    invocation, _ = literal_prefix(invocation, strict=True)
                else:
                    nested = task_actions._wrapped_command(invocation)
                    if nested is None:
                        return
                    invocation = nested
            except ValueError:
                return

    # Collect effects independently of reader-proof syntax. A later glob or
    # unsupported output cannot erase a real GitHub transition already seen.
    i = 0
    while i < len(parts):
        value, operator, _ = parts[i]
        if operator and re.fullmatch(r"[0-9]*(?:>>|>&|<&|>\||>|<)|&>>|&>", value):
            i += 2
            continue
        if operator:
            finish_reader()
            words = []
        else:
            words.append(value)
        i += 1
    finish_reader()

    i = 0
    while i < len(parts):
        value, operator, globs = parts[i]
        if globs:
            return False, github_reads
        if operator and re.fullmatch(r"[0-9]*(?:>>|>&|<&|>\||>|<)|&>>|&>", value):
            i += 1
            if i >= len(parts) or parts[i][1] or parts[i][2] or parts[i][0].startswith('~'):
                return False, github_reads
            target = parts[i][0]
            if value in {'>', '>>', '1>', '1>>', '2>', '2>>'}:
                target = '/dev/null'
            proof.extend((value, shlex.quote(target)))
        elif operator:
            if value not in {'&&', '||', ';', '|'}:
                return False, github_reads
            proof.append(value)
        else:
            proof.append(shlex.quote(value))
        i += 1
    return task_actions.released_read_verdict(' '.join(proof)) == 0, github_reads

reader_chain, github_reads = reader_chain_with_outputs(command)
if reader_chain:
    sys.exit(0)
# Legacy first-gh inspection must not let a GET hide a later real transition.
# Existing whole-command typed metadata exceptions above remain unchanged.
if len(github_reads) > 1 and not all(github_reads):
    print('BLOCKED: mixed GitHub operations require separately checked status calls; split the command.', file=sys.stderr)
    sys.exit(2)

# #1210 owns the literal REST review-reply classifier and UMG authorization.
# A reply's prose is not a workflow transition. Reuse that typed interface
# when present in the combined source; never inspect arbitrary POST bodies as
# grants or duplicate its GitHub lookup/role authorization here.
review_reply = getattr(task_actions, 'github_review_reply', None)
if review_reply and re.match(r'^\s*gh\s+api\s', command):
    try:
        reply_tokens = task_actions.shell_tokens(command)
    except ValueError:
        reply_tokens = []
    if reply_tokens and not any(operator or globs for _, operator, globs in reply_tokens):
        try:
            if review_reply([word for word, _, _ in reply_tokens], sys.argv[3] or os.getcwd()):
                sys.exit(0)
        except ValueError as error:
            print('BLOCKED: invalid typed GitHub review reply: ' + str(error), file=sys.stderr)
            sys.exit(2)
normalized_command = command.replace("$(which gh)", "gh")

try:
    tokens = shlex.split(normalized_command)
except ValueError:
    tokens = normalized_command.split()

# Find the first gh subcommand in shell-ish command tokens. Accept common
# wrapper and absolute-path forms used by shell/Codex sessions: `command gh`,
# `env gh`, `/usr/bin/gh`, `/opt/homebrew/bin/gh`, and `$(which gh)`.
idx = None
for i, tok in enumerate(tokens):
    base = tok.rsplit("/", 1)[-1]
    if base == "gh" and i + 1 < len(tokens) and tokens[i + 1] in {"issue", "pr", "api"}:
        idx = i
        break
if idx is None:
    sys.exit(0)

resource = tokens[idx + 1]
action = tokens[idx + 2] if idx + 2 < len(tokens) else ""
args = tokens[idx + 3:]
api_path = ""
if resource == "api":
    resource = "api"
    api_args = tokens[idx + 2:]
    for tok in api_args:
        if re.search(r'/(?:issues|pulls)/[0-9]+(?:/comments)?(?:$|[/?#])', tok):
            api_path = tok
            break
    action = "api"
    args = api_args
    if re.search(r'/issues/[0-9]+/comments(?:$|[/?#])', api_path):
        resource = "issue"
        action = "comment"
    elif re.search(r'/issues/[0-9]+(?:$|[/?#])', api_path):
        resource = "issue"
        action = "edit"
    elif re.search(r'/pulls/[0-9]+(?:$|[/?#])', api_path):
        resource = "pr"
        action = "edit"

# Read-only subcommands carry no status claim to evaluate; never gate them.
# A completion/evidence gate firing on `gh pr view --json state,mergedAt` is a
# false positive: the --json field names, not a status update, match the
# vocabulary. Reads are outside this guard's domain (status comments + state
# transitions). Ref: claude-configs-public#940.
READ_ACTIONS = {"view", "list", "diff", "checks", "status"}
if resource in {"issue", "pr"} and action in READ_ACTIONS:
    sys.exit(0)
# `gh api` without a mutating method or a request-body/field flag is a GET read.
# This is the retained fallback for API paths outside the shared reader proof;
# issue-path status inspection above is not itself evidence of an HTTP write.
if resource == "api":
    _api_args = tokens[idx + 2:]
    _mutating_method = any(t in {"-X", "--method"} for t in _api_args) and any(
        t.upper() in {"POST", "PUT", "PATCH", "DELETE"} for t in _api_args
    )
    _has_body = any(
        t in {"-f", "--field", "--raw-field", "--input", "-F"}
        or t.startswith(("-f=", "--field=", "--raw-field=", "--input=", "-F="))
        for t in _api_args
    )
    if not _mutating_method and not _has_body:
        sys.exit(0)

BODY_FLAGS = {"--body", "-b", "--comment", "-c", "--message", "-m", "--title"}
BODY_FILE_FLAGS = {"--body-file", "-F"}
EDITOR_FLAGS = {"--editor", "-e", "--web", "-w"}
API_FIELD_FLAGS = {"-f", "--field", "-F", "--raw-field"}
API_INPUT_FLAGS = {"--input"}

def flag_value(flags):
    for i, tok in enumerate(args):
        if tok in flags and i + 1 < len(args):
            return args[i + 1]
        for flag in flags:
            if tok.startswith(flag + "="):
                return tok.split("=", 1)[1]
    return ""


def bool_flag_present(flags):
    for tok in args:
        if tok in flags:
            return True
        for flag in flags:
            if tok.startswith(flag + "="):
                value = tok.split("=", 1)[1].strip().lower()
                if value not in {"0", "false", "no", "off"}:
                    return True
    return False


def api_field_value(name):
    prefixes = (f"{name}=", f"{name}:=")
    for i, tok in enumerate(args):
        candidates = []
        if tok in API_FIELD_FLAGS and i + 1 < len(args):
            candidates.append(args[i + 1])
        for flag in API_FIELD_FLAGS:
            if tok.startswith(flag + "="):
                candidates.append(tok.split("=", 1)[1])
        for candidate in candidates:
            for prefix in prefixes:
                if candidate.startswith(prefix):
                    return candidate[len(prefix):]
    return ""

body = flag_value(BODY_FLAGS)
body_file = flag_value(BODY_FILE_FLAGS)
editor_body = bool_flag_present(EDITOR_FLAGS)
api_input = flag_value(API_INPUT_FLAGS)
if action == "comment":
    body = body or api_field_value("body")
state_value = api_field_value("state")
state_reason_value = api_field_value("state_reason")
api_state_transition = bool(api_path and (state_value or state_reason_value))
unreadable_body_file = ""
uninspectable_body = ""
uninspectable_editor_body = ""
uninspectable_api_payload = ""
if action in {"comment", "edit", "review"} and editor_body:
    uninspectable_editor_body = "editor"
if action in {"comment", "edit"} and api_input:
    uninspectable_api_payload = api_input
if body and body.startswith("@") and action == "comment":
    uninspectable_api_payload = body
if body and re.search(r'\$\(|`|\$\{![^}]+\}|\$\{?[A-Za-z_][A-Za-z0-9_]*\}?|\$[0-9#@*?!-]', body):
    uninspectable_body = body
if body_file:
    if body_file in {"-", "/dev/stdin", "/dev/fd/0", "/proc/self/fd/0"}:
        unreadable_body_file = body_file
    else:
        try:
            body = Path(body_file).read_text()
        except OSError:
            unreadable_body_file = body_file

text = body or normalized_command
lower = text.lower()

# Scope: ordinary issue comments are allowed. The guard only engages when a
# command performs a state transition directly, or when a comment looks like a
# coordinator lane/status update.
state_action = action in {"close", "reopen", "ready"} or (resource == "pr" and action == "review") or api_state_transition
coordinator_marker = re.search(
    r'\b(status|state|lane|coordinator|transition|ready for|done|complete|completed|resolved|shipped|merged|blocked|blocker)\b',
    lower,
)
if unreadable_body_file and action in {"comment", "edit", "review"}:
    print("BLOCKED: coordinator status guard cannot inspect --body-file content.", file=sys.stderr)
    print("Use an inline --body value or a readable file path instead of stdin/process substitution.", file=sys.stderr)
    sys.exit(2)

if uninspectable_body and action in {"comment", "edit", "review"}:
    print("BLOCKED: coordinator status guard cannot inspect shell-expanded --body content.", file=sys.stderr)
    print("Use a literal inline --body value or a readable --body-file path instead of variables/command substitution.", file=sys.stderr)
    sys.exit(2)

if uninspectable_api_payload and action in {"comment", "edit"}:
    print("BLOCKED: coordinator status guard cannot inspect gh api file/input payload content.", file=sys.stderr)
    print("Use literal inspectable fields instead of body=@file, body=@-, or --input payloads for status updates.", file=sys.stderr)
    sys.exit(2)

if uninspectable_editor_body and action in {"comment", "edit", "review"}:
    print("BLOCKED: coordinator status guard cannot inspect editor/web-supplied body content.", file=sys.stderr)
    print("Use a literal inline --body value or a readable --body-file path instead of --editor/--web for status updates.", file=sys.stderr)
    sys.exit(2)

EVIDENCE_HELP = "Required evidence: owner/maintainer signoff, merge/branch target evidence, and deploy/UAT/rollout evidence or N/A."
# Gate-required think-pipeline artifacts (#1164). The Tier C artifacts-posted
# gate needs pre-mortem, investigation and junior/senior posts on the ticket;
# those are risk and plan documents by nature, not lane status updates.
ARTIFACT_HINT = (
    "If this is a gate-required think-pipeline artifact (pre-mortem, investigation fact sheet, "
    "junior/senior review, design note), make its first line a heading naming it (e.g. '## Pre-Mortem') "
    "and include a 'Ticket: <task reference>' line. Completion words outside its hypothetical fields "
    "(Scenario, Mitigation, Success criteria, ...) still need evidence. Ref: #1164."
)


def block(*lines):
    for line in lines:
        print(line, file=sys.stderr)
    # Only a body that already reads as an artifact gets the format hint; a
    # plain status update is not coached toward the artifact lane.
    if action == "comment" and not state_action and ARTIFACT_WORDS.search(lower):
        print(ARTIFACT_HINT, file=sys.stderr)
    sys.exit(2)


def missing_evidence(lowered):
    evidence = {
        "owner_signoff": re.search(r'\b(owner|maintainer|operator)\b.{0,40}\b(approved|signoff|sign-off|signed off|confirmed)\b|\b(approved|signed off|confirmed)\b.{0,40}\bby\b.{0,20}\b(owner|maintainer|operator)\b|\bapproval thread\b.{0,80}\bhttps?://|\bowner response\b.{0,80}\bhttps?://', lowered, re.S),
        "merge_or_branch": re.search(r'\b(merged|merge commit|merge evidence|pr #[0-9]+|pull/[0-9]+|branch target|target branch|base branch|develop|main|hotfix)\b|\b[0-9a-f]{7,40}\b', lowered),
        "rollout": re.search(r'\b(deploy|deployed|deployment|uat|user acceptance|rollout|release|released|backfill|reindex|migration|not applicable|n/a)\b', lowered),
    }
    return [name for name, ok in evidence.items() if not ok]


COMPLETION_RE = re.compile(r'\b(done|complete|completed|resolved|closed|ready|shipped|released|merged|unblocked|green|go)\b')
ARTIFACT_WORDS = re.compile(r'\b(pre-?mortem|investigation|fact sheet|junior|senior|design notes?|tiger)\b')
# The marker is the body's first non-blank line, so a heading appended to a
# status update cannot relabel it; a task reference ties it to one task.
ARTIFACT_HEADING = re.compile(
    r'#{1,6}[ \t]+[*_`]*(?:pre[- ]?mortem|investigation|fact sheet|junior task description|junior review|junior[ /-]senior review|senior adversarial checklist|senior review|pre-implementation comprehension|design notes?)\b',
    re.I,
)
ARTIFACT_TASK_REF = re.compile(
    r'^[ \t>*_-]*(?:ticket|task[ _-]?id|refs?|issue)[*_]*[ \t]*:[*_]*[ \t]*(?:[\w.-]+/[\w.-]+)?#[0-9]+\b'
    r'|^[ \t>*_-]*task[ _-]?id[*_]*[ \t]*:[*_]*[ \t]*(?!n/?a\b|none\b|tbd\b)[a-z0-9][\w./-]{2,}',
    re.I | re.M,
)
# Fields the pre-mortem, investigation and junior/senior formats define for
# hypothetical or planned content (skills/pre-mortem, skills/investigate,
# skills/self-review). A completion word there describes a risk or a goal.
ARTIFACT_HYPOTHETICAL_FIELDS = {
    "scenario", "trigger", "trigger condition", "risk", "risks", "failure mode", "what could go wrong",
    "mitigation", "why it's handled", "what it is", "why it's deferred", "cost of deferral",
    "trigger for revisiting", "intended behavior", "intended outcome", "success criteria",
    "steps", "steps to get there", "hypothesis", "falsification", "falsification criteria",
    "falsifiable-by", "definition of done", "open question", "open questions", "assumption", "assumptions",
}
ARTIFACT_CONDITIONAL_START = re.compile(
    r'(?:if|when|whenever|unless|until|once|could|might|would|may|should|suppose|assuming|in case)\b'
)


# Completion of the artifact itself is not completion of the project lane.
# Remove only the named subject/predicate, retaining other clauses to inspect.
ARTIFACT_RESULT = re.compile(
    r'\b(?:review|investigation|fact[ -]sheet|audit|checklist|(?:(?:named|listed|adversarial)[ \t]+)?checks)'
    r'[ \t]+(?:(?:is|are|was|were|has[ \t]+been|have[ \t]+been)[ \t]+)?(?:complete|completed|done)\b'
)


def artifact_factual_lines(lowered):
    """Keep factual clauses; wrapped hypothetical fields cannot supply evidence."""
    factual, hypothetical = [], False
    for raw in lowered.splitlines():
        line = re.sub(r'^(?:[ \t>#*_`|-]+|\[[ x]\][ \t]*|[0-9]+[.)][ \t]*)+', '', raw)
        line = re.sub(r'[*_`]+', '', line).strip()
        if not line:
            hypothetical = False
            continue
        field = re.match(r'(.{1,40}?)(?::|[ \t]+(?:—|--)[ \t]+)[ \t]*(.*)', line)
        if field:
            hypothetical = field.group(1).strip() in ARTIFACT_HYPOTHETICAL_FIELDS
        elif hypothetical and not raw[:1].isspace():
            hypothetical = False
        elif raw.lstrip().startswith(('#', '-', '*')):
            hypothetical = False
        if hypothetical:
            continue
        # A conditional opener applies to its clause, not a later assertion.
        clauses = re.split(r'[;.!?][ \t]+', line)
        for index, clause in enumerate(clauses):
            value = field.group(2) if index == 0 and field else clause
            if ARTIFACT_CONDITIONAL_START.match(value):
                continue
            factual.append(clause)
    return factual


def artifact_claims(lines):
    return [line for line in lines if COMPLETION_RE.search(ARTIFACT_RESULT.sub('', line))]


body_lines = [line.strip() for line in (body or "").splitlines() if line.strip()]
# A plans/ artifact posted verbatim opens with YAML front matter (required by
# ticket-propagation-guard); its marker heading is the first line after it.
# The claim scan below still covers the front matter.
if body_lines[:1] == ["---"] and "---" in body_lines[1:]:
    body_lines = body_lines[body_lines.index("---", 1) + 1:]
first_line = body_lines[0] if body_lines else ""
if (
    action == "comment"
    and not state_action
    and ARTIFACT_HEADING.match(first_line)
    and (ARTIFACT_TASK_REF.search(body) or re.search(r'#[0-9]+\b', first_line))
):
    factual = artifact_factual_lines(lower)
    claims = artifact_claims(factual)
    missing = missing_evidence('\n'.join(factual)) if claims else []
    if missing:
        print("BLOCKED: think-pipeline artifact also asserts completion status without evidence.", file=sys.stderr)
        print("Claim: " + claims[0], file=sys.stderr)
        print("Missing: " + ", ".join(missing), file=sys.stderr)
        print(EVIDENCE_HELP, file=sys.stderr)
        print("Remove the status claim from the artifact, or post it separately with evidence. Ref: #1164.", file=sys.stderr)
        sys.exit(2)
    sys.exit(0)

if not state_action and not coordinator_marker:
    sys.exit(0)

completion = re.search(r'\b(done|complete|completed|resolved|closed|ready|shipped|released|merged|unblocked|green|go)\b', lower)
blocked = re.search(r'\b(blocked|blocker|request changes|requested changes|no owner response|awaiting owner|awaiting maintainer|awaiting approval|pending approval|approval pending|owner response pending|approval missing|signoff missing|sign-off missing|not approved|not signed off|unresolved|not satisfied|missing evidence|missing)\b', lower)
future_gate_plan = re.search(r"\b(i'll|i will|we will|i am going to|i'm going to|going to|will re-run|will rerun|re-run|rerun|then only decide|only decide whether)\b", lower) and re.search(r'\b(gate|gates|deployment|deploy|uat|hotfix|staging|movement|allowed|rollout)\b', lower)

# Block comments that turn ticket comments into promises to do gates later.
# Gate/deploy/UAT/hotfix movement updates must report current evidence or a
# concrete blocker, not future intent. Ref: #609.
if future_gate_plan:
    block("BLOCKED: coordinator gate/status update is a future-plan comment, not evidence.",
          "Run the gates first, then post current evidence or an explicit blocker/failure reason.")

# Block comments that imply completion while naming unresolved blockers.
if completion and blocked:
    block("BLOCKED: coordinator status update mixes completion with unresolved blocker language.",
          "Keep the lane visibly blocked until the blocker is resolved, or remove the completion claim.")

# Blocked states are valid only when the failure reason is explicit.
if blocked and not re.search(r'\b(blocked because|blocker:|failure reason:|reason:|missing:|waiting on|awaiting)', lower):
    block("BLOCKED: blocked coordinator state must include an explicit failure reason.",
          "Add 'Blocker:', 'Failure reason:', 'Missing:', or 'Waiting on:' with concrete evidence.")

# Completion/close/ready transitions require evidence prerequisites.
if completion or action in {"close", "reopen", "ready"} or api_state_transition:
    missing = missing_evidence(lower)
    # A verified mechanical relationship supplies owner evidence, not a
    # deployment waiver. Close still needs the existing rollout evidence/N/A;
    # ready requests review and does not assert merge/deploy readiness.
    if action in {"ready", "close"} and "owner_signoff" in missing:
        try:
            import importlib.util
            spec = importlib.util.spec_from_file_location('mechanical_completion', Path(sys.argv[2]) / 'github-mechanical-completion.py')
            proof = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(proof)
            if proof.verify(command, sys.argv[3] or os.getcwd(), body):
                missing = [name for name in missing if name not in {'owner_signoff', 'merge_or_branch'}]
                if action == 'ready':
                    missing = []
        except (OSError, ValueError, TypeError, KeyError, AttributeError, ImportError, SyntaxError) as error:
            block("BLOCKED: coordinator completion/state transition lacks required evidence (mechanical own-task/GitHub proof).",
                  "Missing: " + ", ".join(missing), str(error),
                  "Supply the bound own task and live matching PR proof, or the existing signoff evidence.")
    if missing:
        block("BLOCKED: coordinator completion/state transition lacks required evidence.",
              "Missing: " + ", ".join(missing),
              EVIDENCE_HELP)

sys.exit(0)
PY

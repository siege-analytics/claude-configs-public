"""Task-scoped pipeline audit and atomic artifact writer (#1051)."""
import json, sys, os, glob

signal_path, workspace, lib_dir = sys.argv[1:4]
sys.path.insert(0, lib_dir)
import importlib.util
spec = importlib.util.spec_from_file_location('gate_resolver', os.path.join(lib_dir, 'resolve-think-gate.py'))
resolver = importlib.util.module_from_spec(spec)
spec.loader.exec_module(resolver)

def atomic_signal(path, obj):
    import tempfile
    directory = os.path.dirname(path)
    os.makedirs(directory, exist_ok=True)
    fd, temp = tempfile.mkstemp(dir=directory, prefix='.signal-')
    try:
        with os.fdopen(fd, 'w') as f:
            json.dump(obj, f, indent=2)
        os.replace(temp, path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)

import re
# Skill-defined artifact headings (#1164): skills/self-review (Junior task
# description, Senior adversarial checklist), skills/pre-mortem, skills/investigate.
JUNIOR_HEADINGS = r'junior task description|junior review|pre-implementation comprehension|junior[ /-]senior review'
SENIOR_HEADINGS = r'senior adversarial checklist|senior review|junior[ /-]senior review'
INVESTIGATION_HEADINGS = r'investigation fact sheet|fact sheet|investigation'
PREMORTEM_HEADINGS = r'pre[- ]?mortem'
# GitHub renders these as code or quotation, never as the artifact itself.
HTML_CONTAINER = re.compile(
    r'<(/?)(pre|code|blockquote|q|samp|kbd|tt|var|xmp|listing|plaintext|textarea|script|style|template|noscript)\b[^>]*>',
    re.I)
TICKET_REF = re.compile(
    r'github\.com/(?P<url_repo>[\w.-]+/[\w.-]+)/(?:issues|pull)/(?P<url_num>[0-9]+)\b'
    r'|(?:(?P<repo>[\w.-]+/[\w.-]+)|(?<![\w/&]))#(?P<num>[0-9]+)\b')
TICKET_DECLARATION = re.compile(
    r'^[ \t>*_-]*(?:tickets?|ticket[ _-]?refs?|task|task[ _-]?id|issues?|refs?)[*_]*[ \t]*:')
ARTIFACT_HEADING_LINE = re.compile(
    r'^#{1,6}[ \t]+[*_`]*(?:' + '|'.join((JUNIOR_HEADINGS, SENIOR_HEADINGS, INVESTIGATION_HEADINGS, PREMORTEM_HEADINGS)) + r')\b')
# Only the task's own actor or an owner-granted GitHub role can post an
# artifact that counts; author_association is attested by GitHub (#1164).
APPROVED_ASSOCIATIONS = {'OWNER', 'MEMBER', 'COLLABORATOR'}
COMMENT_QUERY = '.[] | {author: .user.login, association: .author_association, body: .body} | @json'


# CommonMark 0.31 HTML blocks (spec 4.6). Their lines are raw HTML, never
# Markdown, so a "heading" inside one is not a heading (#1164 F3).
HTML_BLOCK_1 = re.compile(r' {0,3}<(?:pre|script|style|textarea)(?:[ \t>]|$)', re.I)
HTML_BLOCK_1_END = re.compile(r'</(?:pre|script|style|textarea)>', re.I)
HTML_BLOCK_6 = re.compile(
    r' {0,3}</?(?:address|article|aside|base|basefont|blockquote|body|caption|center|col|colgroup|dd|details|'
    r'dialog|dir|div|dl|dt|fieldset|figcaption|figure|footer|form|frame|frameset|h[1-6]|head|header|hr|html|'
    r'iframe|legend|li|link|main|menu|menuitem|nav|noframes|ol|optgroup|option|p|param|search|section|source|'
    r'summary|table|tbody|td|tfoot|th|thead|title|tr|track|ul)(?:[ \t]|/?>|$)', re.I)
HTML_BLOCK_7 = re.compile(
    r' {0,3}(?:<(?!(?:pre|script|style|textarea)\b)[A-Za-z][A-Za-z0-9-]*'
    r'(?:[ \t]+[A-Za-z_:][\w.:-]*(?:[ \t]*=[ \t]*(?:[^ \t"\'=<>`]+|\'[^\']*\'|"[^"]*"))?)*[ \t]*/?>'
    r'|</[A-Za-z][A-Za-z0-9-]*[ \t]*>)[ \t]*$')
HTML_BLOCK_OPENERS = (  # (start, end); end None means "a blank line ends it"
    (HTML_BLOCK_1, HTML_BLOCK_1_END),
    (re.compile(r' {0,3}<!--'), re.compile(r'-->')),
    (re.compile(r' {0,3}<\?'), re.compile(r'\?>')),
    (re.compile(r' {0,3}<![A-Za-z]'), re.compile(r'>')),
    (re.compile(r' {0,3}<!\[CDATA\['), re.compile(r'\]\]>')),
    (HTML_BLOCK_6, None),
)


def markdown_lines(body):
    """Body lines outside fenced code, with CommonMark HTML-block lines neutralized (#1164 F3).

    Types 1-5 end at the line holding their end marker; types 6-7 end only at
    a blank line, not at a closing tag. Type 7 cannot interrupt a paragraph.
    An HTML-block line is kept, indented one space: it can never be a heading,
    and the later name-aware container filter still sees its tags.
    """
    output, fence, block_end, paragraph = [], None, False, False
    for line in body.splitlines():
        marker = re.match(r'^ {0,3}(`{3,}|~{3,})', line)
        if block_end is False and marker:
            token = marker.group(1)
            if fence is None:
                fence = token
            elif (token[0] == fence[0] and len(token) >= len(fence)
                  and not line[marker.end():].strip()):
                fence = None
            paragraph = False
            continue
        if fence is not None:
            continue
        if block_end is not False:
            if block_end is None and not line.strip():
                block_end, paragraph = False, False
                output.append(line)
                continue
            if block_end is not None and block_end.search(line):
                block_end = False
            output.append(' ' + line)
            continue
        for start, end in HTML_BLOCK_OPENERS + (((HTML_BLOCK_7, None),) if not paragraph else ()):
            opened = start.match(line)
            if opened:
                if end is None or not end.search(line, opened.end()):
                    block_end = end
                paragraph = False
                output.append(' ' + line)
                break
        else:
            output.append(line)
            paragraph = bool(line.strip()) and not re.match(r' {0,3}#{1,6}(?:[ \t]|$)', line)
    return output


def comment_views(body):
    """(identity text, heading text) of one comment.

    Identity keeps inline-code content, so `other/repo#9` still names its
    ticket (#1164 F2). Heading text erases inline code and HTML containers.
    """
    visible = '\n'.join(markdown_lines(body))
    identity = re.sub(r'(`+)(?!`)(.+?)(?<!`)\1(?!`)', r' \2 ', visible)
    return identity, comment_text(visible)


def comment_text(visible):
    """Erase inline code, HTML comments, CDATA and HTML code/quote containers (#1164)."""
    # An inline code span shows `<pre>` as text, so it goes before HTML
    # parsing. Every removed span becomes one space: a remainder can never
    # start a line with `#` and become a heading.
    text = re.sub(r'(`+)(?!`).+?(?<!`)\1(?!`)', ' ', visible)
    text = re.sub(r'<!--.*?(?:-->|\Z)', ' ', text, flags=re.S)
    text = re.sub(r'<!\[CDATA\[.*?(?:\]\]>|\Z)', ' ', text, flags=re.S)
    # Closure is name-aware (#1164 R3): `</blockquote>` cannot end an open
    # `<pre>`. A closing tag ends its own element and anything opened inside it;
    # one naming no open container closes nothing.
    kept, stack, position = [], [], 0
    for tag in HTML_CONTAINER.finditer(text):
        closing, name = bool(tag.group(1)), tag.group(2).lower()
        if not stack:
            if closing:
                continue  # a stray closing tag is plain text
            kept.append(text[position:tag.start()])
            stack.append(name)
        elif not closing:
            stack.append(name)
        elif name in stack:
            del stack[len(stack) - 1 - stack[::-1].index(name):]
            if not stack:
                kept.append(' ')
                position = tag.end()
    # An unclosed container hides the rest of the comment.
    kept.append(text[position:] if not stack else ' ')
    return ''.join(kept)


def ticket_refs(text):
    """(owner/repo or '', number) for each #N, owner/repo#N or GitHub issue URL."""
    return [(m.group('repo') or m.group('url_repo') or '', m.group('num') or m.group('url_num'))
            for m in TICKET_REF.finditer(text)]


def declarations(text):
    """Each artifact heading line and each ticket declaration's entire value.

    A declaration value is its inline text plus every following indented or
    list-item line (#1164 R2): YAML `ticket_refs:` lists, wrapped `Ticket:` values.
    Blank lines do not end it (#1164 F2); the first unindented text line does.
    """
    lines = text.splitlines()
    for index, line in enumerate(lines):
        if ARTIFACT_HEADING_LINE.match(line):
            yield line
        if not TICKET_DECLARATION.match(line):
            continue
        value = [line]
        for follow in lines[index + 1:]:
            if follow.strip() and not (follow[:1].isspace() or re.match(r'[-*+][ \t]', follow)):
                break
            value.append(follow)
        yield '\n'.join(value)


# A leading YAML front-matter block, delimited by `---` lines.
FRONT_MATTER = re.compile(r'\s*---[ \t]*\n(.*?)\n[ \t]*---[ \t]*(?:\n|$)', re.S)


def declares_other_ticket(text, repo_slug, issue_num):
    """True when a declaration, artifact heading or front matter names tickets, none of them the current one.

    Front matter is judged as one whole region, not parsed (#1164 F2): no YAML
    parser is available in the hook runtime as installed. Any ticket reference
    anywhere in the block counts, so blank lines, comments, flow collections
    and folded scalars cannot hide a foreign one.
    """
    def names_only_others(region):
        refs = ticket_refs(region)
        return bool(refs) and not any(num == issue_num and repo in ('', repo_slug) for repo, num in refs)

    front = FRONT_MATTER.match(text)
    if front and names_only_others(front.group(1)):
        return True
    return any(names_only_others(value) for value in declarations(text))


def artifact_heading(lowered_comments, names):
    """True when a markdown heading starting with one of names is followed by content."""
    return bool(re.search(r'^#{1,6}[ \t]+[*_`]*(?:' + names + r')\b[^\n]*\n(?:[ \t]*\n)*[ \t]*[^#\s]',
                          lowered_comments, re.M))


try:
    data = json.load(open(signal_path))
except Exception as e:
    print(f'WARN: think-gate.json is malformed ({e}). Pipeline enforcement skipped.')
    sys.exit(0)

status = data.get('status', '')
if status in ('disposed', 'done-awaiting-pr'):
    sys.exit(0)

task = data.get('task', data.get('ticket', 'unknown'))
current_ticket = data.get('ticket', '')
current_identity = resolver.task_identity(data)
warnings = []

# Scan common artifact locations
plan_dirs = []

# Session plans (Craft Agent)
craft_plans = os.environ.get('CRAFT_AGENT_PLANS_PATH', '')
if craft_plans and os.path.isdir(craft_plans):
    plan_dirs.append(craft_plans)

# Workspace plans/
ws_plans = os.path.join(workspace, 'plans')
if os.path.isdir(ws_plans):
    plan_dirs.append(ws_plans)

# Repo plans/ (from think-gate.json repo_root field)
repo_root = data.get('repo_root', '')
if repo_root:
    repo_plans = os.path.join(repo_root, 'plans')
    if os.path.isdir(repo_plans) and repo_plans not in plan_dirs:
        plan_dirs.append(repo_plans)

def file_references_ticket(filepath, ticket_ref):
    """Check if a file's content references the current ticket."""
    if not ticket_ref:
        return True  # no ticket to check = pass
    try:
        content = open(filepath).read(4096)
    except Exception:
        return False
    return bool(_re.search(r'(?<![A-Za-z0-9_/#-])' + _re.escape(ticket_ref) + r'(?![A-Za-z0-9_#-])', content))

import re as _re
def premortem_has_risks(filepath):
    try:
        content = open(filepath).read(8192)
    except Exception:
        return False
    lower = content.lower()
    return bool(
        'severity:' in lower
        or '**urgency:**' in lower
        or _re.search(r'(?:tiger|paper tiger|elephant)\s+\d', lower)
    )

def premortem_has_launch_blocker(filepath):
    try:
        content = open(filepath).read(8192)
    except Exception:
        return False
    lower = content.lower()
    if 'implementation may proceed: no' in lower:
        return True
    if _re.search(r'\*\*status:\*\*\s*blocks-launch', lower):
        return True
    return False

def find_artifact(patterns, require_ticket=True):
    for d in plan_dirs:
        for p in patterns:
            matches = glob.glob(os.path.join(d, p))
            for m in sorted(matches):
                if require_ticket and current_identity:
                    if file_references_ticket(m, current_identity):
                        return m
                else:
                    return m
    return None

# 1. Investigation artifact
invest_patterns = ['fact-sheet*', 'investigate*', 'investigation*', 'Fact-Sheet*']
invest = find_artifact(invest_patterns)
# Also check investigate-gate.json (ticket association via JSON ticket field)
# Repo-scoped resolution (#578): check <gate>-<slug>.json first
if not invest:
    resolved = resolver._artifact_for({'path': signal_path, 'data': data}, 'investigate-gate', workspace)
    invest_gate_path = resolved['path'] if resolved else ''
    if os.path.isfile(invest_gate_path):
        try:
            ig = json.load(open(invest_gate_path))
            ig_ticket = ig.get('ticket', '')
            if ig_ticket == current_ticket or not current_ticket:
                invest = invest_gate_path
                if not ig.get('findings', []):
                    warnings.append(
                        f'INVESTIGATE: investigate-gate.json exists but has no findings FOR {current_ticket or "current task"}.\n'
                        '  Add at least one finding before proceeding.\n'
                        '  The mutation gate will block until findings are present.'
                    )
        except Exception:
            pass
if not invest:
    warnings.append(
        f'INVESTIGATE: No investigation artifact found FOR {current_ticket or "current task"}.\n'
        '  Produce a Fact Sheet before writing code.\n'
        '  Expected: plans/fact-sheet-*.md or plans/investigate-*.md (must reference current ticket)\n'
        '  Read: skills/investigate/SKILL.md'
    )

# 2. Pre-mortem artifact
premortem_patterns = ['pre-mortem*', 'premortem*', 'risk*', 'Pre-mortem*']
premortem = find_artifact(premortem_patterns)
if not premortem:
    warnings.append(
        f'PRE-MORTEM: No pre-mortem artifact found FOR {current_ticket or "current task"}.\n'
        '  Classify risks before writing code.\n'
        '  Expected: plans/pre-mortem-*.md (must reference current ticket in ticket_refs)\n'
        '  Read: skills/pre-mortem/SKILL.md'
    )
elif not premortem_has_risks(premortem):
    warnings.append(
        f'PRE-MORTEM: Pre-mortem artifact exists but has no classified risks FOR {current_ticket or "current task"}.\n'
        '  Add at least one risk with Severity: or Tiger/Elephant classification.\n'
        '  The mutation gate will block until risks are present.'
    )
elif premortem_has_launch_blocker(premortem):
    warnings.append(
        f'LAUNCH-BLOCKING TIGER: Pre-mortem ({os.path.basename(premortem)}) contains a Launch-Blocking Tiger.\n'
        '  Implementation is halted until the Tiger is mitigated.\n'
        '  Update the pre-mortem to remove Blocks-Launch status or set "Implementation may proceed: YES".\n'
        '  The mutation gate will block until the Launch-Blocking Tiger is resolved.'
    )

# 3. Self-review artifact (only warn when code changes exist)
review = None
try:
    import subprocess
    staged = subprocess.run(
        ['git', '-C', workspace, 'diff', '--cached', '--name-only'],
        capture_output=True, text=True, timeout=5
    ).stdout.strip()
    unstaged = subprocess.run(
        ['git', '-C', workspace, 'diff', '--name-only'],
        capture_output=True, text=True, timeout=5
    ).stdout.strip()
    has_changes = bool(staged or unstaged)
except Exception:
    has_changes = False

if has_changes:
    review_patterns = ['self-review*', 'review*', 'Self-review*']
    review = find_artifact(review_patterns)
    if not review:
        warnings.append(
            'SELF-REVIEW: Code changes detected but no self-review artifact.\n'
            '  Before pushing, produce a self-review artifact.\n'
            '  Expected: plans/self-review-*.md\n'
            '  Read: skills/self-review/SKILL.md'
        )

# 4. Pre-implementation comprehension check (#489 component A).
# When status is 'implementing', check the ticket for Junior's task
# description with the 5 required elements.
if status == 'implementing' and current_ticket:
    junior_found = False
    senior_found = False
    # Track API reachability. When the gh api call fails (rate limit, network,
    # 5xx), we cannot distinguish "artifact absent" from "we could not check."
    # Writing all-false in that case falsely signals "no artifacts posted" and
    # the downstream mutation-gate blocks work whose artifacts were, in fact,
    # posted (#708). The pattern: if api_ok stays False, don't overwrite the
    # signal file; keep the last-known-good state and add api_error field so
    # the downstream reader can see the check was unreachable.
    api_ok = True
    api_error = ''
    junior_stems = [
        'current behavior', 'intended behavior', 'steps to get there',
        'success criteria', 'what could go wrong',
    ]
    senior_stems = [
        'hasty mistakes', 'observable behavior', 'over-focusing',
        'leave out', 'prior work', 'right environment',
        'failure case', 'instance or class', 'done match',
        'skip if nobody',
    ]
    try:
        # Extract owner/repo and issue number from ticket ref.
        if '#' in current_ticket:
            parts = current_ticket.split('#')
            issue_num = parts[-1]
            repo_slug = parts[0].rstrip('/') if len(parts) > 1 and parts[0] else ''
        else:
            issue_num = current_ticket
            repo_slug = ''

        if issue_num.isdigit():
            if repo_slug:
                api_path = f'repos/{repo_slug}/issues/{issue_num}/comments'
            else:
                api_path = f'repos/siege-analytics/claude-configs-public/issues/{issue_num}/comments'

            result = subprocess.run(
                ['gh', 'api', api_path, '--paginate', '-q', COMMENT_QUERY],
                capture_output=True, text=True, timeout=15
            )
            if result.returncode == 0:
                records = [json.loads(line) for line in result.stdout.splitlines() if line.strip()]
                if not all(isinstance(r, str) or isinstance(r, dict) and isinstance(r.get('body'), str)
                           for r in records):
                    raise ValueError('GitHub comment body is not text')
                # The authenticated gh login is the task's own actor. Without
                # it (e.g. an app token), only attested roles count.
                actor = subprocess.run(['gh', 'api', 'user', '-q', '.login'],
                                       capture_output=True, text=True, timeout=15)
                actor_login = actor.stdout.strip() if actor.returncode == 0 else ''
                if not re.fullmatch(r'[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})', actor_login):
                    actor_login = ''
                ticket_repo = (repo_slug or 'siege-analytics/claude-configs-public').lower()
                texts = []
                for record in records:
                    if isinstance(record, str):
                        continue  # a bare body carries no author: it never counts
                    author = record.get('author') if isinstance(record.get('author'), str) else ''
                    if not ((actor_login and author.lower() == actor_login.lower())
                            or record.get('association') in APPROVED_ASSOCIATIONS):
                        continue
                    identity, text = (view.lower() for view in comment_views(record['body']))
                    if not declares_other_ticket(identity, ticket_repo, issue_num):
                        texts.append(text)
                comments = '\n# comment boundary\n'.join(texts)
                junior_hits = sum(1 for s in junior_stems if s in comments)
                if junior_hits >= 3:
                    junior_found = True

                senior_hits = sum(1 for s in senior_stems if s in comments)
                if senior_hits >= 5:
                    senior_found = True
                # A posted artifact headed with its skill name counts even when
                # its prose uses none of the stems (#1164). These are the same
                # headings coordinator-status-guard admits as artifacts. The
                # heading must be followed by a non-blank content line.
                junior_found = junior_found or artifact_heading(comments, JUNIOR_HEADINGS)
                senior_found = senior_found or artifact_heading(comments, SENIOR_HEADINGS)
            else:
                api_ok = False
                api_error = (result.stderr or '').strip()[:200] or f'gh api rc={result.returncode}'
    except Exception as e:
        api_ok = False
        api_error = str(e)[:200]

    if not junior_found:
        warnings.append(
            f'PRE-IMPLEMENTATION COMPREHENSION: No Junior task description found on {current_ticket}.\n'
            '  Before writing code, post a maximal description with:\n'
            '  1. Current behavior (with evidence)\n'
            '  2. Intended behavior (observable, not code-to-write)\n'
            '  3. Steps to get there\n'
            '  4. Success criteria (testable in target environment)\n'
            '  5. What could go wrong\n'
            '  Read: skills/self-review/SKILL.md (Pre-implementation comprehension)'
        )

    # 5. Senior adversarial checklist (#489 component B).
    if not senior_found:
        warnings.append(
            f'SENIOR ADVERSARIAL CHECKLIST: No Senior checklist response found on {current_ticket}.\n'
            '  After the Junior posts the task description, the Senior must run\n'
            '  the 10 presumptive questions and post responses on the ticket.\n'
            '  Read: skills/self-review/SKILL.md (Senior adversarial checklist)'
        )

    # 6. Check if investigation and pre-mortem were posted to ticket (#513).
    investigate_posted = False
    premortem_posted = False
    invest_stems = [
        'findings', 'citations', 'disposition', 'fact sheet',
        'investigation', 'verified', 'evidence',
    ]
    premortem_stems = [
        'severity:', 'tiger', 'risks', 'pre-mortem',
        'elephant', 'paper tiger', 'mitigation',
    ]
    try:
        if result.returncode == 0 and comments:
            invest_hits = sum(1 for s in invest_stems if s in comments)
            if invest_hits >= 3:
                investigate_posted = True

            premortem_hits = sum(1 for s in premortem_stems if s in comments)
            if premortem_hits >= 3:
                premortem_posted = True
            investigate_posted = investigate_posted or artifact_heading(comments, INVESTIGATION_HEADINGS)
            premortem_posted = premortem_posted or artifact_heading(comments, PREMORTEM_HEADINGS)
    except Exception:
        pass

    if not investigate_posted:
        warnings.append(
            f'INVESTIGATE-ON-TICKET: Investigation artifact not found on {current_ticket}.\n'
            '  Post the investigation (Fact Sheet or findings) to the ticket.\n'
            '  The mutation gate will block until the investigation is posted.'
        )

    if not premortem_posted:
        warnings.append(
            f'PRE-MORTEM-ON-TICKET: Pre-mortem artifact not found on {current_ticket}.\n'
            '  Post the pre-mortem (risks/Tigers) to the ticket.\n'
            '  The mutation gate will block until the pre-mortem is posted.'
        )

    # 7. Check if self-review was posted to ticket (#519).
    # Only check when a local self-review artifact exists (review variable
    # from section 3). Self-review comes after implementation, so absence
    # of a local artifact means posting is not yet relevant.
    selfreview_posted = True
    if review:
        selfreview_posted = False
        selfreview_stems = [
            'peer review', 'lead review', 'syntax check',
            'rework ledger', 'findings',
        ]
        try:
            if result.returncode == 0 and comments:
                sr_hits = sum(1 for s in selfreview_stems if s in comments)
                if sr_hits >= 3:
                    selfreview_posted = True
        except Exception:
            pass

        if not selfreview_posted:
            warnings.append(
                f'SELF-REVIEW-ON-TICKET: Self-review artifact exists locally but not found on {current_ticket}.\n'
                '  Post the self-review to the ticket before pushing.\n'
                '  The mutation gate will block until the self-review is posted.'
            )

    # Write junior-senior-gate.json signal file (#492, repo-scoped #578, #708)
    # When the API was unreachable, do not overwrite with all-false. Keep the
    # last-known-good signal file (which may itself be stale, but stale is
    # better than incorrectly-negative). The unreachable-side stamp file lets
    # the downstream reader see the check was unreachable without overwriting
    # the last successful signal.
    import datetime
    signal_dir = resolver.write_directory({'path': signal_path, 'data': data}, workspace)
    if not signal_dir:
        print('No session/task signal directory; legacy root signals are read-only.')
        sys.exit(0)
    gate_path = os.path.join(signal_dir, 'junior-senior-gate.json')
    if api_ok:
        gate_data = {
            'ticket': current_ticket,
            'task_id': resolver.task_identity(data),
            'sessionId': resolver.session_id_from_env(),
            'repo_root': repo_root,
            'junior_found': junior_found,
            'senior_found': senior_found,
            'api_reachable': True,
            'lastChecked': datetime.datetime.now().astimezone().isoformat(),
        }
        try:
            atomic_signal(gate_path, gate_data)
        except Exception:
            pass
    else:
        # API unreachable. Stamp an api_reachable=false side-file so the
        # downstream reader can see the check was unreachable without
        # overwriting the last successful signal.
        stamp_path = gate_path + '.unreachable'
        try:
            atomic_signal(stamp_path, {
                    'ticket': current_ticket,
            'task_id': resolver.task_identity(data),
            'sessionId': resolver.session_id_from_env(),
            'repo_root': repo_root,
                    'api_reachable': False,
                    'api_error': api_error,
                    'lastAttempt': datetime.datetime.now().astimezone().isoformat(),
                })
        except Exception:
            pass

    # Write artifacts-posted-gate.json signal file (#513, #519, repo-scoped #578, #708)
    posted_path = os.path.join(signal_dir, 'artifacts-posted-gate.json')
    if api_ok:
        posted_data = {
            'ticket': current_ticket,
            'task_id': resolver.task_identity(data),
            'sessionId': resolver.session_id_from_env(),
            'repo_root': repo_root,
            'investigate_posted': investigate_posted,
            'premortem_posted': premortem_posted,
            'selfreview_posted': selfreview_posted,
            'api_reachable': True,
            'lastChecked': datetime.datetime.now().astimezone().isoformat(),
        }
        try:
            atomic_signal(posted_path, posted_data)
        except Exception:
            pass
    else:
        stamp_path = posted_path + '.unreachable'
        try:
            atomic_signal(stamp_path, {
                    'ticket': current_ticket,
            'task_id': resolver.task_identity(data),
            'sessionId': resolver.session_id_from_env(),
            'repo_root': repo_root,
                    'api_reachable': False,
                    'api_error': api_error,
                    'lastAttempt': datetime.datetime.now().astimezone().isoformat(),
                })
        except Exception:
            pass

if not warnings:
    found = []
    if invest:
        found.append(f'investigate: {os.path.basename(invest)}')
    if premortem:
        found.append(f'pre-mortem: {os.path.basename(premortem)}')
    summary = ', '.join(found)
    print(f'Pipeline for {task}: artifacts present ({summary}).')
    if status == 'implementing':
        print('Slow is smooth: what have you not yet verified about the deployed state?')
else:
    print(f'Pipeline for {task}: {len(warnings)} artifact(s) missing.')
    print()
    for w in warnings:
        print(w)
        print()
    print('These warnings repeat every turn until the artifacts are produced.')
    print('If this work is trivial, archive think-gate.json to silence them.')

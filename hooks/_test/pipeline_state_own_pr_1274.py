"""#1274: an artifact heading naming the current ticket's own PR counts.

pipeline_state.py read every #N in an artifact heading as a ticket
declaration, so a heading such as "Investigation and pre-mortem for the
process commit on PR #1748" (siege_utilities #1526) excluded the whole
comment. A heading ref now gets one bounded GitHub read of the PR it names;
it counts only when that PR's closingIssuesReferences or its explicit
Refs/Fixes relationship names the current ticket. Every other path, and
front matter or Ticket:/Refs: keys, keeps the strict exclusion.

Each case runs the real writer, real jq projection, and the unchanged Tier C
universal-mutation-gate on an existing and a missing target.
"""
import ast
import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LIB = ROOT / 'hooks/lib'
GATE = ROOT / 'hooks/bash/universal-mutation-gate.sh'
ENV = {k: v for k, v in os.environ.items()
       if not k.startswith(('CRAFT', 'CLAUDE', 'CCP', 'CODEX')) and k != 'SESSION_ID'}
COMMENT_QUERY = '.[] | {author: .user.login, association: .author_association, body: .body} | @json'

PREMORTEM = ('Severity: 3\nTiger 1: the export drops rows\nTiger 2: retries duplicate posts\n'
             'Elephant: the upstream schema is unowned\nMitigation: pin the schema and add a replay test\n')
INVEST = 'Findings: the commit path skips the hook.\nCitations: hooks/lib/x.py:12\nDisposition: fix in #1526.\nVerified with a dry run.\n'
JS = '## Junior task description\nx\n## Senior adversarial checklist\nx\n'


def headed(ref):
    return JS + '## Pre-Mortem for ' + ref + '\n' + PREMORTEM + '## Investigation\n' + INVEST


def pr(repo, number, body, closing=()):
    return {'number': number, 'body': body, 'repository': {'nameWithOwner': repo},
            'closingIssuesReferences': {'nodes': [{'number': n, 'repository': {'nameWithOwner': r}} for r, n in closing]}}


# owner/name#N -> GraphQL pullRequest node, or a failure mode the fake gh enacts.
PULLS = {
    'o/r#1748': pr('o/r', 1748, 'Implements the export fix.\n\nRefs #1526'),
    'o/r#1749': pr('o/r', 1749, 'Second round.', closing=[('o/r', 1526)]),
    'o/r#1750': pr('o/r', 1750, 'Fixes #1526'),
    'o/r#1751': pr('O/R', 1751, 'Mixed-case identity.', closing=[('O/R', 1526)]),
    # Relationship styles used by real develop-target PRs (review S2-2).
    'o/r#1752': pr('o/r', 1752, '## Tickets\n\n- Refs #1526'),
    'o/r#1753': pr('o/r', 1753, '## Tickets\n\n- Refs #1600'),
    'o/r#1754': pr('o/r', 1754, '* Fixes #1526'),
    'o/r#1755': pr('o/r', 1755, 'Refs #1526 (hook-side lane only; the rest lands later)'),
    'o/r#1756': pr('o/r', 1756, 'Refs #1526, item3 only; follow-ups elsewhere'),
    'o/r#1757': pr('o/r', 1757, 'Refs #1526; related to #1600'),
    'o/r#1758': pr('o/r', 1758, '- Refs o/r#1526 for the hook path'),
    'o/r#1759': pr('o/r', 1759, '- Refs #1600 (also touches #1526)'),
    'o/r#1760': pr('o/r', 1760, '- See #1526 for context'),
    'o/r#1761': pr('o/r', 1761, '- Example: Refs #1526'),
    'o/r#1762': pr('o/r', 1762, '```\n- Refs #1526\n```'),
    'o/r#1763': pr('o/r', 1763, '> - Refs #1526'),
    'o/r#1764': pr('o/r', 1764, '- Related to #1526, refs #1600'),
    # List padding (Root P1 on 05ecbbfb): 1-4 spaces after a marker are
    # paragraph padding; a tab or 5+ spaces make the content indented code.
    'o/r#1765': pr('o/r', 1765, '-     Refs #1526'),
    'o/r#1766': pr('o/r', 1766, '1.     Refs #1526'),
    'o/r#1767': pr('o/r', 1767, '1. Refs #1526'),
    'o/r#1768': pr('o/r', 1768, '-    Refs #1526'),
    'o/r#1769': pr('o/r', 1769, '-\tRefs #1526'),
    'o/r#1770': pr('o/r', 1770, '  \t- Refs #1526'),
    'o/r#1771': pr('o/r', 1771, '1.\tRefs #1526'),
    'o/r#1772': pr('o/r', 1772, '-  \tRefs #1526'),
    'o/r#1900': pr('o/r', 1900, 'Unrelated cleanup.\n\nRefs #1600', closing=[('o/r', 1600)]),
    'o/r#1901': pr('o/r', 1901, 'This is related to #1526 in spirit, see the discussion there.'),
    'o/r#1902': pr('o/r', 1902, 'Example: Refs #1526'),
    'other/repo#1748': pr('other/repo', 1748, 'Refs #1526', closing=[('other/repo', 1526)]),
    'other/repo#7': pr('other/repo', 7, 'Cross-repository follow-up.\n\nRefs o/r#1526'),
    'o/r#1800': 'fail',
    'o/r#1801': 'sleep',
    'o/r#1806': 'sleep',
    'o/r#1807': 'sleep',
    'o/r#1808': 'sleep',
    'o/r#1802': 'malformed',
    'o/r#1803': pr('o/r', 9999, 'Refs #1526'),            # reply names another PR number
    'o/r#1804': pr('other/repo', 1804, 'Refs #1526'),     # reply names another repository
    'o/r#1805': {'number': 1805, 'body': 'Refs #1526', 'repository': {'nameWithOwner': 'o/r'},
                 'closingIssuesReferences': {'nodes': 'not-a-list'}},
}

FAKE_GH = '''#!{python}
import json, subprocess, sys, time
from pathlib import Path
here = Path(__file__).resolve().parent.parent
args = sys.argv[1:]
if args[:2] == ['api', 'user']:
    print('task-owner'); sys.exit(0)
if args[:2] == ['api', 'graphql']:
    fields = dict(args[i + 1].split('=', 1) for i, a in enumerate(args) if a in ('-f', '-F'))
    with open(here / 'graphql-calls.log', 'a') as log:
        log.write(json.dumps(fields) + '\\n')
    key = '%s/%s#%s' % (fields.get('owner'), fields.get('name'), fields.get('pr'))
    node = json.loads((here / 'pulls.json').read_text()).get(key)
    if node == 'fail':
        sys.stderr.write('gh: HTTP 502\\n'); sys.exit(1)
    if node == 'sleep':
        time.sleep(30); sys.exit(0)
    if node == 'malformed':
        print('{{"data": '); sys.exit(0)
    if node is None:
        # GitHub answers an issue or unknown number with an error and exit 1.
        print(json.dumps({{'data': {{'repository': {{'pullRequest': None}}}},
                          'errors': [{{'type': 'NOT_FOUND', 'message': 'Could not resolve to a PullRequest'}}]}}))
        sys.exit(1)
    print(json.dumps({{'data': {{'repository': {{'pullRequest': node}}}}}})); sys.exit(0)
assert args[:2] == ['api', 'repos/o/r/issues/1526/comments'], args
query = args[args.index('-q') + 1]
assert query == {query!r}, query
sys.exit(subprocess.run(['jq', '-r', query], input=(here / 'api-comments.json').read_text(), text=True, timeout=10).returncode)
'''


class OwnPullRequestHeading(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def chain(self, name, body, extra_env=None):
        case = Path(self.tmp.name) / name
        session = case / 'workspace/sessions/fixture-session'
        task, repo, fake = session / 'tasks/t', case / 'repo', case / 'fakebin'
        for path in (task, repo / 'hooks/bash', repo / 'plans', fake):
            path.mkdir(parents=True)
        subprocess.run(['git', 'init', '-q', str(repo)], check=True, timeout=10)
        existing = repo / 'hooks/bash/example.sh'
        existing.write_text('#!/bin/bash\n# fixture only\n')
        ident = {'ticket': 'o/r#1526', 'task_id': 'o/r#1526', 'sessionId': session.name, 'repo_root': str(repo),
                 'scope_paths': [str(repo)], 'status': 'implementing', 'tier': 'C'}
        (task / 'think-gate.json').write_text(json.dumps(ident))
        (task / 'investigate-gate.json').write_text(json.dumps(dict(ident, findings=[{'claim': 'fixture'}])))
        (repo / 'plans/pre-mortem-local.md').write_text('o/r#1526\nTiger 1: x\nSeverity: 1\nImplementation may proceed: YES\n')
        bodies = body if isinstance(body, list) else [body]  # oldest first, as GitHub lists them
        (case / 'api-comments.json').write_text(json.dumps(
            [{'user': {'login': 'task-owner'}, 'author_association': 'NONE', 'body': text} for text in bodies]))
        (case / 'pulls.json').write_text(json.dumps(PULLS))
        (fake / 'gh').write_text(FAKE_GH.format(python=sys.executable, query=COMMENT_QUERY))
        (fake / 'gh').chmod(0o755)
        env = dict(ENV, PATH=str(fake) + os.pathsep + ENV['PATH'], CRAFT_AGENT_WORKSPACE=str(case / 'workspace'),
                   CRAFT_SESSION_DIR=str(session), CRAFT_SESSION_ID=session.name, CCP_TASK_ID='o/r#1526')
        env.update(extra_env or {})
        started = time.monotonic()
        writer = subprocess.run([sys.executable, '-I', '-B', str(LIB / 'pipeline_state.py'), str(task / 'think-gate.json'),
                                 str(case / 'workspace'), str(LIB)], cwd=repo, env=env, capture_output=True, text=True, timeout=90)
        elapsed = time.monotonic() - started
        self.assertEqual(writer.returncode, 0, writer.stdout + writer.stderr)
        js = json.loads((task / 'junior-senior-gate.json').read_text())
        ap = json.loads((task / 'artifacts-posted-gate.json').read_text())
        # A failed PR lookup never turns into an unreachable comment read.
        self.assertTrue(js['api_reachable'] and ap['api_reachable'])
        self.assertFalse((task / 'junior-senior-gate.json.unreachable').exists())
        flags = [js['junior_found'], js['senior_found'], ap['investigate_posted'], ap['premortem_posted']]
        exits = []
        for target in (existing, repo / 'hooks/example.sh'):
            payload = {'sessionId': session.name, 'tool_name': 'Write', 'cwd': str(repo),
                       'tool_input': {'file_path': str(target), 'content': 'fixture only'}}
            gate = subprocess.run(['bash', str(GATE)], cwd=repo, env=env, input=json.dumps(payload),
                                  text=True, capture_output=True, timeout=60)
            exits.append((gate.returncode, gate.stdout + gate.stderr))
        log = case / 'graphql-calls.log'
        calls = [json.loads(line) for line in log.read_text().splitlines()] if log.exists() else []
        return flags, exits, calls, elapsed

    def assertChain(self, name, body, counted, extra_env=None):
        flags, exits, calls, elapsed = self.chain(name, body, extra_env)
        self.assertEqual(flags, [counted] * 4, name)
        for code, output in exits:
            self.assertEqual(code, 0 if counted else 2, output)
        return calls, elapsed

    # The own PR counts, in every heading shape.
    def test_su_1526_shape_counts(self):
        self.assertChain('su-shape', JS + '## Investigation and pre-mortem for the process commit on PR #1748\n'
                         + INVEST + PREMORTEM, True)

    def test_bare_number_heading_counts(self):
        calls, _ = self.assertChain('bare', headed('#1748'), True)
        self.assertEqual([(c['owner'], c['name'], c['pr']) for c in calls], [('o', 'r', '1748')])

    def test_pull_url_heading_counts(self):
        self.assertChain('url', headed('https://github.com/o/r/pull/1748'), True)

    def test_closing_reference_counts(self):
        self.assertChain('closing', headed('PR #1749'), True)

    def test_fixes_relationship_counts(self):
        self.assertChain('fixes', headed('PR #1750'), True)

    def test_qualified_cross_repository_pr_naming_ticket_counts(self):
        calls, _ = self.assertChain('cross-repo-own', headed('other/repo#7'), True)
        self.assertEqual([(c['owner'], c['name']) for c in calls], [('other', 'repo')])

    # Bulleted and annotated relationship lines (review S2-2): the leading run
    # of refs after the verb counts; annotations and prose mentions never do.
    def test_bulleted_refs_line_counts(self):
        self.assertChain('bulleted-refs', headed('PR #1752'), True)

    def test_bulleted_fixes_line_counts(self):
        self.assertChain('bulleted-fixes', headed('PR #1754'), True)

    def test_annotated_refs_lines_count(self):
        for number in (1755, 1756, 1757):
            with self.subTest(number):
                self.assertChain('annotated-%d' % number, headed('PR #%d' % number), True)

    def test_bulleted_qualified_refs_line_counts(self):
        self.assertChain('bulleted-qualified', headed('PR #1758'), True)

    def test_bulleted_foreign_refs_excluded(self):
        self.assertChain('bulleted-foreign', headed('PR #1753'), False)

    def test_ticket_only_in_annotation_excluded(self):
        self.assertChain('annotation-only', headed('PR #1759'), False)

    def test_bulleted_prose_mentions_excluded(self):
        for number in (1760, 1764):
            with self.subTest(number):
                self.assertChain('bulleted-prose-%d' % number, headed('PR #%d' % number), False)

    def test_bulleted_example_fence_and_quote_excluded(self):
        for number in (1761, 1762, 1763):
            with self.subTest(number):
                self.assertChain('bulleted-hidden-%d' % number, headed('PR #%d' % number), False)

    def test_list_item_indented_code_excluded(self):
        # `-     Refs` and `1.     Refs` are CommonMark indented code (Root P1).
        for number in (1765, 1766):
            with self.subTest(number):
                self.assertChain('list-code-%d' % number, headed('PR #%d' % number), False)

    def test_tab_list_padding_excluded(self):
        for number in (1769, 1770, 1771, 1772):
            with self.subTest(number):
                self.assertChain('list-tab-%d' % number, headed('PR #%d' % number), False)

    def test_ordinary_numbered_and_max_padding_bullets_count(self):
        for number in (1767, 1768):
            with self.subTest(number):
                self.assertChain('list-padding-%d' % number, headed('PR #%d' % number), True)

    # Mixed outcomes across headings in one comment (review S2-3).
    def test_own_pr_heading_cannot_carry_a_foreign_heading(self):
        body = headed('PR #1748').replace('## Investigation\n', '## Investigation for #9001\n')
        self.assertChain('mixed-headings', body, False)

    def test_one_heading_naming_own_pr_and_another_ref_counts(self):
        # Within ONE heading any resolving ref is enough, matching the
        # existing rule for a heading naming the current ticket among others.
        self.assertChain('mixed-refs-one-heading', headed('PR #1748 and #9001'), True)

    # Unrelated and foreign references stay excluded.
    def test_unrelated_pr_excluded(self):
        self.assertChain('unrelated-pr', headed('PR #1900'), False)

    def test_unrelated_ticket_excluded(self):
        self.assertChain('unrelated-ticket', headed('#99999'), False)

    def test_prose_mention_in_pr_body_excluded(self):
        self.assertChain('prose-mention', headed('PR #1901'), False)

    def test_example_reference_in_pr_body_excluded(self):
        self.assertChain('example-mention', headed('PR #1902'), False)

    def test_foreign_repository_same_number_excluded(self):
        # other/repo#1748 says "Refs #1526": relative to other/repo, not o/r.
        calls, _ = self.assertChain('foreign-repo', headed('other/repo#1748'), False)
        self.assertEqual([(c['owner'], c['name']) for c in calls], [('other', 'repo')])

    def test_front_matter_own_pr_stays_strict(self):
        calls, _ = self.assertChain('front-matter', '---\nticket_refs:\n  - o/r#1748\n---\n' + headed('#1526'), False)
        self.assertEqual(calls, [])

    def test_ticket_key_own_pr_stays_strict(self):
        calls, _ = self.assertChain('ticket-key', 'Ticket: o/r#1748\n' + headed('#1526'), False)
        self.assertEqual(calls, [])

    # Every lookup failure keeps today's exclusion.
    def test_issue_not_pr_excluded(self):
        # #1600 is an issue: GitHub's pullRequest(number) read errors (exit 1).
        calls, _ = self.assertChain('issue', headed('#1600'), False)
        self.assertEqual(len(calls), 1)

    def test_lookup_failure_excluded(self):
        self.assertChain('fail', headed('PR #1800'), False)

    def test_malformed_reply_excluded(self):
        self.assertChain('malformed', headed('PR #1802'), False)

    def test_reply_for_other_number_excluded(self):
        self.assertChain('other-number', headed('PR #1803'), False)

    def test_reply_for_other_repository_excluded(self):
        self.assertChain('other-repository', headed('PR #1804'), False)

    def test_malformed_closing_references_excluded(self):
        self.assertChain('malformed-closing', headed('PR #1805'), False)

    # The guard runs under a 10 s hook timeout (.claude/settings.json).
    HOOK_TIMEOUT = 10.0

    def test_timeout_excluded_within_budget(self):
        calls, elapsed = self.assertChain('timeout', headed('PR #1801'), False)
        self.assertEqual(len(calls), 1)
        self.assertLess(elapsed, self.HOOK_TIMEOUT - 1.0)

    def test_total_budget_stays_inside_hook_timeout(self):
        # Hung reads stop at the 7 s writer ceiling: at most 3 s + 3 s + the
        # remainder, never the fourth, and the whole writer run stays inside
        # the hook timeout with room for the guard's own work.
        calls, elapsed = self.assertChain('budget', headed('#1801, #1806, #1807 and #1808'), False)
        self.assertLessEqual(len(calls), 3)
        self.assertLess(elapsed, self.HOOK_TIMEOUT - 1.0)

    def test_older_foreign_headings_cannot_starve_the_current_artifact(self):
        older = [JS + '## Pre-Mortem for #%d\n' % n + PREMORTEM for n in (9001, 9002, 9003, 9004)]
        calls, _ = self.assertChain('starvation', older + [headed('PR #1748')], True)
        # The newest comment is read first; the cap then stops after four reads.
        self.assertEqual((calls[0]['pr'], len(calls)), ('1748', 4))

    def test_strict_key_after_heading_excludes_without_lookup(self):
        calls, _ = self.assertChain('key-after-heading', headed('PR #1748') + 'Refs: o/r#1748\n', False)
        self.assertEqual(calls, [])

    def test_refs_and_issue_keys_stay_strict(self):
        for key in ('Refs', 'Issue'):
            with self.subTest(key):
                calls, _ = self.assertChain('key-' + key, key + ': #1748\n' + headed('#1526'), False)
                self.assertEqual(calls, [])

    def test_mixed_case_identity_counts(self):
        self.assertChain('mixed-case', headed('O/R#1751'), True)

    def test_leading_zero_ref_shares_cache(self):
        calls, _ = self.assertChain('leading-zero', JS + '## Pre-Mortem for #1748\n' + PREMORTEM
                                    + '## Investigation for #01748\n' + INVEST, True)
        self.assertEqual(len(calls), 1)

    def test_huge_ref_number_excluded_without_read(self):
        # 5000 digits exceed Python's int-digit limit (3.9.14+/3.11+); the ref
        # is rejected before int(), so api_ok is untouched (asserted in chain).
        calls, _ = self.assertChain('huge-ref', headed('#' + '7' * 5000), False)
        self.assertEqual(calls, [])

    def test_foreign_gh_host_reads_nothing(self):
        calls, _ = self.assertChain('gh-host', headed('PR #1748'), False, {'GH_HOST': 'github.example.com'})
        self.assertEqual(calls, [])

    def test_lookup_cap_and_cache(self):
        # Four non-PR refs before the own PR in one heading: the cap stops at
        # four reads, so the own PR is never read and the comment stays excluded.
        calls, _ = self.assertChain('cap', headed('#9001, #9002, #9003, #9004 and #1748'), False)
        self.assertEqual(len(calls), 4)
        # The same own PR in four headings is read once.
        body = JS + ''.join('## Pre-Mortem for #1748\n' + PREMORTEM for _ in range(4)) + '## Investigation for #1748\n' + INVEST
        calls, _ = self.assertChain('cache', body, True)
        self.assertEqual(len(calls), 1)

    # Controls.
    def test_current_ticket_heading_needs_no_lookup(self):
        calls, _ = self.assertChain('current', headed('#1526'), True)
        self.assertEqual(calls, [])

    def test_plain_heading_control(self):
        calls, _ = self.assertChain('plain', headed('the export'), True)
        self.assertEqual(calls, [])

    def test_query_is_the_resolver_pr_identity_read(self):
        """The writer reuses the resolver's existing PR identity query, verbatim."""
        flags, _, calls, _ = self.chain('query', headed('#1748'))
        sent = calls[0]['query']
        resolver = ast.parse((LIB / 'resolve-think-gate.py').read_text())
        literals = {node.value for node in ast.walk(resolver) if isinstance(node, ast.Constant) and isinstance(node.value, str)}
        self.assertIn(sent, literals)


if __name__ == '__main__':
    unittest.main(verbosity=2)

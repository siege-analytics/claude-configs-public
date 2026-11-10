"""#1164 B1/B2 gate-bypass regressions from the hostile review of main 9f47b035.

B1: historical payloads remain byte-for-byte evidence. Under the current typed
operation contract, standalone comment bodies are descriptive metadata; old
word-based expected exits do not define authority or require a fresh owner GO.
B2: pipeline_state.py must count only comments by the task's own actor or an
owner-granted role, that declare no other ticket, outside HTML code/quote
containers; the unchanged universal-mutation-gate then refuses (exit 2).
Every payload and fixture from the review harness is ported, open and closed.
"""
import json
import os
import shlex
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GUARD = ROOT / 'hooks/bash/coordinator-status-guard.sh'
LIB = ROOT / 'hooks/lib'
GATE = ROOT / 'hooks/bash/universal-mutation-gate.sh'
ENV = {k: v for k, v in os.environ.items()
       if not k.startswith(('CRAFT', 'CLAUDE', 'CCP', 'CODEX')) and k != 'SESSION_ID'}

MARKER = '## Pre-Mortem\nTicket: #1164\n'
# name: (comment body, expected guard exit). The review harness payloads come first.
B1 = {
    'original_mitigation': (MARKER + 'Mitigation: The gate is complete. We merged and released the fix; production is ready.', 2),
    'original_conditional': (MARKER + 'If you need the current status: the gate is complete; we merged and released the fix.', 2),
    'original_field_conditional': (MARKER + 'Status: If anyone asks, the gate is complete; we merged and released the fix.', 2),
    'original_split_sentence': (MARKER + 'If the gate fails, investigate. It passed; the fix is merged and released.', 2),
    'original_frontmatter': ('---\nMitigation: We merged and released the fix; the gate is green.\n---\n' + MARKER, 2),
    'conditional_comma': (MARKER + 'If anyone asks, the gate is complete and we merged and released the fix; production is ready.', 2),
    'conditional_no_split': (MARKER + 'If anyone asks, the gate is complete and we merged and released the fix and production is ready.', 2),
    'wrapped_mitigation': (MARKER + 'Mitigation: monitor the gate.\n    The gate is complete. We merged and released the fix; production is ready.', 2),
    'plain_claim_control': (MARKER + 'Status: merged, released, ready. The gate is complete.', 2),
    'genuine_hypothesis_control': (MARKER + 'Scenario: the gate could be green while a blocker remains.\nMitigation: we will probe the gate before release.', 0),
    # Same classes, other shapes.
    'conditional_without_comma': (MARKER + 'If anyone asks the gate is complete and we merged and released the fix.', 2),
    'subordinator_without_consequent': (MARKER + 'When asked we merged and released the fix.', 2),
    'conditional_with_empty_consequent': (MARKER + 'If asked the gate is complete,', 2),
    'scenario_label': (MARKER + 'Scenario: The gate is complete. We merged and released the fix.', 2),
    'dash_label': (MARKER + '**Success criteria** — the gate is complete and the fix is merged.', 2),
    'frontmatter_folded_value': ('---\nmitigation: >\n  We merged and released the fix.\n---\n' + MARKER, 2),
    'wrapped_after_blank_label': (MARKER + 'Mitigation:\n\n    We merged and released it.', 2),
    'bare_to_is_not_modal': (MARKER + 'Mitigation: lane status set to done; PR moved to merged.', 2),
    'modal_does_not_cover_later_conjunct': (MARKER + 'Mitigation: it could be green and we merged and released the fix.', 2),
    # A hypothetical field still cannot supply the evidence for its own claim.
    'label_cannot_supply_evidence': (MARKER + 'Mitigation: the owner approved it; merged to main and released.', 2),
    'url_evidence_line_passes': (MARKER + 'The fix is merged and released. Owner approval thread: https://github.com/x/y/pull/1#issuecomment-1. '
                                 'Target branch: develop. Rollout: UAT not applicable.', 0),
    # R1: a question or a modal clause never supplies evidence; predicates never span lines.
    'question_without_modal_supplies_nothing': (MARKER + 'Status: The gate is complete; the fix is merged and released.\n'
                                                'Has the owner approved the rollout?', 2),
    'inverted_question_without_mark': (MARKER + 'Status: The gate is complete; the fix is merged and released.\n'
                                       'Did the owner approve the rollout', 2),
    'owner_evidence_split_across_lines': (MARKER + 'Status: The gate is complete; the fix is merged and released.\n'
                                          'Owner:\napproved.', 2),
    # F4: a capitalized May/Will that governs a verb stays a modal (fail closed).
    'capitalized_may_with_verb_stays_modal': (MARKER + 'Status: The gate is complete; the fix is merged and released.\n'
                                              'The owner May have approved the rollout.', 2),
    'capitalized_will_with_base_verb_stays_modal': (MARKER + 'Status: The gate is complete; the fix is merged and released.\n'
                                                    'The owner Will approve the rollout.', 2),
    'typographic_negated_modal_supplies_nothing': (MARKER + 'Status: The gate is complete; the fix is merged and released.\n'
                                                   'The owner won\u2019t have approved the rollout.', 2),
    'modal_risk_wording_passes': (MARKER + '- Scenario: the PR could be merged before CI finishes and the hook deployed broken.\n'
                                  '- Mitigation: if CI is red, the gate will hold.', 0),
    'delimited_conditional_passes': (MARKER + '- If the PR is merged early, the gate will hold.\n'
                                     '- Trigger condition: CI could be green on a stale head.', 0),
    'could_go_wrong_passes': (MARKER + '5. What could go wrong: the guard could refuse the post.', 0),
    'to_be_green_passes': (MARKER + 'Steps: tests need to be green before the PR is opened.', 0),
    # N5: an auxiliary plus participle is a declarative field value, not an
    # inversion; a name after a field label is not a sentence-opening modal.
    'owner_has_since_approved_passes': (MARKER + 'Status: The gate is complete; the fix is merged and released.\n'
                                        'Owner: has since approved the rollout.', 0),
    'question_field_inversion_still_refused': (MARKER + 'Status: The gate is complete; the fix is merged and released.\n'
                                               'Question: has the owner approved the rollout', 2),
    'field_will_with_base_verb_stays_modal': (MARKER + 'Status: The gate is complete; the fix is merged and released.\n'
                                              'Owner: Will approve the rollout.', 2),
}

H = '## Junior task description\nx\n## Senior adversarial checklist\nx\n## Investigation\nx\n## Pre-Mortem\nx'
STEMS = ('current behavior intended behavior steps to get there success criteria what could go wrong '
         'hasty mistakes observable behavior over-focusing leave out prior work right environment failure case '
         'instance or class done match skip if nobody findings citations disposition fact sheet investigation '
         'verified evidence severity: tiger risks pre-mortem elephant mitigation')


ROOT_MIXED = '---\nticket_refs: [o/r#1164, other/repo#2]\nrelated: other/repo#3\n---\n' + H + '\n'


def comment(body, author='task-owner', association='NONE'):
    return {'id': 1, 'user': {'login': author}, 'author_association': association, 'body': body}


def heading_ref(ref):
    for name in ('Junior task description', 'Senior adversarial checklist', 'Investigation', 'Pre-Mortem'):
        yield name, f'{name} for {ref}'


# name: (API comment records, `gh api user` login or None when it fails, all four signals expected)
B2 = {
    'empty_control': ([], 'task-owner', False),
    'plain_heading_control': ([comment('Ticket: o/r#1164\n' + H)], 'task-owner', True),
    'original_fenced_example': ([comment('Example only; NOT actual posted artifacts:\n```markdown\n' + H + '\n```')], 'task-owner', False),
    'wrong_ticket': ([comment('Ticket: other/repo#99999\n' + H)], 'task-owner', False),
    'outsider_author': ([comment('Ticket: o/r#1164\n' + H, 'unrelated-outsider')], 'task-owner', False),
    'unlabelled_code_fence': ([comment('Example only:\n```\n' + H + '\n```')], 'task-owner', False),
    'tilde_code_fence': ([comment('Example only:\n~~~markdown\n' + H + '\n~~~')], 'task-owner', False),
    'indented_fence_3_spaces': ([comment('Example only:\n   ```markdown\n' + H + '\n   ```')], 'task-owner', False),
    'indented_code_4_spaces': ([comment('Example only:\n\n' + '\n'.join('    ' + line for line in H.splitlines()))], 'task-owner', False),
    'html_pre_code': ([comment('Example only; NOT actual posted artifacts:\n<pre><code>\n' + H + '\n</code></pre>')], 'task-owner', False),
    'html_blockquote': ([comment('Quotation only; NOT actual posted artifacts:\n<blockquote>\n' + H + '\n</blockquote>')], 'task-owner', False),
    'markdown_blockquote': ([comment('\n'.join('> ' + line for line in H.splitlines()))], 'task-owner', False),
    'cross_comment_boundary': ([comment('## Junior task description'), comment('x\n## Senior adversarial checklist'),
                                comment('x\n## Investigation'), comment('x\n## Pre-Mortem'), comment('x')], 'task-owner', False),
    # Same classes, other shapes.
    'outsider_contributor': ([comment('Ticket: o/r#1164\n' + H, 'drive-by', 'CONTRIBUTOR')], 'task-owner', False),
    'outsider_keyword_stems': ([comment('Ticket: o/r#1164\n' + STEMS, 'unrelated-outsider')], 'task-owner', False),
    'actor_lookup_failed_unattested': ([comment('Ticket: o/r#1164\n' + H)], None, False),
    'wrong_ticket_keyword_stems': ([comment('Ticket: other/repo#99999\n' + STEMS)], 'task-owner', False),
    'wrong_ticket_same_number': ([comment('Ticket: other/repo#1164\n' + H)], 'task-owner', False),
    'wrong_ticket_url': ([comment('Ticket: https://github.com/other/repo/issues/99999\n' + H)], 'task-owner', False),
    'wrong_ticket_in_headings': ([comment(H.replace('## Junior task description', '## Junior task description for #99999')
                                          .replace('## Senior adversarial checklist', '## Senior adversarial checklist for #99999')
                                          .replace('## Investigation', '## Investigation for #99999')
                                          .replace('## Pre-Mortem', '## Pre-Mortem for #99999'))], 'task-owner', False),
    'html_comment': ([comment('<!--\n' + H + '\n-->')], 'task-owner', False),
    'html_unclosed_pre': ([comment('<pre>\n' + H)], 'task-owner', False),
    'html_nested_blockquote': ([comment('<blockquote><blockquote>\nx\n</blockquote>\n' + H + '\n</blockquote>')], 'task-owner', False),
    'html_uppercase_with_attribute': ([comment('<PRE class="x">\n' + H + '\n</PRE>')], 'task-owner', False),
    'html_removal_cannot_start_heading': ([comment('\n'.join('<code>a</code>' + line for line in H.splitlines()))], 'task-owner', False),
    # Real artifacts keep counting.
    'details_content_counts': ([comment('Ticket: o/r#1164\n<details><summary>s</summary>\n\n' + H + '\n</details>')], 'task-owner', True),
    'inline_code_tag_mention_counts': ([comment('Ticket: o/r#1164\nMentions `<pre>` and `<blockquote>` inline.\n' + H)], 'task-owner', True),
    'stray_closing_tag_counts': ([comment('Ticket: o/r#1164\n</pre>\n' + H)], 'task-owner', True),
    'member_counts_without_actor': ([comment('Ticket: o/r#1164\n' + H, 'teammate', 'MEMBER')], None, True),
    'own_actor_counts_without_role': ([comment(H, 'task-owner', 'NONE')], 'task-owner', True),
    'current_ticket_among_others_counts': ([comment('Ticket: o/r#1164, other/repo#99999\n' + H)], 'task-owner', True),
    # R2/R3 context controls.
    'yaml_ticket_refs_mixed_excluded': ([comment('---\nticket_refs:\n  - other/repo#99999: comment posted\n'
                                                 '  - o/r#1164: comment posted\n---\n' + H)], 'task-owner', False),
    'nested_code_close_keeps_pre_open': ([comment('<pre><code>a</code>\n' + H + '\n</pre>')], 'task-owner', False),
    'unclosed_cdata': ([comment('<![CDATA[\n' + H)], 'task-owner', False),
    # F2/N1 (decision A): front matter is one identity region, never parsed;
    # every reference in it must be the current ticket.
    'front_matter_inline_flow_foreign_only': ([comment('---\nticket_refs: [other/repo#1, other/repo#2]\n---\n' + H)],
                                              'task-owner', False),
    'front_matter_mixed_current_and_foreign_excluded': ([comment('---\nticket_refs: [o/r#1164, other/repo#2]\n---\n' + H)],
                                                        'task-owner', False),
    'front_matter_current_only_counts': ([comment('---\nticket: o/r#1164\nrelated: "#1164"\n---\n' + H)], 'task-owner', True),
    'front_matter_without_refs_counts': ([comment('---\ntitle: notes\n---\n' + H)], 'task-owner', True),
    'body_ticket_value_after_blank_line': ([comment('Ticket:\n\n  other/repo#99999\n' + H)], 'task-owner', False),
    # F3: CommonMark HTML blocks. Type 6 ends only at a blank line; type 7 cannot
    # interrupt a paragraph.
    'type6_div_without_blank_line': ([comment('Ticket: o/r#1164\n<div>\nx\n</div>\n' + H)], 'task-owner', False),
    'type7_tag_after_blank_line': ([comment('Ticket: o/r#1164\n\n<span>\n' + H)], 'task-owner', False),
    'type7_tag_cannot_interrupt_paragraph': ([comment('Ticket: o/r#1164\n<span>\n' + H)], 'task-owner', True),
    # N3/N4: one block classifier for headings, keyword stems and identity.
    'type7_after_star_break': ([comment('Ticket: o/r#1164\n\n***\n<span>\n' + H)], 'task-owner', False),
    'type7_after_setext_heading': ([comment('Ticket: o/r#1164\n\nIntro\n=====\n<span>\n' + H)], 'task-owner', False),
    'processing_instruction_stems': ([comment('Ticket: o/r#1164\n<?x\n' + STEMS + '\n?>')], 'task-owner', False),
    'type6_block_stems': ([comment('Ticket: o/r#1164\n<div>\n' + STEMS + '\n</div>')], 'task-owner', False),
    'foreign_ticket_in_cdata_example': ([comment('Ticket: o/r#1164\n<![CDATA[\nTicket: other/repo#9\n]]>\n' + H)],
                                        'task-owner', True),
    'foreign_ticket_in_type6_example': ([comment('Ticket: o/r#1164\n<div>\nTicket: other/repo#9\n</div>\n\n' + H)],
                                        'task-owner', True),
    'inline_code_tag_cannot_hide_foreign_ticket': ([comment('See `<pre>` here.\nTicket: other/repo#9\n' + H)],
                                                   'task-owner', False),
    # Root review of 16e1a61: line endings are normalized before identity and
    # classification; quoted and indented examples never supply a signal.
    'root_mixed_front_matter_lf': ([comment(ROOT_MIXED)], 'task-owner', False),
    'root_mixed_front_matter_crlf': ([comment(ROOT_MIXED.replace('\n', '\r\n'))], 'task-owner', False),
    'mixed_front_matter_cr_only': ([comment(ROOT_MIXED.replace('\n', '\r'))], 'task-owner', False),
    'foreign_front_matter_crlf': ([comment(('---\nticket_refs: [other/repo#2]\n---\n' + H + '\n').replace('\n', '\r\n'))],
                                  'task-owner', False),
    'current_front_matter_crlf_counts': ([comment(('---\nticket_refs: [o/r#1164]\n---\n' + H + '\n').replace('\n', '\r\n'))],
                                         'task-owner', True),
    'plain_headings_crlf_count': ([comment(('Ticket: o/r#1164\n' + H + '\n').replace('\n', '\r\n'))], 'task-owner', True),
    'root_quoted_keyword_stems': ([comment('Ticket: o/r#1164\nExample only:\n> ' + STEMS)], 'task-owner', False),
    'quoted_stems_lazy_continuation': ([comment('Ticket: o/r#1164\n\n> Example only:\n' + STEMS)], 'task-owner', False),
    'root_indented_keyword_stems': ([comment('Ticket: o/r#1164\nExample only:\n    ' + STEMS)], 'task-owner', False),
    'indented_code_stems_after_blank': ([comment('Ticket: o/r#1164\nExample only:\n\n    ' + STEMS)], 'task-owner', False),
    'tab_indented_code_stems': ([comment('Ticket: o/r#1164\nExample only:\n\n\t' + STEMS)], 'task-owner', False),
    'visible_keyword_stems_count': ([comment('Ticket: o/r#1164\n' + STEMS)], 'task-owner', True),
    'list_continuation_stems_count': ([comment('Ticket: o/r#1164\n- Notes:\n\n    ' + STEMS)], 'task-owner', True),
    'real_headings_after_quote_count': ([comment('Ticket: o/r#1164\n> quoted aside\n\n' + H)], 'task-owner', True),
    'quoted_foreign_ticket_example_counts': ([comment('Ticket: o/r#1164\n> Ticket: other/repo#9\n\n' + H)], 'task-owner', True),
    'indented_wrapped_foreign_ticket_excludes': ([comment('Ticket:\n    other/repo#9\n\n' + H)], 'task-owner', False),
}

COMMENT_QUERY = '.[] | {author: .user.login, association: .author_association, body: .body} | @json'
LEGACY_QUERY = '.[].body | @json'
# A fake gh that applies the writer's actual jq query to raw API records with
# real jq, as gh does (null user/author_association included). It also serves
# the pre-#1164 body-only query, so a reverted writer reproduces the original
# bypass instead of an unreachable API.
FAKE_GH = '''#!{python}
import json, subprocess, sys
from pathlib import Path
here = Path(__file__).resolve().parent.parent
args = sys.argv[1:]
if args[:2] == ['api', 'user']:
    actor = json.loads((here / 'actor.json').read_text())
    if actor is None:
        sys.exit(1)
    print(actor)
    sys.exit(0)
assert args[:2] == ['api', 'repos/o/r/issues/1164/comments'], args
query = args[args.index('-q') + 1]
assert query in ({query!r}, {legacy!r}), query
records = (here / 'api-comments.json').read_text()
sys.exit(subprocess.run(['jq', '-r', query], input=records, text=True, timeout=10).returncode)
'''
REVIEW_CASES = json.loads((Path(__file__).resolve().parent / 'gate_bypass_1164_review_cases.json').read_text())


def guard(body):
    payload = {'tool_name': 'Bash', 'cwd': str(ROOT),
               'tool_input': {'command': 'gh issue comment 1164 --body ' + shlex.quote(body)}}
    return subprocess.run(['bash', str(GUARD)], input=json.dumps(payload), text=True,
                          capture_output=True, env=ENV, timeout=60)


class GuardArtifactLane(unittest.TestCase):
    def test_historical_b1_payloads_are_descriptive_metadata(self):
        for name, (body, historical_expected) in B1.items():
            with self.subTest(name):
                result = guard(body)
                self.assertEqual(result.returncode, 0, result.stderr)

    def test_historical_b1_corpus_is_descriptive_metadata(self):
        """Keep every body and historical expectation, including formerly held rows."""
        for case in REVIEW_CASES['B1']:
            with self.subTest(case['file'] + ':' + case['name']):
                self.assertEqual(guard(case['body']).returncode, 0)



class WriterGateChain(unittest.TestCase):
    """Writer signals feed the unchanged Tier C universal-mutation-gate."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def chain(self, name, comments, actor):
        case = Path(self.tmp.name) / name
        session = case / 'workspace/sessions/fixture-session'
        task, repo, fake = session / 'tasks/t', case / 'repo', case / 'fakebin'
        for path in (task, repo / 'hooks/bash', repo / 'plans', fake):
            path.mkdir(parents=True)
        subprocess.run(['git', 'init', '-q', str(repo)], check=True, timeout=10)
        existing = repo / 'hooks/bash/example.sh'
        existing.write_text('#!/bin/bash\n# fixture only\n')
        ident = {'ticket': 'o/r#1164', 'task_id': 'o/r#1164', 'sessionId': session.name, 'repo_root': str(repo),
                 'scope_paths': [str(repo)], 'status': 'implementing', 'tier': 'C'}
        (task / 'think-gate.json').write_text(json.dumps(ident))
        (task / 'investigate-gate.json').write_text(json.dumps(dict(ident, findings=[{'claim': 'Local setup is valid.'}])))
        (repo / 'plans/pre-mortem-local.md').write_text('o/r#1164\nTiger 1: Fixture setup risk\nSeverity: 1\nImplementation may proceed: YES\n')
        (case / 'api-comments.json').write_text(json.dumps(comments))
        (case / 'actor.json').write_text(json.dumps(actor))
        (fake / 'gh').write_text(FAKE_GH.format(python=sys.executable, query=COMMENT_QUERY, legacy=LEGACY_QUERY))
        (fake / 'gh').chmod(0o755)
        env = dict(ENV, PATH=str(fake) + os.pathsep + ENV['PATH'], CRAFT_AGENT_WORKSPACE=str(case / 'workspace'),
                   CRAFT_SESSION_DIR=str(session), CRAFT_SESSION_ID=session.name, CCP_TASK_ID='o/r#1164')
        writer = subprocess.run([sys.executable, str(LIB / 'pipeline_state.py'), str(task / 'think-gate.json'),
                                 str(case / 'workspace'), str(LIB)], cwd=repo, env=env, capture_output=True, text=True, timeout=60)
        self.assertEqual(writer.returncode, 0, writer.stdout + writer.stderr)
        js = json.loads((task / 'junior-senior-gate.json').read_text())
        ap = json.loads((task / 'artifacts-posted-gate.json').read_text())
        # Reachable API: a refusal here is never the stale/unreachable path.
        self.assertTrue(js['api_reachable'] and ap['api_reachable'])
        flags = [js['junior_found'], js['senior_found'], ap['investigate_posted'], ap['premortem_posted']]
        exits = []
        for target in (existing, repo / 'hooks/example.sh'):
            payload = {'sessionId': session.name, 'tool_name': 'Write', 'cwd': str(repo),
                       'tool_input': {'file_path': str(target), 'content': 'fixture only'}}
            gate = subprocess.run(['bash', str(GATE)], cwd=repo, env=env, input=json.dumps(payload),
                                  text=True, capture_output=True, timeout=60)
            exits.append((gate.returncode, gate.stdout + gate.stderr))
        return flags, exits

    def assertChain(self, name, comments, actor, counted):
        flags, exits = self.chain(name, comments, actor)
        self.assertEqual(flags, [counted] * 4)
        for code, output in exits:
            self.assertEqual(code, 0 if counted else 2, output)
            if not counted:
                self.assertIn('Tier', output)

    def test_b2_chain(self):
        for name, (comments, actor, counted) in B2.items():
            with self.subTest(name):
                self.assertChain(name, comments, actor, counted)

    def test_review_corpus_b2(self):
        """Every B2 record set of the 371c4fe review, byte-for-byte; R2/R3 cases now refuse."""
        for index, case in enumerate(REVIEW_CASES['B2']):
            with self.subTest(case['file'] + ':' + case['name']):
                actor = None if case['actor_failure'] else case['actor']
                self.assertChain('review-%d' % index, case['records'], actor, case['expected_counted'])


if __name__ == '__main__':
    unittest.main(verbosity=2)

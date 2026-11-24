#!/usr/bin/env python3
"""Explicit REST GET proof and real preexecution output-scope controls."""
import shlex
import unittest
from task_keyed_gates import Gates


class ExplicitGet(Gates):
    endpoint = "repos/example/target/issues/3133/comments?since=2026-11-13T00:00:00Z&per_page=100"

    def test_get_forms_share_classifier_and_composed_reader(self):
        import task_actions
        classifier = task_actions._released_read_classifier()
        for flags in ('', '--method GET', '--method=GET', '-X GET', '-XGET', '-iXGET', '-iX GET', '-X=GET', '-iX=GET'):
            command = 'gh api ' + flags + ' ' + shlex.quote(self.endpoint)
            with self.subTest(flags=flags):
                self.assertEqual(classifier.main(command), 0)
                self.assertTrue(task_actions.reader(shlex.split(command)))
                self.assertGate(0, command)

    def test_help_is_documentation_not_an_option_value_escape(self):
        import task_actions
        for command in ('gh api --help', 'gh api -h', 'gh api repos/example/target --help'):
            self.assertGate(0, command)
            self.assertTrue(task_actions.reader(shlex.split(command)))
        for value_flag in ('-H', '--header', '-q', '--jq', '-t', '--template', '-X', '--method'):
            self.assertGate(2, 'gh api repos/example/target ' + value_flag + ' --help -XPOST')
        self.assertGate(2, 'gh api --help repos/example/target --method POST')
        self.assertGate(2, 'gh api -h repos/example/target -f body=x')

    def test_graphql_endpoint_is_not_a_rest_resource_name(self):
        for endpoint in ('repos/owner/graphql', 'repos/owner/repo/branches/graphql'):
            self.assertGate(0, 'gh api --method GET ' + shlex.quote(endpoint))
            self.assertGate(0, 'gh api ' + shlex.quote(endpoint))
        for endpoint in ('graphql', '/graphql', 'graphql?query=mutation',
                         'https://api.github.com/graphql', 'https://github.example/api/graphql',
                         'https://[invalid/graphql'):
            self.assertGate(2, 'gh api --method GET ' + shlex.quote(endpoint))

    def test_owned_output_and_reader_companion(self):
        self.task('example/target#3133', self.repo / 'a', status='implementing', artifacts=False)
        command = 'gh api --method GET ' + shlex.quote(self.endpoint)
        output = self.repo / 'a' / 'comments.json'
        self.assertGate(0, command + ' > ' + shlex.quote(str(output)))
        self.assertGate(0, command + ' > ' + shlex.quote(str(output)) + ' && jq . ' + shlex.quote(str(output)))
        self.assertFalse(output.exists())  # Admission only: no GH invocation or output write.
        self.assertGate(2, command + ' > ' + shlex.quote(str(self.repo / 'b' / 'foreign.json')))
        self.assertGate(2, command + ' && touch ' + shlex.quote(str(self.repo / 'b' / 'foreign')))

    def test_write_body_graphql_and_dynamic_controls(self):
        self.task('example/target#3133', self.repo / 'a', status='designing', artifacts=False)
        for suffix in ('--method POST', '--method=DELETE', '-XPOST', '-iXDELETE',
                       '--method GET -f body=x', '--method GET -F body=@file',
                       '--method GET --input body.json', '--method GET --method POST',
                       '--method', '-X', '--meth=GET', '-iFbody=x', '-Xget', '-X= GET', '--method= GET'):
            with self.subTest(suffix=suffix):
                self.assertGate(2, 'gh api ' + shlex.quote(self.endpoint) + ' ' + suffix)
        for command in ("gh api --method GET graphql", "gh api -XGET graphql -f 'query=mutation { deleteIssue(input:{issueId:X}) { clientMutationId } }'",
                        'gh api --method "$METHOD" repos/example/target',
                        'gh api -XGET repos/example/target && gh api -XPOST repos/example/target'):
            with self.subTest(command=command):
                self.assertGate(2, command)


def load_tests(loader, tests, pattern):
    return unittest.TestSuite(ExplicitGet(name) for name in ExplicitGet.__dict__ if name.startswith('test_'))


if __name__ == '__main__':
    unittest.main()

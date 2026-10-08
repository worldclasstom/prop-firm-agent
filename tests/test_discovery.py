"""Synthetic API account discovery, pagination and private setup isolation."""
import contextlib
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

from propfirm.__main__ import main
from propfirm.config import save_json
from propfirm.discovery import discover_accounts
from propfirm.propr import APIError, Client, ReadOnlyClient, DEFAULT_BUILDER_CODE


class Opener:
    def __init__(self, attempts, challenges=None):
        self.attempts = attempts
        self.challenges = challenges or []
        self.calls = []

    def open(self, request, timeout):
        self.calls.append(request)
        url = urlsplit(request.full_url)
        rows = self.attempts if url.path.endswith('challenge-attempts') else self.challenges
        offset = int(parse_qs(url.query)['offset'][0])
        # Server caps pages below the requested limit: discovery must keep paging.
        body = {'data': rows[offset:offset + 1], 'total': len(rows)}
        response = io.BytesIO(json.dumps(body).encode())
        response.status = 200
        return response


class DiscoveryTests(unittest.TestCase):
    def test_multiple_accounts_all_pages_and_no_inferred_trial(self):
        opener = Opener([
            {'accountId': 'a', 'attemptId': 'one', 'status': 'active', 'challengeId': 'c'},
            {'accountId': 'b', 'attemptId': 'two', 'status': 'active'},
            {'accountId': 'c', 'status': 'failed'},
            {'accountId': 'd', 'status': 'passed'},
        ], [{'challengeId': 'c', 'name': 'Free Trial'}])
        documents, summary = discover_accounts(ReadOnlyClient('synthetic', opener=opener))
        self.assertEqual([a['account_id'] for a in summary['accounts']], ['a', 'b', 'c', 'd'])
        self.assertTrue(all(a['account_type'] == 'unverified' for a in summary['accounts']))
        self.assertEqual(summary['accounts'][0]['attempts'][0]['challenge_name'], 'Free Trial')
        self.assertEqual(len(documents['attempts']), 4)
        self.assertTrue(summary['selection_required'])
        for request in opener.calls:
            self.assertEqual(request.method, 'GET')
            self.assertEqual(urlsplit(request.full_url).netloc, 'api.propr.xyz')
            self.assertEqual(request.get_header('X-api-key'), 'synthetic')
            self.assertEqual(request.get_header('X-builder-code'), DEFAULT_BUILDER_CODE)

    def test_single_account_still_requires_selection(self):
        _, summary = discover_accounts(ReadOnlyClient('synthetic', opener=Opener([{'accountId': 'one'}])))
        self.assertTrue(summary['selection_required'])
        self.assertNotIn('selected_account_id', summary)

    def test_empty_result_does_not_suggest_purchase(self):
        _, summary = discover_accounts(ReadOnlyClient('synthetic', opener=Opener([])))
        self.assertEqual(summary['accounts'], [])
        self.assertIn('Free Trial', summary['next'])
        self.assertIn('Do not buy', summary['next'])

    def test_duplicates_grouped_and_missing_ids_reported(self):
        _, summary = discover_accounts(ReadOnlyClient('synthetic', opener=Opener([
            {'accountId': 'a', 'attemptId': 'one'}, {'accountId': 'a', 'attemptId': 'two'},
            {'attemptId': 'missing'}, {'accountId': ''}])))
        self.assertEqual(len(summary['accounts']), 1)
        self.assertEqual(len(summary['accounts'][0]['attempts']), 2)
        self.assertEqual(summary['attempts_without_account_id'], 2)

    def test_read_only_rejects_writes_and_external_origin(self):
        opener = Opener([])
        client = ReadOnlyClient('synthetic', opener=opener)
        for method, path, payload in [('POST', '/v1/accounts/a/orders', {}),
                                     ('GET', 'https://external.example/v1/accounts', None),
                                     ('GET', '/v1/challenge-attempts', {'key': 'value'})]:
            with self.assertRaises(ValueError):
                client.request(method, path, payload)
        self.assertEqual(opener.calls, [])
        with self.assertRaises(ValueError):
            Client('synthetic', '')

    def test_failure_is_not_an_empty_account_list(self):
        client = ReadOnlyClient('synthetic')
        with patch.object(client, 'request', side_effect=APIError(401)):
            with self.assertRaises(APIError):
                discover_accounts(client)

    def test_cli_uses_saved_key_and_preserves_selected_account_and_state(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            key_path = root / '.env'
            key_path.write_text('PROPR_API_KEY=synthetic\n')
            key_path.chmod(0o600)
            save_json(root / 'config.json', {'account_id': 'existing', 'markets': ['preserved']})
            (root / 'approval.json').write_text('existing approval')
            (root / 'state.sqlite').write_bytes(b'existing state')
            preserved = {p.name: p.read_bytes() for p in root.iterdir()}
            output = io.StringIO()
            opener = Opener([{'accountId': 'other', 'status': 'active'}])
            with patch.dict(os.environ, {'PROPFIRM_HOME': directory}, clear=True), \
                    patch('sys.argv', ['propfirm', 'accounts']), \
                    patch('propfirm.propr.build_opener', return_value=opener), \
                    contextlib.redirect_stdout(output):
                self.assertEqual(main(), 0)
            self.assertEqual(json.loads(output.getvalue())['accounts'][0]['account_id'], 'other')
            self.assertNotIn('synthetic', output.getvalue())
            for name, content in preserved.items():
                self.assertEqual((root / name).read_bytes(), content)
            saved = root / 'setup' / 'account-discovery.json'
            self.assertEqual(saved.stat().st_mode & 0o777, 0o600)
            self.assertNotIn('synthetic', saved.read_text())

    def test_malformed_rows_fail_clearly(self):
        client = ReadOnlyClient('synthetic', opener=Opener(['bad row']))
        with self.assertRaisesRegex(ValueError, 'Unrecognized account discovery'):
            discover_accounts(client)

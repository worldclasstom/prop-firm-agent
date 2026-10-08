"""Real loopback HTTP tests with synthetic credentials only."""
import contextlib
import http.client
import io
import os
from pathlib import Path
import tempfile
import threading
import time
import unittest
from urllib.parse import urlencode
from propfirm.connect import ConnectServer, save_key, serve_connect
from propfirm.config import load_key


class ConnectTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.root = Path(self.folder.name)
        self.server = ConnectServer(self.root)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()
        self.folder.cleanup()

    def request(self, method='GET', body=None, headers=None, path=None):
        connection = http.client.HTTPConnection('127.0.0.1', self.server.server_port, timeout=3)
        connection.request(method, path or self.server.path, body, headers or {})
        response = connection.getresponse()
        result = response.status, dict(response.getheaders()), response.read().decode()
        connection.close()
        return result

    def post(self, key='synthetic_trial_key', csrf=None, origin=None):
        return self.request('POST', urlencode({'csrf': csrf or self.server.csrf, 'api_key': key}),
            {'Origin': origin or self.server.origin, 'Content-Type': 'application/x-www-form-urlencoded'})

    def test_form_saves_key_once_without_echo_or_trading(self):
        status, headers, html = self.request()
        self.assertEqual(status, 200)
        self.assertIn('type="password"', html)
        self.assertIn('frame-ancestors', headers['Content-Security-Policy'])
        self.assertEqual(headers['Cache-Control'], 'no-store')
        status, _, html = self.post()
        self.assertEqual(status, 200)
        self.assertIn('API key saved.', html)
        self.assertNotIn('synthetic_trial_key', html)
        self.assertEqual(load_key(self.root), 'synthetic_trial_key')
        self.assertEqual((self.root / '.env').stat().st_mode & 0o777, 0o600)
        self.assertEqual([p.name for p in self.root.iterdir()], ['.env'])
        self.assertEqual(self.post('replacement')[0], 410)
        self.assertEqual(load_key(self.root), 'synthetic_trial_key')

    def test_rejects_cross_origin_and_wrong_csrf(self):
        self.assertEqual(self.post(origin='https://malicious.example')[0], 403)
        self.assertEqual(self.post(csrf='wrong')[0], 403)
        self.assertEqual(self.post(csrf='non-ascii-☃')[0], 403)
        self.assertFalse((self.root / '.env').exists())

    def test_embedded_browser_opaque_origin_requires_same_origin_and_csrf(self):
        headers = {'Origin': 'null', 'Content-Type': 'application/x-www-form-urlencoded'}
        body = urlencode({'csrf': self.server.csrf, 'api_key': 'synthetic'})
        self.assertEqual(self.request('POST', body, headers)[0], 403)
        headers['Sec-Fetch-Site'] = 'cross-site'
        self.assertEqual(self.request('POST', body, headers)[0], 403)
        headers['Sec-Fetch-Site'] = 'same-origin'
        bad = urlencode({'csrf': 'wrong', 'api_key': 'synthetic'})
        self.assertEqual(self.request('POST', bad, headers)[0], 403)
        self.assertEqual(self.request('POST', body, headers)[0], 200)

    def test_rejects_rebound_host_and_unknown_path(self):
        self.assertEqual(self.request(headers={'Host': 'malicious.example'})[0], 403)
        self.assertEqual(self.request(path='/')[0], 404)

    def test_invalid_key_can_be_retried_and_never_echoed(self):
        status, _, html = self.post('synthetic\nINJECT=value')
        self.assertEqual(status, 400)
        self.assertNotIn('INJECT', html)
        self.assertFalse((self.root / '.env').exists())
        self.assertEqual(self.post()[0], 200)

    def test_expiration_and_missing_origin(self):
        body = urlencode({'csrf': self.server.csrf, 'api_key': 'synthetic'})
        self.assertEqual(self.request('POST', body, {'Content-Type': 'application/x-www-form-urlencoded'})[0], 403)
        self.server.deadline = time.monotonic() - 1
        self.assertEqual(self.request()[0], 410)
        self.assertEqual(self.post()[0], 410)

    def test_size_and_duplicate_fields_rejected(self):
        headers = {'Origin': self.server.origin, 'Content-Type': 'application/x-www-form-urlencoded'}
        self.assertEqual(self.request('POST', 'x' * 16385, headers)[0], 400)
        self.assertEqual(self.request('POST', 'csrf=x&api_key=a&api_key=b', headers)[0], 400)
        self.assertFalse((self.root / '.env').exists())

    def test_atomic_save_preserves_other_files_and_replaces_symlink(self):
        target = self.root / 'other'
        target.write_text('untouched')
        (self.root / '.env').symlink_to(target)
        save_key(self.root, 'synthetic')
        self.assertEqual(target.read_text(), 'untouched')
        self.assertFalse((self.root / '.env').is_symlink())
        self.assertEqual(load_key(self.root), 'synthetic')

    def test_rejects_repository_storage(self):
        with self.assertRaises(ValueError):
            save_key(Path(__file__).resolve().parents[1] / 'private-test', 'synthetic')
        for marker in ['.git', 'pyproject.toml']:
            checkout = self.root / marker.replace('.', '')
            checkout.mkdir()
            (checkout / marker).touch()
            (checkout / 'propfirm').mkdir()
            with self.assertRaises(ValueError):
                save_key(checkout / 'private', 'synthetic')
            self.assertFalse((checkout / 'private').exists())

    def test_cli_timeout_leaves_no_credentials(self):
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(serve_connect(self.root, timeout=1), 1)
        self.assertFalse((self.root / '.env').exists())


if __name__ == '__main__':
    unittest.main()

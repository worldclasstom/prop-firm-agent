import importlib.util
import json
import os
from pathlib import Path
import unittest
from unittest.mock import patch
from urllib.error import HTTPError, URLError

spec = importlib.util.spec_from_file_location('runtime_network_probe',
    Path(__file__).resolve().parents[1] / 'scripts' / 'runtime_network_probe.py')
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)


class Response:
    status = 200
    def __enter__(self): return self
    def __exit__(self, *args): pass


class RuntimeNetworkProbeTests(unittest.TestCase):
    def test_only_fixed_public_requests_and_no_secret_output(self):
        requests = []
        class Opener:
            def open(self, request, timeout):
                requests.append(request)
                return Response()
        secret = 'SENSITIVE_SENTINEL'
        with patch.dict(os.environ, {'HTTPS_PROXY': 'https://user:' + secret + '@proxy',
                                     'PROPR_API_KEY': secret}), \
             patch.object(probe, 'build_opener', return_value=Opener()):
            result = probe.probe()
        self.assertNotIn(secret, json.dumps(result))
        self.assertTrue(result['environment_presence']['HTTPS_PROXY'])
        self.assertEqual([r.full_url for r in requests],
                         ['https://api.propr.xyz/v1/health', 'https://api.hyperliquid.xyz/info'])
        self.assertEqual([r.get_method() for r in requests], ['GET', 'POST'])
        self.assertEqual(requests[1].data, b'{"type":"meta"}')
        for request in requests:
            self.assertNotIn('X-api-key', request.headers)

    def test_network_failure_keeps_errno_without_exception_text(self):
        class Opener:
            def open(self, *args, **kwargs):
                raise URLError(OSError(101, 'SENSITIVE_SENTINEL'))
        result = probe.check(None, Opener())
        self.assertEqual(result['errno'], 101)
        self.assertFalse(result['http_response_received'])
        self.assertNotIn('SENSITIVE_SENTINEL', json.dumps(result))

    def test_http_rejection_is_reachable_but_not_success(self):
        class Opener:
            def open(self, *args, **kwargs):
                raise HTTPError('https://private', 403, 'SENSITIVE_SENTINEL', {}, None)
        result = probe.check(None, Opener())
        self.assertTrue(result['http_response_received'])
        self.assertFalse(result['success'])
        self.assertEqual(result['status'], 403)
        self.assertNotIn('SENSITIVE_SENTINEL', json.dumps(result))

    def test_redirect_is_not_followed(self):
        self.assertIsNone(probe.NoRedirects().redirect_request(None, None, 302, '', {},
                                                             'https://elsewhere'))

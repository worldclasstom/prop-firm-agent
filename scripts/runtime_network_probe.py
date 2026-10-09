"""Compare launch contexts using public reads; no keys, orders, or configuration edits.

Run with the worker's Python and launcher, then compare with the command context.
Results describe this process only; they do not certify authenticated access,
WebSocket operation, persistence, or recovery.
"""
import errno
import json
import os
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, HTTPRedirectHandler, build_opener, getproxies


class NoRedirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def failure(error):
    # Never serialize exception text, response bodies, headers, or proxy URLs.
    reason = error.reason if isinstance(error, URLError) else error
    number = getattr(reason, 'errno', None)
    return {'error_type': type(reason).__name__,
            'errno': number if isinstance(number, int) else None,
            'errno_name': errno.errorcode.get(number) if isinstance(number, int) else None}


def check(request, opener):
    start = time.monotonic()
    try:
        with opener.open(request, timeout=10) as response:
            status = response.status
            result = {'http_response_received': True, 'status': status,
                      'success': 200 <= status < 300}
    except HTTPError as error:
        result = {'http_response_received': True, 'status': error.code, 'success': False}
        error.close()
    except Exception as error:
        result = {'http_response_received': False, 'success': False, **failure(error)}
    result['elapsed_seconds'] = round(time.monotonic() - start, 3)
    return result


def probe():
    variables = ('HTTP_PROXY', 'HTTPS_PROXY', 'ALL_PROXY', 'NO_PROXY',
                 'http_proxy', 'https_proxy', 'all_proxy', 'no_proxy',
                 'SSL_CERT_FILE', 'SSL_CERT_DIR', 'REQUESTS_CA_BUNDLE')
    proxies = getproxies()
    opener = build_opener(NoRedirects())
    # Propr's edge answers urllib's default agent string with HTTP 403 while the
    # same request with a product agent string gets 200 (observed 2026-10-09 from
    # a GitHub-hosted runner and from another cloud host). The kit's clients
    # already send a product agent; the diagnostic must send one too, or it
    # reports a block that the trading path does not experience.
    agent = {'User-Agent': 'ProsperityAgentKit-probe/0.2.0'}
    requests = {
        'propr_public_health': Request('https://api.propr.xyz/v1/health', headers=agent),
        'hyperliquid_public_metadata': Request('https://api.hyperliquid.xyz/info',
            data=b'{"type":"meta"}', headers={'Content-Type': 'application/json', **agent}, method='POST'),
    }
    return {
        'at_epoch': time.time(), 'pid': os.getpid(), 'parent_pid': os.getppid(),
        'python': sys.version.split()[0],
        'environment_presence': {name: bool(os.environ.get(name)) for name in variables},
        'effective_proxy_presence': {name: bool(proxies.get(name))
                                     for name in ('http', 'https', 'all', 'no')},
        'checks': {name: check(request, opener) for name, request in requests.items()},
        'scope': 'Public HTTP only; no credentials loaded; does not establish trading readiness.',
    }


if __name__ == '__main__':
    result = probe()
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if all(row['success'] for row in result['checks'].values()) else 1)

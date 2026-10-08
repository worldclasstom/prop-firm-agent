"""Restricted Propr HTTP client with separate authentication and builder attribution."""
from urllib.parse import urlsplit
from urllib.request import Request, HTTPRedirectHandler

DEFAULT_BUILDER_CODE = 'builder_pigUW7hSDKW52DhhFxFyYkRVxq3T7FIq'
ORIGIN = 'https://api.propr.xyz'


class NoRedirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def read_request(path: str, api_key: str, builder_code: str = DEFAULT_BUILDER_CODE) -> Request:
    """Prepare an official-origin GET; an empty builder code opts out."""
    parsed = urlsplit(path)
    if (parsed.scheme or parsed.netloc or not path.startswith('/v1/') or
            parsed.fragment or '\\' in path or '..' in parsed.path or
            any(ord(c) <= 32 for c in path)):
        raise ValueError('Expected a Propr /v1/ path')
    if not api_key or any(c in api_key + builder_code for c in '\r\n'):
        raise ValueError('Invalid header configuration')
    headers = {'X-API-Key': api_key, 'Accept': 'application/json'}
    if builder_code:
        headers['X-Builder-Code'] = builder_code
    return Request(ORIGIN + path, headers=headers, method='GET')

# HTTP client uses the same documented REST contract as the official SDK.
# Do not auto-select an account, retry POSTs, or follow redirects.
import json
import os
import socket
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import build_opener


class APIError(RuntimeError):
    def __init__(self, status=None):
        self.status = status
        super().__init__('Propr request failed' + (f' (HTTP {status})' if status else ' (network/timeout)'))


class ReadOnlyClient:
    """Account discovery without selecting an account or permitting writes."""
    def __init__(self, api_key, builder_code=None, opener=None):
        self.api_key = api_key
        self.builder_code = os.environ.get('PROPR_BUILDER_CODE', DEFAULT_BUILDER_CODE) if builder_code is None else builder_code
        self.opener = opener or build_opener(NoRedirects())

    def request(self, method, path, payload=None, params=None):
        if method != 'GET' or payload is not None:
            raise ValueError('Account discovery permits reads only')
        return self._request(method, path, params=params)

    def _request(self, method, path, payload=None, params=None):
        req = read_request(path + ('?' + urlencode(params) if params else ''), self.api_key, self.builder_code)
        req.method = method
        req.add_header('User-Agent', 'ProsperityAgentKit/0.2.0')
        if payload is not None:
            req.data = json.dumps(payload, allow_nan=False).encode()
            req.add_header('Content-Type', 'application/json')
        try:
            with self.opener.open(req, timeout=10) as response:
                if not 200 <= response.status < 300:
                    raise APIError(response.status)
                return json.load(response)
        except HTTPError as exc:
            raise APIError(exc.code) from None
        except (URLError, socket.timeout, OSError, ValueError):
            raise APIError() from None

    def pages(self, path, **params):
        result, seen = [], set()
        offset = 0
        for _ in range(10000):
            page = self.request('GET', path, params={**params, 'limit': 100, 'offset': offset})
            rows = page.get('data') if isinstance(page, dict) else None
            if not isinstance(rows, list):
                raise ValueError('Unrecognized paginated response')
            fingerprint = json.dumps(rows, sort_keys=True)
            if rows and fingerprint in seen:
                raise ValueError('Pagination repeated a page; refusing incomplete reconciliation')
            seen.add(fingerprint)
            result.extend(rows)
            offset += len(rows)
            total = page.get('total')
            if not rows:
                if total is not None and offset < int(total):
                    raise ValueError('Incomplete paginated response')
                return result
            if total is not None and offset >= int(total):
                return result
        raise ValueError('Pagination did not terminate')

    def attempts(self):
        return self.pages('/v1/challenge-attempts')

    def challenges(self):
        return self.pages('/v1/challenges')


class Client(ReadOnlyClient):
    def __init__(self, api_key, account_id, builder_code=None, opener=None):
        if not account_id:
            raise ValueError('An explicit account ID is required')
        super().__init__(api_key, builder_code, opener)
        self.account_id = account_id

    @property
    def account_path(self):
        return '/v1/accounts/' + quote(self.account_id, safe='')

    def request(self, method, path, payload=None, params=None):
        if method not in ('GET', 'POST'):
            raise ValueError('Unsupported method')
        if method == 'POST' and not (path == self.account_path + '/orders' or
                path.startswith(self.account_path + '/orders/') and path.endswith('/cancel')):
            raise ValueError('Only order submission and cancellation are permitted writes')
        return self._request(method, path, payload, params)

    def account(self):
        return self.request('GET', self.account_path)

    def orders(self):
        return self.pages(self.account_path + '/orders')

    def positions(self):
        return [p for p in self.pages(self.account_path + '/positions', status='open')
                if float(p['quantity']) != 0]

    def submit(self, payload):
        return self.request('POST', self.account_path + '/orders', {'orders': [payload]})

    def cancel(self, order_id):
        return self.request('POST', self.account_path + '/orders/' + quote(order_id, safe='') + '/cancel', {})

    def margin(self, asset):
        return self.request('GET', self.account_path + '/margin-config/' + quote(asset, safe=''))

"""Request preparation only. No networking or trading side effects in this alpha."""
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

"""Short-lived, loopback-only credential form for the user's cloud browser."""
import hmac
from http.server import BaseHTTPRequestHandler, HTTPServer
import os
from pathlib import Path
import secrets
import tempfile
import time
from urllib.parse import parse_qs


def has_repository_marker(directory):
    """Ignore empty cloud-workspace placeholders; reject populated Git markers."""
    marker = directory / '.git'
    try:
        if marker.is_dir():
            return next(marker.iterdir(), None) is not None
        if marker.is_file():
            # A worktree .git file contains a gitdir pointer. Treat any populated
            # marker conservatively, without following or executing its contents.
            with marker.open('rb') as stream:
                return bool(stream.read(4096).strip())
        return False
    except OSError:
        # An unreadable marker must not turn a repository into allowed storage.
        return True


def save_key(root, key):
    key = key.strip()
    if not key or len(key) > 4096 or any(ord(c) < 33 or ord(c) > 126 for c in key):
        raise ValueError('Paste a valid API key without spaces or line breaks.')
    root = Path(root).resolve()
    checkout = Path(__file__).resolve().parents[1]
    if (root == checkout or checkout in root.parents or
            any(has_repository_marker(parent) or
                ((parent / 'pyproject.toml').exists() and (parent / 'propfirm').is_dir())
                for parent in (root, *root.parents))):
        raise ValueError('Credential storage must be outside the source checkout.')
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd, temporary = tempfile.mkstemp(prefix='.credential-', dir=root)
    try:
        with os.fdopen(fd, 'w') as stream:
            stream.write('PROPR_API_KEY=' + key + '\n')
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, root / '.env')
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


STYLE = '''
:root { color-scheme: light; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; color: #101827; background: #eef5fb; }
* { box-sizing: border-box; }
body { margin: 0; padding: 32px 24px; }
main { max-width: 480px; margin: 8vh auto; }
.brand { font-size: 16px; font-weight: 650; margin-bottom: 48px; }
h1 { font-size: clamp(28px, 6vw, 38px); line-height: 1.12; letter-spacing: -.025em; margin: 0 0 20px; }
p { font-size: 16px; line-height: 1.6; color: #3c4d63; margin: 0 0 24px; }
label { display: block; font-weight: 650; margin: 32px 0 10px; }
input { width: 100%; min-height: 52px; border: 1px solid #697b91; border-radius: 8px; background: #fff; color: #101827; padding: 12px 14px; font: inherit; caret-color: #4940a8; }
button { width: 100%; min-height: 52px; border: 0; border-radius: 999px; margin: 20px 0; padding: 12px 20px; background: #5144b5; color: #fff; font: inherit; font-weight: 650; cursor: pointer; }
button:hover { background: #3e328f; }
input:focus-visible,button:focus-visible { outline: 3px solid #286bba; outline-offset: 4px; }
.note { font-size: 14px; }
.error { color: #9c2525; font-weight: 600; }
::selection { background: #d3cbfa; color: #101827; }
'''


def page(path, csrf, *, saved=False, error=''):
    # All interpolated values are generated tokens or fixed application strings.
    content = '''<h1>API key saved.</h1><p>Return to your agent conversation to continue setup.</p>
<p>Your agent will help you select and verify your free-trial account. Trading has not started.</p>''' if saved else f'''
<h1>Connect Propr</h1><p>In Propr, open Settings → Developer and create an API key. Paste it below.</p>
<form method="post" action="{path}" autocomplete="off">
<input type="hidden" name="csrf" value="{csrf}">
<label for="api-key">Propr API key</label>
<input id="api-key" name="api_key" type="password" required maxlength="4096" autocomplete="off" spellcheck="false" aria-describedby="privacy error">
<p id="error" class="error" role="alert">{error}</p>
<button type="submit">Save API key</button></form>
<p id="privacy" class="note">Saved on the computer running your agent. It is not sent to Prosperity Labs or GitHub. Saving the key does not start trading.</p>'''
    return f'<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Connect Propr · Prosperity Labs</title><style>{STYLE}</style></head><body><main><div class="brand">Prosperity Labs</div>{content}</main></body></html>'


class ConnectServer(HTTPServer):
    allow_reuse_address = False

    def __init__(self, root, port=0, timeout=600):
        self.root = Path(root)
        self.path = '/connect/' + secrets.token_urlsafe(32)
        self.csrf = secrets.token_urlsafe(32)
        self.saved = False
        self.deadline = time.monotonic() + timeout
        super().__init__(('127.0.0.1', port), ConnectHandler)
        self.timeout = 1
        self.origin = f'http://127.0.0.1:{self.server_port}'
        self.url = self.origin + self.path


class ConnectHandler(BaseHTTPRequestHandler):
    def log_message(self, *_):
        pass  # Never log request paths, bodies or credentials.

    def setup(self):
        super().setup()
        self.connection.settimeout(5)

    def respond(self, code, html):
        body = html.encode('utf-8')
        self.send_response(code)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('Referrer-Policy', 'no-referrer')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Content-Security-Policy', "default-src 'none'; style-src 'unsafe-inline'; form-action 'self'; frame-ancestors 'none'; base-uri 'none'")
        self.end_headers()
        self.wfile.write(body)

    def allowed(self):
        if self.headers.get('Host') != self.server.origin.removeprefix('http://'):
            self.respond(403, 'This form is only available in the agent computer’s local browser.')
            return False
        if time.monotonic() >= self.server.deadline or self.server.saved:
            self.respond(410, 'This form has closed. Ask your agent to open a new one.')
            return False
        if not hmac.compare_digest(self.path.encode('utf-8'), self.server.path.encode('utf-8')):
            self.respond(404, 'Open the setup form provided by your agent.')
            return False
        return True

    def do_GET(self):
        if self.allowed():
            self.respond(200, page(self.server.path, self.server.csrf))

    def do_POST(self):
        if not self.allowed():
            return
        origin = self.headers.get('Origin')
        # Some embedded cloud browsers send an opaque Origin for local forms.
        # Only accept that case with browser-generated same-origin metadata;
        # the unguessable route and independent CSRF token remain mandatory.
        embedded_local = origin == 'null' and self.headers.get('Sec-Fetch-Site') == 'same-origin'
        if origin != self.server.origin and not embedded_local:
            self.respond(403, 'Reopen the form in the agent computer’s browser.')
            return
        try:
            length = int(self.headers.get('Content-Length', '0'))
            if not 0 < length <= 16384 or self.headers.get_content_type() != 'application/x-www-form-urlencoded':
                raise ValueError()
            fields = parse_qs(self.rfile.read(length).decode('utf-8'), strict_parsing=True, max_num_fields=2)
            if set(fields) != {'csrf', 'api_key'} or any(len(v) != 1 for v in fields.values()):
                raise ValueError()
            if not hmac.compare_digest(fields['csrf'][0].encode('utf-8'), self.server.csrf.encode('utf-8')):
                self.respond(403, 'Reopen the form and try again.')
                return
            save_key(self.server.root, fields['api_key'][0])
        except (ValueError, UnicodeError):
            self.respond(400, page(self.server.path, self.server.csrf, error='Paste a valid API key and try again.'))
            return
        except OSError:
            self.respond(500, page(self.server.path, self.server.csrf, error='The key could not be saved. Return to your agent for help.'))
            return
        self.server.saved = True
        self.respond(200, page(self.server.path, self.server.csrf, saved=True))


def serve_connect(root, port=0, timeout=600):
    if not 1 <= timeout <= 1800:
        raise ValueError('Use a form timeout between 1 and 1800 seconds.')
    with ConnectServer(root, port, timeout) as server:
        print('Open this form in the browser on this same computer, then hand control to the user:', flush=True)
        print(server.url, flush=True)
        print('Do not publish or tunnel this form. It closes after saving or when the timer expires.', flush=True)
        while not server.saved and time.monotonic() < server.deadline:
            server.handle_request()
        if server.saved:
            print('API key saved privately. Continue account selection and verification. Trading has not started.', flush=True)
            return 0
        print('Form expired without saving a key. Run propfirm connect again.', flush=True)
        return 1

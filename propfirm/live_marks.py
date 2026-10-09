"""Propr mark stream for risk equity; no order writes or raw credential logging."""
import json
import logging
import threading
import time
from decimal import Decimal as D


def connect_no_redirects(uri, **kwargs):
    from websockets.sync.client import reconnect

    class NoRedirects(reconnect):
        def process_redirect(self, error):
            return error

    return NoRedirects(uri, **kwargs)


class LiveMarks:
    def __init__(self, api_key, account_id, *, connector=None, clock=time.time):
        self.api_key, self.account_id = api_key, account_id
        self.connector, self.clock = connector, clock
        self.lock = threading.Lock()
        self.stop = threading.Event()
        self.ready = threading.Event()
        self.thread = None
        self.connection = None
        self.connected = False
        self.generation = 0
        self.marks = {}

    def accept(self, message):
        data = message.get('data', {})
        kind = message.get('type', '')
        with self.lock:
            if kind == 'connected':
                self.connected = True
                self.ready.set()
            elif kind == 'mark.updated':
                timestamp = D(str(data.get('timestamp', message.get('timestamp')))) / 1000
                if not timestamp.is_finite() or not -2 <= self.clock() - float(timestamp) <= 10:
                    raise ValueError('Stale or invalid Propr mark event')
                for asset, price in data.get('marks', {}).get('hyperliquid', {}).items():
                    value = D(str(price))
                    if not value.is_finite() or value <= 0:
                        raise ValueError('Invalid Propr mark price')
                    self.marks[asset] = (value, float(timestamp))
            elif kind.startswith(('account.', 'position.', 'order.', 'trade.')):
                # Unknown account IDs invalidate conservatively instead of missing a fill.
                if data.get('accountId') in (None, self.account_id):
                    self.generation += 1

    def disconnected(self):
        with self.lock:
            self.connected = False
            self.ready.clear()
            self.marks.clear()
            self.generation += 1

    def run(self):
        logger = logging.Logger('propfirm.private-websocket')
        logger.addHandler(logging.NullHandler())
        while not self.stop.is_set():
            try:
                connector = self.connector
                if connector is None:
                    connector = connect_no_redirects
                with connector('wss://api.propr.xyz/ws',
                               additional_headers={'X-API-Key': self.api_key},
                               open_timeout=10, close_timeout=2, ping_interval=20,
                               ping_timeout=20, max_size=2**20, logger=logger) as connection:
                    self.connection = connection
                    while not self.stop.is_set():
                        try:
                            self.accept(json.loads(connection.recv(timeout=1)))
                        except TimeoutError:
                            continue
            except Exception:
                # No exception text: handshake failures can contain HTTP headers.
                pass
            finally:
                self.connection = None
                self.disconnected()
            self.stop.wait(5)

    def revision(self):
        if self.thread is None:
            self.thread = threading.Thread(target=self.run, daemon=True, name='propr-marks')
            self.thread.start()
        if not self.ready.wait(10):
            raise ValueError('Propr live mark stream is not connected')
        with self.lock:
            if not self.connected:
                raise ValueError('Propr live mark stream disconnected')
            return self.generation

    def equity(self, account, positions, revision):
        with self.lock:
            self.check_revision(revision)
            equity = D(str(account['balance'])) + D(str(account['isolatedPositionMargin']))
            if not equity.is_finite():
                raise ValueError('Invalid realized account value')
            for p in positions:
                mark, quantity, entry, side = self.position_values(p)
                equity += quantity * (mark - entry) * (1 if side == 'long' else -1)
            return equity

    def check_revision(self, revision):
        if not self.connected or revision != self.generation:
            raise ValueError('Account changed during risk read; retry with fresh state')

    def position_values(self, position):
        # Caller holds self.lock across the entire portfolio calculation.
        if (position.get('accountId') != self.account_id or position.get('exchange') != 'hyperliquid'
                or position.get('productType') != 'perp'):
            raise ValueError('Unexpected position in live equity calculation')
        mark = self.marks.get(position['asset'])
        if not mark or not -2 <= self.clock() - mark[1] <= 10:
            raise ValueError('Missing or stale Propr mark for an open position')
        quantity, entry = D(str(position['quantity'])), D(str(position['entryPrice']))
        if not quantity.is_finite() or not entry.is_finite() or quantity < 0 or entry <= 0:
            raise ValueError('Invalid position numeric value')
        side = position['positionSide']
        if side not in ('long', 'short'):
            raise ValueError('Invalid position side')
        return mark[0], quantity, entry, side

    def gross(self, positions, revision):
        with self.lock:
            self.check_revision(revision)
            values = [self.position_values(p) for p in positions]
            return sum((mark * quantity for mark, quantity, _, _ in values), D(0))

    def close(self):
        self.stop.set()
        connection = self.connection
        if connection is not None:
            connection.close()
        if self.thread is not None:
            self.thread.join(timeout=12)
        self.disconnected()

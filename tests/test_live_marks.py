"""Synthetic streams only: no Propr credentials or order writes."""
from decimal import Decimal as D
import json
import tempfile
import threading
import time
from pathlib import Path
import unittest
from unittest.mock import patch
from propfirm.live_marks import LiveMarks, connect_no_redirects
from propfirm.engine import Engine
from test_account_adapter import documents, mapped_config
from test_execution import NOW, FakeData


def position(**extra):
    return {'accountId': 'a', 'exchange': 'hyperliquid', 'productType': 'perp',
            'asset': 'BTC', 'quantity': '2', 'entryPrice': '100', 'positionSide': 'long', **extra}


class MarkTests(unittest.TestCase):
    def setUp(self):
        self.now = NOW.timestamp()
        self.feed = LiveMarks('fake-key', 'a', clock=lambda: self.now)
        self.feed.accept({'type': 'connected'})
        self.feed.accept({'type': 'mark.updated', 'data': {
            'timestamp': self.now * 1000, 'marks': {'hyperliquid': {'BTC': '105'}}}})
        self.account = {'balance': '4900', 'isolatedPositionMargin': '100',
                        'totalUnrealizedPnl': '999999'}

    def test_equity_uses_live_marks_and_isolated_margin_not_stale_rest_pnl(self):
        self.assertEqual(self.feed.equity(self.account, [position()], 0), D('5010'))
        self.assertEqual(self.feed.equity(self.account, [position(positionSide='short')], 0), D('4990'))
        self.assertEqual(self.feed.equity(self.account, [], 0), D('5000'))

    def test_exposure_uses_live_marks_and_fails_after_account_change(self):
        positions = [position(notionalValue='1'), position(positionSide='short', notionalValue='1')]
        self.assertEqual(self.feed.gross(positions, 0), 420)
        self.feed.accept({'type': 'trade.created', 'data': {'accountId': 'a'}})
        with self.assertRaises(ValueError): self.feed.gross(positions, 0)

    def test_stale_missing_invalid_positions_and_marks_fail(self):
        for changes in ({'accountId': 'b'}, {'exchange': 'other'}, {'productType': 'spot'},
                        {'asset': 'NO_MARK'}, {'quantity': '-1'}, {'quantity': 'NaN'},
                        {'entryPrice': 'Infinity'}, {'positionSide': 'unknown'}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                self.feed.equity(self.account, [position(**changes)], 0)
        for price in ('0', '-1', 'NaN', 'Infinity'):
            with self.subTest(price=price), self.assertRaises(ValueError):
                self.feed.accept({'type': 'mark.updated', 'data': {
                    'timestamp': self.now * 1000, 'marks': {'hyperliquid': {'BTC': price}}}})
        self.now += 11
        with self.assertRaises(ValueError): self.feed.equity(self.account, [position()], 0)
        with self.assertRaises(ValueError):
            self.feed.accept({'type': 'mark.updated', 'data': {'timestamp': (self.now-11)*1000}})

    def test_concurrent_account_changes_and_reconnect_invalidate_snapshot(self):
        self.feed.accept({'type': 'account.updated', 'data': {'accountId': 'b'}})
        self.assertEqual(self.feed.equity(self.account, [position()], 0), 5010)
        self.feed.accept({'type': 'position.updated', 'data': {'accountId': 'a'}})
        with self.assertRaises(ValueError): self.feed.equity(self.account, [position()], 0)
        self.assertEqual(self.feed.equity(self.account, [position()], 1), 5010)
        self.feed.disconnected()
        with self.assertRaises(ValueError): self.feed.equity(self.account, [], 2)
        self.feed.accept({'type': 'connected'})
        with self.assertRaises(ValueError): self.feed.equity(self.account, [position()], 2)

    def test_engine_replaces_rest_equity_with_live_equity(self):
        docs = documents(); cfg = mapped_config(docs)
        class Client:
            api_key = 'fake-key'; account_id = 'a'
            def positions(self): return [position()]
        with tempfile.TemporaryDirectory() as directory:
            engine = Engine(Client(), FakeData(), cfg, Path(directory), clock=lambda: NOW)
            engine.live_marks = self.feed
            with patch.object(self.feed, 'revision', return_value=0), \
                 patch('propfirm.engine.select_documents', return_value=docs) as read:
                result = engine.account()
                self.assertEqual(result.equity, 5210)
                self.assertEqual(result.day_start_balance, 5050)
                read.assert_called_once_with(engine.client, include_daily=True)
            engine.store.close()

    def test_real_socket_handshake_read_and_shutdown_with_synthetic_key(self):
        from websockets.sync.server import serve
        received = []
        finished = threading.Event()
        def handler(connection):
            received.append(connection.request.headers.get('X-API-Key'))
            connection.send(json.dumps({'type': 'connected'}))
            connection.send(json.dumps({'type': 'mark.updated', 'data': {
                'timestamp': int(time.time()*1000), 'marks': {'hyperliquid': {'BTC': '105'}}}}))
            try:
                connection.recv(timeout=5)
            except Exception:
                pass
            finished.set()
        with serve(handler, '127.0.0.1', 0) as server:
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            port = server.socket.getsockname()[1]
            def local_connector(uri, **kwargs):
                self.assertEqual(uri, 'wss://api.propr.xyz/ws')
                return connect_no_redirects(f'ws://127.0.0.1:{port}', proxy=None, **kwargs)
            feed = LiveMarks('synthetic-only', 'a', connector=local_connector)
            try:
                revision = feed.revision()
                deadline = time.monotonic()+3
                while 'BTC' not in feed.marks and time.monotonic() < deadline:
                    time.sleep(.01)
                self.assertEqual(feed.equity(self.account, [position()], revision), 5010)
            finally:
                feed.close()
                server.shutdown()
                thread.join(3)
            self.assertEqual(received, ['synthetic-only'])
            self.assertTrue(finished.wait(1))
            self.assertFalse(feed.thread.is_alive())
            self.assertFalse(feed.connected)

    def test_redirect_is_rejected_without_forwarding_credentials(self):
        from websockets.sync.server import serve
        from websockets.exceptions import InvalidStatus
        count = []
        def reject(connection, request):
            count.append(request.path)
            response = connection.respond(302, 'Redirect')
            response.headers['Location'] = '/other'
            return response
        with serve(lambda c: None, '127.0.0.1', 0, process_request=reject) as server:
            thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
            port = server.socket.getsockname()[1]
            try:
                with self.assertRaises(InvalidStatus):
                    with connect_no_redirects(f'ws://127.0.0.1:{port}/initial', proxy=None,
                                              additional_headers={'X-API-Key': 'synthetic-only'}):
                        pass
            finally:
                server.shutdown(); thread.join(3)
            self.assertEqual(count, ['/initial'])

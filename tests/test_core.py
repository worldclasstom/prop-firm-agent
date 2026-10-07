import contextlib
from datetime import datetime, timedelta, timezone
from decimal import Decimal as D
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from propfirm.strategy import Bar, atr, entry, exit_signal, quantity, stop_price
from propfirm.risk import RiskState, evaluate
from propfirm.state import Store
from propfirm.propr import DEFAULT_BUILDER_CODE, NoRedirects, read_request
from propfirm.__main__ import main


def bar(high='101', low='99', close='100'):
    return Bar(D(high), D(low), D(close))


class StrategyTests(unittest.TestCase):
    def test_signal_uses_previous_twenty_not_current_high(self):
        self.assertEqual(entry([bar()] * 59 + [bar('150', '99', '102')]), 'long')

    def test_short_breakout(self):
        self.assertEqual(entry([bar()] * 59 + [bar('101', '50', '98')]), 'short')

    def test_equal_boundary_is_not_breakout(self):
        self.assertIsNone(entry([bar()] * 59 + [bar(close='101')]))
        self.assertIsNone(entry([bar()] * 59 + [bar(close='99')]))

    def test_insufficient_history_rejected(self):
        with self.assertRaises(ValueError):
            entry([bar()] * 59)

    def test_wilder_recurrence_and_gap(self):
        # Seed 20 ranges of 2, followed by gap TR 11. (19*2+11)/20=2.45.
        self.assertEqual(atr([bar()] * 21), D(2))
        self.assertEqual(atr([bar()] * 21 + [bar('111', '109', '110')]), D('2.45'))

    def test_exit_ignores_signal_bar_extreme(self):
        self.assertTrue(exit_signal([bar()] * 10 + [bar('101', '50', '98')], 'long'))
        self.assertTrue(exit_signal([bar()] * 10 + [bar('150', '99', '102')], 'short'))
        self.assertFalse(exit_signal([bar()] * 10 + [bar(close='99')], 'long'))

    def test_contract_multiplier_and_rounding(self):
        self.assertEqual(quantity(D(25000), D(25000), D(0), D(100), D(3), D(10), D('.1'), D('.1')), D('1.6'))

    def test_exposure_cap_and_minimum(self):
        self.assertEqual(quantity(D(25000), D(25000), D(49950), D(100), D(1), D(1), D('.1'), D('.1')), D('.5'))
        self.assertEqual(quantity(D(25000), D(25000), D(50000), D(100), D(1), D(1), D('.1'), D('.1')), D(0))
        self.assertEqual(quantity(D(25000), D(25000), D(49999), D(100), D(1), D(1), D('.1'), D('.1')), D(0))

    def test_stop_rounding_does_not_widen_risk(self):
        self.assertEqual(stop_price(D(100), D('1.13'), D('.1'), 'long'), D('97.8'))
        self.assertEqual(stop_price(D(100), D('1.13'), D('.1'), 'short'), D('102.2'))

    def test_invalid_stop_rejected(self):
        for side in ('long', 'short'):
            with self.assertRaises(ValueError):
                stop_price(D(100), D('.01'), D(1), side)

    def test_invalid_prices_rejected(self):
        for value in ('NaN', 'Infinity', '-1', '0'):
            with self.assertRaises(ValueError):
                Bar(D(value), D(99), D(100))


class RiskTests(unittest.TestCase):
    now = datetime(2026, 10, 7, 0, 10, tzinfo=timezone.utc)

    def run_risk(self, state=RiskState(), **changes):
        args = dict(starting_balance=D(25000), day_start_balance=D(25000), equity=D(25000),
                    now=self.now, snapshot_at=self.now, monitor_healthy=True)
        args.update(changes)
        return evaluate(state, **args)

    def test_daily_threshold_counts_equity(self):
        self.assertTrue(self.run_risk(equity=D('24500.01')).entries_allowed)
        decision = self.run_risk(equity=D(24500))
        self.assertFalse(decision.entries_allowed)
        self.assertTrue(decision.cancel_entries)
        self.assertFalse(decision.flatten_required)

    def test_recovery_does_not_unlatch_same_day(self):
        state = self.run_risk(equity=D(24500)).state
        self.assertFalse(self.run_risk(state, daily_scan=True).entries_allowed)

    def test_next_day_requires_scheduled_scan(self):
        state = RiskState('2026-10-06')
        self.assertFalse(self.run_risk(state).entries_allowed)
        early = self.now.replace(minute=9)
        self.assertFalse(self.run_risk(state, now=early, snapshot_at=early, daily_scan=True).entries_allowed)
        self.assertTrue(self.run_risk(state, daily_scan=True).entries_allowed)

    def test_current_loss_rehalts_after_reset(self):
        self.assertFalse(self.run_risk(RiskState('2026-10-06'), equity=D(24500), daily_scan=True).entries_allowed)

    def test_static_kill_boundary_and_persistence(self):
        result = self.run_risk(equity=D(23875))
        self.assertTrue(result.flatten_required)
        self.assertTrue(self.run_risk(result.state, monitor_healthy=False).flatten_required)
        self.assertFalse(self.run_risk(result.state).entries_allowed)

    def test_negative_equity_triggers_kill(self):
        self.assertTrue(self.run_risk(equity=D(-1)).flatten_required)

    def test_stale_and_future_snapshots_block(self):
        for age in (31, -1):
            self.assertFalse(self.run_risk(snapshot_at=self.now-timedelta(seconds=age)).entries_allowed)
        self.assertFalse(self.run_risk(monitor_healthy=False).entries_allowed)

    def test_utc_reset_not_local_date(self):
        local = self.now.astimezone(timezone(timedelta(hours=-5)))
        self.assertEqual(self.run_risk(now=local, snapshot_at=local, equity=D(24500)).state.daily_halt_date, '2026-10-07')


class StoreTests(unittest.TestCase):
    def test_retry_survives_restart_and_keeps_exact_payload(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'state.db'
            first = Store(path)
            order = first.reserve('trial:xyz:GOLD:2026-10-07:entry', {'quantity': '1', 'asset': 'xyz:GOLD'})
            first.latch_kill('drawdown')
            first.close()
            second = Store(path)
            self.assertEqual(order, second.reserve('trial:xyz:GOLD:2026-10-07:entry', {'asset': 'xyz:GOLD', 'quantity': '1'}))
            self.assertEqual(second.kill_reason(), 'drawdown')
            self.assertRegex(order[0], r'^[0-7][0-9A-HJKMNP-TV-Z]{25}$')
            with self.assertRaises(ValueError):
                second.reserve('trial:xyz:GOLD:2026-10-07:entry', {'quantity': '2'})
            second.close()

    def test_two_connections_share_reservation(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'state.db'
            a, b = Store(path), Store(path)
            self.assertEqual(a.reserve('same', {'quantity': '1'}), b.reserve('same', {'quantity': '1'}))
            a.close()
            b.close()


class AttributionTests(unittest.TestCase):
    def test_default_override_and_opt_out(self):
        self.assertEqual(read_request('/v1/users/me', 'test-key').get_header('X-builder-code'), DEFAULT_BUILDER_CODE)
        self.assertEqual(read_request('/v1/users/me', 'test-key', 'custom').get_header('X-builder-code'), 'custom')
        req = read_request('/v1/users/me', 'test-key', '')
        self.assertFalse(req.has_header('X-builder-code'))
        self.assertEqual(req.get_header('X-api-key'), 'test-key')

    def test_other_origins_rejected(self):
        for path in ('https://api.hyperliquid.xyz/info', '//evil.example/v1/users/me', '/v1/../users', '/v1/users\n'):
            with self.assertRaises(ValueError):
                read_request(path, 'test-key')

    def test_header_injection_rejected(self):
        with self.assertRaises(ValueError):
            read_request('/v1/users/me', 'test-key', 'code\r\nX-other: value')

    def test_redirect_not_followed(self):
        self.assertIsNone(NoRedirects().redirect_request(None, None, 302, '', {}, 'https://example.com'))


class SetupTests(unittest.TestCase):
    def test_init_preserves_config_and_private_permissions(self):
        with tempfile.TemporaryDirectory() as folder:
            args = ['propfirm', 'init', '--directory', folder]
            with patch.object(sys, 'argv', args), contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(main(), 0)
            path = Path(folder)/'config.json'
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            path.write_text('{"custom": true}')
            with patch.object(sys, 'argv', args), contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(main(), 0)
            self.assertEqual(json.loads(path.read_text()), {'custom': True})

    def test_doctor_does_not_claim_runtime_verified(self):
        result = subprocess.run([sys.executable, '-m', 'propfirm', 'doctor'], capture_output=True, text=True, check=True)
        data = json.loads(result.stdout)
        self.assertFalse(data['trading_available'])
        self.assertEqual(set(data['runtime'].values()), {'unverified'})

    def test_start_fails_clearly(self):
        result = subprocess.run([sys.executable, '-m', 'propfirm', 'start'], capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)
        self.assertIn('unavailable', result.stderr)


if __name__ == '__main__':
    unittest.main()

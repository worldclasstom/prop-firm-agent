import copy
from decimal import Decimal as D
from pathlib import Path
import tempfile
import unittest

from propfirm.backtest import simulate
from propfirm.config import validate
from propfirm.engine import Engine
from propfirm.propr import APIError
from test_execution import config, FakeClient, FakeData, NOW, MARKET


def trial_config():
    cfg = config()
    cfg['account_mode'] = 'trial'
    cfg['order_limits_policy'] = 'trial_broker_validation'
    cfg['markets'][0].update(minimum_quantity=None, minimum_notional=None,
                            limits_evidence='Synthetic fixture: not published; no claim of zero minimum')
    return cfg


class OrderLimitTests(unittest.TestCase):
    def engine(self, cfg=None, client=None, data=None):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        client = client or FakeClient()
        engine = Engine(client, data or FakeData(), cfg or trial_config(), Path(temp.name),
                        sleeper=lambda _: None, clock=lambda: NOW)
        self.addCleanup(engine.store.close)
        return engine, client

    def test_unknown_needs_explicit_trial_policy_and_evidence(self):
        cfg = trial_config()
        validate(cfg)
        for field in ('order_limits_policy', 'limits_evidence'):
            bad = copy.deepcopy(cfg)
            (bad if field == 'order_limits_policy' else bad['markets'][0]).pop(field)
            with self.assertRaises(ValueError): validate(bad)

    def test_missing_values_are_not_silently_converted_to_unknown(self):
        cfg = trial_config(); cfg['markets'][0].pop('minimum_notional')
        with self.assertRaises(KeyError): validate(cfg)
        for value in ('0', '-1', 'NaN', 'Infinity'):
            cfg = trial_config(); cfg['markets'][0]['minimum_notional'] = value
            with self.assertRaises(ValueError): validate(cfg)

    def test_paid_mode_runs_broker_validation_too_and_only_verified_insists_on_known_minima(self):
        # Release 0.2.0b11 (operator, 2026-10-09): the same safeguards on a paid account.
        cfg = trial_config(); cfg['account_mode'] = 'paid'
        validate(cfg)
        cfg['order_limits_policy'] = 'broker_validation'
        validate(cfg)
        self.engine(cfg)
        cfg['order_limits_policy'] = 'verified'
        with self.assertRaises(ValueError): validate(cfg)
        cfg['order_limits_policy'] = 'something_else'
        with self.assertRaises(ValueError): validate(cfg)

    def test_unknown_limits_do_not_bypass_stop_or_precision_checks(self):
        for key, value in (('stop_supported', False), ('quantity_step', '.03')):
            cfg = trial_config(); cfg['markets'][0][key] = value
            with self.assertRaises(ValueError): validate(cfg)

    def test_same_risk_sized_order_and_stop_as_known_limits(self):
        known, kc = self.engine(config()); unknown, uc = self.engine()
        known.scan(); unknown.scan()
        for a, b in zip(kc.sent, uc.sent):
            self.assertEqual({k: v for k, v in a.items() if k != 'intentId'},
                             {k: v for k, v in b.items() if k != 'intentId'})
        self.assertEqual(len(uc.sent), 2)
        self.assertIsNone(unknown.config['markets'][0]['minimum_quantity'])

    def test_known_minimum_still_skips_without_upsizing(self):
        for name in ('minimum_quantity', 'minimum_notional'):
            cfg = trial_config(); cfg['markets'][0][name] = '1000000'
            engine, client = self.engine(cfg); engine.scan()
            self.assertEqual(client.sent, [])

    def test_http_rejection_blocks_entries_without_retry_or_larger_size(self):
        class Reject(FakeClient):
            def submit(self, payload):
                self.sent.append(copy.deepcopy(payload)); raise APIError(422)
        engine, client = self.engine(client=Reject())
        with self.assertRaises(ValueError): engine.scan()
        self.assertEqual(engine.store.get('entry_block'), 'order_request_rejected')
        engine.recover(); engine.scan()
        key, saved = engine.store.all_intents()[0]
        with self.assertRaises(ValueError): engine.send(key, saved)
        self.assertEqual(len(client.sent), 1)
        self.assertEqual(client.position_rows, [])

    def test_order_status_rejection_blocks_entries(self):
        class Reject(FakeClient):
            def submit(self, payload):
                self.sent.append(copy.deepcopy(payload))
                order = {**payload, 'orderId': 'rejected-1', 'status': 'rejected', 'cumulativeQuantity': '0'}
                self.order_rows.append(order)
                return {'data': [order]}
        engine, client = self.engine(client=Reject()); engine.scan(); engine.scan()
        self.assertEqual(engine.store.get('entry_block'), 'order_request_rejected')
        self.assertEqual(len(client.sent), 1)

    def test_partial_fill_gets_actual_size_stop(self):
        engine, client = self.engine(); client.partial = True; engine.scan()
        self.assertEqual(D(client.sent[1]['quantity']), D(client.sent[0]['quantity']) / 2)
        self.assertTrue(client.sent[1]['reduceOnly'])

    def test_rejected_stop_still_latches_shutdown_and_flattens(self):
        engine, client = self.engine(); client.reject_stop = True; engine.scan()
        self.assertEqual(engine.store.kill_reason(), 'protection_failure')
        self.assertEqual(client.positions(), [])
        self.assertTrue(client.sent[-1]['closePosition'])

    def test_no_signal_does_not_send_probe_orders(self):
        class NoSignal(FakeData):
            def candles(self, market):
                rows = super().candles(market); rows[-1].update(h='101', c='100'); return rows
        engine, client = self.engine(data=NoSignal()); engine.scan()
        self.assertEqual(client.sent, [])

    def test_backtest_discloses_unknown_order_eligibility(self):
        market = trial_config()['markets'][0]
        result = simulate({market['asset']: FakeData().candles(market)}, {market['asset']: market})
        self.assertEqual(result['unverified_order_minimums'][market['asset']],
                         ['minimum_quantity', 'minimum_notional'])
        self.assertIn('may be rejected', result['order_eligibility_limitation'])


if __name__ == '__main__':
    unittest.main()

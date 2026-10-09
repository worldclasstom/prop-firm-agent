"""Any Propr product with a static drawdown: the engine reads its limits and keeps its own inside them."""
import unittest
from datetime import timedelta
from decimal import Decimal as D

from propfirm.account import CLASSIC_RULES, challenge_rules, propr_mapping, snapshot
from propfirm.config import validate
from propfirm.risk import RiskState, evaluate, inner_limits
from propfirm.strategy import quantity, risk_fraction
from test_account_adapter import documents, mapped_config
from test_execution import NOW

TURBO = {'maxDailyLossPercent': '3', 'maxDrawdownPercent': '3', 'profitTargetPercent': '9'}
PRO = {'maxDailyLossPercent': '3', 'maxDrawdownPercent': '5', 'profitTargetPercent': '12'}


def product_documents(rules):
    docs = documents()
    docs['challenge'].update(name='Gold 1-Step Turbo', slug='gold-1-step-turbo')
    docs['challenge']['product']['prices'][0]['price'] = '450'
    docs['challenge']['phases'][1].update(rules)
    return docs


def pinned(rules):
    return {'daily_loss_fraction': str(D(rules['maxDailyLossPercent']) / 100),
            'max_drawdown_fraction': str(D(rules['maxDrawdownPercent']) / 100),
            'profit_target_fraction': str(D(rules['profitTargetPercent']) / 100), 'drawdown_type': 'static'}


class ChallengeRulesTests(unittest.TestCase):
    def test_inner_limits_scale_with_the_product(self):
        self.assertEqual(inner_limits(), (D('.02'), D('.045')))
        self.assertEqual(inner_limits(D('.03'), D('.03')), (D('.02'), D('.0225')))
        self.assertEqual(inner_limits(D('.03'), D('.05')), (D('.02'), D('.0375')))
        self.assertEqual(risk_fraction(D('.06')), D('.004'))
        self.assertEqual(risk_fraction(D('.03')), D('.002'))
        with self.assertRaises(ValueError):
            inner_limits(D('1'), D('.06'))

    def test_a_turbo_product_maps_and_snapshots_with_its_own_fractions(self):
        docs = product_documents(TURBO)
        mapping = propr_mapping(docs, 'a')
        self.assertEqual(mapping['max_drawdown_fraction']['scale'], '0.01')
        cfg = mapped_config(docs)
        cfg.update(account_mode='paid', challenge_rules=pinned(TURBO))
        snap = snapshot(docs, cfg, NOW)
        self.assertEqual((snap.daily_loss_fraction, snap.max_drawdown_fraction, snap.profit_target_fraction),
                         (D('.03'), D('.03'), D('.09')))
        self.assertEqual(snap.equity, 5175)
        # The same documents refused by a configuration verified for Classic, and by stale pins.
        with self.assertRaises(ValueError):
            snapshot(docs, {**cfg, 'challenge_rules': None}, NOW)
        with self.assertRaises(ValueError):
            snapshot(docs, {**cfg, 'challenge_rules': pinned(PRO)}, NOW)
        # Classic documents under a Classic configuration keep the defaults.
        classic = documents()
        self.assertEqual(snapshot(classic, mapped_config(classic), NOW).max_drawdown_fraction, D('.06'))

    def test_pinned_rules_are_checked_for_shape(self):
        self.assertEqual(challenge_rules({}), CLASSIC_RULES)
        self.assertEqual(challenge_rules({'challenge_rules': pinned(TURBO)})['max_drawdown_fraction'], D('.03'))
        for bad in ({'daily_loss_fraction': '0.03'}, {**pinned(TURBO), 'max_drawdown_fraction': '1'},
                    {**pinned(TURBO), 'max_drawdown_fraction': 'NaN'}, {**pinned(TURBO), 'drawdown_type': 'trailing'},
                    'classic'):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                challenge_rules({'challenge_rules': bad})
        docs = product_documents(TURBO)
        cfg = mapped_config(docs)
        cfg.update(challenge_rules={**pinned(TURBO), 'drawdown_type': 'trailing'})
        with self.assertRaises(ValueError):
            validate(cfg)

    def test_risk_halts_at_the_product_fractions(self):
        base = dict(starting_balance=D('5000'), day_start_balance=D('5000'), now=NOW, snapshot_at=NOW,
                    monitor_healthy=True, daily_loss_fraction=D('.03'), max_drawdown_fraction=D('.03'))
        self.assertEqual(evaluate(RiskState(), equity=D('4910'), **base).reason, 'within_limits')
        self.assertEqual(evaluate(RiskState(), equity=D('4900'), **base).reason, 'daily_halt')
        self.assertEqual(evaluate(RiskState(), equity=D('4887.50'), **base).reason, 'kill_latched')
        classic = {**base, 'max_drawdown_fraction': D('.06')}
        self.assertEqual(evaluate(RiskState(), equity=D('4887.50'), **classic).reason, 'daily_halt')
        self.assertEqual(evaluate(RiskState(), equity=D('4775'), **classic).reason, 'kill_latched')

    def test_position_risk_scales_with_the_drawdown(self):
        args = (D('5000'), D('5000'), D('0'), D('100'), D('2'), D('1'), D('0.01'), D('0.01'))
        self.assertEqual(quantity(*args), D('5.00'))
        self.assertEqual(quantity(*args, risk=risk_fraction(D('.03'))), D('2.50'))


if __name__ == '__main__':
    unittest.main()

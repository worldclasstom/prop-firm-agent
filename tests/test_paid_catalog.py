"""A paid Classic challenge is proved from the catalog the way the free trial is: by evidence, never by name."""
import copy
import unittest

from propfirm.account import catalog_paid, catalog_trial, inspection_report, snapshot
from test_account_adapter import documents, mapped_config
from test_execution import NOW


def paid_documents():
    docs = documents()
    docs['challenge'].update(name='Bronze Classic', slug='bronze-classic')
    docs['challenge']['product']['prices'][0]['price'] = '49'
    return docs


class PaidCatalogTests(unittest.TestCase):
    def test_a_priced_classic_challenge_is_paid_and_not_the_trial(self):
        docs = paid_documents()
        self.assertTrue(catalog_paid(docs, 'a'))
        with self.assertRaises(ValueError):
            catalog_trial(docs, 'a')
        report = inspection_report(docs, 'a')
        self.assertTrue(report['paid_catalog_verified'])
        self.assertFalse(report['trial_catalog_verified'])
        self.assertEqual(set(report['missing_fields']), {'daily_metrics_binding'})
        trial = inspection_report(documents(), 'a')
        self.assertTrue(trial['trial_catalog_verified'])
        self.assertFalse(trial['paid_catalog_verified'])

    def test_paid_proof_rejects_the_trial_broken_identity_and_bad_rules(self):
        for mutate in (
            lambda d: d['challenge'].update(slug='free-trial'),
            lambda d: d['challenge'].update(slug=''),
            lambda d: d['challenge'].pop('slug'),
            lambda d: d['challenge']['product'].update(productId='other'),
            lambda d: d['challenge']['product'].update(deletedAt='2026-01-01'),
            lambda d: d['challenge'].update(productId=None),
            lambda d: d['challenge']['phases'][1].update(maxDailyLossPercent='0'),
            lambda d: d['challenge']['phases'][1].update(drawdownType='trailing'),
        ):
            docs = paid_documents()
            mutate(docs)
            with self.subTest(documents=docs), self.assertRaises((ValueError, KeyError, TypeError)):
                catalog_paid(docs, 'a')

    def test_a_challenge_propr_gave_away_is_still_a_paid_product(self):
        # The attempt's own fee is not in the catalog; a zero or missing price list changes nothing.
        for mutate in (
            lambda d: d['challenge']['product']['prices'][0].update(price='0'),
            lambda d: d['challenge']['product'].update(prices=[]),
            lambda d: d['challenge']['product'].pop('prices'),
        ):
            docs = paid_documents()
            mutate(docs)
            with self.subTest(documents=docs):
                self.assertTrue(catalog_paid(docs, 'a'))

    def test_snapshot_in_paid_mode_needs_the_paid_proof_and_trial_mode_the_trial_proof(self):
        docs = paid_documents()
        cfg = mapped_config(docs)
        cfg['account_mode'] = 'paid'
        snap = snapshot(docs, cfg, NOW)
        self.assertEqual((snap.starting_balance, snap.equity, snap.day_start_balance), (5000, 5175, 5050))
        trial_docs = documents()
        trial_cfg = mapped_config(trial_docs)
        with self.assertRaises(ValueError):
            snapshot(copy.deepcopy(trial_docs), {**cfg}, NOW)  # the free trial is not a paid account
        with self.assertRaises(ValueError):
            snapshot(copy.deepcopy(docs), {**trial_cfg, 'account_mode': 'trial'}, NOW)  # nor the reverse
        self.assertEqual(snapshot(trial_docs, trial_cfg, NOW).equity, 5175)


if __name__ == '__main__':
    unittest.main()

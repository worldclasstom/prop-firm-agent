"""Hand-written synthetic fixtures matching the observed Propr response structure."""
import contextlib
import copy
from datetime import timedelta
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from propfirm.account import catalog_trial, daily_reference, inspection_report, propr_mapping, select_documents, snapshot
from propfirm.config import save_json, validate, validate_research
from propfirm.__main__ import main
from propfirm.propr import ReadOnlyClient
from test_execution import config, FakeData, MARKET, NOW


def documents():
    return {
        'account': {'accountId': 'a', 'challengeAttemptId': 't', 'challengeId': 'c',
                    'currency': 'USDC', 'exchange': 'hyperliquid', 'type': 'paper',
                    'balance': '5100', 'totalUnrealizedPnl': '-25', 'isolatedPositionMargin': '100'},
        'attempt': {'attemptId': 't', 'accountId': 'a', 'challengeId': 'c', 'status': 'active',
                    'currentPhaseId': 'ap', 'phases': [
                        {'attemptPhaseId': 'old', 'phaseId': 'old-rules'},
                        {'attemptPhaseId': 'ap', 'attemptId': 't', 'phaseId': 'p',
                         'status': 'active', 'startingBalance': '5000'}]},
        'challenge': {'challengeId': 'c', 'currency': 'USDC', 'exchange': 'hyperliquid',
                      'isActive': True, 'name': 'Free Trial', 'slug': 'free-trial',
                      'productId': 'product', 'product': {'productId': 'product', 'prices': [
                          {'productId': 'product', 'price': '0', 'isActive': True, 'billingPeriod': 'one_time'}]},
                      'phases': [{'phaseId': 'other'}, {'phaseId': 'p', 'challengeId': 'c',
                         'maxDailyLossPercent': '3', 'maxDrawdownPercent': '6',
                         'profitTargetPercent': '10', 'drawdownType': 'static'}]},
    }


def mapped_config(docs):
    # These fields are deliberately synthetic; no nonexistent provider field is claimed.
    cfg = config()
    cfg.update(account_id='a', account_adapter='propr-v1')
    docs['daily_metrics'] = {'fixture_rows': [{'accountId': 'a', 'startingBalance': '4950',
        'startingIsolatedPositionMargin': '100', 'fixture_date': NOW.date().isoformat()}]}
    cfg['account_mapping'] = propr_mapping(docs, 'a')
    cfg['daily_metrics_binding'] = {'rows_path': ['fixture_rows'], 'date_path': ['fixture_date'],
                                    'evidence': 'synthetic envelope/date, documented balance fields'}
    return cfg


class AdapterTests(unittest.TestCase):
    def test_joins_active_phase_and_uses_sdk_equity(self):
        docs = documents(); cfg = mapped_config(docs)
        snap = snapshot(docs, cfg, NOW)
        self.assertEqual(snap.starting_balance, 5000)
        self.assertEqual(snap.equity, 5175)
        self.assertEqual(snap.day_start_balance, 5050)
        # API ordering changes must not bind another phase's rules.
        docs['attempt']['phases'].reverse(); docs['challenge']['phases'].reverse()
        self.assertEqual(snapshot(docs, cfg, NOW), snap)

    def test_report_maps_present_fields_without_inventing_proof_or_day_reference(self):
        report = inspection_report(documents(), 'a')
        self.assertFalse(report['trading_ready'])
        self.assertEqual(set(report['missing_fields']), {'daily_metrics_binding'})
        self.assertFalse(set(report['missing_fields']) & report['account_mapping'].keys())
        self.assertEqual(report['account_mapping']['starting_balance']['path'], ['phases', 1, 'startingBalance'])

    def test_missing_mismatched_and_duplicate_phase_links_fail(self):
        for mutate in (
            lambda d: d['account'].update(challengeAttemptId='wrong'),
            lambda d: d['attempt'].update(currentPhaseId='p'),
            lambda d: d['attempt']['phases'].append(copy.deepcopy(d['attempt']['phases'][1])),
            lambda d: d['challenge']['phases'].append(copy.deepcopy(d['challenge']['phases'][1])),
            lambda d: d['challenge']['phases'][1].update(challengeId='wrong'),
            lambda d: d['attempt']['phases'][1].update(status='passed'),
            lambda d: d['account'].update(closedAt='2026-01-01'),
            lambda d: d['challenge'].update(isActive=False),
            lambda d: d['challenge']['phases'][1].update(maxDailyLossPercent='5'),
            lambda d: d['challenge']['phases'][1].update(drawdownType='trailing'),
        ):
            docs = documents(); mutate(docs)
            with self.subTest(documents=docs), self.assertRaises(ValueError):
                propr_mapping(docs, 'a')

    def test_trial_and_utc_reference_still_required(self):
        docs = documents(); cfg = mapped_config(docs)
        docs['challenge']['product']['prices'][0]['price'] = '10'
        with self.assertRaises(ValueError): snapshot(docs, cfg, NOW)
        docs['challenge']['product']['prices'][0]['price'] = '0'
        with self.assertRaises(ValueError): snapshot(docs, cfg, NOW + timedelta(days=1))
        del cfg['daily_metrics_binding']
        with self.assertRaises(ValueError): snapshot(docs, cfg, NOW)

    def test_catalog_trial_rejects_paid_ambiguous_and_name_only(self):
        for mutate in (
            lambda d: d['account'].update(type='b_book'),
            lambda d: d['challenge'].update(slug='classic'),
            lambda d: d['challenge']['product'].update(productId='other'),
            lambda d: d['challenge']['product'].update(prices=[]),
            lambda d: d['challenge']['product']['prices'][0].update(isActive=False),
            lambda d: d['challenge']['product']['prices'][0].update(price='1'),
            lambda d: d['challenge']['product']['prices'][0].update(price='NaN'),
            lambda d: d['challenge']['product']['prices'].append(
                {'productId': 'product', 'price': '1', 'isActive': True, 'billingPeriod': 'one_time'}),
        ):
            docs = documents(); mutate(docs)
            with self.subTest(documents=docs), self.assertRaises(ValueError):
                catalog_trial(docs, 'a')

    def test_daily_metrics_selects_current_day_and_rejects_bad_reference(self):
        docs = documents(); cfg = mapped_config(docs)
        row = docs['daily_metrics']['fixture_rows'][0]
        yesterday = {**row, 'fixture_date': (NOW-timedelta(days=1)).date().isoformat()}
        docs['daily_metrics']['fixture_rows'].insert(0, yesterday)
        self.assertEqual(daily_reference(docs, cfg, NOW)[0], 5050)
        for extra in ({'accountId': 'other'}, {'fixture_date': '2026-10-07T01:00:00-05:00'},
                      {'fixture_date': '2026-10-06'}, {'startingIsolatedPositionMargin': '-1'},
                      {'startingBalance': 'NaN'}, {'startingBalance': '-1000'}):
            bad = copy.deepcopy(docs); bad['daily_metrics']['fixture_rows'][1].update(extra)
            with self.subTest(extra=extra), self.assertRaises(ValueError):
                daily_reference(bad, cfg, NOW)
        docs['daily_metrics']['fixture_rows'].append(copy.deepcopy(row))
        with self.assertRaises(ValueError): daily_reference(docs, cfg, NOW)

    def test_daily_metrics_transport_is_read_only(self):
        from propfirm.propr import Client
        client = Client('synthetic', 'a')
        with patch.object(client, 'request', return_value={}) as request:
            client.daily_metrics()
        request.assert_called_once_with('GET', '/v1/accounts/a/daily-metrics')

    def test_dated_daily_floor_is_equivalent_and_cannot_be_stale(self):
        from test_execution import FakeClient
        client = FakeClient(); cfg = config()
        docs = {'account': client.account(), 'attempt': client.attempts()[0], 'challenge': {}}
        del cfg['account_mapping']['day_start_balance']
        cfg['account_mapping']['daily_loss_floor'] = {'source': 'account', 'path': ['fixture_floor']}
        docs['account']['fixture_floor'] = '4898.50'
        self.assertEqual(snapshot(docs, cfg, NOW).day_start_balance, 5050)
        with self.assertRaises(ValueError): snapshot(docs, cfg, NOW + timedelta(days=1))
        docs['account']['fixture_floor'] = '-1'
        with self.assertRaises(ValueError): snapshot(docs, cfg, NOW)

    def test_fetches_detailed_attempt_and_rejects_wrong_account(self):
        docs = documents()
        class Client:
            account_id = 'a'
            def attempts(self):
                return [{k: docs['attempt'][k] for k in ('accountId', 'attemptId', 'challengeId')}]
            def attempt(self, identifier):
                self.identifier = identifier
                return docs['attempt']
            def challenges(self): return [docs['challenge']]
            def account(self): return docs['account']
        client = Client()
        self.assertEqual(select_documents(client), docs)
        self.assertEqual(client.identifier, 't')
        docs['account']['accountId'] = 'b'
        with self.assertRaises(ValueError): select_documents(client)

    def test_attempt_detail_transport_is_get_and_encodes_urn(self):
        client = ReadOnlyClient('synthetic')
        with patch.object(client, 'request', return_value={}) as request:
            client.attempt('urn:attempt:test')
        request.assert_called_once_with('GET', '/v1/challenge-attempts/urn%3Aattempt%3Atest')

    def test_inspect_preserves_config_key_approval_and_state(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            for name in ('config.json', '.env', 'approval.json', 'state.sqlite'):
                (root / name).write_text('preserved ' + name)
            with patch.dict(os.environ, {'PROPFIRM_HOME': folder}), \
                    patch('sys.argv', ['propfirm', 'inspect', '--account-id', 'a']), \
                    patch('propfirm.__main__.load_key', return_value='synthetic-secret'), \
                    patch('propfirm.account.select_documents', return_value=documents()), \
                    contextlib.redirect_stdout(io.StringIO()) as output:
                self.assertEqual(main(), 0)
            self.assertNotIn('synthetic-secret', output.getvalue())
            for name in ('config.json', '.env', 'approval.json', 'state.sqlite'):
                self.assertEqual((root / name).read_text(), 'preserved ' + name)
            for name in ('account-mapping.json', 'account-inspection.json'):
                self.assertEqual((root / 'setup' / name).stat().st_mode & 0o777, 0o600)


class ResearchTests(unittest.TestCase):
    def test_research_without_account_cannot_validate_for_trading(self):
        cfg = {'markets': [copy.deepcopy(MARKET)], 'backtest_initial_balance': '5000'}
        cfg['markets'][0].pop('stop_supported')
        validate_research(cfg)
        with self.assertRaises(ValueError): validate(cfg)
        cfg.update(account_id='a', account_mapping={'example': True}, mapping_evidence='example')
        with self.assertRaises(ValueError): validate(cfg)
        cfg['markets'][0]['multiplier'] = 'NaN'
        with self.assertRaises(ValueError): validate_research(cfg)

    def test_backtest_cli_needs_no_credentials_and_preserves_live_config(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'config.json').write_text('preserve live config')
            cfg = {'markets': [copy.deepcopy(MARKET)], 'backtest_initial_balance': '5000'}
            cfg['markets'][0]['stop_supported'] = False
            save_json(root / 'research.json', cfg)
            with patch.dict(os.environ, {'PROPFIRM_HOME': folder}, clear=True), \
                    patch('sys.argv', ['propfirm', 'backtest', '--config', str(root / 'research.json')]), \
                    patch('propfirm.data.Data', return_value=FakeData()), \
                    patch('propfirm.__main__.load_key', side_effect=AssertionError('No broker key needed')), \
                    contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(main(), 0)
            result = json.loads((root / 'reports/backtest.json').read_text())
            self.assertTrue(result['research_only']); self.assertFalse(result['account_verified'])
            self.assertEqual(result['initial_balance_assumption'], '5000')
            self.assertEqual(result['window_denominator'], 0)
            self.assertEqual(result['partial_tail_days'], 5)
            self.assertEqual((root / 'config.json').read_text(), 'preserve live config')
            self.assertFalse((root / 'approval.json').exists())

    def test_research_rejects_invalid_initial_capital(self):
        for initial in ('0', '-1', 'NaN', 'Infinity'):
            with self.subTest(initial=initial), self.assertRaises(ValueError):
                validate_research({'markets': [MARKET], 'backtest_initial_balance': initial})

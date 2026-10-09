"""Scheduled execution model: one idempotent tick per scheduler run (docs/SCHEDULED-EXECUTION.md)."""
from datetime import timedelta
import json
from pathlib import Path
import tempfile
import unittest
from propfirm import __version__
from propfirm.config import digest, save_json, validate, runtime_ready
from propfirm.engine import Engine
from propfirm.scheduled import run_tick, EXIT_OK, EXIT_ERROR, EXIT_HALTED
from propfirm.service import serve
from test_execution import FakeClient, FakeData, NOW, config as base_config


def config():
    value = base_config()
    value.update(execution_model='scheduled', tick_interval_minutes=60)
    return value


def evidence(root, cfg, **overrides):
    value = {'execution_model': 'scheduled', 'config_sha256': digest(cfg), 'checked_at': '2026-10-06T12:00:00+00:00',
             'scheduled_interval_minutes': 60,
             'scheduler': {'verified': True, 'observation': 'synthetic'},
             'network_access': {'verified': True, 'observation': 'synthetic'},
             'persistent_state': {'verified': True, 'observation': 'synthetic'},
             'private_secrets': {'verified': True, 'observation': 'synthetic'}}
    value.update(overrides)
    save_json(root / 'runtime.json', value)


class ScheduledTickTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.root = Path(self.temp.name)
        self.now = NOW; self.client = FakeClient(); self.cfg = config()
        self.engine = Engine(self.client, FakeData(), self.cfg, self.root, sleeper=lambda _: None, clock=lambda: self.now)
        save_json(self.root / 'approval.json', {'config_sha256': digest(self.cfg), 'version': __version__,
                  'account_mode': 'trial', 'trading_authorized': True})
        evidence(self.root, self.cfg)

    def tearDown(self):
        self.engine.store.close(); self.temp.cleanup()

    def status(self):
        return json.loads((self.root / 'status.json').read_text())

    def test_first_tick_scans_enters_protects_and_reports(self):
        self.assertEqual(run_tick(self.engine), EXIT_OK)
        entry, stop = self.client.sent
        self.assertFalse(entry['reduceOnly']); self.assertEqual(stop['type'], 'stop_market'); self.assertTrue(stop['reduceOnly'])
        status = self.status()
        self.assertEqual(status['execution_model'], 'scheduled'); self.assertTrue(status['scanned'])
        self.assertEqual(status['scheduled_date'], '2026-10-07'); self.assertIsNone(status['kill'])
        self.assertTrue((self.root / 'reports/2026-10-07.md').exists())
        self.assertEqual(self.engine.store.get('last_tick'), NOW.isoformat())

    def test_repeated_ticks_same_day_are_idempotent(self):
        run_tick(self.engine); sent = len(self.client.sent)
        self.now = NOW + timedelta(minutes=60)
        self.assertEqual(run_tick(self.engine), EXIT_OK)
        self.assertEqual(len(self.client.sent), sent); self.assertFalse(self.status()['scanned'])
        self.assertEqual(len(self.client.positions()), 1)
        stops = [o for o in self.client.orders() if o['type'] == 'stop_market' and o['status'] == 'open']
        self.assertEqual(len(stops), 1)

    def test_scan_waits_for_0010_utc_on_a_new_date(self):
        run_tick(self.engine)
        self.now = NOW.replace(day=8, hour=0, minute=5)
        run_tick(self.engine)
        self.assertEqual(self.status()['scheduled_date'], '2026-10-07'); self.assertFalse(self.status()['scanned'])

    def test_fresh_process_resumes_from_state_without_duplicates(self):
        run_tick(self.engine); sent = len(self.client.sent); self.engine.store.close()
        self.engine = Engine(self.client, FakeData(), self.cfg, self.root, sleeper=lambda _: None, clock=lambda: self.now)
        self.assertEqual(run_tick(self.engine), EXIT_OK); self.assertEqual(len(self.client.sent), sent)

    def test_stop_request_flattens_and_reports_halt(self):
        run_tick(self.engine); (self.root / 'STOP').touch()
        self.assertEqual(run_tick(self.engine), EXIT_HALTED)
        self.assertFalse(self.client.positions()); status = self.status()
        self.assertEqual(status['kill'], 'operator_stop'); self.assertTrue(status['shutdown_complete'])
        self.assertTrue((self.root / 'reports/HALT.md').exists())

    def test_static_loss_between_ticks_shuts_down_on_next_tick(self):
        run_tick(self.engine); self.client.equity = 23875
        self.assertEqual(run_tick(self.engine), EXIT_HALTED)
        self.assertFalse(self.client.positions()); self.assertEqual(self.engine.store.kill_reason(), 'kill_latched')

    def test_missed_runs_are_disclosed_not_hidden(self):
        run_tick(self.engine); self.now = NOW + timedelta(hours=5)
        run_tick(self.engine)
        self.assertEqual(self.status()['gap_minutes'], 300.0)
        events = [json.loads(l)['event'] for l in (self.root / 'reports/2026-10-07.jsonl').read_text().splitlines()]
        self.assertIn('schedule_gap', events)

    def test_read_failure_reports_error_without_entries(self):
        self.engine.account = lambda: (_ for _ in ()).throw(ValueError('synthetic read failure'))
        self.assertEqual(run_tick(self.engine), EXIT_ERROR)
        self.assertFalse(self.client.sent); self.assertEqual(self.status()['error'], 'ValueError')

    def test_tick_refuses_continuous_configuration_and_start_refuses_scheduled(self):
        continuous = base_config()
        other = Engine(self.client, FakeData(), continuous, self.root / 'other', sleeper=lambda _: None, clock=lambda: self.now)
        try:
            with self.assertRaises(ValueError): run_tick(other)
        finally:
            other.store.close()
        with self.assertRaises(ValueError): serve(self.engine)
        self.assertFalse(self.client.sent)

    def test_approval_and_evidence_are_required(self):
        save_json(self.root / 'approval.json', {'config_sha256': 'other', 'version': __version__, 'account_mode': 'trial', 'trading_authorized': True})
        with self.assertRaises(ValueError): run_tick(self.engine)
        save_json(self.root / 'approval.json', {'config_sha256': digest(self.cfg), 'version': __version__, 'account_mode': 'trial', 'trading_authorized': True})
        evidence(self.root, self.cfg, scheduled_interval_minutes=30)
        with self.assertRaises(ValueError): run_tick(self.engine)
        evidence(self.root, self.cfg, scheduler={'verified': False, 'observation': ''})
        with self.assertRaises(ValueError): run_tick(self.engine)
        self.assertFalse(self.client.sent)

    def test_expired_evidence_with_exposure_recovers_only_to_flat(self):
        run_tick(self.engine); evidence(self.root, self.cfg, config_sha256='changed')
        entries = len([o for o in self.client.sent if not o['reduceOnly']])
        self.assertEqual(run_tick(self.engine), EXIT_HALTED)
        self.assertFalse(self.client.positions())
        self.assertEqual(len([o for o in self.client.sent if not o['reduceOnly']]), entries)
        self.assertEqual(self.engine.store.kill_reason(), 'runtime_reverification_required')

    def test_configuration_bounds(self):
        validate(config())
        for interval in (4, 241, '60', True, None):
            bad = config(); bad['tick_interval_minutes'] = interval
            with self.assertRaises(ValueError): validate(bad)
        bad = base_config(); bad['execution_model'] = 'cron'
        with self.assertRaises(ValueError): validate(bad)
        self.assertIs(runtime_ready(self.root, self.cfg)['scheduler']['verified'], True)


if __name__ == '__main__':
    unittest.main()

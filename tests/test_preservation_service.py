"""Specification preservation, actual HTTP encoding and worker lifecycle tests."""
import hashlib
import io
import json
from pathlib import Path
import tempfile
import threading
import time
import unittest
from unittest.mock import patch
from propfirm import __version__
from propfirm.config import digest, save_json
from propfirm.engine import Engine
from propfirm.propr import Client, DEFAULT_BUILDER_CODE
from propfirm.service import serve
from test_execution import FakeClient, FakeData, NOW, config


class PreservationTests(unittest.TestCase):
    def test_full_original_prompt_is_unchanged(self):
        docs=Path(__file__).resolve().parents[1]/'docs'
        original=(docs/'original-build-prompt.txt').read_bytes()
        self.assertEqual(hashlib.sha256(original).hexdigest(),
            '1b452237606fff18f85070ec43a6fd792d883ee50048de831f95f70d60cca976')
        spec=(docs/'SPECIFICATION.md').read_text().split('```text\n',1)[1].split('\n```',1)[0]
        self.assertEqual(spec+'\n',original.decode())
        self.assertEqual((docs/'original-build-prompt.sha256').read_text().split()[0],hashlib.sha256(original).hexdigest())
    def test_short_prompt_requires_full_specification(self):
        prompt=(Path(__file__).resolve().parents[1]/'docs/START-PROMPT.md').read_text()
        self.assertIn('docs/SPECIFICATION.md',prompt)
        self.assertIn('does not replace or remove any trading or risk rule',prompt)


class HTTPTests(unittest.TestCase):
    def test_order_transport_attribution_default_override_optout(self):
        for builder,expected in ((None,DEFAULT_BUILDER_CODE),('builder_override','builder_override'),('',None)):
            captured=[]
            class Opener:
                def open(self,req,timeout):
                    captured.append(req)
                    response=io.BytesIO(b'{"data":[]}');response.status=200
                    return response
            with patch.dict('os.environ',{},clear=True):
                client=Client('synthetic_key','trial-1',builder_code=builder,opener=Opener())
            client.submit({'intentId':'synthetic_intent','quantity':'1'})
            req=captured[0]
            self.assertEqual(req.full_url,'https://api.propr.xyz/v1/accounts/trial-1/orders')
            self.assertEqual(req.method,'POST')
            self.assertEqual(req.get_header('X-builder-code'),expected)
            self.assertEqual(req.get_header('X-api-key'),'synthetic_key')
            self.assertEqual(json.loads(req.data)['orders'][0]['intentId'],'synthetic_intent')
            with self.assertRaises(ValueError):client.request('GET','https://another.example/v1/account')
            self.assertEqual(len(captured),1)


class WorkerTests(unittest.TestCase):
    def make_engine(self,root):
        engine=Engine(FakeClient(),FakeData(),config(),root,sleeper=lambda _:None,clock=lambda:NOW)
        save_json(root/'approval.json',{'config_sha256':digest(config()),'version':__version__,
                  'account_mode':'trial','trading_authorized':True})
        return engine
    def test_scheduler_starts_monitor_trades_and_confirms_stop(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);engine=self.make_engine(root);observations=[]
            original_scan=engine.scan
            def scan():
                observations.append(engine.healthy_at is not None)
                original_scan()
                (root/'STOP').touch()
            engine.scan=scan
            class Clock:
                @staticmethod
                def now(_tz):return NOW
            with patch('propfirm.service.runtime_ready'),patch('propfirm.service.datetime',Clock):
                serve(engine)
            self.assertEqual(observations,[True])
            self.assertTrue(any(not o['reduceOnly'] for o in engine.client.sent))
            self.assertFalse(engine.client.positions())
            status=json.loads((root/'status.json').read_text())
            self.assertTrue(status['shutdown_complete']);self.assertTrue(status['worker_stopped'])
            self.assertEqual(engine.store.get('scheduled_date'),'2026-10-07')
            engine.store.close()
    def test_expired_runtime_evidence_recovers_only_to_flat(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);engine=self.make_engine(root);engine.scan()
            entries=len([o for o in engine.client.sent if not o['reduceOnly']])
            with patch('propfirm.service.runtime_ready',side_effect=ValueError('expired')):
                serve(engine)
            self.assertFalse(engine.client.positions())
            self.assertEqual(len([o for o in engine.client.sent if not o['reduceOnly']]),entries)
            self.assertEqual(engine.store.kill_reason(),'runtime_reverification_required')
            engine.store.close()
    def test_unknown_intent_never_claims_flat_shutdown_complete(self):
        with tempfile.TemporaryDirectory() as folder:
            engine=self.make_engine(Path(folder))
            engine.store.reserve('entry:unknown',{'type':'limit'})
            self.assertFalse(engine.shutdown('test_unknown'))
            self.assertFalse(engine.store.get('shutdown_complete'))
            engine.store.close()
    def test_slow_account_reads_do_not_authorize_entries(self):
        from dataclasses import replace
        from datetime import timedelta
        with tempfile.TemporaryDirectory() as folder:
            engine=self.make_engine(Path(folder));snapshot=engine.account()
            engine.account=lambda:replace(snapshot,observed_at=NOW-timedelta(seconds=31))
            with self.assertRaises(ValueError):engine.scan()
            self.assertIsNone(engine.healthy_at);self.assertFalse(engine.client.sent)
            engine.store.close()

if __name__=='__main__':unittest.main()

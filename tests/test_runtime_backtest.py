import copy
from datetime import datetime,timezone
from decimal import Decimal as D
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from propfirm.account import snapshot
from propfirm.backtest import simulate
from propfirm.config import digest, runtime_ready, save_json
from propfirm.service import exclusive
from propfirm.updates import prepare
from test_execution import MARKET, FakeData, FakeClient, config, NOW


class BacktestTests(unittest.TestCase):
    def history(self):
        rows=FakeData().candles(MARKET)
        # Breakout on index 60, enter on 61. Signal bar never fills at its own close.
        for i in range(60,65): rows[i].update(o='102',h='104',l='101',c='103')
        return rows
    def test_next_bar_entry_has_no_same_bar_close_fill(self):
        rows=self.history()
        result=simulate({'xyz:GOLD':rows},{'xyz:GOLD':MARKET})
        self.assertEqual(result['entry_fills_proxy'][0]['date'],rows[61]['t'])
        self.assertNotEqual(D(result['entry_fills_proxy'][0]['price']),D(rows[60]['c']))
    def test_future_close_does_not_change_entry_size_or_price(self):
        rows=self.history();other=copy.deepcopy(rows)
        other[61].update(h='999',c='999')
        a=simulate({'xyz:GOLD':rows},{'xyz:GOLD':MARKET})
        b=simulate({'xyz:GOLD':other},{'xyz:GOLD':MARKET})
        self.assertEqual(a['entry_fills_proxy'][0],b['entry_fills_proxy'][0])
    def test_stop_can_fire_on_entry_bar(self):
        rows=self.history();rows[61].update(l='80',c='100')
        result=simulate({'xyz:GOLD':rows},{'xyz:GOLD':MARKET})
        self.assertTrue(result['trades'])
        self.assertEqual(result['trades'][0]['exit_date'],rows[61]['t'])
        self.assertEqual(result['trades'][0]['reason'],'intraday_stop_proxy')
    def test_instrument_costs_used(self):
        rows=self.history();rows[61].update(l='95',c='100')
        high={**MARKET,'fee_per_side':'.005'}
        low=simulate({'xyz:GOLD':rows},{'xyz:GOLD':MARKET})
        costly=simulate({'xyz:GOLD':rows},{'xyz:GOLD':high})
        self.assertLess(D(costly['trades'][0]['pnl_after_costs']),D(low['trades'][0]['pnl_after_costs']))


class RuntimeTests(unittest.TestCase):
    def test_exclusive_worker_lock(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            with exclusive(root):
                with self.assertRaises(ValueError):
                    with exclusive(root):pass
            with exclusive(root):pass
    def test_missing_and_wrong_host_evidence_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            with self.assertRaises(FileNotFoundError):runtime_ready(root,config())
            evidence={key:{'verified':True,'observation':'synthetic test'} for key in
                      ('cloud_environment','persistent_storage','private_secrets','network_access','background_execution','idle_recovery','supervisor')}
            evidence.update(config_sha256=digest(config()),host_identity='test-cloud',checked_at=datetime.now(timezone.utc).isoformat())
            save_json(root/'runtime.json',evidence)
            with patch.dict(os.environ,{'PROPFIRM_HOST_ID':'wrong'}):
                with self.assertRaises(ValueError):runtime_ready(root,config())
            with patch.dict(os.environ,{'PROPFIRM_HOST_ID':'test-cloud'}):
                runtime_ready(root,config())
                changed=config();changed['entry_order_type']='market'
                with self.assertRaises(ValueError):runtime_ready(root,changed)
    def test_paid_mode_cannot_be_enabled_by_renaming_account(self):
        client=FakeClient();client.trial=False
        docs={'account':client.account(),'attempt':client.attempts()[0],'challenge':{}}
        cfg=config()
        with self.assertRaises(ValueError):snapshot(docs,cfg,NOW)
        cfg['account_mode']='paid';cfg['account_mapping']['trial']['equals']=False
        snapshot(docs,cfg,NOW)
    def test_update_rejects_shell_or_path_injection(self):
        for tag in ('../../home','main','v0.2.0;touch /tmp/oops','$(whoami)'):
            with self.assertRaises(ValueError):prepare(Path('/tmp'),tag)

if __name__=='__main__':unittest.main()

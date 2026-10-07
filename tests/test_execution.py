"""Synthetic API fixtures, based on documented order/position shapes.
Account fixture_* fields deliberately do not claim to be Propr schema names.
"""
import copy
from datetime import datetime, timezone
from decimal import Decimal as D
import json
from pathlib import Path
import tempfile
import unittest
from propfirm.account import snapshot
from propfirm.config import validate
from propfirm.data import Data, DAY, validated_candles, rounded_price
from propfirm.engine import Engine
from propfirm.propr import Client, APIError

NOW = datetime(2026, 10, 7, 0, 10, tzinfo=timezone.utc)
MARKET = {'asset':'xyz:GOLD','base':'xyz:GOLD','quote':'USDC','product_type':'perp','sz_decimals':2,
          'quantity_step':'.01','minimum_quantity':'.01','minimum_notional':'10','multiplier':'1',
          'sessions_utc':'24/7','stop_supported':True,'evidence':'synthetic fixture'}


def config():
    def field(key, source='account', **extra): return {'source':source, 'path':[key], **extra}
    return {'account_id':'trial-1','entry_order_type':'limit','markets':[copy.deepcopy(MARKET)],'mapping_evidence':'synthetic fixture',
            'account_mapping':{'trial':field('fixture_isTrial','attempt',equals=True),
             'starting_balance':field('fixture_start'),'day_start_balance':field('fixture_day_start'),
             'day_reference':field('fixture_day'),'balance':field('balance'),'equity':field('fixture_equity'),
             'daily_loss_fraction':field('fixture_daily'),'max_drawdown_fraction':field('fixture_max'),
             'profit_target_fraction':field('fixture_target'),'drawdown_type':field('fixture_drawdown',equals='static')}}


class FakeClient:
    account_id='trial-1'
    account_path='/v1/accounts/trial-1'
    def __init__(self):
        self.order_rows=[]; self.position_rows=[]; self.sent=[]
        self.reject_stop=False; self.reject_close=False; self.reject_cancel=False
        self.lose_response=False; self.partial=False; self.mark=102
        self.equity=25000; self.trial=True
    def account(self):
        return {'balance':'25000','fixture_equity':str(self.equity),'fixture_start':'25000',
                'fixture_day_start':'25000','fixture_day':'2026-10-07','fixture_daily':'.03','fixture_max':'.06',
                'fixture_target':'.10','fixture_drawdown':'static'}
    def attempts(self):
        return [{'accountId':'trial-1','challengeId':'challenge-1','status':'active','fixture_isTrial':self.trial}]
    def challenges(self): return [{'challengeId':'challenge-1'}]
    def orders(self): return copy.deepcopy(self.order_rows)
    def positions(self): return copy.deepcopy(self.position_rows)
    def pages(self, *_args, **_kwargs): return []
    def submit(self, payload):
        duplicate=[o for o in self.order_rows if o['intentId']==payload['intentId']]
        if duplicate: return {'data':copy.deepcopy(duplicate)}
        self.sent.append(copy.deepcopy(payload))
        order={**payload,'orderId':'o'+str(len(self.sent)), 'status':'open','cumulativeQuantity':'0'}
        if payload['type']=='stop_market':
            if self.reject_stop: order['status']='rejected'
        elif payload['reduceOnly']:
            if self.reject_close: order['status']='rejected'
            else:
                self.position_rows=[]; order['status']='filled'; order['cumulativeQuantity']=payload['quantity']
        else:
            qty=D(payload['quantity']) / (2 if self.partial else 1)
            order.update(status='cancelled' if self.partial else 'filled', cumulativeQuantity=str(qty), averageFillPrice='102',positionId='p1')
            self.position_rows=[{'positionId':'p1','asset':payload['asset'],'base':payload['base'],'quote':payload['quote'],
                 'positionSide':payload['positionSide'],'quantity':str(qty),'entryPrice':'102','markPrice':'102',
                 'notionalValue':str(qty*102),'status':'open'}]
        self.order_rows.append(order)
        if self.lose_response:
            self.lose_response=False
            raise APIError()
        return {'data':[copy.deepcopy(order)]}
    def cancel(self, oid):
        if self.reject_cancel: raise APIError(500)
        for o in self.order_rows:
            if o['orderId']==oid: o['status']='cancelled'
        return {}


class FakeData:
    def candles(self, market):
        end=int(NOW.timestamp()*1000)//DAY*DAY
        result=[]
        for i in range(65):
            t=end-(65-i)*DAY
            result.append({'t':t,'T':t+DAY-1,'s':market['asset'],'i':'1d','o':'100','h':'101','l':'99','c':'100','v':'100'})
        result[-1].update(h='103',c='102')
        return result
    def quote(self, market): return D('101.9'),D('102')


class ExecutionTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        self.client=FakeClient();self.engine=Engine(self.client,FakeData(),config(),self.root,sleeper=lambda _:None,clock=lambda:NOW)
    def tearDown(self):
        self.engine.store.close();self.temp.cleanup()
    def test_real_order_payload_and_protective_stop_path(self):
        self.engine.scan()
        entry,stop=self.client.sent
        self.assertEqual(entry['type'],'limit');self.assertEqual(entry['timeInForce'],'IOC')
        self.assertEqual(entry['asset'],'xyz:GOLD');self.assertFalse(entry['reduceOnly'])
        self.assertEqual(stop['type'],'stop_market');self.assertTrue(stop['reduceOnly'])
        self.assertEqual(stop['positionId'],'p1');self.assertEqual(stop['side'],'sell')
        self.assertTrue((self.root/'reports/2026-10-07.md').exists())
    def test_duplicate_scan_and_restart_never_adds(self):
        self.engine.scan();sent=len(self.client.sent)
        self.engine.scan();self.assertEqual(len(self.client.sent),sent)
        self.engine.store.close()
        self.engine=Engine(self.client,FakeData(),config(),self.root,sleeper=lambda _:None,clock=lambda:NOW)
        self.engine.recover();self.engine.scan();self.assertEqual(len(self.client.sent),sent)
    def test_partial_ioc_fill_protects_actual_quantity_without_top_up(self):
        self.client.partial=True;self.engine.scan()
        entry,stop=self.client.sent
        self.assertEqual(D(stop['quantity']),D(entry['quantity'])/2)
        self.assertEqual(len([o for o in self.client.sent if not o['reduceOnly']]),1)
    def test_market_entry_is_explicit_option(self):
        self.engine.config['entry_order_type']='market';self.engine.scan()
        self.assertEqual(self.client.sent[0]['type'],'market');self.assertNotIn('price',self.client.sent[0])
    def test_stop_rejection_flattens_and_latches_kill(self):
        self.client.reject_stop=True;self.engine.scan()
        self.assertFalse(self.client.position_rows)
        self.assertEqual(self.engine.store.kill_reason(),'protection_failure')
        self.assertTrue(self.client.sent[-1]['reduceOnly']);self.assertTrue(self.client.sent[-1]['closePosition'])
    def test_failed_close_does_not_mark_shutdown_complete_or_cancel_stop(self):
        self.engine.scan();self.client.reject_close=True
        self.assertFalse(self.engine.shutdown('test'))
        self.assertFalse(self.engine.store.get('shutdown_complete'))
        self.assertEqual(next(o for o in self.client.order_rows if o['type']=='stop_market')['status'],'open')
        self.client.reject_close=False
        self.assertTrue(self.engine.shutdown('test'))
        self.assertTrue(self.engine.store.get('shutdown_complete'))
    def test_failed_cancellation_keeps_shutdown_incomplete(self):
        self.engine.scan();self.client.reject_cancel=True
        self.assertFalse(self.engine.shutdown('test'))
        self.assertFalse(self.engine.store.get('shutdown_complete'))
        self.assertFalse(self.client.position_rows)
    def test_lost_response_reconciles_same_intent_without_second_submission(self):
        payload=self.engine.payload(MARKET,'long',D(1),'limit',price='102')
        self.client.lose_response=True
        with self.assertRaises(ValueError):self.engine.send('test-entry',payload)
        result=self.engine.send('test-entry',payload)
        self.assertEqual(len(self.client.sent),1);self.assertEqual(result['intentId'],self.client.sent[0]['intentId'])
    def test_static_loss_executes_shutdown(self):
        self.engine.scan();self.client.equity=23875;self.engine.tick()
        self.assertFalse(self.client.position_rows);self.assertTrue(self.engine.store.kill_reason())
    def test_daily_halt_keeps_stops_and_blocks_entries(self):
        self.client.equity=24500;self.engine.scan()
        self.assertFalse(self.client.sent);self.assertEqual(self.engine.store.get('daily_halt_date'),'2026-10-07')
    def test_paid_account_rejected_before_orders(self):
        self.client.trial=False
        with self.assertRaises(ValueError):self.engine.scan()
        self.assertFalse(self.client.sent)
    def test_unexpected_rule_change_rejected(self):
        docs={'account':self.client.account(),'attempt':self.client.attempts()[0],'challenge':{}}
        docs['account']['fixture_max']='.03'
        with self.assertRaises(ValueError):snapshot(docs,config(),NOW)
    def test_yesterday_daily_reference_rejected(self):
        docs={'account':self.client.account(),'attempt':self.client.attempts()[0],'challenge':{}}
        docs['account']['fixture_day']='2026-10-06'
        with self.assertRaises(ValueError):snapshot(docs,config(),NOW)


class MarketDataTests(unittest.TestCase):
    def test_completed_bar_filter(self):
        rows=FakeData().candles(MARKET)
        self.assertEqual(len(validated_candles(rows,'xyz:GOLD',rows[-1]['T'])),64)
    def test_no_silent_symbol_substitution(self):
        with self.assertRaises(ValueError):validated_candles(FakeData().candles(MARKET),'GOLD',int(NOW.timestamp()*1000))
    def test_crossed_stale_and_closed_quote_rejected(self):
        for book in ({'coin':'xyz:GOLD','time':0,'levels':[[{'px':'100'}],[{'px':'101'}]]},
                     {'coin':'xyz:GOLD','time':int(NOW.timestamp()*1000),'levels':[[{'px':'102'}],[{'px':'101'}]]}):
            with self.assertRaises(ValueError):Data(Path('/tmp'),request=lambda _:book).quote(MARKET,NOW)
    def test_rounding_respects_price_precision(self):
        self.assertEqual(rounded_price(D('123.4567'),2,False),D('123.45'))
        self.assertEqual(rounded_price(D('123.4567'),2,True),D('123.46'))
        self.assertEqual(rounded_price(D('100001.2'),2,True),D(100002))
    def test_metadata_validation(self):
        validate(config())
        bad=config();bad['markets'][0]['stop_supported']=False
        with self.assertRaises(ValueError):validate(bad)


class PaginationTests(unittest.TestCase):
    def test_follows_actual_offset_until_exhausted(self):
        c=Client('test','trial-1');calls=[]
        def request(method,path,params):
            calls.append(params['offset'])
            return {'data':[{'id':params['offset']}] if params['offset']<3 else []}
        c.request=request
        self.assertEqual(len(c.pages('/v1/challenge-attempts')),3);self.assertEqual(calls,[0,1,2,3])
    def test_repeating_page_rejected(self):
        c=Client('test','trial-1');c.request=lambda *a,**k:{'data':[{'id':1}]}
        with self.assertRaises(ValueError):c.pages('/v1/challenge-attempts')
    def test_non_order_writes_rejected(self):
        c=Client('test','trial-1')
        with self.assertRaises(ValueError):c.request('POST','/v1/payouts',{})

if __name__=='__main__': unittest.main()

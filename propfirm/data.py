"""Hyperliquid public market data, with no Propr credentials."""
import json
from datetime import datetime, timezone
from decimal import Decimal as D, ROUND_FLOOR, ROUND_CEILING
from urllib.request import Request, build_opener
from .propr import NoRedirects
from .config import save_json
from .strategy import Bar, positive

DAY = 86_400_000


def public_info(payload):
    req = Request('https://api.hyperliquid.xyz/info', data=json.dumps(payload).encode(),
                  headers={'Content-Type': 'application/json', 'User-Agent': 'ProsperityAgentKit/0.2.0'}, method='POST')
    with build_opener(NoRedirects()).open(req, timeout=10) as response:
        return json.load(response)


def price_tick(price, sz_decimals):
    positive(price)
    # Hyperliquid permits integer prices regardless of significant figures.
    return D(1) if price >= 100000 else D(10) ** max(price.adjusted() - 4, sz_decimals - 6)


def rounded_price(price, sz_decimals, round_up):
    tick = price_tick(price, sz_decimals)
    value = (price / tick).to_integral_value(rounding=ROUND_CEILING if round_up else ROUND_FLOOR) * tick
    # Rounding across a power-of-ten boundary can change permitted precision.
    tick2 = price_tick(value, sz_decimals)
    return (value / tick2).to_integral_value(rounding=ROUND_CEILING if round_up else ROUND_FLOOR) * tick2


def session_open(market, now):
    sessions = market['sessions_utc']
    if sessions == '24/7':
        return True
    utc = now.astimezone(timezone.utc)
    minute = utc.hour * 60 + utc.minute
    return any(s['weekday'] == utc.weekday() and s['start_minute'] <= minute < s['end_minute'] for s in sessions)


def validated_candles(rows, asset, now_ms):
    values = {}
    for row in rows:
        if row.get('s') != asset or row.get('i') != '1d':
            raise ValueError('Candle symbol/interval mismatch')
        start, end = int(row['t']), int(row['T'])
        if start % DAY or end != start + DAY - 1:
            raise ValueError('Unexpected daily candle boundaries')
        if end >= now_ms:
            continue
        Bar(D(row['h']), D(row['l']), D(row['c']))
        positive(D(row['o']))
        if not D(row['l']) <= D(row['o']) <= D(row['h']) or D(row['v']) < 0 or not D(row['v']).is_finite():
            raise ValueError('Invalid OHLCV')
        if start in values and values[start] != row:
            raise ValueError('Conflicting duplicate candle')
        values[start] = row
    return [values[t] for t in sorted(values)][-400:]


class Data:
    def __init__(self, root, request=public_info):
        self.root, self.request = root, request

    def discover(self, dex=''):
        payload = {'type': 'meta'}
        if dex:
            payload['dex'] = dex
        return self.request(payload)

    def candles(self, market, now=None):
        now = now or datetime.now(timezone.utc)
        ms = int(now.timestamp() * 1000)
        rows = self.request({'type': 'candleSnapshot', 'req': {'coin': market['asset'], 'interval': '1d',
                            'startTime': ms - 401 * DAY, 'endTime': ms}})
        rows = validated_candles(rows, market['asset'], ms)
        if len(rows) < 60:
            raise ValueError('Fewer than 60 completed bars for ' + market['asset'])
        save_json(self.root / 'cache' / (market['asset'].replace(':', '_') + '.json'), rows)
        return rows

    def quote(self, market, now=None):
        now = now or datetime.now(timezone.utc)
        if not session_open(market, now):
            raise ValueError('Market session is closed')
        book = self.request({'type': 'l2Book', 'coin': market['asset']})
        age = now.timestamp() * 1000 - int(book['time'])
        if book.get('coin') != market['asset'] or age < -1000 or age > 10_000:
            raise ValueError('Stale or mismatched quote')
        bid, ask = D(book['levels'][0][0]['px']), D(book['levels'][1][0]['px'])
        positive(bid, ask)
        if bid >= ask:
            raise ValueError('Crossed quote')
        return bid, ask


def strategy_bars(rows):
    return [Bar(D(r['h']), D(r['l']), D(r['c'])) for r in rows]

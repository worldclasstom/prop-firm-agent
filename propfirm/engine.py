"""Account-scoped execution. Every write uses a durable, idempotent intent."""
import hashlib
import json
import threading
import time
from dataclasses import replace
from datetime import datetime, timezone
from decimal import Decimal as D
from .account import select_documents, snapshot
from .config import save_json, validate_markets
from .order_limits import quantity_floor, below_known_notional, unknown_minimums
from .data import DAY, rounded_price, strategy_bars
from .propr import APIError
from .risk import RiskState, evaluate
from .state import Store
from .strategy import atr, entry, exit_signal, quantity

TERMINAL = {'filled', 'cancelled', 'canceled', 'rejected', 'expired'}
ACTIVE = {'pending', 'open', 'partially_filled', 'triggered'}


def active(orders):
    for order in orders:
        if order['status'] not in ACTIVE | TERMINAL:
            raise ValueError('Unrecognized order status; reconciliation required')
    return [o for o in orders if o['status'] in ACTIVE]


class Engine:
    def __init__(self, client, data, config, root, sleeper=time.sleep, clock=None):
        validate_markets(config)
        self.client, self.data, self.config, self.root = client, data, config, root
        self.store = Store(root / 'state.sqlite')
        self.lock = threading.RLock()
        self.sleep = sleeper
        self.clock = clock or (lambda: datetime.now(timezone.utc))
        self.healthy_at = None
        self.live_marks = None
        if config.get('account_adapter') == 'propr-v1':
            from .live_marks import LiveMarks
            self.live_marks = LiveMarks(client.api_key, client.account_id)
        self.markets = {m['asset']: m for m in config['markets']}
        saved = self.store.get('account_id')
        if saved and saved != config['account_id']:
            raise ValueError('Private state belongs to another account; use a separate PROPFIRM_HOME')
        self.store.put('account_id', config['account_id'])

    def report(self, event, **details):
        # Only explicitly constructed fields; never write exception/HTTP bodies or secrets.
        date = self.clock().date().isoformat()
        path = self.root / 'reports' / (date + '.jsonl')
        path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        import os
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
        with os.fdopen(fd, 'a') as stream:
            stream.write(json.dumps({'at': self.clock().isoformat(), 'event': event, **details}, default=str) + '\n')

    def account(self):
        started = self.clock()
        revision = self.live_marks.revision() if self.live_marks else None
        documents = select_documents(self.client, include_daily=self.config.get('account_adapter') == 'propr-v1')
        result = snapshot(documents, self.config, started)
        if self.live_marks:
            result = replace(result, equity=self.live_marks.equity(documents['account'],
                             self.client.positions(), revision))
        if result.day != self.clock().date().isoformat():
            raise ValueError('UTC reset crossed during account read; retry fresh')
        return result

    def payload(self, market, position_side, size, order_type, **extra):
        return {'accountId': self.client.account_id, 'exchange': 'hyperliquid', 'productType': 'perp',
                'asset': market['asset'], 'base': market['base'], 'quote': market['quote'],
                'positionSide': position_side, 'side': 'buy' if position_side == 'long' else 'sell',
                'quantity': str(size), 'type': order_type, 'timeInForce': 'IOC',
                'reduceOnly': False, 'closePosition': False, **extra}

    def send(self, key, payload):
        """Reconcile first; never create a fresh intent after an unknown response."""
        saved = self.store.intent(key)
        if saved is None:
            _, saved = self.store.reserve(key, payload)
        else:
            # A retry must replay persisted bytes, including the original quote and size.
            payload = {k: v for k, v in saved.items() if k != 'intentId'}
        orders = self.client.orders()
        matches = [o for o in orders if o.get('intentId') == saved['intentId']]
        if len(matches) > 1:
            raise ValueError('Duplicate server intents')
        if matches:
            return matches[0]
        if not saved.get('reduceOnly') and self.store.get('rejected_intent:' + saved['intentId']):
            raise ValueError('Entry intent was rejected; it will not be resubmitted')
        try:
            response = self.client.submit(saved)
            matches = [o for o in response.get('data', []) if o.get('intentId') == saved['intentId']]
            if len(matches) == 1:
                self.report('order_submitted', order_id=matches[0]['orderId'], intent_id=saved['intentId'], type=saved['type'])
                return matches[0]
        except APIError as error:
            if error.status in (400, 401, 403, 404, 422):
                self.store.put('rejected_intent:' + saved['intentId'], True)
                self.store.put('entry_block', 'order_request_rejected')
                self.report('order_request_rejected', asset=saved['asset'],
                            intent_id=saved['intentId'], http_status=error.status)
                raise ValueError('Order request rejected; review configuration before retry') from None
        # Unknown does not mean absent; leave the intent for recovery.
        self.store.put('entry_block', 'order_outcome_unknown')
        self.report('order_outcome_unknown', intent_id=saved['intentId'])
        raise ValueError('Order outcome unknown; reconciliation required')

    def cancel(self, order):
        try:
            self.client.cancel(order['orderId'])
        except APIError:
            pass
        # A failed cancel may indicate a fill, so the caller must read positions again.
        rows = [o for o in self.client.orders() if o['orderId'] == order['orderId']]
        if len(rows) != 1 or rows[0]['status'] not in TERMINAL:
            raise ValueError('Cancellation not confirmed')

    def close_position(self, position):
        market = self.markets.get(position['asset'])
        if market is None:
            # Emergency reduction needs only actual position fields, not invented metadata.
            market = {k: position[k] for k in ('asset', 'base', 'quote')}
        prefix = 'close:' + position['positionId']
        # Reuse any unresolved close. A terminal partial IOC can require a new intent.
        orders = self.client.orders()
        pending = [p for k, p in self.store.all_intents() if k.startswith(prefix + ':')
                   and not any(o.get('intentId') == p['intentId'] and o['status'] in TERMINAL for o in orders)]
        if pending:
            payload = pending[0]
            key = next(k for k, p in self.store.all_intents() if p['intentId'] == payload['intentId'])
        else:
            attempt = len([1 for k, _ in self.store.all_intents() if k.startswith(prefix + ':')])
            key = prefix + ':' + str(attempt)
            payload = self.payload(market, position['positionSide'], D(position['quantity']), 'market',
                       side='sell' if position['positionSide'] == 'long' else 'buy',
                       reduceOnly=True, closePosition=True, positionId=position['positionId'])
        result = self.send(key, {k: v for k, v in payload.items() if k != 'intentId'})
        if result['status'] in TERMINAL and not any(p['positionId'] == position['positionId'] for p in self.client.positions()):
            for order in active(self.client.orders()):
                if order.get('positionId') == position['positionId'] and order.get('reduceOnly', False):
                    self.cancel(order)

    def shutdown(self, reason):
        """Keep worker alive until fresh reads confirm flat and all orders terminal."""
        self.store.latch_kill(reason)
        self.store.put('shutdown_complete', False)
        halt_path = self.root / 'reports' / 'HALT.md'
        halt_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        halt_path.write_text('# Trading halted\n\nReason: ' + reason + '\nShutdown is incomplete until fresh reads confirm flat and all orders terminal.\n')
        halt_path.chmod(0o600)
        for order in active(self.client.orders()):
            if not order.get('reduceOnly', False):
                try:
                    self.cancel(order)
                except (APIError, ValueError):
                    self.report('cancel_unresolved', order_id=order['orderId'])
        positions = self.client.positions()
        for p in positions:
            try:
                self.close_position(p)
            except (APIError, ValueError):
                self.report('close_unresolved', position_id=p['positionId'])
        positions = self.client.positions()
        if positions:
            save_json(self.root / 'reports' / 'HALT.json', {'reason': reason, 'complete': False,
                       'unresolved_positions': [p['positionId'] for p in positions]})
            return False
        # Keep protection until position reads confirm flat.
        for order in active(self.client.orders()):
            try:
                self.cancel(order)
            except (APIError, ValueError):
                self.report('cancel_unresolved', order_id=order['orderId'])
        final_orders = self.client.orders()
        known = {o.get('intentId') for o in final_orders}
        unresolved = [p['intentId'] for _, p in self.store.all_intents() if p['intentId'] not in known and not self.store.get('rejected_intent:' + p['intentId'])]
        complete = not self.client.positions() and not active(final_orders) and not unresolved
        self.store.put('shutdown_complete', complete)
        if complete:
            halt_path.write_text('# Trading halted\n\nReason: ' + reason + '\nConfirmed flat with no remaining active orders. The kill latch remains set.\n')
        save_json(self.root / 'reports' / 'HALT.json', {'reason': reason, 'complete': complete, 'unresolved_intents': unresolved})
        return complete

    def protect(self, position):
        pid, asset, side = position['positionId'], position['asset'], position['positionSide']
        context = self.store.get('entry_context:' + asset)
        if not context or asset not in self.markets:
            raise ValueError('Position has no verified agent entry context')
        market = self.markets[asset]
        fill, size, volatility = D(position['entryPrice']), D(position['quantity']), D(context['atr'])
        raw = fill - 2 * volatility if side == 'long' else fill + 2 * volatility
        price = rounded_price(raw, market['sz_decimals'], side == 'long')
        previous = self.store.get('stop:' + pid)
        if previous:
            price = max(price, D(previous)) if side == 'long' else min(price, D(previous))
        self.store.put('stop:' + pid, str(price))
        stops = [o for o in active(self.client.orders()) if o.get('positionId') == pid and
                 o.get('reduceOnly') is True and o['type'] == 'stop_market' and o.get('positionSide') == side]
        suitable = [o for o in stops if o['status'] == 'open' and D(o['quantity']) - D(o.get('cumulativeQuantity', '0')) >= size and
                    (D(o['triggerPrice']) >= price if side == 'long' else D(o['triggerPrice']) <= price)]
        if suitable:
            return
        key = 'stop:' + pid + ':' + hashlib.sha256(f'{size}:{price}'.encode()).hexdigest()[:16]
        payload = self.payload(market, side, size, 'stop_market', side='sell' if side == 'long' else 'buy',
                    timeInForce='GTC', triggerPrice=str(price), reduceOnly=True, positionId=pid)
        self.send(key, payload)
        for _ in range(4):
            current = [o for o in self.client.orders() if o.get('intentId') == self.store.intent(key)['intentId']]
            if current and current[0]['status'] == 'open':
                for old in stops:
                    if old['orderId'] != current[0]['orderId']:
                        self.cancel(old)
                self.report('protection_confirmed', position_id=pid, order_id=current[0]['orderId'], quantity=size, trigger=price)
                return
            if not any(p['positionId'] == pid for p in self.client.positions()):
                return  # Stop may already have fired.
            self.sleep(.25)
        raise ValueError('Protective stop not confirmed')

    def recover(self):
        """Reconcile persisted intents, then protect fills; ambiguous entries block new risk."""
        orders = self.client.orders()
        known = {o.get('intentId') for o in orders}
        for key, payload in self.store.all_intents():
            if key.startswith('entry:') and payload['intentId'] not in known:
                self.store.put('entry_block', 'ambiguous_entry_requires_review')
        for p in self.client.positions():
            self.protect(p)

    def tick(self, daily_scan=False):
        with self.lock:
            if self.store.get('operator_stop'):
                self.store.latch_kill('operator_stop')
            if self.store.kill_reason():
                self.shutdown(self.store.kill_reason())
                return None
            snap = self.account()
            baseline = self.store.get('starting_balance')
            if baseline and D(baseline) != snap.starting_balance:
                raise ValueError('Starting balance changed unexpectedly')
            self.store.put('starting_balance', str(snap.starting_balance))
            state = RiskState(self.store.get('daily_halt_date'), False)
            decision = evaluate(state, starting_balance=snap.starting_balance, day_start_balance=snap.day_start_balance,
                       equity=snap.equity, now=self.clock(), snapshot_at=snap.observed_at, monitor_healthy=True, daily_scan=daily_scan)
            self.store.put('daily_halt_date', decision.state.daily_halt_date)
            if decision.flatten_required:
                self.shutdown(decision.reason)
                return snap
            if decision.cancel_entries or self.store.get('entry_block'):
                for order in active(self.client.orders()):
                    if not order.get('reduceOnly', False):
                        self.cancel(order)
            try:
                for position in self.client.positions():
                    self.protect(position)
            except Exception:
                self.store.put('entry_block', 'protection_failure')
                self.shutdown('protection_failure')
                return snap
            if decision.reason == 'stale_data_or_monitor':
                self.healthy_at = None
                raise ValueError('Account reads exceeded the risk freshness limit')
            self.healthy_at = self.clock()
            self.store.put('heartbeat', {'at': self.healthy_at.isoformat(), 'equity': str(snap.equity),
                          'balance': str(snap.balance), 'day_start_balance': str(snap.day_start_balance),
                          'starting_balance': str(snap.starting_balance), 'daily_floor': str(snap.day_start_balance * D('.97')),
                          'drawdown_floor': str(snap.starting_balance * D('.94'))})
            return snap

    def scan(self):
        histories, errors = {}, []
        for asset, market in self.markets.items():
            try:
                rows = self.data.candles(market)
                expected = int(self.clock().timestamp() * 1000) // DAY * DAY - 1
                if int(rows[-1]['T']) != expected:
                    raise ValueError('Latest daily candle is stale')
                histories[asset] = rows
            except Exception:
                errors.append(asset)
                self.report('market_skipped', asset=asset, reason='missing_stale_or_invalid_daily_data')
        with self.lock:
            snap = self.tick(daily_scan=True)
            if snap is None or self.store.kill_reason():
                return
            positions = self.client.positions()
            for p in positions:
                if p['asset'] in histories and exit_signal(strategy_bars(histories[p['asset']]), p['positionSide']):
                    self.close_position(p)
                    self.report('strategy_exit', position_id=p['positionId'])
            ranked = sorted(histories, key=lambda a: (-D(histories[a][-1]['v']) * D(histories[a][-1]['c']) * D(self.markets[a]['multiplier']), a))
            for asset in ranked:
                market, rows = self.markets[asset], histories[asset]
                bars = strategy_bars(rows)
                side = entry(bars)
                self.report('signal', asset=asset, side=side, signal_date=rows[-1]['T'])
                if side is None:
                    continue
                key = 'entry:' + asset + ':' + str(rows[-1]['T'])
                if self.store.intent(key):
                    continue
                snap = self.tick()
                if snap is None or self.store.kill_reason() or self.store.get('daily_halt_date') or self.store.get('entry_block'):
                    break
                revision = self.live_marks.revision() if self.live_marks else None
                positions, orders = self.client.positions(), active(self.client.orders())
                occupied = {p['asset'] for p in positions} | {o['asset'] for o in orders if not o.get('reduceOnly', False)}
                if asset in occupied or len(occupied) >= 3:
                    continue
                try:
                    bid, ask = self.data.quote(market)
                except Exception:
                    self.report('entry_skipped', asset=asset, reason='quote_or_session_unavailable')
                    continue
                price = rounded_price(ask if side == 'long' else bid, market['sz_decimals'], side == 'short')
                gross = (self.live_marks.gross(positions, revision) if self.live_marks else
                         sum((abs(D(p['notionalValue'])) for p in positions), D(0)))
                # Any unresolved entry blocks new submissions; do not estimate unknown notional.
                if any(not o.get('reduceOnly', False) for o in orders):
                    continue
                volatility = atr(bars)
                if side == 'long' and 2 * volatility >= price:
                    self.report('entry_skipped', asset=asset, reason='stop_not_representable')
                    continue
                size = quantity(snap.starting_balance, snap.equity, gross, price, volatility,
                                D(market['multiplier']), D(market['quantity_step']), quantity_floor(market))
                if size == 0 or below_known_notional(market, size * price * D(market['multiplier'])):
                    continue
                if unknown_minimums([market]):
                    self.report('entry_limits_deferred_to_broker', asset=asset,
                                unknown_fields=unknown_minimums([market])[asset], quantity=str(size))
                self.store.put('entry_context:' + asset, {'atr': str(volatility), 'side': side, 'signal': rows[-1]['T']})
                order_type = self.config.get('entry_order_type', 'limit')
                payload = self.payload(market, side, size, order_type, **({'price': str(price)} if order_type == 'limit' else {}))
                order = self.send(key, payload)
                for _ in range(6):
                    self.tick()  # Protect partial fills and check equity before waiting again.
                    matches = [o for o in self.client.orders() if o.get('intentId') == order['intentId']]
                    if matches and matches[0]['status'] in TERMINAL:
                        if matches[0]['status'] == 'rejected':
                            self.store.put('entry_block', 'order_request_rejected')
                            self.report('entry_rejected', asset=asset, order_id=matches[0]['orderId'])
                        break
                    self.sleep(.25)
                else:
                    if matches:
                        self.cancel(matches[0])
                    self.store.put('entry_block', 'ioc_not_terminal')
                self.tick()
            self.store.put('last_scan', {'at': self.clock().isoformat(), 'data_exclusions': errors})
            self.write_report()

    def write_report(self):
        positions, orders = self.client.positions(), self.client.orders()
        trades = self.client.pages(self.client.account_path + '/trades')
        day = self.clock().date().isoformat()
        summary = {'account_id': self.client.account_id, 'account_type': 'verified_' + self.config.get('account_mode', 'trial'),
                   'order_limits_policy': self.config.get('order_limits_policy', 'verified'),
                   'unverified_order_minimums': unknown_minimums(self.config['markets']),
                   'status': self.store.get('heartbeat'), 'kill': self.store.kill_reason(),
                   'entry_block': self.store.get('entry_block'), 'daily_halt': self.store.get('daily_halt_date'),
                   'positions': positions, 'orders': orders,
                   'trades_today': [t for t in trades if str(t.get('executedAt', '')).startswith(day)]}
        save_json(self.root / 'reports' / (day + '.json'), summary)
        lines = ['# Daily trial report: ' + day, '', 'Account: ' + self.client.account_id,
                 'Account type: verified ' + self.config.get('account_mode', 'trial'), '', '## Account and risk', '',
                 '```json', json.dumps(summary['status'], indent=2), '```', '',
                 '## Activity', '', f'{len(positions)} open positions. See the adjacent JSON and event log for signals, orders, fills and reasons.', '',
                 'Daily halt: ' + str(summary['daily_halt']), 'Entry block: ' + str(summary['entry_block']),
                 'Kill latch: ' + str(summary['kill'])]
        if summary['unverified_order_minimums']:
            lines += ['', 'Broker order minimums remain unknown for: ' +
                      ', '.join(sorted(summary['unverified_order_minimums'])) +
                      '. Qualifying orders may be rejected; order sizes are never increased to satisfy a minimum.']
        heartbeat = summary['status'] or {}
        if heartbeat:
            eq = D(heartbeat['equity'])
            lines += ['', 'Distance to daily challenge limit: ' + str(eq-D(heartbeat['daily_floor'])),
                      'Distance to static challenge limit: ' + str(eq-D(heartbeat['drawdown_floor']))]
        realised = sum((D(t.get('realizedPnl','0')) for t in summary['trades_today']), D(0))
        lines += ['', 'Realised P&L today (before separately reported fees/funding): ' + str(realised), '', '## Positions and stops', '']
        for p in positions:
            stops = [o for o in orders if o.get('positionId') == p['positionId'] and o.get('type') == 'stop_market' and o['status'] == 'open']
            stop_text = ', '.join(str(o['triggerPrice']) + ' (distance ' + str(abs(D(p['markPrice'])-D(o['triggerPrice']))) + ')' for o in stops) or 'NO CONFIRMED STOP'
            lines.append('- ' + p['asset'] + ' ' + p['positionSide'] + ', units ' + str(p['quantity']) + '. Stops: ' + stop_text)
        lines += ['', '## Orders and fills', '']
        for o in orders:
            lines.append('- ' + o['orderId'] + ': ' + o['asset'] + ' ' + o['type'] + ' ' + o['status'] + ', filled ' + str(o.get('cumulativeQuantity','0')))
        log = self.root / 'reports' / (day + '.jsonl')
        if log.exists():
            lines += ['', '## Signals and decisions', '']
            for raw in log.read_text().splitlines():
                event = json.loads(raw)
                lines.append('- ' + event['at'] + ' ' + event['event'] + ' ' + json.dumps({k:v for k,v in event.items() if k not in ('at','event')}))
        path = self.root / 'reports' / (day + '.md')
        path.write_text('\n'.join(lines) + '\n')
        path.chmod(0o600)

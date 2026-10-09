"""Daily OHLC scenario model. No claim that it reproduces actual IOC fills."""
from decimal import Decimal as D
from .data import DAY, strategy_bars, rounded_price
from .strategy import atr, entry, exit_signal, quantity
from .order_limits import quantity_floor, below_known_notional, unknown_minimums


def simulate(histories, markets, initial=D(25000), fee=D('.00075'), slippage=D('.0005'), funding=D('.0001'), *, start_at=None):
    """Next-bar-open proxy, shared signals and sizing, conservative intraday flags.

    All per-day trading decisions use only the previous completed bars and current
    open. Day highs/lows/closes are used only after those decisions to model outcomes.
    """
    for cost in (fee, slippage, funding):
        if not cost.is_finite() or not 0 <= cost < 1:
            raise ValueError('Invalid cost assumption')
    def costs(asset):
        market = markets[asset]
        values = tuple(D(str(market.get(k, v))) for k,v in (('fee_per_side',fee),('slippage_per_side',slippage),('daily_funding_cost',funding)))
        if any(not v.is_finite() or not 0 <= v < 1 for v in values):
            raise ValueError('Invalid instrument cost assumption')
        return values
    dates = sorted({int(r['t']) for rows in histories.values() for r in rows})
    indexed = {a: {int(r['t']): (i, r) for i, r in enumerate(rows)} for a, rows in histories.items()}
    balance, positions, curve, trades, fills = initial, {}, [], [], []
    peak, max_dd, flat_days, longest_flat = initial, D(0), 0, 0
    failure, target_date = None, None
    for date in dates:
        if start_at is not None and date < start_at:
            continue
        today = {a: indexed[a][date] for a in indexed if date in indexed[a] and indexed[a][date][0] >= 60}
        if not today:
            continue
        day_start = balance
        if any(a not in today for a in positions):
            failure = 'missing_data_with_open_position'
            break
        def equity(mark):
            return balance + sum(((D(today[a][1][mark])-p['price']) * p['size'] * p['multiplier'] * p['sign']
                                 for a, p in positions.items()), D(0))
        def close(asset, price, reason):
            nonlocal balance
            p = positions.pop(asset)
            exit_fee, exit_slippage, _ = costs(asset)
            out = price * (1-exit_slippage*p['sign'])
            pnl = (out-p['price'])*p['sign']*p['size']*p['multiplier'] - abs(out*p['size']*p['multiplier'])*exit_fee
            balance += pnl
            trades.append({'asset':asset, 'pnl_after_costs':str(pnl-p['entry_fee']-p['funding']), 'exit_date':date, 'reason':reason})
        # Charge an explicit conservative daily funding assumption to carried positions.
        for asset in list(positions):
            p, (i, row) = positions[asset], today[asset]
            charge = abs(D(row['o'])*p['size']*p['multiplier'])*costs(asset)[2]
            balance -= charge
            p['funding'] += charge
            opening = D(row['o'])
            gap = opening <= p['stop'] if p['sign']==1 else opening >= p['stop']
            if gap or exit_signal(strategy_bars(histories[asset][:i]), 'long' if p['sign']==1 else 'short'):
                close(asset, opening, 'gap_stop' if gap else 'ten_day_exit')
        current = equity('o')
        if current <= initial*D('.955'):
            for asset in list(positions): close(asset, D(today[asset][1]['o']), 'static_kill')
            failure = 'agent_static_kill'
            break
        if current > day_start*D('.98'):
            ranked = sorted(today, key=lambda a: (-D(histories[a][today[a][0]-1]['v'])*D(histories[a][today[a][0]-1]['c'])*D(markets[a]['multiplier']), a))
            for asset in ranked:
                if len(positions) >= 3 or asset in positions:
                    continue
                i, row = today[asset]
                prior = strategy_bars(histories[asset][:i])
                side = entry(prior)
                if not side:
                    continue
                market, sign = markets[asset], D(1) if side=='long' else D(-1)
                entry_cost, entry_slippage, _ = costs(asset)
                price, vol = D(row['o'])*(1+entry_slippage*sign), atr(prior)
                if side=='long' and price <= 2*vol:
                    continue
                gross = sum((abs(D(today[a][1]['o'])*p['size']*p['multiplier']) for a,p in positions.items()), D(0))
                size = quantity(initial, equity('o'), gross, price, vol, D(market['multiplier']), D(market['quantity_step']), quantity_floor(market))
                if not size or below_known_notional(market, price*size*D(market['multiplier'])):
                    continue
                entry_fee = price*size*D(market['multiplier'])*entry_cost
                balance -= entry_fee
                stop = rounded_price(price-2*vol*sign, market['sz_decimals'], side=='long')
                positions[asset] = dict(price=price,size=size,sign=sign,multiplier=D(market['multiplier']),stop=stop,entry_fee=entry_fee,funding=D(0))
                fills.append({'asset':asset,'date':date,'price':str(price),'size':str(size),'side':side})
        # Daily extremes do not establish whether stops or limit breaches happen first.
        worst = balance + sum(((D(today[a][1]['l'] if p['sign']==1 else today[a][1]['h'])-p['price'])*p['sign']*p['size']*p['multiplier'] for a,p in positions.items()), D(0))
        uncertain = worst <= day_start*D('.97') or worst <= initial*D('.94')
        for asset in list(positions):
            p, row = positions[asset], today[asset][1]
            touched = D(row['l']) <= p['stop'] if p['sign']==1 else D(row['h']) >= p['stop']
            if touched:
                close(asset, p['stop'], 'intraday_stop_proxy')
        current = equity('c')
        peak = max(peak,current)
        max_dd = max(max_dd,(peak-current)/peak)
        flat_days = flat_days+1 if not positions else 0
        longest_flat = max(longest_flat,flat_days)
        curve.append({'date_epoch_ms':date,'equity':str(current)})
        if current >= initial*D('1.10') and target_date is None: target_date=date
        if uncertain:
            failure='possible_intraday_breach_daily_data_cannot_resolve'
            break
        if current <= initial*D('.955'):
            failure='agent_static_kill_at_daily_close'
            break
    wins=[D(t['pnl_after_costs']) for t in trades if D(t['pnl_after_costs'])>0]
    losses=[D(t['pnl_after_costs']) for t in trades if D(t['pnl_after_costs'])<=0]
    unknown = unknown_minimums(markets.values())
    return {'curve':curve,'trades':trades,'entry_fills_proxy':fills,'closed_trades':len(trades),
            'unverified_order_minimums': unknown,
            'order_eligibility_limitation': 'Unknown broker minimums are not modeled; simulated fills may be rejected.' if unknown else None,
            'trades_per_market':{a:sum(t['asset']==a for t in trades) for a in markets},
            'win_rate':str(D(len(wins))/len(trades)) if trades else None,
            'average_win':str(sum(wins)/len(wins)) if wins else None,
            'average_loss':str(sum(losses)/len(losses)) if losses else None,
            'max_drawdown':str(max_dd),'longest_flat_days':longest_flat,
            'target_date_epoch_ms':target_date,
            'days_to_target': (target_date-curve[0]['date_epoch_ms'])//86400000 if target_date is not None and curve else None,
            'failure_or_uncertainty':failure,'open_positions_at_end':len(positions)}


def challenge_windows(histories, markets, **assumptions):
    """Full 90-calendar-day research scenarios, starting flat with prior history.

    Keep the entire selected universe and each instrument's actual inception date.
    New instruments become eligible after 60 prior bars; they do not truncate old
    instruments. Retain all prior bars for the same Wilder ATR seed as the main
    simulation. These scenarios cannot establish an actual challenge pass rate.
    """
    eligible = {a: int(rows[60]['t']) for a, rows in histories.items() if len(rows) > 60}
    if not eligible:
        return {'challenge_windows': [], 'window_denominator': 0, 'flagged_windows': 0,
                'partial_tail_days': 0, 'window_method': '90 UTC calendar days; 60 prior bars per market'}
    first = min(eligible.values())
    end = max(int(rows[-1]['t']) for rows in histories.values() if rows) + DAY
    span = 90 * DAY
    windows = []
    for start in range(first, end - span + 1, span):
        stop = start + span
        segment = {a: [r for r in rows if int(r['t']) < stop] for a, rows in histories.items()}
        coverage = {}
        for asset, rows in segment.items():
            begins = max(start, eligible.get(asset, stop))
            dates = {int(r['t']) for r in rows if begins <= int(r['t']) < stop}
            missing = len(set(range(begins, stop, DAY)) - dates)
            coverage[asset] = {'eligible_from_epoch_ms': begins if begins < stop else None,
                               'evaluation_bars': len(dates), 'missing_eligible_days': missing}
        result = simulate(segment, markets, start_at=start, **assumptions)
        incomplete = any(c['missing_eligible_days'] for c in coverage.values())
        windows.append({'start_epoch_ms': start, 'end_exclusive_epoch_ms': stop,
                        'calendar_days': 90, 'market_coverage': coverage,
                        'modeled_days': len(result['curve']),
                        'target_date_epoch_ms': result['target_date_epoch_ms'],
                        'closed_trades': result['closed_trades'],
                        'open_positions_at_end': result['open_positions_at_end'],
                        'failure_or_uncertainty': result['failure_or_uncertainty'] or
                            ('incomplete_market_history' if incomplete else None)})
    return {'challenge_windows': windows, 'window_denominator': len(windows),
            'flagged_windows': sum(w['failure_or_uncertainty'] is not None for w in windows),
            'partial_tail_days': (end - first) % span // DAY,
            'window_method': '90 UTC calendar days; 60 prior bars per market; all earlier bars retained; each window starts flat'}

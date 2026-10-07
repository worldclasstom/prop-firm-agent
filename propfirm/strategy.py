"""Deterministic daily-close strategy; inputs must be verified completed bars."""
from dataclasses import dataclass
from decimal import Decimal, ROUND_FLOOR, ROUND_CEILING
from typing import Literal

D = Decimal
Side = Literal['long', 'short']


def positive(*values: D) -> None:
    if any(not v.is_finite() or v <= 0 for v in values):
        raise ValueError('Expected finite positive values')


@dataclass(frozen=True)
class Bar:
    high: D
    low: D
    close: D

    def __post_init__(self):
        positive(self.high, self.low, self.close)
        if not self.low <= self.close <= self.high:
            raise ValueError('Invalid OHLC range')


def atr(bars: list[Bar]) -> D:
    """Seed ATR(20) with 20 true ranges; then (19 * previous_ATR + TR) / 20."""
    if len(bars) < 21:
        raise ValueError('ATR requires 21 bars including the previous close')
    ranges = [max(b.high-b.low, abs(b.high-a.close), abs(b.low-a.close))
              for a, b in zip(bars, bars[1:])]
    value = sum(ranges[:20], D(0)) / 20
    for tr in ranges[20:]:
        value = (19 * value + tr) / 20
    return value


def entry(bars: list[Bar]) -> Side | None:
    """Close above prior 20 highs is long; below prior 20 lows is short."""
    if len(bars) < 60:
        raise ValueError('Require at least 60 complete daily bars')
    prior, close = bars[-21:-1], bars[-1].close
    if close > max(b.high for b in prior):
        return 'long'
    if close < min(b.low for b in prior):
        return 'short'
    return None


def exit_signal(bars: list[Bar], side: Side) -> bool:
    """Exit long below prior 10 lows; exit short above prior 10 highs."""
    if side not in ('long', 'short') or len(bars) < 11:
        raise ValueError('Require a valid side and 11 completed bars')
    prior, close = bars[-11:-1], bars[-1].close
    return (close < min(b.low for b in prior) if side == 'long'
            else close > max(b.high for b in prior))


def quantity(start_balance: D, equity: D, gross_notional: D, price: D,
             volatility: D, multiplier: D, step: D, minimum: D) -> D:
    """Risk 0.4% of starting balance at 2 ATR; cap gross notional at 2x equity.

    multiplier must be verified quote-currency value per price point per unit.
    Portfolio slot count and currency conversions are the caller's responsibility.
    """
    positive(start_balance, equity, price, volatility, multiplier, step, minimum)
    if not gross_notional.is_finite() or gross_notional < 0:
        raise ValueError('Invalid existing gross notional')
    risk_size = start_balance * D('.004') / (2 * volatility * multiplier)
    exposure_size = max(D(0), 2 * equity - gross_notional) / (price * multiplier)
    rounded = (min(risk_size, exposure_size) / step).to_integral_value(rounding=ROUND_FLOOR) * step
    return rounded if rounded >= minimum else D(0)


def stop_price(fill: D, volatility: D, tick: D, side: Side) -> D:
    """Stop at 2 ATR from fill; round towards fill so risk is never widened."""
    positive(fill, volatility, tick)
    if side not in ('long', 'short'):
        raise ValueError('Invalid side')
    raw = fill - 2 * volatility if side == 'long' else fill + 2 * volatility
    result = (raw / tick).to_integral_value(
        rounding=ROUND_CEILING if side == 'long' else ROUND_FLOOR) * tick
    if result <= 0 or (side == 'long' and result >= fill) or (side == 'short' and result <= fill):
        raise ValueError('Stop cannot be represented at this tick size')
    return result

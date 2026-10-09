"""Known lower-bound filters, separate from risk/exposure upper bounds.

An explicit null is unknown, not zero and not evidence that no broker minimum
exists. Configuration permits this only under the trial broker-validation policy.
"""
from decimal import Decimal as D


def quantity_floor(market):
    value = market['minimum_quantity']
    # The smallest positive grid size is a sizing floor, NOT a broker minimum.
    return D(market['quantity_step'] if value is None else value)


def below_known_notional(market, notional):
    value = market['minimum_notional']
    return value is not None and notional < D(value)


def unknown_minimums(markets):
    return {m['asset']: [k for k in ('minimum_quantity', 'minimum_notional') if m[k] is None]
            for m in markets if m['minimum_quantity'] is None or m['minimum_notional'] is None}

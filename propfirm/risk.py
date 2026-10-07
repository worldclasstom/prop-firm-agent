"""Pure equity-limit decisions, separate from order execution."""
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal as D
from .strategy import positive


@dataclass(frozen=True)
class RiskState:
    daily_halt_date: str | None = None
    killed: bool = False


@dataclass(frozen=True)
class Decision:
    state: RiskState
    entries_allowed: bool
    cancel_entries: bool
    flatten_required: bool
    reason: str


def evaluate(state: RiskState, *, starting_balance: D, day_start_balance: D,
             equity: D, now: datetime, snapshot_at: datetime,
             monitor_healthy: bool, daily_scan: bool = False,
             max_age_seconds: int = 30) -> Decision:
    """Halt at 2% daily equity loss; latch kill at 4.5% static equity loss.

    Daily halts clear only at a daily scan on a later UTC date at/after 00:10.
    The caller must supply Propr's verified day-start reference for that date.
    """
    positive(starting_balance, day_start_balance)
    if not equity.is_finite() or now.tzinfo is None or snapshot_at.tzinfo is None:
        raise ValueError('Require finite equity and timezone-aware timestamps')
    if max_age_seconds <= 0:
        raise ValueError('Invalid freshness threshold')
    utc = now.astimezone(timezone.utc)
    date = utc.date().isoformat()
    # A kill latch remains actionable even when data becomes unavailable.
    killed = state.killed or equity <= starting_balance * D('.955')
    if killed:
        return Decision(RiskState(state.daily_halt_date, True), False, True, True, 'kill_latched')
    age = (now - snapshot_at).total_seconds()
    if age < 0 or age > max_age_seconds or not monitor_healthy:
        return Decision(state, False, True, False, 'stale_data_or_monitor')
    halted = state.daily_halt_date
    if halted and date > halted and daily_scan and (utc.hour, utc.minute) >= (0, 10):
        halted = None
    if equity <= day_start_balance * D('.98'):
        halted = date
    if halted:
        return Decision(RiskState(halted), False, True, False, 'daily_halt')
    return Decision(RiskState(), True, False, False, 'within_limits')

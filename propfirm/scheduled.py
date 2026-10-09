"""Scheduled execution: one idempotent tick per scheduler run, then exit.

This implements the documented revision in docs/SCHEDULED-EXECUTION.md. Between
ticks the only protection is the reduce-only stop resting at Propr for every
position; the tick confirms those stops before anything else. Trading rules,
sizing, halts and the shutdown protocol are the shared Engine, unchanged.
"""
import os
from datetime import datetime, timezone
from .config import runtime_ready, save_json
from .service import check_approval, exclusive
from . import __version__

EXIT_OK, EXIT_ERROR, EXIT_HALTED = 0, 2, 3


def scan_due(engine, now):
    """One scan per UTC date at/after 00:10, exactly as the continuous scheduler."""
    return engine.store.get('scheduled_date') != now.date().isoformat() and (now.hour, now.minute) >= (0, 10)


def run_tick(engine):
    root, config = engine.root, engine.config
    if config.get('execution_model', 'continuous') != 'scheduled':
        raise ValueError('tick requires execution_model "scheduled"; the continuous worker uses start')
    check_approval(root, config)
    runtime_error = None
    try:
        runtime_ready(root, config)
    except (ValueError, KeyError, FileNotFoundError) as error:
        # Expired or mismatched evidence with open exposure still needs reduction. Never resume entries.
        if not engine.store.all_intents() and not engine.store.kill_reason():
            raise
        runtime_error = type(error).__name__
    with exclusive(root):
        now = engine.clock()
        interval = config['tick_interval_minutes']
        previous = engine.store.get('last_tick')
        gap_minutes = None
        if previous:
            gap_minutes = (now - datetime.fromisoformat(previous)).total_seconds() / 60
            if gap_minutes > 2 * interval:
                # Stops rested at Propr meanwhile; the gap is disclosed, not hidden. Fresh reads follow.
                engine.report('schedule_gap', minutes=round(gap_minutes, 1), declared_interval=interval)
        if runtime_error:
            engine.store.latch_kill('runtime_reverification_required')
            engine.report('safety_only_recovery', reason=runtime_error)
        if (root / 'STOP').exists():
            engine.store.latch_kill('operator_stop')
        outcome, error_kind, scanned = 'ok', None, False
        try:
            if not engine.store.kill_reason():
                try:
                    engine.recover()
                except Exception as error:
                    engine.store.put('entry_block', 'recovery_requires_review')
                    engine.report('recovery_error', kind=type(error).__name__)
            engine.tick()
            if not engine.store.kill_reason() and scan_due(engine, now):
                try:
                    engine.scan()
                    engine.store.put('scheduled_date', now.date().isoformat())
                    scanned = True
                except Exception as error:
                    engine.store.put('entry_block', 'scan_error_requires_review')
                    engine.report('scan_error', kind=type(error).__name__)
                    outcome, error_kind = 'error', type(error).__name__
            if not scanned:
                engine.write_report()
        except Exception as error:
            # No raw exception data: it could include account responses or credentials.
            engine.report('tick_error', kind=type(error).__name__)
            outcome, error_kind = 'error', type(error).__name__
        engine.store.put('last_tick', now.isoformat())
        kill = engine.store.kill_reason()
        save_json(root / 'status.json', {
            'version': __version__, 'execution_model': 'scheduled', 'pid': os.getpid(),
            'at': now.isoformat(), 'account_id': config['account_id'],
            'tick_interval_minutes': interval, 'gap_minutes': None if gap_minutes is None else round(gap_minutes, 1),
            'outcome': outcome, 'error': error_kind, 'scanned': scanned,
            'scheduled_date': engine.store.get('scheduled_date'),
            'schedule': 'tick every %d minutes; one scan per UTC date at/after 00:10' % interval,
            'risk_heartbeat': engine.store.get('heartbeat'), 'last_scan': engine.store.get('last_scan'),
            'entry_block': engine.store.get('entry_block'), 'kill': kill,
            'shutdown_complete': engine.store.get('shutdown_complete', False),
            'protection_between_ticks': 'reduce-only stops resting at Propr; see docs/SCHEDULED-EXECUTION.md'})
        if kill:
            return EXIT_HALTED
        return EXIT_ERROR if outcome == 'error' else EXIT_OK

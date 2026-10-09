"""A continuous worker with a UTC daily scan; use a verified cloud supervisor."""
import contextlib
import fcntl
import json
import os
import signal
import threading
import time
from datetime import datetime, timezone
from .config import digest, read_json, runtime_ready, save_json
from . import __version__


@contextlib.contextmanager
def exclusive(root):
    root.mkdir(mode=0o700, parents=True, exist_ok=True)
    fd = os.open(root / 'worker.lock', os.O_CREAT | os.O_RDWR, 0o600)
    try:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise ValueError('Another worker holds this account-state lock') from None
        yield
    finally:
        os.close(fd)


def check_approval(root, config):
    """The approval binds the exact config digest, release and account mode; any change needs a fresh approval."""
    approval = read_json(root / 'approval.json')
    if approval.get('config_sha256') != digest(config) or approval.get('trading_authorized') is not True or approval.get('version') != __version__ or approval.get('account_mode') != config.get('account_mode', 'trial'):
        raise ValueError('Approve this verified account configuration before start')
    return approval


def serve(engine):
    root, config = engine.root, engine.config
    if config.get('execution_model', 'continuous') != 'continuous':
        raise ValueError('This configuration uses scheduled execution; run propfirm tick from the scheduler instead of start')
    check_approval(root, config)
    runtime_error = None
    try:
        runtime_ready(root, config)
    except (ValueError, KeyError, FileNotFoundError) as error:
        # Previously authorized exposure still needs reduction if runtime evidence
        # expires or the supervisor restarts on a changed host. Never resume entries.
        if not engine.store.all_intents() and not engine.store.kill_reason():
            raise
        runtime_error = type(error).__name__
    with exclusive(root):
        if runtime_error:
            engine.store.latch_kill('runtime_reverification_required')
            engine.report('safety_only_recovery', reason=runtime_error)
        quit_event = threading.Event()
        shutdown_requested = threading.Event()
        def handle_signal(_signum, _frame):
            shutdown_requested.set()  # SIGTERM performs verified-flat shutdown, not a blind exit.
        signal.signal(signal.SIGTERM, handle_signal)
        signal.signal(signal.SIGINT, handle_signal)
        def monitor():
            while not quit_event.is_set():
                with engine.lock:
                    try:
                        if shutdown_requested.is_set() or (root / 'STOP').exists():
                            engine.store.latch_kill('operator_stop')
                        engine.tick()
                        if engine.store.kill_reason() and engine.store.get('shutdown_complete'):
                            quit_event.set()
                    except Exception as error:
                        engine.healthy_at = None
                        engine.report('monitor_error', kind=type(error).__name__)
                        # No raw exception data (could include account responses or credentials).
                        # A failed read cannot authorize entries. Keep server stops and retry.
                quit_event.wait(5)
        with engine.lock:
            try:
                if not engine.store.kill_reason():
                    engine.recover()
            except Exception as error:
                engine.store.put('entry_block', 'recovery_requires_review')
                engine.report('recovery_error', kind=type(error).__name__)
        worker = threading.Thread(target=monitor, name='risk-monitor', daemon=False)
        worker.start()
        try:
            while not quit_event.wait(1):
                now = datetime.now(timezone.utc)
                with engine.lock:
                    last_scan = engine.store.get('scheduled_date')
                    if engine.store.kill_reason():
                        continue
                    healthy = engine.healthy_at and (now-engine.healthy_at).total_seconds() <= 30
                if healthy and (now.hour, now.minute) >= (0, 10) and last_scan != now.date().isoformat():
                    try:
                        # Public history fetching occurs outside the execution lock so the
                        # risk worker remains active during slow data requests.
                        engine.scan()
                        with engine.lock:
                            engine.store.put('scheduled_date', now.date().isoformat())
                    except Exception as error:
                        with engine.lock:
                            engine.store.put('entry_block', 'scan_error_requires_review')
                            engine.report('scan_error', kind=type(error).__name__)
                        quit_event.wait(5)
                with engine.lock:
                    save_json(root / 'status.json', {'version': __version__, 'pid': os.getpid(),
                              'at': now.isoformat(), 'account_id': config['account_id'],
                              'risk_heartbeat': engine.store.get('heartbeat'),
                              'last_scan': engine.store.get('last_scan'), 'schedule': '00:10 UTC daily; one catch-up scan on startup',
                              'entry_block': engine.store.get('entry_block'), 'kill': engine.store.kill_reason(),
                              'shutdown_complete': engine.store.get('shutdown_complete', False)})
        finally:
            # Unexpected scheduler errors must also latch a stop while the monitor remains alive.
            if not quit_event.is_set():
                shutdown_requested.set()
            worker.join()
            save_json(root / 'status.json', {'version': __version__, 'at': datetime.now(timezone.utc).isoformat(), 'account_id': config['account_id'], 'shutdown_complete': True, 'worker_stopped': True, 'kill': engine.store.kill_reason()})
            engine.report('worker_stopped', flat_confirmed=True)


def runtime_probe(root, seconds):
    """Harmless persistent heartbeat; no account key or trading endpoints."""
    if seconds < 1:
        raise ValueError('Probe seconds must be positive')
    begin = time.time()
    while time.time()-begin < seconds:
        save_json(root / 'runtime-probe.json', {'started_at_epoch': begin, 'heartbeat_at_epoch': time.time(),
                  'host_identity': os.environ.get('PROPFIRM_HOST_ID'), 'pid': os.getpid()})
        time.sleep(min(5, max(.1, seconds-(time.time()-begin))))

"""Private configuration, deterministic validation and runtime evidence."""
import hashlib
import json
import os
from datetime import datetime, timezone
from decimal import Decimal as D
from pathlib import Path


def root_dir():
    return Path(os.environ.get('PROPFIRM_HOME', '~/.prosperity-agent')).expanduser().resolve()


def read_json(path):
    return json.loads(Path(path).read_text())


def save_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    temporary = path.with_suffix(path.suffix + '.tmp')
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, 'w') as stream:
        json.dump(data, stream, indent=2, default=str, allow_nan=False)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def load_key(root):
    key = os.environ.get('PROPR_API_KEY')
    if key:
        return key
    path = root / '.env'
    if not path.exists():
        raise ValueError('Set PROPR_API_KEY in platform secrets or run propfirm credentials')
    if path.stat().st_mode & 0o077:
        raise ValueError('.env must be private (mode 0600)')
    for line in path.read_text().splitlines():
        if line.startswith('PROPR_API_KEY='):
            return line.split('=', 1)[1]
    raise ValueError('PROPR_API_KEY is missing from private .env')


def digest(config):
    return hashlib.sha256(json.dumps(config, sort_keys=True).encode()).hexdigest()


def validate_markets(config, *, trading=True):
    markets = config.get('markets', [])
    if not markets:
        raise ValueError('No verified markets configured. Complete instrument checks for the saved market selection; do not guess missing limits.')
    if len({m['asset'] for m in markets}) != len(markets):
        raise ValueError('Duplicate market identifiers in configured watchlist')
    for m in markets:
        if m['quote'] != 'USDC' or m.get('product_type') != 'perp':
            raise ValueError('This adapter supports verified USDC-settled linear perpetuals')
        for name in ('multiplier', 'quantity_step', 'minimum_quantity', 'minimum_notional'):
            n = D(m[name])
            if not n.is_finite() or n <= 0:
                raise ValueError('Invalid market numeric metadata')
        if not isinstance(m['sz_decimals'], int) or not 0 <= m['sz_decimals'] <= 6:
            raise ValueError('Invalid size precision')
        if D(m['quantity_step']) != D(10) ** -m['sz_decimals']:
            raise ValueError('Quantity step must match verified Hyperliquid size precision')
        if not m.get('evidence') or (trading and m.get('stop_supported') is not True):
            raise ValueError('Verify market metadata and stop support during setup' if trading
                             else 'Record market metadata sources and research assumptions')
        sessions = m.get('sessions_utc')
        if sessions != '24/7':
            if not isinstance(sessions, list) or not sessions:
                raise ValueError('Provide verified trading sessions or 24/7')
            for s in sessions:
                if s['weekday'] not in range(7) or not 0 <= s['start_minute'] < s['end_minute'] <= 1440:
                    raise ValueError('Invalid UTC trading session')
    return config


def validate_research(config):
    """Historical simulation needs market metadata, not broker credentials/approval."""
    validate_markets(config, trading=False)
    initial = D(str(config.get('backtest_initial_balance', '25000')))
    if not initial.is_finite() or initial <= 0:
        raise ValueError('backtest_initial_balance must be positive and finite')
    return config


def validate(config):
    if not isinstance(config.get('account_id'), str) or not config['account_id']:
        raise ValueError('Select an explicit free-trial account ID')
    environment_account = os.environ.get('CHALLENGE_ACCOUNT_ID')
    if environment_account and environment_account != config['account_id']:
        raise ValueError('CHALLENGE_ACCOUNT_ID must match the explicit configured account')
    if config.get('entry_order_type', 'limit') not in ('limit', 'market'):
        raise ValueError('entry_order_type must be limit or market')
    if config.get('account_mode', 'trial') not in ('trial', 'paid'):
        raise ValueError('Account mode must be trial or paid')
    validate_markets(config)
    if not config.get('account_mapping') or not config.get('mapping_evidence'):
        raise ValueError('Map actual Propr response fields using propfirm inspect and SETUP.md')
    return config


def runtime_ready(root, config):
    evidence = read_json(root / 'runtime.json')
    if evidence.get('config_sha256') != digest(config):
        raise ValueError('Runtime evidence does not match this configuration')
    for key in ('cloud_environment', 'persistent_storage', 'private_secrets', 'network_access',
                'background_execution', 'idle_recovery', 'supervisor'):
        check = evidence.get(key, {})
        if check.get('verified') is not True or not check.get('observation'):
            raise ValueError('Runtime requirement unverified: ' + key)
    if not evidence.get('host_identity') or evidence.get('host_identity') != os.environ.get('PROPFIRM_HOST_ID'):
        raise ValueError('Set PROPFIRM_HOST_ID to the verified cloud host identity')
    checked = datetime.fromisoformat(evidence['checked_at'].replace('Z', '+00:00'))
    age = (datetime.now(timezone.utc) - checked).total_seconds()
    if age < 0 or age > 7 * 86400:
        raise ValueError('Refresh cloud-runtime evidence (maximum age seven days at startup)')
    return evidence

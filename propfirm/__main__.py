"""Offline setup and status. Intentionally no live trading command yet."""
import argparse
import json
import os
from pathlib import Path
import sys
from . import __version__


def main():
    parser = argparse.ArgumentParser(description='Prosperity Labs Agent Kit development alpha')
    parser.add_argument('--version', action='version', version=__version__)
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('doctor', help='Report actual local prerequisites and unverified runtime requirements')
    init = sub.add_parser('init', help='Create private configuration outside the source checkout')
    init.add_argument('--directory', type=Path, default=Path.home() / '.prosperity-agent')
    sub.add_parser('start', help='Explain blockers; trading is unavailable in this alpha')
    args = parser.parse_args()
    if args.command == 'init':
        root = args.directory.expanduser().resolve()
        checkout = Path(__file__).resolve().parents[1]
        if root == checkout or checkout in root.parents:
            parser.error('Choose a private directory outside the source checkout')
        root.mkdir(mode=0o700, parents=True, exist_ok=True)
        path = root / 'config.json'
        config = {'schema_version': 1, 'account_id': '', 'markets': [], 'entry_order_type': 'limit', 'trading_enabled': False}
        try:
            fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        except FileExistsError:
            print('Existing configuration preserved.')
        else:
            with os.fdopen(fd, 'w') as f:
                json.dump(config, f, indent=2)
                f.write('\n')
            print('Created private configuration. No key requested; trading remains disabled.')
        return 0
    if args.command == 'doctor':
        print(json.dumps({'version': __version__, 'python': sys.version.split()[0],
            'python_supported': sys.version_info >= (3, 11), 'trading_available': False,
            'propr_connected': False, 'runtime': {key: 'unverified' for key in (
                'persistent_storage_after_task_end', 'private_secrets', 'propr_network_access',
                'daily_schedule', 'continuous_risk_worker', 'idle_recovery')},
            'next': 'Read STATUS.md and docs/SETUP.md. This command makes no network requests.'}, indent=2))
        return 0
    print('Trading is unavailable in this development alpha. See STATUS.md for integration and runtime blockers.', file=sys.stderr)
    return 2


if __name__ == '__main__':
    raise SystemExit(main())

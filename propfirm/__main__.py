"""Install, configure, verify and operate the free-trial trading service."""
import argparse
from datetime import datetime, timezone
import getpass
import json
import os
from pathlib import Path
import sys
from . import __version__
from .config import root_dir, read_json, save_json, load_key, digest, validate, validate_research, runtime_ready


def main():
    parser = argparse.ArgumentParser(description='Prosperity Labs Agent Kit')
    parser.add_argument('--version', action='version', version=__version__)
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('doctor', help='Report actual setup state and runtime blockers')
    init = sub.add_parser('init', help='Create private configuration outside the source checkout')
    init.add_argument('--directory', type=Path, default=root_dir())
    sub.add_parser('credentials', help='Save Propr key using hidden input, not a command argument')
    connect = sub.add_parser('connect', help='Open a private API-key form in the cloud computer browser')
    connect.add_argument('--port', type=int, default=0)
    connect.add_argument('--timeout', type=int, default=600)
    sub.add_parser('accounts', help='List Propr accounts for user selection; never select or trade')
    inspect = sub.add_parser('inspect', help='Read account documents into private setup files; never trade')
    inspect.add_argument('--account-id', required=True)
    discover = sub.add_parser('markets', help='Read public Hyperliquid market metadata')
    discover.add_argument('--dex', default='')
    sub.add_parser('verify', help='Validate config, account rules, trial proof, selected markets and history')
    backtest = sub.add_parser('backtest', help='Run historical research without broker credentials or trading approval')
    backtest.add_argument('--config', type=Path, help='Separate private research config; does not change live config')
    approve = sub.add_parser('approve-trial', help='Record authorization for the verified free-trial configuration')
    approve.add_argument('--account-id', required=True)
    paid = sub.add_parser('approve-paid', help='Separate explicit paid-account opt-in')
    paid.add_argument('--account-id', required=True)
    paid.add_argument('--acknowledge-paid-risk', action='store_true', required=True)
    reset = sub.add_parser('reset-halt', help='Explicit manual reset, only after verified flat')
    reset.add_argument('--account-id', required=True)
    reset.add_argument('--confirm-flat', action='store_true', required=True)
    sub.add_parser('start', help='Run the daily trading service and risk monitor in the foreground')
    sub.add_parser('status', help='Show worker status, with heartbeat freshness')
    sub.add_parser('stop', help='Request verified-flat shutdown from the running worker')
    sub.add_parser('resume-entries', help='Clear an entry block only after account/order reconciliation')
    probe = sub.add_parser('runtime-probe', help='Harmless cloud heartbeat, no trading')
    probe.add_argument('--seconds', type=int, default=600)
    update = sub.add_parser('prepare-update', help='Clone and test a requested release without changing a running worker')
    update.add_argument('--version', required=True)
    sub.add_parser('check-update', help='Read available GitHub releases; never update a running worker')
    args = parser.parse_args()
    root = root_dir()
    if args.command == 'connect':
        from .connect import serve_connect
        return serve_connect(root, args.port, args.timeout)
    if args.command == 'init':
        root = args.directory.expanduser().resolve()
        checkout = Path(__file__).resolve().parents[1]
        if root == checkout or checkout in root.parents:
            parser.error('Choose a private directory outside the source checkout')
        root.mkdir(mode=0o700, parents=True, exist_ok=True)
        path = root / 'config.json'
        if path.exists():
            print('Existing configuration preserved.')
        else:
            save_json(path, {'schema_version': 2, 'account_id': '', 'markets': [], 'entry_order_type': 'limit',
                            'account_mapping': {}, 'mapping_evidence': '', 'trading_enabled': False})
            print('Created private configuration. Trading remains disabled until verification and trial approval.')
        return 0
    if args.command == 'credentials':
        from .connect import save_key
        key = getpass.getpass('Propr API key (hidden): ').strip()
        save_key(root, key)
        print('Key saved privately. It was not sent to GitHub or written into a report.')
        return 0
    if args.command == 'doctor':
        blockers = []
        try:
            config = validate(read_json(root / 'config.json'))
        except (ValueError, KeyError, FileNotFoundError):
            config = None
            blockers.append('Complete private config.json using SETUP.md')
        if config:
            try:
                runtime_ready(root, config)
            except (ValueError, KeyError, FileNotFoundError):
                blockers.append('Cloud runtime evidence is incomplete, stale or belongs to another host/config')
        print(json.dumps({'version': __version__, 'python': sys.version.split()[0],
            'execution_implemented': True, 'ready_to_verify': not blockers, 'trading_available': False, 'blockers': blockers,
            'runtime': {key: 'unverified' for key in ('persistent_storage_after_task_end', 'background_execution')}
            if blockers else {'evidence': 'recorded; run verify for fresh account checks'},
            'next': 'Follow docs/SETUP.md. doctor does not start trading.'}, indent=2))
        return 0
    if args.command == 'runtime-probe':
        from .service import runtime_probe
        runtime_probe(root, args.seconds)
        return 0
    if args.command == 'prepare-update':
        from .updates import prepare
        target = prepare(root, args.version)
        print('Prepared and tested ' + str(target) + '. No running worker was changed. Follow docs/UPDATES.md before switching.')
        return 0
    if args.command == 'check-update':
        from urllib.request import Request, urlopen
        req = Request('https://api.github.com/repos/worldclasstom/prop-firm-agent/releases',
                      headers={'User-Agent': 'ProsperityAgentKit'})
        with urlopen(req, timeout=10) as response:
            releases = json.load(response)
        print(json.dumps({'installed': __version__, 'available': [
              {'version': r['tag_name'], 'prerelease': r['prerelease'], 'notes': r['html_url']}
              for r in releases if not r['draft']][:5], 'action': 'Review release notes. No update was applied.'}, indent=2))
        return 0
    if args.command == 'status':
        value = read_json(root / 'status.json')
        timestamp = datetime.fromisoformat(value['at'])
        value['worker_status_stale'] = (datetime.now(timezone.utc)-timestamp).total_seconds() > 30
        print(json.dumps(value, indent=2))
        return 0
    if args.command == 'stop':
        root.mkdir(mode=0o700, parents=True, exist_ok=True)
        (root / 'STOP').touch(mode=0o600)
        if (root / 'state.sqlite').exists():
            from .state import Store
            store = Store(root / 'state.sqlite')
            store.put('operator_stop', True)
            store.close()
        print('Shutdown requested. Run status and check Propr. This request alone does not confirm positions are closed.')
        return 0
    if args.command == 'accounts':
        from .propr import ReadOnlyClient
        from .discovery import discover_accounts
        documents, summary = discover_accounts(ReadOnlyClient(load_key(root)))
        save_json(root / 'setup' / 'account-discovery.json', documents)
        print(json.dumps(summary, indent=2))
        return 0
    from .data import Data
    data = Data(root)
    if args.command == 'markets':
        print(json.dumps(data.discover(args.dex), indent=2))
        return 0
    from .propr import Client
    from .account import select_documents, snapshot
    if args.command == 'inspect':
        from .account import inspection_report
        client = Client(load_key(root), args.account_id)
        documents = select_documents(client, include_daily=True)
        save_json(root / 'setup' / 'account-inspection.json', documents)
        report = inspection_report(documents, args.account_id)
        save_json(root / 'setup' / 'account-mapping.json', report)
        print(json.dumps(report, indent=2))
        return 0
    if args.command == 'backtest':
        config = validate_research(read_json(args.config or root / 'config.json'))
        from .backtest import simulate
        markets = {m['asset']: m for m in config['markets']}
        histories = {a: data.candles(m) for a,m in markets.items()}
        costs = config.get('backtest_costs', {})
        from decimal import Decimal as D
        initial = D(str(config.get('backtest_initial_balance', '25000')))
        result = simulate(histories, markets, initial=initial, fee=D(costs.get('fee_per_side', '.00075')),
                          slippage=D(costs.get('slippage_per_side', '.0005')),
                          funding=D(costs.get('daily_funding_cost', '.0001')))
        windows = []
        length = min(len(rows) for rows in histories.values())
        # Non-overlapping 90-day test windows, each with its own preceding 60-bar warmup.
        for start in range(60, length-29, 90):
            segment = {a: rows[-length:][start-60:min(start+90, length)] for a, rows in histories.items()}
            window = simulate(segment, markets, initial=initial, fee=D(costs.get('fee_per_side', '.00075')),
                              slippage=D(costs.get('slippage_per_side', '.0005')),
                              funding=D(costs.get('daily_funding_cost', '.0001')))
            windows.append({'start_index': start, 'failure_or_uncertainty': window['failure_or_uncertainty']})
        result['challenge_windows'] = windows
        result['flagged_windows'] = sum(w['failure_or_uncertainty'] is not None for w in windows)
        result['window_denominator'] = len(windows)
        result['history_bars'] = {a: len(rows) for a, rows in histories.items()}
        result['version'] = __version__
        result['research_only'] = True
        result['account_verified'] = False
        result['initial_balance_assumption'] = str(initial)
        result['market_metadata'] = config['markets']
        result['assumptions'] = {'fee_per_side': costs.get('fee_per_side', '.00075'),
                               'slippage_per_side': costs.get('slippage_per_side', '.0005'),
                               'daily_funding_cost': costs.get('daily_funding_cost', '.0001')}
        save_json(root / 'reports' / 'backtest.json', result)
        note = ('# Daily-data scenario report\n\nThis is a next-bar-open execution proxy. It does not reconstruct IOC fills, '
                'queue position or intraday event order. It cannot establish whether limit or market entries perform better. '
                'Costs and funding are explicit assumptions; replace them with instrument-specific verified values for research. '
                'Possible intraday breaches are conservative flags, not observed challenge failures. A target touch does not prove a pass.\n\n'
                '```json\n' + json.dumps(result, indent=2) + '\n```\n')
        path = root / 'reports' / 'backtest.md'
        path.write_text(note)
        path.chmod(0o600)
        print('Saved reports/backtest.md and backtest.json in the private kit directory.')
        return 0
    config = validate(read_json(root / 'config.json'))
    client = Client(load_key(root), config['account_id'])
    if args.command in ('verify', 'approve-trial', 'approve-paid'):
        if config.get('account_adapter') == 'propr-v1':
            from dataclasses import replace
            from .live_marks import LiveMarks
            marks = LiveMarks(client.api_key, client.account_id)
            try:
                revision = marks.revision()
                documents = select_documents(client, include_daily=True)
                snap = snapshot(documents, config)
                snap = replace(snap, equity=marks.equity(documents['account'], client.positions(), revision))
            finally:
                marks.close()
        else:
            snap = snapshot(select_documents(client), config)
        save_json(root / 'markets.json', config['markets'])
        for market in config['markets']:
            client.margin(market['asset'])
            meta = data.discover(market['asset'].split(':')[0] if ':' in market['asset'] else '')
            rows = [m for m in meta['universe'] if m['name'] == market['asset']]
            if len(rows) != 1 or rows[0]['szDecimals'] != market['sz_decimals'] or rows[0].get('isDelisted'):
                raise ValueError('Market metadata no longer matches the configured instrument')
            data.candles(market)
        if args.command in ('approve-trial', 'approve-paid'):
            runtime_ready(root, config)
            expected_mode = 'trial' if args.command == 'approve-trial' else 'paid'
            if config.get('account_mode', 'trial') != expected_mode:
                raise ValueError('Use the separate approval command for this account mode')
            if args.account_id != config['account_id']:
                raise ValueError('Approval account does not match configuration')
            if client.positions() or any(o['status'] not in ('filled','cancelled','canceled','expired','rejected') for o in client.orders()):
                raise ValueError('First activation requires an empty dedicated trial account')
            save_json(root / 'approval.json', {'account_id': config['account_id'], 'config_sha256': digest(config),
                      'trading_authorized': True, 'account_mode': expected_mode, 'version': __version__, 'at': datetime.now(timezone.utc).isoformat()})
            print('Verified ' + expected_mode + ' account approved. Start through the verified cloud supervisor.')
        else:
            print(json.dumps({'account_id': config['account_id'], 'type': 'verified_' + config.get('account_mode', 'trial'),
                              'starting_balance': str(snap.starting_balance), 'markets': len(config['markets'])}))
        return 0
    from .engine import Engine
    engine = Engine(client, data, config, root)
    try:
        from .service import serve, exclusive
        if args.command == 'reset-halt':
            with exclusive(root), engine.lock:
                if args.account_id != config['account_id'] or client.positions() or any(o['status'] not in ('filled','cancelled','canceled','expired','rejected') for o in client.orders()):
                    raise ValueError('Cannot reset until this account is confirmed flat with no active orders')
                engine.account()
                with engine.store.db:
                    engine.store.db.execute("DELETE FROM flags WHERE key IN ('kill','operator_stop','entry_block','shutdown_complete')")
                (root / 'STOP').unlink(missing_ok=True)
                engine.report('manual_halt_reset')
            print('Halt manually reset after flat confirmation. No worker was started.')
            return 0
        if args.command == 'resume-entries':
            with exclusive(root), engine.lock:
                if engine.store.kill_reason():
                    raise ValueError('Kill remains latched; manual review and reset required')
                engine.recover()
                orders = client.orders()
                if any(not any(o.get('intentId') == p['intentId'] for o in orders) for k,p in engine.store.all_intents() if k.startswith('entry:')):
                    raise ValueError('Unresolved entry intent remains')
                engine.tick()
                if engine.store.kill_reason():
                    raise ValueError('Risk checks latched a kill; entries remain blocked')
                engine.store.put('entry_block', None)
            print('Entry block cleared after reconciliation. Existing daily halt still applies.')
            return 0
        serve(engine)
        return 0
    finally:
        if engine.live_marks:
            engine.live_marks.close()
        engine.store.close()


def entrypoint():
    try:
        return main()
    except (ValueError, KeyError, FileNotFoundError) as error:
        # Configuration errors never embed credential input or API response bodies.
        print('Setup or runtime check failed: ' + str(error), file=sys.stderr)
        return 2
    except Exception as error:
        print('Operation failed (' + type(error).__name__ + '). Check connectivity and private setup; no success is implied.', file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(entrypoint())

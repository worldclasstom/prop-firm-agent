"""Bind observed API fields explicitly; never infer trial status from names."""
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal as D
from .strategy import positive


def resolve(documents, mapping):
    value = documents[mapping['source']]
    for key in mapping['path']:
        value = value[key]
    return value


def number(documents, mapping):
    value = D(str(resolve(documents, mapping)))
    if not value.is_finite():
        raise ValueError('Non-finite account value')
    return value


@dataclass(frozen=True)
class Snapshot:
    starting_balance: D
    day_start_balance: D
    balance: D
    equity: D
    observed_at: datetime
    day: str


def select_documents(client):
    matches = [a for a in client.attempts() if a.get('accountId') == client.account_id]
    if len(matches) != 1:
        raise ValueError('The selected account does not have exactly one challenge attempt')
    attempt = matches[0]
    challenges = [c for c in client.challenges() if c.get('challengeId') == attempt.get('challengeId')]
    return {'account': client.account(), 'attempt': attempt,
            'challenge': challenges[0] if len(challenges) == 1 else {}}


def snapshot(documents, config, now=None):
    now = now or datetime.now(timezone.utc)
    mapping = config['account_mapping']
    attempt = documents['attempt']
    if attempt.get('accountId') != config['account_id'] or attempt.get('status') != 'active':
        raise ValueError('Selected account must be active and match the verified attempt')
    proof = mapping['trial']
    mode = config.get('account_mode', 'trial')
    expected = proof['equals']
    if mode == 'trial':
        valid = expected is True or str(expected).lower() in ('trial', 'free_trial', 'free trial')
    else:
        valid = expected is False or str(expected).lower() in ('paid', 'evaluation', 'challenge')
    if not valid:
        raise ValueError('Account proof must explicitly identify the selected trial/paid mode')
    observed = resolve(documents, proof)
    if type(observed) is not type(expected) or observed != expected:
        raise ValueError('Propr response does not confirm the selected account mode')
    # The mapping must point at a semantic type/trial field, not an account name or balance.
    if not any(any(term in str(k).lower() for term in ('trial', 'type', 'mode')) for k in proof['path']):
        raise ValueError('Trial evidence must be an explicit API type or trial field')
    starting = number(documents, mapping['starting_balance'])
    day_start = number(documents, mapping['day_start_balance'])
    positive(starting, day_start)
    day = str(resolve(documents, mapping['day_reference']))[:10]
    if day != now.astimezone(timezone.utc).date().isoformat():
        raise ValueError('Propr day-start reference has not reset for the current UTC day')
    for key, expected in (('daily_loss_fraction', D('.03')), ('max_drawdown_fraction', D('.06')), ('profit_target_fraction', D('.10'))):
        value = number(documents, mapping[key]) * D(str(mapping[key].get('scale', 1)))
        if value != expected:
            raise ValueError('Account rules differ from Classic one-step: ' + key)
    drawdown = mapping['drawdown_type']
    if resolve(documents, drawdown) != drawdown['equals'] or str(drawdown['equals']).lower() != 'static':
        raise ValueError('Account must use static maximum drawdown')
    balance = number(documents, mapping['balance'])
    if 'equity' in mapping:
        equity = number(documents, mapping['equity'])
    else:
        # Official SDK formula; the chosen mapping is recorded during setup.
        equity = balance + number(documents, mapping['unrealized_pnl']) + number(documents, mapping['isolated_position_margin'])
    return Snapshot(starting, day_start, balance, equity, now, day)

"""Bind observed API fields explicitly; never infer trial status from names."""
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal as D, InvalidOperation
from .strategy import positive


def resolve(documents, mapping):
    value = documents[mapping['source']]
    for key in mapping['path']:
        value = value[key]
    return value


def number(documents, mapping):
    try:
        value = D(str(resolve(documents, mapping)))
    except InvalidOperation:
        raise ValueError('Invalid account numeric value') from None
    if not value.is_finite():
        raise ValueError('Non-finite account value')
    return value


#: Propr's Classic one-step rules, the defaults for configurations that pin none (release 0.2.0b9 and earlier).
CLASSIC_RULES = {'daily_loss_fraction': D('.03'), 'max_drawdown_fraction': D('.06'), 'profit_target_fraction': D('.10')}


def challenge_rules(config):
    """The limits the configuration was verified for, as fractions; Classic when none were pinned.

    Any product with a static maximum drawdown is supported (Propr's Classic,
    Turbo and Pro at any size). A trailing drawdown is refused: its floor
    moves with the account's high-water mark by a rule the provider defines,
    and nothing here computes one.
    """
    pinned = config.get('challenge_rules')
    if not pinned:
        return dict(CLASSIC_RULES)
    if not isinstance(pinned, dict):
        raise ValueError('challenge_rules must be an object')
    rules = {}
    for key in CLASSIC_RULES:
        try:
            value = D(str(pinned[key]))
        except (KeyError, TypeError, InvalidOperation):
            raise ValueError('challenge_rules must pin ' + key) from None
        if not value.is_finite() or not 0 < value < 1:
            raise ValueError('challenge_rules ' + key + ' must be a fraction between 0 and 1')
        rules[key] = value
    if str(pinned.get('drawdown_type', 'static')).lower() != 'static':
        raise ValueError('Only a static maximum drawdown is supported')
    return rules


@dataclass(frozen=True)
class Snapshot:
    starting_balance: D
    day_start_balance: D
    balance: D
    equity: D
    observed_at: datetime
    day: str
    daily_loss_fraction: D = CLASSIC_RULES['daily_loss_fraction']
    max_drawdown_fraction: D = CLASSIC_RULES['max_drawdown_fraction']
    profit_target_fraction: D = CLASSIC_RULES['profit_target_fraction']


def select_documents(client, *, include_daily=False):
    matches = [a for a in client.attempts() if a.get('accountId') == client.account_id]
    if len(matches) != 1:
        raise ValueError('The selected account does not have exactly one challenge attempt')
    listed = matches[0]
    attempt = client.attempt(listed['attemptId'])
    if any(not listed.get(key) or attempt.get(key) != listed[key]
           for key in ('attemptId', 'accountId', 'challengeId')):
        raise ValueError('Challenge attempt details do not match the selected account')
    challenges = [c for c in client.challenges() if c.get('challengeId') == attempt.get('challengeId')]
    if len(challenges) != 1:
        raise ValueError('The selected attempt does not have exactly one linked challenge')
    account = client.account()
    if account.get('accountId') != client.account_id:
        raise ValueError('Account response does not match the selected account')
    documents = {'account': account, 'attempt': attempt, 'challenge': challenges[0]}
    if include_daily:
        documents['daily_metrics'] = client.daily_metrics()
    return documents


def propr_mapping(documents, account_id):
    """Bind the observed Propr schema using IDs, never phase array positions.

    This intentionally supplies no invented trial flag or daily reference. Those
    still need explicit provider evidence. Each runtime read repeats the joins.
    """
    account, attempt, challenge = (documents[k] for k in ('account', 'attempt', 'challenge'))
    if (not account_id or account.get('accountId') != account_id or
            attempt.get('accountId') != account_id or attempt.get('status') != 'active' or
            not attempt.get('attemptId') or
            account.get('challengeAttemptId') != attempt['attemptId'] or
            not challenge.get('challengeId') or
            account.get('challengeId') != challenge['challengeId'] or
            attempt.get('challengeId') != challenge['challengeId']):
        raise ValueError('Account, active attempt and challenge identity links must agree')
    if (account.get('currency') != 'USDC' or challenge.get('currency') != 'USDC' or
            account.get('exchange') != 'hyperliquid' or challenge.get('exchange') != 'hyperliquid' or
            account.get('closedAt') is not None or account.get('deletedAt') is not None or
            challenge.get('deletedAt') is not None or challenge.get('isActive') is not True):
        raise ValueError('Expected an active Hyperliquid USDC account and challenge')
    current = attempt.get('currentPhaseId')
    phases = [(i, p) for i, p in enumerate(attempt.get('phases', []))
              if current and p.get('attemptPhaseId') == current]
    if len(phases) != 1:
        raise ValueError('Current attempt phase must resolve uniquely by attemptPhaseId')
    ai, active = phases[0]
    if (active.get('attemptId') != attempt['attemptId'] or active.get('status') != 'active' or
            not active.get('phaseId') or active.get('endedAt') is not None):
        raise ValueError('Current attempt phase is inactive or has inconsistent identity')
    rules = [(i, p) for i, p in enumerate(challenge.get('phases', []))
             if p.get('phaseId') == active['phaseId']]
    if len(rules) != 1:
        raise ValueError('Current challenge rules must resolve uniquely by phaseId')
    ci, rule = rules[0]
    if rule.get('challengeId') != challenge['challengeId'] or rule.get('deletedAt') is not None:
        raise ValueError('Current phase rules have inconsistent challenge identity')
    def field(source, *path, **extra):
        return {'source': source, 'path': list(path), **extra}
    mapping = {
        'starting_balance': field('attempt', 'phases', ai, 'startingBalance'),
        'balance': field('account', 'balance'),
        'unrealized_pnl': field('account', 'totalUnrealizedPnl'),
        'isolated_position_margin': field('account', 'isolatedPositionMargin'),
        'drawdown_type': field('challenge', 'phases', ci, 'drawdownType', equals='static'),
    }
    # The product's own limits, read from the current phase's rules and checked for sense here;
    # snapshot() holds them to the limits the configuration was verified for.
    for key, provider in (('daily_loss_fraction', 'maxDailyLossPercent'),
                          ('max_drawdown_fraction', 'maxDrawdownPercent'),
                          ('profit_target_fraction', 'profitTargetPercent')):
        mapping[key] = field('challenge', 'phases', ci, provider, scale='0.01')
        value = number(documents, mapping[key]) * D('.01')
        if not 0 < value < 1:
            raise ValueError('Account rule out of range: ' + key)
    positive(number(documents, mapping['starting_balance']))
    for key in ('balance', 'unrealized_pnl', 'isolated_position_margin'):
        number(documents, mapping[key])
    if resolve(documents, mapping['drawdown_type']) != 'static':
        raise ValueError('Account must use static maximum drawdown')
    return mapping


def catalog_trial(documents, account_id):
    """Composite API evidence: linked paper account and zero-price trial product.

    Never accept the display name or paper type alone. This is a deliberately
    narrow adapter for the observed catalog shape, not a provider guarantee.
    """
    propr_mapping(documents, account_id)
    account, challenge = documents['account'], documents['challenge']
    if account.get('type') != 'paper' or challenge.get('slug') != 'free-trial':
        raise ValueError('The linked account/catalog does not identify the free trial')
    product = challenge.get('product', {})
    if (not challenge.get('productId') or product.get('productId') != challenge['productId'] or
            product.get('deletedAt') is not None):
        raise ValueError('Free-trial product identity could not be verified')
    prices = [p for p in product.get('prices', [])
              if p.get('isActive') is True and p.get('deletedAt') is None]
    if not prices or any(p.get('productId') != product['productId'] or
                         p.get('billingPeriod') != 'one_time' or
                         number({'price': p}, {'source': 'price', 'path': ['price']}) != 0 for p in prices):
        raise ValueError('The linked free-trial product must have only active zero-price offers')
    return True


def catalog_paid(documents, account_id):
    """Composite API evidence for a paid challenge: a linked catalog product that is not the free trial.

    The mirror of catalog_trial for the observed catalog shape: the same
    identity links, under a slug other than free-trial. What the trader paid
    for the attempt is not read; a challenge Propr gives away is still a
    paid product with its fee at stake. Never the display name alone, and
    not a provider guarantee.
    """
    propr_mapping(documents, account_id)
    challenge = documents['challenge']
    slug = challenge.get('slug')
    if not isinstance(slug, str) or not slug or slug == 'free-trial':
        raise ValueError('The linked catalog entry does not identify a paid challenge')
    product = challenge.get('product', {})
    if (not challenge.get('productId') or product.get('productId') != challenge['productId'] or
            product.get('deletedAt') is not None):
        raise ValueError('Paid-challenge product identity could not be verified')
    return True


def daily_reference(documents, config, now):
    """Select today's server row using paths verified from the live response.

    The docs establish startingBalance + startingIsolatedPositionMargin, but do
    not publish the response envelope/date key. Setup records those actual paths.
    """
    binding = config.get('daily_metrics_binding')
    if not binding or not binding.get('date_path') or not binding.get('evidence'):
        raise ValueError('Inspect daily-metrics and bind its actual date field and response envelope')
    def at(value, path):
        for key in path:
            value = value[key]
        return value
    rows = at(documents['daily_metrics'], binding['rows_path'])
    if isinstance(rows, dict):
        rows = [rows]
    if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
        raise ValueError('Unrecognized daily-metrics response envelope')
    today = now.astimezone(timezone.utc).date().isoformat()
    def day(row):
        value = at(row, binding['date_path'])
        if not isinstance(value, str):
            raise ValueError('Expected an observed ISO UTC daily-metrics date')
        if len(value) == 10:
            return datetime.strptime(value, '%Y-%m-%d').date().isoformat()
        stamp = datetime.fromisoformat(value.replace('Z', '+00:00'))
        if stamp.tzinfo is None or stamp.utcoffset().total_seconds() != 0:
            raise ValueError('Daily-metrics reference must identify a UTC day')
        return stamp.date().isoformat()
    matches = [row for row in rows if day(row) == today]
    if len(matches) != 1:
        raise ValueError('Daily-metrics must contain exactly one current UTC reference')
    row = matches[0]
    if 'accountId' in row and row['accountId'] != config['account_id']:
        raise ValueError('Daily-metrics belongs to a different account')
    balance, margin = (number({'row': row}, {'source': 'row', 'path': [key]})
                       for key in ('startingBalance', 'startingIsolatedPositionMargin'))
    if not balance.is_finite() or not margin.is_finite() or margin < 0:
        raise ValueError('Invalid daily-metrics opening values')
    base = balance + margin
    positive(base)
    return base, today


def inspection_report(documents, account_id):
    mapping = propr_mapping(documents, account_id)
    try:
        catalog_trial(documents, account_id)
        trial = True
    except (ValueError, KeyError, TypeError):
        trial = False
    try:
        paid = catalog_paid(documents, account_id)
    except (ValueError, KeyError, TypeError):
        paid = False
    return {
        'account_id': account_id, 'adapter': 'propr-v1',
        'account_mapping': mapping,
        'mapping_evidence': 'Propr authenticated account/attempt/challenge ID joins; '
                            'percent fields scaled by 0.01; official Python SDK equity formula.',
        'mapped_fields': sorted(mapping),
        'trial_catalog_verified': trial,
        'paid_catalog_verified': paid,
        'daily_metrics_received': 'daily_metrics' in documents,
        'missing_fields': ([] if trial or paid else ['trial']) + ['daily_metrics_binding'],
        'trading_ready': False,
        'next': 'Inspect the saved daily_metrics response; record its actual rows_path and date_path '
                'in daily_metrics_binding, with source evidence. The documented daily-loss base is '
                'startingBalance + startingIsolatedPositionMargin. Do not use current balance or updatedAt. '
                'Market and runtime verification are separate checks.',
    }


def snapshot(documents, config, now=None):
    now = now or datetime.now(timezone.utc)
    mapping = dict(config['account_mapping'])
    adapter = config.get('account_adapter')
    if adapter == 'propr-v1':
        mapping.update(propr_mapping(documents, config['account_id']))
        mapping.pop('equity', None)
    elif adapter is not None:
        raise ValueError('Unsupported account adapter')
    attempt = documents['attempt']
    if attempt.get('accountId') != config['account_id'] or attempt.get('status') != 'active':
        raise ValueError('Selected account must be active and match the verified attempt')
    mode = config.get('account_mode', 'trial')
    if adapter == 'propr-v1' and mode == 'trial':
        catalog_trial(documents, config['account_id'])
    elif adapter == 'propr-v1' and mode == 'paid':
        # The paid mirror of the trial check: priced catalog product, non-trial slug.
        catalog_paid(documents, config['account_id'])
    else:
        proof = mapping['trial']
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
        if not any(any(term in str(k).lower() for term in ('trial', 'type', 'mode')) for k in proof['path']):
            raise ValueError('Trial evidence must be an explicit API type or trial field')
    starting = number(documents, mapping['starting_balance'])
    if adapter == 'propr-v1':
        day_start, day = daily_reference(documents, config, now)
    elif 'day_start_balance' in mapping:
        day_start = number(documents, mapping['day_start_balance'])
    elif 'daily_loss_floor' in mapping:
        # The provider's dated daily floor is equivalent under the verified 3% rule.
        day_start = number(documents, mapping['daily_loss_floor']) / D('.97')
    else:
        raise ValueError('Missing provider day-start balance or dated daily-loss floor')
    positive(starting, day_start)
    if adapter != 'propr-v1':
        day = str(resolve(documents, mapping['day_reference']))[:10]
    if day != now.astimezone(timezone.utc).date().isoformat():
        raise ValueError('Propr day-start reference has not reset for the current UTC day')
    verified = challenge_rules(config)
    fractions = {}
    for key, expected in verified.items():
        value = number(documents, mapping[key]) * D(str(mapping[key].get('scale', 1)))
        if value != expected:
            raise ValueError('Account rules differ from the verified configuration: ' + key)
        fractions[key] = value
    drawdown = mapping['drawdown_type']
    if resolve(documents, drawdown) != drawdown['equals'] or str(drawdown['equals']).lower() != 'static':
        raise ValueError('Account must use static maximum drawdown')
    balance = number(documents, mapping['balance'])
    if 'equity' in mapping:
        equity = number(documents, mapping['equity'])
    else:
        # Official SDK formula; the chosen mapping is recorded during setup.
        equity = balance + number(documents, mapping['unrealized_pnl']) + number(documents, mapping['isolated_position_margin'])
    return Snapshot(starting, day_start, balance, equity, now, day, fractions['daily_loss_fraction'],
                    fractions['max_drawdown_fraction'], fractions['profit_target_fraction'])

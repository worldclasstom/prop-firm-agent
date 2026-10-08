"""Read account choices without selecting, approving or reconfiguring a trader."""


def discover_accounts(client):
    attempts = client.attempts()
    challenges = client.challenges() if attempts else []
    if any(not isinstance(row, dict) for row in attempts + challenges):
        raise ValueError('Unrecognized account discovery response')
    accounts = {}
    missing_ids = 0
    for attempt in attempts:
        account_id = attempt.get('accountId')
        if not isinstance(account_id, str) or not account_id.strip():
            missing_ids += 1
            continue
        choice = accounts.setdefault(account_id, {
            'account_id': account_id, 'account_type': 'unverified', 'attempts': []})
        linked = [c for c in challenges if c.get('challengeId') is not None
                  and c.get('challengeId') == attempt.get('challengeId')]
        challenge = linked[0] if len(linked) == 1 else {}
        choice['attempts'].append({
            'attempt_id': attempt.get('attemptId'),
            'status': attempt.get('status', 'unknown'),
            'challenge_id': attempt.get('challengeId'),
            'challenge_name': challenge.get('name'),
        })
    summary = {
        'accounts': list(accounts.values()),
        'attempts_without_account_id': missing_ids,
        'selection_required': True,
        'next': ('Show these accounts to the user and ask which one to inspect. '
                 'Active status and challenge names do not prove free-trial eligibility. '
                 'Reuse an already explicit selection only after matching its exact ID.')
                if accounts else
                ('No selectable account IDs were returned. Check the saved key access and '
                 'whether a Free Trial has been created in Propr; then retry. Do not buy a challenge.'),
    }
    return {'attempts': attempts, 'challenges': challenges}, summary

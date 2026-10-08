# Prosperity Labs Agent Kit

A shared framework for building your own Propr trading agent. Give your cloud agent the [setup prompt](docs/START-PROMPT.md); it installs the framework, asks which markets you want and configures your private trading instance on its own cloud VM.

**Trial-testing beta: v0.2.0-beta.3.** This release contains order-execution code, protective stops, exits, risk monitoring and a daily scheduler. Automated tests use simulated API responses. Real Propr execution and Dot's background runtime still need an end-to-end acceptance test. The kit checks those prerequisites and reports blockers before it starts.

The [Agent Kit page](https://prosperitylabs.co/agent) contains the rules and starting prompt. This repository is the shared framework and update source. It supplies reusable strategy, order-execution and risk-management components, tests and setup instructions. Your AI configures those components for your own account; it does not need to rewrite the order engine.

Your API key, account ID, chosen markets, personal configuration, order history, reports and running services belong only on your agent's private cloud VM. Store private files outside the source checkout. Never push them to this public repository or a public fork. Prosperity Labs does not receive your key or operate your account.

## Start here

Copy [the setup prompt](docs/START-PROMPT.md) into Dot or another coding agent with a cloud computer. You choose markets and provide your free-trial account ID. The agent opens a private form where you paste your API key and click **Save API key**. The agent follows [SETUP.md](docs/SETUP.md), runs the checks and starts the actual service when they pass. You do not need to choose a hosting provider.

The full original build prompt is preserved, unchanged, in [SPECIFICATION.md](docs/SPECIFICATION.md) and [original-build-prompt.txt](docs/original-build-prompt.txt). The [requirements map](docs/REQUIREMENTS.md) connects those instructions to the implementation and testing limits.

## What the code does

- Uses daily 20-day breakout entries, 10-day exits and Wilder ATR stops across your verified market watchlist.
- Submits orders through Propr; Hyperliquid is used only for public data.
- Sizes at 0.4% starting-balance risk, with at most three markets and a 2x gross exposure cap.
- Attaches reduce-only stops, protects partial fills, tracks durable intent IDs and reconciles ambiguous responses.
- Monitors equity, latches daily halts and keeps shutdown active until the account is confirmed flat.
- Stores reports and account state outside the source checkout.

Passing a challenge is an aim, not a result established by this kit. Read [STATUS.md](STATUS.md) and [VALIDATION.md](docs/VALIDATION.md) for exactly what has been tested.

## Development and updates

Python 3.11+ on a POSIX cloud runtime. Install with `python -m pip install .` and run `python -m unittest discover -s tests -v`.

[Setup](docs/SETUP.md) · [Updates](docs/UPDATES.md) · [Contributing](CONTRIBUTING.md) · [Releases](https://github.com/worldclasstom/prop-firm-agent/releases)

Updates are explicit and versioned. The kit never silently replaces a running trader. Public issues are for code and reproducible, redacted bug reports. Never post keys or account exports.

## Attribution

The kit includes Prosperity Labs' public Propr Builder Code for API attribution. It is configurable and can be disabled. It is not your trading API key. We do not claim guaranteed builder rewards or eligibility.

[Start a Propr free trial](https://app.propr.xyz/r/4ZZFhyJg). Thomas earns a commission if you later buy a challenge through this referral link, at no extra cost to you. This supports building free tools like this. Propr accounts are simulated; the advertised payouts are USDC. Propr has not reviewed or approved this strategy.

## Risk

Trading can lose money. This kit has no verified performance record. Stops and monitoring cannot guarantee that gaps, slippage, outages or software errors will not breach a challenge. Test on a free trial first and never buy a challenge with money you need.

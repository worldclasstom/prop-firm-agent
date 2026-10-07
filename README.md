# Prosperity Labs Agent Kit

A shared starting point for building a Python trading agent for Propr prop firm challenges.

**Development alpha. Trading is not enabled.** We are building and testing from this repository first. The initial release is a development kit, not a verified turnkey trading service. See [STATUS.md](STATUS.md).

The target is daily trend following across a user-selected Propr watchlist, with a free trial first. The detailed [specification](docs/SPECIFICATION.md) defines signals, sizing, stops, account limits and setup. Passing a challenge is an aim, not a promise.

## Start here

Give your AI agent [this short starting prompt](docs/START-PROMPT.md). It should use its existing cloud computer, check what that environment supports and continue from the current implementation. No separate hosting purchase is required by this kit. An agent must establish that its environment supports the required background work before it starts trading.

For developer commands, read [SETUP.md](docs/SETUP.md). The initial package includes tested strategy, risk and state components. It does not yet include a Propr execution service or historical backtest.

[Validation](docs/VALIDATION.md) · [Updates](docs/UPDATES.md) · [Contributing](CONTRIBUTING.md)

Website: https://prosperitylabs.co/agent

## Attribution

This kit uses Prosperity Labs' public Propr Builder Code for API attribution. It is not an API key. The separate Propr referral link is https://app.propr.xyz/r/4ZZFhyJg. Thomas earns a commission if you buy a challenge through that link. Builder rewards or eligibility are not guaranteed.

## Risk

Trading can lose money. This project has no verified performance record and does not guarantee a challenge pass or compliance with loss limits during gaps, slippage or outages. Test on a free trial before considering a paid challenge. Never buy a challenge with money you need.

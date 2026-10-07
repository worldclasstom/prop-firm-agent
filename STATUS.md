# Status: v0.1.0-alpha.1

**Development alpha. Not a running trader.** This repository is the shared development and test starting point. The site will keep its existing build prompt until the repository setup path is validated.

## Implemented and offline-tested

- Pure daily-close 20-day entry and 10-day exit signals.
- Wilder ATR(20), decimal position sizing with contract multiplier, gross exposure cap and stop rounding.
- Pure daily equity-halt and static kill decisions, UTC timing and stale-data blocking.
- SQLite order intent reservation with durable ULIDs and kill latch storage. These are primitives, not a complete execution state machine.
- Official-origin request preparation with public builder attribution, opt-out and redirect refusal. No HTTP requests are sent by this release.
- Installable Python package, private configuration initialization, explicit runtime-status report and blocked start command.
- 28 offline component tests and GitHub Actions checks.
- Full approved specification, short development starting prompt and update requirements.

## Required before trial trading

1. Resolve the user's chosen Propr markets and verified contract/session metadata. Fetch and validate completed historical bars and fresh execution quotes.
2. Build the backtest using the same strategy functions; document costs, incomplete history and intraday/IOC limits of the data.
3. Implement the Propr account adapter with pagination, explicit free-trial verification and current equity/rule definitions.
4. Implement the execution state machine: idempotent submissions, ambiguous-response reconciliation, partial fills, confirmed stop attachment and verified-flat shutdown. Wire persistent daily halts and shared portfolio locks to the workers.
5. Implement continuous risk monitoring, daily scheduling and private reports. Test failure/recovery cases with mocked API responses.
6. Verify these workers in a real supported agent cloud environment across idle periods and task endings.
7. Connect an explicitly selected free-trial account and validate real execution when a signal qualifies. No forced demonstration trade.
8. Test controlled state-preserving updates before calling the project ready for ongoing use.

No Propr account has been connected. No order has been sent. No strategy performance or platform compatibility claim is established by the offline tests.

# Strategy extension plan

Status: product requirement and implementation plan, not a supported runtime feature.
Requested October 8, 2026. The framework must support additional strategies over
time, rather than make the original daily breakout system its permanent identity.
Finish the current account integration and acceptance run without silently changing
the approved strategy. The archived original specification remains unchanged.

## Current boundary

The shipped beta implements one daily 20/10 breakout strategy with ATR20 and at
least 60 completed daily bars. Those assumptions currently appear in strategy.py,
data.py, engine.py, backtest.py, service.py and the backtest CLI. A different
timeframe or entry/exit system is not yet a supported configuration option.

Insufficient history means a market is ineligible for this strategy at this time;
it does not mean the broker or framework can never support the market. Market
reports should distinguish broker availability, contract/stop support, data
availability and strategy eligibility. Preserve requested markets and show exact
exclusion reasons and counts. Do not lower a strategy's requirements, fabricate
history or silently substitute a timeframe to admit a requested instrument.

## Intended design

| Component | Responsibility |
| --- | --- |
| Strategy definition | Versioned ID, configuration schema, candle interval, completed-bar/warmup requirements, schedule, market filters, ranking, entry/exit signals and proposed protective-stop policy. |
| Data layer | Fetch and validate the declared interval, freshness and required history. Keep symbol/interval caches distinct. Do not impose the original strategy's 60 daily bars on every strategy. |
| Account risk controller | Apply broker rules and explicit account-wide risk budgets to every strategy's proposed order, including pending exposure. Own halts, reconciliation and emergency shutdown. A strategy cannot override these checks. |
| Execution layer | Own authentication, order submission, idempotency, fill reconciliation, protective orders, restart recovery and reporting. Strategy modules propose actions rather than send broker orders directly. |
| Backtest runner | Use the same versioned strategy functions and parameters as the worker, with the appropriate data resolution and explicit costs/execution assumptions. Separate indicator warmup from sufficient research history. |
| Private instance | Store account selection, strategy selection/parameters, watchlist, keys, state and reports on the user's VM outside the shared checkout. |

First extract the existing system as a named, versioned default module. Regression
fixtures must establish that its signals, position sizing, stops, risk thresholds,
00:10 UTC schedule and backtest behavior are unchanged. Unsupported strategy IDs
must fail clearly rather than fall back to the default.

A later separately specified strategy may require a different history window or
timeframe. Evaluate its rules and data requirements on their merits; a shorter
history requirement does not establish that it is suitable or profitable. Choosing
an eligible strategy must remain an explicit user decision, not an automatic
reaction to a market failing another strategy's checks.

## Multiple strategies and accounts

Adding a strategy and running several strategies on one account are separate
features. The current worker assumes it manages every position on its account.
Do not run independent strategy workers against that account: they could close one
another's positions, duplicate entries or each consume the same risk budget.

Implement one strategy per dedicated account first. Keep separate account state
directories and identify existing workers before activation. Shared-account
strategies require one coordinating execution/risk controller, strategy-owned
intents and position attribution, shared exposure reservation, conflict rules for
the same instrument, and tests for netting and recovery. Do not claim that feature
until implemented and verified.

Persist strategy ID, version and parameter digest with approvals, intents,
positions and reports. Strategy changes must require deliberate reconfiguration
and state-compatible migration, not change the interpretation of existing trades.
Use a verified-flat maintenance boundary for the initial implementation.

## Acceptance before releasing strategy selection

- Original-strategy regression behavior and archived specification stay intact.
- A second deterministic test strategy establishes the extension contract; it is
  not advertised as a production trading strategy.
- Different intervals, history minima, incomplete candles and insufficient data
  yield correct eligibility results without weakening broker or account checks.
- Invalid modules/parameters are rejected before activation; backtest and live
  paths select the same strategy version.
- Recovery preserves ownership and protective stops; switching strategies cannot
  reuse incompatible approval or reinterpret previous position state.
- A fresh user setup asks for strategy, markets and account in plain language and
  records decisions privately. No developer commands are required from the user.

These are future acceptance criteria. The current beta remains the original daily
strategy while the first authenticated Propr setup is completed.

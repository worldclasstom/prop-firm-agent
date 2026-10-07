# Working on this kit

Read README.md, STATUS.md and docs/SPECIFICATION.md before work. The specification describes the target, not evidence that code exists or a service is running.

Use the existing cloud environment. Never silently switch to a user's laptop or paid hosting. Record platform checks and limitations. Do not ask for trading credentials until offline checks pass and actual connection code is ready.

Preserve user files and private state. Never commit keys, .env, account exports, positions or reports. The public builder attribution code is intentionally distributable and configurable.

Use deterministic Python for trading. Do not change risk thresholds, signal rules, entry execution or market selection to improve backtest results. Implement and test the same pure strategy functions for backtests and live scans.

Do not start paid-account trading, buy challenges, transfer funds or request payouts. Trial trading requires explicit account selection, verified account type, confirmed protective-order support and verified runtime prerequisites. An unimplemented path must fail clearly, never report success.

Run the documented checks and update STATUS.md with observed results and remaining gaps. Pin releases; do not silently update a running trader. Keep credentials and operational state outside the source checkout.

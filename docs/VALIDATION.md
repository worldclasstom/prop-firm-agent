# Validation log

## 2026-10-07: initial development alpha

- The public repository was created with the approved specification before the reference components were built.
- 28 offline tests passed locally. They cover the 20/10-day breakout boundaries, Wilder ATR including a price gap, decimal contract sizing, exposure caps, stop rounding, equity limits, UTC daily-halt timing, stale inputs, persistent order reservation and kill flags, builder attribution and setup behavior.
- These are component tests. No backtest, live data integration, Propr account connection, order submission or protective stop has been verified.
- The Propr SDK was inspected at `fee880982ce3cf36f330fb07a3a9be57ec4dd904`. It is a reference, not bundled or imported by this release. Integration must recheck the current API and record its selected version.
- A fresh clone from public GitHub at commit `6de65ff05588cf1eab187325fd764e4d1d41fbf0` was installed into a new virtual environment. The installed package passed all 28 tests from outside the source checkout on Python 3.14.7. The CLI status report, private setup, repeat setup preserving existing configuration and blocked start behavior were also checked.
- GitHub Actions passed all three Python 3.11, 3.12 and 3.13 jobs for that commit: https://github.com/worldclasstom/prop-firm-agent/actions/runs/37701570180
- The release adds this validation record after those checks; executable source is unchanged.

Keep trial evidence, account identifiers and operational reports private. Publish a redacted validation summary after actual execution tests, distinguishing no signal, submitted, filled, protected, recovered and stopped.

## 2026-10-07: executable trial-testing beta

The beta adds the real HTTP order path, execution state machine, public market data, scenario backtest and supervised worker. Synthetic fixtures deliberately label unmapped account fields `fixture_*`; they are not invented claims about the Propr API schema.

All 64 automated tests passed locally. Automated checks cover entry/stop/exit payloads, partial fills, lost responses, pagination, both order types, duplicate scans/restart, rejected stops/closes/cancels, unresolved shutdown, stale account data, process locking, runtime evidence, paid-account separation, next-bar backtest causality, cost overrides, real request header encoding, preserved specification and worker startup/scan/stop. The worker test runs actual scheduler/monitor threads against a simulated client and confirms flat shutdown. A separate test confirms expired runtime evidence permits only safety reconciliation for previously authorized exposure.

Public Hyperliquid reads returned 234 native instruments, 400 completed BTC daily bars and 289 xyz:GOLD daily bars. Both histories ran through the scenario model. Results are connectivity/model checks, not published performance evidence.

The full previous landing-page prompt matched the archive before the page was shortened. SHA-256 is recorded in original-build-prompt.sha256 and pinned in the test suite.

Still unverified: authenticated Propr account mapping, actual trial fills/stops, broker failure recovery, and background execution across Dot task/idle boundaries. These require a user's trial account and the intended cloud environment. Exact IOC fills and intraday event order cannot be inferred from daily bars; the backtest explicitly labels its approximations.

A fresh clone of public GitHub commit `a1deea387913863c7b4431a6ea9cc7898b967bdd` installed successfully into a new virtual environment. Running from outside the checkout, all 64 tests passed on Python 3.14.7; initialization and the diagnostic CLI also worked. GitHub Actions passed the 3.11, 3.12 and 3.13 matrix: https://github.com/worldclasstom/prop-firm-agent/actions/runs/37704580663 . This final documentation commit does not change executable code.

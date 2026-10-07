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

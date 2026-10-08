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

## 2026-10-08: private API-key form (beta.3)

All 74 offline tests passed locally, including ten credential-form tests for successful saving, expiry, one-use submission, Host/Origin/CSRF checks, opaque embedded-browser origins, invalid/oversized input, private permissions, atomic symlink replacement and checkout exclusion. The original specification preservation test remains unchanged.

The actual loopback form rendered at 1280×720 and 390×844. A synthetic test key was submitted using the Codex in-app browser; the success page appeared and the CLI exited successfully. No real key or Propr account was used. The test exposed an embedded-browser `Origin: null` submission; that path now additionally requires browser-generated `Sec-Fetch-Site: same-origin`, plus the existing unique route, exact Host and independent CSRF token.

This establishes local form operation only. The fresh Dot run must still demonstrate same-cloud-host browser access, user takeover, authenticated trial checks and worker survival/recovery. It does not establish live trading or ongoing cloud execution.

The beta.3 package was also installed into a fresh virtual environment and tested from outside the source checkout: all 74 tests passed. This caught and corrected credential-directory rejection after installation; Git checkouts and unpacked framework source directories are rejected independently of the installed package location.

## 2026-10-08: empty cloud Git placeholders (beta.4)

Dot reported four beta.3 form tests failed because empty `.git` markers above its private directories were treated as actual repositories. The guard now ignores empty directory/file placeholders while rejecting populated markers (including worktree pointer files), unpacked framework source directories and resolved symlinks into a repository. Unreadable markers remain rejected.

Two regression scenarios exercise HTTP form saving under nested empty markers and rejection inside a real repository beneath an empty marker, including symlink aliases and a permitted private sibling. All 76 offline tests pass. No live account, trading or actual Dot form takeover is established by these tests.

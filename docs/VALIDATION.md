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

### User-observed cloud form handoff

The user then supplied screenshots showing Dot's cloud browser displaying Connect Propr, user takeover, masked key entry, the API key saved confirmation, and control returned to Dot. Dot reported 77 tests passed in its locally patched beta.3 installation. This establishes that the browser handoff and form submission reached success in that cloud run; it is not a test of the exact unmodified beta.4 release, API authentication, account verification or trading. The public beta.4 fix passed 76 tests locally and in GitHub Actions: https://github.com/worldclasstom/prop-firm-agent/actions/runs/37858926998 .

## 2026-10-08: account discovery (beta.5)

The official SDK documents paginated challenge attempts with `accountId`. The kit now offers `propfirm accounts` before an account is selected, using a read-only client and the saved key. It groups multiple attempts under each ID, preserves missing-ID warnings, retains all statuses and leaves trial classification unverified until explicit API evidence is inspected. Discovery does not alter selected configuration, approvals, state or orders.

Eight new synthetic tests cover multiple pages/accounts, a single account requiring confirmation, empty results, duplicate/missing IDs, write/origin rejection, authentication failure, private CLI output/storage and malformed rows. All 84 offline tests passed both locally and from the installed beta.5 package in a fresh virtual environment outside the checkout. No real API key was used in this development run.

Separately, user screenshots show Dot retrieving one account, reporting API type `paper`, asking for confirmation and receiving a yes. Dot then said it would verify the linked trial rules and market support. This is user-observed progress on its existing installation, not validation of the exact beta.5 release or completed trial eligibility, orders or stops. No private account IDs are included in this log.

GitHub Actions also passed the Python 3.11, 3.12 and 3.13 jobs for beta.5: https://github.com/worldclasstom/prop-firm-agent/actions/runs/37859809911 . The Agent Kit page was deployed with the matching beta.5 prompt.

### Authenticated setup follow-up (user-reported)

A later screenshot reports Dot successfully read the selected account and matched its starting balance and 3% daily-loss / 6% static-drawdown / 10% target rules. It could not establish explicit free-trial mode, the UTC day-start balance or that balance's reference date from inspected responses. Its reported account type was `paper` and the linked challenge name was Free Trial, neither accepted as the required explicit trial mapping. Trading remains off. The public SDK/reference reviewed here does not define these three fields; the linked OpenAPI URL returned HTTP 403 from this development environment as well. Actual redacted response structure or authoritative provider semantics are needed before changing the adapter. This is not evidence that Propr cannot provide them.

## 2026-10-08: observed Propr adapter and daily/live risk data (beta.6)

All 105 local tests pass. New checks cover ID-based active phase joins, rejected
mismatched/inactive accounts, current UTC daily references and isolated margin,
composite free-trial product evidence, read-only inspection preserving private
state, and research backtests without broker credentials. Seven live-mark tests
cover long/short equity, gross exposure, stale/missing/invalid data, account-change invalidation,
reconnect cache clearing, engine integration, and a real local WebSocket
handshake/read/shutdown plus redirect rejection, using only synthetic credentials.

The user-supplied redacted diagnostic passes the eight automatic mappings and
composite trial-catalog check. Its account values/identifiers/dates remain outside
the repository and were not used as real configuration. No real key was used.

Sources: https://www.propr.xyz/developers (interactive Integration tab, inspected
October 8) and https://github.com/XBorgLabs/propr-docs. The live reference documents
`daily-metrics` and its two balance fields, but not its JSON envelope/date key;
those paths must be established from the authenticated response. WebSocket
transport uses pinned websockets 17.1 with redirects rejected and private logging.

Outstanding: authenticated daily-metrics binding and Propr WebSocket behavior,
full chosen-market verification, production cloud persistence/recovery, and a
qualifying trial order/fill/stop. No strategy-performance claim follows from these
adapter tests. The original prompt preservation test remains unchanged.

The beta.6 package was installed into a clean virtual environment and all 105 tests
passed from outside the source checkout on Python 3.14.7. This also verified the
pinned WebSocket dependency and installed CLI version.

## 2026-10-08: authenticated Dot feedback and research windows (beta.7)

The user's screenshots report beta.6 passed its actual trial-catalog, dated UTC
daily reference and Propr live-mark checks. The account had no orders/positions.
Dot still reported unverified idle/task-ending and autonomous supervisor recovery,
missing broker order minimums, and interrupted account-market checks (64 matched,
one timeout, 89 pending). These are relayed observations, not local authenticated
tests. Trading has not been reported running.

Code inspection found that the separate research-window report truncated every
asset to the shortest history and aligned assets by array position. It also
counted some partial tails as windows. Beta.7 instead uses complete 90-day UTC
intervals, preserves each asset's inception and full earlier indicator history,
and discloses market gaps and partial tails. The main simulation is unchanged
when no start boundary is supplied. No user's historical data was rerun here;
the previously reported -1.60% result has not been replaced with a new result.

All 111 local tests pass. Six new regression tests cover mixed listing ages,
calendar alignment, late eligibility, complete-window boundaries, missing dates,
retained indicator history/future exclusion and distinct empty/duplicate
watchlist errors. Tests use synthetic histories; no order is sent.

The beta.7 package was also installed and all 111 tests passed from outside the
source checkout on Python 3.14.7; the installed CLI reports `0.2.0b7`.

Public documentation inspected October 8: [Propr Account Settings and trading
reference](https://www.propr.xyz/developers) lists seven minimum quantities but
does not document a complete broker quantity/notional limits response in the
sections inspected. Its margin-config example is availability/leverage evidence.
[Dot computers](https://learn.chatgpt.com/docs/dots/computers-and-apps) and
[tasks](https://learn.chatgpt.com/docs/dots/tasks-and-memory) describe cloud work
and persistence, but do not establish arbitrary daemon autostart after host
termination. Actual platform-supported lifecycle tests remain necessary.

# Status: v0.2.0-beta.7

**Executable trial-testing beta.** The repository now contains the trading path: Propr order submission, partial-fill protection, stops, exits, daily scheduling, continuous risk polling and verified-flat shutdown. The landing-page setup prompt installs this release and follows the preserved full specification.

Beta.7 fixes research-window alignment: each scenario covers a full 90 UTC
calendar days, retains earlier indicator history, and preserves the chosen
universe and each asset's inception date. Short histories no longer truncate
older markets; partial tails are disclosed rather than counted. Missing eligible
market days are flagged. The main backtest and live strategy/risk rules are
unchanged. All 111 local tests pass.

The user's latest Dot screenshots report beta.6's authenticated trial-catalog,
actual dated daily reference and live Propr marks checks passed. The trial service
is still off. These are user-reported observations, not independently observed
local authentication. See the current acceptance gaps below.

## Implemented and checked

- Exact 20/10-day breakout rules, Wilder ATR, decimal risk sizing, cross-asset watchlist metadata and 2x gross cap.
- Public Hyperliquid history/quotes, completed-bar validation, sessions and price/size precision.
- Restricted Propr HTTP transport with public builder attribution, pagination and explicit selected-account mapping.
- Durable order intents, partial fills, stop confirmation, duplicate-run prevention, unknown-response reconciliation and persistent halts.
- Daily 00:10 UTC scan, five-second risk polling plus API latency, process lock, runtime checks, private reports and status/stop commands.
- Scenario backtest with disclosed execution/cost limitations; explicit release checks and separately tested update checkouts.
- Full original prompt archived unchanged and pinned by a preservation test.

## First Dot installation feedback

The user's October 8 screenshot reports beta.2 installed, all 64 tests passed, both APIs reachable, and 154 public non-FX market candidates. No authenticated account was connected and no trades were started. Dot reported unresolved credential input and persistent worker/recovery support; a 35-second heartbeat did not establish lifetime across task endings.

A later screenshot reports Dot found cloud-desktop takeover for hidden terminal key entry and observed a test worker surviving a worker turn ending and recovering from a deliberately crashed process. A subsequent screenshot reports the ten-minute probe passed across worker completion and wait/wake cycles, crash recovery took about one second, shutdown was clean, and twelve markets passed a 400-day history check. Cloud-host restart recovery remained untested. These are user-provided reports, not independently observed tests.

Beta.3 adds a one-field browser form and tests its save path with synthetic credentials. Local desktop/mobile browser testing verifies form rendering, submission and private file storage. Dot cloud browser takeover and continued worker/recovery behavior still require the user's run; local form tests do not establish those cloud capabilities.

Beta.4 addresses the next user-reported Dot failure: four form tests failed under empty Git markers in the cloud workspace. Regression tests now simulate nested empty markers through the actual HTTP save path, while confirming real repositories and symlink aliases remain excluded. The user subsequently supplied screenshots showing successful browser takeover, masked key entry, the API key saved screen, and control returned to Dot on its locally patched beta.3 installation (Dot reported 77 tests). That confirms the form/handoff path in the user's cloud run; the exact unmodified beta.4 release and authenticated account/trading checks still need acceptance.

## Latest Dot feedback and remaining acceptance

October 8 screenshots report 105 offline tests passed in beta.6; the selected
trial account, actual UTC daily reference and live marks were verified. All 154
histories were refreshed. RUNE was excluded after a reported Propr blacklist
change. The 145-market venue-research run reported -1.60% marked return, 4.71%
peak-to-trough drawdown, 51 closed trades and three open modeled positions. The
target was not reached. These results are not a challenge pass rate or evidence
of actual executions. Beta.7 changes the separate window report, not that main
simulation's signal or risk logic; the user's data has not been rerun locally.

Still required:

1. Authoritative Propr minimum quantities (reported missing for 147 candidates)
   and minimum notionals (reported missing for all 154). The public developer
   reference lists seven minimum quantities, not a complete limits endpoint.
   Availability/precision evidence alone does not establish order minimums.
2. Resume account-market verification through permitted tools: the screenshots
   report 64 matches, one timeout and 89 unchecked after an approval-review
   cancellation. Preserve results and do not bypass a review decision.
3. Observed idle/task-ending behavior and autonomous supervisor recovery on the
   actual Dot cloud host. Prior child-process and controlled supervisor restart
   tests do not establish recovery after the supervisor or host disappears.
4. A qualifying Propr trial order, fill and confirmed protective stop, followed
   by recovery and stop-to-flat checks. No signal is valid but does not validate
   fills. A fresh-user setup is still outstanding.

No Propr account has been connected in this local development session and no
actual order has been sent. Local tests and public documentation do not establish
strategy performance or guarantee challenge outcomes. See docs/VALIDATION.md.

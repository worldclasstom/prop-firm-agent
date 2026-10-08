# Status: v0.2.0-beta.4

**Executable trial-testing beta.** The repository now contains the trading path: Propr order submission, partial-fill protection, stops, exits, daily scheduling, continuous risk polling and verified-flat shutdown. The landing-page setup prompt installs this release and follows the preserved full specification.

This release fixes the private API-key form rejecting private storage under empty Git placeholders in cloud workspaces. Populated Git markers and framework source directories remain excluded. The trading engine and preserved original specification are unchanged. All 76 offline tests passed on October 8, 2026, including original-specification preservation. The landing-page copied prompt matches docs/START-PROMPT.md exactly.

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

## What still needs the first real user run

1. A Propr API key and explicit free-trial account ID. Authenticated account fields must be inspected and mapped, including trial proof and the current day-start balance. Public docs do not fully specify them.
2. The user's chosen markets, checked against that account's API/stop support and instrument metadata.
3. Observed Dot/cloud support for persistent background execution across idle periods, task endings and supervisor restarts.
4. A qualifying real Propr trial order, fill and confirmed protective stop, followed by recovery and stop-to-flat checks. No signal is valid but does not validate fills.

No Propr account has been connected in this development session. No actual order has been sent. Offline tests and public market-data checks do not establish strategy performance or guarantee challenge outcomes. See docs/VALIDATION.md and docs/REQUIREMENTS.md.

# Status: v0.2.0-beta.9

**Executable trial-testing beta.** The repository now contains the trading path: Propr order submission, partial-fill protection, stops, exits, daily scheduling, continuous risk polling and verified-flat shutdown. The landing-page setup prompt installs this release and follows the preserved full specification.

Beta.9 adds the scheduled execution model as a documented revision
(docs/SCHEDULED-EXECUTION.md): `propfirm tick` runs one idempotent pass per
scheduler invocation and exits, with reduce-only stops resting at Propr as the
only protection between ticks. It exists because eight betas could not establish
a persistent worker with network access inside Dot's cloud computer. The trading
rules, thresholds and shutdown protocol are the unchanged shared Engine. Twelve
new synthetic tests cover scan timing, idempotence, resumption, stop requests,
breaches between ticks, disclosed gaps, failures, model mixing and evidence.
All 139 local tests pass. A private GitHub repository template
(examples/scheduled-agent) is the reference runtime. No check run from a real
scheduler, no live order and no Propr acceptance of runner addresses has been
observed; the continuous model and its outstanding items below are unchanged.

Beta.8 adds a trial-only broker-validation policy for unpublished order minimums.
Unknown lower bounds stay explicit nulls with a source record. Risk ceilings,
round-down sizing, confirmed protection and all other prerequisites remain in
force. Rejections block entries without upsizing or blind retries. This is a
client policy revision, not newly discovered broker limits. All 123 local tests
pass for the release. Later screenshots report Dot configured this policy for
145 eligible markets; no orders were submitted. See docs/ORDER-LIMITS.md.

Beta.7 fixes research-window alignment: each scenario covers a full 90 UTC
calendar days, retains earlier indicator history, and preserves the chosen
universe and each asset's inception date. Short histories no longer truncate
older markets; partial tails are disclosed rather than counted. Missing eligible
market days are flagged. The main backtest and live strategy/risk rules are
unchanged. All 111 local tests pass.

The user's latest Dot screenshots report beta.8 installed, with account, daily
reference, live marks and checkpointed market checks passed in its command
environment. Its background runtime cannot reach the broker APIs, so the trial
service is still off. These are user-reported observations, not independently
observed local authentication. See the current acceptance gaps below.

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

Later screenshots report beta.7 installed with 111 tests passing. Its corrected
report contains three complete 90-day windows and a 70-day partial tail; none
reached the target and none were flagged by the model. These are modeled results,
not actual challenge passes. The recovery probe restarted the inner supervisor
in about one second, but left an unsupervised old test worker holding its lock.
Restoring supervision required manual cleanup, so autonomous recovery failed.
A separate ten-minute untouched cloud-desktop probe was still in progress in the
latest screenshot; its outcome cannot establish that this orphan-worker defect
is fixed. The repository does not contain Dot's nested-supervisor launcher, and
no runtime fix is claimed from these observations.

The subsequent beta.8 screenshots report 123 release tests passing, all 154
account-market matches confirmed, and 145 markets meeting history/blacklist
filters. The ten-minute idle probe passed, and an offline recovery test using the
actual engine passed, including a rejected close with a retained protective stop.
Full task-ending/host recovery remains unverified. Command-context account, daily
reference and live marks checks passed, but uninterrupted CLI verification did
not. The background context reports network unreachable for Propr and connection
refused for Hyperliquid. No supported setting or pending approval was identified.
No orders were submitted; the reported research return remains -1.60%.

The standalone scripts/runtime_network_probe.py now provides public, credential-free
comparison of launch contexts with redacted environment presence and HTTP/errno
results. It neither changes networking nor resolves the cloud limitation locally.
All 127 repository tests pass, including four diagnostic tests for request scope,
secret redaction, HTTP versus transport failure, and redirect refusal. Beta.8's
published package is unchanged; the diagnostic runs separately from the checkout.

The downloaded beta8 runtime diagnostic was subsequently inspected locally:
all bundled SHA256 checksums match and its probe matches the pinned repository
script. Both desktop contexts fail before TLS (Propr ENETUNREACH, Hyperliquid
ECONNREFUSED). The command context returns Hyperliquid HTTP 200 and Propr health
HTTP 403, whose source is not established. Its proxy is loopback-only in a
different network namespace. Neither desktop context inherits proxy variables;
changing the Supervisor environment whitelist alone is therefore not a fix.
An existing OS CA bundle passed SSL-context construction, not an API connection.

The supplied recovery result records the installed engine completing synthetic
shutdown after supervisor loss, retaining a stop during a rejected fake close,
preserving its halt and singleton lock, and needing no manual orphan cleanup.
The test patched runtime readiness and time and used fake broker adapters.
This resolves the earlier failure only within that bounded offline test; the
supplied Supervisor configurations are diagnostic-only, not a production launcher.

The bundle does not establish a supported persistent worker in the command
environment with network access surviving the initiating task's end. That is a
distinct remaining investigation, not evidence that the desktop proxy can be
copied or that a cloud worker is already available. No raw diagnostic archive or
private configuration has been added to the public repository.

Still required:

1. Verify authenticated REST, public data and live marks from the actual worker's
   launch context after resolving its network failure through supported settings.
   Preserve the selected trial policy and explicit unknown minimums; successful
   order acceptance is still untested.
2. Complete fresh CLI verification through permitted tools. Checkpointed market
   results are preserved, but do not establish uninterrupted worker connectivity.
   No pending approval request was reported; do not bypass a review decision.
3. Observed idle/task-ending behavior and autonomous supervisor recovery on the
   actual Dot cloud host. Prior child-process and controlled supervisor restart
   tests do not establish recovery after the supervisor or host disappears.
   Extend the passed offline orphan-worker fix to the verified production launch
   path, including outermost supervision; retain the duplicate-worker lock.
4. A qualifying Propr trial order, fill and confirmed protective stop, followed
   by recovery and stop-to-flat checks. No signal is valid but does not validate
   fills. A fresh-user setup is still outstanding.

No Propr account has been connected in this local development session and no
actual order has been sent. Local tests and public documentation do not establish
strategy performance or guarantee challenge outcomes. See docs/VALIDATION.md.

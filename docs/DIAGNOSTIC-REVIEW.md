# First Dot setup: diagnostic review

Reviewed October 8, 2026. Source: user-supplied redacted diagnostic from the
locally patched beta.3 cloud installation. This is not a new authenticated test
from the maintainer environment. The archive stays outside the public repository.
Its IDs, account monetary values and account timestamps are synthetic; use them
only to understand response structure, never as configuration or financial data.

## Findings

- Key entry and authenticated account reads succeeded in the reported run.
- All 154 candidate histories were checked: 146 pass the original strategy's
  60-bar minimum and eight do not. None is yet fully verified for trading. A short
  history is a strategy-specific exclusion, separate from missing contract data.
- The scan crossed UTC midnight. Freshness needs a common fresh check before
  activation, not a claim that all collected histories are current together.
- The actual verify and backtest commands stopped at an empty enabled watchlist.
  They did not reach and pass later validation stages; no backtest report exists.
- Supervisor restarted a mock child, and a test controller relaunched Supervisor
  while synthetic state survived. This does not establish automatic Supervisor
  recovery, full parent-task termination, idle suspension or host restart behavior.
- No trial orders, fills or protective stops have been verified.

## Account adapter work

The response supplies more useful product evidence than `type: paper` alone:
the account, active attempt and linked challenge share consistent IDs, and the
challenge has `slug: free-trial` and an active zero-price product. This combination
is worth checking with Propr as a stable product identity contract. The existing
adapter only accepts a literal trial/type/mode mapping; do not invent such a field
or treat the rich-text description's `mode: normal` as account evidence.

The current-phase relationship also needs care. In the observed structure,
`attempt.currentPhaseId` matches an attempt phase's `attemptPhaseId`; that phase's
`phaseId` links to the challenge rule phase. Resolve those identifiers explicitly,
with uniqueness checks, rather than assuming index zero in a multi-phase account.
Observed candidate mappings after that join:

| Value | Observed source |
| --- | --- |
| Starting balance | Matching attempt phase `startingBalance`, corroborated against challenge `initialBalance` and provider meaning |
| Current balance | `account.balance` |
| Unrealized P&L | `account.totalUnrealizedPnl` |
| Isolated margin | `account.isolatedPositionMargin` |
| Daily loss fraction | Matching challenge phase `maxDailyLossPercent`, scaled by 0.01 |
| Static drawdown fraction | Matching challenge phase `maxDrawdownPercent`, scaled by 0.01 |
| Target fraction | Matching challenge phase `profitTargetPercent`, scaled by 0.01 |
| Drawdown type | Matching challenge phase `drawdownType` |

Neither the account nor the detailed attempt/challenge in the supplied archive
contains the current UTC day-start balance or its specific reference date. The
[official rulebook](https://www.propr.xyz/rules) confirms a balance snapshot at
00:00 UTC for the daily equity floor. Current balance, generic `updatedAt`, and
synthetic diagnostic dates cannot stand in for that snapshot. An official current
daily equity floor with its date could also support a documented adapter, if Propr
provides and confirms it. A locally maintained alternative would need a separate
design for first-run initialization, reconciliation and downtime; it must not
quietly replace missing authoritative state.

The [official SDK](https://github.com/XBorgLabs/propr-docs/blob/main/python/propr_sdk.py)
uses balance plus unrealized P&L plus isolated margin for equity. Establish how the
API's `balance` relates to the rulebook/dashboard balance, especially when margin
is isolated, before interpreting a locally recorded balance as the daily reference.

## Contract and runtime work

The 146 history-passing markets still need exact Propr contract mappings,
minimums, precision, sessions, stop support and availability. Complete independent
public metadata work in parallel, keeping unknown and ineligible distinct. Do not
enable them merely because candles exist, or exclude all of them because eight
others fail the history minimum.

The margin-config GET responses exist for three samples. Matching creation/read
times suggest possible lazy defaults but do not prove a write. Ask Propr about
semantics rather than requiring the user to decide a technical detail. Verify the
supported persistent supervisor lifecycle and state/credential survival on the
actual host; a controller-assisted mock restart is only partial evidence.

## Draft provider question (not sent)

We are integrating a Propr free-trial trading-agent framework. Authenticated
account, challenge-attempt and linked-challenge reads work, but we need the
supported API mappings for these checks:

1. Can we identify a free trial through the linked challenge's `slug: free-trial`
   and active zero-price product, with matching account/attempt/challenge IDs?
   Is that a stable authoritative contract, or is there a dedicated field/endpoint?
2. Which endpoint returns today's 00:00 UTC balance snapshot (or daily-loss equity
   floor), with the UTC date it applies to? How is this reference calculated when
   a new trial is created mid-day and when positions use isolated margin?
3. Does API `balance + totalUnrealizedPnl + isolatedPositionMargin` reconcile to
   dashboard equity, and what exactly is snapshotted as start-of-day balance?
4. Where are per-instrument contract multiplier, order minimums, precision, sessions
   and stop support documented for native and namespaced instruments? Does GET
   margin-config initialize defaults, and is it the supported availability check?

The linked `https://propr.xyz/openapi.json` returned HTTP 403. Please provide an
accessible current schema or the relevant field definitions. No credentials or
private account exports are needed in the response.

## Follow-up: official Integration documentation and beta.6

The user supplied `/docs/bot`, which redirects to the interactive developers
reference. Its **Integration** tab documents the previously missed
`GET /accounts/{accountId}/daily-metrics`, the daily-loss base
`startingBalance + startingIsolatedPositionMargin`, and the live equity formula.
It explicitly warns that REST mark prices lag and supplies `mark.updated` on
`wss://api.propr.xyz/ws`. These resolve the endpoint/formula questions above;
the draft question has not been sent and should not be sent unchanged.

Beta.6 implements these reads and live marks, automatic ID-based phase mappings,
and the composite linked paper/free-trial/zero-price catalog check. The supplied
redacted structure passes that catalog check; the provider has not separately
promised its long-term stability. Missing or changed evidence fails verification.
The daily-metrics envelope and reference-date path still need the real response,
which was absent from the archive. No synthetic date or monetary value was used
as account truth. Tests use explicitly synthetic response envelopes/date keys.

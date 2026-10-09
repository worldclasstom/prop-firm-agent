# Specification revision 2: scheduled execution

October 9, 2026 draft revision, following the user's request for a setup that a
person completes by pasting one prompt into an AI tool, with no server to rent
and no laptop to keep on. It revises the original specification's continuous
worker (five-second risk polling under a verified cloud supervisor) into a
scheduled model. It does not edit the archived original specification, and it
changes no trading rule, threshold, sizing rule, stop rule, halt or shutdown
step. Status: implemented and tested offline; no live acceptance run yet.

## Why

Eight betas tried to make an AI tool's cloud computer behave like a server:
a worker surviving the task that started it, network access from a background
context, and autonomous supervisor recovery. STATUS.md records that none of
these was established on the actual host. The continuous model is sound on a
real server; it is not available inside a chat tool. The strategy itself is
daily, and every position already carries a reduce-only stop resting at Propr.
A scheduled model therefore removes the unverifiable part without touching the
trading rules.

## What changes

| Original specification | Scheduled revision |
| --- | --- |
| Continuous worker; risk monitor every five seconds plus API latency | One `propfirm tick` process per scheduler run, every `tick_interval_minutes` (5 to 240; 60 recommended), then exit |
| Verified cloud supervisor, host identity, idle recovery, worker lock across restarts | No supervisor. Each tick is a fresh process. A per-run lock prevents overlapping ticks |
| Runtime evidence: seven host checks, refreshed every seven days | Runtime evidence: scheduler, network access, persistent state and private secrets, declared interval equal to the configured one |
| Dead monitor blocks entries | A missed run is disclosed as `schedule_gap` in the event log and status; the next tick reads fresh account data before any decision |
| `start`, `status` with 30-second heartbeat | `tick`, `status` with `tick_overdue` after two missed intervals |

Everything else is the shared Engine, unchanged: daily 00:10 UTC scan, 20/10-day
breakouts, Wilder ATR, 0.4% starting-balance risk, three positions, 2x gross cap,
two-ATR reduce-only stops confirmed at Propr, 2% daily halt, 4.5% kill switch,
durable intents, reconciliation, the verified-flat shutdown protocol and reports.

## What one tick does

1. Refuse unless the configuration is approved for this exact digest, release
   and account mode, and the scheduled runtime evidence matches it.
2. Take the account-state lock so two overlapping runs cannot trade.
3. Record a `schedule_gap` event if the previous tick is older than twice the
   declared interval.
4. Latch `operator_stop` if a STOP request exists.
5. Reconcile persisted intents against Propr; ambiguous entries block new risk.
6. Run the risk tick: fresh account read, daily halt and kill evaluation,
   cancellation of pending entries when required, and confirmation of a
   reduce-only stop for every open position. A missing or unconfirmable stop
   latches shutdown exactly as before.
7. If no scan has run for this UTC date and it is at or after 00:10, run the
   daily scan: exits first, then ranked entries with stops.
8. Write the daily report and `status.json`, record `last_tick`, exit.

Exit codes: 0 completed, 2 a read or scan failed (no entries were placed; the
event log names the failure kind), 3 a kill latch is set and the account needs
human review before `reset-halt`. A scheduler that shows failed runs therefore
shows exactly the runs that need attention.

## Protection between ticks and the accepted risk

Between ticks nothing runs. Protection is the reduce-only stop-market order
resting at Propr for every position, confirmed on every tick. The 2% daily
halt and the 4.5% kill switch are evaluated at the tick cadence, not every five
seconds. With 0.4% starting-balance risk per position and at most three
positions, the planned loss at stops is about 1.2% plus gaps and slippage; a
move large enough to touch the 3% daily limit between hourly ticks is a gap
event that a five-second loop would not have prevented either. The original
specification already states that stops and checks cannot guarantee a limit
is never hit. The revision widens the reaction window for the equity halts and
nothing else. Choosing an interval above 60 minutes widens it further; 240 is
the cap so that a once-daily run cannot be called monitored.

A scheduler can be late or skip a run. The tick discloses the gap and then
reads fresh data; it never replays stale signals. If a platform disables the
schedule, nothing closes positions: the stops remain at Propr, and the user must
run `propfirm stop` followed by a tick, or close at Propr directly, which the
next tick reconciles.

## Where it runs

The reference runtime is a private GitHub repository created from
`examples/scheduled-agent`. GitHub Actions runs the tick on a cron schedule, the
API key is a repository secret, and the private state directory with reports is
committed back after each run so the user reads reports in their browser and
"is it running" means "when was the last green run". It is free, needs no
server, is owned by the user, and keeps Prosperity Labs out of key custody.
Two platform properties are documented facts that the setup agent must
disclose: GitHub can delay cron runs under load, and it disables scheduled
workflows on repositories with no activity for 60 days, which the state commits
avoid. Propr's public health endpoints and Hyperliquid's public metadata were
reached from a GitHub-hosted runner (Azure, 132.196.30.209) on 2026-10-09 with
HTTP 200, by the workflow `.github/workflows/probe.yml`; see STATUS.md. That
observation covers unauthenticated reads from one runner address. The
template's check run still establishes the authenticated path for each
private repository before approval.

Any other scheduler that can run a command on a cadence with a persistent
directory and a private secret also qualifies, including an AI tool's scheduled
task feature. An AI session in the loop every tick is second choice: it costs
tokens, and it must only run the command and relay the report, never decide.
Setup (account discovery, market verification, backtest, approval) happens in
the AI tool's own computer as before; only operation moves to the scheduler.

## Configuration and evidence

Private `config.json` sets `execution_model: "scheduled"` and
`tick_interval_minutes` (integer, 5 to 240). Both are part of the approved
digest, so changing them needs fresh approval. `runtime.json` follows
`examples/runtime-scheduled.json`: `execution_model`, `config_sha256`,
`checked_at`, `scheduled_interval_minutes` equal to the configured interval, and
`verified`/`observation` for `scheduler`, `network_access`, `persistent_state`
and `private_secrets`. Record what was observed, such as the URL of the check run
that reached both APIs from the scheduler. `start` refuses a scheduled
configuration and `tick` refuses a continuous one, so the two models cannot be
mixed on one account.

## Evidence

`tests/test_scheduled_tick.py` covers, with synthetic API fixtures: a first tick
that scans, enters and confirms a stop; repeated same-day ticks adding nothing;
no scan before 00:10 UTC on a new date; a fresh process resuming from state
without duplicates; STOP flattening with a reported halt; a static-loss breach
between ticks shutting down on the next tick; missed runs disclosed; a read
failure returning an error without entries; model mixing refused; approval and
evidence required; expired evidence with exposure recovering only to flat; and
configuration bounds. These tests do not establish live Propr acceptance or the
scheduler's real cadence. Acceptance still requires a check run and a first
real signal, fill and stop confirmation from the scheduler.

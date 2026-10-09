# Full-prompt requirement map

The complete approved build prompt is preserved byte for byte in `original-build-prompt.txt` and verbatim inside `SPECIFICATION.md`. SHA-256: `1b452237606fff18f85070ec43a6fd792d883ee50048de831f95f70d60cca976`. A test pins that hash. The short setup prompt is an entry point to this specification, not a replacement. Future changes require an explicit documented revision; do not edit the archive to match the implementation.

## Where each requirement lives

| Original requirement | Implementation / installer responsibility | Evidence or remaining check |
| --- | --- | --- |
| Four stages; preserve progress; ask only missing information | SETUP.md and START-PROMPT.md; private configuration and durable SQLite state | Installer must maintain its persistent checklist and reuse saved answers. |
| Existing agent cloud computer; configured cloud coding environment; no laptop or unrequested hosting | SETUP.md runtime inspection; config.runtime_ready; harmless runtime-probe | Real Dot idle/task-ending process lifetime and supervisor remain unverified. Do not fill evidence with assumptions. |
| Check files, secrets, Python, network, schedule, background execution, recovery | runtime.json observations tied to host/config/version approval | Runtime probe and local worker lifecycle tested; real cloud acceptance pending. |
| Read current Propr rulebook and SDK, record commit, report conflicts | SETUP.md; adapter based on SDK fee880982ce3cf36f330fb07a3a9be57ec4dd904 | Recheck current rules and authenticated fields during setup. |
| Deterministic trading; LLM handles setup and explanations | strategy.py, risk.py, engine.py, service.py | No model calls in the trading loop. |
| User-selected cross-asset watchlist; exact native/HIP-3 symbols; no substitutions | config.py, data.py, CLI markets/verify; verified metadata exported to private markets.json | User chooses markets; authenticated Propr availability and contract/stop/session metadata must be verified. Linear USDC perpetuals supported; unsupported products reported. |
| Freeze paid watchlist; shared portfolio budget | Config digest in paid approval, separate state directory, engine portfolio lock | Changed config requires new approval; do not approve a mid-challenge watchlist change. |
| Up to 400 completed daily bars, minimum 60, no fabrication | data.py validation/cache, shared strategy | BTC 400 and xyz:GOLD 289 public bars retrieved in this environment. This is not account execution evidence. |
| Prior-day volume ranking, deterministic tie-break | engine.scan and backtest.simulate | Most recent completed day's USD notional volume, then exact identifier. |
| Daily 00:10 UTC; previous 20-day long/short breakout, previous 10-day exit | strategy.py; service daily scheduler | Scheduler test starts monitor before scan. No signal-bar lookahead. |
| Wilder ATR20 seeded from first 20 true ranges | strategy.atr | Component tests include gaps and recurrence. |
| 0.4% starting-balance risk, max three positions, max 2x equity gross, no adding | strategy.quantity and engine.scan | Decimal sizing, multiplier, lot/minimums; unresolved entries block additional submissions. No leverage-setting write. |
| Two ATR stop from actual fill, directional tick rounding, partial fill protection, never loosen | engine.protect, data.rounded_price | Mock partial fills and rejected stops tested. First real fill and stop confirmation pending. |
| Default limit/IOC at fresh bid/ask; explicit market option; no post-only/chasing/top-up | engine.scan and payload | Both payload paths tested. Quotes limited to ten seconds, sessions checked. No claim either type performs better. |
| Durable ULID before submission; same intent/payload on retry; pagination; deduplication | state.Store; propr.Client; engine.send/recover | Lost-response and restart tests; ambiguous entries block new risk. |
| Daily 3% equity limit; halt/cancel at 2%, latch until next daily run after UTC reset | risk.evaluate and engine.tick | Boundary, persistence, stale data and reset tests. Propr's actual day-start field must be mapped. |
| Static 6% equity limit; kill at 4.5%; no automatic restart | risk.evaluate; Store kill latch | Explicit manual reset only after fresh flat-account confirmation. |
| Cancel entries, reconcile/close, retain stops until flat, verify all orders terminal, retry unresolved shutdown | engine.shutdown/close_position; service monitor | Rejected closes/cancels and unknown intents cannot mark shutdown complete. No blind safety-worker exit. |
| Continuous risk monitoring, stale data blocks entries, recovery without stale replay | service monitor every five seconds plus API latency; snapshot maximum age 30 seconds | Worker lifecycle and slow-read tests. Network calls and shutdown retries can extend cadence; actual host must be tested. No timing guarantee. |
| Backtest shared functions, instrument costs/funding/slippage, no same-close fill, disclosed limitations | backtest.py and CLI backtest | Next-bar-open scenario proxy. Daily data cannot reconstruct IOC fills/queue position or intraday ordering. Finer-data execution comparison remains research work; no statistical superiority claim. |
| Equity, win/loss statistics, drawdown, trades, flat stretch, target timing, start-window denominator/reasons | private reports/backtest.md and JSON | 90-day nonoverlapping evaluation windows with 60-bar warmups. Possible intraday breaches are uncertainty flags, not observed failures. |
| Daily signals/orders/fills/stops/reasons/balances/P&L/positions/distances | engine.write_report plus daily JSON/JSONL, HALT.md | Readable reports and private raw structured records. Actual Propr trade-field interpretation must be checked on connection. |
| Credentials after offline checks; supported secret delivery; never keys in replies/Git/reports/arguments | config.load_key, CLI credentials, SETUP.md | Environment or protected .env; domain-scoped secret injection remains platform-specific setup. Account ID stored explicitly in config; CHALLENGE_ACCOUNT_ID, if supplied by the platform, must match it. |
| Verify explicit trial account; don't infer from name or auto-select; separately authorize paid | account.snapshot, CLI inspect/verify/approve-trial/approve-paid | Account/attempt/challenge mappings deliberately require observed authenticated response fields; no invented default schema. |
| Restrict endpoints; Hyperliquid public data only; no purchase/transfer/payout | propr.Client write allowlist; data.public_info separate transport | Off-origin and non-order write rejection tested. |
| Exact builder attribution, override, empty opt-out, no leakage | propr.DEFAULT_BUILDER_CODE and HTTP Client | Actual serialized-request tests cover default/override/empty; redirects refused. README explains attribution without promising rewards. |
| Tests before start; inspect real worker and schedule; order/stop IDs; distinguish no-signal from fill | CLI approval and service; SETUP.md acceptance steps | Offline execution works; first authenticated Propr fill/stop and cloud persistence still need user acceptance. No forced demonstration trade. |
| Notify errors/halts/decisions, routine reports in files | Persistent logs/HALT/status; installer configures platform-supported notifications with user authorization | No universal notification transport is assumed or silently created. |
| Keep shared updates controlled and preserve operational state | updates.py, UPDATES.md; separate release checkout/tests; explicit flat maintenance | Never auto-replace running code. Real account update/recovery acceptance pending. |

The original names `run_daily.py` and `risk_monitor.py` are responsibilities implemented by `Engine.scan` and the monitored scheduler in `service.py`. This avoids two independent processes racing over the same account. The responsibilities and rules remain intact.

## First user acceptance run

Install the tagged release from GitHub using the page's exact setup prompt. Record cloud checks, choose markets, inspect the supplied free-trial account, configure only observed fields, run verification and the scenario backtest, approve that account, then start the supervised service. Observe a qualifying order, actual fill and protective stop; test task-ending persistence, reconnect, stop-to-flat and state-preserving restart. Until those observations exist, report them as unverified rather than dropping the corresponding requirement.

## Additional user requirements

On October 8, 2026, the user requested support for future strategies with their own data/timeframe requirements. This is separate from the preserved original system and does not authorize weakening its 60-daily-bar requirement. See [STRATEGIES.md](STRATEGIES.md) for the current coupling, intended module boundaries, multi-account/shared-account distinctions and acceptance criteria. Strategy selection is planned, not implemented in the current beta.

The user also requested an onboarding path to describe, import or build a private custom strategy after account connection. The agent must clarify and confirm rules, implement and test a local extension, and use shared account risk/execution. Strategy source, parameters and results stay on the user's VM; public sharing is a separate explicit action. The authoring workflow and acceptance requirements are in STRATEGIES.md; this remains planned functionality.

## Trial order-limit policy revision (October 8)

The user asked for self-service setup without a required provider-support exchange.
Beta.8 explicitly separates unknown lower-bound order filters from verified risk
ceilings and contract/precision/stop checks. The trial-only broker-validation
policy is documented in [ORDER-LIMITS.md](ORDER-LIMITS.md); it never claims unknown
minima are verified or changes the archived original. Paid/default strict mode
still requires known minima. Actual Propr execution and cloud recovery remain
outstanding acceptance checks.

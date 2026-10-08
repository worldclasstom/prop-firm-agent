# Set up and run the kit

These instructions are for the AI agent doing the installation. The visitor gives you the starting prompt, chooses markets and supplies access to a Propr free trial. Install the shared framework and configure a private instance on your existing cloud VM. Handle the files, configuration and commands for them. Keep their API key, account ID, chosen markets, configuration, order history and reports in private storage on that VM, outside the source checkout. Never publish those files or send them to Prosperity Labs. Reuse the framework's execution and risk components rather than generating a separate engine for every user.

The kit contains executable trading code. v0.2.0-beta.4 is a trial-testing beta. Mocked execution tests pass, but real Propr execution and Dot cloud persistence have not yet been verified together. Report that distinction plainly. Do not rebuild the strategy from scratch or claim you started it merely because installation succeeded.

## 1. Install the shared release and run offline tests

Use your existing cloud computer. Do not ask the visitor to buy hosting, configure SSH or keep their laptop on. If Dot delegates to Codex cloud, use a configured cloud environment for this repository. Guide only missing in-app setup and pass the repository and full instructions to the task.

```sh
git clone --branch v0.2.0-beta.4 https://github.com/worldclasstom/prop-firm-agent.git
cd prop-firm-agent
python3 -m venv .venv
. .venv/bin/activate
python -m pip install .
python -m unittest discover -s tests -v
propfirm init
propfirm doctor
```

Python 3.11+ and a POSIX cloud runtime are required. Do not change the user's operating environment silently. `PROPFIRM_HOME` defaults to `~/.prosperity-agent`. Keep it on persistent private storage outside the source checkout. For another account, use a separate directory. `init` preserves existing configuration. Record the release and commit you installed.

Read [SPECIFICATION.md](SPECIFICATION.md). The original full build prompt is preserved unchanged there and in [original-build-prompt.txt](original-build-prompt.txt). Use [REQUIREMENTS.md](REQUIREMENTS.md) to check implementation and outstanding validation.

## 2. Check the cloud runtime and prepare the watchlist

Ask the visitor which Propr markets they want. Use `propfirm markets` for native Hyperliquid perpetuals and `propfirm markets --dex xyz` for that builder's markets. Preserve exact identifiers such as `xyz:GOLD`; other namespaces must be verified against the provider's metadata.

Use `examples/runtime.json` as a template in the private kit directory. Record observations for persistent storage, supported secret entry, outbound HTTPS to `api.propr.xyz` and `api.hyperliquid.xyz`, background Python execution, recovery across idle/task boundaries and the platform's process supervisor. Actively investigate and configure supported alternatives when a default tool is missing; the absence of systemd alone does not establish that background work is unavailable. Preserve completed setup, and ask the visitor only for a concrete required action. Mark a check verified only after observing it. Include the actual cloud host identity in `host_identity` and set `PROPFIRM_HOST_ID` to that same value in the worker environment.

`propfirm runtime-probe --seconds 600` writes a harmless heartbeat. Run it through the platform's supported background mechanism, end the initiating task where supported, then inspect whether timestamps continued. A probe completing while you watched it is not evidence of surviving task termination. Record the test interval and result, including any remaining uncertainty. Do not assume `nohup`, systemd or a Dot reminder is sufficient. The runtime evidence is checked at startup and must be less than seven days old. If the platform cannot support the worker, state the specific blocker and leave trading off.

## 3. Connect and verify the selected account

First confirm whether the visitor already has a Propr account and has selected Free Trial. Reuse answers they have already given. If they need an account, give them https://app.propr.xyz/r/4ZZFhyJg with this explanation:

> Create your account, choose Free Trial, then return to this conversation to continue setup. This is Prosperity Labs' referral link. They may earn a commission if you later buy a challenge through it, at no extra cost to you. This supports building free tools like this.

Use an existing account when they have one. Do not ask for a duplicate account or a paid challenge. Their confirmation helps setup; it does not replace the API checks below that verify the selected account is a free trial before orders are allowed.

After offline tests pass, use the platform's native private credential form if it can supply `PROPR_API_KEY` to this worker. Otherwise use the kit's built-in form:

```sh
propfirm connect
```

Keep this command running in a tool session while the user completes the form. It prints a unique loopback URL and closes after one successful save or ten minutes. Open that URL using the browser on the **same cloud computer**. Verify the empty form loads, then present the platform's browser takeover/handoff so the visitor can paste their key and press **Save API key**. Tell them: “Paste your Propr API key into this form, save it, then return here.” Do not send a localhost link for them to open in their personal browser: that would point to their device, not the cloud computer. Do not expose the form using a public tunnel or deploy it to Prosperity Labs. If the platform browser is on a separate host, investigate its supported private credential delivery or same-host browser access; do not label the input solved until the user can actually access it.

The form stores only the API key, as a mode-0600 `.env` outside the source checkout. It does not contact Propr or authorize trading. It has no analytics, external resources or request logs. Avoid taking screenshots or reading form values while the user enters a real key. Resume when it reports **API key saved**, and check the command's success without printing the key. An expired form can be reopened with the same command. Reuse a working saved credential instead of asking again. Hidden terminal input via `propfirm credentials` remains an alternative when the platform offers the user a private interactive terminal. A missing platform secrets widget alone is not a reason to stop before trying these supported inputs.

Ask for the explicit free-trial account ID if it is not already known. Domain-scoped secret injection is supported through the platform's documented mechanism; do not mistake a proxy placeholder for an invalid key. Never put a key in a chat reply, command argument, repository, report or issue.

```sh
propfirm inspect --account-id 'THE_SELECTED_ACCOUNT_ID'
```

This makes authenticated reads and saves `setup/account-inspection.json` privately. It contains the exact account, matching challenge attempt and linked challenge. It sends no orders. The official docs leave some account fields unspecified, so use this observed response to populate `account_mapping` in private `config.json`. Do not guess a field, use an account name as proof, or set `trial=true` locally as a substitute for Propr's response.

Each mapping is `{ "source": "account" | "attempt" | "challenge", "path": ["actual", "field"] }`. Numeric fields can be strings or numbers. Required mappings:

| Mapping | Meaning |
| --- | --- |
| `trial` | A server-returned explicit trial/type/mode field, with `equals: true` or the server's literal `trial` / `free_trial` value. |
| `starting_balance` | Original challenge balance. Must remain fixed. |
| `day_start_balance` | Propr's current UTC day-start balance, not current equity. |
| `day_reference` | The date/ISO timestamp belonging to that day-start reference. |
| `balance` | Current account balance. |
| `equity` | Current account equity, including open P&L. |
| `daily_loss_fraction` | Must equal 0.03. Add `scale: 0.01` if the API expresses it as 3 rather than 0.03. |
| `max_drawdown_fraction` | Must equal 0.06. Same explicit scale convention. |
| `profit_target_fraction` | Must equal 0.10. Same explicit scale convention. |
| `drawdown_type` | Explicit static drawdown field, with `equals: "static"`. |

If no direct equity field exists, map `unrealized_pnl` and `isolated_position_margin` instead. The official SDK computes equity as balance + unrealised P&L + isolated position margin. Verify this against the actual account and dashboard before approval. Record field meanings and source evidence in `mapping_evidence`. If the needed values cannot be established, report the missing field or schema conflict; do not bypass verification. Account adapters can be improved centrally after the first real response is observed.

For each selected instrument, fill a market object from verified API/documentation metadata:

```json
{
  "asset": "EXACT_PROVIDER_IDENTIFIER",
  "base": "EXACT_PROPR_BASE",
  "quote": "USDC",
  "product_type": "perp",
  "sz_decimals": 2,
  "quantity_step": "0.01",
  "minimum_quantity": "VERIFIED_VALUE",
  "minimum_notional": "VERIFIED_VALUE",
  "multiplier": "VERIFIED_USDC_VALUE_PER_PRICE_POINT_PER_UNIT",
  "sessions_utc": "24/7",
  "stop_supported": true,
  "evidence": "Source and observation establishing these fields",
  "fee_per_side": "VERIFIED_OR_DISCLOSED_ASSUMPTION",
  "slippage_per_side": "DISCLOSED_ASSUMPTION",
  "daily_funding_cost": "VERIFIED_OR_DISCLOSED_ASSUMPTION"
}
```

The strings marked VERIFIED are instructions, not valid configuration values. Do not copy the illustrative precision or 24/7 session without checking the chosen instrument. For noncontinuous sessions, use `[{"weekday": 0, "start_minute": 0, "end_minute": 1440}]` with actual UTC windows, split at midnight. Update windows for seasonal/calendar changes and do not infer that an underlying stock's exchange hours equal its perpetual's hours. This adapter supports verified linear USDC perpetuals across asset classes; report any unsupported contract or settlement currency without substituting another market.

`verify` rechecks Propr market availability via the documented margin-config read, metadata precision, at least 60 complete daily bars, trial identity and challenge rules. It never changes leverage. Verify stop support from the current documented instrument/API capability; the first actual fill must then confirm its protection at Propr.

```sh
propfirm verify
propfirm backtest
```

Read private `reports/backtest.md`. The daily-data model uses next-bar-open fill proxies and disclosed per-instrument fees/slippage/funding assumptions. It cannot prove IOC fill rates or establish which entry type performs better. Missing/inadequate data and possible intraday breaches are reported as limitations. Defaults are assumptions, not measured account costs.

## 4. Start and verify actual trial trading

Use an empty, dedicated trial account so the service can manage every position on it. Keep `account_mode` set to `trial`. Finish runtime evidence, record the config digest with the command below, and set `checked_at` to the actual observation timestamp. The setup agent handles this technical step.

```sh
python -c 'from propfirm.config import root_dir, read_json, digest; print(digest(read_json(root_dir()/"config.json")))'
propfirm approve-trial --account-id 'THE_SELECTED_ACCOUNT_ID'
propfirm start
```

`start` is the real trading service, not a dry run. Run it under the verified cloud supervisor. It polls risk every five seconds plus API latency, starts risk monitoring before the first scan, and performs one daily scan at/after 00:10 UTC. A startup after that time gets one scan of the latest completed daily bar; durable intent keys prevent duplicate entries. A single account-state lock prevents a second local worker. Do not run the same account from a second cloud environment.

Orders go to Propr when a rule qualifies. There is no forced demo trade. The default is limit/IOC at the fresh ask or bid. Market/IOC is an explicit `entry_order_type` option. Partial fills receive protective stops; an unconfirmed stop triggers a latched shutdown. API interruptions block entries and preserve known stops. The service retries shutdown reconciliation until it confirms flat, all orders terminal and no unresolved intent.

```sh
propfirm status
```

Verify the actual worker PID/supervisor, current risk heartbeat, UTC schedule, Propr orders, fills and stop IDs. Check again after the initiating task ends. Report whether it is connected, running without a signal, submitted, filled and protected, or blocked. A passing mock test is not a real fill test. Return the checklist, tests, backtest and daily report. Do not send routine chatter; notify the visitor about errors, halts and required decisions through a supported channel they authorize.

## Stop, recovery and paid accounts

`propfirm stop` requests flattening through the active worker. Check `status` for `shutdown_complete` and verify Propr is flat. If the worker is down, restart it through the supervisor so its persistent stop/kill latch can finish reconciliation. Do not clear state to get around a failure. If you must intervene in Propr, reconcile afterward. Closing a chat or canceling a Dot reminder does not close positions.

`propfirm resume-entries` clears an entry block only after reconciliation; it does not clear a kill. `propfirm reset-halt --account-id ID --confirm-flat` is an explicit manual reset, allowed only with a stopped worker and fresh confirmation of no positions or active orders. It preserves intent history, so it cannot repeat the same day's entry.

A paid challenge requires a separate private state directory, explicit account ID and `account_mode: "paid"`, observed proof of its mode and rules, fresh checks, and the separate `approve-paid --account-id ID --acknowledge-paid-risk` command. Do not perform that transition unless the user explicitly authorizes paid trading. The kit never purchases a challenge, transfers funds or requests payouts.

## Attribution and updates

The default `X-Builder-Code` is `builder_pigUW7hSDKW52DhhFxFyYkRVxq3T7FIq`. `PROPR_BUILDER_CODE` overrides it; an explicitly empty value disables it. `X-API-Key` uses the trader's separate key. Both headers go only to `https://api.propr.xyz`; redirects are refused. Attribution does not change strategy, sizing or fees, and no reward entitlement is promised.

See [UPDATES.md](UPDATES.md) for release checks and a tested, separate checkout. Never auto-update a running trader.

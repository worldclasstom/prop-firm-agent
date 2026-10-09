# Set up and run the kit

These instructions are for the AI agent doing the installation. The visitor gives you the starting prompt, chooses markets and supplies access to a Propr free trial. Install the shared framework and configure a private instance on your existing cloud VM. Handle the files, configuration and commands for them. Keep their API key, account ID, chosen markets, configuration, order history and reports in private storage on that VM, outside the source checkout. Never publish those files or send them to Prosperity Labs. Reuse the framework's execution and risk components rather than generating a separate engine for every user.

The kit contains executable trading code. v0.2.0-beta.9 is a trial-testing beta. Mocked execution tests pass, but real Propr execution and Dot cloud persistence have not yet been verified together. Report that distinction plainly. Do not rebuild the strategy from scratch or claim you started it merely because installation succeeded.

## 1. Install the shared release and run offline tests

Use your existing cloud computer. Do not ask the visitor to buy hosting, configure SSH or keep their laptop on. If Dot delegates to Codex cloud, use a configured cloud environment for this repository. Guide only missing in-app setup and pass the repository and full instructions to the task.

```sh
git clone --branch v0.2.0-beta.9 https://github.com/worldclasstom/prop-firm-agent.git
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

Test lifecycle behavior with the harmless probe before trading: distinguish a
worker crash, a supervisor crash, an initiating task ending, and host idle or
restart. Record which actually occurred, heartbeat timestamps and gaps, and how
the process returned. Restarting Supervisor yourself tests state preservation,
not autonomous recovery. Investigate the host's supported lifecycle/startup hooks
and configure a documented hook when available; do not invent one or treat an
LLM reminder as the five-second risk loop. Never reboot/delete the user's Dot or
host as a surprise test. If a particular user action is necessary, give the
smallest concrete action and preserve setup for resumption.

After a supervisor crash, verify the worker's ownership as well as its heartbeat.
The October 8 Dot probe restarted an inner supervisor while its old test worker
remained alive without supervision and held the worker lock. Manual cleanup was
needed; that is a failed autonomous recovery test. A later idle test passing does
not supersede that failure. Use harmless workers to prove that the supported
recovery mechanism restores exactly one supervised worker without manual cleanup,
either through supported reattachment or controlled shutdown and replacement.
Record worker and supervisor identities, lock ownership, and the recovery interval.
Do not delete `worker.lock` to admit a replacement: a living worker can still hold
the original file open, allowing duplicate workers if the pathname is recreated.
Preserve trading state and shutdown/protection behavior; never use broad process
cleanup or kill an active safety worker just to make the recovery check pass.
Requested-stop process-group settings alone do not prove recovery from a supervisor
crash. Capture the actual launcher/supervisor configuration before changing it.

If API calls work in a command tool but fail in the background worker, run
`scripts/runtime_network_probe.py` from the repository with the worker's Python
through each launcher. This standalone diagnostic uses public Propr health and
Hyperliquid metadata reads. It does not load credentials, follow redirects, place
orders, change networking, or certify readiness. Save each JSON result privately,
label its launch context, and compare HTTP status/errno and proxy/certificate
setting presence. It deliberately omits setting values and exception messages.
A 401/403 is an HTTP response, not successful application access; a successful
public probe still requires authenticated REST and live-mark verification from
the actual worker context.

Inspect the exact supervisor environment and supported platform networking
configuration privately. Missing supported proxy or certificate configuration
may explain a difference, but do not assume it does. Configure only documented,
authorized settings for that runtime; do not copy temporary command-tool access
tokens, disable certificate validation, remove an enforced proxy, create a tunnel,
or otherwise route around platform restrictions. Recheck connectivity and recovery
in the actual worker context after any supported correction. Command-tool success
must not be reused as evidence that a different background environment works.

When the desktop path lacks the command tool's managed network route, inspect
whether the command environment itself offers a supported persistent-worker
mechanism. Do not transfer its loopback proxy to another network namespace.
If that mechanism is supported, test a bounded, harmless worker there using
repeated public reads and heartbeat timestamps before and after the initiating
task actually ends. A command returning while its tool session remains active is
not task teardown. Record the lifecycle event and continuous results together;
a heartbeat-only desktop test cannot establish network survival in this context.
Reuse equivalent completed evidence instead of repeating it. Do not keep the
task alive artificially to manufacture a passing lifetime test. If no supported
mechanism is exposed, record that exact missing capability rather than retrying
the same desktop launch or treating it as a request for broader permissions.
Passing this bounded probe still requires authenticated REST/live marks and the
remaining supervisor and host-recovery checks before trading.

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

After the form succeeds and the visitor returns control, resume setup by running the read-only discovery command with the saved key. Do not wait for them to find or type an account ID:

```sh
propfirm accounts
```

This follows every page of `/v1/challenge-attempts` and `/v1/challenges`, groups attempts by `accountId`, prints account choices and saves the exact response documents privately in `setup/account-discovery.json`. It does not select an account, change configuration or approvals, or place orders. These endpoints and `accountId` are documented in [Propr's official SDK](https://github.com/XBorgLabs/propr-docs/blob/main/python/propr_sdk.py). Do not use the SDK's automatic first-active-account selection.

Present a short numbered list with the account ID, challenge name when returned, and attempt status. Inspect the private API documents for explicit account-type evidence; you may use `propfirm inspect` below to read a candidate's details before confirmation. Label an unestablished type **unverified**, never infer free trial from `active`, a name, a balance or list order. Ask “Which account would you like to use?” For a single candidate ask “Use this account?” The visitor can answer by number or name; bind their answer to the exact ID you displayed. Disambiguate repeated names. Reuse an already explicit account choice only if its ID matches a returned account. Discovery is not trading approval; complete trial proof and all existing checks below.

If there are no accounts, help the visitor check key access and create/select **Free Trial** in Propr, then rerun discovery. Do not suggest buying a challenge. An authentication/network error is not an empty account list. If an attempt has no account ID or one account has multiple attempts, inspect the schema and resolve the ambiguity rather than guessing or dropping it silently. Paid and inactive accounts can appear in the list; they are not eligible for automatic trial startup.

For multiple accounts, keep one explicitly selected account per private `PROPFIRM_HOME`, with separate configuration, approval, state, reports and supervisor identity. Never overwrite an existing instance to switch accounts or share its positions, halt flags or approval with another account. The agent creates and manages the separate directories; the visitor only chooses the account. Before activating another instance on an account, check existing managed workers to avoid duplicate traders. This command supports account discovery, not automatic portfolio-wide trading.

Domain-scoped secret injection is supported through the platform's documented mechanism; do not mistake a proxy placeholder for an invalid key. Never put a key in a chat reply, command argument, repository, report or issue.

```sh
propfirm inspect --account-id 'THE_SELECTED_ACCOUNT_ID'
```

This retrieves the account, the detailed matching attempt, linked challenge and
`GET /v1/accounts/{accountId}/daily-metrics`. It saves the response privately in
`setup/account-inspection.json`, plus a proposed mapping report in
`setup/account-mapping.json`. It sends no orders and never overwrites configuration
or approvals. The agent handles the following configuration; do not ask the visitor
to find JSON fields or paste account exports.

Use `account_adapter: "propr-v1"` in private `config.json`. Copy `account_mapping`
and `mapping_evidence` from the inspection report. The adapter resolves
`attempt.currentPhaseId` through `attemptPhaseId`, then joins `phaseId` to the
challenge rules on every read. It validates identity, active status, starting
balance, USDC settlement, Hyperliquid venue and the unchanged 3% / 6% / 10% static
rules. Phase array order is never treated as identity.

For trial eligibility it checks the linked paper account, exact `free-trial`
catalog slug, matching product ID and active one-time prices that are all zero.
This composite check uses the actual observed catalog structure; a display name,
`paper` alone, or a local `trial=true` flag does not qualify. Missing or conflicting
product evidence fails verification. Paid accounts require the separate explicit
mode proof and authorization described below.

**Daily reference:** the [official developers page](https://www.propr.xyz/developers),
Integration → Deriving Live Values, documents `daily-metrics` and the formula
`startingBalance + startingIsolatedPositionMargin`. Its date key and response
envelope are not illustrated. Inspect the actual authenticated response and add
`daily_metrics_binding` with:

- `rows_path`: the array of actual keys leading to the daily row or rows; use `[]`
  only if the response itself is that row or array.
- `date_path`: the actual key path within a row identifying its UTC reference day.
- `evidence`: the observed field meaning, source and inspection date.

No guessed date keys are provided here. Accept only a dated current UTC row for
the selected account. Do not use the current balance, generic `updatedAt`, a local
clock substituted for a provider date, or diagnostic values. A stale row at UTC
rollover blocks entries until fresh data arrives. If the actual response has a
different shape, retain it privately, implement and test the documented mapping,
and continue; request a provider clarification only for unresolved semantics.

**Live equity:** REST mark prices can lag according to the same Integration page.
The adapter therefore authenticates to `wss://api.propr.xyz/ws` and uses
`mark.updated` prices for each open position, plus REST balance and isolated
margin. Gross position exposure also uses fresh marks for the 2x cap. `verify`, approval and the risk worker require a connected stream. Missing
or more-than-ten-second-old marks, invalid position fields, a disconnect, or an
account event during a state read fail the read and prevent new entries. Reconnect
clears the old marks. Existing protective orders remain at Propr; the worker
retries checks. Verify this feed and equity against the actual account before
activation. REST unrealized P&L is only a diagnostic snapshot, not the live risk
price source for this adapter.

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

Keep a private per-market checklist with separate **verified**, **excluded** and
**pending** states and the source/time for each observation. Keep the user's
requested universe separate from the fully verified live configuration. An empty
live watchlist means instrument verification is unfinished; do not ask the user
to repeat a market choice they already gave. Do not silently narrow an all-market
request. Present verified choices and unresolved markets if a smaller initial
watchlist would help, and obtain their choice before activating it.

As inspected October 8, Propr's [Account Settings reference](https://www.propr.xyz/developers)
lists minimum quantities for seven symbols; the documented margin-config
response confirms availability but does not specify quantity/notional minimums.
Check current official sources and actual read-only metadata for the chosen
instrument. Quantity precision is not minimum quantity, and Hyperliquid's venue
minimum is not proof of Propr's broker minimum. Do not infer zero/no minimum from
an absent field or send test orders to discover constraints.

For a verified free trial, missing published lower bounds need not require a
support conversation. Use the [trial broker-validation policy](ORDER-LIMITS.md):
set `order_limits_policy: "trial_broker_validation"`, preserve known minimums,
and set only unpublished `minimum_quantity` / `minimum_notional` to JSON `null`.
Add `limits_evidence` on each affected market recording the actual sources
checked and which lower bounds are unknown. The setup agent handles these fields;
do not ask the visitor to find limits or enter JSON. Tell them that qualifying
orders may be rejected and will not be resized upward or automatically retried.
Do not call unknown limits verified, or let an unresolved availability, precision,
contract, stop-support or runtime check use this exception.

This is an explicit revision of the beta.7 preflight policy for trial order
minimums, not an edit to the archived original specification. The strict
`verified` policy remains the default for existing configurations; paid accounts
cannot select the trial policy. A changed configuration requires fresh trial
verification/approval as usual. Unknown minimums must remain disclosed in
research results; a simulated fill cannot prove broker acceptance.

Checkpoint permitted read-only checks as each completes. A timeout is pending,
not an unsupported market. On a platform approval-review cancellation, preserve
progress, inspect its reason and any actual pending user action, and respect the
decision. Resume only through permitted operations; changing wrappers or batch
sizes to evade a review is not a fix. Continue independent offline work.

```sh
propfirm backtest
propfirm verify
```

Historical research can run before account verification. Use
`propfirm backtest --config /absolute/private/research.json` for a separate
verified research watchlist when the live watchlist is still being prepared.
Set `backtest_initial_balance` explicitly to the intended scenario balance; the
default is 25,000 USDC. The report labels this as research, never trading approval.
It needs validated market metadata and history, but no API key, trial proof or
live stop-support assertion. Do not enable a live market solely because its
research run succeeds.

Read private `reports/backtest.md`. The daily-data model uses next-bar-open fill proxies and disclosed per-instrument fees/slippage/funding assumptions. It cannot prove IOC fill rates or establish which entry type performs better. Missing/inadequate data and possible intraday breaches are reported as limitations. Defaults are assumptions, not measured account costs.

Research windows use non-overlapping, complete 90-day UTC calendar intervals.
Each starts flat and retains all available prior bars for indicator calculation;
each instrument becomes eligible only after 60 prior bars. Recently listed
markets remain in the universe without erasing older markets' history. Reports
include per-market coverage, missing-day flags and an uncounted partial tail.
An early risk stop remains a flagged scenario, not 90 successfully traded days.
Neither the window count nor an unflagged window establishes a challenge pass.

## 4a. Scheduled execution instead of a persistent worker

If the platform cannot provide a supported persistent worker with network access, or the visitor used the scheduled setup prompt, use the documented revision in [SCHEDULED-EXECUTION.md](SCHEDULED-EXECUTION.md). Set `execution_model: "scheduled"` and `tick_interval_minutes` in private `config.json`, record evidence following `examples/runtime-scheduled.json`, approve as below, and schedule `propfirm tick` from the runtime in [examples/scheduled-agent](../examples/scheduled-agent) or another scheduler with persistent state and a private secret. Section 2's supervisor, host-identity and idle-recovery checks do not apply to that model; its check run replaces them. `start` refuses a scheduled configuration. Disclose the accepted risk from that document to the visitor: the equity halts are evaluated at the tick cadence, with the resting stops at Propr as the only protection between ticks.

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

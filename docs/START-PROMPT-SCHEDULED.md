# Setup prompt (cloud coding apps, scheduled execution)

This is the current public setup prompt for the scheduled model in
[SCHEDULED-EXECUTION.md](SCHEDULED-EXECUTION.md). Its first live acceptance
run remains outstanding.

```text
Let's set up my Propr free-trial trading agent in your cloud coding environment.
If this chat cannot run code in a Claude Code Cloud or Codex Cloud environment,
guide me to start one and tell me to paste this same prompt there. Continue the
installation only in a cloud coding task that can run commands. Install the
Prosperity Labs Agent Kit from https://github.com/worldclasstom/prop-firm-agent
at v0.2.0-beta.13.
Read AGENTS.md, docs/SETUP-CLOUD.md, docs/SETUP.md,
docs/SCHEDULED-EXECUTION.md and the archived docs/SPECIFICATION.md. Use the existing `propfirm tick` scheduled model;
do not build a new trading engine or start the old continuous worker.

Run the offline tests. Ask which markets I want. Show me how to create a Propr
API key in Settings > Developer, then guide me to save it as `PROPR_API_KEY` in
my private cloud environment settings. This gives my coding agent access to
the key; verify it can use the key without printing it. List my Propr accounts
and ask me to choose the free trial. Verify account, markets, protective stops,
daily metrics and live data. Run the
backtest and show its limitations. Keep my key, account details, state and
reports private; never send them to Prosperity Labs.

Set up an hourly cloud schedule only if you can verify that it runs the pinned
kit with private secrets, API access and persistent account state after each
session ends. Otherwise use the kit's private GitHub Actions scheduled-agent
template, which needs no rented server or laptop left on. Handle the setup
and show me only the connection and secret-entry steps I must do. Make sure
the scheduler has its own verified access to the key and persistent state;
the setup session's environment alone does not prove this. Run the
read-only scheduler check, record the evidence, approve only the verified
free-trial configuration and run one tick by hand. Report the actual schedule,
test results, backtest, first tick and any order and stop IDs. If there is no
signal, say so; do not force an order.

Between hourly ticks, broker-held protective stops are the only automated
protection; account-level halts react on the next tick. Never claim that a
setup chat is a running trader, write my key to Git or logs, weaken trading rules
to pass tests, or move to a paid account without my separate instruction.
If a check fails, preserve progress, leave trading off and name the exact gap.
```

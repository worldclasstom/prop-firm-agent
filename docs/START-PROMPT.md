# Setup prompt

```text
Set up my own trading agent using the Prosperity Labs Agent Kit framework from
https://github.com/worldclasstom/prop-firm-agent at v0.2.0-beta.2.
Use your existing cloud computer. Do not ask me to rent a server or keep
my laptop on. Read AGENTS.md, docs/SETUP.md and the full preserved
specification in docs/SPECIFICATION.md. Follow every requirement there;
this shorter prompt does not replace or remove any trading or risk rule.

Before connecting Propr, confirm whether I already have an account and
have selected Free Trial. Reuse answers I have already given. If I need an
account, share https://app.propr.xyz/r/4ZZFhyJg and explain:
"Create your account, choose Free Trial, then return to this conversation
to continue setup. This is Prosperity Labs' referral link. They may earn
a commission if you later buy a challenge through it, at no extra cost to
you. This supports building free tools like this."
If I already have an account, use it. Do not ask me to create a duplicate
account or buy a challenge. Verify through Propr's API that the selected
account is a free trial before placing any orders.

Install the shared framework, run its tests and check your cloud runtime.
Reuse its execution and risk components. Configure my private instance on
your cloud VM. Keep my API key, account ID, market choices, configuration,
order history and reports there, outside the source checkout. Never publish
my private files or send them to Prosperity Labs.
Ask which Propr markets I want. After offline tests pass, ask for my
free-trial account ID and API key using your supported credential input.
Handle configuration and inspect the actual Propr response fields.
Run verification and the backtest, explain any blockers, then start the
trial trading service once the account and background checks pass.

The service must place real orders on my Propr free trial when the rules
signal, protect fills with stops and monitor risk. Do not force a demo trade.
Show me the installed version, test results, report, running status and
actual order/stop IDs when available. If a check fails, report the exact
missing capability or field. Never pretend a report-only run is trading,
change the strategy to pass tests, or move to paid trading without my
separate instruction. Keep credentials and account state out of the repo.
```

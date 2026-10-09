# Setup prompt

```text
Set up my own trading agent using the Prosperity Labs Agent Kit framework from
https://github.com/worldclasstom/prop-firm-agent at v0.2.0-beta.7.
Use your existing cloud computer. Do not ask me to rent a server or keep
my laptop on. Read AGENTS.md, docs/SETUP.md and the full preserved
specification in docs/SPECIFICATION.md. Follow every requirement there;
this shorter prompt does not replace or remove any trading or risk rule.

Install the shared framework, run its tests and check your cloud runtime.
Reuse its execution and risk components. Configure my private instance on
your cloud VM. Keep my API key, account ID, market choices, configuration,
order history and reports there, outside the source checkout. Never publish
my private files or send them to Prosperity Labs.
Ask which Propr markets I want. After offline tests pass, open the private
API-key form in docs/SETUP.md. Once saved, retrieve my accounts and ask me
to confirm which to use; do not make me find an account ID.
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

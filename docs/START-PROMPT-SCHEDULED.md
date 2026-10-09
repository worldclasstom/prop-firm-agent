# Setup prompt (scheduled execution, draft)

This is the short prompt for the scheduled execution model described in
[SCHEDULED-EXECUTION.md](SCHEDULED-EXECUTION.md). It is a draft pending the
first live acceptance run; the original [START-PROMPT.md](START-PROMPT.md)
remains the published prompt until then.

```text
Set up my own trading agent using the Prosperity Labs Agent Kit from
https://github.com/worldclasstom/prop-firm-agent at v0.2.0-beta.9, using its
scheduled execution model (docs/SCHEDULED-EXECUTION.md). Read AGENTS.md,
docs/SETUP.md and the full preserved specification in docs/SPECIFICATION.md.
Follow every trading and risk rule there; this shorter prompt does not replace
or remove any trading or risk rule, and docs/SCHEDULED-EXECUTION.md is the only
documented revision.

Install the kit, run its tests, ask which Propr markets I want, open the private
API-key form, list my accounts and ask me which one to use. Verify markets,
run the backtest and show me the results. Then set up the runtime from
examples/scheduled-agent as a private GitHub repository I own, with my API key
as a repository secret, run its check, record the evidence, approve the
verified free-trial configuration and run the first tick by hand. Show me the
installed version, test results, backtest, the check run and the first report.

Never put my key in chat, a commit or a report. Never pretend a report-only run
is trading, change the strategy to pass tests, or move to a paid account
without my separate instruction. If something is not supported, tell me the
exact missing capability and stop there.
```

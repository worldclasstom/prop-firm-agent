# Starting prompt

This is the development-alpha prompt. It asks the agent to continue unfinished work from shared source. Once trial execution is validated, it can become an installation-only prompt.

```text
Use https://github.com/worldclasstom/prop-firm-agent to set up my Propr
free-trial trading agent in your existing cloud environment.
Read AGENTS.md, STATUS.md and docs/SETUP.md first. Use the repository's
approved specification and tests. Continue unfinished implementation there;
do not independently redesign the strategy or claim unfinished code is running.
Check what your cloud environment supports and tell me any blockers.
Ask which Propr markets I want to trade. Request credentials only after the
build and offline tests are ready. Start trial trading only after the account,
protective orders and background risk checks are verified. Show me the tested
version, results and what is actually running. Never buy or trade a paid
challenge without my separate instruction.
```

For a repeatable test, record the exact commit or release used. Give a delegated coding task the repository and this prompt; it may not inherit the conversation. Changes belong in this shared project and should be reviewed and released before other users adopt them.

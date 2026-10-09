# Scheduled agent template

A private GitHub repository that runs `propfirm tick` on a schedule, per
[docs/SCHEDULED-EXECUTION.md](../../docs/SCHEDULED-EXECUTION.md). The setup
agent creates and fills it; the person only chooses markets, confirms an
account and pastes their key into GitHub.

## Layout

- `.github/workflows/agent.yml` runs the tick hourly at :10 UTC, commits
  `agent-home/` back, and marks the run failed when the tick exits non-zero.
- `agent-home/` is `PROPFIRM_HOME`: private configuration, approval, evidence,
  state and reports. It contains no key.
- `.gitignore` keeps `.env` and transient SQLite files out.

## Setup, performed by the AI agent

1. Complete the usual setup in the AI tool's computer: install the kit, run
   tests, discover accounts, verify markets, run the backtest. Set
   `execution_model: "scheduled"` and `tick_interval_minutes: 60` in
   `config.json`.
2. Create a private repository from this directory. The repository must be
   private: it will hold account identifiers, positions and reports.
3. Add the repository secret `PROPR_API_KEY`. The person pastes it in GitHub's
   secret form, never in chat.
4. Run the workflow by hand with `command: check`. It installs the pinned
   release and performs read-only calls to both APIs from the runner. Record
   the run URL and outcome in `agent-home/runtime.json` following
   `examples/runtime-scheduled.json`, with the config digest.
5. Approve the verified trial configuration with `propfirm approve-trial`,
   commit `agent-home/` (approval, evidence, config, markets, state, setup
   documents) and push.
6. Run the workflow by hand with `command: tick`, then read the committed
   report and `status.json`. From then on the schedule runs it.

## Operating

- Reports: `agent-home/reports/YYYY-MM-DD.md` in the repository.
- Status: `agent-home/status.json`; the Actions tab shows failed runs, which are
  exactly the ticks that exited non-zero.
- Stop: create the file `agent-home/STOP`, commit, and run the workflow by hand.
  The tick latches the stop, closes positions reduce-only, keeps stops until
  flat is confirmed and writes `reports/HALT.md`. Disabling the workflow alone
  does not close positions.
- Update: change the pinned tag in the workflow only after reading the release
  notes; the approval binds the release, so a new release needs fresh approval.

## Known platform properties

GitHub may delay scheduled runs under load; the tick records gaps. GitHub
disables schedules on repositories without activity for 60 days; the state
commits count as activity. Whether Propr accepts requests from GitHub-hosted
runners is established by the check run, not assumed.

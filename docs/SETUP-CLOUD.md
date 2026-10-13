# Set up from Claude Code or Codex Cloud

This is the viewer-facing route for the standalone Agent Kit. It does not use
Tally or a Prosperity Labs account. Start a **cloud** coding session in Claude
Code Desktop or Codex in the ChatGPT desktop app, then paste the prompt in
[START-PROMPT-SCHEDULED.md](START-PROMPT-SCHEDULED.md). The coding agent handles
the files and checks; the visitor chooses a Propr free trial and markets and
enters their own key privately.

The trading program is deterministic Python. The AI session sets it up and
reviews reports; it does not decide whether to trade on each scheduled run.

## What runs after setup

Use the `scheduled` model in [SCHEDULED-EXECUTION.md](SCHEDULED-EXECUTION.md):
`propfirm tick` runs hourly, checks account equity and protective orders,
reconciles prior orders, performs the daily signal scan at or after 00:10 UTC,
writes a report, and exits. Between runs, confirmed reduce-only stops resting
at Propr are the only automated protection. The 2% daily halt and 4.5% static
drawdown kill switch are evaluated on each tick, so an hourly interval delays
their reaction compared with the archived five-second continuous model.
Propr's equity limits still apply at every moment. A late or missed scheduled
run widens the gap. Do not describe a completed setup task as a running trader.

## Choose a launch path

1. In Claude Code Desktop, start a **Cloud** coding session for setup. For
   operation, Claude documents hourly Cloud routines; do not choose a local
   scheduled task. Each routine run starts from a
   fresh repository checkout. Use a native routine for trading only after a
   harmless check proves that it can run the pinned kit, reach both APIs, read
   a private secret, and persist the same account state between runs. A cloud
   routine's green session status by itself is not proof that `tick` succeeded.
2. In Codex Desktop, choose **Cloud** to install and test the kit. Its documented
   project scheduled tasks currently run on the user's computer. Do not label
   those a cloud trading schedule. Test a native cloud scheduler only if the
   user's account actually exposes one with the same checks as above.
3. The common no-server runtime is
   [examples/scheduled-agent](../examples/scheduled-agent): a private GitHub
   repository with an hourly Actions workflow, a repository secret for the
   Propr API key, and private account state committed back between runs. The
   coding agent should prepare it and guide the user through the few GitHub
   connection and secret-entry steps it cannot perform itself. GitHub can
   delay a scheduled run. Observe a read-only check from the runner before
   enabling any trial orders.

Do not place the key in chat, a commit, or a public repository. Do not ask the
visitor to rent a server. Reuse the account and market verification steps in
[SETUP.md](SETUP.md), but use scheduled runtime evidence and `tick` instead of
the continuous supervisor checks and `start` command. This is a trial-testing
beta: no real Propr order, fill, and protective stop from a viewer-owned
scheduler has been accepted end to end yet. Keep trading off when a required
check is incomplete, and report exactly what remains.

The original continuous specification stays archived in
[SPECIFICATION.md](SPECIFICATION.md); the scheduled change is explicit in
[SCHEDULED-EXECUTION.md](SCHEDULED-EXECUTION.md).

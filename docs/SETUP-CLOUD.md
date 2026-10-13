# Set up from Claude Code or Codex Cloud

This is the viewer-facing route for the standalone Agent Kit. It does not use
Tally or a Prosperity Labs account. Start a **cloud** coding session in Claude
Code Desktop or Codex in the ChatGPT desktop app, then paste the prompt in
[START-PROMPT-SCHEDULED.md](START-PROMPT-SCHEDULED.md). If the prompt lands in
an ordinary chat, that assistant should guide the person to a cloud coding
task and ask them to paste the same prompt there before installing anything.
The coding agent handles the files and checks; the visitor chooses a Propr free
trial and markets and enters their own key privately.

The trading program is deterministic Python. The AI session sets it up and
reviews reports; it does not decide whether to trade on each scheduled run.

## If the prompt starts in a regular chat

The assistant should give the smallest handoff for the app in use, then have
the visitor paste the same prompt in the new cloud coding task. In Claude
Desktop, open the **Code** tab, select **Cloud**, and start a session. In Codex,
choose **Work in > Cloud**, then select a published environment or create one
with this repository and publish it. Do not claim that an ordinary chat has
installed the kit or started an hourly trader. Continue setup from the cloud
task rather than making the visitor rewrite the prompt.

## Connect the Propr key in the cloud environment

After offline tests pass, guide the person to Propr **Settings > Developer** to
create an API key. They add it to their *private* Claude Code or Codex cloud
environment settings as the environment variable `PROPR_API_KEY`. This gives
the coding agent access to the key; it is not hidden from the agent. Tell the
person who else can use that environment before they save it. Verify the key
works with a read-only account request without printing or logging the value.
Do not make the loopback `propfirm connect` form the default cloud path: use it
only if the cloud platform actually offers a same-host private browser handoff.

The setup environment's variable does not automatically follow the trader to
its hourly runtime. A Claude Cloud routine must use an environment that can
read `PROPR_API_KEY` on every run and persist account state. A GitHub Actions
runtime instead needs `PROPR_API_KEY` entered once into that private
repository's Actions secret form. Test the actual runtime with read-only
requests before approval. A domain-scoped network secret may be preferable
when supported, but this kit currently reads `PROPR_API_KEY` as an environment
variable and has not been validated with secret injection. Do not claim that
adding a network secret alone connects this release.

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

Use environment settings for key entry by default; the user may choose what
to disclose to their own AI session. Never commit or log the key. Do not ask the
visitor to rent a server. Reuse the account and market verification steps in
[SETUP.md](SETUP.md), but use scheduled runtime evidence and `tick` instead of
the continuous supervisor checks and `start` command. This is a trial-testing
beta: no real Propr order, fill, and protective stop from a viewer-owned
scheduler has been accepted end to end yet. Keep trading off when a required
check is incomplete, and report exactly what remains.

The original continuous specification stays archived in
[SPECIFICATION.md](SPECIFICATION.md); the scheduled change is explicit in
[SCHEDULED-EXECUTION.md](SCHEDULED-EXECUTION.md).

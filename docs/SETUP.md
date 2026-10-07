# Set up the development alpha

## With an AI agent

Use [the starting prompt](START-PROMPT.md). Dot, Codex, Claude or another capable coding agent can work from the same repository. The current release provides tested building blocks and a specification. It cannot yet connect to Propr or place orders.

Use the cloud environment already available to your agent. If cloud coding requires a repository selection, select `worldclasstom/prop-firm-agent` and configure that environment through the tool's supported setup. Do not assume every tool can run a persistent trading worker.

## Reproduce the developer checks

Python 3.11 or later and Git are needed. These commands are for the agent's workspace; visitors do not need to operate a laptop as a trading host.

```sh
git clone https://github.com/worldclasstom/prop-firm-agent.git
cd prop-firm-agent
git checkout v0.1.0-alpha.1
python3 -m venv .venv
. .venv/bin/activate
python -m pip install .
python -m unittest discover -s tests -v
propfirm doctor
propfirm init
```

`init` creates private configuration at `~/.prosperity-agent/config.json` and preserves an existing file. It does not request a key or make network calls. Settings and later account state belong outside the source checkout so code updates do not overwrite them.

`doctor` reports the Python version and marks untested cloud capabilities as unverified. A successful command exit means the report was produced. It does not mean a trading environment is ready. `propfirm start` deliberately exits with a blocker in this alpha.

## Before a trial can start

Implement the missing components listed in STATUS.md, using docs/SPECIFICATION.md as the acceptance criteria. Then verify the actual platform's persistent storage, secret input, outbound API access, saved daily schedule, continuous risk worker and recovery across idle/task boundaries. Record observations and timestamps in private reports. A launched process is not proof that it survives the end of a task.

After the offline checks pass, connect an explicitly selected Propr free-trial account using the platform's supported credential entry. Keep keys out of this repository, issues and reports. Read the account and reconcile its real definitions; do not infer trial status from its name or a user-written flag. Confirm fills and protective stops on Propr when a genuine signal occurs. Do not force a trade to produce a screenshot.

## Builder attribution

The public default is `builder_pigUW7hSDKW52DhhFxFyYkRVxq3T7FIq`. The prepared Propr request uses `X-Builder-Code`; the trader's private key uses `X-API-Key`. The initial helper accepts a replacement code or an empty string to omit attribution. No requests are sent in this alpha. Future execution must read the `PROPR_BUILDER_CODE` environment setting, preserving an explicitly empty opt-out.

Attribution does not change trading rules or sizes. We do not claim a reward rate or commission entitlement for the code. The referral link remains separate.

## Updates

Follow [UPDATES.md](UPDATES.md). This project does not automatically replace code while an account has open positions.

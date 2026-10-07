# Versions and updates

Install an exact release. `v0.2.0-beta.1` includes execution code but awaits real-account and Dot cloud acceptance testing. See STATUS.md for observed evidence.

```sh
propfirm check-update
propfirm prepare-update --version v0.2.0-beta.1
```

The first command reads releases and notes. The second clones the requested release into a separate directory under the private kit home, creates a virtual environment and runs the tests with isolated test state and no inherited API key. It never changes or restarts the running worker. A visitor normally uses this shared upstream; fork only when contributing a change.

Before applying an update, get the user's approval, review release notes and use a maintenance window. Request `propfirm stop`, keep the risk worker alive while it cancels entries, closes positions and reconciles, then verify `shutdown_complete` and the account itself. Stop the cloud supervisor only after confirmed flat. Back up the private kit home. Do not overwrite or publish its key, configuration, SQLite state, intent history, halt flags or reports.

Use the prepared checkout's virtual environment with the same persistent `PROPFIRM_HOME`. Run tests and verification. Review any documented migrations. This release's SQLite initialization preserves existing tables and intent IDs. Never delete state to fix an upgrade or rollback.

A kill/stop latch persists across versions. Reset only through `reset-halt --account-id ID --confirm-flat` after reviewing the reason. Approval is bound to configuration, account mode and executable version, so run the relevant trial/paid approval command again before switching the supervisor to the new executable. Verify status, reconciliation, stops and schedule after restart.

There is deliberately no unattended apply/update command. Preparing code is separate from applying it to a trading account. Rollback also needs a stopped, flat account and a compatible state schema; do not blindly restore old state after new orders.

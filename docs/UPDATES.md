# Versions and updates

Install an exact release. `v0.2.0-beta.9` includes execution code but awaits real-account and Dot cloud acceptance testing. See STATUS.md for observed evidence.

Beta.8 adds an explicit trial-only policy for unpublished order minimums; it is
not a claim that missing values equal zero. Read [ORDER-LIMITS.md](ORDER-LIMITS.md).
Existing configurations keep the strict `verified` default. Setup can select
`trial_broker_validation`, preserve known minimums, and explicitly record unknown
ones as null with source evidence. All other instrument/account/runtime checks
remain required. Paid accounts cannot select this policy. Entry rejection blocks
further entries without upsizing or resubmitting the rejected entry intent;
partial fills and failed protection retain the existing reconciliation/shutdown.
The policy change affects the config digest and needs fresh trial verification
and approval. No migration automatically changes private files or starts trading.

Beta.7 corrected research calendar windows and empty-watchlist diagnostics.
Preserve beta.6 account bindings, key, selected account and completed checks.

Beta.6 added `daily-metrics`, ID-based active phase joins, linked trial-catalog
verification, live Propr WebSocket marks for equity, and historical research
separate from broker verification. It requires the pinned `websockets` dependency
installed by pip. It does not migrate or overwrite private configuration,
approvals or trading state.

For installations older than beta.6, preserve the saved key, selected account,
non-FX preferences, completed checks and private files. Follow SETUP.md to inspect
the selected account again, set `account_adapter: "propr-v1"`, copy the generated
mappings, and bind the actual daily-metrics envelope/date. Do not delete state or
ask the visitor to supply the key or account ID again. The setup agent performs
this migration; new config and executable version require fresh verification and
approval. Old generic mappings remain readable, but do not claim they include the
new Propr live-equity or catalog checks.

```sh
propfirm check-update
propfirm prepare-update --version v0.2.0-beta.9
```

The first command reads releases and notes. The second clones the requested release into a separate directory under the private kit home, creates a virtual environment and runs the tests with isolated test state and no inherited API key. It never changes or restarts the running worker. A visitor normally uses this shared upstream; fork only when contributing a change.

Before applying an update, get the user's approval, review release notes and use a maintenance window. Request `propfirm stop`, keep the risk worker alive while it cancels entries, closes positions and reconciles, then verify `shutdown_complete` and the account itself. Stop the cloud supervisor only after confirmed flat. Back up the private kit home. Do not overwrite or publish its key, configuration, SQLite state, intent history, halt flags or reports.

Use the prepared checkout's virtual environment with the same persistent `PROPFIRM_HOME`. Run tests and verification. Review any documented migrations. This release's SQLite initialization preserves existing tables and intent IDs. Never delete state to fix an upgrade or rollback.

A kill/stop latch persists across versions. Reset only through `reset-halt --account-id ID --confirm-flat` after reviewing the reason. Approval is bound to configuration, account mode and executable version, so run the relevant trial/paid approval command again before switching the supervisor to the new executable. Verify status, reconciliation, stops and schedule after restart.

There is deliberately no unattended apply/update command. Preparing code is separate from applying it to a trading account. Rollback also needs a stopped, flat account and a compatible state schema; do not blindly restore old state after new orders.

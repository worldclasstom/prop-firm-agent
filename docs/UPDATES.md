# Versions and updates

Use a tagged release for a repeatable setup. Alpha releases are development snapshots; they are not verified trading releases. GitHub's release notes state what was tested and what remains unavailable. Subscribe to releases on the repository to hear about changes.

Each user has an independent account and private state. Sharing source does not give Prosperity Labs access to that account or create a centrally managed trading service.

## This alpha

No trading service is running, so testing another version means making a new checkout and following SETUP.md for that exact tag. Keep `~/.prosperity-agent/` outside both checkouts. Never copy API keys into a repository.

## Required before executable trading releases

The updater must report the installed and available versions and show release notes. Applying an update needs the user's approval. It must preserve configuration, account selection, order intent IDs, daily deduplication, halts and trading history.

Do not run `git pull` or install over a live worker. First block new entries. Reconcile orders, positions and protective stops. Use a verified maintenance procedure that keeps protection active; prefer an update window with no exposure. Back up private state, test migrations and prevent two versions from trading the same account at once. Verify reconciliation and worker health before re-enabling entries. A kill latch must survive an update or rollback.

Automatic live updates and a state-aware updater are not implemented in v0.1.0-alpha.1. They are acceptance criteria for the execution release, not current capabilities.

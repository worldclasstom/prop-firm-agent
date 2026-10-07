# Contributing

Start from STATUS.md and docs/SPECIFICATION.md. Discuss changes to the trading rules before implementing them. Keep core strategy functions shared by simulations and execution.

Run `python -m unittest discover -s tests -v` before a pull request. Add tests for changed behavior, especially ambiguous orders, partial fills, risk boundaries and recovery. Describe what was observed and what remains unverified.

Never include keys, account exports, trade reports or private runtime files in issues or patches. Use synthetic fixtures. Builder attribution is public and can be disabled.

A visitor normally installs a release of the shared repository. Fork when contributing code; do not instruct every visitor to create an unrelated copy that loses the update path.

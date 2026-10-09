# Trial order minimums without a support prerequisite

October 8, 2026 implementation revision, following the user's request to finish
setup without making a provider-support conversation a prerequisite. This
explicitly revises the beta.7 requirement to know every positive broker lower
bound before any trial order can be considered. It does not edit the archived
original strategy specification or change its risk/exposure ceilings.

## What is known and what is not

The [official API reference](https://github.com/XBorgLabs/propr-docs/blob/main/docs/api.md)
documents order submission, server validation errors, rejected order statuses,
reduce-only closing, and protective stops attached to a position. It lists seven
minimum quantities but no complete per-market quantity/notional limits response
in the inspected sections. There is no documented dry-run order endpoint in those
sections. No order is sent just to probe validation.

The following is our client policy, not a claim that Propr has no minimums or
guarantees execution. Known broker minimums remain local skip filters. Unpublished
minimums can stay explicitly unknown on a verified trial, leaving final order
acceptance to Propr when the strategy produces a legitimate signal.

## Configuration and execution

The agent selects `order_limits_policy: "broker_validation"` (the earlier name
`trial_broker_validation` means the same). From release 0.2.0b11 it applies to
paid accounts as well as the trial (operator decision, 2026-10-09): the
safeguards below are identical on both, and an order below a minimum nobody
published is rejected by the provider and reported, never guessed around.
Affected markets explicitly set unpublished lower bounds to JSON `null` and
include `limits_evidence` describing sources checked and unresolved fields.
Missing keys, zero, negative and nonfinite numbers are not valid substitutes.
The `verified` policy still requires positive known minima.

Contract multipliers, symbol mapping, size precision/step, sessions, account
availability and stop capability must still be verified. Runtime checks and
account risk checks are unchanged. Unknown order minimums are disclosed in the
daily report and research output, never filled with invented numbers.

Sizing still uses the original risk and exposure caps, rounded down to the
verified step. When minimum quantity is unknown, the smallest positive grid size
is the computational sizing floor; it is not recorded as a broker minimum. Known
quantity and notional minimums still skip undersized entries. The client never
raises a risk-sized order to meet a minimum and never weakens a stop.

An HTTP validation rejection latches an entry block and persists the rejected
intent; that entry is not resubmitted. A returned rejected order status also
blocks new entries. Timeouts retain the existing unknown-outcome reconciliation
path rather than being treated as rejection or absence. No blind retries or
automatic clearing of the block are allowed. A successful order says nothing
about the exact minimum for smaller quantities or later orders.

Every partial or full fill still needs a confirmed protective stop for its actual
quantity. An unconfirmed/rejected stop latches shutdown, attempts reduce-only
flattening, and keeps reconciliation active until flat is confirmed. A rejected
close cannot be reported as successful. As with the existing execution path,
an outage or rejection can delay protection/closing; this policy does not promise
that all qualifying orders will be accepted or that all positions can immediately
be closed.

## Evidence

Synthetic regression tests verify unchanged sizing when the known bounds would
not filter the order, strict paid/default-policy rejection, enforced known minima,
no forced probe without a signal, no retry/upsizing after rejection, partial-fill
protection, and shutdown after failed protection. Research discloses unknown
order eligibility. These tests do not establish live Propr acceptance. This path
still requires the user's authenticated trial run and cloud-runtime checks.

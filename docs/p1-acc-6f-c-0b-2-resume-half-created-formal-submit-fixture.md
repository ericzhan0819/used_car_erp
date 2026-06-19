# P1-ACC-6F-C-0B-2 Resume Half-Created Formal Submit Fixture

Last reviewed: 2026-06-19

Phase: `P1-ACC-6F-C-0B-2`

## Purpose

P1-ACC-6F-C-0B-2 resumes a half-created formal submit fixture.

It does not clean up the fixture. It continues from the existing `Used Car Vehicle` state through the existing formal services until a formal Draft Sales Invoice and submit gate snapshot exist.

## Boundaries

- Not a Sales Invoice submit.
- Does not create a second fixture.
- Does not delete or cancel fixture documents.
- Does not modify COA, Accounts, ERPNext core, submitted documents, GL Entry, or Stock Ledger Entry.
- Leaves a Draft Sales Invoice for the next P1-ACC-6F-C real submit test only when snapshot passes.

## Resume Modes

- `new_fixture`: no existing fixture was found; use normal fixture creation.
- `existing_draft`: existing Draft Sales Invoice was found; only run snapshot.
- `half_fixture_resume`: existing fixture vehicle was found without Draft Sales Invoice; continue safely from current state.

## Inspect

Read-only helper:

```text
used_car_erp.used_car_erp.services.formal_submitted_sales_invoice_test_fixture_setup_service.inspect_formal_submit_fixture_resume_state
```

It reports current fixture vehicle, stock, reservation, money flow, voucher draft, Journal Entry, Sales Invoice, submitted Sales Invoice count, and resume mode without writing data.

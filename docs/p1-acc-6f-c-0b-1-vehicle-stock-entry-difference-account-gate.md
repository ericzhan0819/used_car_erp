# P1-ACC-6F-C-0B-1 Vehicle Stock Entry Difference Account Gate

Last reviewed: 2026-06-19

Phase: `P1-ACC-6F-C-0B-1`

## Purpose

P1-ACC-6F-C-0B-1 fixes the Vehicle Stock Entry Difference Account gate encountered while creating the formal submitted Sales Invoice test fixture.

It targets the formal used car intake `Material Receipt` Stock Entry created by `VehicleStockService` / `VehicleIntakeService`.

This phase is not a Sales Invoice submit.

## Runtime Behavior

When ERPNext `Stock Entry Detail` has an `expense_account` field, `VehicleStockService` writes an explicit Difference Account on the Material Receipt item row.

Resolution order:

- Use `Company.stock_adjustment_account` when the field exists, has a value, and points to a valid ledger expense account for the same company.
- Otherwise use existing fallback `0100005-UC - 中古車銷貨成本 - O` when it is a valid ledger expense account for the same company.
- If neither account is usable, block with a clear setup error.

Validation requires the account to exist, belong to the same company, not be a group account, not be disabled, and have `root_type = Expense`.

## Boundaries

This phase does not:

```text
Submit Sales Invoice.
Create Payment Entry.
Create Delivery Note.
Create Purchase Invoice.
Modify Chart of Accounts.
Create Account.
Enable or disable Account.
Bypass ERPNext Stock Entry validation.
Use ignore_mandatory.
Use raw SQL.
Change Stock Entry submit into draft-only behavior.
```

If fixture setup later fails at another ERPNext master-data gate, that next blocking error belongs to a later phase.

## QA Coverage

Fake-frappe isolated tests cover:

- Company stock adjustment account selected when valid.
- Fallback expense account selected when company stock adjustment account is empty.
- Missing, group, disabled, wrong-company, and non-Expense difference account blocking.
- ERPNext versions where `Stock Entry Detail.expense_account` does not exist.
- No `ignore_mandatory` usage and no COA writes.
- Minimal accounting / stock setup QA reporting difference account readiness.

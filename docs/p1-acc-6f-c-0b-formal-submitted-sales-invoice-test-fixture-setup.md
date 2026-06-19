# P1-ACC-6F-C-0B Formal Submitted Sales Invoice Test Fixture Setup

Last reviewed: 2026-06-19

Phase: `P1-ACC-6F-C-0B`

## Purpose

P1-ACC-6F-C-0B creates one formal flow QA fixture for the next real submitted Sales Invoice test.

It runs the existing formal used car services through Draft Sales Invoice creation, then runs the submit gate snapshot.

This phase is not a Sales Invoice submit.

## Function

```text
used_car_erp.used_car_erp.services.formal_submitted_sales_invoice_test_fixture_setup_service.run_formal_submitted_sales_invoice_test_fixture_setup
```

The fixture marker is:

```text
P1-ACC-6F-C FORMAL SUBMIT FIXTURE
```

## Runtime Behavior

The setup uses existing services to create:

- Used Car Vehicle fixture.
- Submitted intake Stock Entry and linked Item / Serial No.
- Listed vehicle.
- Reservation, deposit money flow, and deposit voucher draft.
- Submitted deposit Journal Entry via voucher confirm.
- Final payment money flow and voucher draft.
- Submitted final payment Journal Entry via voucher confirm.
- Completed reservation and sold vehicle state through `VehicleReservationService`.
- Formal Draft Sales Invoice through guarded draft creation QA.
- Submit gate snapshot for the created Draft Sales Invoice.

If the snapshot passes, `ready_for_submit_test = true` and the next phase may run `P1-ACC-6F-C` real submit test.

P1-ACC-6F-C-0B-1 adds a prerequisite fix for the formal intake `Material Receipt` Stock Entry Difference Account gate. When `Company.stock_adjustment_account` is missing, Vehicle Stock runtime may use existing fallback expense account `0100005-UC - 中古車銷貨成本 - O` on `Stock Entry Detail.expense_account`; it does not modify COA.

## Safety Gates

- Runs only on `erpnext-coa.test`.
- Blocks if submitted Sales Invoice count is already greater than zero.
- Reuses an existing formal submit fixture Draft Sales Invoice if one is found.
- P1-ACC-6F-C-0B-2 resumes a half-created fixture by continuing through existing formal services from the current vehicle state.
- Does not delete, cancel, rebuild, or create a second fixture when a half-created fixture is found.
- Reports resume mode, resume stage, resume state, and existing fixture payload for debugging.
- Reports `stock_adjustment_account`, `stock_entry_difference_account`, original exception message, and already created documents when intake Stock Entry setup blocks.
- Leaves the Draft Sales Invoice and fixture documents in place for the next phase.

## Boundaries

This phase does not:

```text
Submit Sales Invoice.
Create Payment Entry.
Create Delivery Note.
Create Purchase Invoice.
Modify Chart of Accounts.
Modify ERPNext / Frappe core.
Patch old QA draft serial_no.
Write 15-1 deduction amounts into Sales Invoice taxes.
Delete fixture documents.
Cancel Stock Entry, Journal Entry, or Sales Invoice.
Clean up Used Car Vehicle, Reservation, Money Flow, or Voucher Draft.
Use raw SQL to repair data.
Bypass existing formal service business rules.
```

## Commands

Developer checks from the app directory:

```bash
cd /home/z/frappe/frappe-bench/apps/used_car_erp
python -m compileall used_car_erp/used_car_erp/services/formal_submitted_sales_invoice_test_fixture_setup_service.py
python -m compileall used_car_erp/used_car_erp/services/test_formal_submitted_sales_invoice_test_fixture_setup_service.py
python -m compileall used_car_erp/used_car_erp/services/submitted_sales_invoice_preflight_service.py
python -m compileall used_car_erp/used_car_erp/services/submitted_sales_invoice_submit_gate_snapshot_service.py
python -m compileall used_car_erp/used_car_erp/services/guarded_formal_sales_invoice_draft_creation_qa_service.py
```

Live fixture setup from the bench directory:

```bash
cd /home/z/frappe/frappe-bench
bench --site erpnext-coa.test execute used_car_erp.used_car_erp.services.formal_submitted_sales_invoice_test_fixture_setup_service.run_formal_submitted_sales_invoice_test_fixture_setup
```

Read-only resume state inspect:

```bash
cd /home/z/frappe/frappe-bench
bench --site erpnext-coa.test execute used_car_erp.used_car_erp.services.formal_submitted_sales_invoice_test_fixture_setup_service.inspect_formal_submit_fixture_resume_state
```

Read-only checks after setup:

```bash
cd /home/z/frappe/frappe-bench
bench --site erpnext-coa.test execute used_car_erp.used_car_erp.services.submitted_sales_invoice_preflight_service.run_latest_formal_vehicle_sales_invoice_preflight
bench --site erpnext-coa.test execute used_car_erp.used_car_erp.services.submitted_sales_invoice_submit_gate_snapshot_service.run_submitted_sales_invoice_submit_gate_snapshot
```

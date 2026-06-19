# P1-ACC-6F-C-0 Submitted Sales Invoice Submit Gate Snapshot

Last reviewed: 2026-06-19

Phase: `P1-ACC-6F-C-0`

## Purpose

P1-ACC-6F-C-0 is the final read-only gate snapshot before any real Sales Invoice submit test.

It answers only one question: whether the current formal Used Car Vehicle Draft Sales Invoice is safe to schedule for a future `P1-ACC-6F-C` real submit test.

## Function

```text
used_car_erp.used_car_erp.services.submitted_sales_invoice_submit_gate_snapshot_service.run_submitted_sales_invoice_submit_gate_snapshot
```

Arguments:

- `sales_invoice`: optional explicit Sales Invoice name.

If `sales_invoice` is not provided, the service uses the latest formal Draft Sales Invoice linked from `Used Car Vehicle.sales_invoice` and excludes P1-ACC-6E QA draft records.

## Read-only Checks

The snapshot reads:

- Baseline counts for Sales Invoice, submitted Sales Invoice, GL Entry, Stock Ledger Entry, Payment Entry, Journal Entry, Delivery Note, and Stock Entry.
- Sales Invoice submit gate fields such as company, customer, docstatus, update_stock, posting dates, item row, serial number, warehouse, accounts, tax template, and tax row.
- Linked Used Car Vehicle fields including status, formal delivery status, item, serial number, and completed reservation.
- `SubmittedSalesInvoicePreflightService().run(sales_invoice=target)` result.

## Pass / Warning / Fail

- `status = fail` when no formal Draft Sales Invoice is found, the target is not Draft, the linked vehicle is missing or not in the expected formal draft state, Sales Invoice payload is incomplete, tax row is wrong, or submitted preflight is not pass.
- `status = warning` when no blocking errors exist but clean-site assumptions are broken, such as submitted Sales Invoice count already being greater than zero.
- `status = pass` only when there are no blocking errors, no warnings, and submitted preflight reports ready.
- `ready_for_submit_test = True` only when `status = pass` and submitted preflight is ready.

## Commands

Developer checks from the app directory:

```bash
cd /home/z/frappe/frappe-bench/apps/used_car_erp
python -m compileall used_car_erp/used_car_erp/services/submitted_sales_invoice_submit_gate_snapshot_service.py
python -m compileall used_car_erp/used_car_erp/services/test_submitted_sales_invoice_submit_gate_snapshot_service.py
python -m compileall used_car_erp/used_car_erp/services/submitted_sales_invoice_preflight_service.py
python -m compileall used_car_erp/used_car_erp/services/guarded_formal_sales_invoice_draft_creation_qa_service.py
```

Live read-only check from the bench directory:

```bash
cd /home/z/frappe/frappe-bench
bench --site erpnext-coa.test execute used_car_erp.used_car_erp.services.submitted_sales_invoice_submit_gate_snapshot_service.run_submitted_sales_invoice_submit_gate_snapshot
```

To inspect a known Draft Sales Invoice:

```bash
cd /home/z/frappe/frappe-bench
bench --site erpnext-coa.test execute used_car_erp.used_car_erp.services.submitted_sales_invoice_submit_gate_snapshot_service.run_submitted_sales_invoice_submit_gate_snapshot --kwargs "{'sales_invoice': '<SALES_INVOICE_NAME>'}"
```

## Boundaries

This phase does not:

```text
Submit Sales Invoice.
Create Draft Sales Invoice.
Create GL Entry.
Create Stock Ledger Entry.
Create Payment Entry.
Create Journal Entry.
Create Delivery Note.
Create Stock Entry.
Save, insert, db_set, commit, or rollback.
Repair data.
Modify ERPNext / Frappe core.
Modify Chart of Accounts.
Patch ACC-SINV-2026-00002 serial_no.
Create QA Serial No.
Auto-create Used Car Vehicle, Reservation, Money Flow, or Voucher Draft.
Call create_sales_invoice_draft_for_vehicle().
Call run_guarded_formal_sales_invoice_draft_creation_qa().
Write 15-1 deduction amounts into Sales Invoice taxes.
Delete, cancel, or repair any Sales Invoice.
```

True Sales Invoice submit must be implemented in a later phase and is allowed only after this snapshot returns `status = pass` and `ready_for_submit_test = true`.

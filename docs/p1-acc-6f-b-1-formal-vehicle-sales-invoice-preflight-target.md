# P1-ACC-6F-B-1 Formal Vehicle Sales Invoice Preflight Target

Last reviewed: 2026-06-19

Phase: `P1-ACC-6F-B-1`

## 1. Purpose

P1-ACC-6F-B-1 adds read-only targeting for Draft Sales Invoice records created by the formal Used Car Vehicle flow.

This phase only chooses the correct draft and runs the existing submitted Sales Invoice preflight. It does not submit, save, insert, delete, commit, rollback, repair, or create any document.

## 2. Formal Draft Targeting

The formal runner looks for the latest Draft Sales Invoice that can be traced from `Used Car Vehicle.sales_invoice`.

Candidate requirements:

- `Sales Invoice.company = OO`
- `Sales Invoice.docstatus = 0`
- Sales Invoice remarks must not contain the P1-ACC-6E QA marker
- A `Used Car Vehicle` must link back through `sales_invoice`

When a candidate is found, the runner calls the existing `SubmittedSalesInvoicePreflightService().run(sales_invoice=...)` path so item, serial number, warehouse, tax row, account, and baseline checks stay unchanged.

## 3. QA Draft Versus Formal Draft

The P1-ACC-6E QA draft exists only to prove minimal accounting and stock master data can create a Draft Sales Invoice without GL Entry or Stock Ledger Entry.

The formal Used Car Vehicle draft is created by `create_sales_invoice_draft_for_vehicle()` and is linked from `Used Car Vehicle.sales_invoice`. It should carry the real vehicle item, serial number, warehouse, customer, and tax template payload prepared by the formal flow.

P1-ACC-6F-B-1 keeps `run_submitted_sales_invoice_preflight()` unchanged, so its default target remains the latest P1-ACC-6E QA draft. The new formal runner is separate.

## 4. Not Found Is Expected When No Formal Draft Exists

If no formal vehicle draft exists, `run_latest_formal_vehicle_sales_invoice_preflight()` returns a schema-compatible fail report with:

- `status = fail`
- `ready_to_submit = False`
- `blocking_errors` containing `找不到正式車輛流程 Draft Sales Invoice。`

This is a safe blocked state. The runner must not create vehicles, reservations, money flows, voucher drafts, Sales Invoices, serial numbers, or master data.

## 5. Read-only Candidate List

`find_formal_vehicle_sales_invoice_preflight_candidates(limit=10)` returns matching candidate details for inspection only. It does not call preflight and does not write data.

Returned fields include vehicle, Sales Invoice, vehicle status, formal delivery status, customer, docstatus, item code, serial number, warehouse, tax template, and modified time.

## 6. Run Commands

Run from the bench directory:

```bash
cd /home/z/frappe/frappe-bench
bench --site erpnext-coa.test execute used_car_erp.used_car_erp.services.submitted_sales_invoice_preflight_service.run_latest_formal_vehicle_sales_invoice_preflight
bench --site erpnext-coa.test execute used_car_erp.used_car_erp.services.submitted_sales_invoice_preflight_service.find_formal_vehicle_sales_invoice_preflight_candidates
```

Developer checks from the app directory:

```bash
cd /home/z/frappe/frappe-bench/apps/used_car_erp
python -m compileall used_car_erp/used_car_erp/services/submitted_sales_invoice_preflight_service.py
python -m compileall used_car_erp/used_car_erp/services/test_submitted_sales_invoice_preflight_service.py
```

## 7. Boundaries

This phase does not:

```text
Submit Sales Invoice.
Create GL Entry.
Create Stock Ledger Entry.
Create Payment Entry.
Create Journal Entry.
Create Delivery Note.
Create Stock Entry.
Modify Chart of Accounts.
Patch ACC-SINV-2026-00002 serial_no.
Create QA Serial No.
Create formal vehicle transaction data.
Call create_sales_invoice_draft_for_vehicle automatically.
Write 15-1 deduction amounts into Sales Invoice taxes.
```

## 8. Next Phase

P1-ACC-6F-B-1 is a safety preparation step before P1-ACC-6F-C. The real submit remains reserved for P1-ACC-6F-C.

# P1-ACC-6F-B-3 Guarded Formal Sales Invoice Draft Creation QA

Last reviewed: 2026-06-19

Phase: `P1-ACC-6F-B-3`

## Purpose

P1-ACC-6F-B-3 adds a guarded live QA runner for formal Draft Sales Invoice creation.

It only calls `VehicleReservationService.create_sales_invoice_draft_for_vehicle()` after `FormalSalesInvoiceDraftReadinessService` returns `status = pass` and `ready_to_create_sales_invoice_draft = True`.

## Runtime Boundary

This phase creates a Draft Sales Invoice only. It does not submit Sales Invoice and does not create formal GL Entry or Stock Ledger Entry.

If readiness is not pass, the runner returns `status = blocked`, does not call draft creation, and does not modify data.

If a Draft Sales Invoice is created but postcheck or submitted preflight fails, the runner reports `created = True` and returns the blocking errors. It does not delete, cancel, repair, or submit the draft.

## Function

```text
used_car_erp.used_car_erp.services.guarded_formal_sales_invoice_draft_creation_qa_service.run_guarded_formal_sales_invoice_draft_creation_qa
```

Arguments:

- `vehicle_name`: optional explicit Used Car Vehicle.
- `posting_date`: optional Sales Invoice posting date.
- `note`: optional note passed to the formal draft creation runtime.

## Checks

The guarded runner verifies:

- Readiness pass before creation.
- Sales Invoice exists after creation.
- Sales Invoice remains Draft with `docstatus = 0`.
- `update_stock = 1`.
- `taxes_and_charges = 台灣營業稅 5%（含稅） - O`.
- Exactly one item row exists.
- Item row has `serial_no`, `warehouse`, and `income_account`.
- Exactly one tax row exists.
- Tax row uses `On Net Total`, `0202134 - 銷項稅額 - O`, rate `5`, and `included_in_print_rate = 1`.
- Sales Invoice count increases by 1.
- GL Entry, Stock Ledger Entry, Payment Entry, Journal Entry, Delivery Note, and Stock Entry counts remain unchanged.
- `SubmittedSalesInvoicePreflightService().run(sales_invoice=created_sales_invoice)` runs after creation.
- Latest formal vehicle Sales Invoice preflight can find the created draft.

## Commands

Developer checks from the app directory:

```bash
cd /home/z/frappe/frappe-bench/apps/used_car_erp
python -m compileall used_car_erp/used_car_erp/services/guarded_formal_sales_invoice_draft_creation_qa_service.py
python -m compileall used_car_erp/used_car_erp/services/test_guarded_formal_sales_invoice_draft_creation_qa_service.py
python -m compileall used_car_erp/used_car_erp/services/formal_sales_invoice_draft_readiness_service.py
python -m compileall used_car_erp/used_car_erp/services/submitted_sales_invoice_preflight_service.py
```

Live guarded checks from the bench directory:

```bash
cd /home/z/frappe/frappe-bench
bench --site erpnext-coa.test execute used_car_erp.used_car_erp.services.formal_sales_invoice_draft_readiness_service.find_formal_sales_invoice_draft_readiness_candidates
bench --site erpnext-coa.test execute used_car_erp.used_car_erp.services.formal_sales_invoice_draft_readiness_service.run_formal_sales_invoice_draft_readiness
bench --site erpnext-coa.test execute used_car_erp.used_car_erp.services.guarded_formal_sales_invoice_draft_creation_qa_service.run_guarded_formal_sales_invoice_draft_creation_qa
```

If there is no readiness-pass vehicle on the live site, `blocked` is the correct result and no document should be created.

## Boundaries

This phase does not:

```text
Submit Sales Invoice.
Create GL Entry.
Create Stock Ledger Entry.
Create Payment Entry.
Create Journal Entry.
Create Delivery Note.
Create Stock Entry.
Modify ERPNext / Frappe core.
Modify Chart of Accounts.
Patch ACC-SINV-2026-00002 serial_no.
Create QA Serial No.
Create formal transaction data when readiness is not pass.
Auto-create Used Car Vehicle / Reservation / Money Flow / Voucher Draft.
Write 15-1 deduction amounts into Sales Invoice taxes.
Delete, cancel, or repair a draft after creation.
```

True Sales Invoice submit remains reserved for `P1-ACC-6F-C`.

# P1-ACC-6F-B-2 Formal Sales Invoice Draft Readiness Inspector

Last reviewed: 2026-06-19

Phase: `P1-ACC-6F-B-2`

## Purpose

P1-ACC-6F-B-2 adds a read-only readiness inspector before formal Used Car Vehicle Sales Invoice draft creation.

It checks whether an existing sold vehicle has the data needed for `create_sales_invoice_draft_for_vehicle()` without calling that runtime path.

## Runtime Boundary

This inspector is not Sales Invoice draft creation. It is not submit. It does not replace `create_sales_invoice_draft_for_vehicle()`.

The service intentionally does not call `VehicleReservationService.preflight_formal_delivery_for_vehicle()` because that method can backfill vehicle completion summary links and commit changes.

This phase only identifies data gaps before P1-ACC-6F-C. The real formal draft creation must happen in a later phase, and the real submit remains reserved for P1-ACC-6F-C or later.

## Functions

```text
used_car_erp.used_car_erp.services.formal_sales_invoice_draft_readiness_service.run_formal_sales_invoice_draft_readiness
used_car_erp.used_car_erp.services.formal_sales_invoice_draft_readiness_service.find_formal_sales_invoice_draft_readiness_candidates
```

`run_formal_sales_invoice_draft_readiness(vehicle_name=None)` checks a specified Used Car Vehicle, or the latest read-only candidate when no vehicle is passed.

`find_formal_sales_invoice_draft_readiness_candidates(limit=10)` lists sold vehicles with no linked Sales Invoice and unfinished formal delivery status.

## Report

The report is schema-stable and returns `status`, `ready_to_create_sales_invoice_draft`, resolved company, vehicle, reservation, customer, item, serial number, warehouse, income account, sales amount, tax fields, deposit and final payment accounting links, validations, warnings, and blocking errors.

Status rules:

- Blocking errors: `status = fail`, `ready_to_create_sales_invoice_draft = False`
- Warnings only: `status = warning`, `ready_to_create_sales_invoice_draft = False`
- No blocking errors and no warnings: `status = pass`, `ready_to_create_sales_invoice_draft = True`

## Read-only Checks

The inspector checks:

- `Used Car Vehicle.status = 已售出`
- No existing `sales_invoice`
- `formal_delivery_status` is not `已完成`
- Item, serial number, company, and warehouse are resolvable
- Completed reservation exists and has a valid ERPNext Customer
- Vehicle completion summary links exist for deposit and final money flow, voucher draft, and Journal Entry
- Money flow and voucher draft statuses are `已入帳`
- Voucher draft Journal Entry matches the vehicle completion summary Journal Entry
- Sales amount is deposit plus final payment amount, falling back to final money flow amount when needed
- Purchase document type can derive a non-`待確認` tax mode
- Tax template is `台灣營業稅 5%（含稅） - O`
- Tax account is `0202134 - 銷項稅額 - O`
- Income account resolves using the same order as draft creation: Item Default, Item Group Default, Company default, fallback Income ledger account

If reservation links exist but vehicle completion summary fields are missing, the inspector reports this without backfilling.

## Commands

Developer checks from the app directory:

```bash
cd /home/z/frappe/frappe-bench/apps/used_car_erp
python -m compileall used_car_erp/used_car_erp/services/formal_sales_invoice_draft_readiness_service.py
python -m compileall used_car_erp/used_car_erp/services/test_formal_sales_invoice_draft_readiness_service.py
python -m compileall used_car_erp/used_car_erp/services/submitted_sales_invoice_preflight_service.py
```

Live read-only checks from the bench directory:

```bash
cd /home/z/frappe/frappe-bench
bench --site erpnext-coa.test execute used_car_erp.used_car_erp.services.formal_sales_invoice_draft_readiness_service.find_formal_sales_invoice_draft_readiness_candidates
bench --site erpnext-coa.test execute used_car_erp.used_car_erp.services.formal_sales_invoice_draft_readiness_service.run_formal_sales_invoice_draft_readiness
```

## Boundaries

This phase does not:

```text
Submit Sales Invoice.
Create Sales Invoice draft.
Create GL Entry.
Create Stock Ledger Entry.
Create Payment Entry.
Create Journal Entry.
Create Delivery Note.
Create Stock Entry.
Modify ERPNext / Frappe core.
Modify Chart of Accounts.
Backfill vehicle completion summary.
Patch ACC-SINV-2026-00002 serial_no.
Create QA Serial No.
Create formal vehicle transaction data.
Call create_sales_invoice_draft_for_vehicle().
Call runtime preflight that can backfill or commit.
Write 15-1 deduction amounts into Sales Invoice taxes.
```

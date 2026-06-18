# P1-ACC-6F-A Submitted Sales Invoice Preflight Only

Last reviewed: 2026-06-19

Phase: `P1-ACC-6F-A`

## 1. Purpose

P1-ACC-6F-A adds a read-only preflight for a Draft Sales Invoice before any future submitted Sales Invoice test. It checks whether a draft is ready for ERPNext submit behavior that will create GL Entry and Stock Ledger Entry through native `update_stock`.

This phase only reports readiness. It does not submit, save, insert, delete, commit, rollback, or repair any document.

## 2. Why Preflight First

P1-ACC-6E proved that the site can create a Draft Sales Invoice from the minimal accounting and stock setup. Draft creation is not enough evidence for submit safety because ERPNext submit validates stock availability, serial number assignment, warehouse linkage, tax rows, and ledger accounts more strictly.

The preflight makes those assumptions explicit before P1-ACC-6F is allowed to run a real submit.

## 3. Difference Between P1-ACC-6E Draft And P1-ACC-6F Submit

P1-ACC-6E creates a draft and verifies that no GL Entry or Stock Ledger Entry is created.

P1-ACC-6F will be the first phase allowed to submit a Sales Invoice and observe ERPNext's accounting and stock ledger effects. Between those phases, the draft must be checked for `update_stock`, serial number readiness, warehouse account setup, tax account setup, and required ledger accounts.

## 4. Submit Preflight Checklist

The preflight checks:

- Sales Invoice exists, belongs to company `OO`, is Draft, has `update_stock = 1`, has a customer, and uses `台灣營業稅 5%（含稅） - O`.
- Sales Invoice is either a P1-ACC-6E QA draft by remarks marker or can be traced from `Used Car Vehicle.sales_invoice`.
- The item table has exactly one row, qty is 1, rate is greater than 0, warehouse is `中古車庫存倉 - O`, and income account is `0100001-UC - 中古車銷售收入 - O`.
- Serial item rows must have `serial_no`. If serial status or warehouse cannot be read reliably, the preflight returns a warning instead of guessing.
- Warehouse `中古車庫存倉 - O` exists, belongs to `OO`, is not a group, is not disabled, and is linked to `0201131 - 商品 - O`.
- Required accounts exist, belong to `OO`, are non-group ledger accounts, and are not disabled.
- The tax table has exactly one row using `On Net Total`, `0202134 - 銷項稅額 - O`, rate `5`, and `included_in_print_rate = 1`.
- Baseline counts for GL Entry, Stock Ledger Entry, and submitted Sales Invoice are recorded.

## 5. Expected Current Result

The latest P1-ACC-6E QA draft may be not ready because it can lack `serial_no` on the item row. That is an expected fail result for this phase. The preflight must report the issue and must not patch or assign a serial number.

## 6. Run Command

Run from the bench directory:

```bash
cd /home/z/frappe/frappe-bench
bench --site erpnext-coa.test execute used_car_erp.used_car_erp.services.submitted_sales_invoice_preflight_service.run_submitted_sales_invoice_preflight
```

To check a specific draft:

```bash
cd /home/z/frappe/frappe-bench
bench --site erpnext-coa.test execute used_car_erp.used_car_erp.services.submitted_sales_invoice_preflight_service.run_submitted_sales_invoice_preflight --kwargs "{'sales_invoice': 'ACC-SINV-2026-00002'}"
```

Developer checks from the app directory:

```bash
cd /home/z/frappe/frappe-bench/apps/used_car_erp
python -m compileall used_car_erp/used_car_erp/services/submitted_sales_invoice_preflight_service.py
python -m compileall used_car_erp/used_car_erp/services/test_submitted_sales_invoice_preflight_service.py
python -m pytest used_car_erp/used_car_erp/services/test_submitted_sales_invoice_preflight_service.py
```

## 7. Pass / Warning / Fail Conditions

`status = fail` when any blocking error exists. `ready_to_submit` must be false.

`status = warning` when there are no blocking errors but warnings exist, such as baseline counts on `erpnext-coa.test` not matching the clean-site expectation or Serial No stock fields being unavailable. `ready_to_submit` must be false.

`status = pass` when there are no blocking errors and no warnings. Only this status may return `ready_to_submit = true`.

## 8. Non-goals

This phase does not:

```text
Submit Sales Invoice.
Create GL Entry.
Create Stock Ledger Entry.
Create Stock Entry.
Create Payment Entry.
Create Journal Entry.
Create Delivery Note.
Create a new Sales Invoice.
Delete P1-ACC-6E draft Sales Invoice.
Assign or create Serial No.
Create QA Serial No.
Create formal vehicle sales data.
Modify create_sales_invoice_draft_for_vehicle.
Modify Chart of Accounts.
Modify ERPNext / Frappe core.
Write 15-1 deduction amounts into Sales Invoice taxes.
```

## 9. Next Phase

Only P1-ACC-6F may perform the real submitted Sales Invoice runtime. P1-ACC-6F-A is the read-only gate before that step.

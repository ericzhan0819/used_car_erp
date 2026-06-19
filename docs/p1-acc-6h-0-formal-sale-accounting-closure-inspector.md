# P1-ACC-6H-0 Formal Sale Accounting Closure Inspector

Last reviewed: 2026-06-19

Phase: `P1-ACC-6H-0`

## Purpose

P1-ACC-6H-0 是 formal sale accounting closure inspector。

它只讀取並判斷整台車正式售車會計閉環是否完成。

## Functions

```text
used_car_erp.used_car_erp.services.formal_sale_accounting_closure_inspector_service.run_formal_sale_accounting_closure_inspector
used_car_erp.used_car_erp.services.formal_sale_accounting_closure_inspector_service.find_formal_sale_accounting_closure_candidates
```

Arguments:

- `sales_invoice`: optional explicit submitted Sales Invoice target.
- `vehicle_name`: optional explicit Used Car Vehicle target.
- `limit`: optional candidate finder limit.

## Read-only Behavior

The inspector checks:

- Vehicle is `已售出`, `formal_delivery_status = 已完成`, and links Sales Invoice, completed reservation, deposit / final money flow, voucher drafts, receipt Journal Entries, and advance settlement Journal Entry.
- Sales Invoice is submitted, company `OO`, `update_stock = 1`, `outstanding_amount = 0`, has one item row, serial, warehouse, income account, expense account, and the expected 5% included tax template.
- Sales Invoice GL Entry exists, includes receivable, income, tax, inventory, and COGS accounts, and debit / credit balances.
- Sales Invoice Stock Ledger Entry exists and records outbound stock quantity.
- Deposit and final money flows, voucher drafts, and receipt Journal Entries are posted and linked to the same vehicle, reservation, and customer.
- Advance settlement Journal Entry is submitted, has GL Entry, balances, debits advance liability, credits receivable, and equals Sales Invoice grand total plus deposit + final amount.
- Payment Entry, Delivery Note, Purchase Invoice, unexpected Journal Entry, and unexpected Stock Entry linked to the target Sales Invoice are absent.

## Boundaries

This phase does not:

```text
Create documents.
Submit, cancel, amend, or delete documents.
Modify Sales Invoice, Used Car Vehicle, Reservation, Money Flow, Voucher Draft, Journal Entry, GL Entry, or Stock Ledger Entry.
Create Payment Entry, Delivery Note, Purchase Invoice, Stock Entry, Account, or COA changes.
Use raw SQL.
Use ignore_mandatory.
Handle UI.
Handle 15-1 tax formula.
Use preparation, repair, detailing, auction, agency, or other cost data in closure amount.
```

`purchase_price` is reported only as background observation. It does not participate in advance settlement closure amount checks.

## Pass Meaning

If the inspector returns `status = pass`, then:

- `closed = true`.
- `ready_for_ui_review = true`.
- The current formal sale accounting runtime can stop here.
- Next phases can move to Used Car Vehicle simplified UX, 15-1 tax boundary specification, and accounting workspace / dashboard cleanup.

## Commands

Developer checks from the app directory:

```bash
cd /home/z/frappe/frappe-bench/apps/used_car_erp
python -m compileall used_car_erp/used_car_erp/services/formal_sale_accounting_closure_inspector_service.py
python -m compileall used_car_erp/used_car_erp/services/test_formal_sale_accounting_closure_inspector_service.py
python -m compileall used_car_erp/used_car_erp/services/guarded_advance_settlement_journal_qa_service.py
python -m compileall used_car_erp/used_car_erp/services/advance_settlement_readiness_service.py
python -m compileall used_car_erp/used_car_erp/services/formal_delivery_status_sync_service.py
python -m compileall used_car_erp/used_car_erp/services/guarded_formal_sales_invoice_submit_qa_service.py
```

Live read-only checks from the bench directory:

```bash
cd /home/z/frappe/frappe-bench
bench --site erpnext-coa.test execute used_car_erp.used_car_erp.services.formal_sale_accounting_closure_inspector_service.find_formal_sale_accounting_closure_candidates
bench --site erpnext-coa.test execute used_car_erp.used_car_erp.services.formal_sale_accounting_closure_inspector_service.run_formal_sale_accounting_closure_inspector --kwargs "{'sales_invoice': 'ACC-SINV-2026-00004'}"
```

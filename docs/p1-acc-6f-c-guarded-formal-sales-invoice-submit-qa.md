# P1-ACC-6F-C Guarded Formal Sales Invoice Submit QA

Last reviewed: 2026-06-19

Phase: `P1-ACC-6F-C`

## Purpose

P1-ACC-6F-C is the first real submit QA for one formal fixture Sales Invoice.

It only allows submitting a single formal fixture Draft Sales Invoice that passes the submit gate snapshot and requires an explicit confirmation token.

## Function

```text
used_car_erp.used_car_erp.services.guarded_formal_sales_invoice_submit_qa_service.run_guarded_formal_sales_invoice_submit_qa
```

Arguments:

- `sales_invoice`: optional explicit Sales Invoice name.
- `confirmation_token`: must be `P1-ACC-6F-C-SUBMIT`.

If `sales_invoice` is not provided, the service uses the same latest formal Draft Sales Invoice target logic as the submit gate snapshot.

## Guards

- Runs only on `erpnext-coa.test`.
- Requires confirmation token `P1-ACC-6F-C-SUBMIT`.
- Requires target Sales Invoice to exist and be Draft.
- Requires linked `Used Car Vehicle.sales_invoice = target`.
- Requires linked vehicle `status = 已售出` and `formal_delivery_status = 銷售發票草稿`.
- Blocks if submitted Sales Invoice count is already greater than zero, except for observing the same already submitted formal fixture on rerun.
- Runs `SubmittedSalesInvoiceSubmitGateSnapshotService().run(sales_invoice=target)` and requires `status = pass` plus `ready_for_submit_test = true`.

## Runtime Behavior

The only intentional write is:

```python
frappe.get_doc("Sales Invoice", target).submit()
```

The service commits after successful submit, then observes Sales Invoice, vehicle, GL Entry, Stock Ledger Entry, Serial No state, and document counts.

Submitting the Sales Invoice uses ERPNext native behavior and should create GL Entry and Stock Ledger Entry for the Sales Invoice voucher.

## Boundaries

This phase does not:

```text
Create Payment Entry.
Create Delivery Note.
Create Purchase Invoice.
Create Journal Entry.
Create Stock Entry.
Create a new Sales Invoice.
Submit Payment Entry, Journal Entry, Delivery Note, or Stock Entry.
Cancel or delete Sales Invoice.
Cancel or delete fixture documents.
Modify Chart of Accounts.
Modify ERPNext / Frappe core.
Use raw SQL.
Use ignore_mandatory.
Write 15-1 deduction amounts into Sales Invoice taxes.
Create advance_settlement_journal_entry.
Write formal_delivery_status = 已完成.
```

Formal delivery status sync and advance settlement belong to the next phase.

## Expected Observation

- First run submits `ACC-SINV-2026-00004`.
- Submitted Sales Invoice count increases from 0 to 1.
- Sales Invoice docstatus becomes 1.
- Target voucher has GL Entry for receivable, sales income, sales tax, inventory, and COGS accounts.
- Target voucher has Stock Ledger Entry.
- Payment Entry, Delivery Note, Journal Entry, and Stock Entry counts do not change.
- Linked Used Car Vehicle remains `已售出`.
- If `formal_delivery_status` remains `銷售發票草稿`, the service reports a warning and does not repair it.
- Second run observes `already_submitted` and does not submit again.

## Commands

Developer checks from the app directory:

```bash
cd /home/z/frappe/frappe-bench/apps/used_car_erp
python -m compileall used_car_erp/used_car_erp/services/guarded_formal_sales_invoice_submit_qa_service.py
python -m compileall used_car_erp/used_car_erp/services/test_guarded_formal_sales_invoice_submit_qa_service.py
```

Submit gate snapshot from the bench directory:

```bash
cd /home/z/frappe/frappe-bench
bench --site erpnext-coa.test execute used_car_erp.used_car_erp.services.submitted_sales_invoice_submit_gate_snapshot_service.run_submitted_sales_invoice_submit_gate_snapshot --kwargs "{'sales_invoice': 'ACC-SINV-2026-00004'}"
```

Real submit QA from the bench directory:

```bash
cd /home/z/frappe/frappe-bench
bench --site erpnext-coa.test execute used_car_erp.used_car_erp.services.guarded_formal_sales_invoice_submit_qa_service.run_guarded_formal_sales_invoice_submit_qa --kwargs "{'sales_invoice': 'ACC-SINV-2026-00004', 'confirmation_token': 'P1-ACC-6F-C-SUBMIT'}"
```

Post-submit observation uses the same command and should return `already_submitted`.

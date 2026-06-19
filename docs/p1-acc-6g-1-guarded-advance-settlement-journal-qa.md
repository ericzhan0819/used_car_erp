# P1-ACC-6G-1 Guarded Advance Settlement Journal Entry QA

Last reviewed: 2026-06-19

Phase: `P1-ACC-6G-1`

## Purpose

P1-ACC-6G-1 是 guarded advance settlement Journal Entry QA。

它根據 P1-ACC-6G-0 readiness preview，建立並提交一張沖轉 Journal Entry，將已入帳訂金 / 尾款的預收或暫收負債轉沖 submitted Sales Invoice 的應收帳款。

分錄方向：

```text
Dr 預收 / 暫收 / liability account(s)
Cr 應收帳款 receivable account
```

## Function

```text
used_car_erp.used_car_erp.services.guarded_advance_settlement_journal_qa_service.run_guarded_advance_settlement_journal_qa
```

Arguments:

- `sales_invoice`: explicit submitted Sales Invoice target.
- `vehicle_name`: optional Used Car Vehicle target.
- `confirmation_token`: must be `P1-ACC-6G-1-SETTLE`.

## Guard Rails

- Write mode only runs on `erpnext-coa.test`.
- Confirmation token is mandatory.
- P1-ACC-6G-0 readiness must return `status = pass`, `ready_to_create_advance_settlement = True`, and non-empty `settlement_preview`.
- Target vehicle must have no existing `advance_settlement_journal_entry`, except rerun with a submitted linked Journal Entry returns `already_settled`.
- Target vehicle must point to the same Sales Invoice and have `formal_delivery_status = 已完成`.
- Target Sales Invoice must be submitted and company `OO`.
- Journal Entry debit and credit totals must balance before insert.

## Boundaries

This phase does:

```text
Create one Journal Entry.
Submit that Journal Entry.
Write Used Car Vehicle.advance_settlement_journal_entry through controlled write only.
Observe GL Entry and Sales Invoice outstanding_amount after submit.
```

This phase does not:

```text
Create Payment Entry.
Create Delivery Note.
Create Purchase Invoice.
Create Sales Invoice.
Modify Sales Invoice.
Cancel or amend Sales Invoice.
Modify Money Flow.
Modify Voucher Draft.
Modify Reservation.
Modify GL Entry.
Modify Stock Ledger Entry.
Modify Chart of Accounts.
Create or enable Account.
Use raw SQL.
Use ignore_mandatory.
Use 15-1 tax estimates.
Use preparation, repair, detailing, auction, agency, or other cost data.
```

## Rerun Behavior

If the linked `Used Car Vehicle.advance_settlement_journal_entry` already exists and the Journal Entry is submitted, the service returns `already_settled` and does not create another Journal Entry.

## Commands

Developer checks from the app directory:

```bash
cd /home/z/frappe/frappe-bench/apps/used_car_erp
python -m compileall used_car_erp/used_car_erp/services/guarded_advance_settlement_journal_qa_service.py
python -m compileall used_car_erp/used_car_erp/services/test_guarded_advance_settlement_journal_qa_service.py
python -m compileall used_car_erp/used_car_erp/services/advance_settlement_readiness_service.py
python -m compileall used_car_erp/used_car_erp/services/formal_delivery_status_sync_service.py
python -m compileall used_car_erp/used_car_erp/services/guarded_formal_sales_invoice_submit_qa_service.py
```

Live guarded settlement from the bench directory:

```bash
cd /home/z/frappe/frappe-bench
bench --site erpnext-coa.test execute used_car_erp.used_car_erp.services.advance_settlement_readiness_service.run_advance_settlement_readiness --kwargs "{'sales_invoice': 'ACC-SINV-2026-00004'}"
bench --site erpnext-coa.test execute used_car_erp.used_car_erp.services.guarded_advance_settlement_journal_qa_service.run_guarded_advance_settlement_journal_qa --kwargs "{'sales_invoice': 'ACC-SINV-2026-00004', 'confirmation_token': 'P1-ACC-6G-1-SETTLE'}"
```

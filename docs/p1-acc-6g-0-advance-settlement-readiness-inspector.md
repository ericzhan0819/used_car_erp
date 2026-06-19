# P1-ACC-6G-0 Advance Settlement Readiness Inspector

Last reviewed: 2026-06-19

Phase: `P1-ACC-6G-0`

## Purpose

P1-ACC-6G-0 是預收款沖轉 readiness inspector。

它不是沖轉 Journal Entry creation。

它只根據已入帳訂金 / 尾款與 submitted Sales Invoice，檢查是否可進入下一階段 guarded advance settlement Journal Entry creation。

## Functions

```text
used_car_erp.used_car_erp.services.advance_settlement_readiness_service.run_advance_settlement_readiness
used_car_erp.used_car_erp.services.advance_settlement_readiness_service.find_advance_settlement_readiness_candidates
```

Arguments:

- `sales_invoice`: optional explicit submitted Sales Invoice target.
- `vehicle_name`: optional explicit Used Car Vehicle target.
- `limit`: optional candidate finder limit.

## Read-only Behavior

The inspector checks:

- Linked `Used Car Vehicle` exists, is `已售出`, `formal_delivery_status = 已完成`, and has no `advance_settlement_journal_entry`.
- `Sales Invoice` exists, is submitted, belongs to company `OO`, has customer, readable totals, receivable account, and native GL Entry.
- Completed reservation exists.
- Deposit and final `Used Car Money Flow` are `已入帳`, match reservation / vehicle / customer, and have linked Journal Entry.
- Deposit and final `Used Car Voucher Draft` are `已入帳`, match money flow, have lines, and have linked Journal Entry.
- Deposit and final Journal Entry are submitted, balanced, company `OO`, and expose cash / bank debit account plus advance liability credit account.
- `advance_total = deposit_amount + final_amount` equals Sales Invoice `grand_total` within rounding tolerance.

## Preview

The report includes a proposed settlement journal preview only as data:

```text
debit: advance liability account(s)
credit: receivable account
amount: advance_total
reference: Sales Invoice / vehicle / reservation
```

If deposit and final use the same advance liability account, the preview merges the debit line. If they use different accounts, the preview returns separate debit lines.

## Boundaries

This phase does not:

```text
Create Journal Entry.
Submit Journal Entry.
Create Payment Entry.
Modify Sales Invoice.
Modify Used Car Vehicle.
Modify Reservation.
Modify Money Flow.
Modify Voucher Draft.
Modify GL Entry.
Modify Stock Ledger Entry.
Write advance_settlement_journal_entry.
Modify formal_delivery_status.
Modify Chart of Accounts.
Use raw SQL.
Use ignore_mandatory.
Use 15-1 tax estimates in settlement amount.
Use preparation, repair, detailing, auction, agency, or other cost data as settlement basis.
```

## Commands

Developer checks from the app directory:

```bash
cd /home/z/frappe/frappe-bench/apps/used_car_erp
python -m compileall used_car_erp/used_car_erp/services/advance_settlement_readiness_service.py
python -m compileall used_car_erp/used_car_erp/services/test_advance_settlement_readiness_service.py
python -m compileall used_car_erp/used_car_erp/services/formal_delivery_status_sync_service.py
python -m compileall used_car_erp/used_car_erp/services/guarded_formal_sales_invoice_submit_qa_service.py
```

Live read-only checks from the bench directory:

```bash
cd /home/z/frappe/frappe-bench
bench --site erpnext-coa.test execute used_car_erp.used_car_erp.services.advance_settlement_readiness_service.find_advance_settlement_readiness_candidates
bench --site erpnext-coa.test execute used_car_erp.used_car_erp.services.advance_settlement_readiness_service.run_advance_settlement_readiness --kwargs "{'sales_invoice': 'ACC-SINV-2026-00004'}"
```

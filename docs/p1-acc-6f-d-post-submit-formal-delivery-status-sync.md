# P1-ACC-6F-D Post-submit Formal Delivery Status Sync

Last reviewed: 2026-06-19

Phase: `P1-ACC-6F-D`

## Purpose

P1-ACC-6F-D 是 Sales Invoice submit 後的正式交車會計文件狀態同步。

它不是 submit，不提交、取消或修改 Sales Invoice，也不處理預收款沖轉。

## Function

```text
used_car_erp.used_car_erp.services.formal_delivery_status_sync_service.inspect_formal_delivery_status_sync
used_car_erp.used_car_erp.services.formal_delivery_status_sync_service.run_formal_delivery_status_sync
```

Arguments:

- `sales_invoice`: optional explicit Sales Invoice name.
- `dry_run`: `1` is read-only; `0` enables write mode.

## Behavior

- `inspect_formal_delivery_status_sync()` is read-only.
- `run_formal_delivery_status_sync(..., dry_run=1)` is read-only.
- `run_formal_delivery_status_sync(..., dry_run=0)` may update only the linked `Used Car Vehicle` formal delivery sync fields.

Write mode requires `erpnext-coa.test`, `Sales Invoice.docstatus = 1`, company `OO`, a linked sold vehicle, matching `vehicle.sales_invoice`, existing target GL Entry, and existing target Stock Ledger Entry.

Allowed vehicle updates:

```python
{
    "formal_delivery_status": "已完成",
    "formal_delivery_completed_at": now(),
    "formal_delivery_completed_by": frappe.session.user,
    "formal_delivery_note": "Sales Invoice submitted and native ERPNext GL/SLE confirmed: <sales_invoice>",
}
```

If `formal_delivery_posting_date` exists and is empty, it is synced from Sales Invoice `posting_date`.

## Boundaries

This phase does not:

```text
Submit Sales Invoice.
Cancel or amend Sales Invoice.
Modify Sales Invoice.
Modify GL Entry or Stock Ledger Entry.
Create Payment Entry.
Create Delivery Note.
Create Purchase Invoice.
Create Journal Entry.
Create Stock Entry.
Create advance_settlement_journal_entry.
Handle advance settlement.
Modify Chart of Accounts.
Modify ERPNext / Frappe core.
Use raw SQL.
Use ignore_mandatory.
```

預收款沖轉 / advance settlement 是下一階段，不在本任務做。UI 簡化與 15-1 稅務邊界重構也不在本任務做，後續另開規格階段處理。

## Expected Observation

- Dry-run shows the linked vehicle would move from `銷售發票草稿` to `已完成`.
- Write mode updates only the allowed `Used Car Vehicle` fields.
- Sales Invoice remains `docstatus = 1`.
- No new GL Entry, Stock Ledger Entry, Payment Entry, Delivery Note, Journal Entry, or Stock Entry is created by this service.
- Rerun returns `already_synced` and does not write again.

## Commands

Developer checks from the app directory:

```bash
cd /home/z/frappe/frappe-bench/apps/used_car_erp
python -m compileall used_car_erp/used_car_erp/services/formal_delivery_status_sync_service.py
python -m compileall used_car_erp/used_car_erp/services/test_formal_delivery_status_sync_service.py
python -m compileall used_car_erp/used_car_erp/services/guarded_formal_sales_invoice_submit_qa_service.py
python -m compileall used_car_erp/used_car_erp/services/submitted_sales_invoice_submit_gate_snapshot_service.py
```

Live dry-run from the bench directory:

```bash
cd /home/z/frappe/frappe-bench
bench --site erpnext-coa.test execute used_car_erp.used_car_erp.services.formal_delivery_status_sync_service.inspect_formal_delivery_status_sync --kwargs "{'sales_invoice': 'ACC-SINV-2026-00004'}"
bench --site erpnext-coa.test execute used_car_erp.used_car_erp.services.formal_delivery_status_sync_service.run_formal_delivery_status_sync --kwargs "{'sales_invoice': 'ACC-SINV-2026-00004', 'dry_run': 1}"
```

Live write mode:

```bash
cd /home/z/frappe/frappe-bench
bench --site erpnext-coa.test execute used_car_erp.used_car_erp.services.formal_delivery_status_sync_service.run_formal_delivery_status_sync --kwargs "{'sales_invoice': 'ACC-SINV-2026-00004', 'dry_run': 0}"
```

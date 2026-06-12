# Formal Delivery Phase 3B Submit Sales Invoice Spec

Last reviewed: 2026-06-13

## 1. Purpose

This document defines the future implementation boundary for Formal Delivery Phase 3B.

Phase 3B is the first runtime phase that may submit the existing Sales Invoice draft and let ERPNext perform stock delivery through `update_stock = 1`.

This document is a specification only. It does not implement runtime behavior.

## 2. Current baseline

Completed foundations:

```text
Formal Delivery Phase 3 Gate Spec
Formal Delivery Phase 3A Submit Preflight Only
Formal Delivery Phase 3A-1 Submit Readiness UX
Sold Vehicle Final Checklist Foundation
Vehicle Profit and VAT Estimate Summary Foundation
Vehicle Cost Summary Foundation
Sales Invoice Draft Foundation
```

Still not open:

```text
Sales Invoice submit
formal stock delivery
advance settlement Journal Entry
Payment Entry
Delivery Note
manual Stock Entry
Tax Summary
formal VAT filing
custom COGS automation
formal delivery completion marker
```

## 3. Phase 3B decision

Phase 3B should do exactly one dangerous runtime action:

```text
Submit the existing linked Sales Invoice draft.
```

Because the draft must have `update_stock = 1`, ERPNext will handle the stock delivery through Sales Invoice submit.

Phase 3B must not handle advance settlement yet.

## 4. Strict scope

Allowed in Phase 3B:

```text
call Phase 3A preflight
submit the existing Sales Invoice draft when preflight is ready
let ERPNext update stock through Sales Invoice update_stock = 1
write minimal vehicle formal delivery submit marker
write audit log
return result to UI
```

Not allowed in Phase 3B:

```text
create Payment Entry
create Delivery Note
create manual Stock Entry
create advance settlement Journal Entry
submit settlement Journal Entry
create Tax Summary
file VAT data
perform formal 15-1 filing
create custom COGS Journal Entry
mark formal delivery fully completed
change reservation status
modify ERPNext core
modify Frappe core
```

## 5. Required preflight

Before submitting anything, the implementation must call:

```python
preflight_formal_delivery_submit(vehicle_name)
```

The action may proceed only when:

```text
preflight.ready == True
preflight.status == ready
blocked_reasons is empty
```

If the preflight is blocked, the function must stop before any mutation.

Expected blocked response:

```text
Sales Invoice 正式提交前檢查未通過，請先處理待處理項目。
```

## 6. Suggested service function

Runtime implementation should use the existing service file:

```text
used_car_erp/used_car_erp/services/vehicle_formal_delivery_service.py
```

Suggested function:

```python
def submit_formal_delivery_sales_invoice(vehicle_name: str, note: str | None = None) -> dict:
    ...
```

Suggested whitelisted method:

```python
@frappe.whitelist()
def submit_formal_delivery_sales_invoice_for_vehicle(vehicle_name, note=None):
    return submit_formal_delivery_sales_invoice(vehicle_name, note=note)
```

Do not combine Phase 3B with settlement logic.

## 7. Transaction boundary

Phase 3B should be implemented as a single controlled transaction:

```text
1. load vehicle with lock if practical
2. call preflight
3. reload vehicle and Sales Invoice
4. confirm Sales Invoice is still draft
5. submit Sales Invoice
6. write vehicle formal delivery submit marker
7. write audit log
8. return result
```

If any step fails, the transaction should roll back.

## 8. Required rechecks immediately before submit

Even after preflight, recheck these fields immediately before submit:

```text
vehicle.status == 已售出
vehicle.sales_invoice exists
vehicle.formal_delivery_status is empty or 銷售發票草稿
Sales Invoice exists
Sales Invoice.docstatus == 0
Sales Invoice.update_stock == 1
Sales Invoice has exactly one item row
item_code exists
qty == 1
serial_no exists
warehouse exists
income_account exists
grand_total matches vehicle.sold_price within tolerance
```

These rechecks prevent stale UI or race conditions.

## 9. Allowed vehicle mutations

Phase 3B may update only these vehicle fields:

```text
formal_delivery_status = 銷售發票已提交
formal_delivery_posting_date = Sales Invoice.posting_date
formal_delivery_note = note or existing note
```

Phase 3B must not set:

```text
formal_delivery_completed_at
formal_delivery_completed_by
advance_settlement_journal_entry
```

Those fields belong to later settlement and completion phases.

## 10. Sales Invoice submit effect

The only ERPNext formal document mutation in Phase 3B is:

```text
Sales Invoice.docstatus: 0 → 1
```

Because `update_stock = 1`, ERPNext may create stock ledger and accounting ledger effects as part of native Sales Invoice submit.

This is intended and must be made explicit in the UI confirmation.

Phase 3B must not create a separate Delivery Note or Stock Entry.

## 11. UI boundary

Phase 3B should add one dangerous button only after Phase 3A readiness is clear:

```text
提交 Sales Invoice 並正式出庫
```

Display condition:

```text
vehicle.status == 已售出
preflight.ready == true
sales_invoice exists
formal_delivery_status is empty or 銷售發票草稿
```

If runtime checking preflight in display condition is too heavy, the button may still appear for sold vehicles, but clicking it must always run server-side preflight before submit.

## 12. Required confirmation dialog

The button must show a strong confirmation dialog before calling the backend.

Required copy:

```text
此操作會提交 Sales Invoice，並依 ERPNext update_stock 正式出庫。
此操作可能影響收入、庫存與成本。
此操作不會自動建立 Payment Entry。
此操作不會自動完成預收款沖轉。
此操作不會完成正式交車入帳。
提交後 Sales Invoice 將不再是草稿，請確認客戶、車輛、金額、Serial No、Warehouse 與稅務資料均已確認。
```

The user must explicitly confirm.

## 13. Permission boundary

Phase 3B should require stricter permission than draft creation or preflight.

Suggested permission key:

```text
formal_delivery.submit_sales_invoice
```

Recommended role access:

```text
System Manager: allowed
Accounts Manager / Accounting: allowed
Sales: not allowed
```

If custom permission keys are not yet implemented, the service must at minimum check that the user can submit Sales Invoice or has a conservative accounting/system role.

Do not rely on front-end hiding only.

## 14. Audit logging

Phase 3B must write audit logs for both success and blocked attempts.

Suggested events:

```text
formal_delivery.sales_invoice_submit_blocked
formal_delivery.sales_invoice_submitted
```

Suggested audit properties:

```text
vehicle
sales_invoice
reservation
sold_price
grand_total
posting_date
user
before_formal_delivery_status
after_formal_delivery_status
preflight_status
blocked_reasons
```

## 15. Expected return shape

Suggested success response:

```python
{
    "vehicle": vehicle.name,
    "status": "submitted",
    "message": "Sales Invoice 已正式提交並依 update_stock 出庫。預收款沖轉仍待後續處理。",
    "sales_invoice": sales_invoice.name,
    "sales_invoice_docstatus": 1,
    "formal_delivery_status": "銷售發票已提交",
    "next_step": "建立預收款沖轉 Journal Entry 草稿",
}
```

Suggested blocked response:

```python
{
    "vehicle": vehicle.name,
    "status": "blocked",
    "message": "Sales Invoice 正式提交前檢查未通過。",
    "blocked_reasons": [...],
}
```

Expected gate failures should use validation errors or structured blocked results, not raw tracebacks.

## 16. Tests required before runtime implementation is accepted

Required tests:

```text
blocked when Phase 3A preflight is blocked
blocked when Sales Invoice is missing
blocked when Sales Invoice docstatus is not 0
blocked when update_stock is not 1
blocked when amount mismatches vehicle sold_price
blocked when formal_delivery_status is already after draft
success submits exactly one existing Sales Invoice draft
success changes Sales Invoice docstatus from 0 to 1
success updates vehicle formal_delivery_status to 銷售發票已提交
success does not create Payment Entry
success does not create Delivery Note
success does not create manual Stock Entry
success does not create advance settlement Journal Entry
success does not create Tax Summary
failure rolls back vehicle formal delivery status
blocked attempt writes audit or returns blocked reason
```

## 17. Manual QA required before enabling UI button

Before exposing the Phase 3B submit button to normal users, verify manually:

```text
1. Phase 3A preflight shows ready.
2. Sales Invoice is still Draft.
3. Sales Invoice has update_stock = 1.
4. Sales Invoice has exactly one vehicle item row.
5. Item, Serial No, Warehouse, Income Account are correct.
6. Grand total equals vehicle sold_price.
7. Deposit and final payment accounting links exist.
8. Tax metadata is confirmed.
9. Cost and VAT estimate summaries are visible.
10. Submit creates the expected ERPNext ledger / stock effects.
11. No Payment Entry is created.
12. No Delivery Note is created.
13. No manual Stock Entry is created.
14. No settlement Journal Entry is created in Phase 3B.
```

## 18. Phase 3B completion boundary

After Phase 3B succeeds, the vehicle is not fully closed.

Expected state:

```text
Sales Invoice submitted
stock delivery handled by ERPNext Sales Invoice update_stock
advance settlement still pending
formal delivery completion still pending
Tax Summary still pending
```

Next phase after Phase 3B:

```text
Phase 3C: Advance settlement Journal Entry draft
```

Do not jump directly from Phase 3B to final completion.

## 19. Current decision

Do not implement Phase 3B runtime yet.

Next safe runtime step, if approved later:

```text
Formal Delivery Phase 3B Submit Sales Invoice runtime implementation
```

That implementation must follow this specification and keep settlement logic out of Phase 3B.

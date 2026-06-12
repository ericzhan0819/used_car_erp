# Formal Delivery Phase 3E Completion Marker Spec

Last reviewed: 2026-06-13

## 1. Purpose

This document defines the future implementation boundary for Formal Delivery Phase 3E.

Phase 3E should perform the final formal delivery completion check and then mark the Used Car Vehicle formal delivery workflow as completed.

This document is a specification only. It does not implement runtime behavior.

## 2. Current baseline

Completed runtime foundations:

```text
Formal Delivery Phase 3A Submit Preflight Only
Formal Delivery Phase 3A-1 Submit Readiness UX
Formal Delivery Phase 3B Submit Sales Invoice Runtime
Formal Delivery Phase 3C Advance Settlement Journal Draft Runtime
Formal Delivery Phase 3D Submit Advance Settlement Journal Runtime
```

Current Phase 3D result:

```text
Sales Invoice submitted
ERPNext update_stock delivery completed through Sales Invoice submit
advance settlement Journal Entry submitted
formal_delivery_status = 預收款沖轉已提交
formal delivery completion still pending
```

Still not open:

```text
formal delivery completion marker
Tax Summary
formal VAT filing
custom COGS automation
reversal / cancellation flow
```

## 3. Phase 3E decision

Phase 3E should do exactly one workflow mutation:

```text
Mark Used Car Vehicle formal delivery as completed.
```

Phase 3E must not create or submit accounting / stock / tax documents.

## 4. Strict scope

Allowed in Phase 3E:

```text
load sold vehicle
verify Sales Invoice is submitted
verify stock delivery was handled by Sales Invoice update_stock
verify advance settlement Journal Entry is submitted
verify accounting settlement effect is acceptable
verify final checklist state
set formal_delivery_status = 已完成
set formal_delivery_completed_at
set formal_delivery_completed_by
write audit comment
return result to UI
```

Not allowed in Phase 3E:

```text
create Payment Entry
create Delivery Note
create manual Stock Entry
create Journal Entry
submit Journal Entry
create Tax Summary
file VAT data
perform formal 15-1 filing
create custom COGS Journal Entry
cancel or amend Sales Invoice
cancel or amend Journal Entry
change reservation status
modify ERPNext core
modify Frappe core
```

## 5. Required preconditions

Before marking formal delivery completed, the system must verify:

```text
vehicle.status == 已售出
vehicle.formal_delivery_status == 預收款沖轉已提交
vehicle.sales_invoice exists
Sales Invoice exists
Sales Invoice.docstatus == 1
Sales Invoice.update_stock == 1
vehicle.advance_settlement_journal_entry exists
Journal Entry exists
Journal Entry.docstatus == 1
Journal Entry.company == Sales Invoice.company
formal_delivery_completed_at is empty
formal_delivery_completed_by is empty
```

If formal delivery is already completed, Phase 3E must block and not rewrite completion fields automatically.

Expected blocked reason:

```text
正式交車入帳已完成，請勿重複完成。
```

## 6. Required final accounting checks

Phase 3E should verify that the settlement Journal Entry matches the Sales Invoice and has actually produced the intended settlement effect.

Minimum validation:

```text
Journal Entry is linked by vehicle.advance_settlement_journal_entry
Journal Entry.docstatus == 1
Journal Entry has credit account matching Sales Invoice.debit_to
Journal Entry settlement amount > 0
Journal Entry settlement amount <= Sales Invoice.grand_total
```

Recommended completion validation:

```text
Sales Invoice.outstanding_amount == 0 within tolerance
```

Important note:

```text
If the Phase 3C Journal Entry was created without party / reference allocation required by ERPNext, Sales Invoice.outstanding_amount may not be reduced even when the JE is submitted.
```

In that case, Phase 3E must block and require either:

```text
1. a Phase 3C/3D accounting linkage correction, or
2. an explicit accounting review override feature designed in a separate spec.
```

Do not silently mark formal delivery completed while Sales Invoice still has outstanding amount.

Expected blocked reason:

```text
Sales Invoice 應收餘額尚未清零，請先確認預收款沖轉是否正確沖抵應收帳款。
```

## 7. Required stock / delivery checks

Because Phase 3B uses Sales Invoice `update_stock = 1`, Phase 3E should verify:

```text
Sales Invoice.update_stock == 1
Sales Invoice.docstatus == 1
vehicle.item exists
vehicle.serial_no exists
vehicle.stock_warehouse exists
```

Optional stronger validation for later:

```text
verify stock ledger movement exists for Sales Invoice and vehicle serial_no
verify Serial No is no longer in the original stock warehouse when ERPNext data model supports this reliably
```

First implementation may skip deep Stock Ledger validation if it is too brittle, but it must at least require Sales Invoice submitted with `update_stock = 1`.

## 8. Required final checklist checks

Phase 3E should call or reuse the existing final check service where practical.

Recommended check:

```python
get_sold_vehicle_final_check(vehicle.name)
```

However, if the existing final check still treats post-Phase-3D states as blocked because it was originally designed for earlier phases, Phase 3E should not blindly depend on that result until the final check service is updated for post-settlement states.

Minimum Phase 3E required items:

```text
sold vehicle status is valid
Sales Invoice submitted
settlement Journal Entry submitted
no duplicate settlement draft pending
cost summary exists
profit / VAT estimate exists
Tax metadata is not 待補資料 / 待確認
```

Warnings may still exist for dashboard estimates, but completion must block on accounting, stock, and required tax metadata uncertainty.

## 9. Allowed vehicle mutations

After all gates pass, Phase 3E may update only:

```text
formal_delivery_status = 已完成
formal_delivery_completed_at = now_datetime()
formal_delivery_completed_by = frappe.session.user
formal_delivery_note = note or existing note
```

Only update `formal_delivery_note` when a note is provided.

Do not update:

```text
sales_invoice
advance_settlement_journal_entry
formal_delivery_posting_date
reservation.status
vehicle.status
```

`vehicle.status` should already be `已售出` from earlier workflow and must remain unchanged.

## 10. No document creation rule

Phase 3E must not create any ERPNext accounting, stock, or tax document.

Forbidden document types include:

```text
Payment Entry
Delivery Note
Stock Entry
Journal Entry
Tax Summary
Sales Invoice
Purchase Invoice
```

Phase 3E is a workflow completion marker only.

## 11. Transaction boundary

Phase 3E should be implemented as a controlled transaction:

```text
1. permission check
2. load vehicle
3. load Sales Invoice
4. load linked settlement Journal Entry
5. validate preconditions
6. validate accounting settlement effect
7. validate stock / delivery minimums
8. validate final checklist requirements
9. set completion marker fields
10. write audit comment
11. return result
```

If any validation fails, no mutation is allowed.

## 12. Idempotency and duplicate prevention

Rules:

```text
Do not complete if formal_delivery_status == 已完成.
Do not complete if formal_delivery_completed_at already exists.
Do not complete if formal_delivery_completed_by already exists.
Do not create replacement accounting documents.
Do not repair inconsistent status automatically.
```

If existing data is inconsistent, block and require manual accounting review or a future repair spec.

## 13. UI boundary

Phase 3E should add one final dangerous button:

```text
標記正式交車完成
```

Display condition:

```text
vehicle.status == 已售出
formal_delivery_status == 預收款沖轉已提交
sales_invoice exists
advance_settlement_journal_entry exists
formal_delivery_completed_at is empty
```

The button must not appear when:

```text
formal_delivery_status == 已完成
formal_delivery_completed_at exists
formal_delivery_completed_by exists
```

Safe route buttons may remain:

```text
開啟 Sales Invoice
開啟預收款沖轉傳票
```

Route buttons must never mutate accounting state.

## 14. Required confirmation dialog

Before marking completion, show a strong confirmation dialog:

```text
此操作會將本車正式交車入帳流程標記為已完成。

請確認 Sales Invoice 已提交並出庫。
請確認預收款沖轉 Journal Entry 已提交。
請確認 Sales Invoice 應收餘額已清零。
請確認稅務資料、成本摘要與損益估算已檢查。

此操作不會建立 Payment Entry、Delivery Note、Stock Entry、Journal Entry 或 Tax Summary。
此操作不會進行正式營業稅申報。
完成後如需更正，必須走後續 reversal / repair 流程，不可直接重複完成。
```

The user must explicitly confirm.

## 15. Permission boundary

Phase 3E should require accounting / system completion permission.

Suggested future permission key:

```text
formal_delivery.complete
```

Recommended role access:

```text
System Manager: allowed
Accounts Manager / Accounting: allowed
Sales: not allowed
```

If custom permission keys are not yet implemented, use conservative role checks and document the boundary in code comments.

## 16. Audit logging

Phase 3E must write audit logs or comments for blocked and successful attempts.

Suggested events:

```text
formal_delivery.completion_blocked
formal_delivery.completed
```

Suggested properties:

```text
vehicle
sales_invoice
settlement_journal_entry
sales_invoice_outstanding_amount
formal_delivery_completed_at
formal_delivery_completed_by
user
blocked_reasons
before_formal_delivery_status
after_formal_delivery_status
```

## 17. Expected return shape

Suggested success response:

```python
{
    "vehicle": vehicle.name,
    "status": "completed",
    "message": "正式交車入帳流程已標記完成。",
    "sales_invoice": sales_invoice.name,
    "settlement_journal_entry": journal_entry.name,
    "formal_delivery_status": "已完成",
    "formal_delivery_completed_at": vehicle.formal_delivery_completed_at,
    "formal_delivery_completed_by": vehicle.formal_delivery_completed_by,
}
```

Suggested blocked response:

```python
{
    "vehicle": vehicle.name,
    "status": "blocked",
    "message": "正式交車完成檢查未通過。",
    "blocked_reasons": [...],
}
```

## 18. Tests required before runtime implementation is accepted

Required tests:

```text
blocked when vehicle formal_delivery_status is not 預收款沖轉已提交
blocked when Sales Invoice is missing
blocked when Sales Invoice is not submitted
blocked when Sales Invoice.update_stock != 1
blocked when settlement Journal Entry is missing
blocked when settlement Journal Entry is not submitted
blocked when Sales Invoice outstanding_amount is not zero
blocked when formal_delivery_completed_at already exists
blocked when formal_delivery_completed_by already exists
blocked when tax metadata is not confirmed enough
success sets formal_delivery_status to 已完成
success sets formal_delivery_completed_at
success sets formal_delivery_completed_by
success does not change vehicle.status
success does not change reservation.status
success does not create Payment Entry
success does not create Delivery Note
success does not create manual Stock Entry
success does not create Journal Entry
success does not create Tax Summary
blocked case does not mutate completion fields
```

## 19. Manual QA required before enabling UI button

Before exposing Phase 3E to normal users, manually verify:

```text
1. Sales Invoice is submitted.
2. Sales Invoice update_stock is enabled.
3. Stock delivery is reflected as expected in ERPNext.
4. Settlement Journal Entry is submitted.
5. Sales Invoice outstanding_amount is zero or confirmed by approved accounting override.
6. No extra Payment Entry was created by the custom app.
7. No extra Delivery Note was created by the custom app.
8. No manual Stock Entry was created by the custom app.
9. No Tax Summary was created.
10. Tax metadata is reviewed.
11. Cost summary is visible.
12. Profit / VAT estimate is visible.
13. Completion marker is written once.
14. Completion cannot be repeated.
```

## 20. Reversal and correction boundary

Phase 3E does not implement reversal, cancellation, or repair.

Future reversal / repair spec should cover:

```text
reverse completion marker safely
cancel or reverse settlement Journal Entry
cancel or amend Sales Invoice if needed
handle stock reversal if Sales Invoice update_stock was submitted
preserve audit trail
prevent partial reversal inconsistency
```

Do not add reversal logic to Phase 3E runtime.

## 21. Tax boundary

Phase 3E does not create Tax Summary and does not file VAT.

Tax-related output remains management estimate unless a later tax reporting phase is designed.

Future tax reporting phase should separately define:

```text
Tax Summary source data
15-1 input credit confirmation
output VAT confirmation
filing period
accounting review
export / report format
```

## 22. Current decision

Do not implement Phase 3E runtime yet.

Next safe runtime step, if approved later:

```text
Formal Delivery Phase 3E Completion Marker Runtime
```

That implementation must only mark completion after strict accounting and delivery gates pass, and it must keep reversal and tax reporting logic out of Phase 3E.

# Formal Delivery Phase 3 Gate Spec

Last reviewed: 2026-06-13

## 1. Purpose

This document defines the gate conditions for the future Formal Delivery Phase 3.

Phase 3 is the stage that may later submit the existing Sales Invoice draft, perform ERPNext stock delivery through `update_stock = 1`, and then handle advance settlement. This document is only a specification. It does not implement runtime behavior.

## 2. Current stable baseline

Current completed foundations:

```text
Sales Invoice Draft Foundation
Sales Invoice Draft Checklist UX
Tax Metadata Foundation
Vehicle Cost Summary Foundation
Vehicle Cost Quick Create UX
Vehicle Profit and VAT Estimate Summary Foundation
Sold Vehicle Final Checklist Foundation
```

Current blocked items:

```text
Sales Invoice submit
formal stock delivery
advance settlement Journal Entry
formal VAT filing
Tax Summary
custom COGS automation
```

## 3. Phase 3 decision

Formal delivery should eventually follow this sequence:

```text
Sales Invoice draft
→ strict gate check
→ submit Sales Invoice with update_stock = 1
→ create advance settlement Journal Entry draft
→ accounting review
→ submit settlement Journal Entry
→ mark formal delivery completed
```

The next safe development step is not submit. The next safe step is a submit preflight only.

## 4. Strict non-goals for this document

This document must not be interpreted as permission to implement runtime mutation.

Until a later implementation phase explicitly adds it, the system must not:

```text
submit Sales Invoice
create Payment Entry
create Delivery Note
create manual Stock Entry
create Journal Entry
create Tax Summary
file VAT data
settle advance receipts
recognize revenue outside ERPNext Sales Invoice submit
post custom COGS entries
change vehicle or reservation status
modify ERPNext or Frappe core
```

## 5. Primary gate input

Before any future Phase 3 action, the system must call:

```python
get_sold_vehicle_final_check(vehicle_name)
```

The action may proceed only when:

```text
final_check.status == ready
```

If status is `blocked` or `warning`, the action must stop with a clear validation message.

Warning is not enough for formal delivery because warning means human review is still open.

## 6. Required checks

The final checklist must confirm:

```text
成交狀態
訂金入帳
尾款入帳
ERPNext 庫存連結
Sales Invoice 草稿
成本摘要
損益與營業稅估算
稅務資料
```

For Phase 3, tax metadata should be stricter than the read-only dashboard:

```text
vehicle_tax_mode != 待確認
tax_review_status in 已初步判斷 / 已確認 / 已調整 / 已鎖定
```

Recommended production setting:

```text
tax_review_status in 已確認 / 已鎖定
```

## 7. Sales Invoice gate

The linked Sales Invoice must exist and remain draft:

```text
sales_invoice exists
docstatus == 0
```

Required checks:

```text
customer exists
company exists
posting_date exists
grand_total > 0
update_stock == 1
at least one item row exists
item_code exists
qty == 1
serial_no exists
warehouse exists
income_account exists
```

Amount must match the authoritative sold amount. If the implementation chooses a different amount source, it must document that source before submit is enabled.

## 8. Vehicle and stock gate

The vehicle must have:

```text
status == 已售出
item exists
serial_no exists
stock_warehouse exists
sales_invoice exists
formal_delivery_status is empty or 銷售發票草稿
```

Do not create a manual Stock Entry for delivery. The intended route is Sales Invoice with `update_stock = 1`.

## 9. Money flow and accounting gate

The following links must exist:

```text
deposit_money_flow
deposit_voucher_draft
deposit_journal_entry
final_money_flow
final_voucher_draft
final_journal_entry
```

This confirms that deposit and final payment were already reviewed by accounting before formal delivery.

## 10. Cost and profit gate

The system must verify:

```text
purchase_price > 0
total_cost >= purchase_price
sold_price > 0
gross_margin is available
```

Negative gross margin should not block by itself. Negative margin is a business result, not a data integrity error.

## 11. VAT estimate gate

The system must retrieve:

```python
get_vehicle_profit_tax_estimate(vehicle_name)
```

Required result:

```text
tax_estimate_status != 資料不足
tax_estimate_status != 需確認
vehicle_tax_mode != 待確認
```

The VAT estimate remains management-only until a later formal Tax Summary phase exists.

## 12. Recommended implementation phases

### Phase 3A: Submit preflight only

Goal:

```text
return strict ready / blocked reasons
no Sales Invoice submit
no Journal Entry
no formal delivery status mutation
```

Suggested function:

```python
def preflight_formal_delivery_submit(vehicle_name: str) -> dict:
    ...
```

### Phase 3B: Submit Sales Invoice only

Allowed mutation:

```text
Sales Invoice docstatus 0 → 1
ERPNext stock movement through Sales Invoice update_stock = 1
Used Car Vehicle.formal_delivery_status may become 銷售發票已提交
```

Still not included:

```text
Payment Entry
Delivery Note
manual Stock Entry
advance settlement Journal Entry
Tax Summary
custom COGS entry
```

### Phase 3C: Advance settlement Journal Entry draft

Create a draft Journal Entry to settle advance or temporary receipt balances against the receivable created by Sales Invoice.

The journal must remain draft until accounting review.

### Phase 3D: Settlement submit

Allow an accounting role to submit the settlement Journal Entry after explicit confirmation.

### Phase 3E: Formal delivery completion marker

Mark formal delivery completed only after Sales Invoice submit and settlement handling are complete.

Allowed vehicle fields:

```text
formal_delivery_status
formal_delivery_completed_at
formal_delivery_completed_by
formal_delivery_note
advance_settlement_journal_entry
```

## 13. UI boundary

Before Phase 3B, the UI may only show:

```text
正式交車提交前檢查
```

The future submit button should use a clear label such as:

```text
提交 Sales Invoice 並正式出庫
```

The confirmation dialog must explain that this changes ERPNext accounting and stock records.

## 14. Permissions

Future runtime actions should require stricter permissions than draft creation.

Suggested permission areas:

```text
formal_delivery.preflight
formal_delivery.submit_sales_invoice
formal_delivery.create_settlement_draft
formal_delivery.submit_settlement
formal_delivery.complete
```

Suggested role boundary:

```text
System Manager: all
Accounting / Accounts Manager: submit and settlement actions
Sales: checklist view only
```

## 15. Audit logging

Future runtime mutations must log:

```text
formal_delivery.submit_preflight_passed
formal_delivery.submit_preflight_blocked
formal_delivery.sales_invoice_submitted
formal_delivery.settlement_draft_created
formal_delivery.settlement_submitted
formal_delivery.completed
```

Audit properties should include:

```text
vehicle
sales_invoice
reservation
amounts
user
before_status
after_status
```

## 16. User-facing gate errors

Expected gate failures should return clear messages, for example:

```text
Sales Invoice 草稿尚未建立。
Sales Invoice 已不是草稿，請人工確認。
訂金或尾款入帳尚未完整。
稅務資料尚未完整確認，正式申報前仍需確認。
ERPNext Item、Serial No 或 Warehouse 尚未完整。
成本摘要尚未完整。
```

Do not expose raw tracebacks for expected gate failures.

## 17. Future test requirements

Future Phase 3 implementation must test:

```text
blocked when final checklist is blocked
blocked when final checklist is warning
blocked when Sales Invoice missing
blocked when Sales Invoice docstatus != 0
blocked when update_stock != 1
blocked when serial_no missing
blocked when warehouse missing
blocked when money-flow accounting linkage missing
blocked when tax metadata is pending
Sales Invoice submit succeeds only when all gates pass
no Payment Entry is created
no Delivery Note is created
no manual Stock Entry is created
settlement Journal Entry is not created before its phase
vehicle formal_delivery fields update only in the intended phase
```

## 18. Current decision

Do not implement Phase 3 runtime yet.

Next safe development step:

```text
Phase 3A: formal delivery submit preflight only
```

Phase 3A should return strict gate results without submitting or creating any ERPNext formal document.

## 19. Phase 3A implementation status

Phase 3A 已實作 submit preflight only。

此 service 只回傳 ready / blocked、checks 與 blocked reasons，不提交 Sales Invoice、不建立 Journal Entry、不改 formal delivery status。

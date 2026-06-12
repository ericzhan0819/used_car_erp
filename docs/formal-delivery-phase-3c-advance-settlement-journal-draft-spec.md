# Formal Delivery Phase 3C Advance Settlement Journal Draft Spec

Last reviewed: 2026-06-13

## 1. Purpose

This document defines the future implementation boundary for Formal Delivery Phase 3C.

Phase 3C should create a draft Journal Entry to settle customer advance / temporary receipt balances against the receivable created by the submitted Sales Invoice.

Phase 3C runtime 已實作：建立預收款沖轉 Journal Entry 草稿並回寫 vehicle.advance_settlement_journal_entry。

此階段仍不提交 Journal Entry、不建立 Payment Entry、不建立 Delivery Note、不建立 manual Stock Entry、不建立 Tax Summary，也不標記正式交車完成。

## 2. Current baseline

Completed runtime foundations:

```text
Formal Delivery Phase 3A Submit Preflight Only
Formal Delivery Phase 3A-1 Submit Readiness UX
Formal Delivery Phase 3B Submit Sales Invoice Runtime
```

Current Phase 3B result:

```text
Sales Invoice submitted
ERPNext update_stock delivery completed through Sales Invoice submit
formal_delivery_status = 銷售發票已提交
advance settlement still pending
formal delivery completion still pending
```

Still not open:

```text
advance settlement Journal Entry draft
settlement Journal Entry submit
Payment Entry
Delivery Note
manual Stock Entry
Tax Summary
formal VAT filing
formal delivery completion marker
custom COGS automation
```

## 3. Phase 3C decision

Phase 3C should create exactly one draft Journal Entry:

```text
Debit: advance / temporary receipt liability account
Credit: Accounts Receivable account related to the submitted Sales Invoice
```

The Journal Entry must remain draft.

Phase 3C must not submit the Journal Entry.

## 4. Strict scope

Allowed in Phase 3C:

```text
load sold vehicle
verify Sales Invoice has been submitted
calculate settlement amount
resolve advance liability account
resolve receivable account
create one draft Journal Entry
link draft Journal Entry back to Used Car Vehicle.advance_settlement_journal_entry
write audit comment
return result to UI
```

Not allowed in Phase 3C:

```text
submit Journal Entry
create Payment Entry
create Delivery Note
create manual Stock Entry
create Tax Summary
file VAT data
perform formal 15-1 filing
create custom COGS Journal Entry
mark formal delivery fully completed
change reservation status
cancel or amend Sales Invoice
modify ERPNext core
modify Frappe core
```

## 5. Required preconditions

Before creating the settlement Journal Entry draft, the system must verify:

```text
vehicle.status == 已售出
vehicle.formal_delivery_status == 銷售發票已提交
vehicle.sales_invoice exists
Sales Invoice exists
Sales Invoice.docstatus == 1
Sales Invoice.outstanding_amount >= 0
vehicle.advance_settlement_journal_entry is empty
```

If `advance_settlement_journal_entry` already exists, Phase 3C must not create another draft automatically.

Expected blocked reason:

```text
預收款沖轉傳票草稿已存在，請先人工確認既有草稿。
```

## 6. Source accounting links

The vehicle must already have accounting links for deposit and final payment:

```text
deposit_money_flow
deposit_voucher_draft
deposit_journal_entry
final_money_flow
final_voucher_draft
final_journal_entry
```

These links prove that the customer receipts were reviewed and posted before formal delivery.

If any of these links are missing, Phase 3C must block.

## 7. Settlement amount

Recommended settlement amount:

```text
settlement_amount = min(total_advance_received, Sales Invoice.outstanding_amount or Sales Invoice.grand_total)
```

The first implementation may use the vehicle / reservation amount basis already used by Sales Invoice draft creation, but the chosen authoritative source must be explicit.

Minimum rule:

```text
settlement_amount > 0
settlement_amount <= Sales Invoice.grand_total
```

If the total collected amount is greater than Sales Invoice grand total, the system must not silently settle the excess. Overpayment handling belongs to a later dedicated phase.

Expected blocked reason:

```text
預收款金額與 Sales Invoice 金額不一致，請先人工確認是否有溢收或退款。
```

## 8. Account resolution

Phase 3C must resolve two account sides:

```text
advance liability account
receivable account
```

### 8.1 Advance liability account

Preferred source order:

```text
1. Account used in the posted deposit Journal Entry credit line
2. Account used in the posted final payment Journal Entry credit line
3. configured default advance / temporary receipt account
```

If deposit and final payment use different liability accounts, the draft Journal Entry should either:

```text
create separate debit lines per liability account
```

or block with a clear message until account mapping is confirmed.

Recommended first implementation:

```text
support one common liability account
block if multiple liability accounts are detected
```

Expected blocked reason:

```text
訂金與尾款使用不同預收款科目，請先人工確認沖轉科目。
```

### 8.2 Receivable account

Preferred source order:

```text
1. Sales Invoice.debit_to
2. Sales Invoice customer receivable account from ERPNext defaults
```

Recommended first implementation:

```text
use Sales Invoice.debit_to only
block if missing
```

Expected blocked reason:

```text
Sales Invoice 應收帳款科目缺失，請先人工確認。
```

## 9. Draft Journal Entry structure

Journal Entry should be draft:

```text
docstatus = 0
voucher_type = Journal Entry
company = Sales Invoice.company
posting_date = today or Sales Invoice.posting_date, depending on selected policy
user_remark includes vehicle and Sales Invoice reference
```

Recommended posting date policy for first implementation:

```text
posting_date = Sales Invoice.posting_date
```

Lines:

```text
Debit advance liability account: settlement_amount
Credit receivable account: settlement_amount
```

If multiple liability accounts are supported later:

```text
Debit each liability account by its settled amount
Credit receivable account by total settlement amount
```

The Journal Entry must balance exactly.

## 10. Linkage back to vehicle

After creating the draft Journal Entry, Phase 3C may update:

```text
Used Car Vehicle.advance_settlement_journal_entry = Journal Entry.name
```

Phase 3C may also update:

```text
formal_delivery_status = 預收款沖轉草稿
```

However, if `formal_delivery_status` options do not yet include `預收款沖轉草稿`, the implementation must first update the DocType options or avoid changing status.

Do not set:

```text
formal_delivery_completed_at
formal_delivery_completed_by
```

Those fields belong to later completion phase.

## 11. Required DocType option update

Before runtime implementation, confirm whether `Used Car Vehicle.formal_delivery_status` has enough states.

Recommended options:

```text
未處理
銷售發票草稿
銷售發票已提交
預收款沖轉草稿
預收款沖轉已提交
已完成
```

If adding options, the migration must not break existing values.

## 12. UI boundary

Phase 3C should add one button after Sales Invoice has been submitted:

```text
建立預收款沖轉傳票草稿
```

Display condition:

```text
vehicle.status == 已售出
formal_delivery_status == 銷售發票已提交
sales_invoice exists
advance_settlement_journal_entry is empty
```

The button must not appear after a settlement draft exists.

## 13. Required confirmation dialog

Before creating the draft Journal Entry, show a confirmation dialog:

```text
此操作會建立預收款沖轉 Journal Entry 草稿。
此草稿會將已入帳的訂金 / 尾款預收款沖轉至 Sales Invoice 應收帳款。
此操作不會提交 Journal Entry。
此操作不會建立 Payment Entry。
此操作不會完成正式交車入帳。
建立後仍須由會計人工確認與提交。
```

The user must explicitly confirm.

## 14. Permission boundary

Phase 3C should require accounting-level permission.

Suggested future permission key:

```text
formal_delivery.create_settlement_draft
```

Recommended role access:

```text
System Manager: allowed
Accounts Manager / Accounting: allowed
Sales: not allowed
```

If custom permission keys are not yet implemented, use conservative role checks and document the boundary in code comments.

## 15. Audit logging

Phase 3C must write audit logs or comments for blocked and successful attempts.

Suggested events:

```text
formal_delivery.settlement_draft_blocked
formal_delivery.settlement_draft_created
```

Suggested properties:

```text
vehicle
sales_invoice
settlement_journal_entry
settlement_amount
advance_liability_account
receivable_account
user
blocked_reasons
before_formal_delivery_status
after_formal_delivery_status
```

## 16. Expected return shape

Suggested success response:

```python
{
    "vehicle": vehicle.name,
    "status": "draft_created",
    "message": "預收款沖轉 Journal Entry 草稿已建立，仍需會計人工確認與提交。",
    "sales_invoice": sales_invoice.name,
    "journal_entry": journal_entry.name,
    "journal_entry_docstatus": 0,
    "settlement_amount": settlement_amount,
    "formal_delivery_status": "預收款沖轉草稿",
    "next_step": "會計確認並提交預收款沖轉 Journal Entry",
}
```

Suggested blocked response:

```python
{
    "vehicle": vehicle.name,
    "status": "blocked",
    "message": "預收款沖轉傳票草稿建立前檢查未通過。",
    "blocked_reasons": [...],
}
```

## 17. Tests required before runtime implementation is accepted

Required tests:

```text
blocked when Sales Invoice is not submitted
blocked when vehicle formal_delivery_status is not 銷售發票已提交
blocked when advance_settlement_journal_entry already exists
blocked when deposit/final accounting links are missing
blocked when settlement amount is zero
blocked when settlement amount exceeds Sales Invoice grand_total
blocked when receivable account is missing
blocked when advance liability account is missing
blocked when deposit and final use different liability accounts if first implementation supports only one account
success creates one draft Journal Entry only
success Journal Entry docstatus == 0
success Journal Entry is balanced
success debits advance liability account
success credits Sales Invoice receivable account
success links Journal Entry to vehicle.advance_settlement_journal_entry
success does not submit Journal Entry
success does not create Payment Entry
success does not create Delivery Note
success does not create manual Stock Entry
success does not create Tax Summary
success does not mark formal delivery completed
```

## 18. Manual QA required before enabling UI button

Before exposing Phase 3C to normal users, manually verify:

```text
1. Sales Invoice is submitted.
2. Vehicle formal_delivery_status is 銷售發票已提交.
3. Deposit and final payment Journal Entries exist and are posted.
4. Advance liability account is correct.
5. Sales Invoice debit_to receivable account is correct.
6. Settlement amount equals intended collected amount.
7. Draft Journal Entry lines are balanced.
8. Draft Journal Entry remains docstatus 0.
9. No Payment Entry is created.
10. No Delivery Note is created.
11. No manual Stock Entry is created.
12. No Tax Summary is created.
13. Formal delivery is not marked completed.
```

## 19. Completion boundary

After Phase 3C succeeds, expected state:

```text
Sales Invoice submitted
settlement Journal Entry draft created
advance_settlement_journal_entry linked
settlement submit still pending
formal delivery completion still pending
Tax Summary still pending
```

Next phase after Phase 3C:

```text
Phase 3D: Submit advance settlement Journal Entry after accounting review
```

Do not jump directly from Phase 3C to final completion.

## 20. Implementation status

Phase 3C runtime is implemented as:

```text
Formal Delivery Phase 3C Advance Settlement Journal Draft Runtime
```

The implementation creates only one draft Journal Entry and keeps submission / completion logic out of Phase 3C.

Journal Entry submit and formal delivery completion remain reserved for later phases.

# Formal Delivery Phase 3D Submit Advance Settlement Journal Spec

Last reviewed: 2026-06-13

## 1. Purpose

This document defines the future implementation boundary for Formal Delivery Phase 3D.

Phase 3D should allow accounting users to submit the existing advance settlement Journal Entry draft created by Phase 3C.

This document is a specification only. It does not implement runtime behavior.

## 2. Current baseline

Completed runtime foundations:

```text
Formal Delivery Phase 3A Submit Preflight Only
Formal Delivery Phase 3A-1 Submit Readiness UX
Formal Delivery Phase 3B Submit Sales Invoice Runtime
Formal Delivery Phase 3C Advance Settlement Journal Draft Runtime
```

Current Phase 3C result:

```text
Sales Invoice submitted
ERPNext update_stock delivery completed through Sales Invoice submit
advance settlement Journal Entry draft created
advance_settlement_journal_entry linked on Used Car Vehicle
formal_delivery_status = 預收款沖轉草稿
formal delivery completion still pending
```

Still not open:

```text
advance settlement Journal Entry submit
formal delivery completion marker
Payment Entry
Delivery Note
manual Stock Entry
Tax Summary
formal VAT filing
custom COGS automation
```

## 3. Phase 3D decision

Phase 3D should do exactly one dangerous runtime action:

```text
Submit the existing linked advance settlement Journal Entry draft.
```

Phase 3D must not create a new Journal Entry.

Phase 3D must not mark formal delivery completed.

## 4. Strict scope

Allowed in Phase 3D:

```text
load sold vehicle
verify Sales Invoice is submitted
verify advance settlement Journal Entry draft exists
validate Journal Entry structure and accounts
submit the existing Journal Entry draft
update vehicle formal_delivery_status to 預收款沖轉已提交
write audit comment
return result to UI
```

Not allowed in Phase 3D:

```text
create a new Journal Entry
create Payment Entry
create Delivery Note
create manual Stock Entry
create Tax Summary
file VAT data
perform formal 15-1 filing
create custom COGS Journal Entry
mark formal delivery fully completed
set formal_delivery_completed_at
set formal_delivery_completed_by
change reservation status
cancel or amend Sales Invoice
modify ERPNext core
modify Frappe core
```

## 5. Required preconditions

Before submitting the settlement Journal Entry, the system must verify:

```text
vehicle.status == 已售出
vehicle.formal_delivery_status == 預收款沖轉草稿
vehicle.sales_invoice exists
Sales Invoice exists
Sales Invoice.docstatus == 1
vehicle.advance_settlement_journal_entry exists
Journal Entry exists
Journal Entry.docstatus == 0
Journal Entry.company == Sales Invoice.company
Journal Entry.voucher_type == Journal Entry
Journal Entry has balanced debit and credit totals
Journal Entry amount > 0
```

If Journal Entry is already submitted:

```text
blocked
```

Do not silently repair status in Phase 3D.

Expected blocked reason:

```text
預收款沖轉 Journal Entry 已不是草稿，請先人工確認。
```

## 6. Required accounting validation

The linked Journal Entry must match the expected Phase 3C settlement shape.

Minimum validation:

```text
exactly one debit side account or supported debit lines
exactly one credit side receivable account
credit account == Sales Invoice.debit_to
total debit == total credit
settlement amount <= Sales Invoice.grand_total
settlement amount > 0
```

Recommended first implementation:

```text
support the one-liability-account draft created by Phase 3C only
block if Journal Entry has unexpected extra lines
block if credit account does not match Sales Invoice.debit_to
block if debit side cannot be confirmed as liability / payable / temporary account
```

Expected blocked reasons:

```text
預收款沖轉 Journal Entry 分錄結構與 Phase 3C 草稿規格不一致。
預收款沖轉 Journal Entry 應收帳款科目與 Sales Invoice 不一致。
預收款沖轉 Journal Entry 金額與 Sales Invoice 不一致，請先人工確認。
```

## 7. Idempotency and duplicate prevention

Phase 3D must be idempotent at the business level.

Rules:

```text
Only submit the Journal Entry linked by vehicle.advance_settlement_journal_entry.
Do not search for another Journal Entry automatically.
Do not create a replacement Journal Entry automatically.
Do not submit if vehicle.formal_delivery_status is already 預收款沖轉已提交 or 已完成.
Do not submit if Journal Entry.docstatus != 0.
```

If existing data is inconsistent, Phase 3D should block and require a separate repair tool or manual accounting review.

## 8. Transaction boundary

Phase 3D should be implemented as a controlled transaction:

```text
1. permission check
2. load vehicle
3. load Sales Invoice
4. load linked Journal Entry
5. validate preconditions
6. validate Journal Entry structure
7. submit Journal Entry
8. update vehicle formal_delivery_status
9. write audit comment
10. return result
```

If any validation fails before step 7, no mutation is allowed.

If Journal Entry submit fails, the vehicle status must not be changed.

## 9. Allowed vehicle mutations

After successful Journal Entry submit, Phase 3D may update:

```text
formal_delivery_status = 預收款沖轉已提交
formal_delivery_note = note or existing note
```

Only update `formal_delivery_note` when a note is provided.

Phase 3D must not set:

```text
formal_delivery_completed_at
formal_delivery_completed_by
```

These fields belong to Phase 3E formal delivery completion.

## 10. Journal Entry submit effect

The only formal accounting document mutation in Phase 3D is:

```text
Journal Entry.docstatus: 0 → 1
```

This may create native ERPNext GL effects. That is intended.

Phase 3D must not create Payment Entry, Delivery Note, Stock Entry, Tax Summary, or any extra Journal Entry.

## 11. UI boundary

Phase 3D should add one dangerous button after the settlement draft exists:

```text
提交預收款沖轉傳票
```

Display condition:

```text
vehicle.status == 已售出
formal_delivery_status == 預收款沖轉草稿
advance_settlement_journal_entry exists
```

The button must not appear when:

```text
formal_delivery_status == 預收款沖轉已提交
formal_delivery_status == 已完成
advance_settlement_journal_entry is empty
```

The UI may also show a safe route button:

```text
開啟預收款沖轉傳票
```

The route button must never submit.

## 12. Required confirmation dialog

Before submitting the Journal Entry, show a strong confirmation dialog:

```text
此操作會提交預收款沖轉 Journal Entry。

提交後會將已入帳的訂金 / 尾款預收款沖轉至 Sales Invoice 應收帳款。
此操作可能影響正式會計分錄。
此操作不會建立 Payment Entry。
此操作不會建立 Delivery Note 或 Stock Entry。
此操作不會完成正式交車入帳。
提交後仍需進行正式交車完成檢查。
```

The user must explicitly confirm.

## 13. Permission boundary

Phase 3D should require accounting-level submit permission.

Suggested future permission key:

```text
formal_delivery.submit_settlement
```

Recommended role access:

```text
System Manager: allowed
Accounts Manager / Accounting: allowed
Sales: not allowed
```

If custom permission keys are not yet implemented, use conservative role checks and document the boundary in code comments.

## 14. Audit logging

Phase 3D must write audit logs or comments for blocked and successful attempts.

Suggested events:

```text
formal_delivery.settlement_submit_blocked
formal_delivery.settlement_submitted
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
journal_entry_docstatus_before
journal_entry_docstatus_after
```

## 15. Expected return shape

Suggested success response:

```python
{
    "vehicle": vehicle.name,
    "status": "settlement_submitted",
    "message": "預收款沖轉 Journal Entry 已提交，正式交車完成仍待後續確認。",
    "sales_invoice": sales_invoice.name,
    "journal_entry": journal_entry.name,
    "journal_entry_docstatus": 1,
    "settlement_amount": settlement_amount,
    "formal_delivery_status": "預收款沖轉已提交",
    "next_step": "正式交車完成檢查",
}
```

Suggested blocked response:

```python
{
    "vehicle": vehicle.name,
    "status": "blocked",
    "message": "預收款沖轉 Journal Entry 提交前檢查未通過。",
    "blocked_reasons": [...],
}
```

## 16. Tests required before runtime implementation is accepted

Required tests:

```text
blocked when vehicle formal_delivery_status is not 預收款沖轉草稿
blocked when Sales Invoice is missing
blocked when Sales Invoice is not submitted
blocked when advance_settlement_journal_entry is missing
blocked when Journal Entry is missing
blocked when Journal Entry is already submitted
blocked when Journal Entry is not balanced
blocked when Journal Entry has unexpected lines
blocked when credit account does not match Sales Invoice.debit_to
blocked when settlement amount is zero
blocked when settlement amount exceeds Sales Invoice.grand_total
success submits existing linked Journal Entry only
success Journal Entry docstatus becomes 1
success vehicle.formal_delivery_status becomes 預收款沖轉已提交
success does not create another Journal Entry
success does not create Payment Entry
success does not create Delivery Note
success does not create manual Stock Entry
success does not create Tax Summary
success does not mark formal delivery completed
failure before submit does not change vehicle status
```

## 17. Manual QA required before enabling UI button

Before exposing Phase 3D to normal users, manually verify:

```text
1. Sales Invoice is submitted.
2. Vehicle formal_delivery_status is 預收款沖轉草稿.
3. advance_settlement_journal_entry exists.
4. Journal Entry is still draft.
5. Journal Entry lines are balanced.
6. Debit account is the intended advance / temporary receipt liability account.
7. Credit account is Sales Invoice.debit_to.
8. Settlement amount is correct.
9. Submit creates expected ERPNext GL effects.
10. No Payment Entry is created.
11. No Delivery Note is created.
12. No manual Stock Entry is created.
13. No Tax Summary is created.
14. Formal delivery is not marked completed.
```

## 18. Completion boundary

After Phase 3D succeeds, expected state:

```text
Sales Invoice submitted
settlement Journal Entry submitted
formal_delivery_status = 預收款沖轉已提交
formal delivery completion still pending
Tax Summary still pending
```

Next phase after Phase 3D:

```text
Phase 3E: Formal delivery completion check and marker
```

Do not jump directly from Phase 3D to final completion without a separate completion gate.

## 19. Reversal and cancellation boundary

Phase 3D does not implement reversal or cancellation.

If the submitted settlement Journal Entry is wrong, the correction flow must be designed separately.

Future reversal spec should cover:

```text
cancel submitted Journal Entry
cancel or amend Sales Invoice if needed
reverse formal_delivery_status safely
preserve audit trail
prevent partial reversal inconsistency
```

Do not add reversal logic to Phase 3D runtime.

## 20. Current decision

Do not implement Phase 3D runtime yet.

Next safe runtime step, if approved later:

```text
Formal Delivery Phase 3D Submit Advance Settlement Journal Runtime
```

That implementation must submit only the linked settlement Journal Entry and keep final completion logic out of Phase 3D.

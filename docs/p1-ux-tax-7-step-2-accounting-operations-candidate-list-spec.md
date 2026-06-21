# P1-UX-TAX-7 Step 2 Accounting Operations Candidate List Spec

Date: 2026-06-21

Phase: `P1-UX-TAX-7`

Status: Step 4 / Step 5 Desk Page and Workspace shortcut implemented

## 1. Purpose

Step 1 decided that high-impact sold-vehicle accounting actions should gradually move from `Used Car Vehicle` to `會計作業`.

Step 2 defines the read-only candidate list that Accounting Operations should use before any UI or runtime move is implemented.

This document answers:

```text
Which sold vehicles should appear in Accounting Operations?
Why are they candidates?
Which action category do they belong to?
What fields should the accounting user see?
Where should each row link?
Which backend service would a later action call?
```

This step is documentation-only.

## 2. Scope

Allowed in this step:

```text
Define candidate categories.
Define read-only candidate conditions.
Define display fields.
Define route targets.
Define blocked / repair categories.
Define later step sequence.
Sync README.md and docs/current-state.md.
```

Not allowed in this step:

```text
No Desk Page.
No new service.
No whitelisted method.
No JS change.
No Python runtime change.
No DocType JSON change.
No Workspace JSON change.
No hooks.py change.
No permission change.
No document creation.
No Sales Invoice submit.
No Journal Entry creation / submit.
No Sales Invoice relink repair.
```

## 3. Candidate list name

Suggested user-facing name:

```text
售車會計候選
```

Suggested route name for a later Desk Page:

```text
formal-sale-accounting-candidates
```

Suggested location:

```text
會計作業
→ 會計待辦
→ 售車會計候選
```

Do not add this shortcut in Step 2. This document only defines the target.

## 4. Candidate category overview

The candidate list should group rows into five categories.

```text
待確認銷售發票並出庫
待建立預收款沖轉草稿
待確認預收款沖轉入帳
需補資料 / blocked formal accounting
需技術修復 Sales Invoice 草稿連結
```

Each row should represent one `Used Car Vehicle` as the business source.

If a vehicle cannot be resolved but a formal Sales Invoice can be resolved, the row may still show the Sales Invoice as the route target in a later implementation.

## 5. Base source documents

Candidate data should be derived from existing documents only.

Primary source:

```text
Used Car Vehicle
```

Related sources:

```text
Sales Invoice
Journal Entry
Used Car Reservation
Used Car Money Flow
Used Car Voucher Draft
```

Read-only helper services may be used in later runtime steps, but Step 2 does not add them.

Existing service boundaries to preserve:

```text
vehicle_formal_delivery_service.preflight_formal_delivery_submit_for_vehicle
vehicle_formal_delivery_service.submit_formal_delivery_sales_invoice_for_vehicle
vehicle_formal_delivery_service.create_advance_settlement_journal_entry_draft_for_vehicle
vehicle_formal_delivery_service.submit_advance_settlement_journal_entry_for_vehicle
vehicle_formal_delivery_service.recover_sales_invoice_draft_link_for_vehicle
formal_delivery_status_sync_service.inspect_formal_delivery_status_sync
advance_settlement_readiness_inspector_service.run_advance_settlement_readiness_inspector
formal_sale_accounting_closure_inspector_service.run_formal_sale_accounting_closure_inspector
```

## 6. Category definitions

### 6.1 待確認銷售發票並出庫

Meaning:

```text
A sold vehicle has a linked Draft Sales Invoice that appears ready for accounting confirmation / formal submit review.
```

Candidate conditions:

```text
Used Car Vehicle.status = 已售出
Used Car Vehicle.sales_invoice is set
Sales Invoice.docstatus = 0
Sales Invoice is not cancelled
Vehicle formal sale accounting closure is not complete
```

Read-only checks to display:

```text
Sales Invoice draft exists
customer exists
item / serial_no / warehouse exists
amount exists
sales tax row exists
submit readiness status
```

Default route target:

```text
Sales Invoice form
```

Secondary route target:

```text
Used Car Vehicle form
```

Later action target:

```text
確認銷售發票並出庫
```

Later backend method:

```text
submit_formal_delivery_sales_invoice_for_vehicle
```

Step 2 does not call this method.

### 6.2 待建立預收款沖轉草稿

Meaning:

```text
The formal Sales Invoice is submitted and the vehicle is formally marked completed, but no advance settlement Journal Entry draft has been linked yet.
```

Candidate conditions:

```text
Used Car Vehicle.status = 已售出
Used Car Vehicle.sales_invoice is set
Sales Invoice.docstatus = 1
Used Car Vehicle.formal_delivery_status = 已完成
Used Car Vehicle.advance_settlement_journal_entry is empty
Deposit / final payment receipt Journal Entries are available
Advance settlement readiness is pass or inspectable
```

Read-only checks to display:

```text
submitted Sales Invoice exists
Sales Invoice GL Entry exists
Sales Invoice Stock Ledger Entry exists
formal_delivery_status = 已完成
received advance amount
Sales Invoice outstanding amount
readiness status
```

Default route target:

```text
Used Car Vehicle form
```

Secondary route target:

```text
Sales Invoice form
```

Later action target:

```text
建立預收款沖轉草稿
```

Later backend method:

```text
create_advance_settlement_journal_entry_draft_for_vehicle
```

Step 2 does not call this method.

### 6.3 待確認預收款沖轉入帳

Meaning:

```text
An advance settlement Journal Entry draft exists and should be reviewed / submitted by accounting.
```

Candidate conditions:

```text
Used Car Vehicle.status = 已售出
Used Car Vehicle.sales_invoice is set
Sales Invoice.docstatus = 1
Used Car Vehicle.advance_settlement_journal_entry is set
Linked Journal Entry.docstatus = 0
```

Read-only checks to display:

```text
advance settlement Journal Entry draft exists
Journal Entry debit / credit structure is inspectable
linked Sales Invoice exists
settlement amount
readiness / blocked reasons
```

Default route target:

```text
Journal Entry form
```

Secondary route targets:

```text
Used Car Vehicle form
Sales Invoice form
```

Later action target:

```text
確認預收款沖轉入帳
```

Later backend method:

```text
submit_advance_settlement_journal_entry_for_vehicle
```

Step 2 does not call this method.

### 6.4 需補資料 / blocked formal accounting

Meaning:

```text
The vehicle is in a sold or formal-sale related state, but cannot safely proceed to the next accounting action because required data is missing or inconsistent.
```

Possible candidate conditions:

```text
Used Car Vehicle.status = 已售出
missing customer
missing sold_price
missing Sales Invoice when formal sale should have started
Sales Invoice exists but linked vehicle mismatch
Sales Invoice draft readiness failed
Sales Invoice submitted but GL / Stock Ledger evidence is missing
advance settlement readiness failed
formal sale closure inspector failed
```

Read-only checks to display:

```text
blocking category
blocking reason summary
missing document / field
current safe route target
recommended owner: business / accounting / technical maintenance
```

Default route target:

```text
Used Car Vehicle form
```

Secondary route target:

```text
Sales Invoice form, if available
Journal Entry form, if available
```

Later action target:

```text
No direct write action by default.
```

Blocked rows should guide users to the source record and reason. They should not automatically repair documents.

### 6.5 需技術修復 Sales Invoice 草稿連結

Meaning:

```text
The linked Sales Invoice was cancelled, but a valid amended Draft Sales Invoice may exist and can be relinked through the guarded recovery flow.
```

Candidate conditions:

```text
Used Car Vehicle.status = 已售出
Used Car Vehicle.sales_invoice is set
Linked Sales Invoice.docstatus = 2
A unique amended Draft Sales Invoice candidate exists
Recovery state says repair is available
```

Read-only checks to display:

```text
cancelled linked Sales Invoice
replacement Draft Sales Invoice candidate
recovery readiness
blocked reasons, if repair is unavailable
```

Default route target:

```text
Used Car Vehicle form
```

Secondary route target:

```text
Replacement Sales Invoice Draft, if available
```

Later action target:

```text
修復 Sales Invoice 草稿連結
```

Later backend method:

```text
recover_sales_invoice_draft_link_for_vehicle
```

Step 2 does not call this method.

## 7. Suggested display fields

Each row should show only accounting-operations useful fields.

Suggested columns:

```text
狀態分類
車輛
車號 / 車牌
客戶
成交價
Sales Invoice
Sales Invoice 狀態
預收款沖轉 Journal Entry
下一步
阻擋原因摘要
最後更新時間
```

Optional management-only columns:

```text
購車價
管理毛利
15-1 估算狀態
```

Do not show these by default for the first candidate list unless role / permission behavior is intentionally handled.

## 8. Sorting and priority

Recommended order:

```text
1. 需技術修復 Sales Invoice 草稿連結
2. 需補資料 / blocked formal accounting
3. 待確認銷售發票並出庫
4. 待建立預收款沖轉草稿
5. 待確認預收款沖轉入帳
```

Reason:

```text
Repair and blocked states prevent normal accounting flow and should be surfaced first.
Submission and settlement tasks follow the formal sale sequence.
```

Within each category, sort by newest sold / updated vehicle first.

Already closed formal sale accounting cases should not appear in the candidate list:

```text
submitted Sales Invoice + submitted advance settlement Journal Entry
=> exclude from candidates
=> do not show as blocked
```

## 9. Route behavior

Candidate list rows should be route-first, not action-first.

Allowed route behavior:

```text
Open Used Car Vehicle
Open Sales Invoice
Open Journal Entry
Open supporting read-only summary, if a later page provides one
```

Not allowed in Step 2:

```text
Submit Sales Invoice from list
Create Journal Entry from list
Submit Journal Entry from list
Repair link from list
Bulk action
Inline mutation
```

## 10. Role boundary

Accounting users should be the target audience.

Business / sales users should not need this candidate list for normal daily vehicle work.

Recommended permission posture for later implementation:

```text
Candidate list visible to accounting / manager / owner roles only.
Vehicle page remains the source for business lifecycle actions.
High-impact accounting actions require existing backend gates even after migration.
```

Step 2 does not change any permission row or role assignment.

## 11. Later implementation sequence

### Step 3: Read-only service / page data spec or implementation

Recommended next small step:

```text
Create a read-only service or Desk Page data source for formal sale accounting candidates.
No write behavior.
No submit.
No recovery.
```

Step 3 implementation boundary:

```text
Add read-only FormalSaleAccountingCandidateService only.
Return formal sale accounting candidate payload for future Accounting Operations page consumption.
No Desk Page.
No Workspace shortcut.
No Vehicle JS change.
No Sales Invoice / Journal Entry / Used Car Vehicle write.
```

### Step 4: Read-only Desk Page

```text
Add a Desk Page that consumes the read-only candidate data.
Rows route to existing documents only.
```

Step 4 completion update:

```text
P1-UX-TAX-7 Step 4 / Step 5 已將 read-only formal sale accounting candidates 接成 Desk Page，並在 會計作業 Workspace 加入 shortcut。
此階段不會建立、提交、修復或修改 Sales Invoice、Journal Entry、Used Car Vehicle 或任何 ERPNext 文件。
```

Implemented route:

```text
/app/formal-sale-accounting-candidates
```

### Step 5: Workspace shortcut

```text
Add `售車會計候選` shortcut to `會計作業` Workspace.
```

Step 5 completion update:

```text
`會計作業` Workspace 已在 `會計待辦` 區塊加入 `售車會計候選` Page shortcut。
```

### Step 6 / Step 7: Site apply, browser smoke, and handoff

```text
Apply the Page / Workspace to erpnext-coa.test.
Confirm /app/formal-sale-accounting-candidates works.
Confirm 會計作業 shows 售車會計候選 shortcut.
Document smoke result in docs/p1-ux-tax-7-step-7-smoke-handoff.md.
```

### Step 8: Vehicle-page demotion

```text
After browser smoke confirms the Accounting Operations candidate path, demote high-impact vehicle-page accounting buttons.
Keep only business lifecycle primary action on the vehicle page.
```

## 12. Non-goals

Do not use this candidate list to introduce:

```text
new accounting sequence
new tax formula
new management profit calculation
new Payment Entry flow
new Delivery Note flow
new Purchase Invoice flow
bulk submit
bulk repair
automatic formal accounting closure
custom sidebar framework
```

## 13. Step 2 completion criteria

Step 2 is complete when:

```text
This spec exists.
README.md references Step 2.
docs/current-state.md references Step 2.
No runtime files are modified.
```

## 14. Suggested commit message

```text
docs: define accounting operations candidate list spec
```

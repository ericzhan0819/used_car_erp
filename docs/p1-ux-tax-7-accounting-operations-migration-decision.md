# P1-UX-TAX-7 Accounting Operations Migration Decision

Date: 2026-06-21

Phase: `P1-UX-TAX-7`

Status: Step 4 / Step 5 read-only Desk Page and Workspace shortcut added

## 1. Purpose

`P1-UX-TAX-6` closed the immediate Used Car Vehicle primary-action clutter problem.

The next remaining UX issue is that some high-impact sold-vehicle accounting operations still originate from the vehicle form.

This document decides which operations should remain on `Used Car Vehicle` and which operations should move toward `會計作業`.

This step is documentation-only.

## 2. Context from previous phases

Current stable direction:

```text
總覽 = business/status dashboard
車輛管理 = vehicle operation entry
會計作業 = accounting entry
```

Current vehicle-page UX rule:

```text
Used Car Vehicle exposes at most one primary lifecycle action per state.
Business users input business facts.
Accounting users review and confirm accounting documents in accounting operations.
```

Current tax / accounting boundary:

```text
15-1 is sale-side VAT estimate support, not an overview-home task.
Management profit and 15-1 estimate are read-only summaries.
Formal Journal Entry / Sales Invoice / GL details should not become the primary vehicle-page workflow.
```

## 3. Step 1 scope

Allowed in this step:

```text
Inventory current high-impact sold-vehicle accounting actions.
Map each action to its current JS entry point and backend service method.
Decide target surface: Vehicle page vs Accounting Operations.
Define next minimal implementation sequence.
Sync README.md and docs/current-state.md.
```

Not allowed in this step:

```text
No JS change.
No Python service change.
No DocType JSON change.
No Workspace JSON change.
No hooks.py change.
No permission row change.
No accounting runtime change.
No tax runtime change.
No new ERPNext document creation / submit / cancel / amend behavior.
```

## 4. Current sold-vehicle accounting actions

The current `Used Car Vehicle` form still contains these high-impact sold-vehicle accounting actions or related utility actions.

| Action | Current surface | Backend method | Risk / UX issue |
| --- | --- | --- | --- |
| 檢查提交資格 | Vehicle form button | `preflight_formal_delivery_submit_for_vehicle` | Useful read-only gate, but it is an accounting / submit readiness check, not a business lifecycle input. |
| 建立 Sales Invoice 草稿 | Vehicle form primary flow | `create_sales_invoice_draft_for_vehicle` | Draft creation is a controlled accounting document creation step. It may remain as a vehicle next-step only if framed as business-side draft preparation. |
| 確認銷售發票並出庫 | Vehicle form primary flow | `submit_formal_delivery_sales_invoice_for_vehicle` | High-impact ERPNext submit action. It creates official accounting / stock effects and should move toward Accounting Operations. |
| 建立預收款沖轉草稿 | Vehicle form primary flow | `create_advance_settlement_journal_entry_draft_for_vehicle` | Accounting-only draft generation. It should move toward Accounting Operations after the Sales Invoice is submitted. |
| 確認預收款沖轉入帳 | Vehicle form primary flow | `submit_advance_settlement_journal_entry_for_vehicle` | High-impact Journal Entry submit action. It should move toward Accounting Operations. |
| 修復 Sales Invoice 草稿連結 | Vehicle form technical maintenance group | `recover_sales_invoice_draft_link_for_vehicle` | Narrow technical recovery action. It should not be a normal vehicle-page operation. |
| 查看 Sales Invoice / Journal Entry | Vehicle form secondary document links | Route navigation only | Safe as secondary links, but should not be the main workflow. |

## 5. Target surface decision

### 5.1 Keep on Used Car Vehicle

The vehicle page may keep business-facing actions that prepare or navigate the business flow.

Allowed vehicle-page actions:

```text
完成入庫
開始整備
上架銷售
下架回庫存
建立訂金保留
建立尾款收款
確認成交
建立 Sales Invoice 草稿, if still treated as the current business next-step and guarded by readiness checks
查看相關文件 links
```

Rules:

```text
Only one primary lifecycle action should be visible at a time.
High-impact submit / accounting confirmation actions should not be normal vehicle-page primary actions.
Accounting document internals should remain secondary or collapsed.
```

### 5.2 Move toward Accounting Operations

The following actions belong in `會計作業` as the target surface:

```text
檢查提交資格
確認銷售發票並出庫
建立預收款沖轉草稿
確認預收款沖轉入帳
修復 Sales Invoice 草稿連結
blocked formal accounting cases
```

Reason:

```text
These actions create, submit, repair, or validate formal accounting / stock documents.
They require accounting judgment or controlled operational authority.
They are too high-impact to be visually presented as normal vehicle-page actions for business users.
```

## 6. Accounting Operations target UX

`會計作業` should become the home for formal sale accounting closure tasks.

Suggested grouping:

```text
會計待辦
- 待審核傳票草稿
- 單車摘要候選
- 待銷售發票確認與出庫
- 待預收款沖轉
- 需技術修復 / 需補資料

會計資料
- 金流紀錄
- 傳票草稿
- 正式會計傳票
- 銷售發票
```

The Accounting Operations user should see a task list with business-language reasons and links to source records.

The user should not need to open a vehicle and discover hidden accounting buttons manually.

## 7. Migration sequence

Do not move all actions in one patch.

### Step 2: Read-only candidate list spec

Create a spec for an Accounting Operations read-only task page that lists vehicles / Sales Invoices needing formal sale accounting actions.

Allowed:

```text
Document fields needed by the task page.
Define candidate statuses and filters.
Define route links back to Vehicle / Sales Invoice / Journal Entry.
No runtime yet.
```

### Step 3: Read-only candidate data service

Add a read-only data service for formal sale accounting candidates.

Allowed:

```text
Read-only service data.
No document creation.
No submit.
No repair.
No status writeback.
No Desk Page.
No Workspace change.
No Vehicle JS change.
```

### Step 4: Accounting Operations shortcuts

Add a shortcut from `會計作業` to the candidate page.

Allowed:

```text
Workspace shortcut only.
No vehicle-page action removal yet.
```

Step 4 / Step 5 completion update:

```text
P1-UX-TAX-7 Step 4 / Step 5 已將 read-only formal sale accounting candidates 接成 Desk Page，並在 會計作業 Workspace 加入 shortcut。
此階段不會建立、提交、修復或修改 Sales Invoice、Journal Entry、Used Car Vehicle 或任何 ERPNext 文件。
```

Desk Page route:

```text
/app/formal-sale-accounting-candidates
```

### Step 5: Workspace shortcut

`會計作業` Workspace 已在 `會計待辦` 區塊加入：

```text
售車會計候選
```

### Step 6 / Step 7: Site apply, browser smoke, and handoff

Apply the Accounting Operations candidate path to `erpnext-coa.test`, confirm it in browser, and record the handoff checkpoint.

Completion update:

```text
P1-UX-TAX-7 Step 6 site apply / smoke passed.
P1-UX-TAX-7 Step 7 handoff documented in docs/p1-ux-tax-7-step-7-smoke-handoff.md.
/app/formal-sale-accounting-candidates works.
會計作業 shows 售車會計候選 shortcut.
The path remains read-only.
```

### Step 8A: Vehicle-page action demotion spec

Step 8A defines the inventory and JS-only boundary before runtime changes.

```text
docs/p1-ux-tax-7-step-8a-vehicle-page-accounting-action-demotion-spec.md
```

### Step 8B: Vehicle-page action demotion implementation

After the Accounting Operations candidate path is confirmed in browser smoke, demote high-impact accounting actions from the vehicle page.

Allowed:

```text
Keep one business next action on Vehicle.
Move submit / settlement / recovery actions to Accounting Operations or secondary guarded links.
No backend sequence rewrite.
```

## 8. Runtime boundary

This phase does not change backend accounting behavior.

Existing services remain the source of truth:

```text
vehicle_formal_delivery_service.preflight_formal_delivery_submit_for_vehicle
vehicle_formal_delivery_service.submit_formal_delivery_sales_invoice_for_vehicle
vehicle_formal_delivery_service.create_advance_settlement_journal_entry_draft_for_vehicle
vehicle_formal_delivery_service.submit_advance_settlement_journal_entry_for_vehicle
vehicle_formal_delivery_service.recover_sales_invoice_draft_link_for_vehicle
```

Migration means moving the user-facing entry point, not rewriting accounting rules.

## 9. Non-goals

Do not use this phase to add:

```text
new tax formula
new management profit calculation
new Sales Invoice submit behavior
new Journal Entry submit behavior
new Payment Entry flow
new Delivery Note flow
new Purchase Invoice flow
new GL / Stock Ledger manipulation
new permission matrix
new custom sidebar framework
```

## 10. Step 1 completion criteria

Step 1 is complete when:

```text
This document exists.
README.md references P1-UX-TAX-7 Step 1.
docs/current-state.md references P1-UX-TAX-7 Step 1.
No runtime file is modified.
```

## 11. Suggested commit message

```text
docs: define accounting operations migration boundary
```

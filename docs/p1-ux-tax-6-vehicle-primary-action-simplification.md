# P1-UX-TAX-6 Used Car Vehicle Primary Action Simplification

Last reviewed: 2026-06-20

Phase: `P1-UX-TAX-6`

Status: Step 2 JS-only non-sold / reserved primary-action cleanup implemented

## 1. Background

`P1-UX-TAX-5` is closed. The vehicle page now has a read-only `VehicleDashboardSummaryService` consumer, duplicate dashboard headline cleanup, a read-only `單車摘要候選` Desk Page, and an Accounting Operations Workspace shortcut.

The next problem is no longer summary aggregation. The remaining UX issue is that `Used Car Vehicle` still contains too many possible form-level operations across lifecycle, accounting, cost, repair, navigation, and refresh concerns.

This phase focuses on one rule:

```text
At any business lifecycle stage, Used Car Vehicle should expose at most one primary next action.
```

All other controls must be treated as secondary utilities, moved into summary/status areas, moved to Accounting Operations, or deferred to a later phase.

## 2. Step 1 Scope

Step 1 only documents the current action surface and defines the one-primary-action boundary.

Allowed in Step 1:

```text
Read Used Car Vehicle JS
Read Used Car Vehicle DocType JSON
Read relevant P1-UX-TAX documents
Add this P1-UX-TAX-6 boundary document
Sync README / current-state references
```

Not allowed in Step 1:

```text
Do not change runtime behavior
Do not change Used Car Vehicle JS
Do not change Used Car Vehicle DocType JSON
Do not change Python services
Do not change hooks.py
Do not change Workspace JSON
Do not add buttons
Do not remove buttons
Do not create / submit / cancel / mutate ERPNext documents
```

## 3. Current Vehicle Form Layout Inventory

The current `Used Car Vehicle` DocType layout is already mostly aligned with `P1-UX-TAX-0` and `P1-UX-TAX-1`.

Current major tabs / sections:

```text
基本資料
採購
售車
收支
會計狀態
更多資訊
```

Important current fields / sections:

```text
基本資料：status, vehicle identity, specs, mechanical specs
採購：purchase_price, source / purchase information, buying document metadata
售車：sold_price, customer, sold date, delivery date, sales tax section
收支：deposit / final payment completion links and status fields
會計狀態：accounting_status_summary_html, formal_delivery_status, sales_invoice, advance_settlement_journal_entry
更多資訊：tax / registration flags, compliance dates, system links, internal notes
```

This means P1-UX-TAX-6 should not start with another DocType layout refactor. The immediate target is action simplification.

## 4. Current Button / Action Inventory

Current `used_car_vehicle.js` still registers or clears many form-level actions.

### 4.1 Form utility actions

```text
編輯資料
取消編輯
顯示文件連結
隱藏文件連結
```

Assessment:

```text
These are utilities, not business primary actions.
They may remain available, but they must not compete visually with the lifecycle primary action.
```

### 4.2 Intake / inventory lifecycle actions

```text
完成入庫
開始整備
直接上架
整備完成並上架
下架回庫存
```

Assessment:

```text
These are business lifecycle actions.
Only one should be primary at a time.
Current risk: stocked vehicles can expose multiple next-step choices, especially 開始整備 and 直接上架.
```

### 4.3 Reservation / sale workflow actions

```text
建立訂金保留
建立尾款收款
成交前檢查
確認成交
取消保留
```

Assessment:

```text
建立訂金保留 and 建立尾款收款 are business primary actions.
成交前檢查 is a preflight / inspector action and should not compete with 確認成交 as another primary action.
取消保留 is a secondary destructive action.
```

Current issue:

```text
When active reservation is ready, add_reserved_vehicle_primary_action_button can add both 成交前檢查 and 確認成交.
That violates the one-primary-action rule.
```

### 4.4 Sold vehicle / formal accounting actions

```text
建立 Sales Invoice 草稿
確認銷售發票並出庫
建立預收款沖轉草稿
確認預收款沖轉入帳
```

Assessment:

```text
These actions currently implement the formal sale accounting sequence from the vehicle page.
They are high-impact accounting / stock actions and should remain strictly gated.
For UX, only the current stage's one next action may be visible.
Longer term, accounting-heavy actions should be considered for Accounting Operations instead of the vehicle form.
```

Current positive state:

```text
get_sold_vehicle_primary_next_action already centralizes the sold-vehicle next-action sequence.
This is the closest existing pattern to preserve and generalize.
```

### 4.5 Document navigation / technical recovery actions

```text
查看銷售發票
查看預收款沖轉傳票
修復銷售發票草稿連結
```

Assessment:

```text
Document navigation is secondary.
Repair action is exceptional support / maintenance behavior.
Neither should be treated as a primary lifecycle action.
```

Boundary:

```text
Normal users should see document links through the read-only summary or a secondary More / technical area.
Repair actions should be hidden unless a narrow recovery condition is detected, and should not appear as the main next action.
```

### 4.6 Cost / estimate / refresh actions

```text
新增單車成本
重新計算成本摘要
重新整理損益與稅務估算
重新整理交車前檢查
檢查提交資格
```

Assessment:

```text
These are not primary vehicle lifecycle actions.
Cost entry belongs to 收支 / Vehicle Cost workflow.
Estimate refresh actions are mostly obsolete after P1-UX-TAX-5 read-only summary aggregation.
Preflight / check actions should become read-only status inside summary, not standalone top-level buttons competing with business next steps.
```

### 4.7 Legacy labels cleared by JS

`clear_vehicle_action_buttons` also removes several old or alternate labels:

```text
建立 ERPNext 商品
正式入庫
開啟 Sales Invoice 草稿
提交 Sales Invoice 並正式出庫
建立預收款沖轉傳票草稿
提交預收款沖轉傳票
開啟 Sales Invoice
開啟預收款沖轉傳票
顯示會計技術欄位
隱藏會計技術欄位
```

Assessment:

```text
These labels indicate past naming drift and migration residue.
P1-UX-TAX-6 should avoid reintroducing alternate labels for the same action.
```

## 5. Current Dashboard / Intro Inventory

### 5.1 Intro messages

`set_vehicle_intake_intro` currently gives stage-specific guidance for:

```text
new / incomplete intake
庫存中
整備中
上架中
保留中
已售出
封存
```

Assessment:

```text
Intro text is useful, but it should describe the current state and one next step only.
It should not explain every accounting exception or full formal delivery chain at the top of the form.
```

### 5.2 Read-only summary HTML

`accounting_status_summary_html` now renders:

```text
會計狀態
15-1 稅務估算
管理損益
```

Assessment:

```text
This is the correct place for read-only status and warning summary.
It should not add mutation actions.
```

### 5.3 Dashboard comments

The main JS still contains legacy dashboard comment producers for:

```text
保留中狀態
已售出流程進度
交車前最終檢查
正式交車提交前檢查
稅務資料提示
成本摘要
單車損益與預估營業稅
```

`used_car_vehicle_dashboard_comment_cleanup.js` suppresses duplicate headline comments for non-reserved vehicles:

```text
目前階段
流程進度
交車前最終檢查
正式交車提交狀態
正式交車提交前檢查
成本摘要
單車損益與預估營業稅
```

Assessment:

```text
P1-UX-TAX-5 made the user-facing result cleaner, but the JS still prepares several duplicate comments.
A later P1-UX-TAX-6 step may remove or stop calling legacy comment producers after confirming the summary cards cover those messages.
Step 1 does not remove them.
```

## 6. One-primary-action Boundary

The vehicle page should categorize actions into three buckets.

### 6.1 Primary action

Definition:

```text
The one business action the user is expected to perform next for the current vehicle lifecycle state.
```

Rules:

```text
At most one primary action per refresh.
Primary action must be state-derived.
Primary action must be visible only when the required gate is satisfied.
Primary action label must use business language, not accounting internals, whenever possible.
```

### 6.2 Secondary utility

Examples:

```text
編輯資料
取消編輯
查看銷售發票
查看預收款沖轉傳票
顯示 / 隱藏文件連結
取消保留
下架回庫存
```

Rules:

```text
Secondary utility may exist, but should not visually compete with the primary action.
Destructive secondary actions should remain behind confirmation.
Technical links should prefer summary / More area placement.
```

### 6.3 Accounting / technical operation

Examples:

```text
確認銷售發票並出庫
建立預收款沖轉草稿
確認預收款沖轉入帳
修復銷售發票草稿連結
檢查提交資格
```

Rules:

```text
These must remain strictly gated.
They should be candidates for migration to Accounting Operations or an accounting-focused page.
If temporarily kept on vehicle page, only the current stage's one next action may be exposed.
```

## 7. Target Primary Action Matrix

This is the boundary target for later implementation.

| Vehicle state / condition | Primary action | Secondary / moved action |
| --- | --- | --- |
| New document | none | Save / normal form editing |
| Missing required intake data | none | Intro tells user to fill VIN / purchase_price |
| Not stocked, VIN + purchase_price ready | 完成入庫 | ERPNext Item / Stock Entry details hidden behind service |
| 庫存中 and stocked | 開始整備 | 直接上架 should move to secondary / More if still needed |
| 整備中 and stocked | 整備完成並上架 | Cost entry belongs to 收支 / Vehicle Cost |
| 上架中 and stocked | 建立訂金保留 | 下架回庫存 secondary / More |
| 保留中, final payment missing | 建立尾款收款 | 取消保留 secondary / destructive |
| 保留中, payments exist but accounting not confirmed | none | Status says wait for Accounting Operations |
| 保留中, ready for sale completion | 確認成交 | 成交前檢查 should be summary / implicit gate, not another top button |
| 已售出, no Sales Invoice draft | 建立 Sales Invoice 草稿 | Accounting details stay in summary |
| 已售出, Sales Invoice draft exists | 確認銷售發票並出庫 | 查看銷售發票 secondary |
| 已售出, Sales Invoice submitted and no settlement draft | 建立預收款沖轉草稿 | Candidate for Accounting Operations migration |
| 已售出, settlement draft exists | 確認預收款沖轉入帳 | Candidate for Accounting Operations migration |
| 已售出, accounting closure completed | none | Read-only summary and document links only |
| 封存 | none | No normal business action |

## 8. Proposed Later Step Sequence

P1-UX-TAX-6 should continue in very small steps.

Suggested next steps:

```text
Step 2: JS-only action inventory cleanup for non-sold / reserved vehicles.
        Goal: stop showing multiple lifecycle buttons at once.
        No Python runtime, no DocType JSON, no Workspace.

Step 3: JS-only sold vehicle action cleanup.
        Goal: preserve get_sold_vehicle_primary_next_action and ensure related documents / repair actions stay secondary.
        No Python runtime, no service logic changes.

Step 4: Dashboard comment producer cleanup.
        Goal: remove or stop calling legacy duplicate comment producers now covered by summary HTML.
        No backend runtime change.

Step 5: Accounting Operations migration spec for high-impact accounting actions.
        Goal: decide whether submit SI / settlement actions remain on vehicle page or move to accounting page.
        Documentation first.
```

## 9. Step 2 Implementation

Step 2 has implemented the first JS-only primary-action cleanup for non-sold / reserved vehicle states.

Changed file:

```text
used_car_erp/used_car_erp/doctype/used_car_vehicle/used_car_vehicle.js
```

Detailed step document:

```text
docs/p1-ux-tax-6-step-2-non-sold-reserved-primary-action-cleanup.md
```

Implemented changes:

```text
保留中 ready state no longer shows both 成交前檢查 and 確認成交.
非已售出 / 非保留中 vehicle states now use add_non_sold_vehicle_primary_action_button.
庫存中 stocked vehicle shows 開始整備 only; 直接上架 is no longer exposed as a competing top-level button.
整備中 stocked vehicle shows 整備完成並上架 only.
上架中 stocked vehicle shows 建立訂金保留 only; 下架回庫存 is no longer exposed as a competing top-level button.
Cost / estimate refresh buttons are no longer added from the normal non-sold refresh path.
```

Step 2 did not change:

```text
Python service logic
DocType JSON
hooks.py
Workspace JSON
ERPNext core
accounting runtime
15-1 tax runtime
management profit runtime
controlled write gates
permission gates
```

## 10. Non-goals For P1-UX-TAX-6 Step 1

Step 1 does not do:

```text
No runtime changes
No JS changes
No Python service changes
No DocType JSON changes
No Workspace JSON changes
No new buttons
No button removals
No formula changes
No accounting runtime changes
No tax runtime changes
No management profit runtime changes
No ERPNext document creation
No ERPNext document submission
No ERPNext document cancellation
No GL Entry mutation
No Stock Ledger Entry mutation
```

## 11. Acceptance Criteria

Step 1 is complete when:

```text
This document exists
README references P1-UX-TAX-6 Step 1
current-state references P1-UX-TAX-6 Step 1
No runtime files are changed
No DocType JSON files are changed
No JS files are changed
No Python service files are changed
```

Suggested commit message:

```text
docs: define vehicle primary action simplification boundary
```

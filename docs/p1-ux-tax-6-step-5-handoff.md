# P1-UX-TAX-6 Step 5 Handoff

Last reviewed: 2026-06-20

Phase: `P1-UX-TAX-6`

Status: handoff / phase closure document

## 1. Scope

`P1-UX-TAX-6` focused on simplifying the `Used Car Vehicle` page after the P1-UX-TAX-5 read-only dashboard summary was introduced.

Primary goal:

```text
At any business lifecycle stage, Used Car Vehicle should expose at most one primary next action.
```

Secondary goal:

```text
Make the P1-UX-TAX-5 single vehicle summary the primary read-only summary surface.
Avoid duplicate dashboard cards and avoid flash-then-disappear cleanup behavior.
```

## 2. Completed commits

Latest pushed sequence:

```text
b1802ff polish: stop legacy vehicle dashboard comments
0ebb491 polish: group sold vehicle secondary actions
9866db2 fix: simplify vehicle primary actions for non-sold states
efd1d6d docs: define vehicle primary action simplification boundary
```

## 3. Step summary

### Step 1: Boundary document

Commit:

```text
efd1d6d docs: define vehicle primary action simplification boundary
```

Result:

```text
Added docs/p1-ux-tax-6-vehicle-primary-action-simplification.md.
Documented current Vehicle form layout, action inventory, dashboard comment inventory, and one-primary-action rule.
No runtime changes.
```

### Step 2: Non-sold / reserved primary action cleanup

Commit:

```text
9866db2 fix: simplify vehicle primary actions for non-sold states
```

Result:

```text
Replaced scattered non-sold action calls with add_non_sold_vehicle_primary_action_button.
Reserved ready state no longer shows both 成交前檢查 and 確認成交.
Normal non-sold states now expose at most one lifecycle primary action.
```

Primary action state after Step 2:

| Vehicle state / condition | Primary action |
| --- | --- |
| New document | none |
| Not stocked and existing document | 完成入庫 |
| 庫存中 and stocked | 開始整備 |
| 整備中 and stocked | 整備完成並上架 |
| 上架中 and stocked | 建立訂金保留 |
| 保留中, final payment missing | 建立尾款收款 |
| 保留中, waiting for accounting | none |
| 保留中, ready for sale completion | 確認成交 |
| 封存 | none |

### Step 3: Sold vehicle secondary action grouping

Commit:

```text
0ebb491 polish: group sold vehicle secondary actions
```

Result:

```text
Preserved get_sold_vehicle_primary_next_action as the sold-vehicle lifecycle source of truth.
Moved document links and technical operations into secondary groups.
```

Grouping after Step 3:

| Action | Group |
| --- | --- |
| 顯示 / 隱藏文件連結 | 更多資訊 |
| 查看銷售發票 | 文件連結 |
| 查看預收款沖轉傳票 | 文件連結 |
| 修復銷售發票草稿連結 | 技術維護 |

Sold vehicle primary flow preserved:

```text
No Sales Invoice draft -> 建立 Sales Invoice 草稿
Sales Invoice draft exists -> 確認銷售發票並出庫
Sales Invoice submitted, no settlement draft -> 建立預收款沖轉草稿
Settlement draft exists -> 確認預收款沖轉入帳
Accounting closure complete -> no primary action
```

### Step 4: Legacy dashboard comment producer cleanup

Commit:

```text
b1802ff polish: stop legacy vehicle dashboard comments
```

Result:

```text
Stopped calling legacy duplicate dashboard comment producers from apply_vehicle_form_mode.
Removed frm.dashboard.clear_comment fallback from used_car_vehicle_dashboard_comment_cleanup.js.
The cleanup hook now only intercepts duplicate add_comment prefixes before they enter the dashboard.
Browser smoke confirmed no flash-then-disappear behavior.
```

Stopped active calls:

```text
add_sold_vehicle_progress_comment
add_sold_vehicle_final_check_comment
add_formal_delivery_submit_preflight_comment
add_vehicle_cost_summary_comment
```

Preserved:

```text
render_accounting_status_summary
VehicleDashboardSummaryService
reserved vehicle active reservation status
used_car_vehicle_dashboard_comment_cleanup.js prefix safety net
```

## 4. Files changed across the phase

Core JS:

```text
used_car_erp/used_car_erp/doctype/used_car_vehicle/used_car_vehicle.js
used_car_erp/public/js/used_car_vehicle_dashboard_comment_cleanup.js
```

Docs:

```text
docs/p1-ux-tax-6-vehicle-primary-action-simplification.md
docs/p1-ux-tax-6-step-2-non-sold-reserved-primary-action-cleanup.md
docs/p1-ux-tax-6-step-3-sold-vehicle-secondary-action-grouping.md
docs/p1-ux-tax-6-step-4-dashboard-legacy-comment-producer-cleanup.md
docs/p1-ux-tax-6-step-5-handoff.md
README.md
docs/current-state.md
```

## 5. Explicit non-changes

`P1-UX-TAX-6` did not change:

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
formal sale accounting sequence
ERPNext document creation behavior
ERPNext document submission behavior
ERPNext document cancellation behavior
GL Entry behavior
Stock Ledger Entry behavior
```

## 6. Current expected vehicle page behavior

Expected high-level behavior:

```text
Vehicle page should no longer feel like an engineering control panel.
Each normal lifecycle state should expose at most one primary next action.
Read-only status should come from the single vehicle summary cards.
Technical links and repair actions should stay secondary.
Duplicate dashboard cards should not appear.
Dashboard cards should not flash then disappear.
```

Expected smoke states:

| State | Expected behavior |
| --- | --- |
| New document | No primary business action |
| Missing VIN / purchase price | Intro tells user what to fill |
| Not stocked | 完成入庫 only when existing complete-intake guard allows it |
| 庫存中 | 開始整備 only |
| 整備中 | 整備完成並上架 only |
| 上架中 | 建立訂金保留 only |
| 保留中, final payment missing | 建立尾款收款, cancel remains secondary/destructive |
| 保留中, accounting pending | No premature completion action |
| 保留中, ready | 確認成交 only |
| 已售出 | Sold vehicle primary action follows get_sold_vehicle_primary_next_action |
| 已售出 document links | Under 文件連結 / 更多資訊 / 技術維護 groups |
| Any non-reserved state | Single vehicle summary cards remain visible without duplicate dashboard comment cards |

## 7. Remaining known trade-offs

Legacy dashboard producer functions still exist in `used_car_vehicle.js`:

```text
add_sold_vehicle_progress_comment
add_sold_vehicle_final_check_comment
add_formal_delivery_submit_preflight_comment
add_tax_metadata_comment
add_vehicle_cost_summary_comment
add_vehicle_profit_tax_estimate_comment
```

They are not part of the active refresh path after Step 4. They were intentionally not deleted in P1-UX-TAX-6 to keep patches small and avoid unnecessary risk.

`used_car_vehicle_dashboard_comment_cleanup.js` remains as a prefix intercept safety net. It no longer clears already-rendered comments.

## 8. Recommended next phase

Do not continue expanding P1-UX-TAX-6 runtime.

Recommended next phase:

```text
P1-UX-TAX-7 / P1-ACC-OPS-1: Accounting Operations migration decision
```

Purpose:

```text
Decide whether high-impact accounting operations should stay on the vehicle page or move to Accounting Operations.
```

Candidate operations:

```text
確認銷售發票並出庫
建立預收款沖轉草稿
確認預收款沖轉入帳
修復銷售發票草稿連結
檢查提交資格
```

Recommended first step:

```text
Documentation only.
Do not move runtime yet.
Inventory current sold-vehicle accounting actions, gates, service methods, and user roles.
Define which actions belong on vehicle page versus Accounting Operations.
```

## 9. New chat handoff prompt

Use this if opening a new chat:

```text
You are taking over the used_car_erp project.
Repo: ~/frappe/frappe-bench/apps/used_car_erp
GitHub: ericzhan0819/used_car_erp
Site: erpnext-coa.test
Latest known commit: b1802ff polish: stop legacy vehicle dashboard comments

P1-UX-TAX-6 is now closed as a UX cleanup phase for Used Car Vehicle primary actions.
Completed:
- Step 1 boundary document: efd1d6d
- Step 2 non-sold / reserved primary action cleanup: 9866db2
- Step 3 sold vehicle secondary action grouping: 0ebb491
- Step 4 dashboard legacy comment cleanup: b1802ff
- Step 5 handoff document: see docs/p1-ux-tax-6-step-5-handoff.md

Current behavior target:
- Used Car Vehicle exposes at most one primary lifecycle action per state.
- Non-sold states use add_non_sold_vehicle_primary_action_button.
- Sold states use get_sold_vehicle_primary_next_action.
- Sold document links / technical operations are grouped as secondary actions.
- P1-UX-TAX-5 single vehicle summary cards are the primary read-only summary surface.
- Legacy duplicate dashboard comments should not appear or flash-then-disappear.

Do not modify Python services, DocType JSON, hooks.py, Workspace JSON, ERPNext core, accounting runtime, 15-1 tax runtime, management profit runtime, controlled write gates, permission gates, or formal sale accounting sequence unless explicitly requested.

Recommended next phase: documentation-first Accounting Operations migration decision for high-impact sold-vehicle accounting actions.
```

## 10. Suggested commit message

```text
docs: close p1 ux tax 6 handoff
```

# P1-MVP-DASH-1 Used Car Management Dashboard MVP

Last reviewed: 2026-06-20

Phase: `P1-MVP-DASH-1`

Status: Step 2 minimal dashboard entry implemented

## 1. Background

`P1-UX-TAX-6` is closed. The vehicle page now follows the one-primary-action rule and the P1-UX-TAX-5 single vehicle summary is the main read-only vehicle summary surface.

The next MVP gap is the missing used-car-specific landing page after login.

Target:

```text
Login / main entry
-> Used Car Management Dashboard
-> simple report cards
-> pending task cards
-> operation shortcut cards
```

## 2. Product positioning

`used_car_erp` is the used-car business operations layer.

ERPNext remains the underlying ERP engine.

Target split:

```text
used_car_erp = used car business operation layer
ERPNext = accounting / CRM / permissions / reporting foundation
```

Do not steer the MVP back to this direction:

```text
Used car = native Item page as the main business page
Buy car = native Purchase module as the main operation
Sell car = native Sales module as the main operation
```

Correct direction:

```text
Used Car Management app is the primary operations surface.
ERPNext native documents are backend records and controlled outputs.
```

## 3. Why Dashboard first

The system already has meaningful workflow pieces:

```text
vehicle intake
inventory lifecycle
reservation
money flow
voucher draft
accounting operations workspace
15-1 estimate read-only service
management profit read-only service
vehicle dashboard summary aggregator
vehicle page primary action cleanup
```

The missing MVP perception is:

```text
There is no clear used-car management home page after login.
```

Dashboard first is lower risk than another large vehicle form refactor because it can reuse existing read-only summaries and existing navigation targets.

## 4. Step 1 scope

Allowed in Step 1:

```text
Add this boundary document.
Define Dashboard MVP purpose, information architecture, KPI candidates, shortcut candidates, role boundary, and non-goals.
Sync README.md and docs/current-state.md references when committing locally.
No runtime behavior change.
```

Not allowed in Step 1:

```text
No Desk Page yet.
No hooks.py change.
No Workspace JSON change.
No Used Car Vehicle JS change.
No DocType JSON change.
No Python service change.
No dashboard chart runtime.
No accounting / tax / management profit runtime change.
No role or permission row change.
```

## 5. Dashboard MVP target

The Dashboard MVP should become the first used-car management landing page.

It is not a BI system.

It is an operating console.

The first screen should answer:

```text
How many cars are currently active?
What needs action?
Where should the user click next?
```

## 6. Simple metric candidates

First-version metric candidates:

```text
庫存車輛數
待售車輛數
已售車輛數
已售未收清數
本月售出數
本月成交金額
本月估算管理毛利
15-1 待確認車輛數
```

Priority order:

```text
1. total active vehicles
2. listed / available vehicles
3. reserved vehicles
4. sold vehicles this month
5. accounting-pending vehicles
6. 15-1 pending confirmation
7. month sold amount
8. estimated management profit
```

## 7. Pending task candidates

Pending task cards should use business language, not ERPNext internals.

Candidate tasks:

```text
待補購車資料
待補售車資料
待收尾款
待會計確認
待 15-1 判斷
待建立 / 檢查銷售發票草稿
待預收款沖轉
```

Rules:

```text
Pending task cards should link to existing list / page / workspace targets.
They should not mutate documents.
They should not expose GL / ledger internals on the dashboard.
```

## 8. Shortcut card candidates

Shortcut cards should provide the minimum operator-facing navigation.

First-version candidates:

```text
新增車輛
車輛庫存
客戶管理
售車作業
收款作業
單車摘要
15-1 待確認
會計作業
管理報表
```

Shortcut requirements:

```text
Use existing DocType / Page / Workspace routes where possible.
Do not build duplicate runtime just to support shortcuts.
Do not make users navigate through native Item / Purchase / Sales modules as the main used-car workflow.
```

## 9. Sidebar / navigation boundary

Dashboard is not a complete Sidebar replacement.

MVP navigation can still use Workspace / shortcuts first.

Target grouping:

```text
中古車管理
- 車輛列表
- 新增車輛
- 車輛摘要

交易作業
- 採購 / 取得
- 售車
- 收款
- 收支紀錄

會計與稅務
- 會計作業
- 15-1 待確認
- 傳票 / 文件狀態

管理報表
- 單車損益
- 庫存摘要
- 銷售摘要

設定
- 商品 / 科目設定
- 權限設定
```

First implementation can be a Desk Page plus Workspace shortcuts.

Do not build a full custom sidebar framework in this phase.

## 10. Role boundary

Business / sales users should see:

```text
vehicle identity and status
customer / sale operation status
reservation and payment status in business terms
their next operation shortcuts
non-sensitive pending tasks
```

Management users may see:

```text
purchase price
sold price
direct cost totals
management profit
15-1 estimate status
collection status
accounting document status
management KPI cards
```

Accounting users should be routed toward:

```text
Accounting Operations Workspace
voucher draft confirmation
Sales Invoice / Journal Entry status
15-1 review candidates
formal accounting closure checks
```

Step 1 does not implement role-based display logic.

It only defines the boundary.

## 11. 15-1 boundary reminder

Dashboard must preserve the P1-UX-TAX tax boundary:

```text
15-1 is only for sold-vehicle VAT estimate.
purchase_price means vehicle purchase price only.
preparation / repair / detailing / auction / agent fees do not enter 15-1 purchase cost.
management profit and 15-1 estimate are separate numbers.
```

Dashboard cards may show 15-1 status, but should not mix 15-1 with management profit.

## 12. Data-source boundary

Preferred data-source order:

```text
1. reuse existing read-only services where possible
2. add thin read-only dashboard aggregation only when needed
3. avoid write behavior
4. avoid service methods that create accounting documents
```

Existing useful foundation:

```text
VehicleDashboardSummaryService
VehicleAccountingStatusSummaryService
Vehicle15_1TaxEstimateService
VehicleManagementProfitSummaryService
Used Car Vehicle list data
Used Car Reservation / Money Flow / Voucher Draft status
Accounting Operations Workspace routes
```

## 13. Non-goals

Do not do these in P1-MVP-DASH-1:

```text
full BI dashboard
chart engine
custom report builder
complete Sidebar framework
complete role permission matrix
vehicle form rewrite
new accounting document mutation
new tax runtime
new management profit runtime
COA rewrite
Purchase Invoice flow rewrite
Sales Invoice submit behavior changes
Payment Entry migration
Laravel / ERPNext synchronization
public website integration
```

## 14. Proposed later step sequence

Suggested sequence:

```text
Step 1: Documentation boundary.
Step 2: Minimal Dashboard entry with shortcut cards.
Step 3: Read-only summary metrics.
Step 4: Role-aware card visibility.
```

## 15. Step 2 implementation boundary

Recommended Step 2 target:

```text
Create a minimal Used Car Management Dashboard entry.
Show shortcut cards.
Route cards to existing DocTypes / Pages / Workspaces.
Do not introduce dashboard calculation complexity yet.
```

Suggested Step 2 non-goals:

```text
No Python aggregation unless absolutely necessary.
No new permission matrix.
No custom Sidebar framework.
No vehicle form changes.
No accounting / tax runtime changes.
```

Step 2 implementation status:

```text
Added minimal Desk Page route: used-car-management-dashboard.
Added static placeholder metric cards, pending task cards, and shortcut cards only.
Added the page shortcut to the existing 中古車管理 Workspace.
No dashboard data service, whitelisted method, hooks.py change, permission change, accounting runtime change, or tax runtime change.
```

## 16. Suggested commit messages

Step 1:

```text
docs: define used car management dashboard mvp
```

Step 2:

```text
feat: add used car management dashboard entry
```

Step 3:

```text
feat: show dashboard mvp summary metrics
```

Step 4:

```text
feat: split dashboard shortcuts by role
```

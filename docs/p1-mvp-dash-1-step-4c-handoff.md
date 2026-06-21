# P1-MVP-DASH-1 Step 4C Handoff

Date: 2026-06-21

Phase: `P1-MVP-DASH-1`

Status: closed / pushed / browser-smoke confirmed

Latest stable commits:

```text
3616613 feat: make overview a native dashboard workspace
9bbc139 fix: render overview number cards
```

Primary test URL:

```text
http://erpnext-coa.test:8000/app/總覽
```

## 1. Goal

`P1-MVP-DASH-1` creates the first usable landing page for the used-car ERP operations flow.

Final direction:

```text
總覽 = native ERPNext Workspace Dashboard
車輛管理 = vehicle CRUD / vehicle status entry
會計作業 = accounting entry
```

The overview dashboard is a business/status entry, not an accounting task center and not a 15-1 tax screen.

## 2. Final stable behavior

`/app/總覽` is now the native Workspace dashboard itself.

It no longer redirects to:

```text
/app/used-car-management-dashboard
```

The browser-smoke result was confirmed by the user:

```text
/app/總覽 renders normally.
The six native Number Cards render normally.
```

## 3. Redirect rollback

The previous JS redirect strategy was removed because it fought Frappe Workspace routing and could make browser back / route history feel stuck.

Removed file:

```text
used_car_erp/public/js/used_car_overview_redirect.js
```

Removed hook behavior:

```text
app_include_js = "/assets/used_car_erp/js/used_car_overview_redirect.js"
```

Do not restore any of the following:

```text
used_car_overview_redirect.js
app_include_js redirect
click intercept
window.location.replace
frappe.set_route redirect
```

## 4. Native Number Cards

Step 4C adds six standard Frappe Number Cards under:

```text
used_car_erp/used_car_erp/number_card/
```

Cards:

```text
Used Car In Stock   / 在庫
Used Car Inventory  / 庫存中
Used Car Preparing  / 整備中
Used Car Listed     / 上架中
Used Car Reserved   / 保留中
Used Car Sold       / 已售出
```

Card behavior:

```text
doctype: Number Card
module: Used Car ERP
is_public: 1
is_standard: 1
type: Document Type
document_type: Used Car Vehicle
function: Count
```

Filter meaning:

```text
在庫 = status in ["庫存中", "整備中", "上架中", "保留中"]
庫存中 = status = "庫存中"
整備中 = status = "整備中"
上架中 = status = "上架中"
保留中 = status = "保留中"
已售出 = status = "已售出"
```

## 5. Number Card renderer fix

The Number Card documents existed in DB and JSON, but the Workspace UI did not render them at first.

Diagnosis:

```text
Workspace content block type = number_card
Workspace content data key = number_card_name
Workspace child table key = number_card_name
```

The Desk renderer matched the Number Card label, not the ASCII document name.

Therefore the Workspace content blocks must use the Chinese labels:

```text
在庫
庫存中
整備中
上架中
保留中
已售出
```

The final layout uses:

```text
col: 4
```

## 6. Overview Workspace structure

Current `總覽` Workspace should show:

```text
總覽

庫存狀態
- 在庫
- 庫存中
- 整備中
- 上架中
- 保留中
- 已售出

常用作業
- 新增車輛
- 車輛列表
- 單車摘要候選
```

It must not show:

```text
15-1
待 15-1 判斷
待會計確認
待處理事項
待處理檢視
中古車管理 Dashboard
used-car-management-dashboard
```

## 7. Vehicle management Workspace boundary

The old user-facing `中古車管理` Workspace wording was changed to `車輛管理`.

`車輛管理` is now the vehicle CRUD / vehicle status entry, not the dashboard home.

It should keep vehicle operation links such as:

```text
車輛列表
新增車輛
庫存中車輛
整備中車輛
上架中車輛
保留中車輛
已售出車輛
```

It should not include:

```text
中古車管理 Dashboard
總覽 Dashboard shortcut
```

Important previous bug:

```text
Changing only Workspace label/title without renaming the Workspace document caused /app/車輛管理 to show Page 車輛管理 not found.
```

That hotfix has already been pushed.

## 8. Product decisions locked by this step

### 8.1 No 15-1 on the overview home

15-1 is a sale-side VAT estimate detail. It belongs in:

```text
single vehicle summary
sale detail
tax detail
accounting / tax support data
```

It does not belong on the overview home.

### 8.2 No accounting todo center on the overview home

The overview home should be simple business status cards and operation shortcuts.

Accounting todo / confirmation flows belong in:

```text
會計作業 Workspace
```

### 8.3 No hard redirect for the overview route

`/app/總覽` should remain a native Workspace Dashboard.

Do not rebuild the overview home by forcing a route to a custom Page.

## 9. Main changed files

Workspace:

```text
used_car_erp/used_car_erp/workspace/used_car_overview/used_car_overview.json
used_car_erp/used_car_erp/workspace/used_car_management/used_car_management.json
```

Number Cards:

```text
used_car_erp/used_car_erp/number_card/used_car_in_stock/used_car_in_stock.json
used_car_erp/used_car_erp/number_card/used_car_inventory/used_car_inventory.json
used_car_erp/used_car_erp/number_card/used_car_preparing/used_car_preparing.json
used_car_erp/used_car_erp/number_card/used_car_listed/used_car_listed.json
used_car_erp/used_car_erp/number_card/used_car_reserved/used_car_reserved.json
used_car_erp/used_car_erp/number_card/used_car_sold/used_car_sold.json
```

Hooks:

```text
used_car_erp/hooks.py
```

Deleted:

```text
used_car_erp/public/js/used_car_overview_redirect.js
```

Related documents:

```text
docs/p1-mvp-dash-1-step-2-dashboard-entry.md
docs/p1-mvp-dash-1-used-car-management-dashboard-mvp.md
```

## 10. Verification record

Commands run during the phase:

```bash
python -m compileall used_car_erp/hooks.py
python -m json.tool used_car_erp/used_car_erp/workspace/used_car_overview/used_car_overview.json
find used_car_erp/used_car_erp/number_card -name '*.json' -print -exec python -m json.tool {} \;
bench build --app used_car_erp
bench --site erpnext-coa.test migrate
bench --site erpnext-coa.test reload-doc used_car_erp workspace used_car_overview
bench --site erpnext-coa.test clear-cache
bench restart
```

DB checks confirmed:

```text
Workspace: 總覽
number_cards readback normal
shortcuts readback normal
bad text checks passed
```

Number Card DB checks confirmed:

```text
6 Number Card docs exist
is_public = 1
is_standard = 1
type = Document Type
document_type = Used Car Vehicle
function = Count
filters_json correct
```

Browser smoke confirmed:

```text
/app/總覽 renders the six cards correctly.
```

## 11. Frappe export note

Frappe reload / export may create duplicate Chinese Workspace directories:

```text
used_car_erp/used_car_erp/workspace/總覽/
used_car_erp/used_car_erp/workspace/車輛管理/
used_car_erp/used_car_erp/workspace/中古車管理/
```

Do not commit these duplicate export directories after confirming they are redundant.

Tracked Workspace paths remain:

```text
used_car_erp/used_car_erp/workspace/used_car_overview/
used_car_erp/used_car_erp/workspace/used_car_management/
used_car_erp/used_car_erp/workspace/accounting_operations/
```

## 12. Next recommended step

Do not start another large dashboard refactor immediately.

Preferred next step:

```text
Used Car Vehicle Simplified UX
```

Start with documentation / spec alignment before runtime changes.

Alternative small step:

```text
P1-MVP-DASH-1 Step 4D Overview dashboard card polish
```

Possible Step 4D items:

```text
card order polish
在庫 / 庫存中 naming review
common operation shortcut order
whether to add a 車輛管理 shortcut
```

Step 4D limits:

```text
No new service.
No new runtime.
No 15-1 on overview.
No accounting todos on overview.
```

## 13. Handoff summary

Stable information architecture:

```text
總覽 = business/status Dashboard
車輛管理 = vehicle operation entry
會計作業 = accounting entry
```

Stable route:

```text
/app/總覽
```

Stable commit:

```text
9bbc139 fix: render overview number cards
```

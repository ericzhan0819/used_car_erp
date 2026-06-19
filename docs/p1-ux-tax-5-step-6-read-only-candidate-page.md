# P1-UX-TAX-5 Step 6 Read-only Vehicle Dashboard Candidate Page

Last reviewed: 2026-06-20

Phase: `P1-UX-TAX-5 Step 6`

## 1. Scope

This step adds a minimal read-only Desk Page for vehicle dashboard summary candidates.

The page consumes the existing Step 2 aggregator candidate endpoint:

```text
used_car_erp.used_car_erp.services.vehicle_dashboard_summary_service.find_vehicle_dashboard_summary_candidates
```

This step does not change the existing `會計作業` Workspace JSON. The page can be opened directly by route first, then wired into the workspace in a later step only after browser smoke verification.

## 2. Added Files

```text
used_car_erp/used_car_erp/page/vehicle_dashboard_summary_candidates/vehicle_dashboard_summary_candidates.json
used_car_erp/used_car_erp/page/vehicle_dashboard_summary_candidates/vehicle_dashboard_summary_candidates.js
```

## 3. Page Behavior

The page title is:

```text
單車摘要候選
```

The page calls:

```text
find_vehicle_dashboard_summary_candidates(limit=10)
```

It renders a compact read-only table with:

```text
車輛
銷售發票
來源
會計狀態
15-1 稅務估算狀態
管理損益狀態
動作
```

Source badges map to the existing aggregator source keys:

```text
accounting_status -> 會計
tax_estimate -> 稅務
management_profit -> 損益
```

The page also renders `source_statuses`, `warnings`, and `blocking_errors` from the aggregator payload.

## 4. Allowed Actions

Allowed row actions are navigation-only:

```text
Open Used Car Vehicle when vehicle exists.
Open Sales Invoice when vehicle is missing but sales_invoice exists.
```

These actions only call `frappe.set_route`.

## 5. Read-only Boundary

This step does not:

```text
modify backend service logic
modify Workspace JSON
modify DocType JSON
add mutation buttons
add accounting runtime
add tax runtime
add management profit runtime
add formulas
create ERPNext documents
submit ERPNext documents
cancel ERPNext documents
write back Used Car Vehicle
write back Sales Invoice
write back Journal Entry
write back GL Entry
write back Stock Ledger Entry
```

## 6. Verification

Local verification commands:

```bash
node --check used_car_erp/used_car_erp/page/vehicle_dashboard_summary_candidates/vehicle_dashboard_summary_candidates.js
python -m json.tool used_car_erp/used_car_erp/page/vehicle_dashboard_summary_candidates/vehicle_dashboard_summary_candidates.json >/dev/null
git diff --check
```

Suggested browser smoke:

```text
Open /app/vehicle-dashboard-summary-candidates.
Confirm the page calls the candidate endpoint.
Confirm rows show vehicle / sales invoice / source badges / statuses.
Confirm row buttons only navigate to existing documents.
Confirm no create / submit / cancel / write button exists.
Confirm existing 會計作業 Workspace shortcuts are unchanged.
```

## 7. Next Step

After browser smoke, the next smallest step can add a Workspace shortcut to this read-only page.

Suggested commit message:

```text
feat: add accounting workspace shortcut to vehicle dashboard candidates
```

# P1-UX-TAX-5 Step 8 Handoff

Last reviewed: 2026-06-20

Phase: `P1-UX-TAX-5 Step 8`

## 1. Summary

P1-UX-TAX-5 is now closed as a small read-only UX / dashboard cleanup phase.

The phase connected the existing read-only accounting, tax, and management profit summaries into two minimal entry points:

```text
Used Car Vehicle page summary
Accounting Operations Workspace candidate entry
```

This phase deliberately did not add new accounting runtime, tax runtime, management profit runtime, formulas, ERPNext document mutations, or write-back behavior.

## 2. Completed steps

### Step 1

Created the main P1-UX-TAX-5 scope document:

```text
docs/p1-ux-tax-5-accounting-workspace-dashboard-cleanup.md
```

### Step 2

Added read-only aggregator service:

```text
used_car_erp/used_car_erp/services/vehicle_dashboard_summary_service.py
used_car_erp/used_car_erp/services/test_vehicle_dashboard_summary_service.py
```

The aggregator wraps only existing read-only services:

```text
VehicleAccountingStatusSummaryService
Vehicle151TaxEstimateService
VehicleManagementProfitSummaryService
```

### Step 3

Connected `Used Car Vehicle` page summary display through:

```text
used_car_erp/used_car_erp/doctype/used_car_vehicle/used_car_vehicle.js
```

The page renders three summary cards inside the existing:

```text
accounting_status_summary_html
```

### Step 4

Added duplicate dashboard comment cleanup:

```text
used_car_erp/public/js/used_car_vehicle_dashboard_comment_cleanup.js
used_car_erp/hooks.py
```

The cleanup suppresses older duplicate headline comments now covered by the Step 3 summary.

### Step 5

Defined Accounting Workspace candidate list boundary:

```text
docs/p1-ux-tax-5-step-5-accounting-workspace-candidate-list-spec.md
```

### Step 6

Added read-only Desk Page:

```text
used_car_erp/used_car_erp/page/vehicle_dashboard_summary_candidates/vehicle_dashboard_summary_candidates.json
used_car_erp/used_car_erp/page/vehicle_dashboard_summary_candidates/vehicle_dashboard_summary_candidates.js
```

Desk route:

```text
/app/vehicle-dashboard-summary-candidates
```

Page title:

```text
單車摘要候選
```

### Step 7

Connected the Step 6 page into the Accounting Operations Workspace:

```text
used_car_erp/used_car_erp/workspace/accounting_operations/accounting_operations.json
```

Shortcut:

```text
會計作業
→ 會計待辦
→ 單車摘要候選
```

Shortcut target:

```text
vehicle-dashboard-summary-candidates
```

### Step 8

Synchronized closure / handoff documents and marked P1-UX-TAX-5 as a closed read-only phase.

## 3. Current UX state

### Used Car Vehicle page

The vehicle page now has a single minimal summary entry that shows:

```text
會計狀態
15-1 稅務估算
管理損益
```

It still does not add any create / submit / cancel / write action.

### Accounting Operations Workspace

The `會計作業` Workspace now includes a `單車摘要候選` shortcut under `會計待辦`.

The shortcut opens:

```text
/app/vehicle-dashboard-summary-candidates
```

The candidate page displays read-only candidate rows from:

```text
used_car_erp.used_car_erp.services.vehicle_dashboard_summary_service.find_vehicle_dashboard_summary_candidates
```

Each row only allows route navigation:

```text
Used Car Vehicle
Sales Invoice
```

## 4. Strict boundary after closure

P1-UX-TAX-5 must remain read-only.

Do not add these inside this phase:

```text
new accounting runtime
new tax runtime
new management profit runtime
new formulas
new create button
new submit button
new cancel button
write-back action
ERPNext document creation
ERPNext document submission
ERPNext document cancellation
GL Entry mutation
Stock Ledger Entry mutation
```

## 5. Local verification status

The user confirmed browser smoke after Step 7:

```text
會計作業 Workspace opens
單車摘要候選 shortcut appears
shortcut opens the candidate page normally
```

Static checks used during Step 7 / Step 8:

```bash
python -m json.tool used_car_erp/used_car_erp/workspace/accounting_operations/accounting_operations.json
git diff --check
```

## 6. Latest known commit before Step 8

```text
0a7677f feat: add accounting workspace shortcut to vehicle dashboard candidates
```

## 7. Recommended next phase

Do not continue expanding P1-UX-TAX-5.

The recommended next phase is a new, small UX-only phase:

```text
P1-UX-TAX-6：Used Car Vehicle form primary-action simplification
```

Suggested first step:

```text
P1-UX-TAX-6 Step 1：document current vehicle form actions and define one-primary-action boundary
```

Initial boundary:

```text
only inspect and document current buttons / dashboard actions
no runtime change
no DocType JSON change
no accounting service change
no tax service change
no write behavior
```

## 8. Handoff prompt for a new chat

Use this as the starting point in a new chat:

```text
We are working on ERPNext / Frappe app used_car_erp at ~/frappe/frappe-bench/apps/used_car_erp, site erpnext-coa.test, repo ericzhan0819/used_car_erp.

P1-UX-TAX-5 is closed. It added a read-only VehicleDashboardSummaryService aggregator, wired a minimal summary into Used Car Vehicle, cleaned duplicate dashboard comments, added /app/vehicle-dashboard-summary-candidates, and added a 會計作業 Workspace shortcut named 單車摘要候選. The user confirmed the shortcut opens normally.

Do not add accounting runtime, tax runtime, management profit runtime, formulas, write-back actions, create / submit / cancel buttons, or ERPNext document mutations under P1-UX-TAX-5.

Next recommended phase: P1-UX-TAX-6 Used Car Vehicle form primary-action simplification. Start with Step 1 documentation only: inspect current vehicle form actions and define the one-primary-action UX boundary. Do not change runtime, DocType JSON, services, hooks, or Workspace in Step 1.
```

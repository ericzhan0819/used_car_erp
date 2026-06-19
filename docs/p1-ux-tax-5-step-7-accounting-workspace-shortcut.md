# P1-UX-TAX-5 Step 7 Accounting Workspace Shortcut

Last reviewed: 2026-06-20

Phase: `P1-UX-TAX-5 Step 7`

## 1. Goal

Step 7 connects the Step 6 read-only vehicle dashboard summary candidate page into the `會計作業` Workspace.

The goal is only to give accounting users a visible Desk entry point instead of requiring manual navigation to:

```text
/app/vehicle-dashboard-summary-candidates
```

## 2. Modified file

```text
used_car_erp/used_car_erp/workspace/accounting_operations/accounting_operations.json
```

## 3. Added shortcut

Workspace section:

```text
會計作業
→ 會計待辦
→ 單車摘要候選
```

Shortcut metadata:

```json
{
  "label": "單車摘要候選",
  "link_to": "vehicle-dashboard-summary-candidates",
  "type": "Page"
}
```

The `content` layout also includes a matching shortcut block:

```text
uco_vehicle_dashboard_summary_candidates
```

## 4. Runtime boundary

Step 7 only changes version-controlled Workspace metadata.

It does not change:

```text
Python service
candidate page JS
Used Car Vehicle JS
DocType JSON
hooks.py
accounting runtime
tax runtime
management profit runtime
```

It does not add:

```text
create button
submit button
cancel button
write-back action
new formula
new candidate rule
```

## 5. Read-only guarantee

The shortcut only navigates to the already-existing Desk Page:

```text
vehicle-dashboard-summary-candidates
```

That page still only calls:

```text
used_car_erp.used_car_erp.services.vehicle_dashboard_summary_service.find_vehicle_dashboard_summary_candidates
```

The page remains read-only and still only allows route navigation to `Used Car Vehicle` or `Sales Invoice`.

Step 7 does not create, submit, cancel, delete, or modify any ERPNext business / accounting document.

## 6. Manual QA

After migrating / reloading the Workspace metadata, verify:

```text
Open 會計作業 Workspace
The 會計待辦 section contains 單車摘要候選
Clicking 單車摘要候選 opens /app/vehicle-dashboard-summary-candidates
Candidate page still renders candidates or empty state
Candidate page still has no create / submit / cancel / write action
```

Suggested local commands:

```bash
cd ~/frappe/frappe-bench/apps/used_car_erp

python -m json.tool used_car_erp/used_car_erp/workspace/accounting_operations/accounting_operations.json >/dev/null
git diff --check

cd ~/frappe/frappe-bench
bench --site erpnext-coa.test migrate
bench --site erpnext-coa.test clear-cache
bench --site erpnext-coa.test clear-website-cache
```

If the Workspace shortcut does not appear after migrate, reload the Workspace explicitly:

```bash
cd ~/frappe/frappe-bench
bench --site erpnext-coa.test reload-doc used_car_erp workspace accounting_operations
bench --site erpnext-coa.test clear-cache
```

## 7. Commit message

```text
feat: add accounting workspace shortcut to vehicle dashboard candidates
```

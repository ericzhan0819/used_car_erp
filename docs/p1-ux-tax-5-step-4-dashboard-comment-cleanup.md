# P1-UX-TAX-5 Step 4 Vehicle Dashboard Comment Cleanup

Last reviewed: 2026-06-20

Phase: `P1-UX-TAX-5 Step 4`

## 1. Scope

This step only cleans up duplicate `Used Car Vehicle` dashboard headline comments after Step 3 introduced the read-only `accounting_status_summary_html` aggregator summary.

Step 3 already renders the following minimal cards through `run_vehicle_dashboard_summary`:

```text
會計狀態
15-1 稅務估算
管理損益
```

Therefore Step 4 suppresses legacy dashboard headline comments that repeated the same information or exposed excessive engineering detail.

## 2. Implementation

New frontend hook:

```text
used_car_erp/public/js/used_car_vehicle_dashboard_comment_cleanup.js
```

Hook wiring:

```text
used_car_erp/hooks.py
```

The hook patches `frm.dashboard.add_comment` for `Used Car Vehicle` and suppresses duplicate dashboard headline comments with these prefixes:

```text
目前階段：
流程進度：
交車前最終檢查：
正式交車提交狀態
正式交車提交前檢查
成本摘要：
單車損益與預估營業稅：
```

It also clears the initial synchronous legacy dashboard headline for non-reserved saved vehicles because Step 3 summary HTML now owns the read-only numbers and next-step labels.

Reserved vehicle status comments are intentionally kept because they still use the active reservation payload and are not replaced by the Step 3 aggregator summary.

## 3. Boundary

This step does not:

```text
modify backend services
modify Workspace JSON
modify DocType JSON
add buttons
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
change the 15-1 calculation
change the management profit calculation
```

## 4. Expected UI Result

`Used Car Vehicle` should keep the Step 3 single-page minimal summary block as the main read-only entry point for:

```text
會計狀態
15-1 稅務估算
管理損益
warnings / blocking messages
```

Legacy large dashboard headline panels for cost summary, profit / VAT estimate, sold progress, final checklist, and formal delivery preflight are no longer auto-displayed over the vehicle page summary.

## 5. Verification

Suggested local verification:

```bash
node --check used_car_erp/public/js/used_car_vehicle_dashboard_comment_cleanup.js
python -m compileall used_car_erp/hooks.py
git diff --check
```

Browser smoke target:

```text
Open a saved non-reserved Used Car Vehicle.
Confirm the Step 3 單車摘要 block still renders.
Confirm duplicate dashboard headline comments are not displayed.
Open a reserved vehicle.
Confirm active reservation status headline is still allowed.
```

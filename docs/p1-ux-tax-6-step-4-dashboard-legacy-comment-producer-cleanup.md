# P1-UX-TAX-6 Step 4 Dashboard Legacy Comment Producer Cleanup

Last reviewed: 2026-06-20

Phase: `P1-UX-TAX-6`

Status: implemented, pending browser smoke / commit

## 1. Goal

Step 4 removes the remaining duplicate legacy dashboard comment producer calls from the `Used Car Vehicle` form refresh path.

Goal:

```text
Make the P1-UX-TAX-5 single vehicle summary HTML the primary read-only summary surface.
Stop rendering duplicate dashboard comments already covered by the summary cards.
Reduce redundant read-only API calls triggered only for legacy dashboard comments.
```

## 2. Changed file

```text
used_car_erp/used_car_erp/doctype/used_car_vehicle/used_car_vehicle.js
```

## 3. Runtime boundary

This step does not change:

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
```

This step does not add or remove any backend capability.

## 4. Calls removed from refresh path

Before Step 4, `apply_vehicle_form_mode` still called several legacy dashboard comment producers before rendering the summary HTML:

```text
add_sold_vehicle_progress_comment
add_sold_vehicle_final_check_comment
add_formal_delivery_submit_preflight_comment
add_vehicle_cost_summary_comment
```

Step 4 stops calling those functions from the normal form refresh path.

The functions are intentionally left in the file for now to keep the patch small and reduce removal risk. They are no longer part of the active refresh path.

## 5. Why these calls are obsolete

P1-UX-TAX-5 already introduced:

```text
VehicleDashboardSummaryService
accounting_status_summary_html summary cards
used_car_vehicle_dashboard_comment_cleanup.js duplicate suppression
```

The removed calls overlapped with the new summary cards:

```text
sold vehicle progress → 會計狀態摘要
sold vehicle final check → 會計狀態 / blocking messages
formal delivery submit preflight → 會計狀態 / blocking messages
cost summary → 管理損益摘要
profit / tax estimate → 15-1 稅務估算與管理損益摘要
```

Keeping both the calls and the cleanup hook created extra client-side work and duplicate responsibility.

## 6. Behavior after Step 4

The active summary flow is now:

```text
apply_vehicle_form_mode
→ render_accounting_status_summary
→ VehicleDashboardSummaryService
→ accounting / 15-1 tax / management profit cards
```

Reserved vehicle status still uses the active reservation path:

```text
load_active_reservation_for_reserved_vehicle
→ render_reserved_vehicle_status
```

This is intentionally preserved because reserved vehicle state depends on active reservation details and is not fully replaced by the P1-UX-TAX-5 summary card.

## 7. Cleanup hook status

`used_car_vehicle_dashboard_comment_cleanup.js` remains installed as a safety net, but it no longer clears already-rendered dashboard comments on refresh.

Reason:

```text
The old clear_initial_duplicate_dashboard_comment fallback caused a visible flash: legacy dashboard comments could render first, then disappear after frm.dashboard.clear_comment.
Step 4 removes the active legacy producer calls, so the fallback clear is no longer needed.
The hook now only patches dashboard.add_comment to suppress matching duplicate prefixes before they enter the dashboard.
```

A later final cleanup may remove the hook entirely only after browser smoke confirms no duplicate dashboard producer remains.

## 8. Suggested browser smoke

Check several vehicle states:

```text
庫存中
整備中
上架中
保留中
已售出, no Sales Invoice draft
已售出, Sales Invoice draft exists
已售出, Sales Invoice submitted
已售出, accounting closure complete
```

Expected:

```text
單車摘要 remains visible.
No duplicate dashboard cards for 成本摘要 / 流程進度 / 交車前最終檢查 / 正式交車提交前檢查.
No flash-then-disappear behavior from dashboard.clear_comment.
保留中 still shows active reservation status.
Primary action buttons from Step 2 / Step 3 still work visually.
```

## 9. Validation

Suggested checks:

```bash
node --check used_car_erp/used_car_erp/doctype/used_car_vehicle/used_car_vehicle.js
git diff --check
```

## 10. Suggested commit message

```text
polish: stop legacy vehicle dashboard comments
```

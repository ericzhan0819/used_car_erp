# P1-UX-TAX-5 Step 5 Accounting Workspace Candidate List Spec

Last reviewed: 2026-06-20

Phase: `P1-UX-TAX-5 Step 5`

## 1. Scope

This step defines the next minimal read-only wiring target for the Accounting Workspace side of P1-UX-TAX-5.

It is intentionally document-only. It does not change Workspace JSON, DocType JSON, backend runtime, frontend runtime, accounting behavior, tax formulas, or management profit formulas.

## 2. Current State

Step 2 already provides a read-only candidate aggregator:

```text
used_car_erp.used_car_erp.services.vehicle_dashboard_summary_service.find_vehicle_dashboard_summary_candidates
```

The existing Accounting Operations workspace is still a simple navigation workspace with shortcuts for:

```text
待審核傳票草稿
金流紀錄
傳票草稿
正式會計傳票
```

It does not yet show vehicle-level accounting / tax / management-profit candidate summaries.

## 3. Problem

After Step 3 and Step 4, `Used Car Vehicle` has a minimal summary block and duplicate dashboard comments are suppressed.

The remaining UX gap is the accounting-side entry point:

```text
會計作業 should help accounting users find vehicles needing review,
without forcing them to open each vehicle or read technical document links first.
```

## 4. Proposed Minimal Next Wiring

The next implementation step should add a small read-only consumer for:

```text
find_vehicle_dashboard_summary_candidates(limit=10)
```

The consumer should display a compact candidate list with these columns only:

```text
車輛
銷售發票
來源
會計狀態
15-1 稅務估算狀態
管理損益狀態
```

Optional row action:

```text
Open Used Car Vehicle
```

No mutation action should appear in this list.

## 5. Recommended Implementation Shape

Prefer a small custom page or lightweight client-side desk entry over modifying the existing Workspace JSON first.

Reason:

```text
Workspace JSON is currently stable and only contains navigation shortcuts.
A separate read-only page lets us test the candidate payload without disrupting existing accounting navigation.
```

Suggested future file shape:

```text
used_car_erp/used_car_erp/page/vehicle_dashboard_summary_candidates/vehicle_dashboard_summary_candidates.json
used_car_erp/used_car_erp/page/vehicle_dashboard_summary_candidates/vehicle_dashboard_summary_candidates.js
```

The page should:

```text
call find_vehicle_dashboard_summary_candidates(limit=10)
render rows read-only
show source_statuses / warnings / blocking_errors
open vehicle links only
not create or submit any document
```

Only after the page is verified should a later step add a Workspace shortcut.

## 6. Candidate Row Semantics

The Step 2 candidate payload currently merges candidate rows from three services:

```text
accounting_status
tax_estimate
management_profit
```

A row may come from one source or multiple sources. The UI should show the source badges and avoid implying that all three services flagged the same vehicle.

Recommended source labels:

```text
會計
稅務
損益
```

If `vehicle` is missing but `sales_invoice` exists, the row should still be shown as a Sales Invoice candidate and avoid a broken vehicle route.

## 7. Read-only Boundary

This step and the next candidate-list implementation must not:

```text
modify backend service formulas
modify Workspace JSON in Step 5
modify DocType JSON
add accounting runtime
add tax runtime
add management profit runtime
create ERPNext documents
submit ERPNext documents
cancel ERPNext documents
write back Used Car Vehicle
write back Sales Invoice
write back Journal Entry
write back GL Entry
write back Stock Ledger Entry
add mutation buttons
```

## 8. Acceptance Criteria For The Future Implementation Step

A later implementation step may be considered complete when:

```text
A read-only candidate list can be opened from Desk or a direct route.
The page calls find_vehicle_dashboard_summary_candidates only.
Rows show vehicle / sales invoice / source badges / three statuses.
Clicking a vehicle only navigates to Used Car Vehicle.
No create / submit / cancel / write action exists.
Existing Accounting Operations workspace shortcuts remain unchanged.
```

## 9. Suggested Commit Message For Future Implementation

```text
feat: add read-only vehicle dashboard candidate page
```

# P1-UX-TAX-6 Step 3 Sold Vehicle Secondary Action Grouping

Last reviewed: 2026-06-20

Phase: `P1-UX-TAX-6`

Status: implemented, pending browser smoke / commit

## 1. Goal

Step 3 applies a small JS-only cleanup to the `已售出` vehicle page.

Goal:

```text
Keep the sold-vehicle lifecycle action as the only top-level primary action.
Move document navigation, technical field toggle, and recovery actions into secondary button groups.
```

This preserves existing behavior while reducing the visual competition around the main next step.

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

This step does not add any new create / submit / cancel backend capability.

## 4. Preserved sold vehicle primary action flow

The existing sold vehicle primary action selector remains the source of truth:

```text
get_sold_vehicle_primary_next_action
```

The main sold-vehicle sequence is preserved:

```text
No Sales Invoice draft → 建立 Sales Invoice 草稿
Sales Invoice draft exists → 確認銷售發票並出庫
Sales Invoice submitted, no settlement draft → 建立預收款沖轉草稿
Settlement draft exists → 確認預收款沖轉入帳
Accounting closure complete → no primary action
```

## 5. Secondary actions moved into groups

### 5.1 Technical field toggle

Before Step 3, the document-link toggle was added as a normal top-level button:

```text
顯示文件連結
隱藏文件連結
```

After Step 3, it is grouped under:

```text
更多資訊
```

### 5.2 Document navigation

Before Step 3, document navigation was added as normal top-level buttons:

```text
查看銷售發票
查看預收款沖轉傳票
```

After Step 3, these are grouped under:

```text
文件連結
```

### 5.3 Recovery action

Before Step 3, recovery could appear as a normal top-level button when the narrow recovery condition was met:

```text
修復銷售發票草稿連結
```

After Step 3, it is grouped under:

```text
技術維護
```

The recovery gate remains unchanged. The button still appears only after the existing read-only recovery state check says it can recover.

## 6. Why this step is intentionally small

This step does not remove the sold-vehicle document buttons and does not migrate accounting actions to the Accounting Operations Workspace yet.

Reason:

```text
The current sold-vehicle accounting sequence is still handled from the vehicle page.
Step 3 only reduces visual competition.
A later documentation-first step should decide whether high-impact accounting actions should move to Accounting Operations.
```

## 7. Suggested browser smoke

Check an `已售出` vehicle in these states:

```text
No Sales Invoice draft
Sales Invoice draft exists
Sales Invoice submitted
Advance settlement draft exists
Accounting closure complete
```

Expected:

```text
Only the current lifecycle action appears as the main top-level primary action.
顯示 / 隱藏文件連結 appears under 更多資訊.
查看銷售發票 / 查看預收款沖轉傳票 appear under 文件連結 when linked documents exist.
修復銷售發票草稿連結 appears under 技術維護 only when the existing recovery gate allows it.
```

## 8. Validation

Suggested checks:

```bash
node --check used_car_erp/used_car_erp/doctype/used_car_vehicle/used_car_vehicle.js
git diff --check
```

## 9. Suggested commit message

```text
polish: group sold vehicle secondary actions
```

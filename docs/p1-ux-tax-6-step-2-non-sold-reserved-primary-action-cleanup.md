# P1-UX-TAX-6 Step 2 Non-sold / Reserved Primary Action Cleanup

Last reviewed: 2026-06-20

Phase: `P1-UX-TAX-6`

Status: implemented, pending browser smoke / commit

## 1. Goal

Step 2 applies the smallest JS-only cleanup from the Step 1 boundary:

```text
Stop showing multiple lifecycle buttons at the same time on non-sold / reserved vehicle states.
```

This step does not change backend behavior. It only changes which existing front-end buttons are surfaced from `Used Car Vehicle` form refresh logic.

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
```

This step does not add any new create / submit / cancel backend capability.

Existing backend methods remain unchanged. Removed top-level buttons only stop exposing those actions from this form refresh path.

## 4. Reserved vehicle cleanup

Before Step 2, when an active reservation was ready for sale completion, the reserved vehicle branch could add both:

```text
成交前檢查
確認成交
```

Step 2 changes the priority so that ready reservations expose only:

```text
確認成交
```

`成交前檢查` is no longer shown together with `確認成交` in that ready state. The check remains conceptually covered by backend gate / confirmation flow and read-only status messaging.

## 5. Non-sold vehicle cleanup

Before Step 2, normal non-sold vehicles could show multiple top-level lifecycle or utility buttons, including:

```text
完成入庫
開始整備
直接上架
整備完成並上架
下架回庫存
新增單車成本
重新計算成本摘要
重新整理損益與稅務估算
```

Step 2 replaces the scattered calls with one front-end selector:

```text
add_non_sold_vehicle_primary_action_button
```

The selector exposes at most one primary action for the current non-sold state.

## 6. Current primary action matrix after Step 2

| Vehicle state / condition | Top-level primary action after Step 2 |
| --- | --- |
| New document | none |
| Not stocked and existing document | 完成入庫, only when existing complete_intake guard allows it |
| 庫存中 and stocked | 開始整備 |
| 整備中 and stocked | 整備完成並上架 |
| 上架中 and stocked | 建立訂金保留 |
| 保留中, final payment missing | 建立尾款收款 |
| 保留中, waiting for accounting | none |
| 保留中, ready for sale completion | 確認成交 |
| 封存 | none |

## 7. Buttons intentionally no longer shown from this path

The following are no longer added from the normal non-sold vehicle refresh path:

```text
直接上架
下架回庫存
新增單車成本
重新計算成本摘要
重新整理損益與稅務估算
```

Rationale:

```text
直接上架 and 下架回庫存 are secondary listing operations.
新增單車成本 belongs to the future 收支 / cost workflow, not the primary vehicle lifecycle button row.
重新計算成本摘要 and 重新整理損益與稅務估算 are no longer primary after P1-UX-TAX-5 read-only summary aggregation.
```

## 8. Preserved behavior

This step keeps the existing mutation implementations and gates intact:

```text
complete_intake
start_preparation
list_vehicle
create_reservation
create_final_payment_for_active_reservation
complete_active_reservation
```

It only changes which one is exposed as the form's current main next step.

## 9. Validation

Suggested checks:

```bash
node --check used_car_erp/used_car_erp/doctype/used_car_vehicle/used_car_vehicle.js
git diff --check
```

Suggested browser smoke:

```text
草稿 / 未入庫車：只看到「完成入庫」或無主動作
庫存中車：只看到「開始整備」，不看到「直接上架」
整備中車：只看到「整備完成並上架」
上架中車：只看到「建立訂金保留」，不看到「下架回庫存」
保留中 ready 車：只看到「確認成交」，不看到「成交前檢查」
已售出車：不在本步驟範圍，應維持 Step 1 前既有 sold-vehicle primary action behavior
```

## 10. Suggested commit message

```text
fix: simplify vehicle primary actions for non-sold states
```

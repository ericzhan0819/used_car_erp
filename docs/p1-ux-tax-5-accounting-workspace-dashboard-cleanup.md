# P1-UX-TAX-5 Accounting Workspace Dashboard Cleanup

Last reviewed: 2026-06-20

Phase: `P1-UX-TAX-5`

## 1. 任務背景

P1-UX-TAX-2 已提供車輛頁可用的 read-only accounting status summary，將正式售車會計流程濃縮成單一業務狀態、單一下一步與摘要卡片。

P1-UX-TAX-3 已提供 15-1 read-only estimate，以 `purchase_price` 與 `sold_price` / linked Sales Invoice `grand_total` 估算售車營業稅。

P1-UX-TAX-4 已提供 management profit read-only summary，以成交價、購車價、直接成本與其他直接收入計算單車管理毛利。

目前缺口已不在新的計算 service，而是在如何把上述 read-only summary 收斂成車輛頁與會計作業可直接使用的精簡入口，避免業務頁再次暴露過多會計 / ledger 技術細節。

## 2. 本階段目標

本階段先定義 Accounting Workspace / Vehicle page dashboard cleanup 邊界：

```text
只整理既有 read-only summary 的消費方式
不新增新的 accounting runtime
不新增新的 tax runtime
不新增新的 management profit runtime
```

重點是把既有三份 summary：

```text
Vehicle Accounting Status Summary Inspector
Vehicle 15-1 Tax Estimate Read-only Service
Vehicle Management Profit Summary Read-only Service
```

整理成後續最小 implementation 可接線的單一 UX 邊界。

## 3. UX 邊界

後續畫面應遵守：

```text
車輛頁只看精簡摘要
會計作業頁只看待處理候選與摘要
會計文件技術細節不回到車輛主畫面攤開
同一時間只顯示最小必要資訊與單一下一步
```

車輛頁預期只保留：

```text
會計狀態摘要
15-1 稅務估算摘要
管理損益摘要
必要 warning / blocking message
```

會計作業頁預期只保留：

```text
待會計確認候選
需補資料候選
可檢視 15-1 估算候選
可檢視管理損益候選
```

## 4. Read-only Boundary

本階段仍嚴格 read-only。

本階段不建立、不提交、不取消、不刪除、不修改任何文件，不寫回 `Used Car Vehicle`、`Sales Invoice`、`Journal Entry`、`GL Entry`、`Stock Ledger Entry`、`Reservation`、`Money Flow`、`Voucher Draft` 或 Workspace JSON。

後續若需要 aggregator payload，也只允許 read-only 包裝既有 summary service 輸出，不可加入新的寫入行為。

## 5. Non-goals

本階段不做：

```text
不做 JS implementation
不做 Workspace JSON
不做 DocType JSON
不做新按鈕
不做新的 write behavior
不做新的 accounting runtime
不做新的 tax formula
不做新的 management profit formula
不建立或提交任何 ERPNext 文件
```

## 6. Step 2 Implementation

Step 2 已新增 `VehicleDashboardSummaryService`，只做 read-only aggregation，不新增公式、不改寫既有三份 summary 的邏輯。

新增 service：

```text
used_car_erp/used_car_erp/services/vehicle_dashboard_summary_service.py
```

此 service 只呼叫並包裝：

```text
VehicleAccountingStatusSummaryService
Vehicle151TaxEstimateService
VehicleManagementProfitSummaryService
```

單車 payload 保留三份原始 summary：

```text
accounting_status_summary
tax_estimate_summary
management_profit_summary
```

並額外整理一層薄的消費 payload：

```text
vehicle_page_summary
summary_cards
service_statuses
```

若個別 summary 失敗，aggregator 不丟棄其他 summary；失敗內容會保留在對應 summary key，並於 `service_statuses` 標示個別狀態。

候選清單也只做 read-only merge：

```text
find_vehicle_dashboard_summary_candidates
```

只合併三個既有 candidate finder 的輸出來源，不新增新的候選規則。

Step 2 仍不做：

```text
不改 JS
不改 Workspace JSON
不改 DocType JSON
不新增按鈕
不建立 / 提交 / 取消任何 ERPNext 文件
不呼叫 insert / save / submit / cancel / db_set / delete_doc / raw SQL
```

## 7. 後續最小 implementation 建議

後續 implementation 應繼續切小步：

```text
Step 1：文件同步（已完成）
Step 2：read-only aggregator service，只包裝既有三份 summary（已完成）
Step 3：只在單一頁面接入最小摘要顯示，不做整頁重排
```

## 8. 驗收標準

本階段完成後，repo 內應明確記錄：

```text
P1-UX-TAX-5 的 scope
P1-UX-TAX-5 沒有 write behavior
P1-UX-TAX-5 只消費既有 read-only summary
下一步 implementation 應維持最小變更面
```

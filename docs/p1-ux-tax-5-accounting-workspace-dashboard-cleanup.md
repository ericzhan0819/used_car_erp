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

本階段不建立、不提交、不取消、不刪除、不修改任何 ERPNext 業務 / 會計文件，不寫回 `Used Car Vehicle`、`Sales Invoice`、`Journal Entry`、`GL Entry`、`Stock Ledger Entry`、`Reservation`、`Money Flow` 或 `Voucher Draft`。

唯一允許的 Workspace 變更是 Step 7 以 version-controlled Workspace JSON 新增 read-only Page shortcut；不得加入任何 write button、mutation action 或 runtime。

後續若需要 aggregator payload，也只允許 read-only 包裝既有 summary service 輸出，不可加入新的寫入行為。

## 5. Non-goals

本階段不做：

```text
不做新的 write behavior
不做新的 accounting runtime
不做新的 tax formula
不做新的 management profit formula
不建立或提交任何 ERPNext 文件
```

具體 implementation step 的非目標以各 step 文件為準；若該 step 只做文件或只做前端接線，仍不得突破本階段 read-only boundary。

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

## 7. Step 3 Implementation

Step 3 已在 `Used Car Vehicle` 單一頁面接入最小摘要顯示。

修改檔案：

```text
used_car_erp/used_car_erp/doctype/used_car_vehicle/used_car_vehicle.js
```

接線方式：

```text
既有 accounting_status_summary_html HTML 欄位
→ frappe.call(run_vehicle_dashboard_summary)
→ 顯示會計狀態、15-1 稅務估算、管理損益三張摘要卡
→ 顯示 service_statuses 與 aggregator 整體狀態
```

Step 3 只改既有 HTML 摘要區的消費來源，不新增按鈕、不新增 DocType 欄位、不改 Workspace JSON、不改 DocType JSON、不做整頁重排。

此 UI 區塊仍維持 read-only：

```text
不建立 ERPNext 文件
不提交 ERPNext 文件
不取消 ERPNext 文件
不寫回 Used Car Vehicle / Sales Invoice / Journal Entry / GL Entry / Stock Ledger Entry
不新增 accounting runtime
不新增 tax runtime
不新增 management profit runtime
```

若 aggregator 載入失敗，車輛頁只顯示唯讀錯誤提示，不阻斷既有車輛主流程操作。

## 8. Step 4 Implementation

Step 4 已新增車輛頁 duplicate dashboard comment cleanup，讓 Step 3 的單車摘要成為主要 read-only summary 入口。

新增檔案：

```text
used_car_erp/public/js/used_car_vehicle_dashboard_comment_cleanup.js
```

接線檔案：

```text
used_car_erp/hooks.py
```

此 cleanup hook 只抑制與 Step 3 summary 重複的 dashboard headline comments，例如：

```text
目前階段
流程進度
交車前最終檢查
正式交車提交前檢查
成本摘要
單車損益與預估營業稅
```

Step 4 不改 backend service、不改 Workspace JSON、不改 DocType JSON、不新增按鈕、不新增公式、不新增 runtime。

詳細文件：

```text
docs/p1-ux-tax-5-step-4-dashboard-comment-cleanup.md
```

## 9. Step 5 Candidate List Boundary

Step 5 已新增 Accounting Workspace candidate list 規格文件，定義下一個最小 read-only 會計作業入口。

新增文件：

```text
docs/p1-ux-tax-5-step-5-accounting-workspace-candidate-list-spec.md
```

Step 5 結論：下一步不應直接修改既有 `會計作業` Workspace JSON。應先新增一個獨立 read-only page 或等效輕量入口，消費：

```text
find_vehicle_dashboard_summary_candidates(limit=10)
```

候選清單只顯示：

```text
車輛
銷售發票
來源
會計狀態
15-1 稅務估算狀態
管理損益狀態
```

唯一允許的 row action 是開啟 `Used Car Vehicle` 或相關只讀來源，不得新增 create / submit / cancel / write action。

## 10. Step 6 Implementation

Step 6 已新增一個獨立 read-only Desk Page，用來檢視 vehicle dashboard summary candidates。

新增檔案：

```text
used_car_erp/used_car_erp/page/vehicle_dashboard_summary_candidates/vehicle_dashboard_summary_candidates.json
used_car_erp/used_car_erp/page/vehicle_dashboard_summary_candidates/vehicle_dashboard_summary_candidates.js
```

頁面名稱：

```text
單車摘要候選
```

此頁只呼叫：

```text
find_vehicle_dashboard_summary_candidates(limit=10)
```

顯示欄位：

```text
車輛
銷售發票
來源
會計狀態
15-1 稅務估算狀態
管理損益狀態
動作
```

允許的動作只有 route navigation：有 vehicle 時開啟 `Used Car Vehicle`，沒有 vehicle 但有 sales_invoice 時開啟 `Sales Invoice`。

Step 6 不改 Workspace JSON、不改 backend service、不改 DocType JSON、不新增 mutation button、不新增公式、不建立、不提交、不取消、不寫回任何文件。

詳細文件：

```text
docs/p1-ux-tax-5-step-6-read-only-candidate-page.md
```

## 11. Step 7 Implementation

Step 7 已在 `會計作業` Workspace 新增一個 read-only Page shortcut，指向 Step 6 的 candidate page。

修改檔案：

```text
used_car_erp/used_car_erp/workspace/accounting_operations/accounting_operations.json
```

新增入口：

```text
會計作業
→ 會計待辦
→ 單車摘要候選
```

Shortcut 指向：

```text
vehicle-dashboard-summary-candidates
```

此步只變更 version-controlled Workspace metadata，不改 candidate page runtime、不改 aggregator service、不改 DocType JSON、不改 Used Car Vehicle JS、不新增任何寫入行為。

詳細文件：

```text
docs/p1-ux-tax-5-step-7-accounting-workspace-shortcut.md
```

## 12. 後續最小 implementation 建議

後續 implementation 應繼續切小步：

```text
Step 1：文件同步（已完成）
Step 2：read-only aggregator service，只包裝既有三份 summary（已完成）
Step 3：只在單一頁面接入最小摘要顯示，不做整頁重排（已完成）
Step 4：只移除或收斂重複 dashboard comments，不新增新的 runtime（已完成）
Step 5：定義 Accounting Workspace candidate list read-only boundary（已完成）
Step 6：新增 read-only candidate page，只呼叫 find_vehicle_dashboard_summary_candidates，不改 Workspace JSON（已完成）
Step 7：新增會計作業 Workspace shortcut 指向 read-only candidate page（已完成）
```

## 12. 驗收標準

本階段完成後，repo 內應明確記錄：

```text
P1-UX-TAX-5 的 scope
P1-UX-TAX-5 沒有 write behavior
P1-UX-TAX-5 只消費既有 read-only summary
下一步 implementation 應維持最小變更面
```

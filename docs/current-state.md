# Used Car ERP Current State

## 1. 專案定位

本 app 是 ERPNext custom app：`used_car_erp`。

目標是建立中古車買賣用的內部 ERP 工作流，不修改 ERPNext / Frappe core。

`used_car_erp` 自訂 app 只負責中古車業務主檔、工作流 service、表單操作入口。ERPNext 原生 `Item` / `Serial No` / `Stock Entry` / `Warehouse` / `Account` 負責庫存與會計底層。

## 2. 目前穩定流程

目前已打通的基礎流程：

```text
Used Car Vehicle
  -> create ERPNext Item
  -> select stock warehouse
  -> stock in vehicle
  -> submit Stock Entry
  -> create/link Serial No
  -> write back stock_entry / serial_no
  -> status = 庫存中
```

流程涵蓋：`Used Car Vehicle` → ERPNext `Item` → `Stock Entry` 正式入庫 → `Serial No` / VIN → 車輛狀態變成「庫存中」。

Vehicle Intake Foundation Stable：

```text
草稿
→ 完成入庫
→ 庫存中
```

Vehicle Preparation / Listing Foundation：

```text
庫存中
→ 整備中
→ 上架中
→ 下架回庫存中
```

整備 / 上架 / 下架回庫存都只改 `Used Car Vehicle.status`。
不產生 ERPNext `Stock Entry`。
不產生 `Sales Invoice` / `Payment Entry` / `Delivery Note` / `Journal Entry`。

Vehicle Reservation Foundation：

```text
上架中
→ 建立訂金保留
→ 建立金流紀錄
→ 建立傳票草稿
→ 保留中
→ 會計確認入帳
→ 建立正式會計傳票
→ 取消保留
→ 上架中
```

訂金保留會建立 `Used Car Reservation`。
訂金保留可以建立 / 連結 ERPNext `Customer`。
訂金保留會建立 `Used Car Money Flow`。
訂金保留會建立 `Used Car Voucher Draft`。
車輛會從「上架中」改為「保留中」。
取消保留會讓車輛回到「上架中」。
訂金金流會先產生傳票草稿。
傳票草稿必須由會計人工確認。
確認前不會正式入帳。
確認後才建立正式 `Journal Entry`。
訂金先視為預收款 / 暫收款，不直接認列賣車收入。
訂金金額不是 `Payment Entry`。
不建立 `Sales Invoice`。
不建立 `Delivery Note`。
不出庫。
不認列收入。

## 3. 已完成模組

### Used Car Vehicle DocType

* 中古車主檔。
* `stock_no` / 車輛編號由系統自動產生。
* `stock_no` 不允許手動修改。
* `status` 目前包含：草稿、庫存中、整備中、上架中、保留中、已售出、封存。
* 包含車輛規格、採購資料、稅務與證件、ERPNext 連結等 tab。

### Vehicle Form UX

* 已存在車輛預設檢視模式。
* 按「編輯資料」才進入可編輯狀態。
* 系統欄位保持唯讀。
* 表單 JS 只呼叫 whitelisted service，不承擔跨 DocType 業務邏輯。
* 一般 UI 以「完成入庫」作為主要 action，不要求使用者分別操作 ERPNext `Item` / `Stock Entry`。

### Vehicle Item Service Foundation

* 檔案：`used_car_erp/used_car_erp/services/vehicle_item_service.py`
* 負責 `Used Car Vehicle` → ERPNext `Item` 建立 / 綁定。
* `Item Code` 使用 `vehicle.stock_no`。
* `Item Name` 由廠牌、車型、年式、車牌組合。
* 不建立 `Stock Entry`。
* 不建立 `Serial No` document。
* 不建立 `Purchase Invoice` / `Sales Invoice` / `Payment Entry`。
* 驗證已通過。

### Vehicle Stock In Service Foundation

* 檔案：`used_car_erp/used_car_erp/services/vehicle_stock_service.py`
* 負責正式入庫。
* 需要 `vehicle.item`。
* 需要 VIN / 車身號碼。
* 需要 `stock_warehouse`。
* 需要 `purchase_price > 0`。
* 使用 `Material Receipt Stock Entry`。
* `Stock Entry Detail`：
* `item_code = vehicle.item`
* `qty = 1`
* `t_warehouse = vehicle.stock_warehouse`
* `basic_rate = vehicle.purchase_price`
* `serial_no = vehicle.vin`
* 若 ERPNext `Stock Entry Detail` 有 `expense_account` 欄位，會寫入已驗證的 Stock Entry Difference Account。
* Difference Account 優先使用 `Company.stock_adjustment_account`；若公司欄位缺失或未設定，使用既有 `0100005-UC - 中古車銷貨成本 - O` 作為 fallback。
* Difference Account 必須存在、同公司、非群組、未停用且 `root_type = Expense`；runtime 不建立 Account、不改 COA。
* `submit` 成功後回寫：
* `serial_no`
* `stock_entry`
* `status = 庫存中`
* 不建立 `Purchase Invoice` / `Sales Invoice` / `Payment Entry`。
* `bench execute` 驗證已通過。
* 瀏覽器手動驗證已通過。

### Vehicle Intake Service UX Orchestration

* 檔案：`used_car_erp/used_car_erp/services/vehicle_intake_service.py`
* 負責一鍵編排 `Used Car Vehicle` 入庫流程。
* 呼叫 `VehicleItemService` 建立 / 綁定 ERPNext `Item`。
* 缺少 `stock_warehouse` 時，自動套用已綁定庫存科目的預設 Warehouse。
* 呼叫 `VehicleStockService` 建立 / 提交 `Stock Entry` 並建立 / 綁定 `Serial No`。
* 不重寫 `VehicleItemService` / `VehicleStockService` 底層驗證。
* 不建立 `Purchase Invoice` / `Sales Invoice` / `Payment Entry`。

### Vehicle Preparation / Listing Service Foundation

* 檔案：`used_car_erp/used_car_erp/services/vehicle_listing_service.py`
* 負責入庫後、銷售前的業務狀態轉換。
* 允許 `庫存中` → `整備中`。
* 允許 `庫存中` → `上架中`。
* 允許 `整備中` → `上架中`。
* 允許 `上架中` → `庫存中`。
* 只更新 `Used Car Vehicle.status`。
* 不建立 `Stock Entry` / `Sales Invoice` / `Payment Entry` / `Delivery Note` / `Journal Entry`。
* 不修改 `Item` / `Serial No` / `Stock Ledger`。

### Vehicle Reservation Service Foundation

* 檔案：`used_car_erp/used_car_erp/services/vehicle_reservation_service.py`
* 負責上架車輛的訂金保留業務流程。
* 允許 `上架中` → `保留中`。
* 允許取消保留時 `保留中` → `上架中`。
* 建立 `Used Car Reservation`。
* 可建立 / 連結 ERPNext `Customer`。
* 建立 `Used Car Money Flow` 記錄訂金收款。
* 建立 `Used Car Voucher Draft` 作為會計草稿。
* 業務建立訂金時不建立正式 `Journal Entry`。
* 不建立 `Sales Invoice` / `Payment Entry` / `Delivery Note`。
* 不建立新的 `Stock Entry`。
* 不出庫、不認列收入。

### Vehicle Money Flow Service Foundation

* 檔案：`used_car_erp/used_car_erp/services/vehicle_money_flow_service.py`
* 負責從有效訂金保留建立 `Used Car Money Flow`。
* 本次只支援 `flow_type = 訂金收款`。
* 建立後呼叫 voucher service 產生傳票草稿。
* 不建立 `Payment Entry` / `Sales Invoice` / `Delivery Note` / `Stock Entry`。
* 不建立正式 `Journal Entry`。
* 不修改 `Stock Ledger` / `Serial No` / 車輛狀態。

### Vehicle Voucher Draft Service Foundation

* 檔案：`used_car_erp/used_car_erp/services/vehicle_voucher_service.py`
* 負責根據金流紀錄建立 `Used Car Voucher Draft`。
* 訂金草稿分錄：借方為銀行 / 現金科目，貸方為預收款 / 暫收款或負債科目。
* 草稿借貸必須平衡。
* 只有會計在傳票草稿按「確認入帳」後，才建立並提交 ERPNext `Journal Entry`。
* 可退回草稿。
* 可作廢尚未入帳草稿。
* 已入帳草稿不可直接作廢；反向傳票本次不做。

### Workspace / List View

* Workspace「中古車管理」作為導航入口。
* List View 只負責列表顯示與狀態辨識。
* 不做資料寫入。

## 4. ERPNext 基礎設定

目前已設定：

* Warehouse：`商店 - O`。
* 新增 / 使用庫存資產科目：`1211 - 中古車庫存 - O`。
* `1211 - 中古車庫存 - O`：
* `account_type = Stock`
* `root_type = Asset`
* `parent_account = 121~122 - 存貨 - O`
* Warehouse `商店 - O` 已綁定 account：`1211 - 中古車庫存 - O`。

原因：ERPNext `Stock Entry submit` 需要 Warehouse Account 或 Company Default Inventory Account。沒有設定時，`Stock Entry` 會出現：

```text
Please set Account in Warehouse 商店 - O or Default Inventory Account in Company OO
```

## 5. 已清理的測試事故

本次測試中曾發生：

* 遺留 `Stock Entry`：`MAT-STE-2026-00001`。
* 原因：ERPNext 庫存帳戶設定缺漏，導致測試入庫流程中斷。
* 修復方式：
* 建立 / 綁定庫存科目。
* 補回缺失的測試 `Item`。
* 以 ERPNext 允許的方式補回 `Serial No`。
* 使用標準 cancel 流程取消 `Stock Entry`。
* 最終狀態：
* `MAT-STE-2026-00001 docstatus = 2`。
* `Stock Ledger` 已有反向沖銷。
* `qty_after_transaction` 回到 0。
* 沒有殘留庫存數量。

此段是本機測試資料修復紀錄，不代表正式業務流程。

## 6. 目前不要做的事

暫時不要做：

* 不做尾款。
* 不做銷售 / 出庫。
* 不做出售 / 已售出。
* 不做尾款、貸款撥款、退款。
* 不做 `Sales Invoice`。
* 不做 `Purchase Invoice`。
* 不做 `Payment Entry`。
* 不做業務端自動正式入帳。
* 不做自動確認入帳。
* 不做成本分攤。
* 不做毛利計算。
* 不做報表。
* 不做圖片上傳。
* 不做租賃模組。
* 不做完整權限系統。
* 不做 UI 大重構，直到工作流方向討論清楚。

## 7. 目前已知問題：操作流程太麻煩

已識別問題：舊流程需要多次操作，使用者必須分別建立 ERPNext 商品、選擇入庫倉庫、再正式入庫。

本次已新增 `VehicleIntakeService` 與「完成入庫」按鈕，將 ERPNext 底層入庫細節收斂到同一個 service 入口。

新流程目標：

1. 新增車輛。
2. 填 VIN / 採購車價。
3. 儲存。
4. 按「完成入庫」。

ERPNext `Item` / `Serial No` / `Stock Entry` 由系統背後處理。

## 8. 下一步候選方向

以下為候選方向，不在本文件直接決定。

### A. 操作流程簡化

目標：

* 減少建立車輛到正式入庫的點擊數。
* 將 ERPNext 底層 `Item` / `Stock Entry` 複雜度隱藏在 service 後面。
* 讓員工只理解「建立車輛」與「正式入庫」。

### B. Vehicle Intake Workflow

可能建立一個更清楚的入庫流程：

```text
草稿
→ 建立商品
→ 待入庫
→ 庫存中
```

### C. UI Polish

改善：

* 主要 action 位置。
* 狀態提示。
* 下一步提示。
* 已完成 / 未完成 checklist。
* 不同 status 顯示不同操作。

### D. Sales / Reservation 暫緩

等入庫操作簡化後，再做：

* 尾款。
* 已售出。
* 出庫。
* `Sales Invoice`。
* `Payment Entry`。
* `Journal Entry`。
* 會計分錄。
* 報表。

## 9. P1-ACC-6E Minimal Accounting / Stock Setup QA

P1-ACC-6E 新增獨立 QA service，針對 `erpnext-coa.test` / `OO` 檢查最小會計與庫存 master data，並只建立 Draft Sales Invoice 作為驗證。此階段不 submit、不建立 Payment Entry / Journal Entry / Delivery Note / Stock Entry、不產生 GL Entry 或 Stock Ledger Entry、不修改 COA。

文件：`docs/p1-acc-6e-minimal-accounting-stock-setup-qa.md`。

## 10. P1-ACC-6F-A Submitted Sales Invoice Preflight Only

P1-ACC-6F-A 新增獨立只讀 preflight service，檢查既有 Draft Sales Invoice 是否具備未來 submitted Sales Invoice / update_stock 的前置條件。此階段只回傳 `ready_to_submit`、`blocking_errors`、`warnings` 與 baseline counts；不 submit、不建立 GL Entry、不建立 Stock Ledger Entry、不補 serial_no、不修改正式車輛流程。

文件：`docs/p1-acc-6f-a-submitted-sales-invoice-preflight.md`。

## 11. P1-TAX-1-A / P1-ACC-6F-B Sales Invoice Tax Template Runtime

正式 Used Car Vehicle flow 的 `create_sales_invoice_draft_for_vehicle()` 會在建立 Draft Sales Invoice 時固定套用 `台灣營業稅 5%（含稅） - O`，並複製一筆 `0202134 - 銷項稅額 - O`、`rate = 5`、`included_in_print_rate = 1` 的 tax row。此階段只修 Sales Invoice 草稿稅務 payload；不 submit、不建立 GL Entry、不建立 Stock Ledger Entry、不建立 Payment Entry、不建立 Journal Entry、不建立 Delivery Note / Stock Entry、不修改 COA。15-1 仍只作內部扣抵估算，不寫入 Sales Invoice taxes table。

文件：`docs/p1-tax-1-a-sales-invoice-tax-template-runtime.md`。

## 12. P1-ACC-6F-B-1 Formal Vehicle Sales Invoice Preflight Target

P1-ACC-6F-B-1 新增正式 Used Car Vehicle flow 的 Draft Sales Invoice 只讀 preflight target。新的 runner 只從 `Used Car Vehicle.sales_invoice` 反查 `OO` 的 Draft Sales Invoice，排除 P1-ACC-6E QA draft remarks，找到後沿用既有 `SubmittedSalesInvoicePreflightService().run(sales_invoice=...)` 檢查。沒有 formal draft 時回傳 fail / not found，這是 P1-ACC-6F-C 前的安全 blocked 狀態；本階段不建立資料、不修資料、不 submit、不建立 GL Entry / Stock Ledger Entry。

文件：`docs/p1-acc-6f-b-1-formal-vehicle-sales-invoice-preflight-target.md`。

## 13. P1-ACC-6F-B-2 Formal Sales Invoice Draft Readiness Inspector

P1-ACC-6F-B-2 新增正式 Sales Invoice 草稿建立前只讀 readiness inspector。新的 service 只檢查已售出車輛是否具備呼叫 `create_sales_invoice_draft_for_vehicle()` 的資料條件，包含已完成保留單、Customer、Item、Serial No、Warehouse、訂金 / 尾款金流與傳票、收入科目、Sales Tax Template 與買入憑證稅務判斷。本階段不呼叫會 backfill / commit 的 formal delivery preflight，不建立 Sales Invoice 草稿、不 submit、不回填、不修改任何文件，只用來在 P1-ACC-6F-C 前找出資料缺口。

文件：`docs/p1-acc-6f-b-2-formal-sales-invoice-draft-readiness-inspector.md`。

## 14. 驗證指令

## 14. P1-ACC-6F-B-3 Guarded Formal Sales Invoice Draft Creation QA

P1-ACC-6F-B-3 新增受 readiness gate 保護的正式 Draft Sales Invoice 建立 QA runner。只有 readiness pass 時才允許呼叫 `create_sales_invoice_draft_for_vehicle()` 建立草稿；建立後立即檢查 Draft Sales Invoice header、item row、tax row、Sales Invoice count 增加 1，以及 GL Entry / Stock Ledger Entry / Payment Entry / Journal Entry / Delivery Note / Stock Entry counts 不變，並執行 submitted preflight 與 latest formal draft target 確認。本階段不 submit、不建立正式 GL / Stock Ledger、不處理 Payment Entry / Journal Entry / Delivery Note / Stock Entry，真正 submit 仍留到 P1-ACC-6F-C。若 live site 沒有候選或 readiness 未 pass，blocked 是正確結果。

文件：`docs/p1-acc-6f-b-3-guarded-formal-sales-invoice-draft-creation-qa.md`。

## 15. P1-ACC-6F-C-0 Submitted Sales Invoice Submit Gate Snapshot

P1-ACC-6F-C-0 新增 submitted Sales Invoice submit 前最後 read-only gate snapshot。新的 service 只讀最新正式 Draft Sales Invoice 或指定 Sales Invoice，彙整 Sales Invoice submit gate 欄位、linked Used Car Vehicle、baseline counts 與 submitted preflight report，回傳 `ready_for_submit_test` 判斷是否可安排下一階段 real submit test。本階段不是 submit，不建立 draft，不修資料，不呼叫 guarded QA，也不建立 GL Entry / Stock Ledger Entry / Payment Entry / Journal Entry / Delivery Note / Stock Entry。

文件：`docs/p1-acc-6f-c-0-submitted-sales-invoice-submit-gate-snapshot.md`。

## 16. P1-ACC-6F-C-0A Split QA And Formal Preflight Baseline Semantics

P1-ACC-6F-C-0A 將 submitted Sales Invoice preflight baseline 分為 QA draft clean-site expected 與 formal Used Car Vehicle draft observe-only。P1-ACC-6E QA draft 仍在 `erpnext-coa.test` 上把 GL Entry / Stock Ledger Entry / submitted Sales Invoice count 非 0 視為 clean-site warning；formal draft 則只記錄 GL / Stock Ledger baseline counts，因正式流程在建立 Sales Invoice draft 前本來就可能已有 Stock Entry / Journal Entry ledger。submitted Sales Invoice count > 0 仍是第一張 submitted QA 污染風險。本階段不是 submit，也不是 fixture creation。

文件：`docs/p1-acc-6f-c-0a-split-qa-and-formal-preflight-baseline-semantics.md`。

## 17. P1-ACC-6F-C-0B Formal Submitted Sales Invoice Test Fixture Setup

P1-ACC-6F-C-0B 新增 formal submit fixture setup service。此 service 只允許在 `erpnext-coa.test` 執行，且 submitted Sales Invoice count 必須為 0；通過 gate 後會透過既有 Used Car Vehicle 正式流程建立測試車輛、入庫、上架、保留、訂金 / 尾款入帳、成交、Formal Draft Sales Invoice，最後執行 submit gate snapshot。此階段不是 submit，不清理 fixture，保留 Draft Sales Invoice 給下一階段 P1-ACC-6F-C real submit test。

P1-ACC-6F-C-0B-2 讓 formal submit fixture setup 可續跑 half-created fixture。若已存在 fixture vehicle 但沒有 Draft Sales Invoice，service 會用既有正式流程從目前狀態補齊入庫、上架、保留、訂金 / 尾款入帳、成交、readiness、guarded draft creation 與 submit gate snapshot；不刪除、不取消、不重建、不建立第二套 fixture，也不 submit Sales Invoice。

P1-ACC-6F-C 新增 guarded formal Sales Invoice submit QA。此 service 只允許在 `erpnext-coa.test`、confirmation token 正確、target formal fixture Draft Sales Invoice 通過 submit gate snapshot，且 submitted Sales Invoice count 仍為 0 時提交一張指定 Sales Invoice；submit 後只觀察 ERPNext 原生 GL Entry / Stock Ledger Entry、counts、Serial No 與 linked vehicle，不建立 Payment Entry / Delivery Note / Purchase Invoice、不做預收款沖轉、不回寫 `formal_delivery_status = 已完成`。

P1-ACC-6F-D 新增 submitted Sales Invoice 後的 formal delivery status sync。此 service 的 inspect 與 dry-run 完全只讀；write mode 只允許在 `erpnext-coa.test`、Sales Invoice 已提交且 target GL Entry / Stock Ledger Entry 存在時，透過 controlled write 將 linked Used Car Vehicle 的會計文件狀態同步為 `已完成`。本階段不是 submit，不修改 Sales Invoice / GL Entry / Stock Ledger Entry，不建立 Payment Entry / Delivery Note / Purchase Invoice / Journal Entry / Stock Entry，也不建立 `advance_settlement_journal_entry`。

P1-ACC-6G-0 新增預收款沖轉 readiness inspector。此 service 只讀 Sales Invoice、linked Used Car Vehicle、completed reservation、訂金 / 尾款金流、傳票草稿、Journal Entry、GL Entry 與 Account，用來確認是否具備下一階段建立 advance settlement Journal Entry 的條件；本階段不建立 Journal Entry、不提交、不寫回 `advance_settlement_journal_entry`、不修改 formal delivery status，也不把 15-1 稅務估算或整備 / 維修 / 美容 / 拍場 / 代辦等成本資料納入 settlement amount。

P1-ACC-6G-1 新增 guarded advance settlement Journal Entry QA。此 service 只允許在 `erpnext-coa.test` 且 confirmation token 正確時，根據 P1-ACC-6G-0 readiness preview 建立並提交一張沖轉 Journal Entry，借記預收 / 暫收負債科目、貸記 Sales Invoice 應收帳款，並只透過 controlled write 回寫 `Used Car Vehicle.advance_settlement_journal_entry`。本階段不建立 Payment Entry / Delivery Note / Purchase Invoice / Sales Invoice，不修改 Sales Invoice / Money Flow / Voucher Draft / Reservation，不使用 15-1 稅務估算或整備 / 維修 / 美容 / 拍場 / 代辦費。

P1-ACC-6H-0 新增 formal sale accounting closure inspector。此 service 只讀整台已售出車輛的正式售車會計閉環，檢查 `formal_delivery_status = 已完成`、submitted Sales Invoice、Sales Invoice GL Entry / Stock Ledger Entry、submitted advance settlement Journal Entry、settlement GL Entry、Sales Invoice outstanding 歸零、訂金 / 尾款金流與傳票鏈，以及 Payment Entry / Delivery Note / Purchase Invoice 等非本流程文件未產生。若 inspector pass，正式售車會計 runtime 可暫停開發，下一階段可轉向 Used Car Vehicle 簡化 UX、15-1 稅務邊界規格與會計 workspace / dashboard 整理。

目前 formal sale accounting closure 已完成，`ACC-SINV-2026-00004` 的 closure inspector 已回傳 `status = pass`、`closed = true`、`ready_for_ui_review = true`。會計 runtime 暫停擴張，下一階段先做 Vehicle UX / 15-1 tax boundary spec，不再新增會計 runtime。

P1-UX-TAX-0 新增 Used Car Vehicle 簡化 UX 與 15-1 稅務邊界規格。此文件定義車輛頁後續應聚焦基本資料、採購、售車、收支四個業務區塊，會計技術細節移往會計作業；同時明確 `purchase_price = 購車價`，15-1 只用於售車營業稅估算，整備 / 維修 / 美容 / 拍場 / 代辦費不併入 15-1 購入成本。

P1-UX-TAX-1 已開始依 P1-UX-TAX-0 重整 `Used Car Vehicle` 表單 layout，將區塊語意收斂為基本資料、採購、售車、收支、會計狀態、更多資訊。此階段只調整 DocType JSON 與文件，沒有 Python runtime、JS、Workspace、會計流程或 15-1 計算行為變更。

P1-UX-TAX-2 新增 read-only vehicle accounting status summary inspector。此 service 只讀 Vehicle、Sales Invoice、advance settlement Journal Entry、金流 / 傳票狀態與 formal sale accounting closure inspector 結果，回傳車輛頁可顯示的單一會計狀態、單一下一步與 summary cards；本階段沒有 write behavior，不修改 DocType JSON、不新增 JS、不建立或提交任何文件。

P1-UX-TAX-3 新增 read-only 15-1 tax estimate service。此 service 只讀 Vehicle 與 linked Sales Invoice，以 `purchase_price` 購車價與 `sold_price` / Sales Invoice grand_total 估算售車銷項稅額、15-1 可扣抵估算與預估本車營業稅；整備、維修、美容、拍場、代辦或其他後續支出不進入 15-1 購入成本。本階段沒有 write behavior，不修改 DocType JSON、不新增 JS、不建立或提交任何文件。

P1-UX-TAX-4 新增 read-only management profit summary service。此 service 只讀 Vehicle、linked Sales Invoice、Used Car Vehicle Cost 與明確可判斷的其他直接收入，計算成交價、購車價、直接成本、其他直接收入、管理毛利與管理毛利率；管理損益可包含整備、維修、美容、拍場、代辦費，但 15-1 稅務估算仍排除這些後續支出。本階段沒有 write behavior，不修改 DocType JSON、不新增 JS、不建立或提交任何文件。

P1-UX-TAX-5 Accounting Workspace Dashboard Cleanup 已收尾。此階段新增 read-only `VehicleDashboardSummaryService`，只包裝 Vehicle Accounting Status Summary、15-1 Tax Estimate、Management Profit Summary 三份既有 service，回傳單一 payload、薄的 `vehicle_page_summary`、`summary_cards` 與 `service_statuses`；個別 summary 失敗時保留其他 summary。此階段已在 `Used Car Vehicle` 單一頁面接入最小摘要顯示、清理重複 dashboard comments、新增 read-only `單車摘要候選` Desk Page，並在 `會計作業` Workspace 新增 `單車摘要候選` Page shortcut。使用者已確認 browser smoke 正常。後續不再於 P1-UX-TAX-5 擴張 accounting / tax / management profit runtime。

P1-UX-TAX-6 Step 1 新增 Used Car Vehicle primary action simplification 文件盤點。此步驟只讀 `Used Car Vehicle` JS、DocType layout、P1-UX-TAX-0/5 文件與 dashboard cleanup hook，盤點目前 buttons / dashboard comments / intro messages，定義 one-primary-action boundary；沒有修改 JS、Python service、DocType JSON、hooks.py、Workspace JSON 或任何 runtime 行為。

P1-UX-TAX-6 Step 2 已完成 JS-only non-sold / reserved primary action cleanup。`Used Car Vehicle` 非已售出 / 非保留中 refresh path 改由 `add_non_sold_vehicle_primary_action_button` 統一選擇單一下一步；保留中 ready 狀態不再同時顯示「成交前檢查」與「確認成交」，而是優先只顯示「確認成交」。本步驟未改 Python service、DocType JSON、hooks.py、Workspace JSON、會計 runtime、15-1 tax runtime 或 management profit runtime。

P1-UX-TAX-6 Step 3 已完成 JS-only sold vehicle secondary action grouping。已售出車輛仍保留 `get_sold_vehicle_primary_next_action` 作為主流程唯一來源；`顯示 / 隱藏文件連結` 改到 `更多資訊` 群組，`查看銷售發票` / `查看預收款沖轉傳票` 改到 `文件連結` 群組，`修復銷售發票草稿連結` 改到 `技術維護` 群組。本步驟未改 Python service、DocType JSON、hooks.py、Workspace JSON、formal sale accounting sequence 或任何 backend gate。

P1-UX-TAX-6 Step 4 已完成 JS-only dashboard legacy comment producer cleanup。`apply_vehicle_form_mode` 不再呼叫 `add_sold_vehicle_progress_comment`、`add_sold_vehicle_final_check_comment`、`add_formal_delivery_submit_preflight_comment`、`add_vehicle_cost_summary_comment`，讓 `accounting_status_summary_html` / `VehicleDashboardSummaryService` 成為主要 read-only summary surface；保留中 active reservation status 仍保留。依 browser smoke 回饋，`used_car_vehicle_dashboard_comment_cleanup.js` 已移除 refresh 後 `frm.dashboard.clear_comment()` fallback，避免 dashboard card 先閃現再消失；cleanup hook 只保留 prefix intercept safety net。本步驟未改 Python service、DocType JSON、hooks.py、Workspace JSON、accounting / tax / management profit runtime 或 formal sale accounting sequence。

P1-UX-TAX-6 Step 5 已新增 handoff / phase closure 文件並收尾此 UX cleanup phase。P1-UX-TAX-6 最終狀態：車輛頁每個正常 lifecycle state 至多顯示一個 primary next action；非已售出狀態由 `add_non_sold_vehicle_primary_action_button` 控制；已售出狀態保留 `get_sold_vehicle_primary_next_action`；文件連結 / 技術維護降級為 secondary groups；P1-UX-TAX-5 單車摘要成為主要 read-only summary surface。下一階段建議改走 documentation-first Accounting Operations migration decision，不要繼續擴張 P1-UX-TAX-6 runtime。

P1-MVP-DASH-1 Step 4C 已完成並收尾。`總覽` 現在是 `/app/總覽` native ERPNext Workspace Dashboard，不再 redirect 到 `used-car-management-dashboard`；`庫存狀態` 顯示 6 張 native Number Card：在庫、庫存中、整備中、上架中、保留中、已售出。Step 4C 已移除 overview redirect JS 與 hooks 載入，並修正 Workspace Number Card renderer 需要使用中文 label 匹配的問題。使用者已確認 `/app/總覽` 與 6 張卡片正常顯示。後續避免恢復 redirect，且總覽不放 15-1、會計待辦、待處理事項或中古車管理 Dashboard。

P1-UX-TAX-7 Step 1 已新增 Accounting Operations migration decision 文件。此步驟盤點售車後高衝擊會計動作，決定 `確認銷售發票並出庫`、`建立預收款沖轉草稿`、`確認預收款沖轉入帳`、`修復 Sales Invoice 草稿連結` 與 submit readiness 檢查的目標入口應逐步移往 `會計作業`，而不是長期留在 `Used Car Vehicle` 作為一般業務操作。本階段只做文件同步，不修改 JS、Python service、DocType JSON、Workspace、hooks.py、permission、accounting runtime、tax runtime 或 formal sale accounting sequence。

P1-UX-TAX-7 Step 2 已新增 Accounting Operations candidate list spec。此文件定義未來 `會計作業` 內 read-only `售車會計候選` 清單的分類、候選條件、顯示欄位、route target、排序與後續實作順序。候選分類包含：待確認銷售發票並出庫、待建立預收款沖轉草稿、待確認預收款沖轉入帳、需補資料 / blocked formal accounting、需技術修復 Sales Invoice 草稿連結。本階段沒有新增 Page、service、whitelisted method、Workspace shortcut 或任何 write behavior。

P1-UX-TAX-7 Step 3 已新增 read-only `FormalSaleAccountingCandidateService` 與 `run_formal_sale_accounting_candidates(limit=50)`，產出未來 `會計作業` 的 `售車會計候選` payload。已完成售車會計閉環案件不列入 candidate list；submitted Sales Invoice + submitted advance settlement Journal Entry 會被排除，不會顯示為 blocked。此 service 只讀 `Used Car Vehicle`、linked `Sales Invoice`、linked `Journal Entry`，不新增 Desk Page、不改 Workspace、不改 Vehicle JS、不建立 / 提交 / 修改 Sales Invoice、Journal Entry、Used Car Vehicle 或任何 ERPNext 文件。

P1-UX-TAX-7 Step 4 / Step 5 已將 read-only formal sale accounting candidates 接成 Desk Page，並在 會計作業 Workspace 加入 shortcut。`/app/formal-sale-accounting-candidates` 只呼叫 Step 3 read-only service，顯示候選摘要、分類清單、warnings / empty / error state 與 route-only 操作；此階段不會建立、提交、修復或修改 Sales Invoice、Journal Entry、Used Car Vehicle 或任何 ERPNext 文件。

P1-UX-TAX-7 Step 7 已新增 smoke handoff 文件。Step 6 site apply / smoke 已確認 Page record 存在、Workspace DB content 已包含 `uco_formal_sale_accounting_candidates`、service execute 回傳 `status = pass`，且使用者手動確認 `/app/formal-sale-accounting-candidates` 與 `/app/會計作業` shortcut 正常。此 handoff 將目前穩定點標記為可進入 Step 8：Vehicle Page accounting action demotion。

P1-UX-TAX-7 Step 8A 已新增 Vehicle Page accounting action demotion spec。此文件盤點 `used_car_vehicle.js` 中已售出車輛的 primary action mapping，明確定義後續 JS-only 實作應保留 `建立 Sales Invoice 草稿` 與文件 route links，並將 `確認銷售發票並出庫`、`建立預收款沖轉草稿`、`確認預收款沖轉入帳`、`修復 Sales Invoice 草稿連結` 從一般車輛頁 mutation surface 降級到 `會計作業 → 售車會計候選`。本階段只改文件，不修改 runtime。

文件：`docs/p1-acc-6f-c-0b-formal-submitted-sales-invoice-test-fixture-setup.md`。

文件：`docs/p1-acc-6f-c-guarded-formal-sales-invoice-submit-qa.md`。

文件：`docs/p1-acc-6f-d-post-submit-formal-delivery-status-sync.md`。

文件：`docs/p1-acc-6g-0-advance-settlement-readiness-inspector.md`。

文件：`docs/p1-acc-6g-1-guarded-advance-settlement-journal-qa.md`。

文件：`docs/p1-acc-6h-0-formal-sale-accounting-closure-inspector.md`。

文件：`docs/p1-ux-tax-0-used-car-vehicle-simplified-ux-and-15-1-tax-boundary-spec.md`。

文件：`docs/p1-ux-tax-1-used-car-vehicle-form-section-layout-refactor.md`。

文件：`docs/p1-ux-tax-2-vehicle-accounting-status-summary-inspector.md`。

文件：`docs/p1-ux-tax-3-vehicle-15-1-tax-estimate-read-only-service.md`。

文件：`docs/p1-ux-tax-4-vehicle-management-profit-summary-read-only-service.md`。

文件：`docs/p1-ux-tax-5-accounting-workspace-dashboard-cleanup.md`。

文件：`docs/p1-ux-tax-5-step-8-handoff.md`。

文件：`docs/p1-ux-tax-6-vehicle-primary-action-simplification.md`。

文件：`docs/p1-ux-tax-6-step-2-non-sold-reserved-primary-action-cleanup.md`。

文件：`docs/p1-ux-tax-6-step-3-sold-vehicle-secondary-action-grouping.md`。

文件：`docs/p1-ux-tax-6-step-4-dashboard-legacy-comment-producer-cleanup.md`。

文件：`docs/p1-ux-tax-6-step-5-handoff.md`。

文件：`docs/p1-mvp-dash-1-used-car-management-dashboard-mvp.md`。

文件：`docs/p1-mvp-dash-1-step-2-dashboard-entry.md`。

文件：`docs/p1-mvp-dash-1-step-4c-handoff.md`。

文件：`docs/p1-ux-tax-7-accounting-operations-migration-decision.md`。

文件：`docs/p1-ux-tax-7-step-2-accounting-operations-candidate-list-spec.md`。

文件：`docs/p1-ux-tax-7-step-3-read-only-candidate-service.md`。

文件：`docs/p1-ux-tax-7-step-4-formal-sale-accounting-candidate-page.md`。

文件：`docs/p1-ux-tax-7-step-7-smoke-handoff.md`。

文件：`docs/p1-ux-tax-7-step-8a-vehicle-page-accounting-action-demotion-spec.md`。

Service：`used_car_erp/used_car_erp/services/formal_sale_accounting_candidate_service.py`。

Page：`used_car_erp/used_car_erp/page/formal_sale_accounting_candidates/formal_sale_accounting_candidates.js`。

Test：`used_car_erp/used_car_erp/services/test_formal_sale_accounting_candidate_service.py`。

Service：`used_car_erp/used_car_erp/services/vehicle_dashboard_summary_service.py`。

UI：`used_car_erp/used_car_erp/doctype/used_car_vehicle/used_car_vehicle.js`。

Test：`used_car_erp/used_car_erp/services/test_vehicle_dashboard_summary_service.py`。

## 18. 驗證指令

目前常用驗證指令。以下站台以 `erpnext-coa.test` 為準；早期 `erpnext.localhost` 指令屬舊資料，後續不要照抄使用。

```bash
cd ~/frappe/frappe-bench

bench --site erpnext-coa.test migrate
bench --site erpnext-coa.test clear-cache
bench build --app used_car_erp
bench --site erpnext-coa.test clear-cache

bench --site erpnext-coa.test execute used_car_erp.used_car_erp.services.vehicle_item_service.verify_vehicle_item_service

bench --site erpnext-coa.test execute used_car_erp.used_car_erp.services.vehicle_stock_service.verify_vehicle_stock_service

bench --site erpnext-coa.test execute used_car_erp.used_car_erp.services.vehicle_intake_service.verify_vehicle_intake_service
```

如果 `run-tests` 顯示 `Testing is disabled for the site`，不要為了本次文件修改而更動站台測試設定。

## 16. Commit 歷史參考

最近穩定 commits：

* `6b2ddb0` `feat: add vehicle item service foundation`
* `204909c` `feat: add vehicle stock in service foundation`
* `12ae683` `polish: update vehicle ERPNext link descriptions`

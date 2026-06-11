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
→ 保留中
→ 取消保留
→ 上架中
```

訂金保留會建立 `Used Car Reservation`。
訂金保留可以建立 / 連結 ERPNext `Customer`。
車輛會從「上架中」改為「保留中」。
取消保留會讓車輛回到「上架中」。
訂金金額目前是業務紀錄，不是 `Payment Entry`。
不建立 `Sales Invoice`。
不建立 `Delivery Note`。
不出庫。
不認列收入。
不建立會計分錄。

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
* 訂金金額目前只是業務保留紀錄，不是 `Payment Entry`。
* 不建立 `Sales Invoice` / `Payment Entry` / `Delivery Note` / `Journal Entry`。
* 不建立新的 `Stock Entry`。
* 不出庫、不認列收入、不建立會計分錄。

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
* 不做收款。
* 不做 `Sales Invoice`。
* 不做 `Purchase Invoice`。
* 不做 `Payment Entry`。
* 不做 `Journal Entry`。
* 不做會計自動分錄。
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

## 9. 驗證指令

目前常用驗證指令：

```bash
cd ~/frappe/frappe-bench

bench --site erpnext.localhost migrate
bench --site erpnext.localhost clear-cache
bench build --app used_car_erp
bench --site erpnext.localhost clear-cache

bench --site erpnext.localhost execute used_car_erp.used_car_erp.services.vehicle_item_service.verify_vehicle_item_service

bench --site erpnext.localhost execute used_car_erp.used_car_erp.services.vehicle_stock_service.verify_vehicle_stock_service

bench --site erpnext.localhost execute used_car_erp.used_car_erp.services.vehicle_intake_service.verify_vehicle_intake_service
```

如果 `run-tests` 顯示 `Testing is disabled for the site`，不要為了本次文件修改而更動站台測試設定。

## 10. Commit 歷史參考

最近穩定 commits：

* `6b2ddb0` `feat: add vehicle item service foundation`
* `204909c` `feat: add vehicle stock in service foundation`
* `12ae683` `polish: update vehicle ERPNext link descriptions`

# Used Car ERP Module Boundaries

## Current Stable Modules

* Used Car Vehicle DocType
* Used Car Vehicle Form UX
* Used Car Vehicle List UX
* Used Car ERP Workspace
* Vehicle Item Service Foundation
* Vehicle Stock In Service Foundation
* Vehicle Intake Service UX Orchestration
* Vehicle Preparation / Listing Service Foundation

## Boundaries

### Workspace

只負責導航入口與常用連結。
不得包含業務資料寫入邏輯。
不得呼叫建立 Item / Serial No / Invoice / Payment 的方法。

### List View

只負責列表顯示、狀態顏色、快速辨識。
不得修改資料。
不得呼叫後端寫入方法。
不得控制表單欄位唯讀。

### Form View

只負責單筆 Used Car Vehicle 表單互動。
目前包含：已存在車輛預設檢視模式、按「編輯資料」才解鎖。
不得放 Workspace 導航邏輯。
不得放 Item / Serial No / Invoice / Payment 建立邏輯。
表單 JS 只能呼叫 whitelisted service endpoint，不承擔跨 DocType 業務邏輯。
表單 UI 應盡量提供業務語意 action，例如「完成入庫」，不要讓一般使用者直接操作 ERPNext 底層概念，例如「建立 Item」或「建立 Stock Entry」。
Used Car Vehicle Form 可以顯示業務 action，例如「開始整備」、「直接上架」、「整備完成並上架」、「下架回庫存」，但 JS 不得直接修改 status，必須呼叫 whitelisted service。

### Python Controller

只負責 Used Car Vehicle 的資料生命週期。
目前包含：stock_no 系統自動產生、禁止修改 stock_no。
不得直接塞入跨模組大型流程。
未來跨 DocType 流程應拆到 service。

### Future Services

vehicle_item_service.py 只負責 Used Car Vehicle 與 ERPNext Item 的建立 / 綁定。
不得建立 Serial No、Stock Entry、Purchase Invoice、Sales Invoice、Payment Entry。

vehicle_stock_service.py 只負責 Used Car Vehicle 正式入庫、Stock Entry、Serial No / VIN 綁定、回寫 stock_entry / serial_no / status。
不得建立 Purchase Invoice、Sales Invoice、Payment Entry、會計分錄。
不得處理售出、出庫、交車。

vehicle_intake_service.py 只負責編排 Used Car Vehicle 入庫流程，呼叫 VehicleItemService 與 VehicleStockService。
不得直接重寫 Item / Stock Entry / Serial No 底層邏輯。
不得建立 Purchase Invoice、Sales Invoice、Payment Entry、會計分錄。
不得處理銷售、保留、出庫、交車。

vehicle_listing_service.py 只負責入庫後、銷售前的 Used Car Vehicle 業務狀態轉換。
允許：

* 庫存中 → 整備中
* 庫存中 → 上架中
* 整備中 → 上架中
* 上架中 → 庫存中

不允許：

* 建立 Stock Entry
* 建立 Sales Invoice
* 建立 Purchase Invoice
* 建立 Payment Entry
* 建立 Delivery Note
* 建立 Journal Entry
* 修改 Stock Ledger
* 修改 Serial No
* 處理訂金 / 客戶 / 銷售 / 出庫 / 收款 / 會計

未來若要做 Serial No / Purchase Invoice / Sales Invoice / Payment Entry 自動化，請建立獨立 service 檔案，例如：

used_car_erp/used_car_erp/services/vehicle_item_service.py
used_car_erp/used_car_erp/services/vehicle_stock_service.py
used_car_erp/used_car_erp/services/vehicle_intake_service.py
used_car_erp/used_car_erp/services/vehicle_listing_service.py
used_car_erp/used_car_erp/services/vehicle_purchase_service.py
used_car_erp/used_car_erp/services/vehicle_sales_service.py

表單 JS 只能呼叫 whitelisted service endpoint，不直接承擔業務邏輯。
任何會產生 Stock Ledger 的服務，都必須獨立於 Form JS 和 DocType controller，並提供 bench execute 驗證。

## Rule

修 A 不應該破壞 B。
每次修改必須限制在對應模組檔案。
如果需要跨模組修改，必須在 commit summary 中明確列出原因。

# Used Car ERP Module Boundaries

## Current Stable Modules

* Used Car Vehicle DocType
* Used Car Vehicle Form UX
* Used Car Vehicle List UX
* Used Car ERP Workspace

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

### Python Controller

只負責 Used Car Vehicle 的資料生命週期。
目前包含：stock_no 系統自動產生、禁止修改 stock_no。
不得直接塞入跨模組大型流程。
未來跨 DocType 流程應拆到 service。

### Future Services

未來若要做 Item / Serial No / Purchase Invoice / Sales Invoice / Payment Entry 自動化，請建立獨立 service 檔案，例如：

used_car_erp/used_car_erp/services/vehicle_item_service.py
used_car_erp/used_car_erp/services/vehicle_purchase_service.py
used_car_erp/used_car_erp/services/vehicle_sales_service.py

表單 JS 只能呼叫 whitelisted endpoint，不直接承擔業務邏輯。

## Rule

修 A 不應該破壞 B。
每次修改必須限制在對應模組檔案。
如果需要跨模組修改，必須在 commit summary 中明確列出原因。

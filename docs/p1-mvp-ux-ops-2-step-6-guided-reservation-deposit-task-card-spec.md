# P1-MVP-UX-OPS-2 Step 6：Guided Reservation / Deposit Task Card Spec

日期：2026-06-24  
專案：Used Car ERP / ERPNext / Frappe  
Repo：`ericzhan0819/used_car_erp`  
前置穩定點：`26494d6 docs: close guided listing dialog smoke`

---

## 1. 本階段目的

本文件定義下一張業務任務卡：

```text
收訂金並保留
```

目標是讓業務人員在車輛上架後，用一張清楚的任務卡輸入訂金與保留事實，而不是直接面對 `Used Car Reservation`、`Used Car Money Flow` 或 `Used Car Voucher Draft` 等底層文件。

本階段是規格文件，不做 runtime。

```text
不改 JavaScript runtime
不改 Python service
不改 DocType JSON
不改 hooks.py
不改 Workspace / Page
不新增 schema
不改會計流程
不建立 / 修改 / 提交任何 ERPNext 會計文件
```

---

## 2. 產品背景

目前已完成：

```text
P1-MVP-UX-OPS-2 Step 5S：Add Listing Date Field
P1-MVP-UX-OPS-2 Step 5A：Guided Listing Dialog Runtime
P1-MVP-UX-OPS-2 Step 5A：Guided Listing Dialog Smoke Close
```

也就是：

```text
車輛頁「整備完成並上架」已改為 shared guided Dialog
車輛可由 整備中 → 上架中
listing_date / floor_price / asking_price / sales_note 已可寫回
browser smoke passed
```

上架後，下一個自然業務動作是：

```text
客戶看車後付訂金
車輛暫時保留
避免同一台車被重複銷售
```

因此 Step 6 應先定義「收訂金並保留」任務卡的 UX、欄位、底層沿用方式與邊界，再進入 runtime。

---

## 3. 現有 foundation 盤點結論

現有 backend foundation 已足以支援 Step 6 初版。

目前既有流程：

```text
車輛頁 → 建立訂金保留
→ Used Car Reservation
→ Used Car Money Flow：訂金收款
→ Used Car Voucher Draft：訂金傳票草稿
→ Vehicle status = 保留中
```

會計作業後續再確認傳票草稿，才會建立正式 `Journal Entry`。

此流程符合目前產品邊界：

```text
業務輸入事實
系統建立資料流與待審核草稿
會計作業確認正式入帳
業務頁只看業務結果
```

因此 Step 6A runtime 不需要新增 schema，也不需要新增 backend service。

---

## 4. 業務與會計邊界

### 4.1 業務端要做的事

業務端只輸入：

```text
這台車是哪台
客戶是誰
客戶電話
收了多少訂金
何時收訂金
用什麼方式付款
付款備註或末五碼
備註
```

### 4.2 系統要做的事

系統接收業務事實後：

```text
建立保留紀錄
建立訂金收款紀錄
建立待內部確認的草稿
車輛狀態改為 保留中
```

### 4.3 會計端要做的事

會計端在「會計作業」處理：

```text
審核訂金收款
確認草稿金額與科目
建立正式 Journal Entry
```

這些不應出現在業務任務卡內。

---

## 5. 任務入口

### 5.1 按鈕名稱

業務頁按鈕應使用：

```text
收訂金並保留
```

不建議繼續使用：

```text
建立訂金保留
```

原因：

```text
「建立」偏系統操作語氣；「收訂金並保留」比較接近業務真實動作。
```

### 5.2 顯示位置

建議放在：

```text
車輛作業
```

### 5.3 顯示條件

按鈕應只在合理狀態顯示：

```text
車輛已儲存
車輛已入庫
車輛狀態 = 上架中
沒有有效保留單
```

### 5.4 不顯示條件

按鈕不應顯示於：

```text
草稿
庫存中
整備中
保留中
已售出
封存
```

若車輛已保留，應進入保留中流程，不應再次建立訂金保留。

---

## 6. Dialog 欄位規格

### 6.1 Dialog 標題

```text
收訂金並保留
```

### 6.2 必填欄位

```text
vehicle：車輛，由入口帶入，不要求使用者重選
customer_name：客戶姓名
customer_phone：客戶電話
deposit_amount：訂金金額
payment_method：付款方式
deposit_date：訂金日期，預設今天
```

### 6.3 選填欄位

```text
payment_reference：付款備註 / 末五碼
notes：備註
```

### 6.4 建議顯示順序

```text
車輛資訊
客戶姓名
客戶電話
訂金金額
付款方式
訂金日期
付款備註 / 末五碼
備註
```

### 6.5 對應 backend input

任務卡欄位對應：

| Dialog 欄位 | backend input |
| --- | --- |
| 車輛 | `vehicle_name` |
| 客戶姓名 | `customer_name` |
| 客戶電話 | `customer_phone` |
| 訂金金額 | `deposit_amount` |
| 付款方式 | `payment_method` |
| 訂金日期 | `deposit_date` |
| 付款備註 / 末五碼 | `payment_reference` |
| 備註 | `notes` |

backend method：

```text
used_car_erp.used_car_erp.services.vehicle_reservation_service.create_reservation
```

---

## 7. Step 6 初版暫不放入的欄位

以下欄位不放入 Step 6 初版：

```text
既有客戶
成交價
銷售人員
尾款
交車日期
```

原因：

```text
現有 create_reservation 已支援訂金保留主流程
成交價 / 銷售人員牽涉 Used Car Vehicle controlled write
尾款屬於保留後下一步
交車日期屬於成交 / 交車流程
```

若要把成交價或銷售人員納入保留流程，應另開小步任務，例如：

```text
P1-MVP-UX-OPS-2 Step 6S：Reservation Sale Field Controlled Write
```

或納入後續「售出 / 收尾款」任務卡，不應混入 Step 6A 初版 runtime。

---

## 8. 成功後行為

成功後業務 UI 應顯示：

```text
已收訂金，車輛已保留
```

成功後系統狀態：

```text
車輛狀態 = 保留中
```

成功後應：

```text
reload_doc
刷新表單
不跳轉會計文件
不跳轉 ERPNext 技術文件
不顯示 backend 技術 message
```

不得把 backend 回傳的完整 message 直接顯示給業務。

目前 backend message 可能包含：

```text
金流紀錄
傳票草稿
```

Step 6A runtime 應改用固定業務成功訊息，不直接顯示此類技術字詞。

---

## 9. 底層行為邊界

Step 6A runtime 可以沿用現有底層行為：

```text
建立 Used Car Reservation
建立 Used Car Money Flow：訂金收款
建立 Used Car Voucher Draft
Vehicle status = 保留中
```

但業務 UI 不得顯示底層文件名稱。

Step 6A 不應：

```text
建立 Journal Entry
建立 Sales Invoice
建立 Payment Entry
建立 Stock Entry
建立 Delivery Note
提交任何 ERPNext 文件
建立預收款沖轉
修改 15-1 service
修改管理利潤 service
修改會計科目
修改正式交車流程
```

---

## 10. 業務 UI 禁止字詞

不得出現在 Dialog、成功訊息、錯誤提示、任務卡文案：

```text
Money Flow
Voucher Draft
Journal Entry
Sales Invoice
Payment Entry
Stock Entry
Delivery Note
GL Entry
debit
credit
借方
貸方
會計科目
金流紀錄
傳票草稿
正式會計傳票
預收款沖轉
formal delivery
15-1
```

可使用的業務語意：

```text
收訂金並保留
客戶
訂金
付款方式
訂金日期
付款備註
車輛已保留
內部處理中
```

---

## 11. 驗證與阻擋規則

送出前應驗證：

```text
車輛存在
車輛已儲存
車輛已入庫
車輛狀態 = 上架中
客戶姓名存在
客戶電話存在
訂金金額 > 0
付款方式存在且為允許值
訂金日期存在
```

如果車輛不是上架中，應提示：

```text
此車目前不是上架中，不能使用「收訂金並保留」。
```

如果已有有效保留，應提示：

```text
此車已保留，不能重複收訂金保留。
```

不得顯示：

```text
Invalid workflow state
DocPerm denied
Used Car Reservation duplicate
```

---

## 12. 與現有保留中流程的關係

Step 6A 只處理：

```text
上架中 → 收訂金並保留 → 保留中
```

不處理：

```text
保留中 → 建立尾款收款
保留中 → 確認成交
保留中 → 取消保留 polish
```

現有保留中 dashboard 仍可能顯示偏技術字詞，例如：

```text
傳票草稿
已記錄金流
等待會計確認訂金與尾款傳票
```

這是已知問題。

後續應另開小步整理：

```text
P1-MVP-UX-OPS-2 Step 6B：Reserved Vehicle Status Copy Polish
```

或在 Step 7 尾款任務卡時一併調整保留中狀態文案。

Step 6A 不應同時改保留中整段流程，避免 scope 擴大。

---

## 13. Step 6A runtime 建議切分

Step 6A 建議做最小 runtime：

```text
P1-MVP-UX-OPS-2 Step 6A：Guided Reservation / Deposit Dialog Runtime
```

允許範圍：

```text
新增 shared guided reservation/deposit Dialog
車輛頁「建立訂金保留」改為「收訂金並保留」
沿用 vehicle_reservation_service.create_reservation
成功後顯示「已收訂金，車輛已保留」
成功後 reload_doc
hooks.py 載入新的 shared JS
```

建議新增檔案：

```text
used_car_erp/public/js/guided_reservation_deposit_dialog.js
```

建議 namespace：

```text
used_car_erp.guided_reservation_deposit.open(frm)
```

可修改檔案：

```text
used_car_erp/public/js/guided_reservation_deposit_dialog.js
used_car_erp/used_car_erp/doctype/used_car_vehicle/used_car_vehicle.js
used_car_erp/hooks.py
```

不做：

```text
不新增 schema
不改 Python service
不改 DocType JSON
不改會計流程
不處理尾款
不處理成交
不處理 Sales Invoice
不處理 Journal Entry
不處理權限大改
```

---

## 14. Step 6A 驗收標準

Step 6A 完成後應能驗證：

```text
1. 使用一台狀態為 上架中 且已入庫的車
2. 車輛頁看到「收訂金並保留」
3. 點擊後開啟業務語意 Dialog
4. 填寫客戶姓名 / 客戶電話 / 訂金金額 / 付款方式 / 訂金日期
5. 送出後顯示「已收訂金，車輛已保留」
6. 車輛狀態變成 保留中
7. 底層可建立保留與待內部處理資料流
8. 業務 UI 不顯示 Money Flow / Voucher Draft / Journal Entry / Sales Invoice 等技術字詞
9. 不建立 Journal Entry
10. 不建立 Sales Invoice / Payment Entry / Stock Entry
```

若 Dialog 無法載入，應顯示：

```text
收訂金並保留元件尚未載入，請重新整理後再試。
```

---

## 15. 明確不做事項

本規格不要求：

```text
不新增 runtime
不新增 schema
不改 Python service
不改 DocType JSON
不改 hooks.py
不改 Workspace / Page
不改權限
不改會計流程
不建立 Journal Entry
不建立 Sales Invoice
不建立 Payment Entry
不建立 Stock Entry
不建立 Delivery Note
不建立預收款沖轉
不處理尾款任務卡
不處理確認成交任務卡
不處理正式交車入帳
不清理保留中 dashboard 文案
不清理測試資料
```

Step 6A 實作時若發現現有 backend 不足，應停止並回報，不要在同一任務內擴大 schema 或 backend 範圍。

---

## 16. 下一步

建議下一步：

```text
P1-MVP-UX-OPS-2 Step 6A：Guided Reservation / Deposit Dialog Runtime
```

Step 6A 開始前應先盤點：

```text
vehicle_reservation_service.create_reservation input / output
used_car_vehicle.js 既有 add_create_reservation_button
hooks.py app_include_js
現有 guided listing / preparation expense Dialog 寫法
```

建議 commit message：

```text
feat: add guided reservation deposit dialog
```

本文件 commit message：

```text
docs: define guided reservation deposit task card
```

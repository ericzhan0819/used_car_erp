# P1-MVP-UX-OPS-2 Step 7：Guided Final Payment Task Card Spec

日期：2026-06-25  
專案：Used Car ERP / ERPNext / Frappe  
Repo：`ericzhan0819/used_car_erp`  
前置穩定點：`0c9f626 docs: close reservation deposit smoke`

---

## 1. 本階段目的

本文件定義下一張業務任務卡：

```text
收尾款
```

目標是讓業務人員在車輛已保留後，用一張清楚的任務卡輸入尾款收款事實，而不是直接面對 `Used Car Money Flow`、`Used Car Voucher Draft` 或任何會計文件。

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
P1-MVP-UX-OPS-2 Step 6：Guided Reservation / Deposit Task Card Spec
P1-MVP-UX-OPS-2 Step 6A：Guided Reservation / Deposit Dialog Runtime
P1-MVP-UX-OPS-2 Step 6A：Guided Reservation / Deposit Dialog Smoke Close
```

也就是：

```text
車輛頁「收訂金並保留」已改為 shared guided Dialog
上架中車輛可收訂金並進入 保留中
成功訊息為「已收訂金，車輛已保留」
browser smoke passed
```

保留後，下一個自然業務動作是：

```text
客戶付清尾款
業務記錄尾款收款事實
系統產生待內部處理資料
會計後續確認正式入帳
```

因此 Step 7 應先定義「收尾款」任務卡的 UX、欄位、底層沿用方式與邊界，再進入 runtime。

---

## 3. 現有 foundation 盤點結論

現有 backend foundation 已足以支援 Step 7 初版。

目前既有流程：

```text
保留中車輛 → 建立尾款收款
→ 找有效 Used Car Reservation
→ 建立 Used Car Money Flow：尾款收款
→ 建立 Used Car Voucher Draft：尾款傳票草稿
→ 保留單回寫 final_payment_* 與 final_* link
```

會計作業後續再確認傳票草稿，才會建立正式 `Journal Entry`。

此流程符合目前產品邊界：

```text
業務輸入收款事實
系統建立資料流與待審核草稿
會計作業確認正式入帳
業務頁只看業務結果
```

因此 Step 7A runtime 不需要新增 schema，也不需要新增 backend service。

---

## 4. 業務與會計邊界

### 4.1 業務端要做的事

業務端只輸入：

```text
這台保留車是哪台
收了多少尾款
何時收尾款
用什麼方式付款
付款備註或末五碼
備註
```

### 4.2 系統要做的事

系統接收業務事實後：

```text
找到有效保留紀錄
建立尾款收款紀錄
建立待內部確認的草稿
保留單記錄尾款資訊
```

### 4.3 會計端要做的事

會計端在「會計作業」處理：

```text
審核尾款收款
確認草稿金額與科目
建立正式 Journal Entry
```

這些不應出現在業務任務卡內。

---

## 5. 任務入口

### 5.1 按鈕名稱

業務頁按鈕應使用：

```text
收尾款
```

不建議繼續使用：

```text
建立尾款收款
```

原因：

```text
「建立」偏系統操作語氣；「收尾款」比較接近業務真實動作。
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
車輛狀態 = 保留中
存在有效保留單
訂金保留已建立
尚未建立尾款收款
```

現有 JS 已可透過 `get_active_reservation_for_vehicle` 取得 active reservation payload，並依 `final_money_flow` / `final_voucher_draft` 判斷是否需要建立尾款。

### 5.4 不顯示條件

按鈕不應顯示於：

```text
草稿
庫存中
整備中
上架中
已售出
封存
沒有有效保留單
已建立尾款收款
```

若尾款已建立，應進入等待內部確認 / 成交前檢查階段，不應重複收尾款。

---

## 6. Dialog 欄位規格

### 6.1 Dialog 標題

```text
收尾款
```

### 6.2 建議 read-only 顯示資訊

```text
車輛資訊
客戶資訊
訂金資訊
```

其中：

```text
車輛資訊：來自 frm.doc
客戶資訊：來自 active reservation payload
訂金資訊：來自 active reservation payload
```

### 6.3 必填欄位

```text
amount：尾款金額
payment_method：付款方式
payment_date：尾款日期，預設今天
```

### 6.4 選填欄位

```text
payment_reference：付款備註 / 末五碼
notes：備註
```

### 6.5 建議顯示順序

```text
車輛資訊
客戶資訊
訂金資訊
尾款金額
付款方式
尾款日期
付款備註 / 末五碼
備註
```

### 6.6 對應 backend input

任務卡欄位對應：

| Dialog 欄位 | backend input |
| --- | --- |
| 車輛 | `vehicle_name` |
| 尾款金額 | `amount` |
| 付款方式 | `payment_method` |
| 尾款日期 | `payment_date` |
| 付款備註 / 末五碼 | `payment_reference` |
| 備註 | `notes` |

backend method：

```text
used_car_erp.used_car_erp.services.vehicle_reservation_service.create_final_payment_for_active_reservation
```

---

## 7. Step 7 初版暫不放入的欄位與行為

以下不放入 Step 7 初版：

```text
成交確認
交車日期
Sales Invoice
Journal Entry
Payment Entry
Stock Entry
Delivery Note
預收款沖轉
正式交車入帳
```

原因：

```text
Step 7 只處理「收尾款」
成交確認屬於尾款與會計確認後的下一張任務卡
Sales Invoice / Journal Entry 屬於會計作業
Payment Entry / Stock Entry / Delivery Note 不是目前業務任務卡範圍
```

若要做成交確認，應另開：

```text
P1-MVP-UX-OPS-2 Step 8：Guided Sale Completion Task Card Spec
```

或等尾款與會計確認流程跑通後再設計。

---

## 8. 成功後行為

成功後業務 UI 應顯示：

```text
已收尾款
```

成功後應：

```text
reload_doc
刷新保留中狀態摘要
不跳轉會計文件
不跳轉 ERPNext 技術文件
不顯示 backend 技術 message
```

不得把 backend 回傳的完整 message 直接顯示給業務。

目前 backend message 可能包含：

```text
金流紀錄
傳票草稿
等待會計審核入帳
```

Step 7A runtime 應改用固定業務成功訊息，不直接顯示此類技術字詞。

---

## 9. 底層行為邊界

Step 7A runtime 可以沿用現有底層行為：

```text
建立 Used Car Money Flow：尾款收款
建立 Used Car Voucher Draft
Used Car Reservation 回寫 final_payment_amount
Used Car Reservation 回寫 final_payment_date
Used Car Reservation 回寫 final_payment_method
Used Car Reservation 回寫 final_payment_reference
Used Car Reservation 回寫 final_payment_notes
Used Car Reservation 回寫 final_money_flow
Used Car Reservation 回寫 final_voucher_draft
```

但業務 UI 不得顯示底層文件名稱。

Step 7A 不應：

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
確認成交
```

---

## 10. 業務 UI 禁止字詞

不得出現在 Dialog、成功訊息、錯誤提示、確認訊息、任務卡文案：

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
收尾款
尾款金額
付款方式
尾款日期
付款備註
已收尾款
內部處理中
```

---

## 11. 驗證與阻擋規則

送出前應驗證：

```text
車輛存在
車輛已儲存
車輛狀態 = 保留中
存在有效保留單
尚未建立尾款收款
尾款金額 > 0
付款方式存在且為允許值
尾款日期存在
```

如果車輛不是保留中，應提示：

```text
此車目前不是保留中，不能使用「收尾款」。
```

如果找不到有效保留單，應提示：

```text
找不到此車輛的有效保留資料，請先確認保留狀態。
```

如果尾款已建立，應提示：

```text
此車已記錄尾款，不能重複收尾款。
```

不得顯示：

```text
Invalid workflow state
DocPerm denied
Used Car Money Flow duplicate
Used Car Voucher Draft exists
```

---

## 12. 與保留中狀態摘要的關係

Step 7A 只處理：

```text
保留中 → 收尾款
```

不處理：

```text
保留中 dashboard 全面文案降噪
成交前檢查
確認成交
正式交車入帳
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
P1-MVP-UX-OPS-2 Step 7B：Reserved Vehicle Status Copy Polish
```

也可以在 Step 7A smoke 後再決定是否立即做文案降噪。

---

## 13. Step 7A runtime 建議切分

Step 7A 建議做最小 runtime：

```text
P1-MVP-UX-OPS-2 Step 7A：Guided Final Payment Dialog Runtime
```

允許範圍：

```text
新增 shared guided final payment Dialog
車輛頁「建立尾款收款」改為「收尾款」
沿用 vehicle_reservation_service.create_final_payment_for_active_reservation
成功後顯示「已收尾款」
成功後 reload_doc
hooks.py 載入新的 shared JS
```

建議新增檔案：

```text
used_car_erp/public/js/guided_final_payment_dialog.js
```

建議 namespace：

```text
used_car_erp.guided_final_payment.open(frm)
```

可修改檔案：

```text
used_car_erp/public/js/guided_final_payment_dialog.js
used_car_erp/used_car_erp/doctype/used_car_vehicle/used_car_vehicle.js
used_car_erp/hooks.py
```

不做：

```text
不新增 schema
不改 Python service
不改 DocType JSON
不改會計流程
不處理成交
不處理 Sales Invoice
不處理 Journal Entry
不處理權限大改
```

---

## 14. Step 7A 驗收標準

Step 7A 完成後應能驗證：

```text
1. 使用一台狀態為 保留中 且有有效保留單的車
2. 若尚未收尾款，車輛頁看到「收尾款」
3. 點擊後開啟業務語意 Dialog
4. Dialog 顯示車輛資訊、客戶資訊、訂金資訊與尾款欄位
5. 填寫尾款金額 / 付款方式 / 尾款日期
6. 送出後顯示「已收尾款」
7. 表單刷新後不重複顯示「收尾款」
8. 底層可建立尾款待內部處理資料
9. 業務 UI 不顯示 Money Flow / Voucher Draft / Journal Entry / Sales Invoice 等技術字詞
10. 不建立 Journal Entry
11. 不建立 Sales Invoice / Payment Entry / Stock Entry
```

若 Dialog 無法載入，應顯示：

```text
收尾款元件尚未載入，請重新整理後再試。
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
不處理確認成交任務卡
不處理正式交車入帳
不清理保留中 dashboard 文案
不清理測試資料
```

Step 7A 實作時若發現現有 backend 不足，應停止並回報，不要在同一任務內擴大 schema 或 backend 範圍。

---

## 16. 下一步

建議下一步：

```text
P1-MVP-UX-OPS-2 Step 7A：Guided Final Payment Dialog Runtime
```

Step 7A 開始前應先盤點：

```text
vehicle_reservation_service.create_final_payment_for_active_reservation input / output
used_car_vehicle.js 既有 add_final_payment_button
get_active_reservation_for_vehicle payload
hooks.py app_include_js
現有 guided reservation/deposit Dialog 寫法
```

建議 runtime commit message：

```text
feat: add guided final payment dialog
```

本文件 commit message：

```text
docs: define guided final payment task card
```

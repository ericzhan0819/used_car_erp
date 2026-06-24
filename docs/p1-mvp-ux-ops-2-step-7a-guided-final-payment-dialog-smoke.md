# P1-MVP-UX-OPS-2 Step 7A：Guided Final Payment Dialog Smoke Close

日期：2026-06-25  
專案：Used Car ERP / ERPNext / Frappe  
Repo：`ericzhan0819/used_car_erp`  
前置規格穩定點：`29b5959 docs: define guided final payment task card`

---

## 1. 本文件目的

本文件收尾：

```text
P1-MVP-UX-OPS-2 Step 7A：Guided Final Payment Dialog Runtime
```

也就是車輛頁「收尾款」業務任務卡 runtime 的完成與 smoke 紀錄。

本文件也記錄同一 runtime commit 中完成的成交價修正：

```text
收訂金並保留時輸入成交價
收尾款時 read-only 顯示成交價 / 訂金 / 建議尾款
```

本文件只記錄完成狀態與驗證結果，不新增 runtime、不修改 schema、不改會計流程。

---

## 2. Runtime commit

Step 7A runtime commit：

```text
e8a25b5 feat: add guided final payment dialog
```

本次 runtime 修改檔案：

```text
used_car_erp/hooks.py
used_car_erp/public/js/guided_reservation_deposit_dialog.js
used_car_erp/public/js/guided_final_payment_dialog.js
used_car_erp/used_car_erp/doctype/used_car_vehicle/used_car_vehicle.js
used_car_erp/used_car_erp/services/vehicle_reservation_service.py
used_car_erp/used_car_erp/services/used_car_controlled_write_service.py
used_car_erp/used_car_erp/services/vehicle_money_flow_service.py
used_car_erp/used_car_erp/services/formal_submitted_sales_invoice_test_fixture_setup_service.py
used_car_erp/used_car_erp/services/test_vehicle_reservation_service.py
used_car_erp/used_car_erp/services/test_vehicle_money_flow_service.py
used_car_erp/used_car_erp/services/test_vehicle_reservation_active_status.py
used_car_erp/used_car_erp/services/test_used_car_controlled_write_adoption.py
used_car_erp/used_car_erp/services/test_used_car_action_gate_adoption.py
```

---

## 3. Runtime 行為

### 3.1 Shared Dialog

新增 shared namespace：

```text
used_car_erp.guided_final_payment.open(frm)
```

用途：

```text
讓車輛頁用業務任務卡方式完成「收尾款」
```

### 3.2 車輛頁入口

車輛頁保留中流程的尾款入口已改為：

```text
收尾款
```

當車輛符合條件時顯示：

```text
車輛已儲存
車輛狀態 = 保留中
存在有效保留單
尚未建立尾款
```

按下後開啟：

```text
used_car_erp.guided_final_payment.open(frm)
```

若元件尚未載入，顯示 fallback：

```text
收尾款元件尚未載入，請重新整理後再試。
```

### 3.3 Dialog 欄位

Dialog 顯示 read-only 摘要：

```text
車輛資訊
客戶資訊
訂金資訊
成交價
訂金
建議尾款
```

Dialog 只收集尾款相關業務事實：

```text
尾款金額
付款方式
尾款日期
付款備註 / 末五碼
備註
```

尾款金額可預設為：

```text
建議尾款 = 成交價 - 訂金
```

但不強制尾款金額等於建議尾款，保留實務上的折讓、補收或貸款差異空間。

### 3.4 Backend call

Dialog 呼叫既有 method：

```text
used_car_erp.used_car_erp.services.vehicle_reservation_service.create_final_payment_for_active_reservation
```

傳入：

```text
vehicle_name
amount
payment_method
payment_date
payment_reference
notes
```

不傳：

```text
customer
sold_price
sales_staff
delivery fields
Sales Invoice fields
Journal Entry fields
```

### 3.5 成功後行為

成功後固定顯示業務訊息：

```text
已收尾款
```

成功後：

```text
frm.reload_doc()
車輛狀態仍為 保留中
「收尾款」不重複顯示
```

業務 UI 不顯示 backend 技術 message，不跳轉任何底層文件。

---

## 4. 成交價修正

本次 runtime commit 同時修正保留流程的成交價基準。

### 4.1 收訂金並保留

「收訂金並保留」Dialog 新增必填欄位：

```text
成交價
```

送出前驗證：

```text
成交價必須大於 0
訂金必須大於 0
訂金不可大於成交價
```

業務錯誤提示：

```text
成交價必須大於 0。
訂金不能大於成交價。
```

### 4.2 Backend write

`VehicleReservationService.create_reservation` 新增 `sold_price` 必填參數。

建立保留時同步寫入：

```text
Used Car Vehicle.status = 保留中
Used Car Vehicle.sold_price = 成交價
```

此寫入沿用 controlled write 邊界。

### 4.3 Controlled write 邊界

controlled write allowlist 僅開放：

```text
used_car_reservation.create → Used Car Vehicle.sold_price
```

未開放：

```text
sales_staff
delivery_date
Sales Invoice
Journal Entry
formal delivery fields
accounting fields
```

---

## 5. 底層沿用行為

Step 7A 沿用既有 reservation / money flow / voucher foundation。

底層仍會：

```text
建立 Used Car Money Flow：尾款收款
建立 Used Car Voucher Draft
Used Car Reservation 回寫 final_payment_* 欄位
Used Car Reservation 回寫 final_money_flow / final_voucher_draft
```

但這些底層名稱不出現在業務 Dialog、成功訊息或任務卡文案。

本階段不建立：

```text
Journal Entry
Sales Invoice
Payment Entry
Stock Entry
Delivery Note
預收款沖轉
```

---

## 6. Browser smoke 結果

使用者已完成 Step 7A browser smoke，結果通過，並已將 runtime commit 推上 main。

確認項目：

```text
收訂金並保留 Dialog 可輸入成交價
成交價必填且必須大於 0
訂金不可大於成交價
成功後 status = 保留中
成功後 sold_price 已寫入
收尾款 Dialog 可開啟
收尾款 Dialog read-only 顯示成交價 / 訂金 / 建議尾款
尾款金額可預設為建議尾款
成功後顯示「已收尾款」
表單刷新後「收尾款」不重複顯示
```

業務 Dialog / 成功訊息已確認不使用下列技術字詞：

```text
Money Flow
Voucher Draft
Journal Entry
Sales Invoice
Payment Entry
Stock Entry
Delivery Note
金流紀錄
傳票草稿
正式會計傳票
會計科目
預收款沖轉
15-1
formal delivery
```

---

## 7. 驗證紀錄

Step 7A runtime 實作時已執行：

```text
git diff --check
python -m json.tool used_car_erp/used_car_erp/doctype/used_car_vehicle/used_car_vehicle.json
python -m compileall used_car_erp/hooks.py
python -m compileall used_car_erp/used_car_erp/services/vehicle_reservation_service.py
python -m compileall used_car_erp/used_car_erp/services/used_car_controlled_write_service.py
python -m compileall used_car_erp/used_car_erp/services/test_vehicle_reservation_service.py
python -m compileall used_car_erp/used_car_erp/services/test_vehicle_money_flow_service.py
```

Additional affected Python compile also passed for updated helper / fixture / test call sites.

結果：

```text
passed
```

未執行：

```text
bench migrate
```

原因：

```text
本任務未改 schema
```

未執行：

```text
bench restart
```

原因：

```text
本任務不需要重啟
```

未執行：

```text
JS lint
```

原因：

```text
app 根目錄沒有既有 package.json 或 JS lint 指令
```

未執行完整 Frappe tests：

```text
Full Frappe tests likely require bench site/runtime services; compile/static checks completed.
```

---

## 8. 產品邊界確認

本階段維持：

```text
業務歸業務
會計歸會計
```

「收尾款」是業務事實輸入，不是正式會計入帳。

Step 7A 不做：

```text
不新增 schema
不改 DocType JSON
不改 Workspace / Page
不改會計流程
不處理成交確認
不處理取消保留退款
不處理退訂金沖帳
不建立 Journal Entry
不建立 Sales Invoice
不建立 Payment Entry
不建立 Stock Entry
不建立 Delivery Note
不建立預收款沖轉
```

會計作業仍在會計頁處理底層文件與正式入帳。

---

## 9. 已知限制與後續問題

### 9.1 保留中狀態文案

保留中後續狀態文案仍可能顯示既有技術語意，例如：

```text
傳票草稿
已記錄金流
等待會計確認訂金與尾款傳票
```

這不是 Step 7A 的 blocking issue，因為 Step 7A 只處理「保留中 → 收尾款」。

後續可另開：

```text
P1-MVP-UX-OPS-2 Step 7B：Reserved Vehicle Status Copy Polish
```

### 9.2 取消保留 / 退訂金沖帳

目前發現產品問題：

```text
若取消保留，既有訂金草稿仍會留在會計作業端。
```

正確方向不應在 Step 7A 直接混修，而應另開獨立規格：

```text
P1-MVP-UX-OPS-2 Step 8：Guided Reservation Cancellation / Deposit Refund Spec
```

該任務需定義：

```text
取消原因
是否退訂金
退訂金金額
退款方式
退款日期
付款備註
草稿未入帳時的處理
訂金已入帳時的退款 / 沖帳處理
是否允許已收尾款後取消
```

---

## 10. 目前穩定狀態

目前可視為：

```text
P1-MVP-UX-OPS-2 Step 7 completed
P1-MVP-UX-OPS-2 Step 7A completed
```

也就是：

```text
收尾款任務卡規格已完成
Guided Final Payment Dialog runtime 已完成
成交價 patch 已完成
browser smoke passed
main 已 push
working tree clean
```

---

## 11. 下一步建議

下一步建議二選一。

### 方向 A：先處理取消保留 / 退訂金

```text
P1-MVP-UX-OPS-2 Step 8：Guided Reservation Cancellation / Deposit Refund Spec
```

適合情境：

```text
要補上取消保留後的訂金草稿 / 已入帳訂金處理
要避免會計作業端殘留不符合業務狀態的待處理資料
要把取消保留改為有業務輸入與會計邊界的正式任務卡
```

### 方向 B：先進確認成交任務卡

```text
P1-MVP-UX-OPS-2 Step 8：Guided Sale Completion Task Card Spec
```

適合情境：

```text
要先把 保留中 → 已售出 的業務主流程跑完
訂金 / 尾款已收後進入成交確認
```

目前建議優先方向：

```text
Guided Reservation Cancellation / Deposit Refund Spec
```

原因：取消保留已被確認會影響會計作業端資料一致性，應先定義處理邊界，再繼續擴成交閉環。

---

## 12. 建議 commit message

```text
docs: close guided final payment smoke
```

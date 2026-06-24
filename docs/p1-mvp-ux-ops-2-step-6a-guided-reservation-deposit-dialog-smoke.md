# P1-MVP-UX-OPS-2 Step 6A：Guided Reservation / Deposit Dialog Smoke Close

日期：2026-06-25  
專案：Used Car ERP / ERPNext / Frappe  
Repo：`ericzhan0819/used_car_erp`  
前置規格穩定點：`c09e046 docs: define reservation deposit spec`

---

## 1. 本文件目的

本文件收尾：

```text
P1-MVP-UX-OPS-2 Step 6A：Guided Reservation / Deposit Dialog Runtime
```

也就是車輛頁「收訂金並保留」業務任務卡 runtime 的完成與 smoke 紀錄。

本文件只記錄完成狀態與驗證結果，不新增 runtime、不修改 schema、不改會計流程。

---

## 2. Runtime commit

Step 6A runtime commit：

```text
990dab7 feat: add guided reservation deposit dialog
```

本次 runtime 修改檔案：

```text
used_car_erp/public/js/guided_reservation_deposit_dialog.js
used_car_erp/used_car_erp/doctype/used_car_vehicle/used_car_vehicle.js
used_car_erp/hooks.py
```

---

## 3. Runtime 行為

### 3.1 Shared Dialog

新增 shared namespace：

```text
used_car_erp.guided_reservation_deposit.open(frm)
```

用途：

```text
讓車輛頁用業務任務卡方式完成「收訂金並保留」
```

### 3.2 車輛頁入口

車輛頁原本的：

```text
建立訂金保留
```

已改為：

```text
收訂金並保留
```

當車輛符合條件時顯示：

```text
車輛已儲存
車輛已入庫
車輛狀態 = 上架中
```

按下後開啟：

```text
used_car_erp.guided_reservation_deposit.open(frm)
```

若元件尚未載入，顯示 fallback：

```text
收訂金並保留元件尚未載入，請重新整理後再試。
```

### 3.3 Dialog 欄位

Dialog 只收集業務事實：

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

本階段沒有加入：

```text
既有客戶
成交價
銷售人員
尾款
交車日期
```

原因：Step 6A 初版只處理「收訂金並保留」。成交價 / 銷售人員牽涉 Vehicle controlled write，尾款與交車屬於後續任務卡。

### 3.4 Backend call

Dialog 呼叫既有 method：

```text
used_car_erp.used_car_erp.services.vehicle_reservation_service.create_reservation
```

傳入：

```text
vehicle_name
customer_name
customer_phone
deposit_amount
payment_method
deposit_date
payment_reference
notes
```

不傳：

```text
customer
sold_price
sales_staff
final_payment
delivery fields
```

### 3.5 成功後行為

成功後固定顯示業務訊息：

```text
已收訂金，車輛已保留
```

成功後：

```text
frm.reload_doc()
車輛狀態進入 保留中
```

業務 UI 不顯示 backend 技術 message，不跳轉任何底層文件。

---

## 4. 底層沿用行為

Step 6A 沿用既有 reservation / money flow / voucher foundation。

底層仍會：

```text
建立 Used Car Reservation
建立 Used Car Money Flow：訂金收款
建立 Used Car Voucher Draft
Vehicle status = 保留中
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

## 5. Browser smoke 結果

使用者已完成 Step 6A browser smoke，結果通過，並已將 runtime commit 推上 main。

確認項目：

```text
車輛狀態為 上架中 時，頁面顯示「收訂金並保留」
點擊後可開啟 Dialog
Dialog 只顯示業務欄位
送出後顯示「已收訂金，車輛已保留」
表單刷新後 status = 保留中
```

業務 Dialog / 成功訊息已確認不使用下列技術字詞：

```text
Money Flow
Voucher Draft
Journal Entry
Sales Invoice
Payment Entry
Stock Entry
金流紀錄
傳票草稿
正式會計傳票
會計科目
預收款沖轉
15-1
formal delivery
```

---

## 6. 驗證紀錄

Step 6A runtime 實作時已執行：

```text
git diff --check
python -m json.tool used_car_erp/used_car_erp/doctype/used_car_vehicle/used_car_vehicle.json
python -m compileall used_car_erp/hooks.py
```

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
app 根目錄沒有確認可用的既有 package.json 或 JS lint 指令
```

---

## 7. 產品邊界確認

本階段維持：

```text
業務歸業務
會計歸會計
```

「收訂金並保留」是業務事實輸入，不是正式會計入帳。

Step 6A 不做：

```text
不改 Python service
不改 DocType JSON
不新增 schema
不改 Workspace / Page
不改會計流程
不改權限
不處理尾款
不處理成交
不處理 Sales Invoice
不處理 Journal Entry
不處理 Payment Entry
不處理 Stock Entry
```

會計作業仍在會計頁處理底層文件與正式入帳。

---

## 8. 已知限制

保留中後續狀態文案仍可能顯示既有技術語意，例如：

```text
傳票草稿
已記錄金流
等待會計確認訂金與尾款傳票
```

這不是 Step 6A 的 blocking issue，因為 Step 6A 只處理「上架中 → 收訂金並保留 → 保留中」。

後續建議另開：

```text
P1-MVP-UX-OPS-2 Step 6B：Reserved Vehicle Status Copy Polish
```

或在尾款任務卡階段一起整理保留中狀態文案。

---

## 9. 目前穩定狀態

目前可視為：

```text
P1-MVP-UX-OPS-2 Step 6 completed
P1-MVP-UX-OPS-2 Step 6A completed
```

也就是：

```text
收訂金並保留任務卡規格已完成
Guided Reservation / Deposit Dialog runtime 已完成
browser smoke passed
main 已 push
working tree clean
```

---

## 10. 下一步建議

下一步有兩個合理方向：

### 方向 A：先整理保留中狀態文案

```text
P1-MVP-UX-OPS-2 Step 6B：Reserved Vehicle Status Copy Polish
```

適合情境：

```text
要把保留中 dashboard 的技術字詞降噪
要讓業務只看到「訂金已記錄 / 尾款尚未收 / 內部處理中」等業務語意
要在進尾款任務卡前先清理保留中頁面
```

### 方向 B：進下一張任務卡

```text
P1-MVP-UX-OPS-2 Step 7：Guided Final Payment Task Card Spec
```

適合情境：

```text
先推完整業務主流程
進入收尾款任務卡規格
繼續保持一張卡處理一件事
```

若目前要快速串完整 MVP，建議進 Step 7 規格；若要避免保留中頁面出現技術字詞，則先做 Step 6B。

---

## 11. 建議 commit message

```text
docs: close guided reservation deposit smoke
```

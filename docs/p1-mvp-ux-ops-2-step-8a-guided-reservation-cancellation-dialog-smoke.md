# P1-MVP-UX-OPS-2 Step 8A：Guided Reservation Cancellation Dialog Smoke Close

日期：2026-06-25  
專案：Used Car ERP / ERPNext / Frappe  
Repo：`ericzhan0819/used_car_erp`  
前置規格穩定點：`a0595b1 docs: define reservation cancellation refund spec`

---

## 1. 本文件目的

本文件收尾：

```text
P1-MVP-UX-OPS-2 Step 8A：Guided Reservation Cancellation Dialog Runtime
```

也就是車輛頁「取消保留 / 處理訂金」業務任務卡 runtime 的完成與 smoke 紀錄。

本文件只記錄完成狀態、驗證結果與已知 warning，不新增 runtime、不修改 schema、不改會計流程。

---

## 2. Runtime commit

Step 8A runtime commit：

```text
847a2aa feat: add guided reservation cancellation dialog
```

Push result：

```text
done
```

Final git status after runtime commit：

```text
clean
```

---

## 3. Runtime 修改檔案

```text
used_car_erp/public/js/guided_reservation_cancellation_dialog.js
used_car_erp/hooks.py
used_car_erp/used_car_erp/doctype/used_car_vehicle/used_car_vehicle.js
used_car_erp/used_car_erp/services/vehicle_reservation_service.py
used_car_erp/used_car_erp/services/vehicle_money_flow_service.py
used_car_erp/used_car_erp/services/vehicle_voucher_service.py
used_car_erp/used_car_erp/services/used_car_controlled_write_service.py
used_car_erp/used_car_erp/services/used_car_action_permission_service.py
used_car_erp/used_car_erp/services/test_vehicle_reservation_service.py
used_car_erp/used_car_erp/services/test_vehicle_money_flow_service.py
used_car_erp/used_car_erp/services/test_used_car_controlled_write_service.py
used_car_erp/used_car_erp/services/test_used_car_action_permission_service.py
```

---

## 4. Runtime 行為

### 4.1 Shared Dialog

新增 shared namespace：

```text
used_car_erp.guided_reservation_cancellation.open(frm)
```

用途：

```text
讓車輛頁用業務任務卡方式完成「取消保留 / 處理訂金」
```

Dialog 標題：

```text
取消保留 / 處理訂金
```

### 4.2 車輛頁入口

車輛頁「取消保留」按鈕已改為呼叫 shared guided Dialog。

若元件尚未載入，顯示 fallback：

```text
取消保留元件尚未載入，請重新整理後再試。
```

### 4.3 Dialog 顯示內容

Dialog read-only 顯示：

```text
車輛資訊
客戶資訊
成交價
訂金金額
訂金狀態
尾款狀態
```

Dialog 必填：

```text
取消原因
```

若訂金已入帳且尚未收尾款，額外顯示：

```text
退款金額
退款方式
退款日期
付款備註 / 末五碼
退款備註
```

MVP 初版退款金額固定全額退訂金，不支援部分退款。

---

## 5. Backend 行為

新增 / 更新服務能力：

```text
VehicleReservationService.cancel_active_reservation_with_deposit_handling
VehicleMoneyFlowService.create_deposit_refund_money_flow_from_reservation
VehicleVoucherService.create_deposit_refund_voucher_draft_from_money_flow_service
```

新增 action gate / controlled write allowlist：

```text
used_car_reservation.cancel_with_deposit_handling
used_car_money_flow.deposit_refund.create
```

---

## 6. 支援情境

### 6.1 訂金尚未入帳

行為：

```text
取消保留
車輛回到 上架中
訂金待處理資料作廢
不建立退款資料
不建立 Journal Entry
```

成功訊息：

```text
已取消保留
```

### 6.2 訂金已入帳且尚未收尾款

行為：

```text
取消保留
車輛回到 上架中
建立全額退款待內部確認資料
不直接建立 Journal Entry
```

成功訊息：

```text
已取消保留，訂金退款待內部確認
```

### 6.3 已建立尾款

行為：

```text
禁止取消
```

業務語意錯誤：

```text
此車已記錄尾款，請先由管理者或會計處理後再取消。
```

---

## 7. 本階段明確不支援

```text
部分退款
沒收訂金
已收尾款後取消
已完成成交後取消
直接建立 Journal Entry
直接建立 Sales Invoice
直接提交會計文件
新增 schema
修改 DocType JSON
```

---

## 8. Browser smoke 結果

使用者已完成 Step 8A browser smoke，結果通過，並已將 runtime commit 推上 main。

確認項目：

```text
未入帳訂金取消 OK
已入帳訂金取消 + 全額退款待內部確認 OK
已建立尾款禁止取消 OK
成功 / 錯誤提示使用業務語意
車輛狀態可依情境回到 上架中 或維持 保留中
runtime commit 後 working tree clean
```

---

## 9. 驗證紀錄

Step 8A runtime 實作時已執行：

```text
git diff --check
python -m json.tool requested DocType JSON files
python -m compileall changed services / hooks / updated tests
```

結果：

```text
passed
```

Frappe targeted tests 嘗試執行，但被 site test mode 阻擋：

```text
allow_tests true required
```

未修改 site config。

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
無明確重啟需求
```

未執行：

```text
JS lint
```

原因：

```text
app 根目錄沒有已確認可用的 JS lint 指令
```

---

## 10. UI 禁止字詞檢查

Step 8A Dialog、成功訊息、錯誤提示不應出現：

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

會計作業頁與內部技術文件可保留底層術語。

---

## 11. 已知 warning：advance account Journal Entry

使用者在會計作業按入帳時觀察到 ERPNext warning：

```text
Making Journal Entries against advance accounts: {'0202136 - 預收款項 - O'} is not recommended. These Journals won't be available for Reconciliation.
```

此 warning 不是 Step 8A 的業務任務卡錯誤，而是會計層設計提示。

目前 MVP 設計仍是：

```text
Used Car Voucher Draft → 會計確認 → Journal Entry
```

若 Journal Entry 可成功建立並提交，則此 warning 可視為非阻擋 warning，先記錄為後續會計 polish。

後續追蹤文件：

```text
docs/p1-mvp-acc-polish-advance-account-journal-entry-warning.md
```

---

## 12. 目前穩定狀態

目前可視為：

```text
P1-MVP-UX-OPS-2 Step 8 completed
P1-MVP-UX-OPS-2 Step 8A completed
```

也就是：

```text
取消保留 / 處理訂金規格已完成
Guided Reservation Cancellation Dialog runtime 已完成
browser smoke passed
main 已 push
working tree clean
advance account Journal Entry warning 已記錄為後續 polish
```

---

## 13. 下一步建議

下一步建議先做文件 / 會計流程討論，不急著改 runtime：

```text
P1-MVP-ACC-POLISH：Advance Account Journal Entry Warning
```

可選方向：

```text
A. MVP 維持 Journal Entry，但改用非 advance 類型暫收科目
B. 中長期改用 ERPNext 原生 Payment Entry / Payment Reconciliation
```

目前短期建議：

```text
先記錄，不阻擋 MVP；後續若 warning 影響實際入帳或對帳，再啟動 ACC polish。
```

---

## 14. 建議 commit message

```text
docs: close guided reservation cancellation smoke
```

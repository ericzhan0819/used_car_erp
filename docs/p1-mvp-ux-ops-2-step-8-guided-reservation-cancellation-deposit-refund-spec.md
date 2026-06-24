# P1-MVP-UX-OPS-2 Step 8：Guided Reservation Cancellation / Deposit Refund Spec

日期：2026-06-25  
專案：Used Car ERP / ERPNext / Frappe  
Repo：`ericzhan0819/used_car_erp`  
前置穩定點：`bd8c4b6 docs: close guided final payment smoke`

---

## 1. 本階段目的

本文件定義下一張業務任務卡：

```text
取消保留 / 處理訂金
```

目標是修正目前取消保留後的資料一致性問題：

```text
業務按下取消保留後，車輛會回到上架中，但既有訂金草稿 / 訂金收款資料仍可能留在會計作業端。
```

Step 8 應先定義取消保留、訂金退回、草稿作廢與會計邊界，再進入 runtime。

本階段是盤點與規格文件，不做 runtime。

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

## 2. 盤點檔案

本次已盤點：

```text
used_car_erp/used_car_erp/services/vehicle_reservation_service.py
used_car_erp/used_car_erp/services/vehicle_money_flow_service.py
used_car_erp/used_car_erp/services/vehicle_voucher_service.py
used_car_erp/used_car_erp/services/used_car_controlled_write_service.py
used_car_erp/used_car_erp/doctype/used_car_reservation/used_car_reservation.json
used_car_erp/used_car_erp/doctype/used_car_money_flow/used_car_money_flow.json
used_car_erp/used_car_erp/doctype/used_car_voucher_draft/used_car_voucher_draft.json
used_car_erp/used_car_erp/doctype/used_car_vehicle/used_car_vehicle.js
```

---

## 3. 現有取消保留行為盤點

目前取消保留由以下 service 處理：

```text
VehicleReservationService.cancel_active_reservation_for_vehicle
VehicleReservationService.cancel_reservation
```

現有流程：

```text
1. 找到 vehicle + status = 有效 的 Used Car Reservation
2. 將 Used Car Reservation.status 改為 已取消
3. 寫入 cancellation_reason / cancelled_at / cancelled_by
4. 若車輛 status = 保留中，將 Used Car Vehicle.status 改回 上架中
5. commit
```

現有取消保留會寫入：

```text
Used Car Reservation.status
Used Car Reservation.cancellation_reason
Used Car Reservation.cancelled_at
Used Car Reservation.cancelled_by
Used Car Vehicle.status
```

現有取消保留不會處理：

```text
reservation.money_flow
reservation.voucher_draft
reservation.journal_entry
reservation.final_money_flow
reservation.final_voucher_draft
reservation.final_journal_entry
Used Car Money Flow.status
Used Car Voucher Draft.status
Journal Entry
退款 Money Flow
退款 Voucher Draft
```

因此目前問題成立：

```text
業務狀態已取消，車輛已回上架中，但會計作業端可能仍有訂金待審核草稿或已入帳紀錄。
```

---

## 4. 現有訂金資料流盤點

目前訂金建立流程：

```text
VehicleReservationService.create_reservation
→ VehicleMoneyFlowService.create_deposit_money_flow_from_reservation
→ VehicleVoucherService.create_deposit_voucher_draft_from_money_flow_service
```

建立結果：

```text
Used Car Reservation.status = 有效
Used Car Reservation.money_flow = 訂金 Money Flow
Used Car Reservation.voucher_draft = 訂金 Voucher Draft
Used Car Money Flow.flow_type = 訂金收款
Used Car Money Flow.direction = 收入
Used Car Money Flow.status = 待審核
Used Car Voucher Draft.status = 待審核
Used Car Vehicle.status = 保留中
```

會計確認流程：

```text
VehicleVoucherService.confirm_voucher_draft
```

確認後：

```text
建立並 submit Journal Entry
Used Car Voucher Draft.status = 已入帳
Used Car Voucher Draft.journal_entry = Journal Entry
Used Car Money Flow.status = 已入帳
Used Car Money Flow.journal_entry = Journal Entry
Used Car Reservation.journal_entry = Journal Entry
```

可判斷訂金是否已入帳的條件：

```text
reservation.journal_entry 存在
或 voucher_draft.journal_entry 存在
或 money_flow.journal_entry 存在
或 money_flow.status = 已入帳
或 voucher_draft.status = 已入帳
```

---

## 5. 現有尾款資料流盤點

目前尾款建立流程：

```text
VehicleReservationService.create_final_payment_for_active_reservation
→ VehicleMoneyFlowService.create_final_payment_money_flow_from_reservation
→ VehicleVoucherService.create_final_payment_voucher_draft_from_money_flow_service
```

建立結果：

```text
Used Car Money Flow.flow_type = 尾款收款
Used Car Money Flow.direction = 收入
Used Car Money Flow.status = 待審核
Used Car Voucher Draft.status = 待審核
Used Car Reservation.final_payment_amount
Used Car Reservation.final_payment_date
Used Car Reservation.final_payment_method
Used Car Reservation.final_payment_reference
Used Car Reservation.final_payment_notes
Used Car Reservation.final_money_flow
Used Car Reservation.final_voucher_draft
```

會計確認後：

```text
Used Car Reservation.final_journal_entry = Journal Entry
Used Car Money Flow.status = 已入帳
Used Car Voucher Draft.status = 已入帳
```

目前取消保留不檢查 final_money_flow / final_voucher_draft / final_journal_entry，因此：

```text
已建立尾款後仍可能被取消保留
取消後尾款資料也不會被作廢或退款
```

MVP 初版應先禁止「已建立尾款後取消保留」，避免退款範圍瞬間擴大。

---

## 6. 現有退款承載能力盤點

### 6.1 Used Car Money Flow

`Used Car Money Flow.flow_type` 目前已有：

```text
退款
```

`Used Car Money Flow.direction` 支援：

```text
收入
支出
```

且已具備：

```text
vehicle
reservation
customer
customer_name
customer_phone
amount
payment_date
payment_method
payment_reference
evidence_attachment
notes
voucher_draft
journal_entry
```

因此 DocType 初版可承載退款資料，不一定需要 schema change。

但目前缺少專用語意：

```text
訂金退款
```

MVP 初版可二選一：

```text
A. 使用既有 flow_type = 退款，notes / memo 標示訂金退款
B. 新增 flow_type = 訂金退款
```

建議 MVP 初版先使用既有：

```text
flow_type = 退款
direction = 支出
```

理由：

```text
避免 schema change
先建立可用流程
後續若報表需要更細分類，再新增 flow_type
```

### 6.2 Used Car Voucher Draft

`Used Car Voucher Draft` 已可承載：

```text
money_flow
vehicle
reservation
customer
memo
lines
journal_entry
status
```

欄位本身足夠承載退款草稿。

但 `VehicleVoucherService` 目前只有：

```text
create_deposit_voucher_draft
create_final_payment_voucher_draft
create_general_expense_voucher_draft
confirm_voucher_draft
reject_voucher_draft
void_voucher_draft
```

目前沒有：

```text
create_deposit_refund_voucher_draft
create_refund_voucher_draft
```

因此 Step 8A runtime 若要支援已入帳訂金退款，應新增專用退款 voucher draft 建立函式。

---

## 7. 現有作廢能力盤點

`VehicleVoucherService.void_voucher_draft` 已支援：

```text
只允許 status = 待審核 或 已退回
若 draft.journal_entry 存在則不可作廢
作廢 draft.status = 已作廢
作廢 linked money_flow.status = 已作廢
```

這可支援「訂金草稿尚未入帳時取消保留」的資料清理方向。

但目前 `cancel_reservation` 沒有呼叫 `void_voucher_draft`，而且 `void_voucher_draft` 本身需要：

```text
used_car_voucher_draft.void
```

這是會計 / 草稿作廢權限，不一定適合由業務端直接觸發。

Step 8A 應定義 service-owned safe void 行為，而不是讓業務 UI 直接操作傳票草稿。

---

## 8. 情境矩陣

### A. 訂金草稿尚未入帳，取消保留

目前狀態：

```text
訂金 Money Flow.status = 待審核 或 已退回
訂金 Voucher Draft.status = 待審核 或 已退回
無 Journal Entry
```

建議 MVP 行為：

```text
取消保留
作廢訂金 Voucher Draft
作廢訂金 Money Flow
車輛回到 上架中
不建立退款 Money Flow
不建立 Journal Entry
```

理由：

```text
款項尚未正式入帳，會計端尚未建立正式 Journal Entry。
作廢待處理草稿即可避免會計作業端殘留。
```

### B. 訂金已入帳，取消保留且全額退訂金

目前狀態：

```text
訂金 Money Flow.status = 已入帳
訂金 Voucher Draft.status = 已入帳
訂金 Journal Entry 已存在
```

建議 MVP 行為：

```text
取消保留
建立退款 Money Flow：flow_type = 退款 / direction = 支出
建立退款 Voucher Draft
等待會計確認後建立正式 Journal Entry
車輛可先回到 上架中，但保留單需保留退款待確認狀態資訊
```

注意：若不新增 schema，退款 Money Flow / Voucher Draft 可透過 reservation 連回取消保留單。

### C. 訂金已入帳，取消保留但沒收訂金

這是會計與營業決策，不建議 MVP 初版支援。

可能需要：

```text
沒收訂金原因
沒收訂金金額
是否轉其他收入
會計科目判斷
```

MVP 建議：

```text
先不支援沒收訂金
若訂金已入帳，取消保留初版只支援全額退訂金
```

### D. 訂金已入帳，取消保留且部分退訂金

這也不建議 MVP 初版支援。

若要支援，需要：

```text
refund_amount
retained_deposit_amount
退款原因
沒收原因
會計分類
```

MVP 建議：

```text
先不支援部分退款
```

### E. 已建立尾款後取消保留

目前系統可建立尾款 Money Flow / Voucher Draft / Journal Entry，但取消保留不處理尾款。

MVP 建議：

```text
若 reservation.final_money_flow 或 reservation.final_voucher_draft 存在，禁止取消保留
提示：此車已記錄尾款，請先由管理者 / 會計處理後再取消。
```

理由：

```text
尾款後取消涉及全額退款、訂金與尾款合併退款、可能已成交前狀態、會計沖轉，範圍過大。
```

---

## 9. Step 8 MVP 建議範圍

Step 8 建議任務名稱：

```text
P1-MVP-UX-OPS-2 Step 8：Guided Reservation Cancellation / Deposit Refund Spec
```

任務卡名稱：

```text
取消保留 / 處理訂金
```

Step 8A runtime 建議拆成最小 MVP：

```text
P1-MVP-UX-OPS-2 Step 8A：Guided Reservation Cancellation Dialog Runtime
```

Step 8A MVP 支援：

```text
1. 無尾款的保留單才可取消
2. 若訂金尚未入帳：取消保留 + 作廢訂金待處理草稿 + 車輛回上架中
3. 若訂金已入帳：取消保留 + 建立全額退款待處理資料 + 車輛回上架中
4. 業務 UI 只顯示取消原因、是否退訂金、退款資訊
5. 會計端再確認正式入帳或退款
```

Step 8A MVP 不支援：

```text
部分退款
沒收訂金
已收尾款後取消
已完成成交後取消
直接建立 Journal Entry
直接建立 Sales Invoice
直接提交會計文件
```

---

## 10. 建議 Dialog 欄位

Dialog 標題：

```text
取消保留 / 處理訂金
```

Read-only 摘要：

```text
車輛資訊
客戶資訊
成交價
訂金金額
訂金狀態
尾款狀態
```

必填欄位：

```text
取消原因
```

若訂金尚未入帳：

```text
處理方式：取消保留，作廢尚未入帳的訂金資料
```

此時不顯示退款金額，因為尚未正式入帳。

若訂金已入帳且無尾款：

```text
是否退訂金：預設 是
退款金額：預設 訂金金額，初版唯讀或不可改
退款方式
退款日期
付款備註 / 末五碼
退款備註
```

MVP 初版退款金額建議固定全額：

```text
退款金額 = 訂金金額
```

---

## 11. 建議 backend service 切分

### 11.1 Reservation service

新增 / 改造：

```text
VehicleReservationService.cancel_active_reservation_with_deposit_handling
```

或擴充現有：

```text
VehicleReservationService.cancel_active_reservation_for_vehicle
```

建議新增新 method，避免破壞舊路徑，也讓 Step 8A 能明確區分新 guided behavior。

輸入：

```text
vehicle_name
reason
refund_deposit
refund_amount
refund_payment_method
refund_date
refund_reference
refund_notes
```

### 11.2 Money flow service

新增：

```text
VehicleMoneyFlowService.create_deposit_refund_money_flow_from_reservation
```

建立：

```text
Used Car Money Flow.flow_type = 退款
Used Car Money Flow.direction = 支出
Used Car Money Flow.status = 待審核
reservation = cancelled reservation
customer / customer_name / customer_phone copied from reservation
amount = refund_amount
payment_date = refund_date
payment_method = refund_payment_method
payment_reference = refund_reference
notes = refund_notes
```

### 11.3 Voucher service

新增：

```text
VehicleVoucherService.create_deposit_refund_voucher_draft_from_money_flow_service
```

會計分錄方向應為訂金收款反向概念，具體科目仍由會計在 Voucher Draft 確認。

不可直接：

```text
submit Journal Entry
```

---

## 12. 是否需要 schema change

### MVP 初版可不做 schema change

理由：

```text
Used Car Money Flow 已有 flow_type = 退款
Used Car Money Flow 已有 direction = 支出
Used Car Money Flow 已有 reservation link
Used Car Money Flow 已有 amount / payment_date / payment_method / payment_reference / evidence_attachment / notes
Used Car Voucher Draft 已有 money_flow / reservation / customer / lines
Used Car Reservation 已有 cancellation_reason / cancelled_at / cancelled_by
```

但不做 schema change 的限制是：

```text
Reservation 上不會有 refund_money_flow / refund_voucher_draft / refund_journal_entry 明確欄位
```

MVP 可接受做法：

```text
透過 reservation + flow_type = 退款 查詢退款 Money Flow
```

### 後續可能 schema change

若後續要更完整、報表更清楚，可新增：

```text
Used Car Reservation.refund_money_flow
Used Car Reservation.refund_voucher_draft
Used Car Reservation.refund_journal_entry
Used Car Reservation.refund_amount
Used Car Reservation.refund_status
```

但 Step 8A MVP 不建議先做，避免擴大 schema / migrate。

---

## 13. Controlled write 建議

Step 8A 若不做 schema change，仍需要 controlled write action。

建議新增 action：

```text
used_car_reservation.cancel_with_deposit_handling
```

允許：

```text
Used Car Reservation.status
Used Car Reservation.cancellation_reason
Used Car Reservation.cancelled_at
Used Car Reservation.cancelled_by
Used Car Vehicle.status
Used Car Money Flow.status          # 作廢未入帳訂金或建立退款資料
Used Car Money Flow.flow_type
Used Car Money Flow.direction
Used Car Money Flow.vehicle
Used Car Money Flow.reservation
Used Car Money Flow.stock_no
Used Car Money Flow.customer
Used Car Money Flow.customer_name
Used Car Money Flow.customer_phone
Used Car Money Flow.amount
Used Car Money Flow.payment_date
Used Car Money Flow.payment_method
Used Car Money Flow.payment_reference
Used Car Money Flow.notes
Used Car Money Flow.created_by_service
Used Car Money Flow.voucher_draft
Used Car Voucher Draft.status
Used Car Voucher Draft.posting_date
Used Car Voucher Draft.money_flow
Used Car Voucher Draft.vehicle
Used Car Voucher Draft.reservation
Used Car Voucher Draft.customer
Used Car Voucher Draft.memo
Used Car Voucher Draft.review_note
Used Car Voucher Draft.lines
```

不要開放：

```text
Sales Invoice
Journal Entry
Payment Entry
Stock Entry
Delivery Note
會計科目欄位直接給業務寫入
formal delivery fields
```

---

## 14. 業務 UI 禁止字詞

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

可使用業務語意：

```text
取消保留
處理訂金
退訂金
退款金額
退款方式
退款日期
內部處理中
已取消保留
訂金退款待內部確認
```

---

## 15. Step 8A runtime 建議

Step 8A 建議做最小 runtime：

```text
P1-MVP-UX-OPS-2 Step 8A：Guided Reservation Cancellation Dialog Runtime
```

允許範圍：

```text
新增 shared guided cancellation Dialog
車輛頁「取消保留」改為 shared Dialog
沿用 / 新增 backend cancellation service
未入帳訂金：作廢待處理資料
已入帳訂金：建立退款待處理資料
成功後顯示「已取消保留」或「已取消保留，訂金退款待內部確認」
成功後 reload_doc
```

建議新增檔案：

```text
used_car_erp/public/js/guided_reservation_cancellation_dialog.js
```

建議 namespace：

```text
used_car_erp.guided_reservation_cancellation.open(frm)
```

可修改檔案：

```text
used_car_erp/public/js/guided_reservation_cancellation_dialog.js
used_car_erp/used_car_erp/doctype/used_car_vehicle/used_car_vehicle.js
used_car_erp/hooks.py
used_car_erp/used_car_erp/services/vehicle_reservation_service.py
used_car_erp/used_car_erp/services/vehicle_money_flow_service.py
used_car_erp/used_car_erp/services/vehicle_voucher_service.py
used_car_erp/used_car_erp/services/used_car_controlled_write_service.py
相關 tests / fixtures
```

不做：

```text
不新增 schema
不改 DocType JSON
不處理部分退款
不處理沒收訂金
不處理已收尾款後取消
不處理已完成成交後取消
不直接建立 Journal Entry
不直接建立 Sales Invoice
不直接提交會計文件
```

---

## 16. Step 8A 驗收標準

### 情境 A：訂金未入帳

```text
1. 建立上架中車輛
2. 收訂金並保留
3. 不進會計確認
4. 點取消保留 / 處理訂金
5. 輸入取消原因
6. 送出後顯示「已取消保留」
7. 車輛 status = 上架中
8. Reservation status = 已取消
9. 訂金待處理資料不再出現在會計待處理清單
10. 不建立 Journal Entry
```

### 情境 B：訂金已入帳，全額退訂金

```text
1. 建立上架中車輛
2. 收訂金並保留
3. 會計確認訂金入帳
4. 點取消保留 / 處理訂金
5. 顯示退款金額 = 訂金金額
6. 輸入退款方式 / 退款日期 / 備註
7. 送出後顯示「已取消保留，訂金退款待內部確認」
8. 車輛 status = 上架中
9. Reservation status = 已取消
10. 建立退款待處理資料
11. 不直接建立 Journal Entry
```

### 禁止情境

```text
已建立尾款後取消 → 阻擋
已完成成交後取消 → 阻擋
部分退款 → 阻擋或不提供入口
沒收訂金 → 阻擋或不提供入口
```

---

## 17. 下一步

下一步建議：

```text
P1-MVP-UX-OPS-2 Step 8A：Guided Reservation Cancellation Dialog Runtime
```

Step 8A 開始前應先盤點：

```text
VehicleVoucherService.void_voucher_draft 是否能安全由 cancellation service 重用
退款 voucher draft 分錄方向
會計作業頁是否能列出 flow_type = 退款 的 Voucher Draft
action permission 是否需要新增 used_car_reservation.cancel_with_deposit_handling
controlled write allowlist 的最小欄位
現有 tests 中 create_reservation / cancel_reservation 的更新範圍
```

建議 runtime commit message：

```text
feat: add guided reservation cancellation dialog
```

本文件 commit message：

```text
docs: define reservation cancellation refund spec
```

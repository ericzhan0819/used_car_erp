# P1-MVP-OPS Step 3B-0：採購付款 Money Flow 規格

日期：2026-06-29  
專案：Used Car ERP / ERPNext / Frappe  
Repo：`ericzhan0819/used_car_erp`  
本機路徑：`~/frappe/frappe-bench/apps/used_car_erp`

---

## 1. 本文件目的

本文件定義：

```text
P1-MVP-OPS Step 3B：採購付款 Money Flow
```

目標是把「購車付款」納入 `Used Car Money Flow`，讓營運管理帳能追蹤：

```text
購車款金額
付款日期
付款方式
資金帳戶
交易對象
已付款 / 待付款 / 部分付款
```

本文件只做規格，不改 schema、不改 Python、不改 JS、不跑 migrate。

---

## 2. 背景

Step 3A 已完成最小資金帳戶 runtime：

```text
Used Car Cash Account
Money Flow.cash_account
Money Flow.settlement_status
Money Flow.counterparty_name
新增支出 / 訂金 / 尾款 / 退款資金欄位
車輛頁收支摘要資金欄位
```

但採購付款尚未成為獨立 Money Flow runtime。

目前 `Used Car Vehicle.purchase_price` 代表購車價與成本基礎，但不能回答資金何時、從哪個帳戶、付給誰。

---

## 3. 核心分工

```text
Used Car Vehicle.purchase_price = 購車價 / 成本基礎
Used Car Money Flow flow_type=購車付款 = 實際付款行為
```

`purchase_price` 繼續作為管理損益與 15-1 估算的購入基礎。  
`購車付款` Money Flow 只記錄現金 / 銀行 / 待付款等營運事實。

不得用購車付款 Money Flow 覆寫 `purchase_price`。  
不得把購車付款再算成一筆後續直接支出。

---

## 4. 最小資料語意

建議 Money Flow：

```text
flow_type = 購車付款
direction = 支出
status = 待審核
amount = 實際付款金額
payment_date = 付款日期或紀錄日期
payment_method = 現金 / 匯款 / 信用卡 / 其他
cash_account = 現金 / 主要銀行 / 其他
settlement_status = 已付款 / 待付款 / 部分付款
counterparty_name = 賣方 / 車主 / 同行 / 拍賣場 / 其他供應商
```

`status` 表示既有 Money Flow / Voucher Draft 處理狀態。  
`settlement_status` 表示營運收付狀態。

---

## 5. Runtime 建議拆分

```text
Step 3B-1：Purchase Payment service foundation
Step 3B-2：Guided Purchase Payment Dialog
Step 3B-3：Vehicle purchase payment summary polish
Step 3B-4：Browser smoke / handoff
```

---

## 6. Step 3B-1 建議

新增 service method：

```text
VehicleMoneyFlowService.create_purchase_payment_money_flow(...)
```

建議參數：

```text
vehicle
amount
payment_date
payment_method
payment_reference
notes
evidence_attachment
cash_account
settlement_status
counterparty_name
```

建議新增 controlled write action：

```text
used_car_money_flow.purchase_payment.create
```

目前 `Used Car Money Flow.flow_type` options 尚未包含 `購車付款`，runtime 階段應補上。

不建議把 `購車付款` 直接塞進一般支出 flow types。採購付款是 purchase_price 的付款行為，不是整備 / 維修 / 美容等後續支出。

---

## 7. Dialog 建議

業務端按鈕名稱：

```text
新增購車付款
```

Dialog 欄位：

```text
付款金額
付款日期
付款方式
收付狀態
資金帳戶
交易對象
付款備註 / 末五碼
憑證附件
備註
```

成功訊息：

```text
購車付款紀錄已建立。
```

業務端不得顯示：

```text
Money Flow
Voucher Draft
Journal Entry
會計科目
借方 / 貸方
Payment Entry
Reconciliation
```

---

## 8. Validation 建議

```text
vehicle 必填
amount 必須大於 0
payment_method 必須是現金 / 匯款 / 信用卡 / 其他
settlement_status 必須是已付款 / 待付款 / 部分付款
```

若 `settlement_status = 已付款`：

```text
cash_account 應必填或由 payment_method 推導
payment_date 未填可使用 nowdate()
```

若 `settlement_status = 待付款`：

```text
cash_account 可空白
payment_date 可表示預計付款日或紀錄日
```

允許多筆購車付款。  
付款合計小於 purchase_price 表示尚有待付款。  
付款合計大於 purchase_price 先做 warning，不在 MVP hard block。

---

## 9. 管理毛利邊界

管理毛利仍應維持：

```text
管理毛利 = 成交價 + 其他直接收入 - purchase_price - 後續直接支出
```

`flow_type = 購車付款` 不得被扣第二次。

原因：

```text
purchase_price 已代表購車成本。
購車付款只是該成本的付款紀錄。
```

---

## 10. 15-1 邊界

15-1 售車營業稅估算仍使用：

```text
purchase_price
```

不使用：

```text
購車付款 Money Flow 合計
整備 / 維修 / 美容 / 拍場 / 代辦等後續支出
```

---

## 11. 明確不做

```text
不做 Purchase Invoice
不做 Payment Entry
不做 Payment Reconciliation
不做 Journal Entry 重構
不處理 advance account warning
不做刷卡未撥款
不做私人代墊
不做多銀行管理 UI
不做月結批次付款
不做資金轉帳
不做完整應付帳款模組
不把會計術語加回業務頁
不把購車付款重複算進管理成本
```

---

## 12. 建議下一步

下一步：

```text
P1-MVP-OPS Step 3B-1：Purchase Payment service foundation
```

建議 commit message：

```text
feat: add purchase payment money flow service
```

---

## 13. 結論

Step 3B 的核心是補齊營運管理帳最大的支出流：

```text
購車付款進 Money Flow
cash_account 追蹤現金 / 銀行流出
settlement_status 追蹤已付款 / 待付款
purchase_price 繼續作為成本基礎
管理毛利不得重複扣購車付款
```

完成後，系統才能更可靠回答：

```text
這台車買進成本是多少？
購車款實際付了多少？
現金 / 銀行少了多少？
還有多少購車款待付？
```
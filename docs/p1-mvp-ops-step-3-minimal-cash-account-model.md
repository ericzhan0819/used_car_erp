# P1-MVP-OPS Step 3：資金帳戶最小模型規格

日期：2026-06-25  
專案：Used Car ERP / ERPNext / Frappe  
Repo：`ericzhan0819/used_car_erp`  
本機路徑：`~/frappe/frappe-bench/apps/used_car_erp`  
前置文件：

```text

docs/p1-mvp-ops-used-car-operation-ledger-direction.md
docs/p1-mvp-ops-step-2-money-flow-ledger-field-audit.md
```

---

## 1. 本文件目的

本文件執行：

```text
P1-MVP-OPS Step 3：資金帳戶最小模型規格
```

目標是定義 P1-MVP-OPS 的最小資金帳戶模型，作為後續 Step 3A runtime 的依據。

本文件只做規格，不改 schema、不新增 DocType、不改 runtime、不跑 migrate。

---

## 2. 已確認決策

本階段採用以下已確認決策。

### 2.1 採購付款要進 Money Flow

`purchase_price` 仍代表購車價，是單車購入成本與 15-1 售車營業稅估算基礎。

但實際付款行為也要進 `Used Car Money Flow`。

也就是：

```text
Used Car Vehicle.purchase_price = 這台車的購車價
Used Car Money Flow = 這筆購車款實際怎麼付、什麼時候付、從哪個資金帳戶付
```

後續新增或設計採購付款時，Money Flow 應支援：

```text
flow_type = 購車付款
direction = 支出
```

注意：

```text
購車付款進 Money Flow 不代表 purchase_price 被重新計算。
管理損益計算時必須避免 purchase_price 與購車付款重複扣成本。
```

---

### 2.2 待收款 / 待付款不作為資金帳戶

本階段不把以下項目放入 `Used Car Cash Account`：

```text
待收款
待付款
```

原因：

```text
待收款 / 待付款不是錢實際所在位置，而是收付狀態。
```

因此待收 / 待付應由 Money Flow 的營運結清狀態欄位表示。

建議欄位：

```text
settlement_status
```

---

### 2.3 資金帳戶需要期初餘額

若要讓 Dashboard 能顯示現金 / 銀行餘額，資金帳戶需要期初資料。

因此 `Used Car Cash Account` 最小模型應包含：

```text
opening_balance
opening_balance_date
```

Dashboard 餘額概念：

```text
目前餘額 = 期初餘額 + 期初日後已收款收入 - 期初日後已付款支出
```

---

### 2.4 不建立私人代墊資金帳戶

本階段不建立：

```text
老闆代墊
私人代墊
```

原因：

```text
MVP 先避免把私人資金與公司營運帳混在一起。
```

若實務上維修廠、代辦、拍場或配合廠商採月結 / 簽帳，應以 `settlement_status = 待付款` 表示。

例如：

```text
flow_type = 維修支出
direction = 支出
amount = 5000
counterparty_name = XX維修廠
settlement_status = 待付款
cash_account = 空白
```

月底付款時，再把該筆或相關付款紀錄標為：

```text
settlement_status = 已付款
cash_account = 主要銀行
payment_method = 匯款
```

---

### 2.5 初期不做刷卡 / 刷卡未撥款

本階段不設計：

```text
刷卡未撥款
信用卡收款撥款確認
刷卡手續費
```

原因：

```text
MVP 先處理現金與主要銀行即可。
```

若未來需要刷卡，可另開新階段補：

```text
card_receivable_account
card_settlement_flow
card_fee
card_payout_to_bank
```

---

## 3. 核心語意分工

### 3.1 payment_method

`payment_method` 表示收付方式。

範例：

```text
現金
匯款
其他
```

它回答：

```text
這筆錢用什麼方式收 / 付？
```

它不回答：

```text
錢在哪個資金帳戶？
```

---

### 3.2 cash_account

`cash_account` 表示錢實際進出哪個資金帳戶。

範例：

```text
現金
主要銀行
其他
```

它回答：

```text
這筆錢進出哪裡？
```

例如：

```text
payment_method = 匯款
cash_account = 主要銀行
```

或：

```text
payment_method = 現金
cash_account = 現金
```

---

### 3.3 settlement_status

`settlement_status` 表示這筆 Money Flow 的營運收付狀態。

它回答：

```text
這筆錢實際收了嗎？付了嗎？還是待收 / 待付？
```

建議 options：

```text
待收款
已收款
部分收款
待付款
已付款
部分付款
不需收付
已取消
```

`settlement_status` 與現有 `status` 分工如下：

| 欄位 | 語意 | 範例 |
| --- | --- | --- |
| `status` | 既有會計 / 草稿處理狀態 | 待審核、已入帳、已作廢 |
| `settlement_status` | 營運收付狀態 | 待付款、已付款、待收款、已收款 |

不得把營運收付狀態硬塞進現有 `status`，避免破壞既有 Money Flow / Voucher Draft / Journal Entry 流程。

---

## 4. Used Car Cash Account 最小模型

建議新增 DocType：

```text
Used Car Cash Account
```

中文顯示可用：

```text
資金帳戶
```

### 4.1 欄位建議

| 欄位 | 類型 | 必填 | 說明 |
| --- | --- | --- | --- |
| `account_name` | Data | 是 | 帳戶名稱，例如：現金、主要銀行 |
| `account_type` | Select | 是 | 帳戶類型 |
| `is_default` | Check | 否 | 是否預設帳戶 |
| `opening_balance` | Currency | 否 | 期初餘額 |
| `opening_balance_date` | Date | 否 | 期初餘額日期 |
| `is_active` | Check | 是 | 是否啟用 |
| `sort_order` | Int | 否 | 顯示排序 |
| `notes` | Small Text | 否 | 備註 |

### 4.2 account_type options

最小 options：

```text
現金
銀行
其他
```

不包含：

```text
待收款
待付款
老闆代墊
刷卡未撥款
```

---

## 5. 初期預設資金帳戶

Step 3A runtime 若需要建立初始資料，初期只建立：

| account_name | account_type | 用途 |
| --- | --- | --- |
| 現金 | 現金 | 店內現金收付 |
| 主要銀行 | 銀行 | 公司主要銀行帳戶收付 |
| 其他 | 其他 | 暫時無法歸類的資金來源 / 去向 |

### 5.1 不建立待收 / 待付帳戶

待收 / 待付由 `settlement_status` 表示。

例如尾款尚未收：

```text
flow_type = 尾款收款
direction = 收入
amount = 100000
settlement_status = 待收款
cash_account = 空白
```

收款後：

```text
settlement_status = 已收款
cash_account = 主要銀行
payment_method = 匯款
```

### 5.2 不建立老闆代墊帳戶

若廠商月結：

```text
flow_type = 維修支出
direction = 支出
settlement_status = 待付款
cash_account = 空白
```

付款後：

```text
settlement_status = 已付款
cash_account = 主要銀行
```

### 5.3 不建立刷卡未撥款帳戶

本階段不處理刷卡收款。

若實務發生刷卡，短期先用人工備註處理，不進 MVP 主流程。

---

## 6. Money Flow 欄位延伸建議

後續 Step 3A 若進入 runtime，建議在 `Used Car Money Flow` 補最小欄位：

| 欄位 | 類型 | 說明 |
| --- | --- | --- |
| `cash_account` | Link Used Car Cash Account | 實際進出資金帳戶 |
| `settlement_status` | Select | 營運收付狀態 |
| `counterparty_name` | Data | 通用交易對象，例如維修廠、賣方、買方、代辦、拍場 |

可暫不新增：

```text
evidence_status
document_type
tax_handling_status
accountant_handoff_status
affects_management_profit
linked_vehicle_cost
```

原因：

```text
Step 3A 應只處理資金帳戶最小 runtime。
憑證、稅務、交記帳士與 Vehicle Cost 整合應另拆後續階段。
```

---

## 7. flow_type 與資金帳戶分工

### 7.1 收款類

| flow_type | direction | settlement_status 預設 | cash_account 預設 |
| --- | --- | --- | --- |
| 訂金收款 | 收入 | 已收款 | 依 payment_method 決定，通常現金或主要銀行 |
| 尾款收款 | 收入 | 已收款 | 依 payment_method 決定，通常現金或主要銀行 |
| 貸款撥款 | 收入 | 待收款或已收款 | 收到時為主要銀行 |
| 其他 | 收入 | 已收款 | 依 payment_method 決定 |

### 7.2 支出類

| flow_type | direction | settlement_status 預設 | cash_account 預設 |
| --- | --- | --- | --- |
| 購車付款 | 支出 | 已付款或待付款 | 已付款時現金或主要銀行；待付款時空白 |
| 整備支出 | 支出 | 已付款或待付款 | 已付款時現金或主要銀行；待付款時空白 |
| 維修支出 | 支出 | 已付款或待付款 | 已付款時現金或主要銀行；待付款時空白 |
| 美容支出 | 支出 | 已付款或待付款 | 已付款時現金或主要銀行；待付款時空白 |
| 代辦支出 | 支出 | 已付款或待付款 | 已付款時現金或主要銀行；待付款時空白 |
| 拍場支出 | 支出 | 已付款或待付款 | 已付款時現金或主要銀行；待付款時空白 |
| 其他支出 | 支出 | 已付款或待付款 | 已付款時現金或主要銀行；待付款時空白 |
| 退款 | 支出 | 已付款或待付款 | 已付款時現金或主要銀行；待付款時空白 |

---

## 8. 範例情境

### 8.1 現金收訂金

```text
flow_type = 訂金收款
direction = 收入
amount = 30000
payment_method = 現金
cash_account = 現金
settlement_status = 已收款
```

### 8.2 匯款收尾款

```text
flow_type = 尾款收款
direction = 收入
amount = 270000
payment_method = 匯款
cash_account = 主要銀行
settlement_status = 已收款
payment_reference = 匯款末五碼
```

### 8.3 維修廠月結，尚未付款

```text
flow_type = 維修支出
direction = 支出
amount = 5000
counterparty_name = XX維修廠
payment_method = 其他
cash_account = 空白
settlement_status = 待付款
```

### 8.4 月底匯款支付維修費

```text
flow_type = 維修支出
direction = 支出
amount = 5000
counterparty_name = XX維修廠
payment_method = 匯款
cash_account = 主要銀行
settlement_status = 已付款
payment_reference = 匯款末五碼
```

### 8.5 購車款現金支付

```text
flow_type = 購車付款
direction = 支出
amount = 315000
payment_method = 現金
cash_account = 現金
settlement_status = 已付款
```

此筆不得在管理毛利中與 `Used Car Vehicle.purchase_price` 重複扣除。

---

## 9. Dashboard / Summary 計算方向

### 9.1 現金餘額

```text
現金餘額 = 現金帳戶期初餘額
+ 已收款且 cash_account = 現金 的收入
- 已付款且 cash_account = 現金 的支出
```

### 9.2 銀行餘額

```text
主要銀行餘額 = 主要銀行期初餘額
+ 已收款且 cash_account = 主要銀行 的收入
- 已付款且 cash_account = 主要銀行 的支出
```

### 9.3 待收款

```text
待收款 = direction = 收入 且 settlement_status in (待收款, 部分收款) 的未收金額
```

### 9.4 待付款

```text
待付款 = direction = 支出 且 settlement_status in (待付款, 部分付款) 的未付金額
```

本階段不設計部分收付金額欄位；若 Step 3A 不處理部分收付，部分收款 / 部分付款可先保留為 future option，不進最小 runtime。

---

## 10. 與現有會計流程的邊界

資金帳戶模型不取代 ERPNext 會計。

短期內：

```text
Money Flow.status 仍可由 Voucher Draft / Journal Entry 流程更新。
Money Flow.settlement_status 表示營運收付狀態。
Money Flow.cash_account 表示資金帳位置。
Journal Entry / Sales Invoice / Payment Entry 不再是 P1-MVP-OPS Step 3 驗收重點。
```

不得因為新增資金帳戶，而把以下項目加回業務頁：

```text
Journal Entry
Sales Invoice
Voucher Draft
Payment Entry
會計科目
借方 / 貸方
預收款沖轉
```

---

## 11. Step 3A runtime 建議範圍

下一階段若進入 runtime，建議名稱：

```text
P1-MVP-OPS Step 3A：Minimal Cash Account Runtime
```

建議做：

```text
新增 Used Car Cash Account DocType
新增 Money Flow.cash_account
新增 Money Flow.settlement_status
新增 Money Flow.counterparty_name
建立初始資金帳戶：現金、主要銀行、其他
更新新增支出 / 訂金 / 尾款 / 退款 / 採購付款的欄位接線
更新車輛頁收支摘要顯示資金帳戶與收付狀態
```

暫不做：

```text
刷卡未撥款
私人代墊
多銀行管理 UI
部分收付明細
資金轉帳
月結批次付款
Payment Entry / Reconciliation 重構
Money Flow 與 Vehicle Cost 整合
記帳士交接包
成交結案列印
```

---

## 12. 結論

P1-MVP-OPS Step 3 的資金帳戶模型確定為：

```text
cash_account 只表示真正資金位置：現金、主要銀行、其他。
待收款 / 待付款 不作為資金帳戶，而由 settlement_status 表示。
採購付款要進 Money Flow，但不得與 purchase_price 重複計入管理成本。
資金帳戶需要期初餘額與期初日期，否則 Dashboard 不能可靠顯示餘額。
本階段不做私人代墊，不做刷卡未撥款。
```

下一步建議：

```text
P1-MVP-OPS Step 3A：Minimal Cash Account Runtime
```

建議 commit message：

```text
feat: add minimal cash account model
```

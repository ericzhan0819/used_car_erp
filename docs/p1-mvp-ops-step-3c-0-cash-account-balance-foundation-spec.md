# P1-MVP-OPS Step 3C-0：Cash Account Balance Foundation Spec

日期：2026-06-30  
專案：Used Car ERP / ERPNext / Frappe  
Repo：`ericzhan0819/used_car_erp`  
本機路徑：`~/frappe/frappe-bench/apps/used_car_erp`  
Site：`erpnext-coa.test`

---

## 1. 本文件目的

本文件定義：

```text
P1-MVP-OPS Step 3C-0：Cash account balance foundation spec
```

本階段是 docs-only spec。

目標是定義 `Used Car Cash Account` 與 `Used Car Money Flow` 如何形成 read-only 資金帳戶餘額，供後續 service / dashboard / owner overview 使用。

本階段不實作 runtime，不新增 Dashboard，不新增正式會計流程。

---

## 2. 產品目標

老闆視角需要回答：

```text
現金還有多少？
主要銀行還有多少？
其他資金帳戶還有多少？
哪些款項已經實際收付？
哪些款項只是待收 / 待付，不能進資金餘額？
是否能從 Money Flow 回推資金帳戶餘額？
```

本階段先定義 read-only foundation，後續才進 runtime。

必須明確區分：

```text
資金帳戶餘額 = 實際資金位置餘額
單車損益 = 每台車賺賠
收支摘要 = 車輛交易明細 / 營運事實列表
正式會計帳 = ERPNext / 記帳士層
```

資金帳戶餘額不是單車損益，也不是正式會計科目餘額。

---

## 3. 現有資料模型盤點

### 3.1 Used Car Cash Account

目前 `Used Car Cash Account` 已存在，且 `autoname` 使用 `field:account_name`。

現有欄位：

| fieldname | label | fieldtype | 語意 |
|---|---|---|---|
| `account_name` | 帳戶名稱 | Data | 資金帳戶名稱，也是 naming 來源 |
| `account_type` | 帳戶類型 | Select | 現金 / 銀行 / 其他 |
| `is_default` | 預設帳戶 | Check | 是否為預設資金帳戶 |
| `opening_balance` | 期初餘額 | Currency | ERP 開始記帳時的帳戶實際餘額 |
| `opening_balance_date` | 期初日期 | Date | 期初餘額基準日 |
| `is_active` | 啟用 | Check | 是否啟用 |
| `sort_order` | 排序 | Int | 顯示排序 |
| `notes` | 備註 | Small Text | 內部備註 |

目前 `Used Car Cash Account` 已具備期初餘額欄位，因此 Step 3C-1 不需要新增期初餘額欄位，只需要確認是否符合 service 計算需求。

### 3.2 Used Car Money Flow

現有關鍵欄位：

| fieldname | label | fieldtype | 現有選項 / 語意 |
|---|---|---|---|
| `vehicle` | 車輛 | Link | 連到 `Used Car Vehicle` |
| `flow_type` | 金流類型 | Select | 訂金收款、尾款收款、貸款撥款、退款、其他、購車付款、整備支出、維修支出、美容支出、代辦支出、拍場支出、其他支出 |
| `direction` | 金流方向 | Select | 收入 / 支出 |
| `amount` | 金額 | Currency | 本筆金流金額 |
| `payment_date` | 付款日期 | Date | 收付日期 |
| `payment_method` | 付款方式 | Select | 現金 / 匯款 / 信用卡 / 其他 |
| `cash_account` | 資金帳戶 | Link | 連到 `Used Car Cash Account` |
| `settlement_status` | 收付狀態 | Select | 待收款、已收款、部分收款、待付款、已付款、部分付款、不需收付、已取消 |
| `counterparty_name` | 交易對象 | Data | 交易對象顯示名稱 |
| `status` | 金流狀態 | Select | 待審核 / 已入帳 / 已作廢 |
| `evidence_attachment` | 憑證附件 | Attach | 收據、發票、合約、付款截圖等交易憑證 |
| `voucher_draft` | 傳票草稿 | Link | 會計輔助連結，非業務頁入口 |
| `journal_entry` | 正式會計傳票 | Link | 會計輔助連結，非業務頁入口 |

---

## 4. 資金餘額最小計算公式

MVP read-only 計算公式：

```text
cash_account_balance =
  cash_account.opening_balance
  + included_money_flow_income_total
  - included_money_flow_expense_total
```

方向規則依現有 `Used Car Money Flow.direction`：

```text
收入 = 增加資金帳戶餘額
支出 = 減少資金帳戶餘額
```

最小納入規則：

```text
已作廢資料不進餘額
沒有 cash_account 的資料不進餘額
待付款 / 待收款不進實際資金餘額
已付款 / 已收款且有 cash_account 才能進實際資金餘額
部分付款 / 部分收款暫定依 amount 進實際資金餘額
不需收付 / 已取消不進實際資金餘額
```

---

## 5. Money Flow 是否進資金餘額規則

| 條件 | 是否進資金餘額 | 原因 |
|---|---:|---|
| `cash_account` 空白 | 否 | 無實際資金位置 |
| `status = 已作廢` | 否 | 作廢紀錄不影響餘額 |
| `settlement_status = 待付款` | 否 | 尚未實際付款 |
| `settlement_status = 待收款` | 否 | 尚未實際收款 |
| `settlement_status = 已付款` 且有 `cash_account` | 是 | 已實際付款，依 `direction` 加減 |
| `settlement_status = 已收款` 且有 `cash_account` | 是 | 已實際收款，依 `direction` 加減 |
| `settlement_status = 部分付款` 且有 `cash_account` | 暫定是 | 目前只有 `amount`，暫定代表本筆已實際付款金額 |
| `settlement_status = 部分收款` 且有 `cash_account` | 暫定是 | 目前只有 `amount`，暫定代表本筆已實際收款金額 |
| `settlement_status = 不需收付` | 否 | 不代表實際資金異動 |
| `settlement_status = 已取消` | 否 | 不代表有效資金異動 |
| `flow_type = 購車付款` 且 `settlement_status = 已付款 / 部分付款` | 是 | 採購款實際支出，依 `direction = 支出` 扣減 |
| `flow_type = 訂金收款` 且 `settlement_status = 已收款 / 部分收款` | 是 | 訂金實際收入，依 `direction = 收入` 增加 |
| `flow_type = 尾款收款` 且 `settlement_status = 已收款 / 部分收款` | 是 | 尾款實際收入，依 `direction = 收入` 增加 |
| `flow_type = 貸款撥款` 且 `settlement_status = 已收款 / 部分收款` | 是 | 撥款實際收入，依 `direction = 收入` 增加 |
| `flow_type = 退款` 且 `settlement_status = 已付款 / 部分付款` | 是 | 實際退款支出，依 `direction = 支出` 扣減 |
| 整備 / 維修 / 美容 / 代辦 / 拍場 / 其他支出 且 `settlement_status = 已付款 / 部分付款` | 是 | 實際支出，依 `direction = 支出` 扣減 |

注意：

```text
資金餘額計算以 direction 決定加減，不直接用 flow_type 推導加減。
flow_type 只用於理解業務類型與報表分類。
```

---

## 6. 部分付款 / 部分收款語意

目前 `Used Car Money Flow` 只有一個 `amount`，沒有 `total_amount` / `paid_amount` / `unpaid_amount` 分欄。

MVP 暫定：

```text
Money Flow.amount 代表本筆已記錄的收付金額。
若 settlement_status = 部分付款 且 cash_account 有值，該 amount 暫定視為本筆已實際付款金額，可進資金餘額。
若 settlement_status = 部分收款 且 cash_account 有值，該 amount 暫定視為本筆已實際收款金額，可進資金餘額。
真正未付 / 未收餘額應由後續付款紀錄或應收 / 應付摘要計算，不在本階段處理。
```

風險記錄：

```text
如果未來要記錄「總應付 100 萬，已付 30 萬」，需要新增 total_amount / paid_amount / unpaid_amount 或拆分 Money Flow 模型。
本階段不新增欄位。
```

因此 Step 3C read-only balance service 不應假設 `部分付款` 的 `amount` 是總應付金額。

---

## 7. 期初餘額語意

期初餘額定義：

```text
期初餘額 = ERP 開始記帳當下，該資金帳戶實際餘額。
```

用途：

```text
避免只從系統上線後 Money Flow 加總，導致現金 / 銀行餘額不準。
```

目前 `Used Car Cash Account` 已有：

```text
opening_balance
opening_balance_date
```

Step 3C-1 不需要優先新增 schema；應先檢查：

```text
opening_balance 預設值是否足夠
opening_balance_date 是否需要在 service 中顯示或校驗
is_active = 0 的帳戶是否仍顯示餘額
```

初步建議：

```text
read-only balance service 可納入所有 Cash Account，但 UI 可預設只顯示 is_active = 1。
已停用帳戶仍可保留歷史資料，不應讓既有 Money Flow 失效。
```

---

## 8. 不進資金餘額但仍要管理的項目

以下項目不等於資金帳戶實際餘額，但仍需要管理：

```text
待付款
待收款
缺憑證
未交記帳士
紙本文件缺漏
應收摘要
應付摘要
```

說明：

```text
這些是管理帳狀態，不等於資金帳戶實際餘額。
未來可以做待收 / 待付報表，但不能混入現金 / 銀行餘額。
```

例如：

```text
購車付款待付款 200,000 不應讓現金減少。
客戶尾款待收款 100,000 不應讓銀行增加。
```

---

## 9. 與單車損益 / 管理毛利的邊界

資金帳戶餘額不等於單車損益。

必須維持：

```text
購車付款影響資金餘額，但不得重複扣管理毛利。
管理毛利仍以 Used Car Vehicle.purchase_price 作為購車成本基礎。
整備 / 維修 / 美容 / 拍場 / 代辦等支出可影響管理毛利，也可在已付款時影響資金餘額。
```

例子：

```text
購車價 500,000
購車付款已付 300,000
資金帳戶減少 300,000
單車購車成本仍是 500,000
待付購車款 200,000 是應付狀態，不是現金餘額
```

也就是：

```text
purchase_price = 成本基礎
purchase payment Money Flow = 資金履約紀錄
```

兩者不能互相覆寫，也不能在管理毛利中重複扣除。

---

## 10. 與正式會計的邊界

本資金餘額是營運管理帳 read-only balance。

它不是：

```text
ERPNext GL Balance
銀行對帳
Payment Entry reconciliation
Journal Entry reconciliation
正式會計科目餘額
報稅申報帳
```

本功能不保證直接等於正式會計科目餘額。

正式報稅 / 記帳士資料仍以文件交接與正式帳務流程為準。

---

## 11. Step 3C 建議拆分

建議後續拆分如下：

### Step 3C-1：Cash Account balance schema gap review

```text
確認 Used Car Cash Account 現有 opening_balance / opening_balance_date / is_active 是否足夠。
確認 Money Flow 現有 direction / settlement_status / status options 是否足夠。
如果不需要新增欄位，Step 3C-1 可以是 docs-only close。
不做 UI。
```

### Step 3C-2：Cash Account balance read-only service

```text
新增 read-only service。
依本 spec 加總 opening_balance + included Money Flow。
不做 Dashboard。
不做正式會計。
```

### Step 3C-3：Cash Account balance tests

```text
測已收款收入增加餘額。
測已付款支出扣減餘額。
測退款扣減餘額。
測待付款 / 待收款不進餘額。
測已作廢不進餘額。
測沒有 cash_account 不進餘額。
測部分付款 / 部分收款暫定規則。
```

### Step 3C-4：Overview cash balance display

```text
在總覽顯示現金 / 主要銀行 / 其他餘額。
只讀。
不做轉帳。
不做對帳。
不做多銀行管理 UI。
```

### Step 3C-5：Cash balance browser smoke / docs close

```text
確認總覽顯示正確。
確認待收 / 待付未混入現金 / 銀行餘額。
確認作廢資料不影響餘額。
文件收尾。
```

---

## 12. Non-scope

本階段不做：

```text
不新增 runtime
不新增 Dashboard
不新增 Page
不新增 report
不新增 DocType 欄位
不改 Money Flow 寫入邏輯
不改 Guided Dialog
不改 Vehicle page JS
不改管理毛利
不改 15-1
不處理正式會計
不做銀行對帳
不做資金轉帳
不做私人代墊
不做刷卡未撥款
不做月結批次付款
不處理 advance account warning
```

---

## 13. 結論

Step 3C-0 結論：

```text
資金帳戶餘額應由 Used Car Cash Account.opening_balance 加上符合條件的 Used Car Money Flow 收入 / 支出形成。
只有已實際收付且有 cash_account 的 Money Flow 才能進資金餘額。
待收 / 待付不進現金 / 銀行餘額。
部分付款 / 部分收款暫定以 amount 作為本筆已實際收付金額。
資金餘額不等於單車損益，也不等於 ERPNext 正式會計餘額。
```

下一步建議：

```text
P1-MVP-OPS Step 3C-1：Cash Account balance schema gap review
```

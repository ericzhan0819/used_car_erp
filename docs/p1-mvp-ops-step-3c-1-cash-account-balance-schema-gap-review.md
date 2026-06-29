# P1-MVP-OPS Step 3C-1：Cash Account Balance Schema Gap Review

日期：2026-06-30  
專案：Used Car ERP / ERPNext / Frappe  
Repo：`ericzhan0819/used_car_erp`  
本機路徑：`~/frappe/frappe-bench/apps/used_car_erp`  
Site：`erpnext-coa.test`

---

## 1. 本文件目的

本文件記錄：

```text
P1-MVP-OPS Step 3C-1：Cash Account balance schema gap review
```

本階段是 docs-only gap review。

目標是確認現有 `Used Car Cash Account` 與 `Used Car Money Flow` schema 是否足夠支撐下一步：

```text
P1-MVP-OPS Step 3C-2：Cash Account balance read-only service
```

本階段不新增欄位、不修改 DocType JSON、不新增 service、不改 JS、不改 Python、不新增 Dashboard。

---

## 2. Review 結論

結論：

```text
No schema change required for Step 3C-2 read-only balance service.
```

原因：

```text
Used Car Cash Account 已有資金帳戶名稱、帳戶類型、期初餘額、期初日期、啟用狀態。
Used Car Money Flow 已有方向、金額、付款日期、資金帳戶、收付狀態與金流狀態。
現有欄位足夠支撐 read-only balance service 的 MVP 計算。
```

因此下一步可以直接進 read-only service，不需要先新增 schema。

---

## 3. Used Car Cash Account schema review

目前 `Used Car Cash Account` 已具備：

| fieldname | label | fieldtype | Step 3C-2 是否足夠 | 說明 |
|---|---|---|---:|---|
| `account_name` | 帳戶名稱 | Data | 是 | 資金帳戶名稱，且為 autoname 來源 |
| `account_type` | 帳戶類型 | Select | 是 | 現金 / 銀行 / 其他，足夠做基本分類彙總 |
| `is_default` | 預設帳戶 | Check | 是 | 可供後續預設帳戶 UI 使用，balance service 不依賴 |
| `opening_balance` | 期初餘額 | Currency | 是 | 可作為資金餘額起點 |
| `opening_balance_date` | 期初日期 | Date | 是 | 可作為期初基準資訊，Step 3C-2 可先顯示或保留，不強制校驗 |
| `is_active` | 啟用 | Check | 是 | UI 可預設只顯示啟用帳戶，service 可保留停用帳戶歷史查詢能力 |
| `sort_order` | 排序 | Int | 是 | 可供 UI 排序使用，balance service 不依賴 |
| `notes` | 備註 | Small Text | 是 | 備註資訊，balance service 不依賴 |

### 3.1 Cash Account gap 判斷

本次未發現必須新增欄位。

不需要新增：

```text
不需要新增 initial_balance：已有 opening_balance
不需要新增 disabled：已有 is_active
不需要新增 title：已有 account_name 並作為 title_field
不需要新增 account category：已有 account_type = 現金 / 銀行 / 其他
```

### 3.2 `is_active` 建議語意

建議 Step 3C-2 service 語意：

```text
read-only balance service 預設可回傳所有 Cash Account。
UI 顯示層可預設只顯示 is_active = 1。
停用帳戶仍保留歷史餘額與既有 Money Flow 連結，不應讓歷史資料失效。
```

---

## 4. Used Car Money Flow schema review

目前 `Used Car Money Flow` 已具備：

| fieldname | label | fieldtype | Step 3C-2 是否足夠 | 說明 |
|---|---|---|---:|---|
| `vehicle` | 車輛 | Link | 是 | 可追溯單車來源 |
| `flow_type` | 金流類型 | Select | 是 | 可供業務分類與報表分類 |
| `direction` | 金流方向 | Select | 是 | 收入 / 支出，決定資金餘額加減 |
| `amount` | 金額 | Currency | 是 | 本筆收付金額 |
| `payment_date` | 付款日期 | Date | 是 | 可供排序、期間查詢、餘額截至日 |
| `payment_method` | 付款方式 | Select | 是 | 可供輔助顯示，balance service 不必依賴 |
| `cash_account` | 資金帳戶 | Link | 是 | 決定歸屬哪個資金帳戶 |
| `settlement_status` | 收付狀態 | Select | 是 | 決定是否納入實際資金餘額 |
| `counterparty_name` | 交易對象 | Data | 是 | 顯示與追溯用，balance service 不必依賴 |
| `status` | 金流狀態 | Select | 是 | 排除已作廢資料 |
| `evidence_attachment` | 憑證附件 | Attach | 是 | 管理帳輔助，不影響餘額計算 |
| `voucher_draft` | 傳票草稿 | Link | 是 | 會計輔助連結，不進業務餘額邏輯 |
| `journal_entry` | 正式會計傳票 | Link | 是 | 會計輔助連結，不進業務餘額邏輯 |

### 4.1 Money Flow option review

現有 `direction`：

```text
收入
支出
```

足夠支撐 Step 3C-2 加減邏輯。

現有 `status`：

```text
待審核
已入帳
已作廢
```

足夠支撐 Step 3C-2 排除作廢資料。

現有 `settlement_status`：

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

足夠支撐 Step 3C-2 判斷「是否實際收付」。

### 4.2 Money Flow gap 判斷

本次未發現必須新增欄位。

不需要新增：

```text
不需要新增 balance_effect 欄位：可由 settlement_status + direction + cash_account + status 推導。
不需要新增 paid_amount：MVP 暫定 amount 代表本筆已記錄收付金額。
不需要新增 total_amount：總應收 / 應付模型留到未來應收應付報表，不阻塞 Step 3C-2。
不需要新增 account ledger table：Step 3C-2 可由 Money Flow 即時計算 read-only balance。
```

---

## 5. Step 3C-2 read-only service 建議輸入 / 輸出

### 5.1 建議 service 名稱

建議新增 read-only service：

```text
used_car_erp.used_car_erp.services.cash_account_balance_service
```

可先提供一個主要方法：

```text
get_cash_account_balance_summary(as_of_date=None, include_inactive=False)
```

此名稱只是 Step 3C-2 建議，實作時可依專案慣例微調。

### 5.2 建議輸入

```text
as_of_date: optional Date
include_inactive: optional bool, default False
```

MVP 可先不支援複雜期間，只支援：

```text
截至指定日期或截至今日的 read-only balance。
```

### 5.3 建議輸出

建議 payload：

```json
{
  "accounts": [
    {
      "cash_account": "現金",
      "account_name": "現金",
      "account_type": "現金",
      "opening_balance": 0,
      "income_total": 0,
      "expense_total": 0,
      "balance": 0,
      "is_active": 1
    }
  ],
  "totals": {
    "income_total": 0,
    "expense_total": 0,
    "balance": 0
  }
}
```

### 5.4 納入條件

Step 3C-2 service 應納入：

```text
cash_account 不為空
status != 已作廢
settlement_status in 已收款 / 已付款 / 部分收款 / 部分付款
```

並依 `direction` 加減：

```text
direction = 收入 → 加到 income_total
direction = 支出 → 加到 expense_total
```

Step 3C-2 service 應排除：

```text
cash_account 空白
status = 已作廢
settlement_status = 待收款
settlement_status = 待付款
settlement_status = 不需收付
settlement_status = 已取消
```

---

## 6. Step 3C-2 測試建議

下一步 service 測試應至少覆蓋：

```text
opening_balance 會進 balance
已收款收入會增加 balance
已付款支出會減少 balance
部分收款暫定會增加 balance
部分付款暫定會減少 balance
待收款不進 balance
待付款不進 balance
不需收付不進 balance
已取消不進 balance
已作廢不進 balance
cash_account 空白不進 balance
不同 cash_account 分別彙總
include_inactive=False 時不回傳停用帳戶，但不得破壞歷史資料
```

---

## 7. 與 Step 3C-0 的一致性

本 review 維持 Step 3C-0 定義：

```text
資金帳戶餘額 = opening_balance + included Money Flow income - included Money Flow expense
只有實際收付且有 cash_account 的 Money Flow 進餘額
待收 / 待付不進現金 / 銀行餘額
部分付款 / 部分收款暫定以 amount 作為本筆已實際收付金額
資金餘額不等於單車損益，也不等於 ERPNext 正式會計餘額
```

---

## 8. Non-scope

本階段不做：

```text
不新增 runtime
不新增 service
不新增 test
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

## 9. 結論

Step 3C-1 結論：

```text
No schema change required.
現有 Used Car Cash Account schema 已足夠支撐 read-only balance foundation。
現有 Used Car Money Flow schema 已足夠支撐 read-only balance foundation。
下一步可直接進 P1-MVP-OPS Step 3C-2：Cash Account balance read-only service。
```

建議下一步：

```text
P1-MVP-OPS Step 3C-2：Cash Account balance read-only service
```

建議 commit message：

```text
feat: add cash account balance read-only service
```

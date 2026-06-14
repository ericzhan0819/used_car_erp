# Taiwan Accounting Item Code Seed Design

Last reviewed: 2026-06-14

Phase: `P1-ACC-0`

本文件定義如何把「113年度會計項目代號名稱對照表」用在 `used_car_erp`，作為台灣報表 / 申報分類的種子資料設計。

本階段只做文件設計，不建立 DocType、不新增 fixture、不修改 ERPNext Account、不修改 runtime。

---

## 1. Source document

來源文件：`113年度會計項目代號名稱對照表.pdf`

文件內容包含台灣申報 / 財報使用的會計項目代號與中文名稱，例如：

```text
0100001 營業收入總額
0100005 營業成本
0201111 現金
0201112 銀行存款
0201123 應收帳款
0201130 存貨
0201144 進項稅款
0201145 留抵稅額
0202121 應付帳款
0202134 銷項稅額
0202136 預收款項
0300090 營業成本
```

---

## 2. Core decision

這份 PDF 不應直接轉成 ERPNext Chart of Accounts。

正確定位：

```text
Taiwan Accounting Item Code
= 台灣申報 / 報表分類代號
= ERPNext Account 的外部分類 mapping
```

錯誤定位：

```text
Taiwan Accounting Item Code
= ERPNext Account 本身
= 直接整份匯入 Chart of Accounts
```

原因：

```text
1. PDF 只提供 code/name，沒有 ERPNext Account 必要欄位。
2. ERPNext Account 需要 company、parent_account、root_type、report_type、account_type、is_group、currency 等結構。
3. 官方代號偏報表分類，不等於公司日常記帳科目。
4. 公司實際科目表可能比官方代號更細，例如銀行帳戶、各車輛庫存、預收款、銷項稅等。
5. 直接匯入會破壞 ERPNext 原生 Chart of Accounts 樹狀結構。
```

---

## 3. Target model

未來可建立一個獨立 master DocType 或 fixture：

```text
Taiwan Accounting Item Code
```

建議欄位：

```text
code: Data, unique, required
item_name: Data, required
category: Select
statement_type: Select
normal_balance: Select, optional
is_group_like: Check
is_active: Check
source_year: Data
source_note: Small Text
```

### 3.1 code

官方代號，例如：

```text
0202134
```

### 3.2 item_name

官方中文名稱，例如：

```text
銷項稅額
```

### 3.3 category

系統內部分類，用於篩選與 mapping UI。

建議 options：

```text
Income
Cost
Expense
Asset
Liability
Equity
InventoryCost
ManufacturingExpense
RAndDExpense
Other
```

### 3.4 statement_type

建議 options：

```text
Profit and Loss
Balance Sheet
Cost Statement
Other
```

### 3.5 normal_balance

可選欄位，不強制。

建議 options：

```text
Debit
Credit
None
```

### 3.6 is_group_like

官方項目有些是總額 / 小計 / 分類項目，例如：

```text
0100001 營業收入總額
0100004 營業收入淨額
0201000 資產總額
0202000 負債總額
0203000 權益總額
```

這類通常不應直接 mapping 到單一 ERPNext posting account，可標記為 `is_group_like = 1`。

---

## 4. ERPNext Account mapping model

未來應建立 mapping，而不是直接把官方代號變成 Account。

建議建立：

```text
Used Car Account Mapping
或
Taiwan Accounting Item Account Mapping
```

建議欄位：

```text
company: Link / Company
account: Link / Account
taiwan_accounting_item_code: Link / Taiwan Accounting Item Code
mapping_purpose: Select
is_default: Check
is_active: Check
note: Small Text
```

### 4.1 mapping_purpose

建議 options：

```text
Sales Revenue
COGS
Inventory
Accounts Receivable
Accounts Payable
Output VAT
Input VAT
VAT Retained Credit
Advance Received
Cash
Bank
Expense
Other
```

### 4.2 mapping cardinality

允許：

```text
多個 ERPNext Account → 同一個官方代號
```

例如公司可能有多個銀行帳戶：

```text
銀行存款 - A銀行
銀行存款 - B銀行
```

都可對應：

```text
0201112 銀行存款
```

不建議：

```text
一個 ERPNext posting Account → 多個官方代號
```

除非有明確報表拆分規則。

---

## 5. MVP seed list

P1-ACC-1 不應整份匯入 PDF。第一批只放中古車買賣流程會用到的最小集合。

### 5.1 Sales / revenue

```text
0100001 營業收入總額
0100004 營業收入淨額
```

用途：

```text
中古車銷售收入 mapping
Sales Invoice income account 報表分類
```

### 5.2 Cost / inventory

```text
0100005 營業成本
0201130 存貨
0201131 商品
0300090 營業成本
```

用途：

```text
中古車庫存
銷貨成本 / 進銷成本分類
未來 COGS / inventory report 對照
```

注意：

```text
0100005 與 0300090 都可能與營業成本有關。
P1-ACC-1 先保留兩者，實際報表 mapping 需由會計師確認。
```

### 5.3 Cash / bank / receivables

```text
0201111 現金
0201112 銀行存款
0201123 應收帳款
0201129 其他應收款
```

用途：

```text
訂金 / 尾款入帳
Sales Invoice 應收帳款
其他應收款分類
```

### 5.4 VAT / tax

```text
0201144 進項稅款
0201145 留抵稅額
0202132 應付稅捐
0202134 銷項稅額
```

用途：

```text
Sales Taxes and Charges Template 的銷項稅 Account 對照
進項稅 / 留抵稅額報表分類
15-1 內部估算報稅輔助分類
```

重要邊界：

```text
15-1 可扣抵進項稅額是內部報稅輔助，不進 Sales Invoice taxes table。
```

### 5.5 Payables / advances

```text
0202121 應付帳款
0202130 其他應付款
0202136 預收款項
0202137 預收貨款
0202138 其他預收款
```

用途：

```text
採購 / 整備應付
訂金 / 尾款預收款
預收款沖轉 Journal Entry 對照
```

### 5.6 Expenses

```text
0100016 修繕費
0100017 廣告費
0100018 水電瓦斯費
0100019 保險費
0100022 稅捐
0100030 佣金支出
0100032 其他費用
```

用途：

```text
整備 / 維修 / 美容 / 廣告 / 保險 / 稅費等費用分類
```

注意：

```text
中古車整備成本是否進庫存成本或期間費用，仍需依交易性質與會計師判斷。
本 mapping 只做報表分類，不自動決定 COGS。
```

---

## 6. Explicit non-goals

P1-ACC-0 / P1-ACC-1 不做：

```text
不整份匯入 113 年度所有官方代號
不建立完整 Chart of Accounts
不覆蓋 ERPNext 既有 Account
不新增或修改 Sales Invoice runtime
不新增 Journal Entry runtime
不新增 Tax Summary runtime
不自動決定 COGS
不自動提交任何會計文件
不處理電子發票 API
不取代會計師報稅判斷
```

---

## 7. Fixture strategy

建議 P1-ACC-1 使用 fixture 或 patch seed，但要保持可重跑、idempotent。

### 7.1 Fixture data shape

建議先用 Python tuple / list of dicts，而不是從 PDF 動態解析。

範例：

```python
TAIWAN_ACCOUNTING_ITEM_CODES = [
    {
        "code": "0202134",
        "item_name": "銷項稅額",
        "category": "Liability",
        "statement_type": "Balance Sheet",
        "normal_balance": "Credit",
        "is_group_like": 0,
        "source_year": "113",
    },
]
```

理由：

```text
1. PDF 是外部來源，不適合每次 migrate 動態解析。
2. 手工挑選 MVP 代號比較安全。
3. 可控、可 review、可測試。
4. 未來年度更換時可用明確 diff 管理。
```

### 7.2 Idempotent rule

Seed 必須以 `code` 為唯一鍵：

```text
已存在 code → update label/category metadata if needed
不存在 code → insert
```

不可用 item_name 當唯一鍵，因為中文名稱可能改字或含全形符號。

### 7.3 Source year

每筆資料保留：

```text
source_year = 113
```

未來如果 114 年度代號表有變動，才新增更新策略。

---

## 8. Validation rules

未來 DocType 應驗證：

```text
code 必填
code 唯一
item_name 必填
source_year 必填
category 必須是允許值
statement_type 必須是允許值
```

Mapping 應驗證：

```text
company 必填
account 必填
account.company 必須等於 mapping.company
account 不可 disabled
account 不可 is_group
taiwan_accounting_item_code 必填
停用官方代號不可被 active mapping 使用
```

---

## 9. Report usage

這份 seed 的主要用途不是日常開傳票，而是報表歸類。

未來報表可用：

```text
ERPNext GL Entry
→ Account
→ Taiwan Accounting Item Account Mapping
→ Taiwan Accounting Item Code
→ 報表 / 匯出 / 會計師檢查資料
```

範例：

```text
Sales Invoice income account
→ 中古車銷售收入
→ 0100001 營業收入總額

Sales Taxes and Charges account_head
→ 銷項稅額
→ 0202134 銷項稅額

Advance liability account
→ 預收款項
→ 0202136 預收款項
```

---

## 10. Suggested implementation sequence

### P1-ACC-0

```text
文件設計，本文件。
```

### P1-ACC-1

```text
新增 Taiwan Accounting Item Code DocType
新增 MVP seed / patch
新增 basic tests / verification function
不建立 Account mapping UI
```

### P1-ACC-2

```text
新增 ERPNext Account 對官方代號 mapping DocType
手動 mapping existing Account
新增 validation
```

### P1-ACC-3

```text
會計報表 / 匯出用 mapping lookup
不影響正式 GL posting
```

---

## 11. Current recommendation

短期最穩定作法：

```text
1. 先保留 ERPNext 原生 Chart of Accounts。
2. 不用官方代號直接建立 Account。
3. 用官方代號建立獨立 master data。
4. 用 mapping 連接 ERPNext Account 與官方代號。
5. 第一批只 seed 中古車買賣、銷項稅、進項稅、預收款、應收帳款、存貨、營業收入、營業成本會用到的代號。
```

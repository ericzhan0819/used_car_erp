# ERPNext Sales Tax Template Setup Guide

Last reviewed: 2026-06-14

Phase: `P1-TAX-1-0`

本文件定義在 `used_car_erp` 寫入任何 Sales Invoice tax template 自動套用邏輯之前，ERPNext 站台需要先完成的會計設定。

本文件是設定指南與下一階段程式設計邊界，不是報稅建議。正式科目名稱、發票開立方式、申報方式仍應由會計師確認。

---

## 1. Scope

### 1.1 本階段要完成

```text
確認 ERPNext 的銷項稅科目
建立 Sales Taxes and Charges Template
固定 template 命名
確認含稅 / 未稅使用邊界
定義 P1-TAX-1-A 自動套用邏輯的前置條件
```

### 1.2 本階段不做

```text
不修改 Python runtime
不修改 DocType JSON
不新增 patch
不提交 Sales Invoice
不建立 Journal Entry / Payment Entry / Delivery Note / Stock Entry
不自動建立 Sales Taxes and Charges Template
不把 15-1 扣抵額塞進 Sales Invoice taxes table
不串電子發票 API
不做正式營業稅申報檔
```

---

## 2. ERPNext source observations

本文件已對照 ERPNext upstream `frappe/erpnext` 的 doctype 結構，主要參考：

```text
erpnext/accounts/doctype/sales_taxes_and_charges_template/sales_taxes_and_charges_template.json
erpnext/accounts/doctype/sales_taxes_and_charges/sales_taxes_and_charges.json
erpnext/accounts/doctype/sales_invoice/sales_invoice.json
erpnext/accounts/doctype/account/account.json
```

### 2.1 Sales Taxes and Charges Template

ERPNext 的 `Sales Taxes and Charges Template` 是 setup DocType，核心欄位包含：

```text
title
is_default
disabled
company
tax_category
taxes
```

其中 `taxes` 是 child table，指向 `Sales Taxes and Charges`。

設計意義：

```text
P1-TAX-1-A 不應硬塞自製稅額欄位。
應沿用 ERPNext 原生 Sales Taxes and Charges Template。
```

### 2.2 Sales Taxes and Charges row

`Sales Taxes and Charges` 重要欄位包含：

```text
charge_type
account_head
description
included_in_print_rate
rate
tax_amount
total
```

`charge_type` 支援：

```text
Actual
On Net Total
On Previous Row Amount
On Previous Row Total
On Item Quantity
```

台灣一般 5% 銷項稅第一階段應使用：

```text
charge_type = On Net Total
rate = 5
account_head = 銷項稅額科目
```

若成交價是客戶談好的含稅總價，應使用：

```text
included_in_print_rate = 1
```

若成交價是未稅價，才使用：

```text
included_in_print_rate = 0
```

### 2.3 Sales Invoice

ERPNext `Sales Invoice` 原生包含：

```text
tax_category
taxes_and_charges
taxes
total_taxes_and_charges
grand_total
```

設計意義：

```text
P1-TAX-1-A 應在建立 Sales Invoice 草稿時設定 taxes_and_charges，並讓 ERPNext 原生計算 taxes / total_taxes_and_charges / grand_total。
不應自行在 Used Car Vehicle 上計算正式 Sales Invoice 稅額。
```

### 2.4 Account

ERPNext `Account` 支援：

```text
root_type
account_type
tax_rate
company
is_group
disabled
```

其中 `account_type` 包含 `Tax`。

設計意義：

```text
銷項稅額科目應使用非群組、未停用、所屬公司正確、可作為稅項 account_head 的 Account。
建議 Account Type 設為 Tax。
```

---

## 3. Used Car tax boundary

P1-TAX-0 已決定：車輛頁只記錄買入憑證 / 是否取得可扣抵統一發票。

```text
purchase_document_type = 統一發票
→ vehicle_tax_mode = 一般發票扣抵

purchase_document_type = 未取得 / 買賣合約 / 讓渡書 / 匯款紀錄 / 收據
→ vehicle_tax_mode = 15-1 特殊扣抵

purchase_document_type = 拍場單據 / 其他 / 空值
→ vehicle_tax_mode = 待確認
→ 阻擋 Sales Invoice 草稿建立
```

P1-TAX-1-0 延續此邊界：

```text
Sales Invoice 處理對客戶開立的銷項稅。
15-1 的購入成本換算進項扣抵，只是內部報稅輔助資料。
15-1 扣抵額不得出現在客戶 Sales Invoice taxes table 內。
```

---

## 4. Recommended ERPNext setup

### 4.1 Account：銷項稅額

請在 ERPNext `Account` 建立或確認銷項稅額科目。

建議資料：

```text
Account Name: 銷項稅額
Company: 你的公司
Is Group: 0
Root Type: Liability
Report Type: Balance Sheet
Account Type: Tax
Tax Rate: 5
Disabled: 0
```

實際帳號名稱會依 ERPNext company abbreviation 變成類似：

```text
銷項稅額 - <company_abbr>
```

若 ERPNext 已有符合條件的銷項稅額科目，可沿用，不需要重複建立。

### 4.2 Template：台灣營業稅 5%（含稅）

這是本專案第一優先 template。

理由：中古車成交價通常是客戶談好的總價，實務上較接近含稅總價。

請建立：

```text
DocType: Sales Taxes and Charges Template
Title: 台灣營業稅 5%（含稅）
Company: 你的公司
Disabled: 0
Default: 不強制
```

Taxes child row：

```text
Type / charge_type: On Net Total
Account Head: 銷項稅額 - <company_abbr>
Description: 營業稅 5%（含稅）
Rate: 5
Is this Tax included in Basic Rate? / included_in_print_rate: 1
```

範例結果：

```text
成交價 / item rate: 1,000,000
included_in_print_rate: 1
ERPNext 應反推出：
- 未稅銷售額：約 952,381
- 銷項稅額：約 47,619
- Grand Total：約 1,000,000
```

### 4.3 Template：台灣營業稅 5%（未稅）

這是備用 template。

只有在公司明確決定 `sold_price` 是未稅價時才使用。

請建立：

```text
DocType: Sales Taxes and Charges Template
Title: 台灣營業稅 5%（未稅）
Company: 你的公司
Disabled: 0
Default: 不強制
```

Taxes child row：

```text
Type / charge_type: On Net Total
Account Head: 銷項稅額 - <company_abbr>
Description: 營業稅 5%（未稅）
Rate: 5
Is this Tax included in Basic Rate? / included_in_print_rate: 0
```

範例結果：

```text
成交價 / item rate: 1,000,000
included_in_print_rate: 0
ERPNext 應計算：
- 未稅銷售額：1,000,000
- 銷項稅額：50,000
- Grand Total：1,050,000
```

---

## 5. Template selection policy for used car sales

### 5.1 Current recommendation

短期建議固定使用：

```text
台灣營業稅 5%（含稅）
```

原因：

```text
中古車售價通常是跟客戶談總價。
台灣應稅貨物定價通常以含稅方式呈現。
含稅 template 可避免 Sales Invoice grand_total 高於客戶實際成交價。
```

### 5.2 一般發票扣抵與 15-1 的 Sales Invoice 表現

兩種買入憑證模式，在 Sales Invoice 上都應呈現正常銷項稅：

```text
一般發票扣抵
→ Sales Invoice 套台灣營業稅 5% template
→ 進項發票扣抵由採購憑證 / Purchase side 處理

15-1 特殊扣抵
→ Sales Invoice 仍套台灣營業稅 5% template
→ 15-1 估算另由內部會計 / 報稅輔助資料處理
→ 不把 15-1 扣抵額塞進 Sales Invoice taxes row
```

### 5.3 待確認憑證

若 `purchase_document_type` 對應 `vehicle_tax_mode = 待確認`：

```text
不得建立 Sales Invoice 草稿。
請先由會計確認買入憑證是否可扣抵或是否適用 15-1。
```

這個 gate 已在 P1-TAX-0 完成。

---

## 6. Manual setup checklist

### 6.1 建立 / 確認 Account

在 ERPNext：

```text
Accounting → Chart of Accounts → New Account
```

確認：

```text
[ ] 銷項稅額科目存在
[ ] Account 屬於正確 Company
[ ] Is Group = 0
[ ] Disabled = 0
[ ] Account Type = Tax
[ ] Tax Rate = 5
```

### 6.2 建立含稅 template

在 ERPNext：

```text
Accounting → Taxes → Sales Taxes and Charges Template → New
```

確認：

```text
[ ] Title = 台灣營業稅 5%（含稅）
[ ] Company 正確
[ ] Disabled = 0
[ ] taxes child table 有且只有一列 5% 銷項稅
[ ] charge_type = On Net Total
[ ] account_head = 銷項稅額科目
[ ] rate = 5
[ ] included_in_print_rate = 1
```

### 6.3 建立未稅 template

```text
[ ] Title = 台灣營業稅 5%（未稅）
[ ] Company 正確
[ ] Disabled = 0
[ ] taxes child table 有且只有一列 5% 銷項稅
[ ] charge_type = On Net Total
[ ] account_head = 銷項稅額科目
[ ] rate = 5
[ ] included_in_print_rate = 0
```

### 6.4 手動 Sales Invoice 驗證

建立一張測試用 Draft Sales Invoice，不要 submit。

含稅 template 驗證：

```text
Item rate = 1,000,000
Taxes and Charges = 台灣營業稅 5%（含稅）
預期 Grand Total 約等於 1,000,000
```

未稅 template 驗證：

```text
Item rate = 1,000,000
Taxes and Charges = 台灣營業稅 5%（未稅）
預期 Grand Total 約等於 1,050,000
```

驗證完請刪除測試草稿，或保留但明確標記為測試資料。

---

## 7. SQL verification

可用 Adminer 或 bench mariadb 檢查。

```sql
select name, title, company, disabled, is_default
from `tabSales Taxes and Charges Template`
where title in ('台灣營業稅 5%（含稅）', '台灣營業稅 5%（未稅）');
```

```sql
select parent, charge_type, account_head, description, rate, included_in_print_rate
from `tabSales Taxes and Charges`
where parent in (
  select name
  from `tabSales Taxes and Charges Template`
  where title in ('台灣營業稅 5%（含稅）', '台灣營業稅 5%（未稅）')
);
```

```sql
select name, account_name, company, root_type, account_type, tax_rate, is_group, disabled
from `tabAccount`
where account_type = 'Tax'
  and disabled = 0
  and is_group = 0;
```

---

## 8. P1-TAX-1-A implementation target

下一階段 `P1-TAX-1-A` 才修改 runtime。

預期行為：

```text
create_sales_invoice_draft_for_vehicle
→ 確認 vehicle_tax_mode 不是 待確認
→ 解析公司
→ 找到啟用中的 Sales Taxes and Charges Template
→ 將 taxes_and_charges 設為 台灣營業稅 5%（含稅）
→ 讓 ERPNext 自行帶入 taxes child rows 並計算 grand_total
→ Sales Invoice 保持 Draft
→ 會計人工檢查後才 submit
```

最小阻擋條件：

```text
template 不存在 → block
多個同名 template / 公司不一致 → block
account_head 不存在 → block
account_head disabled / is_group → block
rate 不是 5 → block
included_in_print_rate 不符合預期 → block
```

remarks 建議追加：

```text
中古車稅務判斷：一般發票扣抵 / 15-1 特殊扣抵
買入憑證：統一發票 / 未取得 / 買賣合約 / ...
Sales Invoice 稅項：台灣營業稅 5%（含稅）
15-1 扣抵估算不列入客戶 Sales Invoice 稅項。
```

---

## 9. Non-goals for P1-TAX-1-A

```text
不自動建立稅務 template
不支援多稅率
不支援電子發票 API
不支援 Tax Category 自動分流
不支援 Item Tax Template
不建立正式 Tax Summary DocType
不建立 15-1 Journal Entry
不建立 Purchase Invoice
不把 15-1 扣抵額列成 Sales Invoice 負稅項或折扣
```

---

## 10. Open accounting decisions

進入正式自動化前，請與會計師確認：

```text
1. 銷項稅額科目正式名稱。
2. 中古車成交價是否一律視為含稅總價。
3. Sales Invoice print format 是否要顯示稅額拆分。
4. 15-1 扣抵估算報表需要哪些欄位。
5. 拍場單據在你的實際交易中如何判斷可扣抵 / 15-1 / 其他處理。
6. 電子發票或統一發票開立系統是否與 ERPNext 串接，或仍由外部系統處理。
```

---

## 11. Current recommendation

短期最穩定設定：

```text
Vehicle page:
- 只維護買入憑證 / 是否取得可扣抵發票

Sales Invoice Draft:
- 一律套用 台灣營業稅 5%（含稅）
- 不把 15-1 扣抵額放入 Sales Invoice

Accounting / Tax workpaper:
- 另外呈現 15-1 可扣抵進項稅額估算
- 報稅季交由會計師確認
```

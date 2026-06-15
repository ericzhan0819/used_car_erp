# Taiwan Full Chart of Accounts Source Catalog

Last reviewed: 2026-06-16

Phase: `P1-ACC-4`

## 1. Purpose

P1-ACC-4 建立 `113 年度台灣完整會計項目代號` 的 machine-readable source catalog，作為後續 P1-ACC-5 產生 ERPNext Chart of Accounts Importer 檔案的來源。

本 catalog 保留官方代號與名稱，並先標記 ERPNext 匯入前需要的 root type、report type、group/ledger、預設 enabled/disabled 與人工覆核資訊。

## 2. Source PDF

來源文件：

```text
113年度會計項目代號名稱對照表.pdf
```

PDF 僅作本機人工來源，不提交到 repo。

## 3. Catalog File

Catalog 位置：

```text
used_car_erp/data/taiwan_coa_113_full.json
```

本階段收錄來源 PDF 中可抽取的所有有效 `code/name`，包含純數字代號與英數混合代號。唯一鍵為：

```text
source_year + code
```

不得以中文名稱去重，因此 `0100005 營業成本` 與 `0300090 營業成本` 必須同時存在。

## 4. Fields

每筆 catalog row 包含：

```text
source_year
code
official_item_name
account_number
account_name
root_type
report_type
parent_code
parent_account_name
is_group
account_type
is_enabled_by_default
disabled_reason
is_system_required
source_page
source_note
manual_review_required
```

欄位規則：

```text
source_year 固定為 113。
account_number 預設等於 code。
account_name 預設等於 official_item_name。
root_type 限 Asset / Liability / Equity / Income / Expense。
report_type 限 Balance Sheet / Profit and Loss / Cost Statement / Other。
is_group、is_enabled_by_default、is_system_required、manual_review_required 使用 0 或 1。
disabled row 必須填 disabled_reason。
官方代號列 is_system_required 固定為 0。
```

## 5. Enabled And Disabled Rules

中古車買賣第一版核心科目預設 enabled，包含現金、銀行存款、應收帳款、商品、進項稅款、留抵稅額、應付帳款、銷項稅額、預收款項、營業收入、營業成本與常用營業費用。

Group account 原則上保持 enabled，用於後續維持 ERPNext Chart of Accounts 樹狀結構。

其他目前不常用的 ledger account 會建立但預設 disabled，包含金融資產與投資、長期投資、固定資產細項、遞耗資產、無形資產、使用權資產、長期負債、公司債、複雜權益調整、製造成本明細、`04B` 製造費用、`05C` 研究發展費用，以及需會計人工定義的其他 / 加：其他 / 減：其他項目。

## 6. Manual Review Rules

`manual_review_required = 1` 表示該 row 在後續產生 importer 前需要人工覆核。常見原因包含：

```text
同名但不同代號，且用途容易混淆。
加：其他、減：其他、其他類泛用項目。
可能是報表列、小計列或公式列。
ERPNext root_type、account_type 或 group/ledger 用途需會計確認。
```

若未來遇到 PDF 抽取出 code 但官方中文名稱缺漏，必須標記 `manual_review_required = 1` 並補上 `source_note`；若名稱完全無法判讀，應先列入 unresolved 文件，不得任意補入正式 catalog。

本次抽取未發現名稱完全無法判讀的 unresolved rows。

## 7. Validation Functions

Service 位置：

```text
used_car_erp/used_car_erp/services/taiwan_coa_catalog_service.py
```

可用 function：

```python
load_taiwan_coa_catalog()
validate_taiwan_coa_catalog()
get_taiwan_coa_catalog_summary()
```

Bench 驗證範例：

```bash
bench --site erpnext.localhost execute used_car_erp.used_car_erp.services.taiwan_coa_catalog_service.get_taiwan_coa_catalog_summary
bench --site erpnext.localhost execute used_car_erp.used_car_erp.services.taiwan_coa_catalog_service.validate_taiwan_coa_catalog
```

## 8. Runtime Boundary

本階段不做：

```text
不匯入 Chart of Accounts。
不停用 Account。
不修改 tabAccount。
不 rename Account。
不改 Company Defaults。
不改 Item Defaults。
不改 Warehouse。
不改 Sales Taxes and Charges Template。
不修改 Sales Invoice / Journal Entry / GL Entry runtime。
不新增 patch 自動匯入 Account。
```

## 9. Next Phase

P1-ACC-5 才會根據此 catalog 產生 ERPNext Chart of Accounts Importer 檔案。

P1-ACC-5 仍應只產生 importer 檔案，不應自動匯入或修改 runtime。

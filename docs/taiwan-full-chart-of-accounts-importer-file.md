# Taiwan Full Chart of Accounts Importer File

Last reviewed: 2026-06-16

Phase: `P1-ACC-5`

## 1. Purpose

P1-ACC-5 依 P1-ACC-4 的 `113` 年度台灣完整會計項目 source catalog，產生 ERPNext Chart of Accounts Importer 可人工檢查與手動匯入用 artefacts。

本階段只產出檔案與 validation service，不執行匯入、不停用 Account、不修改 `tabAccount`、不修改 ERPNext accounting runtime。

## 2. Source Catalog

來源 catalog：

```text
used_car_erp/data/taiwan_coa_113_full.json
```

P1-ACC-4 validation summary：

```text
catalog_total_count: 291
enabled_count: 80
disabled_count: 211
manual_review_required_count: 22
duplicate_codes: []
missing_core_codes: []
```

## 3. ERPNext Importer Format Confirmation

本機 ERPNext v15.111.0 原始碼確認位置：

```text
/home/z/frappe/frappe-bench/apps/erpnext/erpnext/accounts/doctype/chart_of_accounts_importer/chart_of_accounts_importer.py
/home/z/frappe/frappe-bench/apps/erpnext/erpnext/accounts/doctype/account/chart_of_accounts/chart_of_accounts.py
```

確認結果：

```text
1. Chart of Accounts Importer 接受 CSV / XLS / XLSX，不接受 JSON 匯入。
2. CSV / Excel 固定需要 8 欄。
3. 欄位為 Account Name、Parent Account、Account Number、Parent Account Number、Is Group、Account Type、Root Type、Account Currency。
4. importer 不支援 disabled 欄位。
5. importer 支援 account_type。
6. parent / child hierarchy 由 Parent Account 與 Parent Account Number 表示。
7. root account 必須沒有 parent，且 Root Type 必須是 Asset / Liability / Expense / Income / Equity 之一。
8. ERPNext 會要求五種 root type 都存在。
```

## 4. Generated Files

本階段產出：

```text
exports/chart_of_accounts/taiwan_used_car_full_coa_113_preview.json
exports/chart_of_accounts/taiwan_used_car_full_coa_113.csv
exports/chart_of_accounts/taiwan_used_car_full_coa_113_post_import_disable_plan.json
```

未產生 JSON importer file，因為本機 ERPNext importer 不接受 JSON 檔案。

## 5. Preview JSON

Preview JSON 是人工檢查用 normalized artefact，不是 ERPNext 原生 importer 格式。

每筆 account 包含：

```text
code
official_item_name
account_number
account_name
root_type
report_type
parent_account
is_group
account_type
is_enabled_by_default
disabled
manual_review_required
source
source_note
```

Preview 也包含 summary、manual review codes、importer format 與 disabled support 判斷。

## 6. CSV Importer File

CSV 檔案使用 ERPNext Chart of Accounts Importer template 的 8 欄：

```text
Account Name
Parent Account
Account Number
Parent Account Number
Is Group
Account Type
Root Type
Account Currency
```

Generated hierarchy root groups：

```text
TW-ASSET - 資產
TW-LIABILITY - 負債
TW-EQUITY - 權益
TW-INCOME - 收入
TW-EXPENSE - 費用
```

這些 root groups 只用於 ERPNext importer tree 結構，`source = generated_hierarchy_group`，不冒充官方台灣會計項目代號。

## 7. Disabled Support

本機 ERPNext v15.111.0 Chart of Accounts Importer 不支援 disabled 欄位。

因此 CSV importer file 不包含 disabled 欄位，也不硬塞非模板欄位，避免 importer 因欄位數不符而失敗。

## 8. Post-import Disable Plan

因 importer 不支援 disabled，本階段另外產生：

```text
exports/chart_of_accounts/taiwan_used_car_full_coa_113_post_import_disable_plan.json
```

用途：記錄 P1-ACC-4 catalog 中 `is_enabled_by_default = 0` 的 ledger / account 後續應停用清單。

後續 P1-ACC-6 或更晚階段如需停用 Account，必須使用 Frappe ORM 與明確 QA，不可直接 SQL update。

本階段不執行 disable plan。

## 9. Manual Review Rows

Manual review rows 不會被忽略，全部保留於 preview 與 CSV export。

目前 manual review codes：

```text
0100032
0100044
0100052
0201138
0201199
0201904
0202135
0202196
0202999
0203506
0300302
0300303
0301202
0301203
0301602
0301603
0302202
0302203
0303202
0303203
04B0090
05C2920
```

`0100005` 與 `0300090` 均保留於 export，不以中文名稱合併。

以下 posting-sensitive core codes 也都保留於 export，P1-ACC-6 匯入前仍需人工確認 account_type、用途與後續 defaults：

```text
0202134
0201144
0201145
0202136
0201123
0201131
```

## 10. Pre-import Gates

P1-ACC-6 手動匯入前至少需確認：

```text
1. catalog validation 通過。
2. importer export validation 通過。
3. 已人工檢查 preview JSON 與 CSV hierarchy。
4. 已備份 dev site。
5. 已確認 Company / abbr / existing GL Entry 狀態。
6. 已確認 manual_review_required rows。
7. 已確認 post-import disable plan 只在匯入後由 ORM 流程處理。
```

## 11. Runtime Boundary

本階段明確不做：

```text
不執行 Chart of Accounts Importer。
不修改 tabAccount。
不 disable Account。
不刪除 Account。
不 rename Account。
不改 Company Defaults。
不改 Item Defaults。
不改 Warehouse。
不改 Sales Taxes and Charges Template。
不新增 patch 自動匯入 Account。
不修改 Sales Invoice / Journal Entry / GL Entry runtime。
```

## 12. Next Phase

P1-ACC-6 才允許在 dev site 進行手動 Chart of Accounts Importer 匯入與 QA。

P1-ACC-6 仍需先完成匯入前 gates，並將停用 Account、Company Defaults、Item Defaults、Warehouse、Tax Template 與最小交易 QA 分開處理。

# Taiwan Chart of Accounts Import Preflight

Last reviewed: 2026-06-16

Phase: `P1-ACC-6A`

## 1. Purpose

P1-ACC-6A 在正式使用 ERPNext Chart of Accounts Importer 前，先完成 dev site 匯入前只讀檢查、目前 `tabAccount` 備份、會計 / 庫存資料數量盤點與 gate report。

本階段目標是讓後續人工匯入前具備可檢查的客觀證據，避免在已有正式會計或庫存資料時誤覆蓋 Chart of Accounts。

## 2. Why Preflight Is Required

Chart of Accounts 會影響 Sales Invoice、Purchase Invoice、Payment Entry、Journal Entry、GL Entry、Stock、Tax Template、Item Default、Warehouse 與 Company Defaults。匯入前必須先確認公司、既有科目、正式交易資料與 P1-ACC-5 匯入檔案狀態。

Preflight 只做盤點與 gate 判斷，不代表已取得匯入授權。即使 gate 可匯入，仍必須由使用者人工確認。

## 3. Read Scope

本階段讀取 DB：

```text
Company
Account
GL Entry
Sales Invoice
Purchase Invoice
Payment Entry
Journal Entry
Stock Ledger Entry
Stock Entry
Delivery Note
Purchase Receipt
Item
Warehouse
Sales Taxes and Charges Template
Purchase Taxes and Charges Template
Used Car Vehicle
Used Car Reservation
Used Car Money Flow
Used Car Voucher Draft
Used Car Vehicle Cost
Taiwan Accounting Item Code
Taiwan Accounting Item Account Mapping
```

本階段讀取 P1-ACC-5 export artefacts：

```text
exports/chart_of_accounts/taiwan_used_car_full_coa_113_preview.json
exports/chart_of_accounts/taiwan_used_car_full_coa_113.csv
exports/chart_of_accounts/taiwan_used_car_full_coa_113_post_import_disable_plan.json
```

Preflight 會呼叫：

```python
used_car_erp.used_car_erp.services.taiwan_coa_importer_export_service.validate_taiwan_coa_importer_export()
```

若 P1-ACC-5 validation 有 errors，gate 必須 fail。

## 4. Generated Files

產出位置：

```text
exports/chart_of_accounts/preflight/current_account_backup.csv
exports/chart_of_accounts/preflight/accounting_data_counts.json
exports/chart_of_accounts/preflight/pre_import_gate_report.json
```

`current_account_backup.csv` 匯出目前 `Company = OO` 的 Account 欄位。若本機 ERPNext 版本缺少部分欄位，service 會保留可取得欄位並在 gate report warnings 記錄缺失欄位。

`accounting_data_counts.json` 記錄每個 DocType 是否存在、總數，以及有 `docstatus` 時的 draft / submitted / cancelled 數量。

`pre_import_gate_report.json` 記錄 company、company_abbr、gate 狀態、warnings、errors、artefact 路徑、`can_import_chart_of_accounts` 與 `required_manual_confirmation`。

## 5. Gate Rules

必須 pass：

```text
1. Company OO 存在。
2. Company abbr = O。
3. P1-ACC-5 importer CSV 存在。
4. P1-ACC-5 preview JSON 存在。
5. P1-ACC-5 post_import_disable_plan JSON 存在。
6. P1-ACC-5 validate_taiwan_coa_importer_export passed。
7. current_account_backup.csv 已產出。
8. accounting_data_counts.json 已產出。
```

任一必須 pass 的條件不成立，`status = fail`，`can_import_chart_of_accounts = false`。

## 6. Warning And Fail Definitions

以下任一數量大於 0 時，`status = warning` 且 `can_import_chart_of_accounts = false`：

```text
GL Entry count
submitted Sales Invoice count
submitted Purchase Invoice count
submitted Payment Entry count
submitted Journal Entry count
Stock Ledger Entry count
submitted Stock Entry count
submitted Delivery Note count
submitted Purchase Receipt count
```

若上述正式會計 / 庫存資料都是 0，但仍有 draft 文件或 custom app workflow records，仍可維持 `status = warning`，因為 dev site 覆蓋仍需人工確認。

即使所有 gate 都 pass，`required_manual_confirmation` 永遠是 `true`。本階段不允許自動匯入。

## 7. How To Run Preflight

在 bench 目錄執行：

```bash
bench --site erpnext.localhost execute used_car_erp.used_car_erp.services.taiwan_coa_import_preflight_service.get_chart_of_accounts_import_preflight_summary
bench --site erpnext.localhost execute used_car_erp.used_car_erp.services.taiwan_coa_import_preflight_service.run_chart_of_accounts_import_preflight
bench --site erpnext.localhost execute used_car_erp.used_car_erp.services.taiwan_coa_import_preflight_service.validate_chart_of_accounts_import_preflight_files
```

可選測試：

```bash
bench --site erpnext.localhost run-tests --app used_car_erp --module used_car_erp.used_car_erp.services.test_taiwan_coa_import_preflight_service
```

若 site 顯示 `Testing is disabled for the site!`，只記錄結果，不修改 site 設定。

## 8. Manual Check For Account Backup

人工檢查 `current_account_backup.csv`：

```text
1. 確認只包含 company = OO 的 Account。
2. 確認 Account root / group / ledger 結構是否仍是預期 dev site 狀態。
3. 檢查 disabled、account_type、account_currency 是否有匯入後需保留或重建的資訊。
4. 若 gate report warnings 顯示缺少欄位，確認該 ERPNext 版本是否本來沒有該欄位。
```

## 9. Manual Check For Accounting Data Counts

人工檢查 `accounting_data_counts.json`：

```text
1. 確認 GL Entry 與 Stock Ledger Entry 是否為 0。
2. 確認 Sales Invoice、Purchase Invoice、Payment Entry、Journal Entry 是否已有 submitted 文件。
3. 確認 Stock Entry、Delivery Note、Purchase Receipt 是否已有 submitted 文件。
4. 檢查 custom app workflow records 是否可接受 dev site 覆蓋風險。
5. 若 DocType 不存在，確認這是 app 未安裝、未 migrate 或版本差異，而不是 preflight 錯誤。
```

## 10. Runtime Boundary

本階段明確不做：

```text
不匯入 Chart of Accounts。
不停用 Account。
不修改 tabAccount。
不 rename Account。
不 delete Account。
不改 Company Defaults。
不改 Item Defaults。
不改 Warehouse。
不改 Sales Taxes and Charges Template。
不修改 Sales Invoice / Journal Entry / GL Entry runtime。
不提交、取消或刪除任何會計 / 庫存文件。
```

## 11. Next Phase

P1-ACC-6B 才允許使用 ERPNext UI 手動匯入 Chart of Accounts。

P1-ACC-6B 仍需先人工確認 P1-ACC-6A gate report、Account backup、accounting data counts、P1-ACC-5 preview / CSV / disable plan，以及 dev site 可覆蓋風險。

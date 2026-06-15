# Taiwan Full Chart of Accounts Import Design

Last reviewed: 2026-06-14

Phase: `P1-ACC-3`

本文件重新定義 `used_car_erp` 的台灣會計科目表策略：由先前的「保留 ERPNext 預設 Chart of Accounts + 官方代號 mapping」調整為「建立完整台灣官方會計項目導向的 ERPNext Chart of Accounts」。

本階段只產出設計文件，不匯入 Chart of Accounts、不停用 Account、不修改 runtime、不提交任何會計文件。

---

## 1. Decision

採用 ERPNext 官方 Chart of Accounts Importer 路線，建立一套台灣公司適用的完整 Chart of Accounts。

核心決策：

```text
1. 將 113 年度會計項目代號名稱對照表中的所有有效 code/name 納入資料來源。
2. 不是只匯入中古車 MVP 會用到的少數代號。
3. ERPNext Account Number 優先使用台灣官方會計項目代號。
4. 目前中古車買賣會用到的科目保持 enabled。
5. 目前不用、但未來可能用到的科目一併建立，但預設 disabled。
6. Group account 原則上保持 enabled，用於維持樹狀結構；不要為了減少下拉選單而停用 group。
7. Link / transaction 下拉雜訊主要透過 ledger account disabled 控制。
8. Taiwan Accounting Item Code / Account Mapping 保留，但角色降級為報表補強、驗證與未來匯出對照。
```

這個決策適合目前仍在建置初期、尚未正式大量入帳的狀態。若站台已存在正式 GL Entry、Sales Invoice、Purchase Invoice、Payment Entry 或 Journal Entry，匯入前必須先停止並重新評估。

---

## 2. Source documents

主要來源：

```text
113年度會計項目代號名稱對照表.pdf
```

ERPNext 官方能力邊界：

```text
ERPNext Chart of Accounts Importer
```

本設計假設後續會依官方 importer 格式產出可匯入檔案，而不是直接 SQL 修改 `tabAccount`。

---

## 3. Why full import instead of pruning existing accounts

先前方案是：

```text
保留 ERPNext 預設 Chart of Accounts
→ 停用不需要的 leaf accounts
→ 透過 Taiwan Accounting Item Account Mapping 補足官方代號
```

新方案改為：

```text
完整建立台灣官方會計項目導向 Chart of Accounts
→ 所有官方項目都存在
→ 日常不用者 disabled
→ 中古車核心者 enabled
```

原因：

```text
1. 使用者選 Account 時，不應看到大量 ERPNext 預設但台灣中古車業務不會用的科目。
2. 會計師看到 Account Number / Account Name 時，應能直接理解台灣報表分類。
3. 現階段尚未正式大量入帳，重建 Chart of Accounts 的成本最低。
4. 只做 MVP seed 會導致未來新增業務時還要再次匯入或補科目。
5. 完整匯入但預設 disable，可以兼顧未來擴充與日常下拉選單乾淨度。
```

---

## 4. Scope

### 4.1 Included

本階段設計納入：

```text
1. 113 年度官方會計項目代號全量資料策略。
2. ERPNext Chart of Accounts hierarchy 設計。
3. Account Number / Account Name 命名規則。
4. Group / Ledger 判斷規則。
5. Enabled / Disabled 初始狀態規則。
6. ERPNext 必要系統帳戶策略。
7. Company Defaults / Item Defaults / Warehouse / Tax Template 後續設定要求。
8. 匯入前後驗證規則。
9. 與既有 Taiwan Accounting Item Code / Mapping DocType 的關係。
```

### 4.2 Not included

本階段不做：

```text
1. 不產出正式 CSV / JSON import file。
2. 不執行 Chart of Accounts Importer。
3. 不修改 tabAccount。
4. 不直接 SQL disable account。
5. 不提交、取消或刪除任何會計文件。
6. 不處理正式電子發票 API。
7. 不取代會計師最終科目表審核。
```

---

## 5. Full source import rule

後續資料建置時，應採用以下規則。

### 5.1 Include all valid rows

從來源 PDF 解析出的所有有效代號列都必須納入資料目錄：

```text
有效列 = code 非空 + item_name 非空 + code 格式可辨識
```

有效 code 格式包含：

```text
純數字代號，例如 0100001、0202134、0300090
英數混合代號，例如 04B0001、05C2901
```

不得只挑中古車 MVP 會用的代號。

### 5.2 Do not import blank-name rows silently

PDF 解析可能出現 code 有值但中文名稱缺漏的列，例如來源文字抽取不完整。

這類資料不得直接產生 ERPNext Account，必須列入 unresolved list：

```text
code
raw_text_context
reason = missing_item_name
```

處理方式：

```text
1. 人工回看 PDF。
2. 補正 item_name。
3. 補正後才允許進入 Chart of Accounts import data。
```

### 5.3 Do not deduplicate by Chinese name

不得用中文名稱當唯一鍵。

例如：

```text
0100005 營業成本
0300090 營業成本
```

兩者中文名稱相同，但代號與報表位置不同，必須同時存在。

唯一鍵：

```text
source_year + code
```

---

## 6. Account identity rules

### 6.1 Account Number

正式台灣會計項目 account：

```text
account_number = official code
```

例：

```text
0202134 - 銷項稅額 - O
0201144 - 進項稅款 - O
0100001 - 中古車銷售收入 - O
0100005 - 中古車銷貨成本 - O
```

### 6.2 Account Name

Account Name 使用中文業務名稱。

預設：

```text
account_name = 官方項目中文名稱
```

允許針對中古車核心科目加上業務語意，但不得改變官方代號的分類意義。

例：

```text
0100001 官方名稱：營業收入總額
ERPNext Account Name 可用：中古車銷售收入
source_item_name 保留：營業收入總額
```

若名稱有業務化，必須在資料檔保留：

```text
official_item_name
account_name
name_override_reason
```

### 6.3 ERPNext Account document name

ERPNext 實際顯示通常會組成：

```text
{account_number} - {account_name} - {company_abbr}
```

例如：

```text
0202134 - 銷項稅額 - O
```

這是預期行為。

---

## 7. Hierarchy strategy

來源 PDF 是報表 / 申報項目代號表，不是完整 ERPNext 樹狀帳戶模板。因此匯入前必須建立 ERPNext hierarchy。

### 7.1 ERPNext root accounts

必須保留 ERPNext root type：

```text
Asset
Liability
Equity
Income
Expense
```

建議中文 root group：

```text
1 - 資產
2 - 負債
3 - 權益
4 - 收入
5 - 成本
6 - 費用
7 - 營業外收入及費用
8 - 所得稅費用
9 - 非經常營業損益
```

其中 `7` 依 ERPNext root_type 實作時需要拆到 Income / Expense 或以內部 group 區分，不可違反 ERPNext root_type 檢查。

### 7.2 Source prefix to statement area

初步分類規則：

| Prefix | Source meaning | ERPNext area |
|---|---|---|
| `010` | 損益 / 收入 / 費用 / 所得額 | Income / Expense |
| `0201` | 資產 | Asset |
| `0202` | 負債 | Liability |
| `0203` | 權益 | Equity |
| `030` | 成本表 / 製造成本 / 營業成本 | Expense / Cost |
| `04B` | 製造費用明細 | Expense |
| `05C` | 研究發展費用明細 | Expense |

實作時不可只靠 prefix 自動決定，必須允許人工覆寫。

---

## 8. Group vs Ledger rules

ERPNext transaction 只能過帳到 ledger account，不應過帳到 group account。

### 8.1 Group-like official rows

以下類型預設為 group account 或 reporting-only group：

```text
總額
淨額
總計
小計
營業毛利
營業淨利
全年所得額
資產總額
負債總額
權益總額
流動資產
非流動資產
流動負債
非流動負債
營業收入總額
非營業收入總額
非營業損失及費用總額
```

### 8.2 Ledger-like official rows

以下類型可作 ledger account：

```text
現金
銀行存款
應收帳款
其他應收款
商品 / 存貨
進項稅款
留抵稅額
應付帳款
其他應付款
應付稅捐
銷項稅額
預收款項
預收貨款
銷售收入
銷貨成本
修繕費
廣告費
水電瓦斯費
保險費
稅捐
佣金支出
其他費用
```

### 8.3 Ambiguous rows

以下不得自動判定為可用 ledger，需人工分類：

```text
加：其他（ ）
減：其他（ ）
其他
其他流動資產－其他
其他流動負債－其他
其他非流動負債－其他
```

預設策略：

```text
建立但 disabled = 1
需要時由會計人員啟用並命名補充用途
```

---

## 9. Enabled / Disabled policy

### 9.1 Enabled by default

中古車買賣第一版必要科目預設 enabled。

#### Cash / Bank / Receivables

```text
0201111 現金
0201112 銀行存款
0201123 應收帳款
0201129 其他應收款
```

#### Inventory / Stock

```text
0201130 存貨
0201131 商品
```

建議實際中古車庫存 ledger：

```text
0201131 - 中古車商品
```

#### VAT / Tax

```text
0201144 進項稅款
0201145 留抵稅額
0202132 應付稅捐
0202134 銷項稅額
```

#### Payables / Advances

```text
0202121 應付帳款
0202130 其他應付款
0202136 預收款項
0202137 預收貨款
0202138 其他預收款
```

#### Revenue / COGS

```text
0100001 營業收入總額
0100004 營業收入淨額
0100005 營業成本
0300090 營業成本
```

其中：

```text
0100001 / 0100004 可作報表 group 或 revenue mapping。
0100005 / 0300090 的實際 COGS 用途需由會計師確認。
MVP 可先使用 0100005 作中古車銷貨成本，0300090 disabled 或 reporting-only。
```

#### Operating expenses

```text
0100010 薪資支出
0100011 租金支出
0100012 文具用品
0100013 旅費
0100014 運費
0100015 郵電費
0100016 修繕費
0100017 廣告費
0100018 水電瓦斯費
0100019 保險費
0100020 交際費
0100022 稅捐
0100024 折舊
0100027 伙食費
0100028 職工福利
0100030 佣金支出
0100031 訓練費
0100032 其他費用
```

### 9.2 Disabled by default

以下類型全量匯入，但預設 disabled：

```text
金融資產與投資類
避險資產 / 避險負債
長期投資
基金
固定資產細項
遞耗資產
無形資產
商譽
使用權資產
出租資產
長期應收票據及催收帳款
長期負債
公司債
特別股負債
退休金準備
複雜權益調整
製造成本明細
製造費用 04B 類
研究發展費用 05C 類
停業部門損益
非常損益
會計原則變動累積影響數
少數股權相關項目
其他 / 加：其他 / 減：其他 等待人工定義項目
```

目的：

```text
1. 未來要用時不必再次匯入。
2. 日常 Account link 下拉選單不顯示大量不會用的 ledger accounts。
3. 保留完整官方代號覆蓋率。
```

---

## 10. ERPNext required internal accounts

ERPNext 可能需要一些不直接對應台灣官方代號的系統帳戶。這些不得省略。

建議保留或建立：

```text
SYS-TEMP-OPENING - Temporary Opening
SYS-STOCK-ADJUSTMENT - Stock Adjustment
SYS-SRBNB - Stock Received But Not Billed
SYS-EXP-IN-VALUATION - Expenses Included In Valuation
SYS-ROUND-OFF - Round Off
SYS-WRITE-OFF - Write Off
SYS-EXCHANGE-GAIN-LOSS - Exchange Gain / Loss
```

規則：

```text
1. system account 不使用台灣官方 code 作 account_number。
2. system account 需標記 source = ERPNext System Required。
3. system account 預設 enabled。
4. system account 不出現在台灣官方科目覆蓋率檢查中。
5. 匯出給會計師時，若有餘額或交易，必須額外列示並人工 mapping。
```

---

## 11. Account Type mapping

核心 Account Type 建議：

| Official code | Account name | ERPNext account_type |
|---|---|---|
| `0201111` | 現金 | Cash |
| `0201112` | 銀行存款 | Bank |
| `0201123` | 應收帳款 | Receivable |
| `0201131` | 商品 / 中古車商品 | Stock |
| `0201144` | 進項稅款 | Tax |
| `0201145` | 留抵稅額 | Tax |
| `0202121` | 應付帳款 | Payable |
| `0202134` | 銷項稅額 | Tax |
| `0202136` | 預收款項 | 空白或 Payable-like，依 ERPNext 驗證決定 |
| `0100001` | 中古車銷售收入 | Income Account |
| `0100005` | 中古車銷貨成本 | Cost of Goods Sold |

注意：

```text
ERPNext account_type 會影響 Sales Invoice、Purchase Invoice、Payment Entry、Stock、Tax Template 驗證。
不可只依官方名稱建立 Account，必須填對 account_type。
```

---

## 12. Import data model

後續實作應先建立一份 machine-readable source catalog，再產生 ERPNext importer file。

建議資料檔：

```text
used_car_erp/data/taiwan_coa_113_full.json
或
used_car_erp/data/taiwan_coa_113_full.csv
```

每筆欄位：

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

### 12.1 `is_enabled_by_default`

```text
1 = 匯入後 enabled
0 = 匯入後 disabled
```

### 12.2 `manual_review_required`

以下情況需標記：

```text
1. 中文名稱缺漏或不完整。
2. 同名但不同代號，且用途容易混淆。
3. ERPNext root_type 無法單靠 prefix 判斷。
4. 可能是公式列 / 小計列 / 報表列，不一定應作 ledger。
5. 會影響 COGS / stock / tax posting。
```

---

## 13. Import file strategy

Chart of Accounts importer file 應由 catalog 產生，不手工維護。

建議流程：

```text
113年度 PDF
→ 人工校對後的 taiwan_coa_113_full.json/csv
→ generate_erpnext_chart_of_accounts_import_file
→ ERPNext Chart of Accounts Importer CSV / JSON
```

產出檔應另存：

```text
exports/chart_of_accounts/taiwan_used_car_full_coa_113.csv
```

不要把臨時下載的官方 PDF commit 進 repo。

---

## 14. Pre-import gates

正式匯入前必須全部通過：

```text
1. `tabGL Entry` count = 0，或明確確認這是可重建的 dev site。
2. 已備份 site：bench --site erpnext.localhost backup --with-files。
3. 已匯出現有 tabAccount 清單。
4. 已確認 Company = OO / abbr = O。
5. 已確認沒有正式 Sales Invoice / Purchase Invoice / Payment Entry / Journal Entry。
6. 已確認 Item / Warehouse / Tax Template 可在匯入後重新設定。
7. 已由使用者確認要覆蓋現有 Chart of Accounts。
```

如果任一 gate 不通過：

```text
不得執行 Chart of Accounts Importer。
```

---

## 15. Post-import setup

匯入完成後，必須設定：

### 15.1 Company Defaults

```text
default_cash_account
default_bank_account
default_receivable_account
default_payable_account
default_income_account
default_expense_account / default COGS
round_off_account
write_off_account
exchange_gain_loss_account
stock_received_but_not_billed
stock_adjustment_account
```

實際欄位名稱以站台版本為準；不可假設所有 GitHub develop branch 欄位都存在。

### 15.2 Item / Item Group Defaults

中古車 Item / Item Group 應設定：

```text
default_inventory_account = 0201131 - 中古車商品
income_account = 0100001 - 中古車銷售收入
default_cogs_account = 0100005 - 中古車銷貨成本
```

### 15.3 Warehouse

中古車庫存倉應確認：

```text
Warehouse.account = 0201131 - 中古車商品
```

若 ERPNext 版本允許空白並使用 parent/company default，也需在 QA 中確認 stock accounting posting 正確。

### 15.4 Sales Taxes and Charges Template

台灣營業稅 5% template：

```text
account_head = 0202134 - 銷項稅額
charge_type = On Net Total
rate = 5
included_in_print_rate = 依售價是否含稅決定
```

### 15.5 Purchase tax / input VAT

進項稅相關科目：

```text
0201144 - 進項稅款
0201145 - 留抵稅額
```

是否由 Purchase Invoice / Purchase Taxes and Charges Template 使用，需等採購 / 整備費發票流程設計後決定。

---

## 16. Relationship with existing custom DocTypes

### 16.1 Taiwan Accounting Item Code

保留。

用途改為：

```text
1. 官方代號 master data。
2. 檢查 Chart of Accounts 是否覆蓋所有官方 code。
3. 會計師匯出時提供官方分類 metadata。
4. 未來年度更新比對。
```

### 16.2 Taiwan Accounting Item Account Mapping

保留，但角色降低。

新的主要情境：

```text
1. ERPNext system account 無官方 code 時，補 mapping。
2. 一個官方 code 拆成多個公司內部 ledger 時，提供報表彙總 mapping。
3. Account Name 因業務需求覆寫時，仍可回指 official item。
4. 未來報表需要多目的 mapping，例如 Sales Revenue / COGS / Input VAT / Output VAT。
```

### 16.3 Existing P1-ACC-1 / P1-ACC-2 notes

P1-ACC-1 / P1-ACC-2 的保守設計仍可作為 fallback。

但本文件採用新決策：

```text
若在正式交易前重建 Chart of Accounts 可行，優先使用完整台灣 COA import。
若已經有正式交易，才退回原本的 mapping-only / pruning 方案。
```

---

## 17. Validation rules

### 17.1 Source coverage validation

```text
count(valid source rows) = count(import catalog official rows)
missing_codes = []
duplicate_codes = [] for source_year = 113
blank_item_name = []
manual_review_required rows explicitly listed
```

### 17.2 Account structure validation

```text
Every ledger account has parent_account.
Every group account has valid root_type.
Every enabled transaction account has correct account_type if ERPNext requires it.
Every disabled account has disabled_reason.
No two enabled ledger accounts use the same official code unless explicitly allowed.
```

### 17.3 ERPNext runtime validation

最低 QA：

```text
Create Customer
Create Supplier
Create Item / Serial No
Create Sales Invoice draft
Apply Sales Taxes and Charges Template
Create Journal Entry draft
Create Payment Entry draft if enabled later
Create Stock Entry / Sales Invoice update_stock path if enabled later
```

本階段文件不執行 runtime QA，但後續 import phase 必須執行。

---

## 18. Rollback strategy

匯入前必須具備：

```text
1. bench backup file
2. existing tabAccount export
3. generated import file committed or archived
4. source catalog committed
```

若匯入後發現錯誤：

```text
1. 優先在 dev site restore backup。
2. 不在 production 直接批次 rename / delete Account。
3. 不直接 SQL rollback。
```

---

## 19. Implementation sequence

### P1-ACC-3

```text
本文件：完整台灣 Chart of Accounts 匯入策略。
不改 runtime。
不匯入。
```

### P1-ACC-4

```text
建立 taiwan_coa_113_full source catalog。
納入 113 年度 PDF 所有有效 code/name。
標記 group/ledger、enabled default、manual review。
新增 validation function。
```

### P1-ACC-5

```text
產生 ERPNext Chart of Accounts Importer 檔案。
不自動匯入。
提供人工下載 / 手動 importer 操作。
```

### P1-ACC-6

```text
Dev site 手動匯入。
設定 Company Defaults / Item Defaults / Warehouse / Tax Template。
執行最小交易 QA。
```

### P1-ACC-7

```text
若 dev site QA 通過，再決定是否重建正式站台。
```

---

## 20. Current recommendation

目前建議改走完整台灣 COA import 路線：

```text
1. 不再繼續手動停用大量 ERPNext 預設科目。
2. 不只匯入中古車 MVP 代號。
3. 將 113 年度所有有效官方項目納入完整 source catalog。
4. 目前不用的 ledger accounts 預設 disabled。
5. 中古車買賣核心科目 enabled。
6. 匯入前先完成 source catalog + importer 檔案 + backup gate。
7. 匯入後重新設定 ERPNext defaults 與稅務 template。
```

這會讓日常 Account 下拉選單乾淨，同時避免未來新增業務時還要重新補整份官方科目表。

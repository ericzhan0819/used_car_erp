# 台灣中古車稅務與成本設計文件

Last reviewed: 2026-06-12

本文件用於定義 `used_car_erp` 在台灣有限公司、中古自用小客車買賣情境下的稅務與成本設計方向。

本文件不是報稅建議，也不取代會計師判斷。系統第一階段只提供內部管理估算、交會計師檢查資料與後續功能規格基準；正式申報與入帳規則須由會計師確認後再進入自動化。

交車前最終檢查面板會引用單車成本與預估營業稅摘要，協助使用者在 Phase 3 前確認資料完整性；此面板不代表正式申報、會計入帳或 COGS。

---

## 1. 適用業務情境

目前使用者明確條件：

```text
公司型態：有限公司
營業模式：中古自用小客車買賣
車源：個人、同業車商、拍場
發票：預期需開立統一發票
系統目的：知道單車賺賠、預估營業稅影響、產出會計師可檢查資料
正式申報：仍由會計師確認
```

本文件目前只涵蓋：

```text
中古自用小客車買賣
一般 5% 營業稅估算
舊乘人小汽車第 15-1 條特殊扣抵設計
單車成本與管理毛利
交會計師報表資料結構
```

本文件暫不涵蓋：

```text
租賃業務
進口車專案
機車買賣
貨車 / 商用車
委售車
金融貸款分潤
電子發票 API 串接
正式營業稅申報檔
正式營利事業所得稅申報
```

---

## 2. 官方法規依據摘要

### 2.1 營業稅基本公式

《加值型及非加值型營業稅法》第 15 條規定：

```text
當期應納或溢付營業稅額 = 當期銷項稅額 - 進項稅額
```

進項稅額是營業人購買貨物或勞務時，依規定支付之營業稅額。

系統設計意義：

```text
一般公司支出若有合法可扣抵憑證，原則上可作為一般進項稅額。
中古車本體若向非一般稅額計算者買入，不能簡化為一般進項發票扣抵，需走第 15-1 條特殊處理。
```

### 2.2 舊乘人小汽車 / 機車特殊扣抵

《加值型及非加值型營業稅法》第 15-1 條規定：

營業人銷售向「非依一般稅額計算者」購買的舊乘人小汽車及機車，得以購入成本按營業稅徵收率換算進項稅額。

公式：

```text
15-1 可扣抵進項稅額 = 購入成本 × 徵收率 / (1 + 徵收率)
```

限制：

```text
應於申報該車銷售額當期申報扣抵。
超過該車銷項稅額的部分不得扣抵。
```

系統設計意義：

```text
向個人購入中古自用小客車時，通常沒有一般進項統一發票。
系統不得把買車款當成一般進項稅發票。
系統應建立「15-1 特殊扣抵估算」欄位或摘要。
Sales Invoice 仍應保留完整成交價，不應只用毛利差額開立。
```

### 2.3 不得扣抵進項稅額

《加值型及非加值型營業稅法》第 19 條列出不得扣抵銷項稅額的進項稅額，包含：

```text
未依規定取得並保存憑證
非供本業及附屬業務使用
交際應酬用貨物或勞務
酬勞員工個人之貨物或勞務
自用乘人小汽車
```

系統設計意義：

```text
支出不能只分「有發票 / 沒發票」。
需要額外標記 tax_deductibility。
交際費、自用乘人小汽車、非本業支出不可預設進項可扣抵。
買來轉售的中古車庫存，需與公司自用乘人小汽車區分。
```

### 2.4 統一發票與含稅定價

《加值型及非加值型營業稅法》第 32 條規定：

```text
營業人銷售貨物或勞務，應依規定時限開立統一發票交付買受人。
應稅貨物或勞務之定價應內含營業稅。
```

系統設計意義：

```text
系統銷售金額應保留完整成交價。
若成交價為含稅價，應拆出未稅銷售額與銷項稅額供管理估算。
不要用「毛利」取代發票金額。
```

### 2.5 營業稅申報期

《加值型及非加值型營業稅法》第 35 條規定：

```text
營業人除另有規定外，不論有無銷售額，應以每二月為一期，於次期開始十五日內申報銷售額、應納或溢付營業稅額。
使用統一發票者，並應檢附統一發票明細表。
```

系統設計意義：

```text
系統未來應以兩個月為一個 VAT period 彙總。
車輛銷售日期 / 發票日期會決定進入哪一期營業稅估算。
15-1 特殊扣抵應與該車銷售額同一期呈現。
```

### 2.6 存貨與實際成本

《所得稅法》第 44 條規定，商品等存貨估價以實際成本為準；成本高於淨變現價值時，得以淨變現價值為準，跌價損失得列銷貨成本。

《所得稅法》第 45 條規定，實際成本包含取得價格，以及因取得並為適於營業上使用而支付的一切必要費用；因擴充、換置、改良、修理而增加價值或效能者，得加入實際成本餘額計算。

系統設計意義：

```text
買車成本應屬單車庫存成本。
直接讓車輛可出售、提高價值或效能的整備與修理，系統可先歸入單車成本，並標記供會計師確認。
一般期間費用不可硬塞到單車成本。
```

---

## 3. 本專案稅務設計決策

### 3.0 P1-TAX-0：車輛買入憑證邊界

P1-TAX-0 決策：車輛頁只記錄買入憑證 / 是否取得可扣抵統一發票，不顯示稅額估算，也不處理正式 Sales Invoice 稅務設定。

```text
統一發票 → 一般發票扣抵。
未取得、買賣合約、讓渡書、匯款紀錄、收據 → 15-1 特殊扣抵初步判斷。
拍場單據、其他、空值 → 待會計確認，Sales Invoice 草稿建立前應阻擋。
```

正式 Sales Invoice 稅務 template wiring 留到 P1-TAX-1。15-1 扣抵估算只作內部會計 / 報稅輔助，不塞進客戶 Sales Invoice 明細。

### 3.1 系統採「會計師確認前估算」模式

系統第一階段不直接宣告正式稅額。

系統欄位與報表命名應使用：

```text
預估營業稅
預估 15-1 可扣抵進項稅額
預估單車毛利
會計師確認狀態
```

避免使用：

```text
正式應納稅額
已申報稅額
最終營所稅
```

除非後續已有會計師確認流程。

### 3.2 Sales Invoice 永遠保留完整成交價

禁止設計成：

```text
Sales Invoice 只開毛利差額
```

建議設計成：

```text
Sales Invoice = 完整成交價
Tax Summary = 另算銷項稅額、15-1 可扣抵進項稅額、預估營業稅影響
```

理由：

```text
營業稅法第 32 條要求應稅貨物或勞務定價內含營業稅。
第 15-1 條處理的是可扣抵進項稅額，不是把銷售發票金額改成毛利。
```

### 3.3 車輛採單車成本制

每台車獨立管理成本：

```text
單車總成本 = 車輛購入成本 + 直接取得成本 + 直接整備成本 + 直接修理成本 + 其他會計師確認可歸屬成本
```

用途：

```text
判斷單車賺賠
建立 COGS / 成本結轉基礎
提供營利事業所得稅成本資料
提供會計師查核憑證索引
```

### 3.4 支出需分稅務用途與管理用途

同一筆支出至少需要兩層分類：

```text
management_cost_category：管理用成本分類
vat_deductibility：營業稅進項扣抵屬性
```

例如：

| 支出 | management_cost_category | vat_deductibility |
|---|---|---|
| 買車款 | vehicle_purchase_cost | depends_on_source |
| 個人賣車買入 | vehicle_purchase_cost | vat_15_1_special |
| 同業開發票賣車 | vehicle_purchase_cost | normal_input_vat_or_review |
| 拍場成交費 | vehicle_direct_cost | review_required |
| 過戶費 | vehicle_direct_cost | review_required |
| 板金 / 烤漆 / 修理 | vehicle_reconditioning_cost | normal_input_vat_or_review |
| 美容清潔 | vehicle_reconditioning_cost | normal_input_vat_or_review |
| 廣告 | operating_expense | normal_input_vat_or_review |
| 房租水電網路 | operating_expense | normal_input_vat_or_review |
| 交際應酬 | operating_expense | non_deductible_input_vat |
| 公司自用乘人小汽車 | fixed_asset_or_expense | non_deductible_input_vat |

---

## 4. 車源稅務模式

### 4.1 個人賣車

建議預設：

```text
source_type = individual
vehicle_tax_mode = used_passenger_car_vat_15_1
```

系統估算：

```text
sale_output_vat = tax_inclusive_sale_price × tax_rate / (1 + tax_rate)
vat_15_1_input_credit = purchase_cost × tax_rate / (1 + tax_rate)
vat_15_1_input_credit_capped = min(vat_15_1_input_credit, sale_output_vat)
estimated_vehicle_vat_payable = sale_output_vat - vat_15_1_input_credit_capped
```

狀態：

```text
需會計師確認買方、車種、憑證與是否確實適用第 15-1 條。
```

### 4.2 同業車商

建議預設：

```text
source_type = dealer
vehicle_tax_mode = review_required
```

原因：

```text
同業可能是一般營業人並開立統一發票。
也可能有不同代收代付、拍賣或轉售型態。
不能一律套 15-1。
```

系統要記錄：

```text
是否取得統一發票
發票號碼
發票日期
發票金額
發票稅額
對方統編
是否可扣抵
會計師確認狀態
```

### 4.3 拍場

建議預設：

```text
source_type = auction
vehicle_tax_mode = auction_review_required
```

原因：

```text
拍場可能同時存在車款、手續費、代收代付、發票與非發票憑證。
車款本身與拍場服務費可能稅務屬性不同。
```

系統要拆分：

```text
車輛成交價
拍場手續費
拖車 / 停車 / 其他費用
憑證類型
可扣抵狀態
```

---

## 5. 建議欄位設計

### 5.1 Used Car Vehicle 建議欄位

未來可在 `Used Car Vehicle` 增加稅務與成本摘要欄位。

```text
purchase_source_type
vehicle_tax_mode
purchase_price_tax_inclusive
purchase_price_tax_exclusive
purchase_vat_amount
purchase_document_type
purchase_document_no
purchase_document_date
purchase_counterparty_name
purchase_counterparty_tax_id
purchase_counterparty_is_business
accountant_tax_review_status
accountant_tax_review_note
```

建議選項：

```text
purchase_source_type:
- individual
- dealer
- auction
- other

vehicle_tax_mode:
- used_passenger_car_vat_15_1
- normal_input_vat
- non_deductible_input_vat
- auction_review_required
- accountant_review_required

accountant_tax_review_status:
- pending
- reviewed
- adjusted
- locked
```

### 5.2 單車成本欄位

```text
vehicle_purchase_cost
vehicle_direct_acquisition_cost
vehicle_reconditioning_cost
vehicle_other_capitalized_cost
vehicle_total_cost
cost_review_status
cost_review_note
```

### 5.3 稅務估算欄位

```text
sale_price_tax_inclusive
sale_price_tax_exclusive
sale_output_vat
vat_15_1_input_credit
vat_15_1_input_credit_capped
estimated_vehicle_vat_payable
vat_period
vat_review_status
vat_review_note
```

---

## 6. 建議 DocType / 報表設計

### 6.1 Used Car Tax Summary

可作為每台車的稅務摘要，不直接取代 ERPNext Sales Invoice。

建議欄位：

```text
vehicle
reservation
sales_invoice
customer
company
posting_date
vat_period
source_type
vehicle_tax_mode
purchase_cost
sale_price_tax_inclusive
tax_rate
sale_output_vat
vat_15_1_input_credit
vat_15_1_input_credit_capped
estimated_vehicle_vat_payable
normal_input_vat_amount
non_deductible_input_vat_amount
accountant_review_status
accountant_review_note
locked_at
locked_by
```

系統邏輯：

```text
Sales Invoice 草稿建立後，可預覽 Used Car Tax Summary。
Sales Invoice 正式提交前，Tax Summary 必須至少是 pending/review_required，不得自動視為 final。
會計師確認後才能 locked。
```

### 6.2 Used Car Cost Summary

可作為單車成本與毛利摘要。

```text
vehicle
purchase_cost
direct_acquisition_cost
reconditioning_cost
other_capitalized_cost
total_vehicle_cost
sale_price_tax_exclusive
gross_profit_before_period_expense
estimated_vehicle_vat_payable
management_profit_estimate
accountant_review_status
```

### 6.3 VAT Period Report

以兩個月為一期。

```text
period
company
sales_invoice_total
output_vat_total
normal_input_vat_total
used_vehicle_15_1_credit_total
non_deductible_input_vat_total
estimated_vat_payable
accountant_review_status
```

---

## 7. 成本分類決策

### 7.1 歸入單車成本

預設歸入單車成本：

```text
買車款
拍場車輛成交直接費用
拖車費
過戶前必要處理費
驗車必要費
板金
烤漆
機械修理
內裝整理
美容清潔
為該車銷售前必要處理的零件與工資
```

條件：

```text
能明確對應某一台車。
是取得、整備、修理或使該車達可銷售狀態所必要。
保留憑證。
```

### 7.2 列一般營業費用

預設列一般營業費用：

```text
廣告費
店租
水電
網路
電話
系統費
辦公用品
一般員工薪資
一般交通費
非特定車輛的營運費用
```

### 7.3 需會計師確認

```text
牌照稅
燃料費
保險
過戶費
規費
代收代付款
交車時代辦費
拍場多項費用包在一起的項目
同業交易未明確拆稅額的項目
```

這些費用可能因交易安排不同而有不同處理方式，系統應先標記為 `accountant_review_required`。

Phase Cost-1 已建立單車成本摘要基礎。`Used Car Vehicle Cost` 用於記錄直接歸屬於單台車的整備、維修、美容、拍場費、拖車費與其他成本。

只有 `capitalization_mode = 單車成本` 的資料會納入 `Used Car Vehicle.total_cost`。此階段的 `total_cost` / `gross_margin` 只作管理估算，不代表正式會計成本、COGS 或稅務申報結果。

車輛頁提供「新增單車成本」快速入口，可直接建立 `Used Car Vehicle Cost` 並帶入目前車輛。此 UX 僅用於管理成本紀錄，不代表正式會計成本、COGS 或稅務申報結果。

---

## 8. 公式設計

### 8.1 含稅價拆未稅與稅額

```text
tax_exclusive_amount = tax_inclusive_amount / (1 + tax_rate)
vat_amount = tax_inclusive_amount - tax_exclusive_amount
```

若稅率為 5%：

```text
vat_amount = tax_inclusive_amount × 5 / 105
```

### 8.2 第 15-1 條估算

```text
sale_output_vat = sale_price_tax_inclusive × tax_rate / (1 + tax_rate)
vat_15_1_input_credit = purchase_cost × tax_rate / (1 + tax_rate)
vat_15_1_input_credit_capped = min(vat_15_1_input_credit, sale_output_vat)
estimated_vehicle_vat_payable = sale_output_vat - vat_15_1_input_credit_capped
```

### 8.3 單車毛利

```text
sale_revenue_tax_exclusive = sale_price_tax_inclusive / (1 + tax_rate)
vehicle_total_cost = purchase_cost + direct_acquisition_cost + reconditioning_cost + other_capitalized_cost
gross_profit_before_period_expense = sale_revenue_tax_exclusive - vehicle_total_cost
```

### 8.4 管理用估算利潤

```text
management_profit_estimate = gross_profit_before_period_expense - allocated_period_expense_optional
```

第一版不建議強制分攤期間費用到單車，避免增加操作負擔。

---

## 9. ERPNext 整合邊界

### 9.1 Sales Invoice

Sales Invoice 應承載：

```text
完整成交價
Customer
Company
Item
Serial No
Warehouse
Income Account
Update Stock
```

Sales Invoice 不應承載：

```text
15-1 可扣抵進項稅額
單車所有成本明細
會計師稅務審核狀態
```

這些應放在自訂摘要或報表。

### 9.2 Journal Entry

已存在的訂金與尾款入帳邏輯屬於成交前金流：

```text
借：現金 / 銀行
貸：預收款 / 暫收款
```

正式交車後的預收款沖轉應另行設計：

```text
借：預收款 / 暫收款
貸：應收帳款
```

但本文件不實作自動沖轉。

### 9.3 Stock / COGS

Sales Invoice 提交並 update stock 後，ERPNext 會進入正式出庫與庫存異動情境。

後續需確認：

```text
車輛 Item 是否正確設定為 stock item
Serial No 是否與車輛一致
Warehouse 是否為實際所在倉
COGS 科目與庫存科目是否正確
單車成本是否已進 ERPNext Stock Valuation
```

本文件不直接處理 COGS 自動化。

---

## 10. Phase 建議

### Phase Tax-0：文件與決策

目前文件階段。

輸出：

```text
本文件
會計師確認問題清單
後續欄位設計
```

### Phase Tax-1：稅務標記欄位

目標：先讓每台車標記來源與稅務模式。

Phase Tax-1 已實作 Tax Metadata Foundation。

目前只在 `Used Car Vehicle` 收集車源類型、稅務模式、買入憑證、買入金額與稅務確認狀態。

此階段不計算正式營業稅、不建立 Tax Summary、不提交 Sales Invoice、不做稅務入帳。

UX 決策：日常操作畫面避免過度使用「會計師確認」字眼，改以「稅務確認」呈現；正式申報與最終稅務判斷仍須由會計師或稅務人員確認。

```text
purchase_source_type
vehicle_tax_mode
purchase_document_type
purchase_document_no
purchase_price
tax_review_status
tax_review_note
```

Phase Tax-1 欄位選項：

```text
vehicle_tax_mode:
- 待確認
- 15-1 特殊扣抵
- 一般發票扣抵
- 不可扣抵
- 拍場需確認

tax_review_status:
- 待補資料
- 待確認
- 已初步判斷
- 已確認
- 已調整
- 已鎖定
```

不做正式稅額入帳。

### Phase Tax-2：單車成本摘要

目標：讓每台車能顯示：

```text
買車成本
整備成本
總成本
未稅銷售收入
粗估毛利
```

Phase Cost-1 已建立單車成本摘要基礎。`Used Car Vehicle Cost` 記錄直接歸屬於單台車的成本；只有 `capitalization_mode = 單車成本` 會納入 `Used Car Vehicle.total_cost`，`total_cost` / `gross_margin` 只作管理估算，不代表正式會計成本、COGS 或稅務申報結果。

車輛頁提供「新增單車成本」快速入口，可直接建立 `Used Car Vehicle Cost` 並帶入目前車輛。此 UX 僅用於管理成本紀錄，不代表正式會計成本、COGS 或稅務申報結果。

Phase Tax-2 已建立單車損益與預估營業稅摘要基礎。

系統會以成交價、買入金額、單車直接成本、稅務模式與成本進項稅狀態估算：

- 預估銷項稅
- 預估可扣抵稅額
- 預估應納營業稅
- 扣稅後管理毛利

此摘要只作內部管理估算，不代表正式營業稅申報、所得稅申報、會計分錄或 COGS。

### Phase Tax-3：15-1 預估摘要

目標：在已建立 Sales Invoice 草稿後，建立或顯示：

```text
銷項稅額
15-1 可扣抵進項稅額
可扣抵上限
預估該車營業稅影響
```

### Phase Tax-4：營業稅期別報表

目標：兩個月一期彙總：

```text
銷項稅額
一般進項稅額
15-1 特殊扣抵
不可扣抵進項
預估應納 / 留抵
會計師調整欄位
```

### Phase Tax-5：會計師確認與鎖定

目標：會計師確認後鎖定：

```text
車輛稅務模式
成本歸屬
15-1 扣抵額
申報期別
```

鎖定後才允許後續正式稅務報表或自動化。

---

## 11. 會計師確認問題清單

以下問題需在功能正式自動化前確認：

```text
1. 有限公司中古自用小客車買賣是否全部依一般稅額 5% 申報？
2. 向個人買入的自用小客車是否適用營業稅法第 15-1 條？
3. 第 15-1 條的購入成本範圍是否只含車款，還是可含拍場費、過戶費、整備費？
4. Sales Invoice 是否應以完整成交價開立？
5. 是否需要電子發票串接，或初期只保留 Sales Invoice / 發票資訊供人工開立？
6. 同業車商車源若有統一發票，是否依一般進項稅額扣抵？
7. 拍場車源中，車款、手續費、代收代付項目如何拆分稅務屬性？
8. 整備、維修、烤漆、美容是否歸入單車成本，或哪些項目應列期間費用？
9. 牌照稅、燃料費、保險、規費、過戶費在不同情境下如何分類？
10. 預收款沖轉分錄是否使用「借：預收款 / 貸：應收帳款」？
11. Sales Invoice submit 時的 COGS / Stock Valuation 是否能正確反映單車成本？
12. 兩個月營業稅申報報表需要哪些欄位與附件索引？
```

---

## 12. Source references

Official sources used for this design review:

```text
加值型及非加值型營業稅法（全國法規資料庫）
https://law.moj.gov.tw/LawClass/LawAll.aspx?pcode=G0340080

所得稅法（全國法規資料庫）
https://law.moj.gov.tw/LawClass/LawAll.aspx?pcode=G0340003
```

Key articles referenced:

```text
加值型及非加值型營業稅法：第 15 條、第 15-1 條、第 19 條、第 32 條、第 35 條
所得稅法：第 44 條、第 45 條
```

---

## 13. Current project decision

本專案目前決策：

```text
1. 先不自動報稅。
2. 先不自動提交 Sales Invoice。
3. 先不自動產生正式稅務調整分錄。
4. 先建立單車成本、稅務模式、15-1 估算與會計師確認欄位。
5. Sales Invoice 保留完整成交價。
6. 中古車 15-1 特殊扣抵放在 Tax Summary，不放在 Sales Invoice 金額本身。
7. 任何正式申報數字都必須有 accountant_review_status。
```

# P1-UX-TAX-0 Used Car Vehicle Simplified UX And 15-1 Tax Boundary Spec

Last reviewed: 2026-06-19

Phase: `P1-UX-TAX-0`

## 1. Background

P1-ACC-6H-0 已完成 formal sale accounting closure inspector。針對 `ACC-SINV-2026-00004` 的檢查已回傳 `status = pass`、`closed = true`、`ready_for_ui_review = true`，代表正式售車會計閉環已跑通。

目前已完成的閉環包含：車輛已售出、Sales Invoice 已提交、Sales Invoice GL / SLE 已存在、`formal_delivery_status` 已同步為 `已完成`、advance settlement Journal Entry 已提交、Sales Invoice outstanding amount 已歸零。

因此會計 runtime 現階段應停止擴張。下一步不再把更多 accounting action button 塞進 Used Car Vehicle form，而是轉向 UX 簡化與 15-1 稅務語意校正。

後續 UI 應遵守：

```text
業務頁只輸入業務資料
會計頁才看傳票與入帳
車輛頁只看簡單狀態
複雜檢查收進「更多資訊」或「會計狀態」
同一時間只顯示一個下一步
```

會計技術細節應移往「會計作業」workspace、dashboard 或 review pages，不應繼續佔滿車輛表單。

## 2. Core UX Principle

```text
Used Car Vehicle = 車輛業務事實頁
會計作業 = 傳票 / 入帳 / 正式文件審核頁
Sales Invoice / Journal Entry / GL / SLE = 技術會計文件，只顯示摘要與狀態，不佔滿車輛頁
```

車輛頁主要分成四個主區塊：

```text
基本資料
採購
售車
收支
```

使用者主要操作語言不應再是 `formal delivery`、`preflight`、`Sales Invoice`、`Journal Entry`。這些可以存在於會計狀態摘要、更多資訊或會計作業頁，但不是車輛頁的主要語言。

## 3. Vehicle Form Proposed Sections

### A. 基本資料

基本資料只放車子本體資料：

```text
車牌
VIN / 車身號碼
品牌
車型
年份
顏色
里程
排氣量
燃料
變速系統
車況
入庫日期
庫存狀態
備註
```

基本資料不要放：

```text
Sales Invoice
Journal Entry
GL Entry
Stock Ledger Entry
預收款沖轉
正式交車狀態技術欄位
成本摘要
損益估算
稅務 preflight
大量紅色警告
完整檢查清單
```

### B. 採購

採購區只處理買進這台車的資料：

```text
買入金額
賣方 / 車主 / 來源
車源類型
買入日期
買入憑證
過戶 / 牌照資料
採購備註
採購付款狀態
```

採購區可以顯示簡短稅務提示：

```text
購車價將作為 15-1 購入可扣抵稅額估算基礎。
整備、維修、美容、拍場費、代辦費等後續支出不併入 15-1 購入成本。
```

### C. 售車

售車區只處理賣車：

```text
成交價
客戶
成交日期
訂金
尾款
交車日期
Sales Invoice 狀態
售車稅務模式
售車備註
```

15-1 / 營業稅相關摘要只應出現在售車區或會計稅務摘要，不應散落在基本資料：

```text
售價
售車稅務模式：15-1 / 一般 / 不適用 / 待確認
銷項稅額估算
15-1 可扣抵估算
預估本車營業稅
售車稅務確認狀態
```

### D. 收支

收支區集中所有金流與支出：

```text
採購付款
整備支出
維修支出
美容支出
代辦費
拍場費
訂金收入
尾款收入
其他收入
其他支出
```

使用者新增收支時只看業務欄位：

```text
類型
日期
金額
收 / 支
付款方式
對象
備註
```

系統背後流程：

```text
金流紀錄
→ 傳票草稿
→ 會計確認
→ 正式 Journal Entry
```

不要要求業務人員理解：

```text
debit
credit
liability account
receivable account
Sales Invoice.debit_to
Journal Entry Account
GL Entry
Stock Ledger Entry
```

## 4. 15-1 Tax Boundary

核心規則：

```text
15-1 只用在「售車營業稅」。
購入成本 = 購車價。
整備費、維修費、美容費、拍場費、代辦費，不併入 15-1 的中古車購入成本。
其他營業稅、營所稅照一般稅法與會計師判斷處理。
```

估算公式：

```text
售車銷項稅額 = 售車價 ÷ 1.05 × 5%
15-1 購入可扣抵稅額 = 購車價 ÷ 1.05 × 5%
實際可扣抵 = min(購入可扣抵稅額, 銷項稅額)
預估本車營業稅 = 銷項稅額 - 實際可扣抵
```

範例：

```text
買車價：315,000
可扣抵進項稅額 = 315,000 ÷ 1.05 × 5% = 15,000

售車價：378,000
銷項稅額 = 378,000 ÷ 1.05 × 5% = 18,000

15-1 可扣抵額 = min(15,000, 18,000) = 15,000
本車應納營業稅估算 = 18,000 - 15,000 = 3,000
```

此估算不是電子發票、不是營業稅申報、不是營所稅結算，也不是 Sales Invoice tax row 的替代規則。正式申報仍需會計師或稅務人員確認。

## 5. purchase_price Semantic

`purchase_price` 的語意必須固定為：

```text
purchase_price = 購車價，不包含整備費、維修費、美容費、拍場費、代辦費或其他後續費用。
```

用途：

```text
單車購入成本
15-1 可扣抵進項稅額計算基礎
營所稅成本基礎之一
```

不應混入：

```text
整備費
維修費
美容費
拍場費
代辦費
其他後續費用
```

如果後續需要呈現完整管理成本，應使用單車成本或收支資料另外計算，不得回頭污染 `purchase_price`。

## 6. Management Profit vs 15-1 Tax Estimate

系統應清楚區分兩套數字。

### A. 單車管理損益

單車管理損益是給老闆看真實賺多少：

```text
成交價
- 購車價
- 整備費
- 維修費
- 美容費
- 拍場費
- 其他直接支出
= 管理毛利
```

這裡可以包含整備費、維修費、美容費、拍場費、代辦費與其他直接支出。

### B. 15-1 營業稅估算

15-1 營業稅估算只用於售車營業稅估算：

```text
售車銷項稅額 = 售車價 ÷ 1.05 × 5%
15-1 購入可扣抵稅額 = 購車價 ÷ 1.05 × 5%
實際可扣抵 = min(購入可扣抵稅額, 銷項稅額)
預估本車營業稅 = 銷項稅額 - 實際可扣抵
```

這裡不得包含：

```text
整備費
維修費
美容費
拍場費
代辦費
其他後續支出
```

## 7. Accounting Status Summary For Vehicle Page

車輛頁只顯示簡單狀態，不顯示完整會計技術細節。

建議狀態：

```text
未開始
待會計確認
已建立發票草稿
發票已提交
預收款已沖轉
會計閉環完成
需補資料
錯誤需處理
```

可顯示摘要：

```text
Sales Invoice：已提交 / 草稿 / 未建立
預收款沖轉：已完成 / 未完成
會計閉環：已完成 / 未完成
```

技術細節放進「更多資訊」或「會計作業」：

```text
Sales Invoice name
Journal Entry name
GL Entry count
SLE count
preflight detail
closure inspector report
```

## 8. Primary Action Rule

同一時間只顯示一個主動作。

範例：

```text
尚未入庫 → 完成入庫
庫存中 → 建立保留 / 售車
保留中且尾款未建立 → 建立尾款收款
訂金與尾款已入帳 → 確認成交
已售出但未建立發票草稿 → 建立售車發票草稿
發票草稿已建立 → 提交售車發票
發票已提交但 formal status 未同步 → 同步正式交車狀態
formal status 已完成但未沖轉 → 建立預收款沖轉
沖轉完成 → 會計閉環完成
```

這些步驟不應全部攤在頁首。車輛頁只顯示當前下一步，其餘資訊收進狀態摘要、更多資訊或會計作業頁。

## 9. Accounting Workspace Boundary

會計作業 workspace 應放：

```text
待審核傳票草稿
金流紀錄
傳票草稿
正式 Journal Entry
Sales Invoice
會計閉環 inspector
異常資料清單
```

車輛頁不應顯示完整：

```text
Journal Entry Account
GL Entry
Stock Ledger Entry
debit / credit detail
preflight raw report
```

車輛頁可以保留摘要與連結，但完整審核、排錯、傳票分錄與 ledger details 應移到會計作業脈絡。

## 10. Non-goals

本規格階段不做：

```text
不改 runtime
不改 DocType JSON
不改 Workspace JSON
不改 JS
不新增按鈕
不新增 service
不新增 test
不改 Sales Invoice
不改 Journal Entry
不改 GL Entry
不改 Stock Ledger Entry
不做 15-1 runtime 計算
不做 UI 實作
不做報表
不做 dashboard
不做電子發票
不做會計申報
不做租賃
```

## 11. Follow-up Phases

後續建議階段：

```text
P1-UX-TAX-1：Used Car Vehicle Form Section Layout Refactor
P1-UX-TAX-2：Vehicle Page Accounting Status Summary
P1-UX-TAX-3：15-1 Estimate Read-only Service
P1-UX-TAX-4：Vehicle Management Profit Summary
P1-UX-TAX-5：Accounting Workspace Dashboard Cleanup
```

本任務只做 P1-UX-TAX-0 文件，不進入 UI 或 runtime 實作。

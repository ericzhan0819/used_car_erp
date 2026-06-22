# P1-MVP Business Input Boundary Report

日期：2026-06-22  
專案：ERPNext / Frappe `used_car_erp`  
Repo：`ericzhan0819/used_car_erp`  
本機路徑：`~/frappe/frappe-bench/apps/used_car_erp`  
Bench 路徑：`~/frappe/frappe-bench`  
Site：`erpnext-coa.test`  
目前穩定點：`fcb718e fix: show inline vehicle cashflow summary`

---

## 1. 本文件目的

本文件正式定義 `used_car_erp` 在 P1-MVP 階段的產品操作邊界。

核心原則：

```text
業務歸業務
會計歸會計
```

業務人員不應該接觸、理解或操作會計文件與會計流程。業務人員只需要輸入真實世界已經發生或即將發生的商業事實。

會計資料流、傳票草稿、正式會計文件、稅務估算、管理損益與摘要，應由系統根據業務輸入自動推導，並交由會計人員在「會計作業」區域處理。

本文件不是新的 runtime 規格，也不是要求立即新增功能。本文件用來約束後續 UI、Dashboard、Workspace、會計作業頁與流程設計。

---

## 2. 核心產品方向

`used_car_erp` 應收斂為：

```text
極簡業務輸入介面 + 嚴謹後台流程引擎
```

也就是：

```text
業務人員只輸入：
- 花多少錢買車
- 花多少錢整備 / 維修 / 美容 / 代辦 / 拍場
- 收多少訂金
- 收多少尾款
- 這台車賣多少錢
- 是否成交

系統負責：
- 建立車輛狀態流
- 建立金流紀錄
- 建立傳票草稿
- 更新收支摘要
- 推導會計待辦
- 推導售車會計候選
- 推導 15-1 營業稅估算
- 推導管理毛利
- 提供 Dashboard / 摘要 / 待辦

會計人員負責：
- 審核傳票草稿
- 確認入帳
- 處理 Sales Invoice
- 處理 Journal Entry
- 處理預收款沖轉
- 處理正式會計閉環
```

真正目標不是讓業務更容易操作 ERPNext 的會計文件，而是讓業務端根本不需要知道 ERPNext 會計文件存在。

---

## 3. 業務端應看到的世界

業務端 UI 應只呈現業務語言。

### 3.1 業務人員需要理解的資料

```text
車輛基本資料
買進價格
整備支出
維修支出
美容支出
代辦支出
拍場支出
其他支出
訂金
尾款
售車成交價
客戶資料
成交狀態
收支摘要
```

### 3.2 業務人員不應該看到的東西

業務端不應暴露以下概念：

```text
Money Flow
Voucher Draft
Journal Entry
Sales Invoice
Payment Entry
GL Entry
Stock Ledger Entry
預收款沖轉
借方 / 貸方
會計科目
會計候選
正式出庫入帳
submit / cancel / amend
```

即使底層實際會產生這些資料，也不應該讓業務人員在 UI 上直接看到或操作。

---

## 4. 正確 UI 語言對照

| 業務畫面用語 | 底層實際行為 |
| --- | --- |
| 買進這台車 | 建立 Used Car Vehicle，後續可建立 Item / Serial No / Stock Entry |
| 完成入庫 | 系統自動建立 / 綁定 ERPNext Item、Serial No、Stock Entry |
| 新增支出 | 建立 Used Car Money Flow，並產生待審核 Used Car Voucher Draft |
| 收訂金 | 建立 Reservation、Money Flow、Voucher Draft |
| 收尾款 | 建立尾款 Money Flow、Voucher Draft |
| 確認成交 | 車輛標記已售出，保留單標記完成 |
| 查看收支摘要 | 讀取金流、收入、支出與狀態摘要 |
| 已送交內部處理 | 底層可能已有會計草稿或候選，但不向業務暴露技術文件名稱 |

---

## 5. 車輛頁邊界

`Used Car Vehicle` 車輛頁應定位為：

```text
業務事實輸入頁
```

### 5.1 車輛頁應保留

```text
基本資料
買進資料
入庫狀態
整備 / 上架狀態
售車資料
收款資料
新增支出
成交狀態
收支摘要
必要的業務提示
```

### 5.2 車輛頁不應保留

```text
Sales Invoice route button
Journal Entry route button
Voucher Draft route button
售車會計候選 route button
正式出庫 button
預收款沖轉 button
確認銷售發票並出庫 button
確認預收款沖轉入帳 button
會計技術欄位切換
正式會計文件維護入口
```

即使是 route-only button，也不應放在業務車輛頁。原因是業務人員不應被引導去理解會計流程。

如果業務完成成交後不知道後續怎麼辦，應修正的是：

```text
總覽提示
會計作業待辦
會計人員入口
Dashboard / Workspace 文案
```

而不是把會計入口放回車輛頁。

---

## 6. 會計作業頁邊界

`會計作業` 才是會計人員處理正式會計流程的地方。

會計作業頁應承接：

```text
待審核傳票草稿
金流紀錄
傳票草稿
正式 Journal Entry
Sales Invoice
售車會計候選
預收款沖轉
正式會計閉環檢查
```

會計人員可以在這裡看到：

```text
哪些支出待審核
哪些收款待審核
哪些車已成交但尚未處理 Sales Invoice
哪些 Sales Invoice 已建立但尚未正式提交
哪些車需要預收款沖轉
哪些車正式會計閉環已完成
```

---

## 7. 15-1 營業稅邊界

15-1 的語意必須固定為：

```text
15-1 只用在「售車營業稅」。
購入成本 = 購車價。
整備費、維修費、美容費、拍場費、代辦費，不併入 15-1 的中古車購入成本。
其他營業稅、營所稅照一般稅法與會計師判斷處理。
```

### 7.1 purchase_price 語意

`purchase_price` 固定代表：

```text
購車價，不包含整備、維修、美容、拍場費、代辦費或其他後續費用。
```

用途：

```text
單車購入成本
15-1 可扣抵進項稅額計算基礎
營所稅成本基礎之一
```

### 7.2 後續支出語意

以下支出：

```text
整備支出
維修支出
美容支出
代辦支出
拍場支出
其他直接支出
```

可以進入：

```text
單車管理損益
營所稅資料
費用傳票草稿
```

但不得進入：

```text
15-1 購入成本
15-1 可扣抵進項稅額計算基礎
```

### 7.3 兩套數字

系統應清楚分離兩套數字。

#### A. 單車管理損益

給管理者 / 老闆看的經營數字：

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

#### B. 15-1 營業稅估算

給營業稅估算使用：

```text
售車銷項稅額 = 售車價 ÷ 1.05 × 5%
15-1 購入可扣抵稅額 = 購車價 ÷ 1.05 × 5%
實際可扣抵 = min(購入可扣抵稅額, 銷項稅額)
預估本車營業稅 = 銷項稅額 - 實際可扣抵
```

整備、維修、美容、拍場、代辦等後續支出不放進此公式。

---

## 8. 目前已完成狀態

目前主流程方向已大致正確：

```text
車輛頁新增支出
→ 系統建立 Used Car Money Flow
→ 系統建立 Used Car Voucher Draft
→ 會計作業確認
→ 系統建立 Journal Entry
→ 車輛頁顯示收支摘要
```

這符合核心原則：

```text
業務輸入事實
系統建立資料流
會計處理確認
業務端只看摘要
```

最新穩定點：

```text
fcb718e fix: show inline vehicle cashflow summary
```

已完成：

```text
車輛頁可新增一般支出
新增支出會建立 Money Flow
新增支出會建立 Voucher Draft
車輛頁可顯示 inline cashflow summary
會計 mutation action 已從車輛頁降級 / 移除
會計作業已有售車會計候選方向
```

---

## 9. 對已售出車輛會計 action 的判斷

已售出車輛頁的 sold vehicle accounting action function 若為 no-op，不應直接視為 bug。

正確解讀應為：

```text
這符合「業務歸業務，會計歸會計」的產品邊界。
```

已售出車輛頁不應恢復：

```text
建立 Sales Invoice 草稿
前往售車會計候選
確認銷售發票並出庫
建立預收款沖轉草稿
確認預收款沖轉入帳
修復 Sales Invoice 草稿連結
```

這些應由會計作業區承接。

---

## 10. 目前真正需要驗證的問題

下一階段不應把會計按鈕修回車輛頁。

下一階段應驗證：

```text
1. 業務人員是否能從車輛頁完成：
   - 建車
   - 入庫
   - 整備 / 上架
   - 收訂金
   - 收尾款
   - 新增支出
   - 確認成交

2. 業務人員是否完全不需要接觸：
   - Sales Invoice
   - Journal Entry
   - Voucher Draft
   - 會計候選
   - 預收款沖轉

3. 會計人員是否能從會計作業找到：
   - 待審核收款
   - 待審核支出
   - 待確認傳票草稿
   - 待處理售車會計候選

4. Dashboard 是否能讓不同角色知道下一步：
   - 業務看業務待處理
   - 會計看會計待處理
   - 老闆看經營摘要
```

---

## 11. 建議下一階段

建議下一階段名稱：

```text
P1-MVP-UX-OPS-1：Business Input Surface Simplification
```

目標：

```text
把業務畫面徹底整理成：
- 買車花多少
- 整備花多少
- 賣車收多少
- 成交了沒有
- 收支摘要是多少
```

不做：

```text
不新增 accounting runtime
不新增 tax runtime
不恢復車輛頁會計入口
不把 Sales Invoice / Journal Entry route button 放回車輛頁
不讓業務選會計科目
不讓業務操作傳票草稿
不讓業務進售車會計候選
```

---

## 12. 建議實作順序

### Step 1：文件同步

正式寫入產品原則：

```text
業務端只輸入商業事實。
會計文件與會計候選只存在於會計作業。
車輛頁不暴露會計技術文件。
```

建議 commit message：

```text
docs: define business input and accounting operation boundary
```

### Step 2：主流程 browser smoke

依業務角度測試：

```text
總覽
→ 車輛管理
→ 新增車輛
→ 完成入庫
→ 整備 / 上架
→ 建立訂金
→ 建立尾款
→ 新增支出
→ 確認成交
→ 查看收支摘要
```

記錄：

```text
業務是否看得懂
業務是否找得到下一步
業務是否碰到會計名詞
業務是否被導向會計頁
業務是否看到不該看的技術文件
```

建議 commit message：

```text
docs: record business main flow smoke result
```

### Step 3：最小 UX 修正

只修：

```text
文案
按鈕出現時機
業務提示
route shortcut
Dashboard / Workspace 入口
```

不得修：

```text
backend accounting runtime
Sales Invoice submit
Journal Entry submit
Stock Ledger
GL Entry
COA
permission 大改
```

建議 commit message：

```text
fix: simplify business vehicle input surface
```

### Step 4：會計作業承接確認

確認會計端能從「會計作業」看到所有由業務輸入產生的後續事項：

```text
支出待審核
訂金待審核
尾款待審核
售車會計候選
Sales Invoice 待處理
預收款沖轉待處理
```

建議 commit message：

```text
docs: verify accounting operations handoff from business flow
```

---

## 13. 長期產品方向

未來即使導入 AI，也應遵守同一條邊界：

```text
AI 可以協助業務更快輸入商業事實。
AI 可以協助查詢摘要。
AI 可以協助產生草稿建議。
AI 不可以直接提交正式會計文件。
AI 不可以繞過會計作業區。
AI 不可以讓業務端暴露會計流程。
```

正確架構應為：

```text
業務輸入層
→ 系統流程層
→ 會計確認層
→ 摘要 / 報表層
→ 未來 AI 指令層
```

AI 不是取代會計邊界。AI 只是更自然的輸入與查詢方式。

---

## 14. 最終結論

目前 `used_car_erp` 的方向應明確收斂為：

```text
業務人員：
只管這台車花多少、收多少、賣多少、成交沒有。

系統：
自動產生金流、草稿、摘要、候選與狀態。

會計人員：
只在會計作業區審核、確認與過帳。

老闆 / 管理者：
從總覽與摘要看經營狀態。
```

這是比「把 ERPNext 操作簡化」更進一步的產品方向。

真正目標不是讓業務更容易操作 ERPNext。
真正目標是讓業務根本不需要知道 ERPNext 和會計文件存在。

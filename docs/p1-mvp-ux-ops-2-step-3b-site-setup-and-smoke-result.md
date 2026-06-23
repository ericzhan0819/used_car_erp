# P1-MVP-UX-OPS-2 Step 3B：Guided Intake Site Setup and Smoke Result

日期：2026-06-24  
專案：Used Car ERP / ERPNext / Frappe  
Repo：`ericzhan0819/used_car_erp`  
Site：`erpnext-coa.test`  
Company：`OO`

---

## 1. 本文件目的

本文件記錄 `P1-MVP-UX-OPS-2 Step 3B` 的 site setup 與手動 smoke 結果。

本文件只作為操作與驗收紀錄：

```text
不修改 runtime
不修改 DocType JSON
不修改 Workspace
不修改權限
不清理測試殘留資料
```

---

## 2. 前置程式穩定點

本次手動 smoke 前的最新程式穩定點：

```text
eef7699 fix: validate stock entry difference account for guided intake
```

相關前置完成項目：

```text
Step 3A：Guided Vehicle Intake Backend Orchestrator
Step 3B：Guided Vehicle Intake Dialog UI
Step 3B-FIX-1：客戶 / 原車主自由文字修正
Step 3B-FIX-2：Stock Entry Difference Account gate 與 rollback safety
```

---

## 3. Site setup：Company.stock_adjustment_account

### 3.1 問題背景

Guided intake 建立車輛後會呼叫既有入庫流程，入庫流程會建立 ERPNext `Stock Entry`。

ERPNext 在 `Stock Entry Detail` 需要合法的 Difference Account。先前曾發生錯誤：

```text
At row #1: you have selected the Difference Account 0100005-UC - 中古車銷貨成本 - O, which is a Cost of Goods Sold type account. Please select a different account
```

根本原因：

```text
0100005-UC - 中古車銷貨成本 - O 是 Cost of Goods Sold 類型科目。
ERPNext 不允許該科目作為 Stock Entry Difference Account。
```

Step 3B-FIX-2 已移除銷貨成本 fallback，改為要求 `Company.stock_adjustment_account` 必須設定有效庫存調整科目。

### 3.2 本次設定

本次於 `erpnext-coa.test` / Company `OO` 設定：

```text
Company.stock_adjustment_account = 中古車庫存調整 - O
```

此科目用途：

```text
只作為 Company.stock_adjustment_account
只作為 Stock Entry Difference Account
不作為中古車銷貨成本
不作為 Sales Invoice / 出庫成本認列科目
```

此科目應符合：

```text
root_type = Expense
is_group = 0
disabled = 0
account_type 不可為 Cost of Goods Sold
```

---

## 4. 手動 smoke 結果

### 4.1 測試入口

手動測試入口：

```text
Used Car Vehicle List
→ 新增買入車輛
→ Step 1：車輛基本資料
→ Step 2：收購資料
→ 建立車輛
```

### 4.2 測試重點

本次手動 smoke 驗證：

```text
1. List View 可看到「新增買入車輛」入口
2. Dialog 可依 Step 1 / Step 2 填寫資料
3. Step 2 顯示「客戶 / 原車主」，不再顯示「供應商 / 原車主」
4. 客戶 / 原車主可輸入自由文字，不要求 ERPNext Supplier 預先存在
5. 建立後會呼叫 guided vehicle intake backend orchestrator
6. 系統可建立 Used Car Vehicle
7. 系統可沿用既有 intake service 建立 / 綁定 Item、Serial No、Stock Entry
8. 系統可沿用既有 listing service 讓車輛進入「整備中」
9. 成功後導向新車輛頁
```

### 4.3 測試結果

本次手動 smoke 結果：

```text
Guided Vehicle Intake Dialog smoke passed.
```

成功結果：

```text
新增買入車輛 Dialog
→ 建立 Used Car Vehicle
→ 自動建立 / 綁定 Item
→ 自動 Stock Entry 入庫
→ 建立 / 綁定 Serial No
→ 狀態進入「整備中」
→ 導向新車輛頁
```

---

## 5. 已知測試殘留

使用者確認目前測試 DB 中有殘留測試車輛：

```text
VH-202606-0003
VH-202606-0004
```

處理策略：

```text
不清理
不修復
不再拿來測
正式上線前 DB 重製時一併丟棄
```

原因：

```text
目前仍為 MVP / QA 階段。
正式上線前資料庫會重製，因此不需要為這些測試殘留追加清理流程。
```

---

## 6. 不做事項

本階段不做：

```text
不清理測試殘留資料
不新增資料清理 service
不新增會計科目建立 runtime
不修改 COA runtime
不修改 DocType JSON
不修改 Workspace
不修改 Dashboard
不修改權限
不新增整備支出任務卡
不新增上架任務卡
不新增訂金任務卡
不新增尾款任務卡
不新增成交任務卡
```

---

## 7. 下一步

下一步建議：

```text
P1-MVP-UX-OPS-2 Step 3C：Guided Vehicle Intake Workspace Shortcut / UX Polish
```

Step 3C 建議邊界：

```text
只把「新增買入車輛」入口從 Used Car Vehicle List 延伸到總覽 / Workspace 或更直覺的位置。
不重寫 Step 3A backend。
不重寫 Step 3B Dialog。
不新增其他任務卡。
不處理會計流程。
```

若 Step 3C 前再次測試 guided intake，需注意：

```text
使用新的 VIN
不要重用 VH-202606-0003 / VH-202606-0004
Company.stock_adjustment_account 必須維持為有效非 COGS Expense account
```

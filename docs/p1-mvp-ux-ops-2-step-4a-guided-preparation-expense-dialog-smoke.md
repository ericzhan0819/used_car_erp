# P1-MVP-UX-OPS-2 Step 4A：Guided Preparation Expense Dialog Smoke Close

日期：2026-06-24  
專案：Used Car ERP / ERPNext / Frappe  
Repo：`ericzhan0819/used_car_erp`  
本機路徑：`~/frappe/frappe-bench/apps/used_car_erp`  
Bench：`~/frappe/frappe-bench`  
Site：`erpnext-coa.test`  
Company：`OO`

---

## 1. 本文件目的

本文件收尾記錄：

```text
P1-MVP-UX-OPS-2 Step 4A：Guided Preparation Expense Dialog Runtime
```

本階段已完成車輛頁「新增支出」業務任務卡 runtime，並通過 browser smoke。

目標是讓業務人員以任務卡方式新增整備 / 維修 / 美容 / 代辦 / 拍場 / 其他支出，而不是直接面對 ERPNext 會計文件或底層 `Used Car Money Flow` 技術語意。

---

## 2. Runtime commit

Step 4A runtime commit：

```text
8e7b577 feat: add guided preparation expense dialog
```

注意：原本本機 commit 曾顯示為：

```text
ff913fd feat: add guided preparation expense dialog
```

但因遠端已有前置 docs commits，rebase 後 SHA 已改變。後續文件與 handoff 應以遠端 main 的 `8e7b577` 為準。

前置 docs commits：

```text
761b7e5 docs: define preparation expense task card spec
36afcd1 docs: update current state for preparation expense spec
c8e12e9 docs: add preparation expense spec to docs index
```

---

## 3. 本階段修改檔案

```text
used_car_erp/public/js/guided_preparation_expense_dialog.js
used_car_erp/used_car_erp/doctype/used_car_vehicle/used_car_vehicle.js
used_car_erp/hooks.py
```

---

## 4. 主要變更

### 4.1 新增 shared guided expense Dialog

新增：

```text
used_car_erp/public/js/guided_preparation_expense_dialog.js
```

提供 shared Dialog：

```text
used_car_erp.guided_preparation_expense.open(frm)
```

Dialog 使用業務語意：

```text
新增支出
車輛資訊
支出日期
支出類型
金額
付款方式
付款對象 / 付款參考
憑證附件
備註
建立支出紀錄
```

### 4.2 車輛頁改呼叫 shared Dialog

`Used Car Vehicle` 車輛頁原本內嵌 `frappe.prompt` 的「新增支出」邏輯已改為呼叫 shared Dialog。

保留按鈕：

```text
新增支出
```

按鈕行為改為：

```text
used_car_erp.guided_preparation_expense.open(frm)
```

並保留 safe fallback message，避免 shared JS 未載入時直接報錯。

### 4.3 hooks.py 載入 shared JS

`hooks.py` 的 `app_include_js` 已加入：

```text
/assets/used_car_erp/js/guided_preparation_expense_dialog.js
```

並保留既有：

```text
/assets/used_car_erp/js/guided_vehicle_intake_dialog.js
```

---

## 5. 底層行為

Dialog 仍沿用既有 service：

```text
used_car_erp.used_car_erp.services.vehicle_money_flow_service.create_general_expense_money_flow
```

底層仍會建立：

```text
Used Car Money Flow
Used Car Voucher Draft
```

但業務 UI 不顯示這些技術名稱。

成功後業務端只看到業務語意：

```text
支出紀錄已建立
```

業務端不顯示：

```text
Money Flow
Voucher Draft
Journal Entry
Sales Invoice
GL Entry
借方 / 貸方
會計科目
預收款沖轉
15-1
```

---

## 6. Browser smoke 結果

使用者已完成 browser smoke，確認：

```text
Dialog 可正常開啟
Dialog 操作沒問題
```

Smoke 結論：

```text
pass
```

已確認重點：

```text
車輛頁「新增支出」可開啟 guided Dialog
Dialog 使用業務語意
支出欄位可操作
不需要面對 Money Flow / Voucher Draft / Journal Entry 等會計術語
```

---

## 7. Kilo 驗證狀態

已執行：

```text
python -m compileall used_car_erp/used_car_erp/services/vehicle_money_flow_service.py
python -m json.tool used_car_erp/used_car_erp/doctype/used_car_money_flow/used_car_money_flow.json
git diff --check
```

未執行：

```text
JS lint：repo 沒有 package.json / 既有 JS lint command
bench migrate：無 schema change，不需要
bench restart：不需要
```

---

## 8. 保留的產品邊界

本階段維持核心邊界：

```text
業務端 = 輸入支出事實
系統 = 建立金流與傳票草稿
會計端 = 後續審核與入帳
```

車輛頁不新增：

```text
Money Flow route button
Voucher Draft route button
Journal Entry route button
Sales Invoice route button
formal delivery accounting action
售車會計候選入口
會計科目選擇 UI
```

---

## 9. 明確未做事項

本階段刻意不做：

```text
不改 DocType JSON
不新增 paid_to 欄位
不新增支票 payment method
不改 /app/總覽
不新增總覽「新增支出」入口
不重設計支出列表
不重設計會計作業頁
不重寫 Voucher Draft 入帳流程
不改 Journal Entry runtime
不改 Sales Invoice runtime
不改 Stock Entry runtime
不改 15-1 service
不清理測試車資料
不做大規模權限調整
```

---

## 10. Step 4A 完成狀態

目前可視為：

```text
P1-MVP-UX-OPS-2 Step 4A completed
```

功能狀態：

```text
新增支出 guided Dialog runtime 已完成
車輛頁入口已接上
業務語意已降噪
底層 Money Flow / Voucher Draft foundation 沿用
browser smoke passed
schema 未改
```

---

## 11. 下一步建議

Step 4A 收尾後，下一步可進入下一張任務卡或 Step 4B 文案小修。

若繼續小步收尾，建議範圍為：

```text
P1-MVP-UX-OPS-2 Step 4B：Preparation Expense Post-Smoke Polish
```

只允許：

```text
文案微調
支出 Dialog 小型 UX polish
必要文件補充
不新增 runtime
不改 schema
不改會計流程
```

若不需要 polish，則可進下一張業務任務卡：

```text
整備完成並上架 task card
或
保留 / 收訂金 task card
```

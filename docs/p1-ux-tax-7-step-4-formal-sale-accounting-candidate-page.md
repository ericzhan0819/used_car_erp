# P1-UX-TAX-7 Step 4 / Step 5 Formal Sale Accounting Candidate Page

Date: 2026-06-21

Phase: `P1-UX-TAX-7`

Status: Step 7 smoke passed / handoff documented

## 1. Purpose

P1-UX-TAX-7 Step 4 / Step 5 已將 read-only formal sale accounting candidates 接成 Desk Page，並在 `會計作業` Workspace 加入 shortcut。

新增使用者入口：

```text
會計作業
→ 會計待辦
→ 售車會計候選
```

Page route：

```text
/app/formal-sale-accounting-candidates
```

## 2. Runtime boundary

此階段只消費 Step 3 read-only service：

```text
used_car_erp.used_car_erp.services.formal_sale_accounting_candidate_service.run_formal_sale_accounting_candidates
```

此階段不會建立、提交、修復或修改 Sales Invoice、Journal Entry、Used Car Vehicle 或任何 ERPNext 文件。

Page 操作欄只做 route navigation：

```text
開啟主要文件
開啟車輛
開啟 Sales Invoice
開啟 Journal Entry
```

前端只允許使用既有文件 route：

```javascript
frappe.set_route("Form", doctype, name)
```

## 3. Desk Page

新增 Page：

```text
used_car_erp/used_car_erp/page/formal_sale_accounting_candidates/formal_sale_accounting_candidates.json
used_car_erp/used_car_erp/page/formal_sale_accounting_candidates/formal_sale_accounting_candidates.js
```

顯示名稱：

```text
售車會計候選
```

Page 會顯示：

```text
候選總數
需技術修復
需補資料 / blocked
待確認銷售發票並出庫
待建立預收款沖轉草稿
待確認預收款沖轉入帳
```

候選表格欄位包含：

```text
分類
車輛
車號 / 車牌
客戶
成交價
Sales Invoice
Sales Invoice 狀態
預收款沖轉 Journal Entry
下一步
阻擋原因 / 提醒
最後更新時間
操作
```

## 4. Workspace shortcut

`會計作業` Workspace 已在 `會計待辦` 區塊新增 Page shortcut：

```text
label: 售車會計候選
type: Page
link_to: formal-sale-accounting-candidates
```

既有 shortcut 保持不變。

## 5. Smoke result

P1-UX-TAX-7 Step 6 site apply / smoke 已完成，Step 7 已新增 handoff 文件：

```text
docs/p1-ux-tax-7-step-7-smoke-handoff.md
```

已確認：

```text
/app/formal-sale-accounting-candidates 可開。
售車會計候選頁正常顯示。
summary / empty state / refresh 正常。
/app/會計作業 可看到 售車會計候選 shortcut。
shortcut route 正常。
仍維持 read-only boundary。
```

## 6. Non-goals

本階段明確不做：

```text
不建立 Sales Invoice。
不提交 Sales Invoice。
不建立 Journal Entry。
不提交 Journal Entry。
不修復 Sales Invoice link。
不回寫 Used Car Vehicle。
不修改 Vehicle JS。
不修改 DocType JSON。
不修改 hooks.py。
不新增 bulk action。
不新增 inline mutation。
```

## 7. Suggested commit message

```text
feat: add read-only formal sale accounting candidate page
```

# P1-UX-TAX-7 Step 3 Read-only Candidate Service

Date: 2026-06-21

Phase: `P1-UX-TAX-7`

Status: Step 4 / Step 5 Desk Page and Workspace shortcut implemented

## 1. Purpose

P1-UX-TAX-7 Step 3 新增 read-only `FormalSaleAccountingCandidateService`。

此 service 只產出會計作業售車會計候選 payload，供未來 `售車會計候選` 頁面消費。

## 2. Runtime boundary

本階段只允許讀取既有資料：

```text
Used Car Vehicle
Sales Invoice
Journal Entry
```

明確不做：

```text
不新增 Desk Page。
不改 Workspace。
不改 Vehicle JS。
不建立 / 提交 / 修改 Sales Invoice、Journal Entry、Used Car Vehicle 或任何 ERPNext 文件。
不修復 Sales Invoice link。
不回寫 Used Car Vehicle。
```

## 3. Service

新增檔案：

```text
used_car_erp/used_car_erp/services/formal_sale_accounting_candidate_service.py
```

Service：

```python
FormalSaleAccountingCandidateService
```

Whitelisted read-only function：

```python
run_formal_sale_accounting_candidates(limit=50)
```

## 4. Candidate categories

初版固定輸出五類：

```text
needs_sales_invoice_submit = 待確認銷售發票並出庫
needs_advance_settlement_draft = 待建立預收款沖轉草稿
needs_advance_settlement_submit = 待確認預收款沖轉入帳
blocked = 需補資料 / blocked formal accounting
needs_sales_invoice_recovery = 需技術修復 Sales Invoice 草稿連結
```

候選來源以 `Used Car Vehicle.status = 已售出` 為主，依 linked `Sales Invoice` / `Journal Entry` docstatus 做保守分類。

已完成售車會計閉環案件不列入 candidate list：

```text
submitted Sales Invoice + submitted advance settlement Journal Entry
=> 不產生 candidate
=> 不增加 candidate_count
=> 不增加 category_counts
=> 不顯示為 blocked
```

## 5. Completion criteria

Step 3 完成後：

```text
read-only service skeleton exists.
isolated fake-frappe tests cover initial category mapping.
README.md and docs/current-state.md reference Step 3.
Step 1 / Step 2 docs mention Step 3 boundary.
No Desk Page, Workspace, Vehicle JS, DocType JSON, hooks.py, or write behavior is added.
```

## 6. Step 4 / Step 5 update

P1-UX-TAX-7 Step 4 / Step 5 已將 read-only formal sale accounting candidates 接成 Desk Page，並在 會計作業 Workspace 加入 shortcut。

Desk Page：

```text
/app/formal-sale-accounting-candidates
```

此頁只呼叫本文件定義的 Step 3 read-only service：

```text
run_formal_sale_accounting_candidates(limit=50)
```

此階段不會建立、提交、修復或修改 Sales Invoice、Journal Entry、Used Car Vehicle 或任何 ERPNext 文件。

## 7. Suggested commit message

```text
feat: add read-only formal sale accounting candidates
```

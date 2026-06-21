# P1-UX-TAX-7 Step 8B Vehicle Page Accounting Action Demotion

Date: 2026-06-22

Phase: `P1-UX-TAX-7`

Status: JS-only demotion implemented

Latest stable commit before this implementation step:

```text
2abc896 docs: define vehicle accounting action demotion spec
```

## 1. Purpose

Step 8B 將 `Used Car Vehicle` 已售出車輛頁上的高衝擊會計 mutation actions 從一般車輛頁 surface 降級，主要入口改為：

```text
會計作業
→ 會計待辦
→ 售車會計候選
→ /app/formal-sale-accounting-candidates
```

本次是 JS-only implementation，不改 backend accounting behavior。

## 2. Vehicle page actions kept

車輛頁保留低風險或 route-only action：

```text
建立 Sales Invoice 草稿
查看銷售發票
查看預收款沖轉傳票
顯示文件連結 / 隱藏文件連結
```

`建立 Sales Invoice 草稿` 仍保留，因為此步驟只建立草稿，不提交、不出庫、不入帳。

`查看銷售發票` 與 `查看預收款沖轉傳票` 只開啟既有文件 route。

文件連結 toggle 只影響 UI 顯示。

## 3. Vehicle page actions demoted

以下 mutation actions 不再由一般已售出車輛頁掛出 primary / normal button：

```text
檢查提交資格
確認銷售發票並出庫
建立預收款沖轉草稿
確認預收款沖轉入帳
修復 Sales Invoice 草稿連結
修復銷售發票草稿連結
```

`add_recover_sales_invoice_draft_link_button_if_needed(frm)` function 保留，但不再由 `add_sold_vehicle_related_document_buttons(frm)` 呼叫。Sales Invoice recovery 主要入口改由 `售車會計候選` 的 `needs_sales_invoice_recovery` category 承接。

## 4. Route-only accounting button

當已售出車輛的下一步屬於會計作業處理時，車輛頁新增次要按鈕：

```text
button: 前往售車會計候選
group: 會計作業
route: /app/formal-sale-accounting-candidates
```

此 button 只執行 route navigation：

```javascript
frappe.set_route("formal-sale-accounting-candidates");
```

此 button 不呼叫任何 mutation service。

## 5. Primary action mapping after Step 8B

已售出車輛頁 primary action mapping：

| Accounting next action | Vehicle page behavior |
|---|---|
| `create_sales_invoice_draft` | 保留 `建立 Sales Invoice 草稿` |
| `submit_sales_invoice` | 不加 mutation button，顯示 `前往售車會計候選` |
| `create_advance_settlement_draft` | 不加 mutation button，顯示 `前往售車會計候選` |
| `submit_advance_settlement` | 不加 mutation button，顯示 `前往售車會計候選` |

## 6. Runtime boundary

本次未修改：

```text
Python service
DocType JSON
Workspace JSON
hooks.py
permission
backend accounting sequence
Sales Invoice submit behavior
Journal Entry create / submit behavior
Sales Invoice recovery behavior
GL / Stock Ledger behavior
```

未新增：

```text
doc.save()
doc.submit()
doc.cancel()
frappe.db.set_value()
frappe.db.commit()
frappe.db.sql write
新的 whitelisted mutation
新的 bulk action
```

## 7. Suggested commit message

```text
fix: demote vehicle page accounting actions
```

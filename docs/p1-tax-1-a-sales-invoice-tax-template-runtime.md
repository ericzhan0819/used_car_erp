# P1-TAX-1-A Sales Invoice Tax Template Runtime

## Scope

本階段只修正式 Used Car Vehicle flow 的 Sales Invoice draft tax template runtime：

`Used Car Vehicle -> completed reservation -> create_sales_invoice_draft_for_vehicle() -> Draft Sales Invoice`

正式流程建立 Draft Sales Invoice 時，客戶 Sales Invoice 稅項固定使用 `台灣營業稅 5%（含稅） - O`。

## Runtime Behavior

建立 Sales Invoice 草稿時會設定：

- `taxes_and_charges = 台灣營業稅 5%（含稅） - O`
- `taxes` child table 從 Sales Taxes and Charges Template 複製一筆 tax row
- tax row 必須是 `charge_type = On Net Total`
- tax row 必須是 `account_head = 0202134 - 銷項稅額 - O`
- tax row 必須是 `rate = 5`
- tax row 必須是 `included_in_print_rate = 1`

## Master Data Gate

Runtime 只驗證既有 master data，不自動修正設定。

若 Sales Taxes and Charges Template 或 tax account 有以下問題，會阻擋 Sales Invoice 草稿建立：

- template 不存在
- template company 不等於目前 Sales Invoice company
- template 已停用
- template taxes 不是剛好一筆
- tax row charge type / account / rate / included-in-print-rate 不符合固定含稅模板規格
- tax account 不存在
- tax account 不屬於同 company
- tax account 是 group account
- tax account 已停用

阻擋後應由人工修正 master data；runtime 不修改 COA、不自動建立 template、不自動建立 account。

## Boundaries

本階段仍不做：

- 不 submit Sales Invoice
- 不建立 GL Entry
- 不建立 Stock Ledger Entry
- 不建立 Payment Entry
- 不建立 Journal Entry
- 不建立 Delivery Note
- 不建立 Stock Entry
- 不修改 COA
- 不補 QA draft serial_no
- 不建立 QA Serial No
- 不硬造完整正式交易資料
- 不把 15-1 扣抵額寫進 Sales Invoice taxes table
- 不實作多稅率
- 不實作未稅 template runtime 切換
- 不實作 Tax Category 自動分流
- 不實作 Item Tax Template

## 15-1 Boundary

15-1 只作內部扣抵估算，不寫入 Sales Invoice taxes table。

客戶 Sales Invoice 的銷項稅仍固定使用台灣營業稅 5% 含稅模板，避免把內部扣抵估算混入客戶發票稅項明細。

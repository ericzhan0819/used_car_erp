# P1-ACC-6E Minimal Accounting / Stock Setup QA

Last reviewed: 2026-06-19

Phase: `P1-ACC-6E`

## 1. Purpose

P1-ACC-6E verifies that the `erpnext-coa.test` site has the minimal ERPNext accounting and stock master data required to create a draft Sales Invoice for company `OO`.

This QA is intentionally narrow. It checks company defaults, ledger accounts, warehouse account linkage, the used-car stock Item, and the Taiwan 5% included Sales Taxes and Charges Template.

## 2. Draft Only

This phase only creates a Draft Sales Invoice.

It must not submit the Sales Invoice. It must not create GL Entry or Stock Ledger Entry records. The created draft is for validation only and can be deleted after review.

## 3. Required Master Data

```text
Company: OO
Company Abbreviation: O
Currency: TWD
Country: Taiwan

Item: USED-CAR-VEHICLE
Item Group: 中古車
Stock UOM: NOS
Stock Item: 1
Sales Item: 1
Purchase Item: 1
Serial No enabled: 1

Warehouse: 中古車庫存倉 - O
Warehouse Account: 0201131 - 商品 - O

Income Account: 0100001-UC - 中古車銷售收入 - O
Expense / COGS Account: 0100005-UC - 中古車銷貨成本 - O
Inventory Account: 0201131 - 商品 - O
Receivable Account: 0201123 - 應收帳款 - O
Output Tax Account: 0202134 - 銷項稅額 - O

Primary Sales Taxes and Charges Template:
台灣營業稅 5%（含稅） - O
```

The service may also validate `台灣營業稅 5%（未稅） - O`, but draft creation uses the included template by default.

## 4. Run Command

Run from the bench directory:

```bash
cd /home/z/frappe/frappe-bench
bench --site erpnext-coa.test execute used_car_erp.used_car_erp.services.minimal_accounting_stock_setup_qa_service.run_minimal_accounting_stock_setup_qa
```

Developer checks from the app directory:

```bash
cd /home/z/frappe/frappe-bench/apps/used_car_erp
python -m compileall used_car_erp/used_car_erp/services/minimal_accounting_stock_setup_qa_service.py
pytest used_car_erp/used_car_erp/services/test_minimal_accounting_stock_setup_qa_service.py
```

## 5. Expected Pass Conditions

```text
status = pass
Company OO exists and has abbreviation O.
GL Entry count is 0 before and after draft creation.
Stock Ledger Entry count is 0 before and after draft creation.
Required Accounts exist, belong to OO, are ledger accounts, and are not disabled.
Company Defaults match the required accounts.
Warehouse is active, non-group, belongs to OO, and is linked to inventory account.
Item and Item Default match the required warehouse / income / expense setup.
Included Taiwan 5% tax template has exactly one On Net Total row at 5%.
Draft Sales Invoice remains docstatus 0.
Draft item row uses the required item, warehouse, and income account.
Draft tax row uses the required output tax account, rate 5, and included_in_print_rate 1.
```

## 6. Blocking And Warning Conditions

Blocking conditions return `status = fail` and stop before draft creation when they are detected before insert:

```text
Company OO missing or abbreviation mismatch.
GL Entry count is not 0.
Stock Ledger Entry count is not 0.
Required Account missing, group, disabled, or wrong company.
Company Defaults mismatch.
Warehouse missing, group, disabled, wrong company, or wrong account.
Item missing or required flags/defaults mismatch.
Primary included Sales Taxes and Charges Template missing or invalid.
ERPNext validation blocks Draft Sales Invoice insert.
```

Warning conditions return `status = warning` when no blocking error exists:

```text
Optional excluded tax template is missing.
ERPNext does not populate item expense_account at draft stage.
```

## 7. Non-goals

This phase does not:

```text
Submit Sales Invoice.
Create Payment Entry.
Create Journal Entry.
Create Delivery Note.
Create Stock Entry.
Create or submit Purchase Invoice.
Generate GL Entry.
Generate Stock Ledger Entry.
Import or overwrite Chart of Accounts.
Create or repair tax templates.
Disable or enable Accounts.
Patch ERPNext core.
Implement runtime tax template auto-selection.
Write 15-1 deduction amounts into Sales Invoice taxes.
```

## 8. Next Phase

P1-ACC-6F is the first phase that may test submitted Sales Invoice behavior, stock movement, and GL / Stock Ledger results.

P1-ACC-6E evidence only proves the site can safely create and inspect the minimal draft Sales Invoice.

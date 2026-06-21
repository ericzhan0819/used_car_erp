# P1-UX-TAX-7 Step 7 Smoke Handoff

Date: 2026-06-21

Phase: `P1-UX-TAX-7`

Status: Step 7 smoke test handoff / phase checkpoint

Latest stable commit before this documentation step:

```text
7b7addb feat: add read-only formal sale accounting candidate page
```

## 1. Purpose

This handoff records the site apply and browser smoke result for the read-only formal sale accounting candidate path.

P1-UX-TAX-7 Step 4 / Step 5 added:

```text
/app/formal-sale-accounting-candidates
會計作業 → 會計待辦 → 售車會計候選
```

Step 6 applied the Page / Workspace to `erpnext-coa.test` and confirmed the route in browser.

This Step 7 document creates a stable checkpoint before the next runtime UX phase: vehicle-page accounting action demotion.

## 2. Confirmed browser smoke result

User-confirmed manual smoke test:

```text
/app/formal-sale-accounting-candidates 可開。
售車會計候選頁正常顯示。
summary / empty state / refresh 正常。
/app/會計作業 可看到 售車會計候選 shortcut。
shortcut route 正常。
目前仍是 read-only，沒有 write behavior。
```

## 3. Site apply / verification record

Commands run during Step 6 smoke preparation:

```bash
cd ~/frappe/frappe-bench
bench --site erpnext-coa.test migrate
bench --site erpnext-coa.test execute used_car_erp.used_car_erp.services.formal_sale_accounting_candidate_service.run_formal_sale_accounting_candidates
bench --site erpnext-coa.test execute frappe.db.exists --args "['Page', 'formal-sale-accounting-candidates']"
bench --site erpnext-coa.test execute frappe.db.get_value --args "['Page', 'formal-sale-accounting-candidates', 'title']"
bench --site erpnext-coa.test execute frappe.reload_doc --args "['used_car_erp', 'workspace', 'accounting_operations']"
bench --site erpnext-coa.test import-doc apps/used_car_erp/used_car_erp/used_car_erp/workspace/accounting_operations/accounting_operations.json
```

Service execution result:

```json
{
  "status": "pass",
  "candidate_count": 0,
  "candidates": [],
  "category_counts": {
    "needs_sales_invoice_recovery": 0,
    "blocked": 0,
    "needs_sales_invoice_submit": 0,
    "needs_advance_settlement_draft": 0,
    "needs_advance_settlement_submit": 0
  },
  "warnings": [],
  "blocking_errors": []
}
```

Page DB verification:

```text
Page exists: formal-sale-accounting-candidates
Page title: 售車會計候選
```

Workspace DB verification:

```text
Workspace: 會計作業
content includes: uco_formal_sale_accounting_candidates
shortcut_name: 售車會計候選
```

Final repo state after site apply:

```text
git status --short
(no output)
```

## 4. Known warning during migrate

`bench migrate` printed existing Number Card export warnings:

```text
number_card/中古車庫存中/中古車庫存中.json missing
number_card/中古車上架中/中古車上架中.json missing
number_card/中古車在庫/中古車在庫.json missing
number_card/中古車已售出/中古車已售出.json missing
number_card/中古車保留中/中古車保留中.json missing
number_card/中古車整備中/中古車整備中.json missing
```

These warnings match the previously recorded Frappe duplicate Chinese export / tracked path behavior from the dashboard work.

Current tracked Number Card paths should remain the existing English export paths. Do not commit redundant Chinese duplicate Number Card export directories unless a future task explicitly decides to normalize those exports.

## 5. Runtime boundary still locked

The candidate page and workspace shortcut remain read-only.

No Step 7 work added or required:

```text
No Sales Invoice creation.
No Sales Invoice submit.
No Journal Entry creation.
No Journal Entry submit.
No Sales Invoice link repair.
No Used Car Vehicle writeback.
No Vehicle JS change.
No DocType JSON change.
No hooks.py change.
No permission change.
No accounting sequence rewrite.
```

The only write-like site operation in Step 6 was applying existing committed app metadata to the local site by migrate / reload / import.

## 6. Current stable user flow

Accounting users can now enter the formal sale accounting candidate path from Accounting Operations:

```text
會計作業
→ 會計待辦
→ 售車會計候選
→ /app/formal-sale-accounting-candidates
```

Candidate row actions are route-only:

```text
Open primary document.
Open Used Car Vehicle.
Open Sales Invoice.
Open Journal Entry.
```

## 7. Next recommended phase

Next recommended implementation phase:

```text
P1-UX-TAX-7 Step 8 Vehicle Page Accounting Action Demotion
```

Goal:

```text
Demote high-impact sold-vehicle accounting actions from Used Car Vehicle now that Accounting Operations has a working candidate entry point.
```

Candidate actions to demote from the normal vehicle page surface:

```text
檢查提交資格
確認銷售發票並出庫
建立預收款沖轉草稿
確認預收款沖轉入帳
修復 Sales Invoice 草稿連結
```

Recommended Step 8 boundary:

```text
JS-only first, if possible.
No backend accounting service rewrite.
No new Sales Invoice / Journal Entry behavior.
No permission change.
No DocType JSON change.
No Workspace change.
Keep route links to existing accounting documents.
Keep one primary business lifecycle action on Vehicle.
```

## 8. Handoff summary

P1-UX-TAX-7 now has a working Accounting Operations candidate path:

```text
Step 1: migration decision documented.
Step 2: candidate list spec documented.
Step 3: read-only candidate data service implemented.
Step 4 / Step 5: read-only Desk Page and Workspace shortcut implemented.
Step 6: site apply and browser smoke passed.
Step 7: handoff checkpoint documented.
```

This phase can now safely proceed to controlled vehicle-page action demotion.

## 9. Suggested commit message

```text
docs: close p1 ux tax 7 smoke handoff
```

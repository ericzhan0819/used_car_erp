# P1-UX-TAX-7 Step 8C Vehicle Page Accounting Action Demotion Smoke

Date: 2026-06-22

Phase: `P1-UX-TAX-7`

Status: smoke / handoff documented

## 1. Purpose

Step 8C records the smoke / handoff boundary after Step 8B JS-only vehicle-page accounting action demotion.

Step 8B已完成：`Used Car Vehicle`已售出頁不再掛出高衝擊會計 mutation buttons，會計後續操作改由：

```text
會計作業
→ 會計待辦
→ 售車會計候選
→ /app/formal-sale-accounting-candidates
```

## 2. Smoke result

Static verification passed.

Browser smoke was not executed by this agent because no browser/build/clear-cache approval was requested in this run. Manual browser checklist remains the handoff target for `erpnext-coa.test` after site assets are confirmed current.

## 3. Accounting Operations checklist

Manual smoke targets:

```text
/app/formal-sale-accounting-candidates
/app/會計作業
```

Expected result:

```text
售車會計候選頁仍可開。
會計作業仍可看到 售車會計候選 shortcut。
shortcut route 正常。
candidate summary / empty state / refresh 正常。
```

## 4. Vehicle page checklist

Manual smoke targets for sold `Used Car Vehicle` records:

| State | Expected vehicle-page surface |
|---|---|
| 已售出、尚無 Sales Invoice | 可保留 `建立 Sales Invoice 草稿`；不顯示 `確認銷售發票並出庫`、`建立預收款沖轉草稿`、`確認預收款沖轉入帳` |
| 已售出、有 Sales Invoice 草稿 | 可看到 `查看銷售發票` route link；可看到 route-only `前往售車會計候選`；不顯示 `確認銷售發票並出庫` 或 `修復銷售發票草稿連結` mutation button |
| Sales Invoice 已提交 | 可看到 `查看銷售發票` route link；可看到 route-only `前往售車會計候選`；不顯示 `建立預收款沖轉草稿` mutation button |
| 預收款沖轉 Journal Entry 草稿已建立 | 可看到 `查看預收款沖轉傳票` route link；可看到 route-only `前往售車會計候選`；不顯示 `確認預收款沖轉入帳` mutation button |
| 已完成 / 預收款沖轉已提交 | 只保留 route links / read-only summary；不顯示高衝擊 accounting mutation buttons |

## 5. Verified vehicle states

Browser state verification was not run in this agent session.

States to verify manually on `erpnext-coa.test`:

```text
已售出、尚無 Sales Invoice
已售出、有 Sales Invoice 草稿
Sales Invoice 已提交
預收款沖轉 Journal Entry 草稿已建立
已完成 / 預收款沖轉已提交
```

## 6. Missing fixtures

Fixture availability was not inspected from the live browser in this run.

Record missing fixture states during manual smoke if the site does not contain every state listed above.

## 7. Runtime boundary

Step 8C does not change runtime behavior.

No changes were made to:

```text
Used Car Vehicle JS
Python service
DocType JSON
Workspace JSON
hooks.py
permission
backend accounting sequence
Sales Invoice / Journal Entry behavior
GL Entry / Stock Ledger behavior
```

Step 8B remains JS-only demotion. Step 8C is documentation / handoff only.

## 8. Verification

Commands run:

```bash
git status --short
git diff --check
python -m compileall used_car_erp/used_car_erp/services/formal_sale_accounting_candidate_service.py
python -m compileall used_car_erp/used_car_erp/services/test_formal_sale_accounting_candidate_service.py
```

Result:

```text
pass
```

## 9. Not run

Not run in this session:

```bash
bench build --app used_car_erp
bench --site erpnext-coa.test clear-cache
bench --site erpnext-coa.test migrate
```

`bench migrate` is not needed for Step 8C because this step only updates documentation and Step 8B was JS / Markdown only.

## 10. Suggested commit message

```text
docs: close vehicle accounting action demotion smoke
```

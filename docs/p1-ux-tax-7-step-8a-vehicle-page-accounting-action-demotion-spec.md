# P1-UX-TAX-7 Step 8A Vehicle Page Accounting Action Demotion Spec

Date: 2026-06-21

Phase: `P1-UX-TAX-7`

Status: Step 8A documentation-only inventory and demotion boundary

Step 8B implementation note: `docs/p1-ux-tax-7-step-8b-vehicle-page-accounting-action-demotion.md` records the JS-only demotion implementation. Step 8B keeps Sales Invoice draft creation and document route links on the vehicle page, removes high-impact accounting mutation buttons from the normal sold-vehicle surface, and adds a route-only `前往售車會計候選` button.

Latest stable commit before this documentation step:

```text
cc4c18e docs: close p1 ux tax 7 smoke handoff
```

## 1. Purpose

P1-UX-TAX-7 Step 8A defines how to demote high-impact sold-vehicle accounting actions from `Used Car Vehicle` after the Accounting Operations candidate path has passed browser smoke.

The target Accounting Operations entry point is already available:

```text
會計作業
→ 會計待辦
→ 售車會計候選
→ /app/formal-sale-accounting-candidates
```

Step 8A is documentation-only. It does not change runtime behavior.

## 2. Current vehicle page inventory

Current sold-vehicle branch in `used_car_vehicle.js`:

```text
apply_vehicle_form_mode(frm)
  if status == 已售出:
    add_accounting_status_technical_fields_toggle_button(frm)
    add_sold_vehicle_primary_action_button(frm)
    add_sold_vehicle_related_document_buttons(frm)
    set_vehicle_fields_read_only(frm, true)
    allow_sold_vehicle_tax_metadata_edit(frm)
    allow_sold_vehicle_sale_workflow_edit(frm)
```

Relevant functions:

```text
add_sold_vehicle_primary_action_button(frm)
add_sold_vehicle_related_document_buttons(frm)
get_sold_vehicle_primary_next_action(frm)
add_submit_formal_delivery_sales_invoice_button(frm)
add_create_advance_settlement_journal_entry_draft_button(frm)
add_submit_advance_settlement_journal_entry_button(frm)
add_recover_sales_invoice_draft_link_button_if_needed(frm)
add_open_sales_invoice_button(frm)
add_open_advance_settlement_journal_entry_button(frm)
add_sold_vehicle_next_step_button(frm)
```

## 3. Current primary action mapping

`get_sold_vehicle_primary_next_action(frm)` currently maps sold-vehicle states to these primary actions:

| Vehicle state | Current primary action | Current button |
|---|---|---|
| Sold, no Sales Invoice | `create_sales_invoice_draft` | `建立 Sales Invoice 草稿` |
| Sales Invoice draft exists | `submit_sales_invoice` | `確認銷售發票並出庫` |
| Sales Invoice submitted, no settlement JE | `create_advance_settlement_draft` | `建立預收款沖轉草稿` |
| Settlement JE draft exists | `submit_advance_settlement` | `確認預收款沖轉入帳` |
| Settlement JE submitted | none | route links only |
| Formal accounting completed | none | route links only |

## 4. Actions to keep on vehicle page

Keep these vehicle-page actions:

```text
建立 Sales Invoice 草稿
查看銷售發票
查看預收款沖轉傳票
顯示文件連結 / 隱藏文件連結
```

Rationale:

```text
建立 Sales Invoice 草稿 is still a business preparation step and does not submit or post accounting documents.
查看銷售發票 and 查看預收款沖轉傳票 are route-only links.
技術欄位 toggle is a local display-only action.
```

## 5. Actions to demote from normal vehicle page surface

Demote these high-impact accounting actions from the normal vehicle-page primary action surface:

```text
檢查提交資格
確認銷售發票並出庫
建立預收款沖轉草稿
確認預收款沖轉入帳
修復 Sales Invoice 草稿連結
```

Target surface:

```text
會計作業 → 售車會計候選
```

Demotion means removing or hiding normal vehicle-page mutation entry points. It does not mean deleting backend services.

## 6. Step 8B JS-only implementation boundary

Recommended Step 8B should be JS-only.

Allowed:

```text
Modify used_car_erp/used_car_erp/doctype/used_car_vehicle/used_car_vehicle.js.
Keep backend service method names unchanged.
Keep read-only summary rendering unchanged.
Keep existing Sales Invoice / Journal Entry route links.
Add one route-only secondary button to /app/formal-sale-accounting-candidates if useful.
Update README.md, docs/current-state.md, and a Step 8B doc.
```

Not allowed:

```text
No Python service change.
No DocType JSON change.
No Workspace JSON change.
No hooks.py change.
No permission change.
No new accounting sequence.
No Sales Invoice creation / submit behavior change.
No Journal Entry creation / submit behavior change.
No Sales Invoice relink behavior change.
No GL / Stock Ledger behavior change.
No migrate / build / restart unless explicitly requested.
```

## 7. Recommended Step 8B behavior

### 7.1 Primary action handling

`add_sold_vehicle_primary_action_button(frm)` should keep only the non-posting sold-vehicle primary action:

```text
create_sales_invoice_draft → keep 建立 Sales Invoice 草稿
submit_sales_invoice → do not add mutation button
create_advance_settlement_draft → do not add mutation button
submit_advance_settlement → do not add mutation button
```

### 7.2 Accounting Operations route button

Add a route-only secondary button for sold vehicles when the next step is now accounting-owned:

```text
label: 前往售車會計候選
route: /app/formal-sale-accounting-candidates
button group: 會計作業 or 文件連結
```

The button must only route:

```javascript
frappe.set_route("formal-sale-accounting-candidates")
```

or the equivalent Frappe route syntax used by this repo.

It must not call any mutation service.

### 7.3 Technical recovery action

`修復銷售發票草稿連結` should no longer appear as a normal vehicle-page mutation button.

Preferred handling for Step 8B:

```text
Do not call add_recover_sales_invoice_draft_link_button_if_needed(frm) from normal sold-vehicle related document rendering.
Let the Accounting Operations candidate page surface the repair category.
Keep the backend recovery method untouched.
```

### 7.4 Read-only comments / summary

Keep read-only information surfaces unless they create visual noise:

```text
單車摘要 read-only cards remain.
Document route buttons remain.
Intro text may mention Accounting Operations for accounting follow-up.
No need to remove read-only preflight dashboard comments unless they are currently visible and noisy.
```

## 8. Expected UX after Step 8B

Sold vehicle page should no longer present high-impact accounting mutation buttons as primary actions.

Expected behavior:

```text
If no Sales Invoice exists: vehicle page may show 建立 Sales Invoice 草稿.
If Sales Invoice draft exists: vehicle page shows route link to Sales Invoice and route to 售車會計候選, but not 確認銷售發票並出庫.
If Sales Invoice submitted: vehicle page shows route link to Sales Invoice and route to 售車會計候選, but not 建立預收款沖轉草稿.
If settlement JE draft exists: vehicle page shows route links and route to 售車會計候選, but not 確認預收款沖轉入帳.
If recovery is needed: vehicle page should not show 修復銷售發票草稿連結 as a mutation action; Accounting Operations candidate page should be the primary entry.
```

## 9. Step 8C smoke requirements

After Step 8B implementation, perform browser smoke against `erpnext-coa.test`.

Required checks:

```text
Open an 已售出 vehicle without Sales Invoice.
Open an 已售出 vehicle with draft Sales Invoice.
Open an 已售出 vehicle with submitted Sales Invoice.
Open an 已售出 vehicle with settlement JE draft, if fixture exists.
Confirm high-impact accounting mutation buttons are absent from normal vehicle page surface.
Confirm route links to Sales Invoice / Journal Entry still work.
Confirm 前往售車會計候選 opens /app/formal-sale-accounting-candidates.
Confirm 會計作業 → 售車會計候選 still works.
Confirm no backend accounting behavior changed.
```

## 10. Completion criteria

Step 8A is complete when:

```text
This document exists.
README.md references Step 8A.
docs/current-state.md references Step 8A.
Step 7 handoff points to this demotion spec.
No runtime files are modified.
```

## 11. Suggested commit message

```text
docs: define vehicle accounting action demotion spec
```

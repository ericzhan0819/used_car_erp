# P1-MVP-DASH-2：Custom Overview Page

## 本階段目的

本階段將 `/app/總覽` 從原生 Workspace 改成 custom Page。

原因是總覽已定位為中古車業務操作面板，不只是 shortcut / number card 容器。業務人員應可從總覽直接開啟新增買入車輛流程，不需要先被導到 List View。

## 刪除原生 Workspace 的原因

原生 Workspace 無法乾淨做到直接開 guided intake Dialog。

保留舊 Workspace 會造成兩套入口與誤用風險。因此本階段直接刪除 repo 中的 `used_car_overview` Workspace JSON，讓 custom Page `總覽` 成為唯一總覽入口。

## Guided intake form completeness check

### 原始 Used Car Vehicle 可填業務欄位

依 `used_car_vehicle.json` 盤點，排除 Section Break、Column Break、Tab Break、HTML、Button、hidden、read_only、系統產生、會計文件連結與 ERPNext stock / accounting technical link 後，新增買入車輛時可由業務填寫的欄位為：

- 車輛基本資料：`status`, `branch_location`, `license_plate`, `vin`, `engine_no`, `brand`, `model`, `variant_trim`, `year`, `manufacture_date`, `license_date`, `mileage_km`, `color`, `interior_color`
- 車籍 / 規格資料：`fuel_type`, `engine_cc`, `transmission`, `drivetrain`, `doors`, `seats`
- 收購資料：`purchase_type`, `supplier`, `purchase_staff`, `source`, `purchase_date`, `expected_received_date`, `received_date`, `purchase_price`, `purchase_source_type`, `purchase_document_no`, `original_owner_name`, `original_owner_phone`, `referral_name`, `referral_phone`, `purchase_note`
- 稅費 / 監理狀態：`license_tax_paid`, `fuel_tax_paid`, `has_unpaid_loan`, `has_tax_penalty`, `registration_restricted`, `insurance_cancelled`, `plate_cancelled`, `need_document_check`, `license_tax_due_date`, `fuel_tax_due_date`, `insurance_expiry_date`, `registration_note`
- 其他備註：`notes`

### 原 guided intake Dialog 已有欄位

- `brand`
- `model`
- `year`
- `license_plate`
- `vin`
- `mileage`，後端寫入 `mileage_km`
- `color`
- `purchase_price`
- `purchase_source_type`
- `seller`
- `original_owner_name`
- `purchase_staff`
- `license_tax_paid`
- `fuel_tax_paid`
- `has_unpaid_loan`
- `has_tax_penalty`
- `registration_restricted`
- `insurance_cancelled`
- `plate_cancelled`
- `need_document_check`

### 本次補上的欄位

- 車輛基本資料：`variant_trim`, `engine_no`, `interior_color`
- 車籍 / 規格資料：`manufacture_date`, `license_date`, `fuel_type`, `engine_cc`, `transmission`, `drivetrain`, `doors`, `seats`
- 收購資料：`purchase_type`, `source`, `purchase_date`, `expected_received_date`, `received_date`, `purchase_document_no`, `original_owner_phone`, `referral_name`, `referral_phone`, `purchase_note`
- 稅費 / 監理狀態：`license_tax_due_date`, `fuel_tax_due_date`, `insurance_expiry_date`, `registration_note`
- 其他備註：`notes`

### 排除欄位與原因

- `stock_no`：system generated，儲存時自動產生。
- `status`：system controlled，guided intake 完成後由流程推進到整備中。
- `branch_location`：not part of intake，目前新增買入流程未要求指定車場 / 分店。
- `supplier`：technical Link / ERPNext party link，自由文字原車主不可寫入 Supplier；Dialog 使用 `seller` / `original_owner_name`。
- `floor_price`：not part of intake，主管底價屬上架 / 定價流程。
- `asking_price`：not part of intake，開價屬上架流程。
- `purchase_commission`：hidden field。
- `other_payable`：hidden field。
- `purchase_document_type`：hidden field，憑證判斷與會計確認不放入業務 intake。
- `customer`, `sold_price`, `reserved_date`, `sold_date`, `expected_delivery_date`, `delivery_date`, `sales_staff`, `sales_note`：not part of intake，屬售車 / 交車流程。
- `vehicle_tax_mode`, `tax_review_status`, `tax_review_note`：hidden / accounting decision field。
- `completed_reservation`, `completed_at`, `completed_by`, `completion_note`：read-only summary / system generated。
- `deposit_money_flow`, `deposit_voucher_draft`, `deposit_journal_entry`, `final_money_flow`, `final_voucher_draft`, `final_journal_entry`：accounting document link / technical link。
- `accounting_status_summary_html`：HTML summary。
- `formal_delivery_status`, `formal_delivery_posting_date`, `formal_delivery_completed_at`, `formal_delivery_completed_by`, `formal_delivery_note`：read-only accounting status。
- `sales_invoice`, `advance_settlement_journal_entry`：accounting document link。
- `total_cost`, `gross_margin`：read-only summary / system calculated。
- `item`, `serial_no`, `stock_warehouse`, `stock_entry`, `purchase_invoice`：ERPNext stock / accounting technical link。

### Excluded / needs decision

- `branch_location`：可能未來需在多分店流程納入，但目前任務沒有明確要求，先不放入 guided intake。
- `purchase_document_type`：雖與買入憑證相關，但現有欄位 hidden 且牽涉稅務判斷，先不放入業務 Dialog。

## 新架構

```text
/app/總覽 → custom Page
新增買入車輛 → shared guided intake Dialog
Used Car Vehicle List → shared guided intake Dialog
```

shared guided intake Dialog 位於：

```text
used_car_erp/public/js/guided_vehicle_intake_dialog.js
```

List View 與 custom Page 都呼叫：

```javascript
used_car_erp.guided_vehicle_intake.open_dialog()
```

## 本月銷售卡

`Used Car Vehicle` 目前存在可靠銷售日期欄位 `sold_date`。

本階段 MVP custom Page 先不查 DB 計數，避免把前端 Dashboard 擴成報表 runtime；本月銷售卡顯示 `—`，副文字顯示「待銷售日期欄位確認」。後續若要顯示實際數字，應另以 whitelisted read method 或報表查詢實作。

## DB cleanup

刪 repo 檔案不會自動刪 DB Doc。因此本地 site 需要明確刪除舊 Workspace 與舊 launcher Page。

```python
import frappe

for doctype, name in [
    ("Workspace", "總覽"),
    ("Page", "guided-vehicle-intake"),
]:
    if frappe.db.exists(doctype, name):
        frappe.delete_doc(doctype, name, ignore_permissions=True, force=True)

frappe.db.commit()
```

## Workspace import-doc 經驗

先前 `used_car_overview.json` 單靠 `bench migrate` 未必會進 DB。

但本階段已移除該 Workspace JSON，因此不再依賴 `import-doc` 更新總覽。

## 不做事項

- 不改 Stock Entry / accounting runtime
- 不新增其他任務卡
- 不新增銷售 / 支出 / 成交流程
- 不清理測試車資料
- 不做手動瀏覽器檢查

## 下一步

下一步建議：

```text
P1-MVP-UX-OPS-2 Step 4：Preparation Expense Task Card Spec
```

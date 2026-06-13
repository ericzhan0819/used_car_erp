# Used Car Role Permission Inventory Phase P1-A

## 1. Scope

This inventory is read-only documentation for current custom DocType permissions, sensitive fields, client-side buttons, and server-side gates in `apps/used_car_erp`.

No DocType JSON, runtime Python, JavaScript, database schema, Role, User, Permission, Sales Invoice, Journal Entry, Stock Entry, or ERPNext/Frappe core behavior was changed in this phase.

Risk grading:

| Grade | Meaning |
| --- | --- |
| High | Client-side only protection for money/accounting/stock/status action. |
| Medium | Sensitive value visible/editable through normal write permission. |
| Low | Wording, cleanup, or future improvement. |

## 2. Current Custom DocTypes

| DocType | Path | Module | Is Submittable | Track Changes | Allow Rename | Autoname | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Used Car Vehicle | `used_car_erp/used_car_erp/doctype/used_car_vehicle/used_car_vehicle.json` | Used Car ERP | Not set | 1 | 0 | `field:stock_no` | Main vehicle master and workflow state holder. |
| Used Car Money Flow | `used_car_erp/used_car_erp/doctype/used_car_money_flow/used_car_money_flow.json` | Used Car ERP | 0 | 1 | 0 | `field:money_flow_no` | Deposit/final payment fact record. |
| Used Car Voucher Draft | `used_car_erp/used_car_erp/doctype/used_car_voucher_draft/used_car_voucher_draft.json` | Used Car ERP | 0 | 1 | 0 | `field:voucher_draft_no` | Accounting voucher draft that can create Journal Entry. |
| Used Car Voucher Draft Line | `used_car_erp/used_car_erp/doctype/used_car_voucher_draft_line/used_car_voucher_draft_line.json` | Used Car ERP | Not set | Not set | 0 | Not set | Child table for voucher lines; permission rows are empty as expected for child tables. |
| Used Car Reservation | `used_car_erp/used_car_erp/doctype/used_car_reservation/used_car_reservation.json` | Used Car ERP | 0 | 1 | 0 | `field:reservation_no` | Reservation, deposit, final payment, and sale completion record. |
| Used Car Vehicle Cost | `used_car_erp/used_car_erp/doctype/used_car_vehicle_cost/used_car_vehicle_cost.json` | Used Car ERP | 0 | 1 | 0 | Not set | Vehicle cost fact record. |

No separate `Used Car Customer` custom DocType was found. Customer data currently links to ERPNext `Customer` where present.

## 3. Current Permission Rows By DocType

### Used Car Vehicle

| Role | Permlevel | Read | Write | Create | Delete | Submit | Cancel | Amend | Report | Export | If Owner |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| System Manager | 0 | 1 | 1 | 1 | 1 | 0 | 0 | 0 | 1 | 1 | 0 |

### Used Car Money Flow

| Role | Permlevel | Read | Write | Create | Delete | Submit | Cancel | Amend | Report | Export | If Owner |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| System Manager | 0 | 1 | 1 | 1 | 1 | 0 | 0 | 0 | 1 | 1 | 0 |

### Used Car Voucher Draft

| Role | Permlevel | Read | Write | Create | Delete | Submit | Cancel | Amend | Report | Export | If Owner |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| System Manager | 0 | 1 | 1 | 1 | 1 | 0 | 0 | 0 | 1 | 1 | 0 |

### Used Car Voucher Draft Line

| Role | Permlevel | Read | Write | Create | Delete | Submit | Cancel | Amend | Report | Export | If Owner |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| None | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A |

### Used Car Reservation

| Role | Permlevel | Read | Write | Create | Delete | Submit | Cancel | Amend | Report | Export | If Owner |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| System Manager | 0 | 1 | 1 | 1 | 1 | 0 | 0 | 0 | 1 | 1 | 0 |

### Used Car Vehicle Cost

| Role | Permlevel | Read | Write | Create | Delete | Submit | Cancel | Amend | Report | Export | If Owner |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| System Manager | 0 | 1 | 1 | 1 | 1 | 0 | 0 | 0 | 1 | 1 | 0 |

## 4. Sensitive Fields And Current Permlevel Status

| DocType | Fieldname | Label | Fieldtype | Current Permlevel | Current Read Only | Risk |
| --- | --- | --- | --- | --- | --- | --- |
| Used Car Vehicle | `purchase_price` | 購車價 | Currency | 0 | 0 | Medium: sensitive procurement cost is visible/editable to any role that receives normal write access. |
| Used Car Vehicle | `floor_price` | 底價 | Currency | 0 | 0 | Medium: floor price is visible/editable through normal write access. |
| Used Car Vehicle | `customer` | 客戶 | Link | 0 | 0 | Medium: customer sale fact is visible/editable through normal write access before accounting lock. |
| Used Car Vehicle | `sold_price` | 成交價 | Currency | 0 | 0 | Medium: sale amount is visible/editable through normal write access before accounting lock. |
| Used Car Vehicle | `deposit_journal_entry` | 訂金正式會計傳票 | Link | 0 | 1 | Medium: accounting link is visible at permlevel 0. |
| Used Car Vehicle | `final_journal_entry` | 尾款正式會計傳票 | Link | 0 | 1 | Medium: accounting link is visible at permlevel 0. |
| Used Car Vehicle | `formal_delivery_status` | 會計文件狀態 | Select | 0 | 1 | Medium: accounting status is visible at permlevel 0; server-side manual edit guard exists. |
| Used Car Vehicle | `formal_delivery_posting_date` | 會計文件處理日期 | Date | 0 | 1 | Medium: accounting date is visible at permlevel 0; server-side manual edit guard exists. |
| Used Car Vehicle | `sales_invoice` | Sales Invoice | Link | 0 | 1 | Medium: Sales Invoice link is visible at permlevel 0; server-side manual edit guard exists. |
| Used Car Vehicle | `advance_settlement_journal_entry` | 預收款沖轉傳票 | Link | 0 | 1 | Medium: Journal Entry link is visible at permlevel 0; server-side manual edit guard exists. |
| Used Car Vehicle | `formal_delivery_completed_at` | 會計文件完成時間 | Datetime | 0 | 1 | Medium: accounting completion metadata is visible at permlevel 0; server-side manual edit guard exists. |
| Used Car Vehicle | `formal_delivery_completed_by` | 會計文件完成人員 | Link | 0 | 1 | Medium: accounting completion metadata is visible at permlevel 0; server-side manual edit guard exists. |
| Used Car Vehicle | `total_cost` | 累計支出 | Currency | 0 | 1 | Medium: cost summary is visible at permlevel 0. |
| Used Car Vehicle | `gross_margin` | 管理毛利 | Currency | 0 | 1 | Medium: profit estimate is visible at permlevel 0 and also rendered in client summary. |
| Used Car Money Flow | `customer` | 客戶 | Link | 0 | 1 | Medium: customer link is visible at permlevel 0. |
| Used Car Money Flow | `amount` | 金額 | Currency | 0 | 1 | Medium: payment amount is visible at permlevel 0. |
| Used Car Money Flow | `voucher_draft` | 傳票草稿 | Link | 0 | 1 | Medium: accounting draft link is visible at permlevel 0. |
| Used Car Money Flow | `journal_entry` | 正式會計傳票 | Link | 0 | 1 | Medium: Journal Entry link is visible at permlevel 0. |
| Used Car Voucher Draft | `customer` | 客戶 | Link | 0 | 1 | Medium: customer link is visible at permlevel 0. |
| Used Car Voucher Draft | `total_debit` | 借方合計 | Currency | 0 | 1 | Medium: accounting amount is visible at permlevel 0. |
| Used Car Voucher Draft | `total_credit` | 貸方合計 | Currency | 0 | 1 | Medium: accounting amount is visible at permlevel 0. |
| Used Car Voucher Draft | `difference` | 借貸差額 | Currency | 0 | 1 | Low: calculation field is visible at permlevel 0. |
| Used Car Voucher Draft | `journal_entry` | 正式會計傳票 | Link | 0 | 1 | Medium: Journal Entry link is visible at permlevel 0. |
| Used Car Voucher Draft | `reviewed_by` | 審核人員 | Link | 0 | 1 | Medium: accounting reviewer metadata is visible at permlevel 0. |
| Used Car Voucher Draft | `reviewed_at` | 審核時間 | Datetime | 0 | 1 | Medium: accounting reviewer metadata is visible at permlevel 0. |
| Used Car Voucher Draft Line | `account` | 會計科目 | Link | 0 | 0 | Medium: accounting account line is editable through parent table write access. |
| Used Car Voucher Draft Line | `debit` | 借方 | Currency | 0 | 0 | Medium: accounting amount line is editable through parent table write access while draft is not posted. |
| Used Car Voucher Draft Line | `credit` | 貸方 | Currency | 0 | 0 | Medium: accounting amount line is editable through parent table write access while draft is not posted. |
| Used Car Reservation | `customer` | ERPNext 客戶 | Link | 0 | 1 | Medium: customer link is visible at permlevel 0. |
| Used Car Reservation | `deposit_amount` | 訂金金額 | Currency | 0 | 0 | Medium: payment amount is visible/editable through normal write access. |
| Used Car Reservation | `final_payment_amount` | 尾款金額 | Currency | 0 | 1 | Medium: final payment amount is visible at permlevel 0; server-side service-field guard exists. |
| Used Car Reservation | `voucher_draft` | 訂金傳票草稿 | Link | 0 | 1 | Medium: accounting draft link is visible at permlevel 0. |
| Used Car Reservation | `journal_entry` | 訂金正式會計傳票 | Link | 0 | 1 | Medium: Journal Entry link is visible at permlevel 0. |
| Used Car Reservation | `final_journal_entry` | 尾款正式會計傳票 | Link | 0 | 1 | Medium: Journal Entry link is visible at permlevel 0. |
| Used Car Vehicle Cost | `amount` | 金額 | Currency | 0 | 0 | Medium: cost amount is visible/editable through normal write access. |

No inspected custom DocType currently uses field-level `permlevel` for sensitive fields.

## 5. Current Client-Side-Only Button Hiding Risks

| Area | Client Entry Point | Server Method | Current Server Gate | Risk |
| --- | --- | --- | --- | --- |
| Vehicle tax metadata editability | `used_car_vehicle.js` role check uses `frappe.user_roles` for sold vehicle tax fields | Normal DocType save | Backend validates tax metadata values and accounting lock, but role-specific tax edit permission is client-side only before formal accounting lock. | High: accounting/tax-sensitive fields can be edited by any user who later receives normal vehicle write permission unless server role gate is added. |
| Vehicle cost creation | `新增單車成本` button hides only by vehicle status | New `Used Car Vehicle Cost` document | DocType permission only; no dedicated role/action gate found. | Medium: currently only System Manager has DocType permission, but future broader create/write permissions need server action boundary. |
| Cost summary recalculation | `重新計算成本摘要` button hides only by vehicle status | `vehicle_cost_service.recalculate_vehicle_cost_summary_for_vehicle` | Not found in role-gate search. | Medium: recalculation touches cost/profit summaries; needs explicit gate before broader permissions. |
| Profit/tax estimate refresh | `重新整理損益與稅務估算` button hides only by vehicle status | `vehicle_profit_tax_estimate_service.get_vehicle_profit_tax_estimate_for_vehicle` | Not found in role-gate search. | Medium: exposes management margin/tax estimates at permlevel 0. |
| Complete intake / stock-in | `完成入庫` button hides by vehicle status and local state | `vehicle_intake_service.complete_intake` | `vehicle.check_permission("write")` plus business validations; no dedicated intake role gate found. | High: stock mutation path should have explicit procurement/manager gate before broader vehicle write permissions. |
| Listing status transitions | `開始整備`, `直接上架`, `整備完成並上架`, `下架回庫存` | `vehicle_listing_service.*` | `vehicle.check_permission("write")` plus status validations; no dedicated role gate found. | Medium: operational status mutation should be role-scoped before broader vehicle write permissions. |
| Create reservation | `建立訂金保留` | `vehicle_reservation_service.create_reservation` | Not found in role-gate search; service-level business validations exist. | Medium: money/customer action currently depends on DocType permissions and business state. |
| Create final payment | `建立尾款收款` | `vehicle_reservation_service.create_final_payment_for_active_reservation` and `vehicle_money_flow_service.create_final_payment_money_flow_from_reservation` | Not found in role-gate search; service-level business validations exist. | High: payment/money-flow creation should have explicit server-side sales/accounting boundary. |
| Complete reservation | `確認成交` | `vehicle_reservation_service.complete_active_reservation` | Not found in role-gate search; service-level accounting preflight exists. | High: sale status mutation should have explicit sales/manager gate. |
| Cancel reservation | `取消保留` | `vehicle_reservation_service.cancel_active_reservation_for_vehicle` | Not found in role-gate search; service-level business validations exist. | Medium: status cancellation should be role-scoped. |
| Create Sales Invoice draft | `建立 Sales Invoice 草稿` | `vehicle_reservation_service.create_sales_invoice_draft_for_vehicle` | Not found in role-gate search; service-level business validations exist. | High: accounting document draft creation should have explicit accounting/manager gate. |
| Voucher confirm/reject/void | `確認入帳`, `退回草稿`, `作廢草稿` | `vehicle_voucher_service.confirm_voucher_draft`, `reject_voucher_draft`, `void_voucher_draft` | `draft.check_permission("write")` plus status/account validations; no dedicated accounting role gate found. | High: Journal Entry creation/submission and voucher status mutation need explicit accounting gate. |
| Accounting technical field visibility | `顯示文件連結` / `隱藏文件連結` | Client display only | No security boundary intended; fields remain permlevel 0. | Low: UX-only toggle may create false sense of protection if not paired with permlevel. |

## 6. Current Server-Side Permission Gates

| File | Gate / Method | Current Enforcement | Coverage |
| --- | --- | --- | --- |
| `used_car_vehicle.py` | `validate`, `_prevent_manual_sale_completion_change` | Blocks direct edits to sale completion fields unless service flag is set. | Protects completion summary integrity, not role-based access. |
| `used_car_vehicle.py` | `validate`, `_prevent_manual_formal_delivery_change` | Blocks direct edits to formal delivery/accounting fields unless service flag is set. | Protects accounting link/status integrity, not role-based access. |
| `used_car_vehicle.py` | `validate`, `_protect_locked_sale_workflow_fields` | Blocks sale fact changes after formal accounting lock. | Protects submitted accounting/stock consistency, not role-based access before lock. |
| `used_car_reservation.py` | `validate`, `_prevent_accounting_link_change` | Blocks manual edits to reservation status/accounting/payment service fields unless service flag is set. | Protects service-owned fields, not role-based access to actions. |
| `used_car_voucher_draft.py` | `validate`, `_prevent_posted_content_change` | Blocks changes to posted voucher date/memo/lines. | Protects posted accounting content, not role-based confirm authority. |
| `vehicle_voucher_service.py` | `confirm_voucher_draft` | Calls `draft.check_permission("write")`, validates draft state/accounts, creates and submits Journal Entry. | Relies on DocType write permission; no dedicated accounting role gate found. |
| `vehicle_voucher_service.py` | `reject_voucher_draft`, `void_voucher_draft` | Calls `draft.check_permission("write")` and validates status. | Relies on DocType write permission; no dedicated accounting role gate found. |
| `vehicle_intake_service.py` | `complete_intake` | Calls `vehicle.check_permission("write")` and validates VIN, purchase price, and status. | Relies on vehicle write permission; no dedicated intake/procurement gate found. |
| `vehicle_listing_service.py` | listing methods | Calls `vehicle.check_permission("write")` and validates status/stocked vehicle. | Relies on vehicle write permission; no dedicated operations gate found. |
| `vehicle_formal_delivery_service.py` | `_require_formal_delivery_submit_permission` | Allows Administrator or roles intersecting `SUBMIT_ALLOWED_ROLES`; otherwise blocks Sales Invoice submit. | Explicit server-side role gate exists for formal Sales Invoice submission. |
| `vehicle_formal_delivery_service.py` | `_require_advance_settlement_draft_permission` | Allows Administrator or roles intersecting `SETTLEMENT_DRAFT_ALLOWED_ROLES`; otherwise blocks settlement draft creation. | Explicit server-side role gate exists for advance settlement draft. |
| `vehicle_formal_delivery_service.py` | `_require_advance_settlement_submit_permission` | Allows Administrator or roles intersecting `SETTLEMENT_SUBMIT_ALLOWED_ROLES`; otherwise blocks settlement Journal Entry submit. | Explicit server-side role gate exists for settlement submit. |
| `vehicle_formal_delivery_service.py` | `_require_cancelled_sales_invoice_recovery_permission` | Allows Administrator or roles intersecting `RECOVERY_ALLOWED_ROLES`; otherwise blocks Sales Invoice draft relink recovery. | Explicit server-side role gate exists for recovery action. |

The app-level `hooks.py` contains commented Frappe `has_permission` examples only. No active global custom `has_permission` hook was found for these DocTypes.

## 7. Gaps Against Role Permission Boundary Spec

| Gap | Current State | Spec Expectation | Risk |
| --- | --- | --- | --- |
| Custom business roles are not represented in DocType permissions | Non-child custom DocTypes only grant `System Manager`. | Use roles such as Used Car Owner, Manager, Sales, Procurement, Preparation, Accounting, Accounting Manager, Viewer. | Low now because access is narrow; High before broader rollout if implemented ad hoc. |
| Field-level sensitivity is not implemented | Sensitive money, cost, margin, tax, customer, and accounting links are all permlevel 0. | Use Permission Level for purchase price, floor price, gross margin, accounting links, tax fields. | Medium. |
| Server action gates are incomplete | Formal delivery Phase 3B/3C/3D and recovery have role gates; many reservation, cost, intake, listing, and voucher actions do not. | Every money/accounting/stock/status action should have server-side checks. | High for broader role rollout. |
| Client-side visibility can be mistaken for security | Buttons are conditionally shown/hidden by status or `frappe.user_roles`. | JS display is UX only; backend must enforce action authority. | High for tax edit, voucher confirmation, final payment, Sales Invoice draft, and stock-in actions. |
| Permission rows are not aligned with intended matrix | Only System Manager has read/write/create/delete/report/export. | Built-in DocType permissions should separate read/create/write/submit/report/export by business role. | Medium. |
| Submit semantics are not used for voucher/money DocTypes | Money Flow and Voucher Draft are not submittable; Journal Entry is submitted by service. | Spec allows custom server checks for business actions beyond basic submit permission. | Medium. |
| No User Permission / branch scoping | No branch/shop/person-level record scoping found in current DocType permissions. | Future P4 may use User Permissions for branch/shop/company scope. | Low for current single-scope inventory. |

## 8. Recommended Phase P1-B Implementation Plan

| Step | Recommendation | Scope |
| --- | --- | --- |
| 1 | Create or seed the agreed used-car roles only after confirming role names from the boundary spec. | Roles only; no broad runtime rewrite. |
| 2 | Add minimal DocType permission rows for `Used Car Vehicle`, `Used Car Money Flow`, `Used Car Voucher Draft`, `Used Car Reservation`, and `Used Car Vehicle Cost`. | Built-in DocType Permissions first. |
| 3 | Apply field-level permlevels for procurement cost, floor price, gross margin, accounting links, voucher lines, and tax review fields. | Permission Level foundation. |
| 4 | Add a centralized permission helper for business actions before broadening write access. | Avoid scattered `frappe.get_roles` checks. |
| 5 | Gate high-risk whitelisted actions server-side: stock-in, final payment, Sales Invoice draft, voucher confirm/reject/void, sale completion, cost recalculation, and tax metadata edits. | Server-side action boundary. |
| 6 | Keep JS button hiding as UX only and align button visibility with backend action results. | Client cleanup after server gates. |
| 7 | Add permission verification for admin, normal employee, denied user, and direct-permission override cases. | Test/QA foundation before rollout. |

Suggested P1-B priority order:

| Priority | Action |
| --- | --- |
| High | Protect voucher confirmation and Journal Entry creation/submission with Used Car Accounting / Accounting Manager gates. |
| High | Protect Sales Invoice draft creation, final payment creation, and sale completion with explicit server-side gates. |
| High | Protect stock-in / intake mutation with Used Car Procurement / Manager gate. |
| Medium | Add permlevel protection for `purchase_price`, `floor_price`, `total_cost`, `gross_margin`, `sales_invoice`, Journal Entry links, and tax review fields. |
| Medium | Split vehicle read/write permissions for procurement, sales, operations, accounting, manager, owner, and viewer. |
| Low | Add branch/shop scoping later if the organization structure requires it. |

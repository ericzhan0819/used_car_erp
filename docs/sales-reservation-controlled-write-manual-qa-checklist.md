# Sales Reservation Controlled Write Manual QA Checklist Phase P1-F-3-A

## Purpose

This checklist verifies Phase P1-F-3-A after sales reservation flow was connected to service-controlled writes.

The goal is to confirm that allowed business users can complete the intended sales workflow through services, while raw DocType permissions and accounting boundaries remain restricted.

## Scope

This checklist covers:

```text
Used Car Sales / Manager / Owner operational sales reservation workflow
→ create reservation
→ create deposit money flow
→ auto-generate deposit voucher draft
→ create final payment money flow
→ auto-generate final payment voucher draft
→ accounting confirms voucher drafts
→ preflight delivery
→ complete sale
```

This checklist does not cover:

```text
Sales Invoice draft creation
Sales Invoice submit
Journal Entry controlled bypass
Stock Entry / intake controlled bypass
purchase_price write
Vehicle Cost amount write
tax metadata write
accounting link repair
formal delivery completion marker
```

## Preconditions

Before QA, make sure the latest code is pulled and runtime cache is refreshed:

```bash
cd ~/frappe/frappe-bench/apps/used_car_erp
git pull

cd ~/frappe/frappe-bench
bench restart
bench --site erpnext.localhost clear-cache
```

No migration is required for P1-F-3-A because it does not change DocType JSON, patches, or schema.

## Recommended Test Users

Use separate users when possible:

| User Type | Required Role |
| --- | --- |
| Sales user | `Used Car Sales` |
| Accounting user | `Used Car Accounting` |
| Manager user | `Used Car Manager` |
| Owner user | `Used Car Owner` |
| Admin user | `System Manager` |

Do not use `System Manager` for sales-role boundary tests because System Manager bypasses known action gates.

## Test Data Setup

Create or identify one eligible listed vehicle:

```text
Used Car Vehicle status = 上架中
item exists
serial_no exists
stock_entry exists
no active reservation
```

If no eligible vehicle exists, prepare one through the existing intake/listing workflow as admin or an authorized procurement/manager user.

Record before-counts for restricted ERPNext documents if possible:

```sql
select count(*) from `tabPayment Entry`;
select count(*) from `tabSales Invoice`;
select count(*) from `tabDelivery Note`;
select count(*) from `tabStock Entry`;
select count(*) from `tabJournal Entry`;
```

The reservation workflow should not create Payment Entry, Sales Invoice, Delivery Note, or extra Stock Entry. Journal Entry should only be created later when accounting confirms voucher drafts.

## A. Sales Can Create Reservation Through Service Flow

Log in as `Used Car Sales`.

Action:

```text
Open an eligible listed vehicle.
Create a reservation through the intended sales workflow UI / service button.
Enter customer name, customer phone, deposit amount, payment method, and optional reference/note.
```

Expected result:

```text
Used Car Reservation is created.
Used Car Money Flow for deposit is created.
Used Car Voucher Draft for deposit is auto-generated through internal service path.
Vehicle status changes from 上架中 to 保留中.
Reservation status is 有效.
Money Flow status is 待審核.
Voucher Draft status is 待審核.
No Journal Entry is created yet.
No Payment Entry / Sales Invoice / Delivery Note is created.
No extra Stock Entry is created.
```

Failure to watch for:

```text
Sales user gets raw DocPerm write error after action gate passed.
Reservation is created but money flow or voucher draft is missing.
Vehicle status does not change to 保留中.
Journal Entry is created before accounting confirmation.
Sales Invoice / Payment Entry / Delivery Note appears unexpectedly.
```

## B. Duplicate Reservation Remains Blocked

Stay as `Used Car Sales`.

Action:

```text
Try to create another active reservation for the same vehicle.
```

Expected result:

```text
The second reservation is blocked.
Existing active reservation remains unchanged.
No duplicate Money Flow is created.
No duplicate Voucher Draft is created.
```

## C. Sales Cannot Directly Confirm Voucher Draft

Stay as `Used Car Sales`.

Action:

```text
Open or call the voucher draft confirm action for the deposit voucher draft.
```

Expected result:

```text
Used Car Sales is blocked by action gate.
Voucher Draft remains 待審核.
Money Flow remains 待審核.
No Journal Entry is created.
```

This confirms P1-F-3-A did not accidentally grant accounting authority to Sales.

## D. Accounting Can Confirm Deposit Voucher Draft

Log in as `Used Car Accounting` or `Used Car Accounting Manager`.

Action:

```text
Open the generated deposit voucher draft.
Review lines.
Confirm voucher draft.
```

Expected result:

```text
Voucher Draft status becomes 已入帳.
Money Flow status becomes 已入帳.
Journal Entry is created and submitted.
Reservation journal_entry link is updated when applicable.
No Payment Entry / Sales Invoice / Delivery Note is created.
```

## E. Sales Can Create Final Payment Through Service Flow

Log in again as `Used Car Sales`.

Action:

```text
Open the reserved vehicle.
Create final payment through the intended sales workflow UI / service button.
Enter amount, payment method, payment date/reference/note as needed.
```

Expected result:

```text
Final payment Used Car Money Flow is created.
Final payment Used Car Voucher Draft is auto-generated through internal service path.
Reservation final_payment_amount is updated.
Reservation final_money_flow is updated.
Reservation final_voucher_draft is updated.
Vehicle remains 保留中.
Reservation remains 有效.
No Sales Invoice is created.
No Payment Entry is created.
No Delivery Note is created.
No extra Stock Entry is created.
No Journal Entry is created until accounting confirms the final payment voucher draft.
```

Failure to watch for:

```text
Vehicle changes to 已售出 immediately after final payment.
Sales Invoice / Payment Entry / Delivery Note is created.
Final payment overwrites existing deposit links incorrectly.
Duplicate final payment can be created.
```

## F. Duplicate Final Payment Remains Blocked

Stay as `Used Car Sales`.

Action:

```text
Try to create a second final payment for the same active reservation.
```

Expected result:

```text
The second final payment is blocked.
Existing final money flow and final voucher draft remain unchanged.
```

## G. Accounting Can Confirm Final Payment Voucher Draft

Log in as `Used Car Accounting` or `Used Car Accounting Manager`.

Action:

```text
Open the generated final payment voucher draft.
Confirm voucher draft.
```

Expected result:

```text
Final payment Voucher Draft status becomes 已入帳.
Final payment Money Flow status becomes 已入帳.
Journal Entry is created and submitted.
Reservation final_journal_entry link is updated when applicable.
No Sales Invoice / Payment Entry / Delivery Note is created.
```

## H. Sales Can Run Preflight But It Does Not Mutate Accounting Core

Log in as `Used Car Sales` or an allowed role that can access the vehicle/reservation context.

Action:

```text
Run 成交前檢查 / delivery preflight for the active reservation.
```

Expected result:

```text
Preflight passes only after both deposit and final payment are 已入帳.
Preflight returns existing money flow, voucher draft, and journal entry links.
No new Journal Entry is created by preflight.
No Sales Invoice / Payment Entry / Delivery Note / Stock Entry is created.
```

## I. Sales Can Complete Sale After Accounting Preflight Passes

Log in as `Used Car Sales`.

Action:

```text
Run 確認成交 / complete sale after both deposit and final payment are confirmed by accounting.
Enter optional completion note.
```

Expected result:

```text
Vehicle status changes from 保留中 to 已售出.
Reservation status changes from 有效 to 已完成.
Vehicle completion summary fields are written.
Reservation completed_at / completed_by / completion_note are written.
No Sales Invoice is created.
No Payment Entry is created.
No Delivery Note is created.
No Stock Entry is created.
No new Journal Entry is created by complete sale.
```

## J. Complete Sale Is Blocked Before Accounting Is Ready

Use a separate active reservation where either deposit or final payment has not been confirmed by accounting.

Log in as `Used Car Sales`.

Action:

```text
Try to run 確認成交 / complete sale.
```

Expected result:

```text
The action is blocked by preflight / business validation.
Vehicle remains 保留中.
Reservation remains 有效.
No completion summary is written.
No Sales Invoice / Payment Entry / Delivery Note / Stock Entry is created.
```

## K. Sales Can Cancel Active Reservation Through Service Flow

Use a separate active reservation that has not been completed.

Log in as `Used Car Sales`.

Action:

```text
Cancel active reservation through the intended service workflow.
Enter cancellation reason.
```

Expected result:

```text
Reservation status changes from 有效 to 已取消.
Reservation cancellation_reason / cancelled_at / cancelled_by are written.
Vehicle status changes from 保留中 to 上架中 only if it was still 保留中.
No Journal Entry is cancelled.
No Sales Invoice / Payment Entry / Delivery Note / Stock Entry is created or cancelled.
```

## L. Cancel Requires Reason

Log in as `Used Car Sales`.

Action:

```text
Try to cancel an active reservation without reason.
```

Expected result:

```text
The action is blocked.
Reservation remains 有效.
Vehicle status remains unchanged.
```

## M. Raw DocType Permission Boundary Remains Restricted

Log in as `Used Car Sales`.

Try direct raw form operations outside intended workflow:

```text
Directly edit Used Car Reservation level 1 / level 2 sensitive fields.
Directly edit Used Car Money Flow amount/customer/accounting links.
Directly edit Used Car Vehicle purchase_price / floor_price / total_cost / gross_margin.
Directly edit Used Car Vehicle accounting links.
Directly edit Used Car Voucher Draft lines or confirm/reject/void directly if not allowed.
```

Expected result:

```text
Sales cannot directly edit sensitive high-permlevel fields through raw DocType form.
Sales cannot perform accounting review actions.
Sales cannot access or mutate accounting-controlled links directly.
```

## N. Manager / Owner Workflow Check

Log in as `Used Car Manager` and `Used Car Owner` separately.

Action:

```text
Repeat reservation creation, final payment creation, cancellation, and complete sale through service workflow.
```

Expected result:

```text
Manager and Owner can perform sales reservation flow actions through service workflow.
Owner still cannot confirm/reject/void voucher draft unless also assigned Used Car Accounting or Used Car Accounting Manager.
Raw accounting authority is not implied by Owner role alone.
```

## O. Accounting Boundary Check

Log in as `Used Car Accounting`.

Action:

```text
Try to create reservation or final payment through sales workflow.
```

Expected result:

```text
Accounting user is blocked unless they also have Sales / Manager / Owner role.
Accounting can perform voucher draft accounting actions according to action gate.
```

## P. Restricted ERPNext Document Count Check

After completing QA, compare restricted document counts against expected behavior:

```sql
select count(*) from `tabPayment Entry`;
select count(*) from `tabSales Invoice`;
select count(*) from `tabDelivery Note`;
select count(*) from `tabStock Entry`;
select count(*) from `tabJournal Entry`;
```

Expected result:

```text
Payment Entry count unchanged.
Sales Invoice count unchanged.
Delivery Note count unchanged.
Stock Entry count unchanged except records intentionally created before QA setup.
Journal Entry count increases only when accounting confirms deposit/final payment voucher drafts.
```

## Pass Criteria

P1-F-3-A passes manual QA only if:

```text
1. Sales can complete the sales reservation workflow through service actions.
2. Sales cannot mutate sensitive fields through raw form access.
3. Sales cannot perform accounting review actions.
4. Voucher draft auto-generation still works.
5. Duplicate reservation and duplicate final payment remain blocked.
6. Complete sale requires accounting preflight to pass.
7. Complete sale does not create Sales Invoice / Payment Entry / Delivery Note / Stock Entry.
8. Restricted ERPNext core document counts match expectations.
9. Manager / Owner permissions behave as business roles, not accounting superuser roles.
10. Accounting role remains accounting-focused and does not become sales workflow authority unless combined with another role.
```

## Fail Fast Conditions

Stop and investigate immediately if any of these occurs:

```text
Sales can confirm / reject / void voucher draft.
Sales can create Sales Invoice draft.
Sales can submit Sales Invoice.
Sales can directly edit purchase_price, cost amount, tax metadata, or accounting links.
Reservation workflow creates Payment Entry / Sales Invoice / Delivery Note.
Complete sale creates Journal Entry or stock document.
A workflow succeeds without the required action role.
A controlled write accepts fields outside its allowlist.
```

## Notes

This checklist intentionally validates behavior at the business boundary, not only at the UI boundary.

Client-side button hiding is not sufficient. If possible, also verify server behavior by calling the whitelisted methods directly with a user that lacks the required action role.

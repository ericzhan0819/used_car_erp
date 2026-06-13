# Used Car DocType Permission Rows Design Phase P1-E

## Purpose

This document defines the minimum target DocType permission rows for the used-car business roles after Phase P1-D-A moved sensitive fields out of `permlevel 0`.

This is a design-first phase.

It does not change:

- DocType JSON;
- runtime Python;
- client scripts;
- user assignments;
- Role records;
- server-side action gates;
- ERPNext core permission behavior;
- Sales Invoice, Journal Entry, Stock Entry, Payment Entry, or Delivery Note behavior.

The goal is to prevent accidentally granting broad access to pricing, cost, margin, accounting links, or tax-control fields when opening custom DocType access to non-System Manager roles.

## Current Preconditions

The project already completed:

```text
P1-A: permission inventory
P1-B: used-car role records foundation
P1-C: field permlevel design
P1-D-A: applied permlevels to DocType JSON
P1-D-A-1: protected Used Car Voucher Draft Line.note at permlevel 2
```

After pulling the latest commits, the site must run migration before verifying permissions in the UI:

```bash
cd ~/frappe/frappe-bench
bench --site erpnext.localhost migrate
```

## Critical Rule

Frappe `permlevel` is a level-based permission boundary, not a per-field role matrix.

If a role receives `read` on a DocType at `permlevel 1`, that role may read all fields in that DocType that are assigned to level 1.

Therefore, do not treat `permlevel 1` as if it can selectively expose only one field such as `purchase_price`.

## Current Permlevel Risk

### Used Car Vehicle Level 1

Current level 1 includes multiple sensitive categories:

```text
purchase_price
floor_price
sold_price
total_cost
gross_margin
```

This means:

```text
Granting Vehicle level 1 read to Procurement for purchase_price may also expose floor_price, sold_price, total_cost, and gross_margin.
```

Therefore, Phase P1-E must not grant `Used Car Procurement`, `Used Car Sales`, or `Used Car Preparation` Vehicle level 1 access by default.

### Reservation Level 1

Current level 1 includes customer and money fields:

```text
customer
deposit_amount
final_payment_amount
```

This means a sales role that directly creates or edits a reservation through the DocType form may need level 1 access to operate naturally, but granting that access also exposes money/customer fields for the whole level.

Phase P1-E should not solve this by broad DocPerm. Reservation creation should be handled by a controlled server-side action in Phase P1-F.

### Vehicle Cost Level 1

Current level 1 includes:

```text
amount
```

Preparation users may need to enter cost amount operationally, but amount is a sensitive cost field. Phase P1-E should not broadly grant this until a server-side action gate or a more precise UX path exists.

## Permission Strategy

Use DocType permissions only for baseline document visibility and low-risk operational editing.

Use server-side action gates for business actions that change money, accounting documents, stock, locked state, sale completion, or irreversible workflow state.

Do not rely on client-side button hiding as a permission boundary.

## Global Defaults For Phase P1-E

Unless explicitly stated otherwise, new non-System Manager permission rows should use:

| Permission | Default |
| --- | --- |
| read | policy-based |
| write | restricted |
| create | restricted |
| delete | 0 |
| submit | 0 |
| cancel | 0 |
| amend | 0 |
| report | usually same as read |
| export | 0 |
| print | 0 |
| email | 0 |
| share | 0 |

Reasoning:

```text
Export, print, email, and share can leak business-sensitive vehicle, customer, money, cost, and accounting information. They should be granted later only after a separate policy decision.
```

System Manager permission rows may remain broad for development and administration.

## Target Roles

Phase P1-E covers the existing used-car role skeleton:

```text
Used Car Owner
Used Car Manager
Used Car Procurement
Used Car Sales
Used Car Preparation
Used Car Accounting
Used Car Accounting Manager
Used Car Viewer
Used Car Auditor
```

## Target DocTypes

Phase P1-E covers these custom DocTypes:

```text
Used Car Vehicle
Used Car Money Flow
Used Car Voucher Draft
Used Car Voucher Draft Line
Used Car Reservation
Used Car Vehicle Cost
```

`Used Car Voucher Draft Line` is a child table. It should not receive standalone DocPerm rows.

## Minimum Permission Rows By Role

### Used Car Viewer

Purpose:

```text
Read-only operational vehicle visibility.
```

Rows:

| DocType | Permlevel | Read | Report | Create | Write | Notes |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| Used Car Vehicle | 0 | 1 | 1 | 0 | 0 | Read-only vehicle list/detail access. |

Do not grant:

```text
level 1
level 2
level 3
Money Flow
Reservation
Vehicle Cost
Voucher Draft
export / print / email / share
```

Open question:

```text
Used Car Vehicle.customer is currently level 0. If customer visibility is not acceptable for Viewer, move customer out of level 0 before granting Viewer read access.
```

### Used Car Sales

Purpose:

```text
Sales users can see operational vehicle data and participate in reservation/sales workflow through controlled business actions.
```

Rows:

| DocType | Permlevel | Read | Report | Create | Write | Notes |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| Used Car Vehicle | 0 | 1 | 1 | 0 | 0 | Read-only vehicle context. |
| Used Car Reservation | 0 | 1 | 1 | 0 | 0 | Read reservation shell/status only. Creation should use server action. |
| Used Car Money Flow | 0 | 1 | 1 | 0 | 0 | Read non-sensitive money-flow shell/status only. |

Do not grant:

```text
Used Car Vehicle level 1
Used Car Vehicle level 2
Used Car Reservation level 1
Used Car Reservation level 2
Used Car Money Flow level 1
Used Car Money Flow level 2
Vehicle Cost
Voucher Draft
Vehicle write
Reservation create/write by raw DocType form
Money Flow create/write by raw DocType form
```

Rationale:

```text
Sales needs to perform actions such as create reservation, receive deposit, create final payment, or complete sale. These are not simple DocType writes. They must use server-side methods with explicit role gates and business validations.
```

### Used Car Procurement

Purpose:

```text
Procurement users can create and maintain ordinary vehicle acquisition data without seeing margin, floor price, accounting links, or tax-control fields.
```

Rows:

| DocType | Permlevel | Read | Report | Create | Write | Notes |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| Used Car Vehicle | 0 | 1 | 1 | 1 | 1 | Operational vehicle intake data only. |

Do not grant:

```text
Used Car Vehicle level 1
Used Car Vehicle level 2
Used Car Vehicle level 3
Money Flow
Reservation
Vehicle Cost amount access
Voucher Draft
```

Rationale:

```text
Procurement may need purchase_price, but current Vehicle level 1 also contains floor_price, sold_price, total_cost, and gross_margin. Do not grant level 1 until the field levels are split more precisely or purchase price is handled by a controlled server-side action.
```

Required Phase P1-F action gate:

```text
set / update purchase_price
complete intake / stock-in
link Item / Serial No / Warehouse / Stock Entry / Purchase Invoice
```

### Used Car Preparation

Purpose:

```text
Preparation users can view vehicle context and create operational cost records without direct access to sensitive cost amount until an action gate is available.
```

Rows:

| DocType | Permlevel | Read | Report | Create | Write | Notes |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| Used Car Vehicle | 0 | 1 | 1 | 0 | 0 | Read-only vehicle context. |
| Used Car Vehicle Cost | 0 | 1 | 1 | 1 | 1 | Cost shell fields only; amount remains level 1. |

Do not grant:

```text
Used Car Vehicle level 1
Used Car Vehicle Cost level 1
Money Flow
Reservation
Voucher Draft
```

Rationale:

```text
Vehicle Cost amount is sensitive. Preparation may later receive a controlled cost-entry workflow, but Phase P1-E should not expose cost amount broadly through level 1 DocPerm.
```

Required Phase P1-F action gate:

```text
create cost with amount
update cost amount
recalculate vehicle total_cost / gross_margin
lock or confirm cost record
```

### Used Car Accounting

Purpose:

```text
Accounting users can read operational context, financial values, and accounting links, and can work on voucher drafts. Formal accounting actions still require server-side gates.
```

Rows:

| DocType | Permlevel | Read | Report | Create | Write | Notes |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| Used Car Vehicle | 0 | 1 | 1 | 0 | 0 | Vehicle context. |
| Used Car Vehicle | 1 | 1 | 0 | 0 | 0 | Read financial values. |
| Used Car Vehicle | 2 | 1 | 0 | 0 | 0 | Read accounting document links/status. |
| Used Car Money Flow | 0 | 1 | 1 | 0 | 0 | Money-flow context. |
| Used Car Money Flow | 1 | 1 | 0 | 0 | 0 | Read customer and amount. |
| Used Car Money Flow | 2 | 1 | 0 | 0 | 0 | Read voucher / Journal Entry links. |
| Used Car Reservation | 0 | 1 | 1 | 0 | 0 | Reservation context. |
| Used Car Reservation | 1 | 1 | 0 | 0 | 0 | Read customer and payment amount. |
| Used Car Reservation | 2 | 1 | 0 | 0 | 0 | Read money-flow and accounting links. |
| Used Car Vehicle Cost | 0 | 1 | 1 | 0 | 0 | Cost context. |
| Used Car Vehicle Cost | 1 | 1 | 0 | 0 | 0 | Read amount. |
| Used Car Voucher Draft | 0 | 1 | 1 | 0 | 1 | Work on voucher draft shell fields. |
| Used Car Voucher Draft | 2 | 1 | 0 | 0 | 1 | Work on accounting fields before confirmation, if policy allows. |

Do not grant:

```text
Vehicle write
Money Flow write
Reservation write
Vehicle Cost write level 1
submit / cancel / amend
Voucher confirm / reject / void by raw DocType write alone
Journal Entry creation/submission without server-side gate
```

Rationale:

```text
Accounting can review and prepare accounting data, but confirm/reject/void and Journal Entry creation must be explicit server methods with role checks and business validations.
```

### Used Car Accounting Manager

Purpose:

```text
Accounting manager has broader accounting review/control visibility and limited correction authority.
```

Rows:

| DocType | Permlevel | Read | Report | Create | Write | Notes |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| Used Car Vehicle | 0 | 1 | 1 | 0 | 0 | Vehicle context. |
| Used Car Vehicle | 1 | 1 | 0 | 0 | 0 | Financial values. |
| Used Car Vehicle | 2 | 1 | 0 | 0 | 0 | Accounting links/status. |
| Used Car Vehicle | 3 | 1 | 0 | 0 | 0 | Tax/exception fields read by default. |
| Used Car Money Flow | 0 | 1 | 1 | 0 | 0 | Money-flow context. |
| Used Car Money Flow | 1 | 1 | 0 | 0 | 0 | Customer and amount. |
| Used Car Money Flow | 2 | 1 | 0 | 0 | 0 | Accounting links. |
| Used Car Reservation | 0 | 1 | 1 | 0 | 0 | Reservation context. |
| Used Car Reservation | 1 | 1 | 0 | 0 | 0 | Customer and amount. |
| Used Car Reservation | 2 | 1 | 0 | 0 | 0 | Accounting links. |
| Used Car Vehicle Cost | 0 | 1 | 1 | 0 | 1 | Cost context/correction policy. |
| Used Car Vehicle Cost | 1 | 1 | 0 | 0 | 1 | Cost amount correction policy. |
| Used Car Voucher Draft | 0 | 1 | 1 | 0 | 1 | Voucher draft review. |
| Used Car Voucher Draft | 2 | 1 | 0 | 0 | 1 | Accounting draft details. |

Do not grant by default:

```text
submit
cancel
amend
delete
export / print / email / share
```

Open policy question:

```text
Whether Accounting Manager can write Used Car Vehicle level 3 tax/review fields should be decided in a separate tax-control phase. Default for P1-E is read-only.
```

### Used Car Manager

Purpose:

```text
Manager can oversee business operations and read sensitive financial summaries without directly changing accounting-controlled fields.
```

Rows:

| DocType | Permlevel | Read | Report | Create | Write | Notes |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| Used Car Vehicle | 0 | 1 | 1 | 1 | 1 | Operational management. |
| Used Car Vehicle | 1 | 1 | 0 | 0 | 0 | Read price/cost/margin. |
| Used Car Vehicle | 2 | 1 | 0 | 0 | 0 | Read accounting status/links if business policy allows. |
| Used Car Reservation | 0 | 1 | 1 | 0 | 0 | Reservation oversight. |
| Used Car Reservation | 1 | 1 | 0 | 0 | 0 | Read customer/payment amount. |
| Used Car Reservation | 2 | 1 | 0 | 0 | 0 | Read accounting links/status. |
| Used Car Money Flow | 0 | 1 | 1 | 0 | 0 | Money-flow oversight. |
| Used Car Money Flow | 1 | 1 | 0 | 0 | 0 | Read customer/amount. |
| Used Car Money Flow | 2 | 1 | 0 | 0 | 0 | Read accounting links. |
| Used Car Vehicle Cost | 0 | 1 | 1 | 0 | 0 | Cost oversight. |
| Used Car Vehicle Cost | 1 | 1 | 0 | 0 | 0 | Read cost amount. |
| Used Car Voucher Draft | 0 | 1 | 1 | 0 | 0 | Voucher status oversight. |
| Used Car Voucher Draft | 2 | 1 | 0 | 0 | 0 | Accounting details read-only, policy-based. |

Do not grant by default:

```text
level 3 write
raw money-flow write
raw accounting write
submit / cancel / amend
delete
```

### Used Car Owner

Purpose:

```text
Owner has full business visibility but should still avoid bypassing accounting workflows through raw DocType writes.
```

Rows:

| DocType | Permlevel | Read | Report | Create | Write | Notes |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| Used Car Vehicle | 0 | 1 | 1 | 1 | 1 | Operational control. |
| Used Car Vehicle | 1 | 1 | 0 | 0 | 0 | Read financial values by default. |
| Used Car Vehicle | 2 | 1 | 0 | 0 | 0 | Read accounting links/status. |
| Used Car Vehicle | 3 | 1 | 0 | 0 | 0 | Read tax/exception fields by default. |
| Used Car Reservation | 0 | 1 | 1 | 0 | 0 | Reservation visibility. |
| Used Car Reservation | 1 | 1 | 0 | 0 | 0 | Customer/payment visibility. |
| Used Car Reservation | 2 | 1 | 0 | 0 | 0 | Accounting link visibility. |
| Used Car Money Flow | 0 | 1 | 1 | 0 | 0 | Money-flow visibility. |
| Used Car Money Flow | 1 | 1 | 0 | 0 | 0 | Customer/amount visibility. |
| Used Car Money Flow | 2 | 1 | 0 | 0 | 0 | Accounting link visibility. |
| Used Car Vehicle Cost | 0 | 1 | 1 | 0 | 0 | Cost visibility. |
| Used Car Vehicle Cost | 1 | 1 | 0 | 0 | 0 | Cost amount visibility. |
| Used Car Voucher Draft | 0 | 1 | 1 | 0 | 0 | Voucher overview. |
| Used Car Voucher Draft | 2 | 1 | 0 | 0 | 0 | Voucher accounting details. |

Owner write access to level 1/2/3 should not be granted in P1-E by default.

Rationale:

```text
Even Owner-level correction should use explicit correction or reversal flows, not raw edits that bypass accounting and audit boundaries.
```

### Used Car Auditor

Purpose:

```text
Auditor can inspect records but cannot mutate business, money, accounting, stock, tax, or correction state.
```

Rows:

| DocType | Permlevel | Read | Report | Create | Write | Notes |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| Used Car Vehicle | 0 | 1 | 1 | 0 | 0 | Operational context. |
| Used Car Vehicle | 1 | 1 | 0 | 0 | 0 | Financial values. |
| Used Car Vehicle | 2 | 1 | 0 | 0 | 0 | Accounting links/status. |
| Used Car Vehicle | 3 | 1 | 0 | 0 | 0 | Tax/exception read-only. |
| Used Car Money Flow | 0 | 1 | 1 | 0 | 0 | Money-flow context. |
| Used Car Money Flow | 1 | 1 | 0 | 0 | 0 | Customer/amount. |
| Used Car Money Flow | 2 | 1 | 0 | 0 | 0 | Accounting links. |
| Used Car Reservation | 0 | 1 | 1 | 0 | 0 | Reservation context. |
| Used Car Reservation | 1 | 1 | 0 | 0 | 0 | Customer/payment amounts. |
| Used Car Reservation | 2 | 1 | 0 | 0 | 0 | Accounting links. |
| Used Car Vehicle Cost | 0 | 1 | 1 | 0 | 0 | Cost context. |
| Used Car Vehicle Cost | 1 | 1 | 0 | 0 | 0 | Cost amount. |
| Used Car Voucher Draft | 0 | 1 | 1 | 0 | 0 | Voucher context. |
| Used Car Voucher Draft | 2 | 1 | 0 | 0 | 0 | Accounting lines/details. |

Do not grant:

```text
create
write
delete
submit
cancel
amend
export / print / email / share unless explicitly approved
```

## DocType-Level Matrix Summary

### Used Car Vehicle

| Role | L0 | L1 | L2 | L3 |
| --- | --- | --- | --- | --- |
| Used Car Viewer | read | no | no | no |
| Used Car Sales | read | no | no | no |
| Used Car Procurement | read/create/write | no | no | no |
| Used Car Preparation | read | no | no | no |
| Used Car Accounting | read | read | read | no |
| Used Car Accounting Manager | read | read | read | read |
| Used Car Manager | read/create/write | read | read | no by default |
| Used Car Owner | read/create/write | read | read | read |
| Used Car Auditor | read | read | read | read |

### Used Car Reservation

| Role | L0 | L1 | L2 |
| --- | --- | --- | --- |
| Used Car Viewer | no | no | no |
| Used Car Sales | read | no | no |
| Used Car Procurement | no | no | no |
| Used Car Preparation | no | no | no |
| Used Car Accounting | read | read | read |
| Used Car Accounting Manager | read | read | read |
| Used Car Manager | read | read | read |
| Used Car Owner | read | read | read |
| Used Car Auditor | read | read | read |

### Used Car Money Flow

| Role | L0 | L1 | L2 |
| --- | --- | --- | --- |
| Used Car Viewer | no | no | no |
| Used Car Sales | read | no | no |
| Used Car Procurement | no | no | no |
| Used Car Preparation | no | no | no |
| Used Car Accounting | read | read | read |
| Used Car Accounting Manager | read | read | read |
| Used Car Manager | read | read | read |
| Used Car Owner | read | read | read |
| Used Car Auditor | read | read | read |

### Used Car Vehicle Cost

| Role | L0 | L1 |
| --- | --- | --- |
| Used Car Viewer | no | no |
| Used Car Sales | no | no |
| Used Car Procurement | no by default | no |
| Used Car Preparation | read/create/write | no |
| Used Car Accounting | read | read |
| Used Car Accounting Manager | read/write | read/write |
| Used Car Manager | read | read |
| Used Car Owner | read | read |
| Used Car Auditor | read | read |

### Used Car Voucher Draft

| Role | L0 | L2 |
| --- | --- | --- |
| Used Car Viewer | no | no |
| Used Car Sales | no | no |
| Used Car Procurement | no | no |
| Used Car Preparation | no | no |
| Used Car Accounting | read/write | read/write |
| Used Car Accounting Manager | read/write | read/write |
| Used Car Manager | read | read |
| Used Car Owner | read | read |
| Used Car Auditor | read | read |

### Used Car Voucher Draft Line

No standalone permission rows.

Reason:

```text
Used Car Voucher Draft Line is a child table. Access is controlled through the parent Used Car Voucher Draft and field permlevel.
```

## High-Risk Actions Not Covered By DocPerm Alone

These actions must have explicit server-side permission gates before broad operational write access is introduced:

```text
complete intake / stock-in
create or update purchase_price
create reservation
cancel reservation
create deposit money flow
create final payment money flow
complete sale / mark sold
create Sales Invoice draft
submit Sales Invoice / stock-out
create advance settlement Journal Entry draft
submit settlement Journal Entry
create voucher draft
confirm voucher draft
reject voucher draft
void voucher draft
repair Sales Invoice link
recalculate vehicle cost summary
recalculate profit / VAT estimate
edit tax metadata
lock or unlock accounting-controlled fields
```

## P1-F Server Gate Direction

Phase P1-F should introduce a small permission helper or explicit checks in service methods.

P1-F-0/P1-F-1 has turned the action gate concept into a shared helper skeleton. DocPerm does not equal high-risk business action permission. P1-F-2 should connect the helper to existing whitelisted service methods in small, testable batches.

P1-F-2 已開始把 action gate 接到第一批高風險 service methods，但尚未放寬 DocPerm 或加入 controlled write bypass。

Suggested conceptual actions:

```text
used_car_vehicle.intake.complete
used_car_vehicle.purchase_price.write
used_car_vehicle.status.transition
used_car_reservation.create
used_car_reservation.cancel
used_car_reservation.complete
used_car_money_flow.deposit.create
used_car_money_flow.final_payment.create
used_car_vehicle_cost.create_with_amount
used_car_vehicle_cost.amount.write
used_car_vehicle_cost.summary.recalculate
used_car_voucher_draft.create
used_car_voucher_draft.review
used_car_voucher_draft.confirm
used_car_voucher_draft.reject
used_car_voucher_draft.void
used_car_sales_invoice_draft.create
used_car_sales_invoice.submit
used_car_advance_settlement.create_draft
used_car_advance_settlement.submit
used_car_tax_metadata.write
used_car_accounting_link.repair
```

These action gates should check:

```text
current user role
business state
linked document state
accounting lock state
vehicle status
reservation status
money-flow status
voucher status
idempotency
same source document consistency
```

## Implementation Guidance For Future P1-E-1

## Phase P1-E-1 Runtime Application Boundary

P1-E-1 applies a more conservative runtime subset than parts of the design matrix. It does not grant Preparation `Vehicle Cost` create/write because `amount` is required and protected at level 1; it does not grant Sales raw Reservation creation; and it does not grant Procurement level 1 `purchase_price` visibility because that level also exposes other sensitive vehicle financial fields. These operations are intentionally deferred to P1-F server-side action gates.

When implementing DocPerm rows:

1. Add only the rows listed in this document.
2. Keep all `delete`, `submit`, `cancel`, and `amend` disabled for non-System Manager roles.
3. Keep `export`, `print`, `email`, and `share` disabled unless a separate policy says otherwise.
4. Do not add permission rows for `Used Car Voucher Draft Line`.
5. Run `bench --site erpnext.localhost migrate` after DocType JSON changes.
6. Use Role Permission Manager or fixture verification to confirm rows.
7. Manually test with at least these users:
   - Used Car Viewer
   - Used Car Sales
   - Used Car Procurement
   - Used Car Preparation
   - Used Car Accounting
   - Used Car Accounting Manager
   - Used Car Manager
   - Used Car Auditor

## Suggested Verification Queries

After implementation and migration:

```sql
select parent, role, permlevel, `read`, `write`, `create`, `delete`, `submit`, `cancel`, `amend`, `report`, `export`, `print`, `email`, `share`
from tabDocPerm
where parent in (
  'Used Car Vehicle',
  'Used Car Money Flow',
  'Used Car Voucher Draft',
  'Used Car Reservation',
  'Used Car Vehicle Cost'
)
order by parent, role, permlevel;
```

Check child table remains empty:

```sql
select parent, role, permlevel, `read`, `write`, `create`
from tabDocPerm
where parent = 'Used Car Voucher Draft Line';
```

Expected result:

```text
No rows for Used Car Voucher Draft Line.
```

## Acceptance Criteria

Phase P1-E design is acceptable only if:

```text
1. No ordinary role receives broad level 1 access just to expose one field.
2. Sales does not receive cost, floor price, margin, or accounting-link visibility.
3. Procurement does not receive floor price, sold price, total cost, gross margin, or accounting-link visibility.
4. Preparation does not receive accounting-link visibility.
5. Accounting can read money/accounting context but cannot bypass confirm/reject/void flows by raw DocType write alone.
6. Manager/Owner read visibility does not become unrestricted correction authority.
7. Auditor is read-only.
8. submit/cancel/amend remain disabled for custom used-car roles.
9. Used Car Voucher Draft Line remains a child table with no standalone DocPerm rows.
10. P1-F server-side gates are explicitly required before high-risk operations are opened.
```

## Final Decision

Phase P1-E should be conservative.

The safe first step is:

```text
Open minimal document visibility.
Keep sensitive levels restricted to accounting/management read-only where possible.
Do not grant ordinary roles level 1 access just because one field in that level is operationally useful.
Move high-risk business operations to explicit server-side action gates in Phase P1-F.
```

This prevents the project from accidentally exposing purchase price, floor price, sold price, total cost, gross margin, accounting links, or tax-control fields through Frappe's level-based permission model.

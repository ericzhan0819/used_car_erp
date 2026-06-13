# Used Car Controlled Write Bypass Design Phase P1-F-3

## Purpose

Phase P1-F-3 defines how selected server-side used-car business workflows may write documents even when the acting business role does not have broad raw DocType write access.

This is required because Phase P1-E-1 intentionally kept DocType permissions conservative, and Phase P1-F-2 introduced action gates without changing existing `check_permission`, `insert`, or `save` behavior.

The target is not to bypass security. The target is to support safe, service-controlled business actions after explicit action authorization.

## Current State

Completed permission phases:

```text
P1-A: permission inventory
P1-B: used-car role records foundation
P1-C: field permlevel design
P1-D-A: sensitive field permlevel application
P1-E-1: minimal DocType permission rows
P1-F-0/P1-F-1: action gate design and helper skeleton
P1-F-2: first high-risk service methods adopted action gate
```

Current behavior after P1-F-2:

```text
User role passes action gate
→ service continues
→ existing DocPerm / check_permission / insert / save may still block the operation
```

This is expected.

P1-F-3 decides where and how to introduce narrow controlled writes so that business users can complete allowed workflows without granting broad sensitive DocType write permission.

## Problem To Solve

Frappe permission levels are level-based, not field-specific per role.

For example:

```text
Used Car Sales should be allowed to create a reservation through the service workflow.
```

But direct Reservation level 1 write would expose or allow direct form writes to fields such as:

```text
customer
deposit_amount
final_payment_amount
```

Similarly, direct Vehicle level 1 access may expose:

```text
purchase_price
floor_price
sold_price
total_cost
gross_margin
```

Therefore, the safe path is:

```text
Do not grant broad DocPerm.
Allow selected service methods to write selected fields only after action gate and business validation pass.
```

## Core Rule

Controlled write bypass is allowed only when all conditions are true:

```text
1. The action has an explicit ACTION_ROLE_MAP entry.
2. The caller has passed assert_can_perform_used_car_action(action).
3. The service method owns the workflow and validation.
4. The target DocType is explicitly allowed for that workflow.
5. The written fields are explicitly whitelisted for that workflow.
6. The business state transition is valid.
7. The operation is idempotent or has duplicate prevention.
8. Existing accounting, stock, and linked-document integrity checks are preserved.
```

If any condition is not true, do not bypass DocPerm.

## Non-goals

P1-F-3 must not:

```text
- create a custom login system;
- create a custom permission table;
- replace Frappe Role / DocPerm / Permission Level;
- grant broad DocPerm to business roles;
- add submit/cancel/amend permission to used-car roles;
- bypass permissions for ERPNext core accounting or stock documents casually;
- allow raw form edits to sensitive fields;
- use ignore_permissions=True without action-gate and workflow-level justification;
- let client-side button hiding become a security boundary;
- change the meaning of delivery, payment, and accounting status boundaries.
```

## Controlled Write Pattern

The preferred pattern is:

```python
assert_can_perform_used_car_action(action)
validate_inputs()
load_and_validate_source_documents()
validate_business_state()
validate_no_duplicate_target_document()
create_or_update_allowed_documents_with_controlled_permissions()
write_only_allowed_fields()
commit_or_rollback()
```

The permission bypass must be local to the service workflow. It must not be exposed as a general-purpose helper that arbitrary callers can use to write any DocType.

## Helper Direction

If helper code is introduced, it should be narrowly scoped.

Possible helper shape:

```python
def insert_service_controlled_doc(doc, *, action: str, allowed_doctype: str):
    assert_can_perform_used_car_action(action)
    if doc.doctype != allowed_doctype:
        frappe.throw("此服務不可建立指定文件類型。")
    return doc.insert(ignore_permissions=True)
```

Possible field update helper shape:

```python
def set_service_controlled_values(doc, *, action: str, allowed_fields: set[str], values: dict):
    assert_can_perform_used_car_action(action)
    disallowed_fields = set(values) - allowed_fields
    if disallowed_fields:
        frappe.throw("此服務不可寫入未授權欄位。")
    for fieldname, value in values.items():
        doc.set(fieldname, value)
    return doc.save(ignore_permissions=True)
```

However, P1-F-3 implementation should not introduce overly generic bypass tools unless tests clearly constrain their behavior.

## Required Tests For Any Controlled Write

Every controlled write implementation must test at least:

```text
1. Allowed role can pass action gate.
2. Disallowed role is blocked before document mutation.
3. Unknown action is blocked.
4. Controlled write does not allow disallowed DocType.
5. Controlled write does not allow disallowed fields.
6. Duplicate target document remains blocked.
7. Existing state validation still applies.
8. Existing restricted ERPNext documents are not created unexpectedly.
```

For workflows that create accounting or stock documents, tests must also assert that the expected ERPNext core document is the only document created or submitted.

## P1-F-3-A Recommended First Scope

The first controlled write implementation should be limited to sales-side reservation flow.

Recommended scope:

```text
1. Sales creates reservation through VehicleReservationService.create_reservation.
2. The service creates the related deposit Used Car Money Flow.
3. The service creates the related Used Car Voucher Draft through existing internal workflow.
4. Sales creates final payment through VehicleReservationService.create_final_payment_for_active_reservation.
5. Sales cancels active reservation through service workflow.
6. Sales confirms sale after accounting preflight has passed.
```

P1-F-3-A should avoid:

```text
- Sales Invoice draft creation;
- Sales Invoice submit;
- Journal Entry confirm/reject/void permission bypass;
- Stock Entry / intake bypass;
- purchase_price writes;
- Vehicle Cost amount writes;
- tax metadata writes;
- accounting-link repair;
- formal delivery completion marker.
```

Reason:

```text
Reservation and sales-side money flow are the first workflow where business users need operational action authority, but formal accounting and ERPNext core document submission should remain more tightly controlled.
```

## First-Scope Allowed Write Surface

### Reservation Creation

Action:

```text
used_car_reservation.create
```

Allowed actor roles:

```text
Used Car Sales
Used Car Manager
Used Car Owner
System Manager
```

Allowed document writes:

```text
Used Car Reservation insert
Used Car Money Flow insert for deposit
Used Car Voucher Draft insert for generated deposit draft
Used Car Vehicle status update: 上架中 → 保留中
Used Car Reservation link updates: money_flow, voucher_draft
Used Car Money Flow link update: voucher_draft
```

Allowed fields must remain constrained to fields already set by the existing service workflow.

Do not allow the caller to pass arbitrary fields into Reservation, Money Flow, Voucher Draft, or Vehicle.

### Final Payment Creation

Action:

```text
used_car_money_flow.final_payment.create
```

Allowed actor roles:

```text
Used Car Sales
Used Car Manager
Used Car Owner
System Manager
```

Allowed document writes:

```text
Used Car Money Flow insert for final payment
Used Car Voucher Draft insert for generated final payment draft
Used Car Reservation final payment fields update
Used Car Reservation final_money_flow link update
Used Car Reservation final_voucher_draft link update
Used Car Money Flow voucher_draft link update
```

Do not update Vehicle sold/completed status here.

### Reservation Cancel

Action:

```text
used_car_reservation.cancel
```

Allowed actor roles:

```text
Used Car Sales
Used Car Manager
Used Car Owner
System Manager
```

Allowed document writes:

```text
Used Car Reservation status: 有效 → 已取消
Used Car Reservation cancellation_reason
Used Car Reservation cancelled_at
Used Car Reservation cancelled_by
Used Car Vehicle status: 保留中 → 上架中, only when the vehicle is still 保留中
```

Do not cancel Journal Entry, Sales Invoice, Stock Entry, or Payment Entry.

### Complete Sale

Action:

```text
used_car_reservation.complete_sale
```

Allowed actor roles:

```text
Used Car Sales
Used Car Manager
Used Car Owner
System Manager
```

Allowed document writes:

```text
Used Car Vehicle status: 保留中 → 已售出
Used Car Vehicle completion summary fields
Used Car Reservation status: 有效 → 已完成
Used Car Reservation completed_at
Used Car Reservation completed_by
Used Car Reservation completion_note
```

Required precondition:

```text
preflight_delivery_for_active_reservation must pass.
```

Do not create Sales Invoice, Journal Entry, Delivery Note, Payment Entry, or Stock Entry in this action.

## Accounting-Side Controlled Writes Are Later Scope

The following actions are not part of P1-F-3-A:

```text
used_car_voucher_draft.confirm
used_car_voucher_draft.reject
used_car_voucher_draft.void
used_car_sales_invoice_draft.create
used_car_sales_invoice.submit
used_car_advance_settlement.create_draft
used_car_advance_settlement.submit
used_car_accounting_link.repair
used_car_tax_metadata.write
```

These need separate review because they may create or mutate formal accounting, stock, or tax-controlled records.

## Interaction With Existing DocPerm

Controlled write bypass does not mean the user can open the raw DocType form and edit hidden or sensitive fields.

Expected behavior:

```text
Raw form access remains limited by DocPerm.
Service workflow can write a narrow set of fields after action gate and validation pass.
```

This preserves both usability and security:

```text
Sales can complete sales workflow.
Sales cannot browse or edit accounting fields directly.
Accounting can review accounting drafts.
Owner sees business status but does not automatically receive accounting authority.
```

## Audit Direction

If audit logging is added later, controlled write workflows should record:

```text
action key
current user
source document
created / updated document
previous status
new status
amount fields where relevant
reason / note when provided
```

Audit logging is not required in P1-F-3-A unless already available in the local app.

## Manual QA Direction

For P1-F-3-A implementation, manual QA should include at least:

```text
1. Used Car Sales can create reservation from an eligible listed vehicle through the service workflow.
2. Used Car Sales still cannot directly edit high-level sensitive fields through raw form permissions.
3. Used Car Sales can create final payment through the service workflow.
4. Used Car Sales can cancel active reservation through the service workflow.
5. Used Car Sales can complete sale only after accounting preflight passes.
6. Used Car Sales cannot confirm voucher draft.
7. Used Car Accounting can confirm voucher draft through existing accounting action gate.
8. Reservation workflow still does not create Payment Entry, Sales Invoice, Delivery Note, or extra Stock Entry.
9. Voucher draft auto-generation still works after controlled write adoption.
10. Duplicate reservation and duplicate final payment remain blocked.
```

## Final Decision

P1-F-3 should proceed conservatively.

The correct first implementation is not broad permission bypass. It is:

```text
Action-gated, service-owned, workflow-specific, field-constrained controlled writes for the sales reservation flow only.
```

Everything involving formal accounting, Sales Invoice submission, Stock Entry, tax review, purchase price correction, or accounting-link repair must remain outside the first controlled write scope.

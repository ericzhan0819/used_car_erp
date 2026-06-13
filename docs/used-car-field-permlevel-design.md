# Used Car Field Permlevel Design Phase P1-C

## Purpose

This document defines the target field-level permission model for the used-car business layer before opening custom DocType permissions to non-System Manager roles.

This is a design-only phase. It does not change DocType JSON, does not change permission rows, and does not implement server-side action gates.

The reason for this phase is that the current permission inventory found sensitive fields at `permlevel 0`. If broad read/write permissions are granted before field levels are designed, procurement cost, floor price, gross margin, Sales Invoice links, and Journal Entry links may become visible or editable to roles that should not see them.

## Design Principle

Use Frappe's built-in `permlevel` and DocType permission model as the first field-level boundary.

The project should separate:

```text
ordinary business fields
pricing / cost / margin fields
accounting document links
review / correction / exceptional control fields
```

Client-side hiding can improve UX, but it must not be the only security boundary for sensitive values or irreversible business actions.

## Target Permlevel Model

### Permlevel 0 — General Operational Fields

Purpose:

```text
Fields required for ordinary daily vehicle operation.
```

Typical visibility:

- Used Car Owner
- Used Car Manager
- Used Car Procurement
- Used Car Sales
- Used Car Preparation
- Used Car Accounting
- Used Car Viewer, read-only if later granted

Allowed examples:

```text
vehicle identity
basic vehicle specification
status labels
stock number
license / VIN style identifiers where appropriate
preparation notes
non-sensitive workflow notes
public asking price if business policy allows
```

Rule:

```text
Only fields safe for ordinary operational users should remain at permlevel 0.
```

### Permlevel 1 — Pricing / Cost / Margin Fields

Purpose:

```text
Business-sensitive pricing, procurement cost, cost summary, and margin visibility.
```

Typical visibility:

- Used Car Owner
- Used Car Manager
- Used Car Accounting, read-only where needed
- Used Car Accounting Manager
- Optional: Used Car Procurement for purchase-related fields only
- Optional: Used Car Sales for sold price only, not floor price / margin, depending on policy

Field categories:

```text
purchase price
floor price
total cost
gross margin
cost amount
profit / VAT estimate values
```

Rule:

```text
Sales and preparation users should not automatically see cost, floor price, or gross margin.
```

### Permlevel 2 — Accounting Document Links / Accounting Amounts

Purpose:

```text
Links and values related to formal accounting documents, voucher drafts, Journal Entries, Sales Invoice, review metadata, and accounting workflow state.
```

Typical visibility:

- Used Car Owner, read-only where appropriate
- Used Car Manager, policy-based read-only
- Used Car Accounting
- Used Car Accounting Manager
- Used Car Auditor, read-only if later granted

Field categories:

```text
Sales Invoice link
Journal Entry link
voucher draft link
voucher draft amounts
reviewed_by / reviewed_at
formal_delivery_status
formal_delivery_posting_date
formal_delivery_completed_at
formal_delivery_completed_by
```

Rule:

```text
Accounting links should not be visible by default to sales, procurement, preparation, or viewer roles.
```

### Permlevel 3 — Tax Review / Exception / Repair Control Fields

Purpose:

```text
Tax-sensitive review fields and exceptional system repair metadata.
```

Typical visibility:

- Used Car Owner, read-only or approval policy
- Used Car Accounting Manager
- Used Car Accounting, only if needed
- Used Car Auditor, read-only if later granted

Field categories:

```text
tax review status
tax review note
tax reviewer
tax review timestamp
exception repair state
manual recovery notes
future correction / reversal metadata
```

Rule:

```text
Tax review and repair fields should be treated as restricted accounting-control fields, not ordinary operational fields.
```

## Target Field Classification

### Used Car Vehicle

| Fieldname | Current Meaning | Target Permlevel | Default Access Policy | Notes |
| --- | --- | --- | --- | --- |
| `stock_no` | Vehicle stock number | 0 | Operational read | Safe operational identifier. |
| `status` | Vehicle business status | 0 | Operational read/write through controlled flows | Status mutation still needs server-side action gates for important transitions. |
| `brand` / `model` / basic spec fields | Vehicle information | 0 | Operational read/write | Keep ordinary vehicle data accessible. |
| `purchase_price` | Purchase price / buying price | 1 | Procurement write, Manager/Owner/Accounting read | Do not expose broadly to sales/viewer. |
| `asking_price` | Public asking/listing price | 0 or 1 | Sales can usually read/write if policy allows | If asking price is used publicly, permlevel 0 is acceptable. If internal negotiation-sensitive, use level 1. |
| `floor_price` | Minimum acceptable sales price | 1 | Owner/Manager only by default | Sales access should be explicit business decision, not default. |
| `customer` | Customer for sale | 0 or 1 | Sales write before accounting lock; Accounting read | Consider privacy policy before leaving at level 0. |
| `sold_price` | Final sold price | 1 | Sales write before accounting lock; Manager/Accounting read | Sensitive sale amount; do not leave broadly visible if viewer roles are introduced. |
| `total_cost` | Cost summary | 1 | Manager/Owner/Accounting read | Not for ordinary sales/prep users. |
| `gross_margin` | Management margin | 1 | Owner/Manager/Accounting read | Must not be visible to ordinary sales/viewer by default. |
| `deposit_money_flow` | Deposit money flow link | 2 | Accounting/Manager read | Operational users can see business status via summary, not technical link. |
| `deposit_voucher_draft` | Deposit voucher draft link | 2 | Accounting read | Hide from non-accounting roles. |
| `deposit_journal_entry` | Deposit Journal Entry link | 2 | Accounting read | Hide from non-accounting roles. |
| `final_money_flow` | Final payment money flow link | 2 | Accounting/Manager read | Hide technical link from ordinary users. |
| `final_voucher_draft` | Final payment voucher draft link | 2 | Accounting read | Hide from non-accounting roles. |
| `final_journal_entry` | Final payment Journal Entry link | 2 | Accounting read | Hide from non-accounting roles. |
| `sales_invoice` | Sales Invoice link | 2 | Accounting read; Manager policy read | Hide from ordinary sales/prep/viewer unless policy allows. |
| `advance_settlement_journal_entry` | Advance settlement Journal Entry link | 2 | Accounting read | Accounting-only by default. |
| `formal_delivery_status` | Accounting document status | 2 | Accounting/Manager read | Not physical delivery status. |
| `formal_delivery_posting_date` | Accounting document processing date | 2 | Accounting read | Accounting control data. |
| `formal_delivery_completed_at` | Accounting completion timestamp | 2 | Accounting read | Accounting control data. |
| `formal_delivery_completed_by` | Accounting completion user | 2 | Accounting read | Accounting control data. |
| tax metadata fields | Tax basis/review data | 3 | Accounting Manager / Accounting read-write by policy | Use level 3 when implemented or confirmed. |

### Used Car Money Flow

| Fieldname | Current Meaning | Target Permlevel | Default Access Policy | Notes |
| --- | --- | --- | --- | --- |
| `money_flow_no` | Money flow identifier | 0 | Operational read | Safe identifier. |
| `vehicle` | Vehicle link | 0 | Operational read | Safe relationship. |
| `reservation` | Reservation link | 0 or 2 | Sales/Accounting read by policy | Technical link may be level 2 if too noisy. |
| `customer` | Customer link | 1 | Sales/Accounting read | Privacy-sensitive if viewer roles are introduced. |
| `amount` | Payment amount | 1 | Sales/Accounting read; Accounting write/confirm | Money amount is sensitive. |
| `money_flow_type` / `payment_method` | Money flow fact | 0 or 1 | Sales/Accounting read | Use level 1 if it exposes sensitive payment detail. |
| `voucher_draft` | Voucher draft link | 2 | Accounting read | Technical accounting link. |
| `journal_entry` | Journal Entry link | 2 | Accounting read | Technical accounting link. |

### Used Car Voucher Draft

| Fieldname | Current Meaning | Target Permlevel | Default Access Policy | Notes |
| --- | --- | --- | --- | --- |
| `voucher_draft_no` | Voucher draft identifier | 2 | Accounting read | Voucher draft is accounting document. |
| `vehicle` | Vehicle link | 2 | Accounting read | Could be visible via business summary elsewhere. |
| `customer` | Customer link | 2 | Accounting read | Accounting context. |
| `total_debit` | Debit total | 2 | Accounting read | Accounting-sensitive. |
| `total_credit` | Credit total | 2 | Accounting read | Accounting-sensitive. |
| `difference` | Debit/credit difference | 2 | Accounting read | Accounting-sensitive. |
| `journal_entry` | Journal Entry link | 2 | Accounting read | Accounting-sensitive. |
| `reviewed_by` | Reviewer | 2 | Accounting read | Audit/control metadata. |
| `reviewed_at` | Review time | 2 | Accounting read | Audit/control metadata. |
| correction/reversal future fields | Exceptional accounting controls | 3 | Accounting Manager | Future control fields. |

### Used Car Voucher Draft Line

| Fieldname | Current Meaning | Target Permlevel | Default Access Policy | Notes |
| --- | --- | --- | --- | --- |
| `account` | Accounting account | 2 | Accounting read/write before confirmed | Child table follows parent access. |
| `debit` | Debit amount | 2 | Accounting read/write before confirmed | Child table follows parent access. |
| `credit` | Credit amount | 2 | Accounting read/write before confirmed | Child table follows parent access. |
| `remarks` | Accounting line note | 2 | Accounting read/write | Child table follows parent access. |

### Used Car Reservation

| Fieldname | Current Meaning | Target Permlevel | Default Access Policy | Notes |
| --- | --- | --- | --- | --- |
| `reservation_no` | Reservation identifier | 0 | Sales/Manager read | Safe operational identifier. |
| `vehicle` | Vehicle link | 0 | Sales/Manager read | Operational relationship. |
| `customer` | ERPNext customer | 1 | Sales/Accounting read | Customer privacy. |
| `deposit_amount` | Deposit amount | 1 | Sales/Accounting read/write by phase | Money amount. |
| `final_payment_amount` | Final payment amount | 1 | Sales/Accounting read by phase | Money amount. |
| `deposit_money_flow` / `final_money_flow` | Money flow links | 2 | Accounting read | Technical links. |
| `voucher_draft` / `final_voucher_draft` | Voucher draft links | 2 | Accounting read | Accounting links. |
| `journal_entry` / `final_journal_entry` | Journal Entry links | 2 | Accounting read | Accounting links. |
| completion/confirmation metadata | Completion control | 2 or 3 | Accounting/Manager read | Use level 3 if exceptional control. |

### Used Car Vehicle Cost

| Fieldname | Current Meaning | Target Permlevel | Default Access Policy | Notes |
| --- | --- | --- | --- | --- |
| `vehicle` | Vehicle link | 0 | Preparation/Manager read | Operational relationship. |
| `cost_type` | Cost category | 0 or 1 | Preparation/Accounting read/write by policy | If category reveals sensitive source, level 1. |
| `amount` | Cost amount | 1 | Manager/Accounting read; Preparation create by policy | Sensitive cost amount. |
| `description` / notes | Cost note | 0 or 1 | Preparation/Accounting read/write | Use level 1 if notes may expose supplier/cost strategy. |
| accounting links future fields | Linked voucher/JE | 2 | Accounting read | If added later. |

## Role Access Direction By Permlevel

This is a design target, not yet implemented.

| Role | Level 0 | Level 1 | Level 2 | Level 3 |
| --- | --- | --- | --- | --- |
| Used Car Owner | Read/Write policy | Read/Write policy | Read policy | Read/Approve policy |
| Used Car Manager | Read/Write policy | Read/Write policy | Read policy | Limited read policy |
| Used Car Procurement | Read/Write procurement fields | Purchase-related only | No by default | No |
| Used Car Sales | Read/Write sales fields | Sold price policy only | No by default | No |
| Used Car Preparation | Read/Write preparation fields | Limited cost create policy | No by default | No |
| Used Car Accounting | Read level 0 context | Read financial values | Read/Write accounting docs | Limited tax/review policy |
| Used Car Accounting Manager | Read level 0 context | Read financial values | Read/Write accounting docs | Read/Write/Approve |
| Used Car Viewer | Read only | No by default | No | No |
| Used Car Auditor | Read policy | Read policy | Read policy | Read policy |

## Implementation Strategy

## Phase P1-D-A Application Boundary

This phase applies target permlevels to sensitive fields.

It only preserves System Manager access to higher permlevels.

It does not grant Used Car business roles any DocType permissions yet.

### Phase P1-C — Documentation Only

Current phase. Define field levels before opening permissions.

No runtime change.

### Phase P1-D — Apply Permlevel To DocType JSON

Future phase.

Apply field `permlevel` in custom DocType JSON only after reviewing this document.

Important:

```text
Changing field permlevel without matching permission rows may hide fields from users unexpectedly.
```

Therefore P1-D should include tests/manual verification.

### Phase P1-E — Add DocType Permission Rows

Future phase.

After sensitive fields move out of level 0, add role-specific DocType permission rows for level 0 and selected higher levels.

Do not open write permissions broadly before action gates are in place.

### Phase P1-F — Server-side Action Gates

Future phase.

Any action that changes money, accounting, stock, sale completion, formal document links, or locked state must receive explicit server-side permission checks.

Examples:

```text
complete intake / stock-in
create final payment
complete sale
create Sales Invoice draft
submit Sales Invoice / stock-out
create voucher draft
confirm voucher draft
submit settlement Journal Entry
repair Sales Invoice link
recalculate cost / profit summaries
```

## Non-goals

This phase does not:

- change DocType JSON;
- change existing permission rows;
- assign users;
- hide fields in JavaScript;
- implement role-based server gates;
- create new delivery/payment fields;
- modify Sales Invoice, Journal Entry, Stock, Payment Entry, or Delivery Note runtime.

## Acceptance Criteria For Future P1-D

Before applying permlevel changes:

```text
1. Every target field has a documented level.
2. Every sensitive money/profit/accounting link leaves permlevel 0 unless explicitly justified.
3. Role Permission Manager plan exists for levels 1/2/3.
4. Manual QA accounts exist or can be created for at least Manager, Sales, Procurement, Accounting, Viewer.
5. No critical action relies only on client-side button hiding.
```

## Final Decision

Do not open broad Used Car Vehicle read/write permissions until field-level sensitivity is separated.

The minimum safe direction is:

```text
Level 0 = ordinary operational data
Level 1 = price / cost / margin data
Level 2 = accounting document links and accounting values
Level 3 = tax review / exception / repair control data
```

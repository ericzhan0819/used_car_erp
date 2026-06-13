# Used Car Role / Permission Boundary Spec

## Purpose

This document defines the role and permission boundary for the used-car business layer before implementing permission logic.

The project should not build a separate user/permission system from scratch. It should primarily use Frappe / ERPNext built-in permission features, then add custom server-side checks only where the business action is more specific than basic DocType read/write/submit permissions.

## Built-in Frappe / ERPNext Capabilities to Reuse

Frappe already provides a user authentication and permission system. The project should reuse these features before introducing custom permission tables.

Relevant built-in concepts:

```text
User
Role
DocType Permissions
Permission Level
Role Permission Manager
User Permissions
Restricting Views and Forms
Allow Modules
Role Permission for Page and Report
Workflow / Submit / Cancel permissions
```

Recommended usage:

| Built-in Feature | Use in this project |
| --- | --- |
| User | Actual login account for each employee. |
| Role | Business role such as Used Car Sales, Used Car Accounting, Used Car Procurement. |
| DocType Permissions | Base read/create/write/submit/cancel/report/export rules for custom DocTypes. |
| Permission Level | Hide or protect sensitive fields such as floor price, gross margin, accounting links. |
| Role Permission Manager | Admin configuration and verification tool for DocType permission rows. |
| User Permissions | Optional branch/shop/person-level document filtering. |
| Allow Modules | Control whether a user sees Used Car Management, Accounting Operations, etc. |
| Role Permission for Page and Report | Control future dashboard/report visibility. |
| Workflow | Future candidate for state-based approval flows if custom status handling becomes too complex. |

## Design Principle

Use three layers:

```text
1. Built-in DocType permissions for broad access.
2. Field-level permission / read-only UI for sensitive information.
3. Server-side custom action checks for irreversible or accounting-sensitive actions.
```

Do not rely on client-side JavaScript alone for sensitive actions. JS may hide buttons, but every action that changes money, accounting documents, stock, or status must also be checked server-side.

## Proposed Roles

### System / Owner Roles

#### Used Car Owner

Business owner / company decision maker.

Can:

- view all used-car documents;
- view prices, floor price, gross margin, and profit summaries;
- view accounting document links;
- approve high-level business exceptions if implemented later;
- access management reports.

Should not automatically replace accounting approval. If an action creates or submits accounting documents, it should still follow accounting role rules unless intentionally designed otherwise.

#### Used Car Manager

Operational manager.

Can:

- view all vehicles and transaction status;
- edit non-accounting business data before accounting lock;
- view purchase price, asking price, floor price, sold price;
- view costs and gross margin;
- supervise procurement, sales, and preparation workflow;
- trigger non-accounting operational actions if allowed later.

Should not directly submit formal accounting documents unless also assigned accounting roles.

### Operational Roles

#### Used Car Procurement

Handles vehicle acquisition and initial record creation.

Can:

- create vehicle records;
- edit basic vehicle data before accounting lock;
- enter purchase source and purchase date;
- enter purchase price;
- enter asking price and floor price only if business policy allows;
- upload or enter purchase-related evidence when implemented;
- view procurement-related cost facts.

Should not:

- enter final sold price after sales workflow starts unless also sales/manager;
- submit Sales Invoice;
- submit Journal Entry;
- confirm accounting entries;
- view accounting links unless explicitly allowed.

#### Used Car Sales

Handles customer negotiation, reservation, sale facts, and customer-facing workflow.

Can:

- view available vehicles;
- create or update customer-facing sale facts;
- create reservations if implemented;
- enter customer, sold price, sold date, expected delivery date;
- record sales notes;
- request payment collection records or create draft payment facts depending on future design.

Should not:

- view floor price unless policy allows;
- view gross margin unless policy allows;
- submit accounting documents;
- confirm prepayment settlement;
- directly edit purchase price;
- directly edit accounting lock fields.

#### Used Car Preparation / Operations

Handles reconditioning, detailing, inspection, logistics, and physical vehicle condition.

Can:

- view assigned vehicles;
- update preparation status and notes;
- create preparation expense facts or cost records if policy allows;
- view non-sensitive vehicle data.

Should not:

- view floor price or gross margin;
- edit purchase price or sold price;
- submit accounting documents;
- confirm sales invoice / stock-out unless explicitly designed as an operations action.

### Accounting Roles

#### Used Car Accounting

Handles accounting review, voucher draft confirmation, sales/accounting document checks, and financial links.

Can:

- view vehicles relevant to accounting;
- view money flow records;
- view voucher drafts;
- review and confirm voucher drafts;
- view Sales Invoice and Journal Entry links;
- review tax metadata;
- confirm or submit accounting-side actions where permitted;
- view receivable/payment status.

Should not automatically be able to modify business facts such as customer/sold price after formal accounting lock, except through a controlled correction or reversal workflow.

#### Used Car Accounting Manager

Higher-level accounting authority.

Can:

- do everything Used Car Accounting can do;
- approve reversal/correction flows when implemented;
- resolve accounting mapping/account configuration issues;
- manage accounting-related reports;
- approve exceptional document relinking or repair actions.

### Read-only Roles

#### Used Car Viewer

Can:

- view basic vehicle data;
- view non-sensitive status summaries.

Should not:

- edit vehicle data;
- see floor price;
- see gross margin;
- see accounting links;
- create money flow;
- submit or confirm any accounting/stock action.

#### Used Car Auditor / External Accountant Viewer

Optional future role for accountant review or audit support.

Can:

- view accounting documents and supporting records;
- view tax metadata;
- export reports if allowed.

Should not:

- modify operational records;
- perform sale workflow actions;
- perform stock-out actions;
- create new business records unless explicitly allowed.

## Permission Matrix Draft

Legend:

```text
R = Read
C = Create
W = Write
S = Submit / Confirm
V = View sensitive value/link
- = No access by default
```

| Area / Action | Owner | Manager | Procurement | Sales | Prep/Ops | Accounting | Accounting Manager | Viewer |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Vehicle basic data | R/W | R/W | C/W | R | R/W limited | R | R | R |
| Purchase price | V/W | V/W | V/W | - | - | V | V | - |
| Asking price | V/W | V/W | V/W policy | V | - | V | V | R policy |
| Floor price | V/W | V/W | V/W policy | V policy | - | V policy | V | - |
| Sold price | V | V/W before lock | - | V/W before lock | - | V | V | R policy |
| Customer / sale facts | R/W | R/W | R policy | C/W before lock | - | R | R | R policy |
| Preparation status | R | R/W | R | R | C/W | R | R | R |
| Cost / expense facts | V | V/W | R policy | - | C/W policy | V | V/W | - |
| Gross margin | V | V | - | - or policy | - | V | V | - |
| Money flow records | R | R | - or C policy | C policy | C policy | C/W/S | C/W/S | - |
| Voucher drafts | R | R | - | - | - | C/W/S | C/W/S | - |
| Sales Invoice link | V | V policy | - | V policy | - | V | V | - |
| Journal Entry link | V | V policy | - | - | - | V | V | - |
| Confirm sales invoice / stock-out | S policy | S policy | - | - or request only | - or request only | S policy | S | - |
| Confirm prepayment settlement | - or V | - or V | - | - | - | S | S | - |
| Reversal / correction | Approve policy | Request | Request | Request | Request | Request / process | Approve / process | - |

This matrix is a draft. Do not implement all permissions at once. Use it to guide the next small, testable implementation phase.

## Sensitive Fields

Fields that likely need restricted visibility:

```text
purchase_price
floor_price
total_cost
gross_margin
sales_invoice
advance_settlement_journal_entry
deposit_journal_entry
final_journal_entry
formal_delivery_status
formal_delivery_posting_date
formal_delivery_completed_at
formal_delivery_completed_by
```

Potentially sensitive by business policy:

```text
asking_price
sold_price
customer
purchase_source_type
purchase_document_no
tax_review_status
tax_review_note
```

Recommended implementation approach:

- Use Permission Level for stable field-level restrictions where possible.
- Use role-based JS display only for UX, not for security.
- Use server-side checks for any action that mutates sensitive state.

## Action Permission Boundary

The following actions must not rely only on button visibility:

```text
create vehicle
complete intake
start preparation
create cost / expense record
create reservation
create money flow
create voucher draft
confirm voucher draft
edit sold price after Sales Invoice draft exists
submit Sales Invoice / stock-out
create advance settlement Journal Entry draft
submit advance settlement Journal Entry
repair Sales Invoice draft link
future reversal / cancellation / correction
```

Every one of these should have server-side role checks when implemented.

## Built-in First, Custom Second

Recommended implementation order:

### Phase P0 — Documentation Only

Current phase. Define roles and permission boundaries. No runtime change.

### Phase P1 — Built-in Role and DocType Permission Foundation

Create custom roles and assign basic DocType permissions for custom DocTypes:

```text
Used Car Owner
Used Car Manager
Used Car Procurement
Used Car Sales
Used Car Preparation
Used Car Accounting
Used Car Accounting Manager
Used Car Viewer
```

Use DocType permissions and Role Permission Manager as the first enforcement layer.

### Phase P2 — Field Sensitivity

Apply Permission Level where practical:

```text
purchase price / floor price
gross margin
accounting links
sensitive tax fields
```

### Phase P3 — Server-side Action Gates

Add explicit server-side permission helpers for business actions that cannot be described by simple DocType permissions.

Examples:

```text
can_confirm_sales_invoice_stock_out
can_submit_advance_settlement
can_repair_sales_invoice_draft_link
can_edit_sale_facts_before_accounting_lock
can_view_profit_fields
```

### Phase P4 — User Permissions / Branch Scoping

If the business later has multiple shops or branches, use User Permissions to restrict records by branch/shop/company where possible.

Do not hard-code branch filtering in JavaScript.

### Phase P5 — Workflow / Approval Review

Evaluate whether Frappe Workflow should handle future approval flows:

```text
purchase approval
sale approval
delivery approval
accounting approval
reversal approval
```

Use Workflow only if it makes the business process clearer. Do not force every small status into Workflow.

## Explicit Non-goals

Do not do these in the first implementation:

- Do not build a custom user table.
- Do not build a custom password/login system.
- Do not duplicate Frappe Role Permission Manager.
- Do not make JavaScript button hiding the only security boundary.
- Do not add complicated branch/person scoping before the actual organization structure is known.
- Do not change Phase 3B / 3C / 3D accounting runtime just to add roles.
- Do not implement all roles at once if a smaller role foundation is enough.

## Immediate Recommendation

The next technical step should not be a full permission system rewrite.

Recommended next step:

```text
Phase P1-A: Create role boundary foundation and document target DocType permissions without changing runtime behavior.
```

Then implement the smallest useful permissions for:

```text
Used Car Vehicle
Used Car Money Flow
Used Car Voucher Draft
```

Start with read/create/write separation. Add submit/accounting action gates only after the role list is stable.

## Final Decision

The project should use Frappe / ERPNext built-in User, Role, DocType Permission, Permission Level, Role Permission Manager, User Permission, and module visibility mechanisms as the base.

Custom permission logic should only be added for business actions that are more specific than basic DocType permissions.

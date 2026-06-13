# Used Car Server-side Action Gate Design Phase P1-F

## 目的

- 建立 action-based server-side permission boundary。
- 避免把 DocType write 當成業務動作權限。
- 避免只靠前端按鈕隱藏。
- 不自建登入系統，不取代 Frappe Role / DocPerm。
- 在 Frappe Role + DocPerm 之外，對高風險 business action 加明確 gate。

## 核心規則

- DocPerm = 文件 baseline 可見性 / 低風險操作。
- Action Gate = 業務動作授權。
- 只要會改 money/accounting/stock/status/locked state，都要走 action gate。
- System Manager 永遠可通過 gate。
- Owner 不是萬能會計角色；Owner 若要做會計動作，應另外分配 Used Car Accounting 或 Used Car Accounting Manager。

## Phase Boundary

P1-F-0/P1-F-1 只建立 server-side action gate 設計與共用 permission helper skeleton。

本階段不大量修改既有 runtime service，不把所有 whitelisted method 立即接上 gate，不新增 DocType，不新增 patch，不修改 DocType JSON，不修改 ERPNext / Frappe core。

P1-F-2 才開始逐步把 helper 接入高風險 whitelisted methods，例如 create reservation、money flow、voucher confirm/reject/void、Sales Invoice draft、advance settlement 與 accounting-link repair。

## Action Map Initial Version

```python
ACTION_ROLE_MAP = {
    "used_car_vehicle.intake.complete": {
        "Used Car Procurement",
        "Used Car Manager",
        "Used Car Owner",
    },
    "used_car_vehicle.purchase_price.write": {
        "Used Car Procurement",
        "Used Car Manager",
        "Used Car Owner",
    },
    "used_car_vehicle.status.transition": {
        "Used Car Manager",
        "Used Car Owner",
    },

    "used_car_reservation.create": {
        "Used Car Sales",
        "Used Car Manager",
        "Used Car Owner",
    },
    "used_car_reservation.cancel": {
        "Used Car Sales",
        "Used Car Manager",
        "Used Car Owner",
    },
    "used_car_reservation.complete_sale": {
        "Used Car Sales",
        "Used Car Manager",
        "Used Car Owner",
    },

    "used_car_money_flow.deposit.create": {
        "Used Car Sales",
        "Used Car Manager",
        "Used Car Owner",
    },
    "used_car_money_flow.final_payment.create": {
        "Used Car Sales",
        "Used Car Manager",
        "Used Car Owner",
    },

    "used_car_vehicle_cost.create_with_amount": {
        "Used Car Preparation",
        "Used Car Accounting Manager",
        "Used Car Manager",
        "Used Car Owner",
    },
    "used_car_vehicle_cost.amount.write": {
        "Used Car Accounting Manager",
        "Used Car Manager",
        "Used Car Owner",
    },
    "used_car_vehicle_cost.summary.recalculate": {
        "Used Car Accounting",
        "Used Car Accounting Manager",
        "Used Car Manager",
        "Used Car Owner",
    },

    "used_car_voucher_draft.create": {
        "Used Car Accounting",
        "Used Car Accounting Manager",
    },
    "used_car_voucher_draft.confirm": {
        "Used Car Accounting",
        "Used Car Accounting Manager",
    },
    "used_car_voucher_draft.reject": {
        "Used Car Accounting",
        "Used Car Accounting Manager",
    },
    "used_car_voucher_draft.void": {
        "Used Car Accounting",
        "Used Car Accounting Manager",
    },

    "used_car_sales_invoice_draft.create": {
        "Used Car Accounting",
        "Used Car Accounting Manager",
    },
    "used_car_sales_invoice.submit": {
        "Used Car Accounting",
        "Used Car Accounting Manager",
    },

    "used_car_advance_settlement.create_draft": {
        "Used Car Accounting",
        "Used Car Accounting Manager",
    },
    "used_car_advance_settlement.submit": {
        "Used Car Accounting",
        "Used Car Accounting Manager",
    },

    "used_car_tax_metadata.write": {
        "Used Car Accounting Manager",
    },
    "used_car_accounting_link.repair": {
        "Used Car Accounting Manager",
    },
}
```

## Helper Contract

The shared helper lives at:

```text
used_car_erp/used_car_erp/services/used_car_action_permission_service.py
```

Required behavior:

- Known action + allowed business role passes.
- Known action + System Manager passes.
- Guest, empty user, empty roles, or unknown action cannot pass.
- Unknown action must never silently allow access.
- Runtime helper may use `frappe.session.user` only as the default fallback when no explicit user is provided.
- Pure role-set helper stays lightweight for tests and future service adoption.

## Runtime Adoption Plan

P1-F-2 should connect this helper to high-risk whitelisted service methods in small batches.

## P1-F-2 Adoption Status

P1-F-2 已將 action gate 接到第一批高風險 service methods：

- reservation create / cancel / complete sale
- final payment money flow
- deposit/final money flow creation
- voucher confirm / reject / void

本階段只做 gate adoption，不做 controlled write bypass。

部分業務角色仍可能被既有 DocPerm / check_permission 擋住，這留到 P1-F-3 處理。

create_deposit_voucher_draft / create_final_payment_voucher_draft 暫不接 used_car_voucher_draft.create，避免打斷 reservation → money flow → voucher draft 的現有自動流程。

Priority candidates:

```text
used_car_reservation.create
used_car_reservation.cancel
used_car_reservation.complete_sale
used_car_money_flow.deposit.create
used_car_money_flow.final_payment.create
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

Each service must still keep its business-state validation. Action gate only answers whether the user may attempt the action; it does not replace document validation, accounting balance checks, stock consistency checks, idempotency checks, or linked-document integrity checks.

## Non-goals

This phase does not:

- replace Frappe login, Role, DocPerm, Permission Level, or Role Permission Manager;
- create a custom user table or custom permission table;
- grant new roles or assign users;
- alter DocType permission rows;
- alter sensitive field permlevels;
- change frontend button behavior;
- change existing runtime service behavior.

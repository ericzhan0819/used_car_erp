# Vehicle Delivery / Payment / Accounting Status Boundary Spec

## Purpose

This document fixes the business boundary before continuing vehicle workflow implementation.

The current runtime uses `formal_delivery_status`, but the name is misleading. In the used-car business workflow, physical delivery, payment collection, and accounting document processing are separate facts. They must not be treated as the same state.

This spec is intentionally non-runtime. It defines the language and future direction so later UI and workflow changes do not keep mixing delivery, payment, and accounting.

## Core Rule

```text
交車 / 離場 ≠ 收清款項 ≠ 會計完成
```

These three states can progress at different times:

- A vehicle may leave the shop before final payment is received.
- A loan may be pending after the customer takes the car.
- A Sales Invoice may be submitted while Accounts Receivable is still outstanding.
- Accounting may need to confirm or adjust prepayment settlement after physical delivery.

## Terms

### Physical Delivery Status

Physical delivery means the car is actually handed over to the customer or has left the shop.

It does not mean:

- final payment has been received;
- the loan has been funded;
- Sales Invoice has been submitted;
- Journal Entry has been submitted;
- accounting has finished.

Recommended future field:

```text
delivery_status
```

Recommended future UI label:

```text
交車 / 離場狀態
```

Recommended future states:

```text
未交車
準備交車
已交車 / 已離場
交車取消
```

### Payment Status

Payment status means how much money has actually been collected or remains outstanding.

It does not mean the vehicle is or is not physically delivered.

Recommended future field:

```text
payment_status
```

Recommended future UI label:

```text
收款狀態
```

Recommended future states:

```text
未收款
已收訂金
部分收款
尾款待收
貸款待撥
已收清
退款 / 退訂
```

Example valid combinations:

| Delivery Status | Payment Status | Meaning |
| --- | --- | --- |
| 未交車 | 已收訂金 | Customer reserved the car; car still in shop. |
| 準備交車 | 貸款待撥 | Delivery is being prepared; loan funding not received yet. |
| 已交車 / 已離場 | 尾款待收 | Car has left the shop but money is not fully collected. |
| 已交車 / 已離場 | 已收清 | Car has left and payment is fully collected. |

### Accounting Document Status

Accounting document status means how formal ERPNext accounting documents have progressed.

The existing field:

```text
formal_delivery_status
```

should be understood as:

```text
formal accounting / sales document status
```

It should not be interpreted as the physical delivery status.

Recommended current UI label:

```text
會計文件狀態
```

Possible current states:

```text
未處理
銷售發票草稿
銷售發票已提交
預收款沖轉草稿
預收款沖轉已提交
已完成
```

Important rule:

```text
Sales Invoice 已提交 ≠ 已收清
```

Sales Invoice submission records a formal sale and may create or update receivables, but it does not prove cash has been collected.

## Current Runtime Boundary

Current `formal_delivery_status` runtime should remain unchanged until a dedicated migration/refactor is planned.

Current Phase 3B / 3C / 3D behavior should be interpreted as formal sales/accounting document workflow:

- Phase 3B submits the existing Sales Invoice draft and uses ERPNext `update_stock` to perform formal stock-out.
- Phase 3C creates an advance/prepayment settlement Journal Entry draft.
- Phase 3D submits the existing advance/prepayment settlement Journal Entry.

These phases do not automatically mean:

- the car physically left the shop;
- payment was fully collected;
- loan funding was received;
- all operational delivery steps were completed.

## UI Language Correction

Avoid using `正式交車入帳狀態` as the main label for `formal_delivery_status`.

Prefer:

```text
會計文件狀態
```

or, if more explicit:

```text
正式銷售文件狀態
```

Button labels should not imply payment completion unless the action actually confirms payment.

### Better Button Language

Current technical language:

```text
提交 Sales Invoice 並出車
提交 Sales Invoice 並正式出庫
```

Safer business language:

```text
確認出庫並建立應收
```

or:

```text
確認銷售發票並出庫
```

Do not use:

```text
確認收清
完成收款
交車並收清
```

unless the action actually verifies and records full payment.

## Workflow Principle

The correct high-level workflow is:

```text
售車成交
→ 記錄訂金 / 尾款 / 貸款金流
→ 準備交車
→ 車輛實際交車 / 離場
→ 銷售文件與出庫處理
→ 應收帳款追蹤
→ 後續收款 / 貸款撥款
→ 會計確認沖帳
```

The actual order may vary by case. The system should support this separation rather than forcing one linear meaning into one field.

## Future Data Model Direction

Future implementation should consider adding separate fields to `Used Car Vehicle` or a related sales/delivery document:

```text
delivery_status
payment_status
```

These should be independent from:

```text
formal_delivery_status
```

Recommended semantic mapping:

| Concern | Current / Future Field | Owner | Meaning |
| --- | --- | --- | --- |
| Physical handover | `delivery_status` | Sales / operations | Whether the car has left the shop. |
| Payment collection | `payment_status` | Sales / accounting | Whether money is unpaid, partial, loan pending, or fully collected. |
| Accounting documents | `formal_delivery_status` | Accounting / system | ERPNext formal documents and settlement status. |

## Current Scope

Do now:

- Use this document as the boundary for future UI and workflow changes.
- Adjust UI wording so `formal_delivery_status` is not confused with physical delivery.
- Keep the current runtime stable.

Do not do now:

- Do not implement Phase 3E completion marker.
- Do not rename database fields immediately.
- Do not add role-based permission logic until the personnel/role system is designed.
- Do not assume vehicle delivery means payment is fully collected.
- Do not assume Sales Invoice submission means payment is fully collected.

## Acceptance Criteria for Future Changes

Any future vehicle workflow patch must satisfy:

```text
1. Physical delivery, payment collection, and accounting documents are described separately.
2. Button labels do not imply payment collection unless payment is actually verified.
3. Sales Invoice language is hidden behind business wording where possible.
4. Accounting/system links remain secondary to business status.
5. No new runtime should bind 已交車 to 已收清.
```

## Final Decision

The project should treat the current `formal_delivery_status` as an accounting document status, not as a real-world delivery status.

Future UX should show users three independent concepts:

```text
交車 / 離場狀態
收款狀態
會計文件狀態
```

This prevents the system from incorrectly assuming that a car leaving the shop means all money has been received or all accounting work has been completed.

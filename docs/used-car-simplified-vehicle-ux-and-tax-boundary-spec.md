# Used Car Simplified Vehicle UX and Tax Boundary Spec

Last reviewed: 2026-06-13

## 1. Purpose

This document resets the product direction for the Used Car Vehicle form.

The current Used Car Vehicle UI has become too complex because vehicle data, accounting documents, formal delivery phases, tax checks, cost summaries, profit estimates, and many action buttons are shown together.

This document defines a simpler business-first UX and a clear product boundary for the 15-1 estimate. It is a product specification only and does not implement runtime behavior.

## 2. Core UX decision

The Used Car Vehicle form should be simplified into four user-facing areas:

```text
基本資料
採購
售車
收支
```

The vehicle form should not expose low-level accounting implementation details as the primary user experience.

Business users should input business facts. Accounting users should confirm voucher drafts in the accounting workspace.

## 3. 15-1 product boundary

For this app, 15-1 handling belongs to the sale-side vehicle tax estimate.

Product rule:

```text
15-1 estimate uses purchase_price and sold_price.
purchase_price means 購車價 only.
sold_price means 售車成交價.
```

Important product boundary:

```text
purchase_price does not include reconditioning, repair, detailing, auction fee, agency fee, licensing fee, or later vehicle expenses.
```

Later expenses may still affect management profit, cashflow, voucher drafts, accounting review, and normal business reporting. They must not be added into the app's 15-1 purchase-price estimate basis.

Final tax treatment must still be reviewed by the accountant.

## 4. Business example to support product behavior

Business-provided example:

```text
Purchase price: 315,000
Purchase-side estimate: 315,000 / 1.05 * 5% = 15,000

Sale price: 378,000
Sale-side output estimate: 378,000 / 1.05 * 5% = 18,000

Allowed 15-1 estimate for this vehicle: min(15,000, 18,000) = 15,000
Estimated sale-side VAT payable for this vehicle: 18,000 - 15,000 = 3,000
```

System interpretation:

```text
15-1 purchase-side estimate is calculated from purchase_price only.
15-1 estimate is capped by the sale-side output estimate.
Post-purchase costs do not increase the 15-1 purchase-side estimate.
```

## 5. Data meaning correction

### 5.1 purchase_price

`purchase_price` must mean:

```text
購車價：取得車輛本身的價格。
```

It must not mean:

```text
purchase price plus reconditioning
purchase price plus repair
purchase price plus detailing
purchase price plus all direct costs
```

Recommended UI help text:

```text
購車價僅指取得車輛本身的價格；不包含整備、維修、美容、拍場、代辦或其他後續支出。
```

### 5.2 Later vehicle expenses

Examples:

```text
整備支出
維修支出
美容支出
拍場費
代辦費
牌照 / 規費
其他支出
```

These records may affect:

```text
management profit
cashflow
voucher draft generation
accounting review
normal business reporting
```

They must not affect:

```text
15-1 purchase_price estimate basis
```

### 5.3 sold_price

`sold_price` means:

```text
售車成交價
```

It is used for:

```text
Sales Invoice amount
sale-side output estimate
15-1 estimate cap
management profit
```

## 6. Separate management profit from 15-1 estimate

The system must keep two separate views.

### 6.1 Management profit

Purpose:

```text
給經營者看單車大約賺多少。
```

Suggested management view:

```text
management_profit = sold_price - purchase_price - direct_vehicle_expenses
```

This is not the 15-1 estimate basis.

### 6.2 15-1 estimate

Purpose:

```text
給售車營業稅估算與會計確認參考。
```

Suggested app estimate:

```text
output_estimate = round(sold_price / 1.05 * 0.05)
purchase_side_estimate = round(purchase_price / 1.05 * 0.05)
allowed_15_1_estimate = min(purchase_side_estimate, output_estimate)
estimated_vehicle_vat_payable = output_estimate - allowed_15_1_estimate
```

Do not include direct_vehicle_expenses in `purchase_side_estimate`.

## 7. Simplified form structure

### 7.1 基本資料

Purpose:

```text
只記錄車輛本身。
```

Examples:

```text
車牌
VIN / 車身號碼
品牌
車型
年份
顏色
里程
排氣量
燃料
變速系統
車況
入庫日期
庫存狀態
備註
```

This section should not be visually dominated by Sales Invoice, Journal Entry, tax estimate, or formal delivery internals.

### 7.2 採購

Purpose:

```text
記錄這台車怎麼買進來。
```

Examples:

```text
購車價
買入日期
賣方 / 來源
車源類型
買入憑證類型
買入憑證號碼 / 備註
採購付款狀態
採購備註
```

Primary action:

```text
新增採購付款
```

Expected behavior:

```text
Business user enters payment fact.
System creates voucher draft.
Accounting user reviews in accounting workspace.
System creates formal Journal Entry after confirmation.
```

### 7.3 售車

Purpose:

```text
記錄這台車怎麼賣出去。
```

Examples:

```text
成交價
客戶
成交日期
訂金
尾款
交車日期
Sales Invoice 狀態
售車備註
```

Tax information belongs here:

```text
售車稅務模式
15-1 適用狀態
銷項估算
15-1 估算
預估本車營業稅
售車稅務確認狀態
```

Rule:

```text
15-1 warning and estimate should be shown in the sale flow, not as a large warning on the basic vehicle-data flow.
```

### 7.4 收支

Purpose:

```text
記錄所有與單車相關的收款與付款。
```

Examples:

```text
採購付款
整備支出
維修支出
美容支出
拍場費
代辦費
訂金收入
尾款收入
其他收入
其他支出
```

Cashflow input fields:

```text
類型
日期
金額
收 / 支
付款方式
對象
備註
憑證類型
憑證號碼 / 備註
```

## 8. Voucher draft workflow boundary

Money-related input should follow one consistent workflow:

```text
cashflow input
→ voucher draft generated
→ accounting review
→ formal Journal Entry created / submitted
→ simple vehicle-side status updated
```

Vehicle-side statuses should be simple:

```text
待產生傳票草稿
待會計確認
已入帳
需補資料
作廢
```

## 9. Accounting workspace responsibility

The accounting workspace should handle:

```text
voucher draft review
account mapping confirmation
Journal Entry creation
Journal Entry submission
blocked accounting cases
accounting audit trail
```

The vehicle form may show route links:

```text
查看傳票草稿
查看正式傳票
查看 Sales Invoice
```

Route links must not be the main business workflow.

## 10. Formal delivery UI simplification

The existing Phase 3B / 3C / 3D runtime can remain internally, but the UI should not show all phase buttons together.

Recommended display:

```text
目前階段
下一步
一顆主要操作按鈕
相關文件 links
更多資訊 collapse
```

Only one primary next-step action should be visible at a time.

## 11. Actions to remove from primary clutter

The following actions should not all appear together in the primary vehicle form header:

```text
檢查提交資格
重新整理最終檢查
建立 Sales Invoice 草稿
提交 Sales Invoice 並正式出庫
建立預收款沖轉傳票草稿
提交預收款沖轉傳票
標記正式交車完成
```

They should be represented through one current next-step action and secondary links / more-info sections.

## 12. Error and warning presentation

Recommended rule:

```text
Basic vehicle area: no large accounting warnings unless vehicle data itself is invalid.
Sale area: sale tax and Sales Invoice warnings.
Cashflow area: voucher draft and accounting confirmation warnings.
Accounting workspace: full accounting blocked reasons.
```

## 13. Implementation strategy

Do not rewrite everything in one patch.

### UX Phase A: Documentation and wording alignment

```text
Add this spec.
Update README high-level UX direction.
Clarify purchase_price label / help text.
Clarify that purchase_price excludes later expenses.
Clarify that 15-1 estimate uses purchase_price only.
```

### UX Phase B: Vehicle form primary action cleanup

```text
Keep existing runtime services.
Replace many top-level buttons with one primary next-step card.
Move secondary links to related documents area.
Move debug/preflight details to collapsed section.
Do not change accounting runtime.
```

### UX Phase C: Tab simplification

```text
Reorganize visible sections into 基本資料 / 採購 / 售車 / 收支.
Hide or move technical fields away from primary view.
Keep data model compatible.
Do not delete existing fields.
```

### UX Phase D: Cashflow-centered input

```text
Make cashflow input the normal path for purchase, expenses, deposits, and final payments.
Generate voucher drafts automatically.
Let accounting workspace handle confirmation and Journal Entry creation.
```

## 14. Non-goals

The first UI cleanup must not change accounting runtime.

Do not change:

```text
Sales Invoice submit logic
Journal Entry draft creation logic
Journal Entry submit logic
stock update logic
formal_delivery_status progression
existing voucher draft service behavior
existing money flow service behavior
```

Do not delete fields.
Do not migrate accounting history.
Do not implement tax filing.
Do not implement reversal / cancellation.

## 15. Acceptance criteria for first implementation slice

The first implementation slice is successful if:

```text
A user can open a vehicle and immediately understand current status.
Only one primary next-step action is visible.
Vehicle basic data is not visually dominated by accounting internals.
15-1 wording clearly says it uses purchase_price only.
Later vehicle expenses remain separate from the 15-1 purchase-price estimate basis.
Existing Phase 3B / 3C / 3D runtime still works.
Existing verify functions still pass.
```

## 16. Current decision

Do not continue adding Phase 3E runtime before the UI and 15-1 product-boundary simplification is addressed.

Next safe step:

```text
Implement UX Phase A / B as a small UI cleanup patch.
```

The first code patch should avoid changing accounting runtime and should focus on primary action simplification and 15-1 wording correction.

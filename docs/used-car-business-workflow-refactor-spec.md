# Used Car Business Workflow Refactor Spec

Last reviewed: 2026-06-13

## 1. Purpose

This document defines the target business workflow for the Used Car Vehicle module after recent UI QA showed that the current form is still too accounting-document driven.

The core correction is:

```text
成交價 does not belong to vehicle intake.
成交價 belongs to the sale workflow and should only be entered when the vehicle is actually sold.
```

The vehicle lifecycle must be business-first:

```text
採購建檔
→ 整備與支出
→ 銷售成交
→ 金流輸入
→ 傳票草稿
→ 會計確認
→ 正式入帳
```

This is a refactor specification only. It does not implement runtime behavior.

## 2. Current problem

The current UI still exposes too much formal-delivery and accounting machinery on the Used Car Vehicle form.

Observed issues:

```text
成交價 cannot be edited at the time the user expects.
Vehicle intake, purchase, reconditioning, sale, cashflow, Sales Invoice, and Journal Entry steps are mixed together.
The user has to think like an accountant or engineer instead of following the business workflow.
```

This causes operational friction.

## 3. Target role-based business workflow

### 3.1 Procurement staff / vehicle intake

When a car is purchased or received, procurement staff should create the vehicle record and enter vehicle acquisition facts.

They should enter:

```text
車輛基本資料
購車價
底價
開價
車源 / 賣方
買入日期
採購備註
```

They should not enter:

```text
成交價
正式售車客戶
Sales Invoice details
Journal Entry details
formal delivery settlement details
```

### 3.2 Reconditioning / preparation

When the vehicle enters preparation, any spending should be entered into the system as vehicle-related cashflow / expense facts.

Examples:

```text
整備費
維修費
美容費
拍場費
代辦費
牌照 / 規費
其他單車支出
```

Expected behavior:

```text
User enters the expense fact.
System creates a voucher draft.
Accounting user reviews the draft.
Accounting confirmation creates the formal Journal Entry.
```

These expenses may affect management profit, but they do not become part of the app's 15-1 purchase-price estimate basis.

### 3.3 Sales staff / sale workflow

When the car is sold, sales staff should enter the sale facts.

They should enter:

```text
賣給誰
成交價
成交日期
訂金
尾款
交車日期 / 預計交車日期
售車備註
```

This is the first normal point where `成交價` should be entered.

Sale-side tax mode and 15-1 estimate belong to this sale workflow.

### 3.4 Accounting staff

Accounting staff should not rely on the vehicle form as the main accounting workspace.

Accounting staff should work in:

```text
會計作業
→ 傳票草稿
→ 檢查來源資料
→ 確認
→ 系統建立 / 提交正式 Journal Entry
```

The vehicle form should show simple accounting statuses and document links only.

## 4. Target top-level sections

Used Car Vehicle should eventually present the workflow as:

```text
基本資料
採購
整備 / 收支
售車
會計狀態
```

If keeping only four areas is preferred, use:

```text
基本資料
採購
售車
收支
```

`收支` can contain reconditioning and other expense entries.

## 5. Field ownership

### 5.1 Basic vehicle data

Belongs to vehicle intake.

Examples:

```text
車輛編號
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
車輛位置
庫存狀態
備註
```

### 5.2 Procurement fields

Belongs to procurement.

Examples:

```text
購車價
底價
開價
買入日期
車源
賣方
買入憑證
採購付款狀態
```

Important:

```text
購車價 is the purchase price of the vehicle itself.
It does not include reconditioning, repair, detailing, auction, agency, licensing, or later expenses.
```

### 5.3 Reconditioning / expense fields

Belongs to the cashflow / expense workflow.

Do not force these into the basic vehicle form header.

Examples:

```text
支出類型
支出日期
金額
付款方式
對象
憑證
備註
傳票草稿狀態
入帳狀態
```

### 5.4 Sale fields

Belongs to the sale workflow.

Examples:

```text
客戶
成交價
成交日期
訂金
尾款
交車日期
售車稅務模式
15-1 估算
Sales Invoice 狀態
```

Important:

```text
成交價 is not a procurement or intake field.
成交價 should be editable when creating or updating the sale workflow before formal accounting lock.
```

## 6. Cashflow-to-voucher-draft rule

All business actions with money impact should follow the same rule:

```text
business cashflow input
→ system creates voucher draft
→ accounting review
→ accounting confirmation
→ formal Journal Entry
```

Examples:

```text
購車付款 → 傳票草稿 → 會計確認 → Journal Entry
整備支出 → 傳票草稿 → 會計確認 → Journal Entry
訂金收入 → 傳票草稿 → 會計確認 → Journal Entry
尾款收入 → 傳票草稿 → 會計確認 → Journal Entry
其他收入 / 支出 → 傳票草稿 → 會計確認 → Journal Entry
```

The user entering the cashflow should not need to decide debit / credit manually.

## 7. Tax boundary

15-1 estimate belongs to the sale workflow only.

The app's current product boundary:

```text
15-1 purchase-side estimate uses purchase_price only.
15-1 sale-side estimate uses sold_price.
Allowed estimate is capped by sale-side output estimate.
```

Do not include:

```text
整備費
維修費
美容費
拍場費
代辦費
其他後續費用
```

in the 15-1 purchase-side estimate basis.

Those expenses may still be relevant for management profit and normal accounting review.

## 8. UI behavior target

### 8.1 Vehicle intake screen

The user should feel they are creating a vehicle record, not creating accounting documents.

Primary action examples:

```text
儲存車輛
完成入庫
開始整備
直接上架
```

Do not show sale completion, Sales Invoice, settlement Journal Entry, or formal delivery buttons on a newly purchased vehicle.

### 8.2 Procurement area

Primary action examples:

```text
新增採購付款
查看採購付款
查看採購入帳狀態
```

### 8.3 Reconditioning / cashflow area

Primary action examples:

```text
新增整備支出
新增維修支出
新增美容支出
新增其他支出
```

Each action creates or links to voucher draft generation.

### 8.4 Sale area

Primary action examples:

```text
建立售車資料
輸入成交價
新增訂金收入
新增尾款收入
建立 / 查看 Sales Invoice
```

Sale area is the correct place for sale tax mode and 15-1 estimate.

### 8.5 Accounting status area

Show simple status only:

```text
待產生傳票草稿
待會計確認
已入帳
需補資料
已作廢
```

Provide document links, not engineering-style action clutter.

## 9. Locking rules

The form must not lock sale fields too early.

Target rule:

```text
Before formal accounting lock, sale workflow fields such as customer and sold_price must be editable through the sale workflow.
After Sales Invoice / formal accounting documents are submitted, corrections should go through a controlled correction / reversal workflow, not direct field editing.
```

This means:

```text
Vehicle status = 已售出
```

alone should not be treated as enough reason to make every sale-related field permanently uneditable.

The system needs a clearer distinction between:

```text
business sold state
formal accounting locked state
formal delivery completed state
```

## 10. Implementation strategy

Do not rewrite all runtime at once.

### Phase R1: Business workflow spec and UI wording

```text
Add this spec.
Stop treating sold_price as an intake / procurement field in UI wording.
Clarify which fields belong to procurement and which belong to sale.
```

### Phase R2: Sale workflow editability fix

```text
Allow customer / sold_price / sale facts to be edited in the sale workflow before formal accounting lock.
Do not unlock procurement or accounting technical fields.
Do not allow direct editing after submitted formal accounting documents without a correction workflow.
```

### Phase R3: Cashflow-centered operation

```text
Make purchase payments, preparation expenses, deposits, final payments, and other money movements use one cashflow input pattern.
Generate voucher drafts automatically.
Accounting workspace confirms voucher drafts.
```

### Phase R4: Form layout refactor

```text
Reorganize the Used Car Vehicle form into business sections.
Move technical Sales Invoice / Journal Entry details into status cards and document links.
Keep existing data model compatible where possible.
```

### Phase R5: Accounting lock / correction workflow

```text
Define formal lock points.
Add correction / reversal workflow for submitted documents.
Do not allow silent direct edits to formally posted accounting data.
```

## 11. Non-goals for the next code patch

The next code patch should not implement a full rewrite.

Do not:

```text
Delete existing fields
Delete existing services
Change submitted Journal Entry behavior
Change submitted Sales Invoice behavior
Change stock update behavior
Implement Phase 3E
Implement cancellation / reversal
Rewrite all doctypes
```

## 12. Next safe code patch

The next safest implementation slice is:

```text
Sale Workflow Editability Fix
```

Scope:

```text
Allow sale facts, especially customer and sold_price, to be edited from the sale workflow while the vehicle is not formally accounting-locked.
Keep accounting technical fields read-only.
Keep submitted document correction out of scope.
```

This should be implemented as a small UI / validation patch before any larger form-layout refactor.

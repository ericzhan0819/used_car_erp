# P1-MVP-ACC-POLISH：Advance Account Journal Entry Warning

日期：2026-06-25  
專案：Used Car ERP / ERPNext / Frappe  
Repo：`ericzhan0819/used_car_erp`  
觀察點：Step 8A 取消保留 / 退訂金流程後續會計入帳

---

## 1. 本文件目的

本文件記錄目前會計確認入帳時出現的 ERPNext warning：

```text
Making Journal Entries against advance accounts: {'0202136 - 預收款項 - O'} is not recommended. These Journals won't be available for Reconciliation.
```

此 warning 不是 Step 8A「取消保留 / 處理訂金」業務任務卡 runtime 的阻擋問題，而是 ERPNext 會計流程設計層提示。

本文件只記錄問題、風險與後續方向，不修改 runtime、不修改科目、不修改會計流程。

---

## 2. 目前現象

使用者在會計作業按入帳時，ERPNext 顯示：

```text
Making Journal Entries against advance accounts: {'0202136 - 預收款項 - O'} is not recommended. These Journals won't be available for Reconciliation.
```

重點：

```text
0202136 - 預收款項 - O
```

被 ERPNext 視為 advance account。

ERPNext 不建議直接用 Journal Entry against advance accounts，因為這類 Journal Entry 不會進入 ERPNext 原生 Payment Reconciliation 流程。

---

## 3. 目前 Used Car ERP 設計

目前中古車金流基礎設計是：

```text
Used Car Money Flow
→ Used Car Voucher Draft
→ 會計確認
→ Journal Entry
```

訂金 / 尾款 / 退款目前都走 internal Voucher Draft，再由會計確認成 Journal Entry。

這符合目前 MVP 邊界：

```text
業務頁只輸入商業事實
會計作業頁確認科目與金額
不讓業務直接面對 ERPNext 底層會計文件
```

但它沒有完全採用 ERPNext 原生的：

```text
Payment Entry
Payment Reconciliation
Sales Order advance allocation
Sales Invoice allocation
```

因此 ERPNext 會對 advance account + Journal Entry 組合提出 warning。

---

## 4. 風險判斷

若按入帳後：

```text
Journal Entry 成功建立並 submit
Used Car Voucher Draft.status = 已入帳
Used Car Money Flow.status = 已入帳
```

則此 warning 可視為：

```text
非阻擋 warning
```

短期不影響 Used Car ERP MVP 的任務卡流程。

但長期風險是：

```text
ERPNext 原生 Payment Reconciliation 不會納入這些 Journal Entry
未來若要使用 ERPNext 原生應收 / 預收 / 發票沖帳流程，會不順
會計查帳可能需要依賴自訂 Money Flow / Voucher Draft / Journal Entry 關聯，而不是 ERPNext 原生對帳工具
```

---

## 5. 短期方案 A：維持 Journal Entry，但避開 advance account

短期可考慮把 Used Car ERP 的訂金 / 尾款 / 退款草稿預設科目，從 ERPNext 會視為 advance account 的：

```text
0202136 - 預收款項 - O
```

改為非 advance account 類型的暫收科目，例如：

```text
中古車客戶暫收款
中古車訂金暫收
其他暫收款
```

前提：

```text
該科目不可被 ERPNext 視為 advance account
仍需符合公司會計分類與報表需求
```

優點：

```text
改動小
保留現有 Used Car Voucher Draft → Journal Entry 架構
不大幅重寫業務流程
可能可消除 warning
```

缺點：

```text
仍不是 ERPNext 原生 Payment Entry 流程
仍不會走 Payment Reconciliation
未來正式導入原生對帳時仍可能要重構
```

---

## 6. 中長期方案 B：改用 ERPNext 原生 Payment Entry

方案 B 是把訂金、尾款與退款正式改成 ERPNext 原生 payment flow。

概念上會從：

```text
Used Car Money Flow → Voucher Draft → Journal Entry
```

改成：

```text
Used Car 業務任務卡
→ 建立 / 建議 ERPNext Payment Entry
→ Payment Entry submit
→ 未來與 Sales Invoice / Sales Order 做 allocation / reconciliation
```

可能需要引入：

```text
Payment Entry
Payment Reconciliation
Sales Order advance 或其他可承接 advance 的文件
Sales Invoice allocation
退款 Payment Entry 或反向付款流程
```

優點：

```text
更貼近 ERPNext 原生會計邏輯
advance payment 可被 ERPNext 原生工具追蹤與分配
未來與 Sales Invoice、outstanding、reconciliation 整合較自然
可降低 advance account + Journal Entry warning
```

缺點：

```text
改動大
需要重新設計訂金 / 尾款 / 退款與成交流程
可能需要更早建立 Sales Order 或其他可承接 advance 的正式交易文件
業務任務卡與會計作業頁都要重新接 ERPNext Payment Entry 狀態
會讓 MVP 時程變長
```

---

## 7. 目前建議

目前不建議立刻導入方案 B。

理由：

```text
目前 MVP 重點是讓業務流程跑通
Step 8A warning 尚未證實阻擋入帳
方案 B 會牽涉 Sales Order / Payment Entry / Payment Reconciliation / Sales Invoice allocation
導入成本高於目前收益
```

短期建議：

```text
先保留現有 Voucher Draft → Journal Entry 架構
若 warning 不阻擋提交，暫時記錄為 non-blocking warning
下一個會計 polish 再評估方案 A：改用非 advance 類型暫收科目
```

中長期建議：

```text
等 MVP 主流程穩定後，再開 P2 或 P1-ACC-PAYMENT-ENTRY 重新設計 Payment Entry / Reconciliation 架構
```

---

## 8. 後續任務建議

### 8.1 短期 polish

```text
P1-MVP-ACC-POLISH-1：Review Used Car advance account warning
```

目標：

```text
確認 warning 是否阻擋提交
確認 0202136 - 預收款項 - O 的 ERPNext account type / root type / account settings
確認可替代的非 advance 暫收科目
評估是否只改 Voucher Draft 預設科目
```

### 8.2 中長期 payment native flow

```text
P2-ACC-PAYMENT-ENTRY：Native Payment Entry Flow
```

目標：

```text
評估訂金 / 尾款是否改用 Payment Entry
評估是否建立 Sales Order 承接訂金 advance
評估成交時 Sales Invoice 如何 allocation
評估退款是否走 Payment Entry / return payment
評估是否保留 Used Car Money Flow 作為業務摘要層
```

---

## 9. 本文件狀態

```text
status: recorded
runtime change: none
schema change: none
blocking: no, unless Journal Entry cannot submit
recommended next action: observe and defer to accounting polish
```

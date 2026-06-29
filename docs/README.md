# Used Car ERP Docs Index

## 1. 文件使用原則

`docs/` 目前同時包含 active docs 與 historical docs。

新任務應優先閱讀 active docs，確認目前產品主線、UX 邊界與下一步實作範圍。

historical docs 只能作為背景、施工紀錄或回溯參考，不應直接主導新任務。

不要因為舊 handoff、formal delivery 或 accounting runtime 文件，而把會計按鈕加回車輛頁。車輛頁應維持業務事實與摘要，不承接會計文件操作入口。

---

## 2. Active documents

- `docs/current-state.md`：目前專案定位、穩定點、產品主線與下一步邊界。
- `docs/p1-mvp-ops-used-car-operation-ledger-direction.md`：P1-MVP-OPS 營運管理帳方向定調，定義 Money Flow 主帳、資金帳、單車損益、文件檢查、結案列印與記帳士交接主線。
- `docs/p1-mvp-ops-step-2-money-flow-ledger-field-audit.md`：Money Flow 主帳欄位盤點，記錄現有欄位、建立來源、消費端、缺口與下一步資金帳戶模型方向。
- `docs/p1-mvp-ops-step-3-minimal-cash-account-model.md`：資金帳戶最小模型規格，定義 `cash_account` / `payment_method` / `settlement_status` 分工、期初餘額、初期資金帳戶與 Step 3A runtime 邊界。
- `docs/p1-mvp-ops-step-3b-purchase-payment-money-flow-spec.md`：採購付款 Money Flow 規格，定義 `purchase_price` 與 `flow_type = 購車付款` 的分工。
- `docs/p1-mvp-ops-step-3b-2a-guided-purchase-payment-dialog-smoke.md`：新增購車付款 guided Dialog browser smoke 收尾紀錄，包含 DocType Select options metadata sync 注意事項。
- `docs/p1-mvp-business-input-boundary-report.md`：業務輸入與會計作業分工邊界。
- `docs/p1-mvp-ux-ops-2-guided-business-flow-forms.md`：任務卡片式業務流程總規格。
- `docs/p1-mvp-ux-ops-2-step-2-guided-vehicle-intake-task-card-spec.md`：新增車輛任務卡 Step 1 / Step 2 規格。
- `docs/p1-mvp-dash-2-custom-overview-page.md`：總覽 custom Page 與 shared guided intake Dialog 架構修正。
- `docs/p1-mvp-ux-ops-2-step-4-preparation-expense-task-card-spec.md`：新增整備 / 維修 / 美容 / 代辦 / 拍場支出任務卡規格。
- `docs/p1-mvp-ux-ops-2-step-4a-guided-preparation-expense-dialog-smoke.md`：新增支出 shared guided Dialog browser smoke 收尾紀錄。
- `docs/p1-mvp-ux-ops-2-step-5-guided-listing-task-card-spec.md`：整備完成並上架任務卡規格。
- `docs/p1-mvp-ux-ops-2-step-5a-guided-listing-dialog-smoke.md`：整備完成並上架 shared guided Dialog browser smoke 收尾紀錄。
- `docs/p1-mvp-ux-ops-2-step-6-guided-reservation-deposit-task-card-spec.md`：收訂金並保留任務卡規格。
- `docs/p1-mvp-ux-ops-2-step-6a-guided-reservation-deposit-dialog-smoke.md`：收訂金並保留 shared guided Dialog browser smoke 收尾紀錄。
- `docs/p1-mvp-ux-ops-2-step-7-guided-final-payment-task-card-spec.md`：收尾款任務卡規格。
- `docs/p1-mvp-ux-ops-2-step-7a-guided-final-payment-dialog-smoke.md`：收尾款 shared guided Dialog browser smoke 收尾紀錄。
- `docs/p1-mvp-ux-ops-2-step-8-guided-reservation-cancellation-deposit-refund-spec.md`：取消保留 / 處理訂金任務卡規格。
- `docs/p1-mvp-ux-ops-2-step-8a-guided-reservation-cancellation-dialog-smoke.md`：取消保留 / 處理訂金 shared guided Dialog browser smoke 收尾紀錄。
- `docs/p1-mvp-acc-polish-advance-account-journal-entry-warning.md`：advance account + Journal Entry warning 與後續 Payment Entry 方案記錄。
- `docs/p1-mvp-dash-1-used-car-management-dashboard-mvp.md`：中古車管理總覽與 Dashboard MVP 邊界。
- `docs/used-car-role-permission-boundary-spec.md`：角色與權限邊界規格。
- `docs/used-car-role-permission-inventory.md`：現有角色與權限盤點。
- `docs/used-car-field-permlevel-design.md`：欄位 permlevel 與顯示邊界設計。
- `docs/vehicle-delivery-payment-accounting-status-boundary-spec.md`：交車、收款與會計狀態邊界。

---

## 3. Current product direction

```text
Used Car ERP 是 ERPNext 上的中古車行營運操作層。
目前 MVP 主線是車行營運管理帳，而不是完整 ERPNext 會計閉環。
Money Flow 是現階段 MVP 主帳，用來記錄收入、支出、退款、待收、待付與單車損益事實。
ERPNext 的 Journal Entry、Sales Invoice、Payment Entry、Reconciliation 等正式會計流程降級為後期 / 選配 / 會計輔助層。
```

目前優先目標：

```text
每台車花多少
每台車收多少
每台車賺賠多少
現金 / 銀行還有多少
哪些款項待收 / 待付
哪些文件缺漏
哪些資料要交給記帳士
成交後能否列印車輛結案明細表
```

業務端禁止 / 避免字詞：

- Sales Invoice
- Journal Entry
- Voucher Draft
- Money Flow
- GL Entry
- 借方 / 貸方
- 會計科目
- 預收款沖轉

會計文件與技術術語應留在會計作業、技術文件、內部開發文件或管理 / 會計專用頁面，不應出現在業務任務卡、車輛頁或總覽業務入口。

---

## 4. Current runtime direction

目前主要入口：

```text
/app/總覽 → custom Page
```

`/app/總覽` 不再是 Frappe native Workspace。總覽是中古車業務操作面板，可直接呼叫 shared guided intake Dialog。

目前業務任務卡 runtime 已包含：

```text
新增買入車輛
新增支出
整備完成並上架
收訂金並保留
收尾款
取消保留 / 處理訂金
新增購車付款
```

P1-MVP-OPS Step 3B-2A 已完成：

```text
Guided Purchase Payment Dialog browser smoke close
```

P1-MVP-OPS Step 3B-3 已完成：

```text
Vehicle purchase payment summary polish
```

結論：

```text
新增購車付款 Dialog runtime 可用。
購車付款可建立為 Used Car Money Flow。
車輛頁收支摘要已新增「購車付款摘要」，顯示購車價、已記錄購車付款、待付購車款與付款狀態。
Used Car Money Flow.flow_type Select options 有 metadata 變更時，需要 migrate 或 reload-doc 同步 site DB metadata。
```

下一步建議：

```text
P1-MVP-OPS Step 3B-3A：Vehicle purchase payment summary browser smoke
```

Step 3B-3 已聚焦單車購車付款摘要。本階段只做單車摘要，不新增 Dashboard 總餘額、不建立正式會計文件、不改管理毛利成本計算。

---

## 5. Historical / reference documents

以下類型目前視為 historical / reference：

- `p1-acc-*`
- `formal-delivery-*`
- `p1-ux-tax-*`
- `*-handoff.md`
- smoke / QA handoff 文件

這些文件可用來理解過去施工脈絡、驗證紀錄與已完成基礎能力，但不代表目前 UX 主線，也不應覆蓋 active docs 的產品邊界。

---

## 6. Future cleanup plan

本次不搬檔、不刪檔、不建立 archive 目錄，只提出後續可能計畫。

```text
P1-DOCS-CLEANUP-2 才考慮搬移歷史文件到：
- docs/archive/handoffs/
- docs/archive/accounting-runtime/
- docs/archive/superseded/
```

P1-DOCS-CLEANUP-1 只建立 docs 索引並更新 current state。

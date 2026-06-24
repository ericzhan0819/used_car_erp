# Used Car ERP Current State

## 1. 專案定位

`used_car_erp` 是 ERPNext custom app。

定位是中古車業務操作層，不修改 ERPNext / Frappe core。

ERPNext 原生模組負責會計、庫存、正式文件與報表。

`used_car_erp` 的業務頁應讓使用者輸入商業事實，並由系統與會計作業承接底層資料流。

## 2. 最新穩定點

```text
9aa2a64 feat: replace overview workspace with custom page
761b7e5 docs: define preparation expense task card spec
```

目前 runtime 穩定點：

```text
9aa2a64 feat: replace overview workspace with custom page
```

目前最新規格文件穩定點：

```text
761b7e5 docs: define preparation expense task card spec
```

## 3. 目前產品主線

```text
P1-MVP-UX-OPS-2：Guided Business Flow Forms
```

核心方向：

- 業務端使用任務卡片。
- 一張卡處理一件事。
- 業務不直接面對完整 ERPNext DocType 表單。
- 業務頁不暴露會計文件與會計術語。
- 會計作業承接 Journal Entry / Sales Invoice / Voucher Draft 等正式流程。

目前產品主線已轉為：

```text
業務端 = 任務卡片式輸入
會計端 = 會計作業
車輛頁 = 業務事實與摘要
會計文件與技術術語不暴露在業務頁
```

目前總覽入口已改為 custom Page：

```text
/app/總覽 → custom Page
```

總覽不再是 Frappe native Workspace。custom Page 作為中古車業務操作面板，提供庫存狀態卡與常用作業，並直接呼叫 shared guided intake Dialog 開啟「新增買入車輛」。

## 4. 目前已完成主流程摘要

- 車輛主檔 `Used Car Vehicle` 已作為中古車業務主檔。
- 入庫 foundation：建立 Item / Serial No / Stock Entry，狀態可進入庫存中。
- 整備 / 上架 foundation：狀態可在庫存中、整備中、上架中之間切換。
- 訂金保留 foundation：建立 Reservation、Money Flow、Voucher Draft。
- 尾款收款 foundation：建立尾款金流與傳票草稿。
- 會計確認 foundation：會計作業確認後建立正式 Journal Entry。
- 成交 foundation：車輛可標記已售出，保留單可標記完成。
- 收支摘要：車輛頁可看業務語意的收支摘要。
- 15-1 邊界：購車價作為購入估算基礎，整備 / 維修 / 美容 / 拍場 / 代辦等後續支出不併入 15-1 購入成本。
- Guided intake：`/app/總覽` 與 `Used Car Vehicle List` 共用 shared guided intake Dialog。
- Custom overview：`/app/總覽` 已由 native Workspace 改為 custom Page。
- Preparation expense spec：已定義「新增支出」任務卡規格，尚未實作 runtime。

## 5. 目前 UX 邊界

業務頁應顯示：

- 車輛基本資料
- 買入來源
- 購車價
- 收購業務
- 監理 / 稅務 checklist
- 整備 / 維修 / 美容 / 代辦 / 拍場支出
- 訂金
- 尾款
- 成交價
- 收支摘要

業務頁不應顯示：

- Sales Invoice
- Journal Entry
- Voucher Draft
- Money Flow
- GL Entry
- 借方 / 貸方
- 會計科目
- 預收款沖轉
- formal delivery 技術流程
- preflight 技術語言

## 6. 目前下一步

下一步建議：

```text
P1-MVP-UX-OPS-2 Step 4A：Guided Preparation Expense Dialog Runtime
```

Step 4A 應依據：

```text
docs/p1-mvp-ux-ops-2-step-4-preparation-expense-task-card-spec.md
```

Step 4A 只做：

- 車輛頁「新增支出」業務任務卡。
- 支出日期、支出類型、金額、付款方式、付款對象、憑證附件、備註。
- 薄 wrapper service，如必要。
- 沿用既有 Money Flow service 建立底層支出紀錄。
- 成功後刷新車輛頁收支摘要。

Step 4A 不做：

- 總覽新增支出入口。
- 支出列表重設計。
- 會計作業頁重設計。
- Voucher Draft 入帳流程重寫。
- 科目選擇 UI。
- 權限大改。
- DocType schema 大改。
- Journal Entry / Sales Invoice / Stock Entry runtime 修改。

## 7. Historical docs 注意事項

`docs/` 中仍保留大量 P1-ACC、formal-delivery、handoff、smoke 文件。

它們是歷史施工紀錄，不代表目前 UX 主線。

新任務應以 `docs/README.md` 和 active docs 為準。

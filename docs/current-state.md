# Used Car ERP Current State

## 1. 專案定位

`used_car_erp` 是 ERPNext custom app。

定位是中古車業務操作層，不修改 ERPNext / Frappe core。

ERPNext 原生模組負責會計、庫存、正式文件與報表。

`used_car_erp` 的業務頁應讓使用者輸入商業事實，並由系統與會計作業承接底層資料流。

## 2. 最新穩定點

```text
990dab7 feat: add guided reservation deposit dialog
docs: close guided reservation deposit smoke
```

目前 runtime 穩定點：

```text
990dab7 feat: add guided reservation deposit dialog
```

目前 docs 收尾穩定點：

```text
docs: close guided reservation deposit smoke
```

目前最新 smoke 文件：

```text
P1-MVP-UX-OPS-2 Step 6A：Guided Reservation / Deposit Dialog Smoke Close
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
- Preparation expense Step 4A：車輛頁「新增支出」已改為 shared guided Dialog。
- Preparation expense Step 4A：成功後顯示「支出紀錄已建立」。
- Preparation expense Step 4A：沿用 `create_general_expense_money_flow`。
- Preparation expense Step 4A：底層 Money Flow / Voucher Draft foundation 沿用。
- Preparation expense Step 4A：browser smoke passed。
- Guided listing Step 5 spec：已定義「整備完成並上架」任務卡規格，範圍限定文件，不改 runtime / schema / 會計流程。
- Guided listing Step 5S：已新增 Used Car Vehicle `listing_date` 上架日期欄位，供 Step 5A runtime 寫入。
- Guided listing Step 5A：已新增 shared guided listing Dialog，車輛頁可用「整備完成並上架」將 `listing_date` / `floor_price` / `asking_price` / `sales_note` 寫回，並將狀態改為 `上架中`。
- Guided listing Step 5A：browser smoke passed。
- Guided reservation / deposit Step 6 spec：已定義「收訂金並保留」任務卡規格，範圍限定文件，不改 runtime / schema / 會計流程。
- Guided reservation / deposit Step 6A：已新增 shared guided reservation/deposit Dialog，車輛頁可用「收訂金並保留」輸入客戶與訂金資料，成功後顯示「已收訂金，車輛已保留」，並將狀態改為 `保留中`。
- Guided reservation / deposit Step 6A：browser smoke passed。

## 5. 目前 UX 邊界

業務頁應顯示：

- 車輛基本資料
- 買入來源
- 購車價
- 收購業務
- 監理 / 稅務 checklist
- 整備 / 維修 / 美容 / 代辦 / 拍場支出
- 上架日期
- 底價 / 開價
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

下一步建議可二選一：

```text
P1-MVP-UX-OPS-2 Step 6B：Reserved Vehicle Status Copy Polish
```

或：

```text
P1-MVP-UX-OPS-2 Step 7：Guided Final Payment Task Card Spec
```

Step 6B 適合先整理保留中 dashboard 文案，避免業務頁出現「傳票草稿」「金流」等技術語意。

Step 7 適合繼續推完整業務主流程，進入收尾款任務卡規格，繼續遵守一張卡處理一件事。

## 7. Historical docs 注意事項

`docs/` 中仍保留大量 P1-ACC、formal-delivery、handoff、smoke 文件。

它們是歷史施工紀錄，不代表目前 UX 主線。

新任務應以 `docs/README.md` 和 active docs 為準。

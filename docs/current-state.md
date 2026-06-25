# Used Car ERP Current State

## 1. 專案定位

`used_car_erp` 是 ERPNext custom app。

定位是中古車業務操作層，不修改 ERPNext / Frappe core。

ERPNext 原生模組負責會計、庫存、正式文件與報表。

`used_car_erp` 的業務頁應讓使用者輸入商業事實，並由系統與會計作業承接底層資料流。

## 2. 最新穩定點

```text
847a2aa feat: add guided reservation cancellation dialog
docs: close guided reservation cancellation smoke
```

目前 runtime 穩定點：

```text
847a2aa feat: add guided reservation cancellation dialog
```

目前 docs 收尾穩定點：

```text
docs: close guided reservation cancellation smoke
```

目前最新 smoke 文件：

```text
P1-MVP-UX-OPS-2 Step 8A：Guided Reservation Cancellation Dialog Smoke Close
```

目前已知會計 polish 記錄：

```text
P1-MVP-ACC-POLISH：Advance Account Journal Entry Warning
```

## 3. 目前產品主線

目前產品主線正式調整為：

```text
P1-MVP-OPS：中古車行營運管理帳
```

核心方向：

```text
車行營運管理帳
+ 資金帳
+ 單車損益
+ 文件檢查
+ 成交結案列印
+ 記帳士交接包
```

`P1-MVP-UX-OPS-2：Guided Business Flow Forms` 已完成多個業務任務卡 runtime，是目前業務輸入層的重要基礎，但後續 MVP 不再以完整 ERPNext 會計閉環作為主線。

目前主線改為：

```text
業務端 = 任務卡片式輸入營運事實
Money Flow = MVP 主帳 / 營運事實紀錄
管理帳層 = 單車損益、現金、銀行、待收、待付、缺憑證
會計交接層 = 記帳士交接資料、結案明細、申報期彙整
正式會計閉環 = 後期 / 選配 / 會計輔助層
```

核心邊界維持：

- 業務端使用任務卡片。
- 一張卡處理一件事。
- 業務不直接面對完整 ERPNext DocType 表單。
- 業務頁不暴露會計文件與會計術語。
- Money Flow 記錄車行營運事實，不等同正式會計分錄。
- Journal Entry / Sales Invoice / Payment Entry / Reconciliation 不再是 MVP 驗收主軸。
- 紙本資料夾仍保存正式文件，ERP 負責索引、檢查、統計、列印與交接。

目前總覽入口已改為 custom Page：

```text
/app/總覽 → custom Page
```

總覽作為中古車業務操作面板，提供庫存狀態卡與常用作業，並直接呼叫 shared guided intake Dialog 開啟「新增買入車輛」。後續 Dashboard 指標應逐步往老闆可用的營運總覽收斂，例如現金 / 銀行餘額、待收款、缺憑證與本月成交台數。

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
- Guided reservation / deposit Step 6A：已新增 shared guided reservation/deposit Dialog，車輛頁可用「收訂金並保留」輸入客戶、成交價與訂金資料，成功後顯示「已收訂金，車輛已保留」，並將狀態改為 `保留中`。
- Guided reservation / deposit Step 6A：browser smoke passed。
- Guided final payment Step 7 spec：已定義「收尾款」任務卡規格，範圍限定文件，不改 runtime / schema / 會計流程。
- Guided final payment Step 7A：已新增 shared guided final payment Dialog，車輛頁可用「收尾款」輸入尾款資料，成功後顯示「已收尾款」。
- Guided final payment Step 7A：收尾款 Dialog read-only 顯示成交價 / 訂金 / 建議尾款。
- Guided final payment Step 7A：browser smoke passed。
- Guided reservation cancellation / deposit refund Step 8 spec：已盤點取消保留、訂金收款、尾款收款、草稿作廢與退款承載能力，並定義「取消保留 / 處理訂金」任務卡規格。
- Guided reservation cancellation Step 8A：已新增 shared guided cancellation Dialog，車輛頁「取消保留」改為「取消保留 / 處理訂金」任務卡。
- Guided reservation cancellation Step 8A：未入帳訂金取消會作廢待處理資料並讓車輛回 `上架中`。
- Guided reservation cancellation Step 8A：已入帳訂金取消會建立全額退款待內部確認資料，不直接建立 Journal Entry。
- Guided reservation cancellation Step 8A：已建立尾款後取消會被阻擋。
- Guided reservation cancellation Step 8A：browser smoke passed。
- Accounting polish note：會計入帳時若使用 advance account `0202136 - 預收款項 - O` 產生 Journal Entry，ERPNext 會提示該 Journal Entry 不會進入 Payment Reconciliation；目前記錄為 non-blocking warning，後續評估科目 polish 或 Payment Entry 原生流程。
- P1-MVP-OPS Step 2：已完成 Money Flow 主帳欄位盤點，確認 `Used Car Money Flow` 已有車輛、金額、日期、付款方式、憑證附件、Voucher Draft / Journal Entry 連結等基礎，但缺資金帳戶、通用交易對象、憑證狀態、營運結清狀態、是否交記帳士，以及與 `Used Car Vehicle Cost` 的明確邊界 / 連結。
- P1-MVP-OPS Step 3：已完成資金帳戶最小模型規格，確認 `cash_account` 只表示真正資金位置，初期帳戶為 `現金`、`主要銀行`、`其他`；待收 / 待付不作為資金帳戶，而由 `settlement_status` 表示；採購付款要進 Money Flow；資金帳戶需要期初餘額；本階段不做私人代墊與刷卡未撥款。
- P1-MVP-OPS Step 3A-1：已新增 `Used Car Cash Account` schema foundation；`Used Car Money Flow` 已新增 `cash_account` / `settlement_status` / `counterparty_name` 欄位；初始資金帳戶為 `現金` / `主要銀行` / `其他`。本階段不改 Dialog、不改 service wiring、不改會計 runtime。
- P1-MVP-OPS Step 3A-2：已完成 service wiring；Money Flow service 現在會寫入 `cash_account` / `settlement_status` / `counterparty_name`；`現金` / `匯款` / `其他` / `信用卡` 會保守推導到 `現金` / `主要銀行` / `其他`。本階段不改 Dialog、不改車輛頁摘要、不改會計 runtime。
- P1-MVP-OPS Step 3A-3A：已完成新增支出 Dialog 資金欄位接線。新增支出 Dialog 現在可輸入交易對象、收付狀態、資金帳戶。本階段只處理新增支出 Dialog，未修改訂金 / 尾款 / 退款 Dialog，未改 DocType schema、service wiring、會計 runtime。

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
- 取消保留原因
- 退訂金業務事實

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
P1-MVP-OPS Step 3A-3B：收訂金 / 收尾款 Dialog 接資金欄位
```

原因：

```text
P1-MVP-OPS Step 3A-3A 已完成新增支出 Dialog 的 cash_account / settlement_status / counterparty_name 接線。
下一步要讓收訂金 / 收尾款 Dialog 接入資金欄位。
仍不改 Journal Entry / Sales Invoice / Payment Entry，不處理 advance account warning。
```

Step 3A-3B 建議範圍：

```text
更新收訂金 / 收尾款 guided Dialog 欄位輸入
保留既有 Money Flow / Voucher Draft / 會計 runtime 邊界
```

Step 3A 不應：

```text
不做刷卡未撥款
不做私人代墊
不做多銀行管理 UI
不做部分收付明細
不做資金轉帳
不做月結批次付款
不改 Journal Entry / Sales Invoice / Payment Entry
不處理 advance account warning
不直接做成交確認任務卡 runtime
不合併 Money Flow 與 Vehicle Cost runtime
```

建議 commit message：

```text
feat: add cash account inputs to sales payment dialogs
```

## 7. Historical docs 注意事項

`docs/` 中仍保留大量 P1-ACC、formal-delivery、handoff、smoke 文件。

它們是歷史施工紀錄，不代表目前 UX 主線。

新任務應以 `docs/README.md` 和 active docs 為準。

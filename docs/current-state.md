# Used Car ERP Current State

## 1. 專案定位

`used_car_erp` 是 ERPNext custom app。

定位是中古車業務操作層，不修改 ERPNext / Frappe core。

ERPNext 原生模組負責會計、庫存、正式文件與報表。

`used_car_erp` 的業務頁應讓使用者輸入商業事實，並由系統與會計作業承接底層資料流。

---

## 2. 最新穩定點

目前 runtime 穩定點：

```text
f9c45e5 fix: move purchase payment summary to purchase section
```

目前 docs 收尾穩定點：

```text
docs: close purchase payment summary smoke
```

目前最新 smoke 文件：

```text
P1-MVP-OPS Step 3B-3C：Purchase Payment Summary Browser Smoke Close
```

目前已知會計 polish 記錄：

```text
P1-MVP-ACC-POLISH：Advance Account Journal Entry Warning
```

Advance account warning 目前仍記錄為 non-blocking，不作為下一步主線。

---

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

目前主線：

```text
業務端 = 任務卡片式輸入營運事實
Money Flow = MVP 主帳 / 營運事實紀錄
管理帳層 = 單車損益、現金、銀行、待收、待付、缺憑證
會計交接層 = 記帳士交接資料、結案明細、申報期彙整
正式會計閉環 = 後期 / 選配 / 會計輔助層
```

核心邊界：

- 業務端使用任務卡片。
- 一張卡處理一件事。
- 業務不直接面對完整 ERPNext DocType 表單。
- 業務頁不暴露會計文件與會計術語。
- Money Flow 記錄車行營運事實，不等同正式會計分錄。
- Journal Entry / Sales Invoice / Payment Entry / Reconciliation 不再是 MVP 驗收主軸。
- 紙本資料夾仍保存正式文件，ERP 負責索引、檢查、統計、列印與交接。

目前總覽入口：

```text
/app/總覽 → custom Page
```

總覽作為中古車業務操作面板，提供庫存狀態卡與常用作業，並直接呼叫 shared guided intake Dialog 開啟「新增買入車輛」。後續 Dashboard 指標應逐步往老闆可用的營運總覽收斂，例如現金 / 銀行餘額、待收款、缺憑證與本月成交台數。

---

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
- Guided preparation expense：車輛頁「新增支出」已改為 shared guided Dialog。
- Guided listing：車輛頁可用「整備完成並上架」寫入 `listing_date` / `floor_price` / `asking_price` / `sales_note` / `status = 上架中`。
- Guided reservation / deposit：車輛頁可用「收訂金並保留」輸入客戶、成交價與訂金資料，成功後車輛進入 `保留中`。
- Guided final payment：車輛頁可用「收尾款」輸入尾款資料，成功後顯示「已收尾款」。
- Guided reservation cancellation：車輛頁「取消保留」已改為「取消保留 / 處理訂金」任務卡。
- P1-MVP-OPS Step 2：已完成 Money Flow 主帳欄位盤點。
- P1-MVP-OPS Step 3：已完成資金帳戶最小模型規格。
- P1-MVP-OPS Step 3A-1：已新增 `Used Car Cash Account` schema foundation；`Used Car Money Flow` 已新增 `cash_account` / `settlement_status` / `counterparty_name` 欄位。
- P1-MVP-OPS Step 3A-2：已完成 service wiring；Money Flow service 現在會寫入 `cash_account` / `settlement_status` / `counterparty_name`。
- P1-MVP-OPS Step 3A-3A：已完成新增支出 Dialog 資金欄位接線。
- P1-MVP-OPS Step 3A-3B：已完成收訂金並保留 / 收尾款 Dialog 資金欄位接線。
- P1-MVP-OPS Step 3A-3C：已完成取消保留 / 處理訂金 Dialog 的退款資金欄位接線。
- P1-MVP-OPS Step 3A-4：已完成車輛頁收支摘要資金欄位顯示。
- P1-MVP-OPS Step 3A-4B：已完成保留 / 成交流程同步 Used Car Vehicle 售車摘要欄位。
- P1-MVP-OPS Step 3B-1：已完成購車付款 Money Flow service foundation。`Used Car Money Flow.flow_type` 已支援 `購車付款`，`VehicleMoneyFlowService.create_purchase_payment_money_flow` 可建立支出方向、待審核、已付款 / 待付款 / 部分付款的購車付款紀錄，並保留 `purchase_price` 作為管理毛利成本基礎。本階段未新增 JS Dialog、車輛頁按鈕、Voucher Draft 或正式會計文件。
- P1-MVP-OPS Step 3B-2：已完成 Guided Purchase Payment Dialog。車輛頁新增「新增購車付款」任務卡，接線至 `create_purchase_payment_money_flow`，可建立購車付款 Money Flow，成功後刷新車輛頁收支摘要。本階段未新增 Dashboard 餘額、未新增購車付款摘要統計、未建立 Voucher Draft、未改正式會計流程。
- P1-MVP-OPS Step 3B-2A：已完成 Guided Purchase Payment Dialog browser smoke close。首次測試遇到 `Used Car Money Flow.flow_type` Select options metadata 尚未同步，執行 migrate / reload-doc 類操作後通過。購車付款可成功建立並顯示於車輛頁收支摘要。
- P1-MVP-OPS Step 3B-3：已完成 Vehicle purchase payment summary polish。車輛頁收支摘要新增「購車付款摘要」，顯示購車價、已記錄購車付款、待付購車款與付款狀態。本階段只做單車摘要，不新增 Dashboard 總餘額、不建立正式會計文件、不改管理毛利成本計算。
- P1-MVP-OPS Step 3B-3B：已完成購車付款摘要位置修正。購車付款摘要由收支摘要上方移至採購 / 買入資料區附近；收支摘要恢復為近 20 筆收支紀錄明細。本階段只調整 UI 掛載位置，不改購車付款計算邏輯、不改 Money Flow service、不新增 Dashboard 總餘額、不改正式會計流程。
- P1-MVP-OPS Step 3B-3C：已完成 Purchase payment summary browser smoke close。購車付款摘要確認位於採購 / 買入資料區附近；購車付款摘要不再出現在收支摘要上方；收支摘要維持尚無收支紀錄或近 20 筆收支紀錄明細；新增購車付款後採購區摘要與收支摘要可更新。本階段不改 runtime、不改 schema、不改正式會計流程。

---

## 5. 目前 UX 邊界

業務頁應顯示：

- 車輛基本資料
- 買入來源
- 購車價
- 收購業務
- 監理 / 稅務 checklist
- 整備 / 維修 / 美容 / 代辦 / 拍場支出
- 購車付款
- 購車付款摘要
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

---

## 6. Metadata sync 注意事項

本階段確認：

```text
即使沒有新增欄位，只要 DocType Select options 有變更，也需要 migrate 或 reload-doc 同步 site DB metadata。
```

本次實際問題：

```text
金流類型 cannot be "購車付款".
```

原因是 repo 已更新 `Used Car Money Flow.flow_type` options，但 site DB metadata 尚未同步。

修正方式：

```bash
cd ~/frappe/frappe-bench
bench --site erpnext-coa.test migrate
bench --site erpnext-coa.test clear-cache
bench restart
```

或小範圍：

```bash
cd ~/frappe/frappe-bench
bench --site erpnext-coa.test reload-doc used_car_erp doctype used_car_money_flow
bench --site erpnext-coa.test clear-cache
bench restart
```

---

## 7. 目前下一步

下一步建議：

```text
P1-MVP-OPS Step 3C：Cash account balance foundation
```

原因：

```text
P1-MVP-OPS Step 3B 採購付款輸入、單車摘要與位置修正已完成 browser smoke close。
下一步可進入資金帳餘額 foundation，但建議先做文件規格，不直接新增 Dashboard runtime。
需先定義期初餘額、已付款 / 部分付款 / 待付款對資金餘額的影響、哪些金流類型進餘額、哪些狀態不進餘額。
仍不改 Journal Entry / Sales Invoice / Payment Entry，不處理 advance account warning，不新增正式會計流程。
```

Step 3C 第一小步建議：

```text
P1-MVP-OPS Step 3C-0：Cash account balance foundation spec
```

建議 commit message：

```text
docs: define cash account balance foundation
```

---

## 8. Historical docs 注意事項

`docs/` 中仍保留大量 P1-ACC、formal-delivery、handoff、smoke 文件。

它們是歷史施工紀錄，不代表目前 UX 主線。

新任務應以 `docs/README.md` 和 active docs 為準。

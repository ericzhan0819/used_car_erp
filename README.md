### Used Car ERP

Used car business operations layer for ERPNext.

### Current Workflow

目前主流程聚焦中古車買賣內部作業：

```text
新增車輛
→ 完成入庫
→ 庫存中
→ 整備中 / 上架中
→ 建立訂金保留
→ 建立訂金金流紀錄
→ 建立訂金傳票草稿
→ 會計作業
→ 待審核傳票草稿
→ 確認訂金入帳
→ 建立正式會計傳票
→ 建立尾款收款
→ 建立尾款金流紀錄
→ 建立尾款傳票草稿
→ 會計確認尾款入帳
→ 建立正式會計傳票
→ 成交前檢查
→ 確認成交
→ 車輛標記已售出
→ 保留單標記已完成
```

目前業務端只建立訂金保留、金流紀錄與傳票草稿；正式會計傳票由會計人員在「會計作業」工作區人工確認後建立。

目前尾款收款仍屬於成交前金流，不會自動交車、出庫、開銷售發票、建立收款單或把車改成已售出。

成交前檢查只驗證訂金與尾款是否都已入帳，不交車、不出庫、不開銷售發票、不建立收款單。

確認成交目前只完成業務狀態轉換，不交車、不出庫、不開銷售發票、不建立收款單、不做收入認列。

確認成交後，車輛會顯示成交摘要，包含成交保留單、訂金金流、訂金傳票、訂金正式會計傳票、尾款金流、尾款傳票與尾款正式會計傳票。

成交摘要只顯示既有流程結果，不代表已完成 ERPNext 正式出庫、銷售發票或收入認列。

正式交車入帳前檢查只做條件驗證，不建立 Sales Invoice、不出庫、不建立沖轉 Journal Entry。

Sales Invoice Draft Foundation 只建立銷售發票草稿，供人工檢查 customer、item、serial_no、warehouse、金額與 update_stock；不提交發票、不出庫、不建立沖轉傳票。

已售出車輛頁已簡化為下一步操作模式；未建立 Sales Invoice 草稿時只顯示建立草稿，已建立後只提供開啟草稿檢查。

Sales Invoice 草稿建立後，已售出車輛頁會提供白話檢查清單，讓使用者確認銷售發票草稿內容後再進入後續正式提交階段。

Tax Metadata Foundation 會先在車輛上收集車源、稅務模式、買入憑證、買入金額與稅務確認狀態；此階段只作資料準備，不作正式稅務計算或入帳。

Tax Metadata Foundation 的日常 UI 採中性稅務確認語氣；正式申報與最終稅務判斷仍需由會計師或稅務人員確認。

Vehicle Cost Summary Foundation 會先記錄單車直接成本，並在車輛上顯示買入金額、累計成本、成交價與預估毛利；此階段只作管理估算，不作正式會計入帳、COGS 或稅務申報。

Vehicle Cost Quick Create UX 允許使用者從車輛頁直接新增單車成本，系統會自動帶入目前車輛；此功能只提升成本紀錄效率，不改變正式會計、庫存或稅務行為。

Vehicle Profit and VAT Estimate Summary Foundation 會在車輛頁顯示單車損益與預估營業稅摘要；此功能只作管理估算，不作正式稅務申報、會計入帳、COGS 或 Sales Invoice submit。

Sold Vehicle Final Checklist Foundation 會在已售出車輛頁彙整成交、收款、傳票、Sales Invoice 草稿、成本、損益與稅務估算狀態；此面板只作 Phase 3 前人工檢查，不會正式提交、出庫、沖轉或入帳。

Formal Delivery Phase 3A Submit Preflight Only 會新增正式交車提交前檢查，用來判斷已售出車輛是否具備未來提交 Sales Invoice 與正式出庫條件；此階段只回傳 gate 結果，不提交、不出庫、不沖轉、不入帳。

Formal Delivery Phase 3A-1 Submit Readiness UX 強化已售出車輛頁的提交前檢查提示，明確區分「檢查通過」與「已正式提交」；此階段仍不提交 Sales Invoice、不出庫、不沖轉、不入帳。

Formal Delivery Phase 3B Submit Sales Invoice Runtime 會在 Phase 3A preflight 通過後，提交既有 Sales Invoice 草稿，並依 ERPNext update_stock 正式出庫；此階段不建立 Payment Entry、不建立 Delivery Note、不手動建立 Stock Entry、不沖轉預收款、不建立 Tax Summary，也不標記正式交車完成。

Formal Delivery Phase 3C Advance Settlement Journal Draft Runtime 會在 Sales Invoice 已提交後建立預收款沖轉 Journal Entry 草稿，用於將已入帳的訂金 / 尾款預收款沖轉至 Sales Invoice 應收帳款；此階段不提交 Journal Entry、不建立 Payment Entry、不建立 Delivery Note、不手動建立 Stock Entry、不建立 Tax Summary，也不標記正式交車完成。

Formal Delivery Phase 3D Submit Advance Settlement Journal Runtime 會在 Phase 3C 建立預收款沖轉 Journal Entry 草稿後，提交該既有 linked Journal Entry；此階段不建立新 Journal Entry、不建立 Payment Entry、不建立 Delivery Note、不手動建立 Stock Entry、不建立 Tax Summary，也不標記正式交車完成。

Used Car Vehicle Simplified UX Phase A/B 已開始將車輛頁從工程式流程頁整理為業務操作頁。第一階段明確化 purchase_price = 購車價，不包含整備、維修、美容、拍場、代辦或其他後續支出；15-1 估算僅以購車價與售車成交價作為估算基礎。已售出車輛頁同一時間僅顯示一個主要下一步操作，相關 Sales Invoice / Journal Entry 以文件連結呈現。

Sold Vehicle Secondary Button Cleanup 已移除已售出車輛頁的成本、損益稅務估算、交車前檢查等次要工程按鈕；已售出車輛頁僅保留一個主要下一步操作與相關文件連結。

Sale Workflow Editability Fix 釐清 business sold state 與 formal accounting locked state。成交價、客戶、售車日期等售車事實在正式會計鎖定前可於售車流程修正；若 Sales Invoice 草稿已存在，需同步更新草稿或阻止不一致儲存。Sales Invoice 已提交後，售車核心欄位不允許直接修改，後續需走修正 / 反轉流程。

Used Car Vehicle Form Layout Refactor Phase A 已將車輛表單改為業務導向分區：基本資料、採購、售車、收支 / 會計狀態、證件 / 稅費、系統連結；成交價移至售車區，購車價 / 底價 / 開價移至採購區，Sales Invoice / Journal Entry 等技術連結集中於收支 / 會計狀態區。

Used Car Vehicle Layout Order Cleanup 已同步 field_order 與 fields[] 實際順序，移除基本資料中的價格摘要殘留，確保購車價 / 底價 / 開價位於採購區、成交價位於售車區、累計支出 / 管理毛利位於收支 / 會計狀態區。

Cancelled Sales Invoice Draft Relink Recovery 會在已售出車輛仍連到 cancelled Sales Invoice、但存在 amended Draft Sales Invoice 時，提供安全修復流程，將 vehicle.sales_invoice relink 到 replacement draft，並在必要時回填 customer / sold_price，避免售車流程編輯被錯誤鎖定。

Hide Healthy Sales Invoice Recovery Button 讓「修復 Sales Invoice 草稿連結」只在 linked Sales Invoice 已取消且存在唯一 amended Draft 時顯示；健康 Draft 狀態不再顯示 recovery 按鈕。

Used Car Vehicle Form Layout Refactor Phase B 新增會計狀態摘要，將訂金 / 尾款 / Sales Invoice / 預收款沖轉狀態以業務語言呈現，並預設隱藏技術欄位，必要時可切換顯示。

Vehicle Delivery / Payment / Accounting Status Boundary Spec 已明確定義交車 / 離場、收款、會計文件三者不可綁死；目前 formal_delivery_status 應理解為會計文件狀態，不代表實體交車或款項收清。

Vehicle Delivery / Payment / Accounting Boundary UI Copy Cleanup 已依交車 / 收款 / 會計文件狀態邊界，將 Used Car Vehicle 上的正式交車入帳、Sales Invoice、預收款沖轉等文案改為較清楚的業務語言；本次不改 runtime、不新增狀態欄位、不做權限限制。

Used Car Role / Permission Boundary Spec 已規劃中古車角色與權限邊界，決策優先沿用 Frappe / ERPNext 內建 User、Role、DocType Permissions、Permission Level、Role Permission Manager、User Permissions 與模組可見性，不自建登入或權限系統。

Used Car Role Permission Inventory Phase P1-A 盤點 custom DocType 目前 permission rows、敏感欄位 permlevel、client-side button hiding 與 server-side gate 現況；本階段只產出文件，不修改 runtime 或實際權限設定。

Used Car Role Records Foundation Phase P1-B 新增中古車業務角色骨架，但不開放 custom DocType 權限、不調整 permlevel、不指派任何使用者；正式權限需等敏感欄位與 server-side action gate 設計完成後再開放。

Decision documents:

- [正式交車 / 出庫 / 銷售文件決策文件](docs/formal-delivery-sales-document-decision.md)
- [台灣中古車稅務與成本設計文件](docs/taiwan-used-car-tax-accounting-design.md)
- [交車 / 收款 / 會計文件狀態邊界文件](docs/vehicle-delivery-payment-accounting-status-boundary-spec.md)
- [中古車角色 / 權限邊界文件](docs/used-car-role-permission-boundary-spec.md)
- [中古車角色 / 權限現況盤點](docs/used-car-role-permission-inventory.md)

Manual QA checklist:

- [訂金保留到會計入帳手動 QA 清單](docs/deposit-accounting-manual-qa-checklist.md)
- [尾款收款金流手動 QA 清單](docs/final-payment-money-flow-manual-qa-checklist.md)

### Installation

You can install this app using the [bench](https://github.com/frappe/bench) CLI:

```bash
cd $PATH_TO_YOUR_BENCH
bench get-app $URL_OF_THIS_REPO --branch develop
bench install-app used_car_erp
```

### Contributing

This app uses `pre-commit` for code formatting and linting. Please [install pre-commit](https://pre-commit.com/#installation) and enable it for this repository:

```bash
cd apps/used_car_erp
pre-commit install
```

Pre-commit is configured to use the following tools for checking and formatting your code:

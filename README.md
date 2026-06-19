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

Used Car Field Permlevel Design Phase P1-C 定義中古車欄位層級：Level 0 一般營運欄位、Level 1 價格 / 成本 / 毛利欄位、Level 2 會計文件連結 / 會計金額、Level 3 稅務審核 / 例外修復欄位；本階段只產出文件，不改 DocType JSON、不開放權限。

Used Car Field Permlevel Application Phase P1-D-A 依欄位權限層級設計，將價格 / 成本 / 毛利、會計文件連結與會計金額移出 permlevel 0；本階段只保留 System Manager 可存取高層級欄位，不開放中古車業務角色、不改 runtime。

Used Car Voucher Draft Line Note Permlevel Cleanup Phase P1-D-A-1 將實際存在的 `note` 欄位移至 permlevel 2，並修正設計文件中 placeholder `remarks` 與實際 fieldname 不一致的問題；本次不開放任何中古車業務角色權限、不改 runtime。

Used Car DocType Permission Rows Phase P1-E-1 已依 P1-E 設計套用最小 DocType permission rows，開放中古車角色基礎 read/report 與少量低風險 write；不開放 submit/cancel/amend/delete/export，不給 Sales/Procurement/Preparation 高層級敏感欄位，高風險業務動作仍需 P1-F server-side action gates。

Used Car Server-side Action Gate Foundation Phase P1-F-0/P1-F-1 新增 action-based server-side permission gate 設計與 helper skeleton，將高風險業務動作從 DocType write 中獨立出來；本階段不改 runtime service 行為、不新增 DocType、不新增 patch、不修改 ERPNext core，後續 P1-F-2 才會逐步接入 create reservation、money flow、voucher confirm、Sales Invoice draft 等 whitelisted methods。

Used Car Server-side Action Gate Adoption Phase P1-F-2 已將 action-based server-side permission gate 接入第一批高風險 service methods，包含保留單建立 / 取消 / 成交確認、訂金與尾款金流建立、傳票草稿確認 / 退回 / 作廢；本階段只做 gate adoption，不修改 DocType JSON、不新增 Role、不新增 patch、不放寬 DocPerm、不加入 controlled write bypass。

Used Car Controlled Write Bypass Design Phase P1-F-3 定義 action-gated、service-owned、workflow-specific、field-constrained controlled writes；本階段只新增設計文件，不修改 runtime，不放寬 DocPerm，不新增 patch，第一批建議只處理 sales reservation flow，不碰 Sales Invoice、Journal Entry、Stock Entry、tax metadata 或 accounting-link repair。

Used Car Controlled Write Bypass Phase P1-F-3-A 已將 sales reservation flow 接上 service-controlled writes，使通過 action gate 的 Sales / Manager / Owner 可透過服務流程建立保留單、訂金 / 尾款金流、自動產生對應傳票草稿、取消保留與確認成交；本階段仍不放寬 DocPerm、不修改 DocType JSON、不新增 Role、不碰 Sales Invoice / Journal Entry / Stock Entry / 稅務 / 成本敏感流程。

Sales Reservation Controlled Write Manual QA Phase P1-F-3-A-QA 新增 sales reservation flow 手動 QA 清單，用於驗證 Sales / Manager / Owner 可透過 service workflow 完成保留、金流、取消與成交確認，同時確認 Sales 不能越權確認傳票、建立 Sales Invoice、修改敏感欄位或直接操作會計 / 庫存文件。

Used Car Vehicle Reserved State UX Cleanup Phase P1-UX-1 簡化保留中車輛頁，將畫面聚焦於目前狀態、下一步、建立尾款收款、取消保留，以及會計確認後才顯示成交前檢查 / 確認成交；本階段只改前端表單 UX，不改 runtime service、DocType JSON、DocPerm、Role、patch 或 ERPNext core。

Used Car Vehicle Reserved Status Source Fix Phase P1-UX-1A 修正保留中狀態卡資料來源，改由 active Used Car Reservation 解析訂金 / 尾款金流、傳票草稿與 Journal Entry 狀態，不再用 Vehicle completion summary 欄位誤判保留中階段的入帳狀態；本階段不改 DocType JSON、不改 permission、不改 controlled write、不回填 Vehicle 成交摘要。

P1-TAX-0：Simplified Vehicle Tax Evidence Boundary 已將車輛頁稅務邊界簡化為買入憑證判斷：`purchase_document_type = 統一發票` 推導 `一般發票扣抵`；未取得、買賣合約、讓渡書、匯款紀錄、收據推導 `15-1 特殊扣抵`；拍場、其他或空值會阻擋 Sales Invoice 草稿建立直到會計確認。車輛頁不再把稅額估算作為主要 workflow card 顯示，且本階段尚未 wiring Sales Invoice tax template，保留給 P1-TAX-1。

P1-ACC-1：Taiwan Accounting Item Code DocType + MVP Seed 新增台灣官方會計項目代號 master data，使用官方 code 作為唯一鍵，允許相同中文名稱對應不同代號，例如 `0100005 營業成本` 與 `0300090 營業成本` 可同時存在；本階段不修改 ERPNext Chart of Accounts、不 disable root account、不建立 Account mapping、不影響 Sales Invoice / Journal Entry runtime。

P1-ACC-2：Taiwan Accounting Item Account Mapping DocType 新增 ERPNext Account 到台灣官方會計項目代號的 mapping layer，使用官方 code/document name 作為對應鍵，允許相同中文名稱不同代號並存；mapping 只接受同公司、非群組、未停用 ERPNext Account，並限制同一公司同一用途的 active default mapping 唯一。本階段不修改 Chart of Accounts、不 disable root account、不影響 Sales Invoice / Journal Entry / GL runtime。

P1-ACC-4：Taiwan Full Chart of Accounts Source Catalog 新增 113 年度台灣會計項目完整 source catalog 設計與驗證，準備後續產生 ERPNext Chart of Accounts Importer 檔案；本階段不匯入 Chart of Accounts、不停用 Account、不修改 tabAccount、不影響 Sales Invoice / Journal Entry / GL runtime。

P1-ACC-5：Taiwan Full Chart of Accounts Importer File 依 P1-ACC-4 source catalog 產生 ERPNext Chart of Accounts Importer 檔案與 preview / validation；本階段只產出檔案，不執行匯入、不停用 Account、不修改 tabAccount、不影響 Sales Invoice / Journal Entry / GL runtime。

P1-ACC-6A：Chart of Accounts Import Preflight 新增匯入前只讀檢查、現有 Account 備份、會計 / 庫存資料數量盤點與 gate report；本階段不匯入 Chart of Accounts、不停用 Account、不修改 tabAccount、不影響 Sales Invoice / Journal Entry / GL runtime。

P1-ACC-6E：Minimal Accounting / Stock Setup QA 新增 `erpnext-coa.test` / `OO` 最小會計與庫存設定檢查，僅建立 Draft Sales Invoice 驗證 master data；不 submit、不產生 GL Entry、不產生 Stock Ledger Entry、不修改 COA。

P1-ACC-6F-A：Submitted Sales Invoice Preflight Only 新增 Draft Sales Invoice 提交前只讀檢查，確認 Sales Invoice / item / serial_no / warehouse / tax / account 與 baseline counts；不 submit、不建立 GL Entry、不建立 Stock Ledger Entry、不補 serial_no、不修改正式流程。

P1-TAX-1-A / P1-ACC-6F-B：正式 Used Car Vehicle 流程建立 Sales Invoice 草稿時，固定套用 `台灣營業稅 5%（含稅） - O`，並從 Sales Taxes and Charges Template 複製單筆銷項稅 row；若 template 或 tax account 設定錯誤會阻擋草稿建立，由人工修 master data，不由 runtime 自動修。本階段仍不 submit、不建立 GL Entry / Stock Ledger Entry、不建立 Payment Entry / Journal Entry / Delivery Note / Stock Entry、不修改 COA。

P1-ACC-6F-B-1：新增正式 Used Car Vehicle flow 的 Draft Sales Invoice 只讀 preflight target，可從 `Used Car Vehicle.sales_invoice` 找到最新 formal draft 並排除 P1-ACC-6E QA draft；找不到時回傳 fail / not found，不建立資料、不修資料、不 submit。P1-ACC-6F-C 前仍不建立 GL Entry / Stock Ledger Entry。

P1-ACC-6F-B-2：新增正式 Sales Invoice 草稿建立前只讀 readiness inspector，檢查已售出車輛、已完成保留單、訂金 / 尾款金流與傳票、Item / Serial No / Warehouse、稅務模板與收入科目是否具備呼叫 `create_sales_invoice_draft_for_vehicle()` 的條件；本階段不呼叫會 backfill 的 formal delivery preflight、不建立 Sales Invoice 草稿、不 submit、不修改資料，只用來在 P1-ACC-6F-C 前找出資料缺口。

P1-ACC-6F-B-3：新增受 readiness gate 保護的正式 Draft Sales Invoice 建立 QA runner；只有 readiness pass 時才呼叫 `create_sales_invoice_draft_for_vehicle()` 建立草稿，建立後檢查 Sales Invoice、tax row、item row、counts 與 formal preflight。此階段不 submit、不建立 GL Entry / Stock Ledger Entry、不處理 Payment Entry / Journal Entry / Delivery Note / Stock Entry；若沒有候選或 readiness 未通過，blocked 是正確結果。

P1-ACC-6F-C-0：新增 submitted Sales Invoice submit gate snapshot，針對最新正式 Draft Sales Invoice 或指定 Sales Invoice 讀取 submit 前欄位、linked Used Car Vehicle、baseline counts 與 submitted preflight 結果，只回答是否可安排 P1-ACC-6F-C real submit test；本階段不 submit、不建立 draft、不修資料、不建立 GL Entry / Stock Ledger Entry。

P1-ACC-6F-C-0A：修正 submit preflight baseline semantics，將 P1-ACC-6E QA draft 的 clean-site expected baseline 與正式 Used Car Vehicle draft 的 observe-only baseline 分開；formal flow 前置 Stock Entry / Journal Entry 造成的 GL / Stock Ledger counts 不再視為 formal draft payload warning，但 submitted Sales Invoice count > 0 仍是第一張 submitted QA 污染風險。

P1-ACC-6F-C-0B：新增 formal submit fixture setup service，只允許在 `erpnext-coa.test` 且 submitted Sales Invoice count 為 0 時，透過既有正式中古車 service 建立完整 formal flow 測試 fixture 與 Draft Sales Invoice，並執行 submit gate snapshot；本階段不是 submit，不清理 fixture，保留草稿給下一階段 P1-ACC-6F-C real submit test。

P1-ACC-6F-C-0B-1：修正正式車輛入庫 Material Receipt 的 Stock Entry Difference Account gate；若 `Company.stock_adjustment_account` 缺失，runtime 可在 `Stock Entry Detail.expense_account` 使用既有 fallback expense account `0100005-UC - 中古車銷貨成本 - O`。本階段不 submit Sales Invoice、不修改 COA、不建立或啟停 Account。

P1-ACC-6F-C-0B-2：formal submit fixture setup 可安全續跑半套 fixture，不清理、不重建、不建立第二套 fixture，而是用既有正式 service 從目前車輛狀態補到 Draft Sales Invoice 與 submit gate snapshot；本階段仍不 submit Sales Invoice。

P1-ACC-6F-C：新增 guarded formal Sales Invoice submit QA，只允許在 `erpnext-coa.test`、confirmation token 正確且 submit gate snapshot 通過時提交一張 formal fixture Draft Sales Invoice。此階段會造成 ERPNext 原生 GL Entry / Stock Ledger Entry，但不建立 Payment Entry / Delivery Note / Purchase Invoice、不做預收款沖轉、不回寫 `formal_delivery_status = 已完成`。

P1-ACC-6F-D：新增 Sales Invoice submit 後正式交車狀態同步，只在 submitted Sales Invoice 已有 ERPNext 原生 GL Entry / Stock Ledger Entry 後，將 linked Used Car Vehicle 的會計文件狀態從 `銷售發票草稿` 同步為 `已完成`；本階段不是 submit、不處理預收款沖轉、不建立 Journal Entry / Payment Entry / Delivery Note / Purchase Invoice / Stock Entry。

P1-ACC-6G-0：新增預收款沖轉 readiness inspector，檢查已提交 Sales Invoice、已完成正式交車會計狀態、已入帳訂金 / 尾款金流與 Journal Entry 是否可進入下一階段預收款沖轉建立；本階段只回傳 gate report 與 settlement preview，不建立或提交 Journal Entry，不修改任何文件，不使用 15-1 稅務估算或成本資料作為沖轉依據。

P1-ACC-6G-1：新增 guarded advance settlement Journal Entry QA，只允許在 `erpnext-coa.test` 且 confirmation token 正確時，根據 P1-ACC-6G-0 readiness preview 建立並提交一張預收款沖轉 Journal Entry，將已入帳訂金 / 尾款預收款轉沖 submitted Sales Invoice 應收帳款；本階段不建立 Payment Entry / Delivery Note / Purchase Invoice / Sales Invoice，不修改 Sales Invoice / Money Flow / Voucher Draft / Reservation，且只透過 controlled write 回寫 `Used Car Vehicle.advance_settlement_journal_entry`。

P1-ACC-6H-0：新增 formal sale accounting closure inspector，集中只讀檢查已售出車輛、submitted Sales Invoice、Sales Invoice GL / SLE、advance settlement Journal Entry、訂金 / 尾款金流與傳票鏈，以及非本流程文件是否為 0；本階段不建立、不提交、不修改任何文件，不處理 UI、15-1 稅務公式或整備 / 維修 / 美容 / 拍場 / 代辦費。

P1-ACC-6H-0 formal accounting closure inspector 已完成，正式售車會計閉環已可通過只讀檢查；下一階段轉向 UX / tax boundary，不再繼續增加 accounting runtime。

P1-UX-TAX-0：新增 Used Car Vehicle 簡化 UX 與 15-1 稅務邊界規格，明確定義車輛頁應收斂為基本資料、採購、售車、收支四個業務區塊，會計文件與 ledger 技術細節移往會計作業；15-1 只用在售車營業稅估算，`purchase_price` 只代表購車價，不包含整備、維修、美容、拍場、代辦或其他後續費用。

P1-UX-TAX-1：Used Car Vehicle 表單已開始依 P1-UX-TAX-0 重整為基本資料、採購、售車、收支、會計狀態、更多資訊六個業務語意區塊；本階段只修改 DocType layout 與文件，沒有 runtime 行為變更。

P1-UX-TAX-2：新增 Vehicle Accounting Status Summary Inspector，提供車輛頁可使用的 read-only 會計狀態摘要、單一下一步與摘要卡片；本階段沒有 write behavior，不新增按鈕、不修改 JS、不修改 DocType JSON。

Decision documents:

- [正式交車 / 出庫 / 銷售文件決策文件](docs/formal-delivery-sales-document-decision.md)
- [台灣中古車稅務與成本設計文件](docs/taiwan-used-car-tax-accounting-design.md)
- [交車 / 收款 / 會計文件狀態邊界文件](docs/vehicle-delivery-payment-accounting-status-boundary-spec.md)
- [中古車角色 / 權限邊界文件](docs/used-car-role-permission-boundary-spec.md)
- [中古車角色 / 權限現況盤點](docs/used-car-role-permission-inventory.md)
- [中古車欄位權限層級設計](docs/used-car-field-permlevel-design.md)
- [中古車 Server-side Action Gate 設計](docs/used-car-server-side-action-gate-design.md)
- [中古車 Controlled Write Bypass 設計](docs/used-car-controlled-write-bypass-design.md)
- [台灣會計項目代號 Seed 設計](docs/taiwan-accounting-item-code-seed-design.md)
- [台灣會計項目代號 Account Mapping 設計](docs/taiwan-accounting-item-account-mapping-design.md)
- [台灣完整 Chart of Accounts 匯入設計](docs/taiwan-full-chart-of-accounts-import-design.md)
- [台灣完整 Chart of Accounts Source Catalog](docs/taiwan-full-chart-of-accounts-source-catalog.md)
- [台灣完整 Chart of Accounts Importer 檔案](docs/taiwan-full-chart-of-accounts-importer-file.md)
- [台灣 Chart of Accounts 匯入前檢查](docs/taiwan-chart-of-accounts-import-preflight.md)
- [P1-ACC-6E Minimal Accounting / Stock Setup QA](docs/p1-acc-6e-minimal-accounting-stock-setup-qa.md)
- [P1-ACC-6F-A Submitted Sales Invoice Preflight Only](docs/p1-acc-6f-a-submitted-sales-invoice-preflight.md)
- [P1-TAX-1-A Sales Invoice Tax Template Runtime](docs/p1-tax-1-a-sales-invoice-tax-template-runtime.md)
- [P1-ACC-6F-B-1 Formal Vehicle Sales Invoice Preflight Target](docs/p1-acc-6f-b-1-formal-vehicle-sales-invoice-preflight-target.md)
- [P1-ACC-6F-B-2 Formal Sales Invoice Draft Readiness Inspector](docs/p1-acc-6f-b-2-formal-sales-invoice-draft-readiness-inspector.md)
- [P1-ACC-6F-B-3 Guarded Formal Sales Invoice Draft Creation QA](docs/p1-acc-6f-b-3-guarded-formal-sales-invoice-draft-creation-qa.md)
- [P1-ACC-6F-C-0 Submitted Sales Invoice Submit Gate Snapshot](docs/p1-acc-6f-c-0-submitted-sales-invoice-submit-gate-snapshot.md)
- [P1-ACC-6F-C-0A Split QA And Formal Preflight Baseline Semantics](docs/p1-acc-6f-c-0a-split-qa-and-formal-preflight-baseline-semantics.md)
- [P1-ACC-6F-C-0B Formal Submitted Sales Invoice Test Fixture Setup](docs/p1-acc-6f-c-0b-formal-submitted-sales-invoice-test-fixture-setup.md)
- [P1-ACC-6F-C-0B-1 Vehicle Stock Entry Difference Account Gate](docs/p1-acc-6f-c-0b-1-vehicle-stock-entry-difference-account-gate.md)
- [P1-ACC-6F-C-0B-2 Resume Half-Created Formal Submit Fixture](docs/p1-acc-6f-c-0b-2-resume-half-created-formal-submit-fixture.md)
- [P1-ACC-6F-C Guarded Formal Sales Invoice Submit QA](docs/p1-acc-6f-c-guarded-formal-sales-invoice-submit-qa.md)
- [P1-ACC-6F-D Post-submit Formal Delivery Status Sync](docs/p1-acc-6f-d-post-submit-formal-delivery-status-sync.md)
- [P1-ACC-6G-0 Advance Settlement Readiness Inspector](docs/p1-acc-6g-0-advance-settlement-readiness-inspector.md)
- [P1-ACC-6G-1 Guarded Advance Settlement Journal Entry QA](docs/p1-acc-6g-1-guarded-advance-settlement-journal-qa.md)
- [P1-ACC-6H-0 Formal Sale Accounting Closure Inspector](docs/p1-acc-6h-0-formal-sale-accounting-closure-inspector.md)
- [P1-UX-TAX-0 Used Car Vehicle Simplified UX And 15-1 Tax Boundary Spec](docs/p1-ux-tax-0-used-car-vehicle-simplified-ux-and-15-1-tax-boundary-spec.md)
- [P1-UX-TAX-1 Used Car Vehicle Form Section Layout Refactor](docs/p1-ux-tax-1-used-car-vehicle-form-section-layout-refactor.md)
- [P1-UX-TAX-2 Vehicle Accounting Status Summary Inspector](docs/p1-ux-tax-2-vehicle-accounting-status-summary-inspector.md)

Manual QA checklist:

- [訂金保留到會計入帳手動 QA 清單](docs/deposit-accounting-manual-qa-checklist.md)
- [尾款收款金流手動 QA 清單](docs/final-payment-money-flow-manual-qa-checklist.md)
- [Sales Reservation Controlled Write 手動 QA 清單](docs/sales-reservation-controlled-write-manual-qa-checklist.md)

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

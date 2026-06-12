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

Decision documents:

- [正式交車 / 出庫 / 銷售文件決策文件](docs/formal-delivery-sales-document-decision.md)
- [台灣中古車稅務與成本設計文件](docs/taiwan-used-car-tax-accounting-design.md)

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

# P1-MVP-OPS Step 3A-5：Cash Account Runtime Close / Handoff

日期：2026-06-29
專案：Used Car ERP / ERPNext / Frappe
Repo：`ericzhan0819/used_car_erp`

## 1. 本文件目的

本文件執行 `P1-MVP-OPS Step 3A-5：Cash Account Runtime Close / Handoff`。

此階段是 Step 3A Minimal Cash Account Runtime 的文件收尾與交接；不修改 Python runtime、JavaScript runtime、DocType JSON、patch 或會計流程。

## 2. 結論

Step 3A 已完成一個可交接段落：

```text
資金帳戶最小模型
Money Flow 欄位 foundation
Money Flow service 寫入資金欄位
新增支出 / 訂金 / 尾款 / 退款 Dialog 接線
車輛頁收支摘要顯示資金帳戶 / 收付狀態 / 交易對象
保留 / 成交流程同步車輛售車摘要欄位
```

目前業務輸入每一筆收款 / 付款時，系統已能記錄金額、日期、收付方式、實際資金帳戶、收付狀態、交易對象與所屬車輛。

## 3. 已完成範圍

- `Used Car Cash Account` DocType foundation。
- `Used Car Money Flow.cash_account`。
- `Used Car Money Flow.settlement_status`。
- `Used Car Money Flow.counterparty_name`。
- `VehicleMoneyFlowService` 已支援一般支出、訂金、尾款與退款的資金欄位。
- 車輛頁 inline 收支摘要已顯示日期、類型、金額、收付、帳戶、對象、憑證與金流狀態。
- 收支摘要 render timing、掛載位置與重複 render 問題已處理。
- 保留 / 成交流程已同步 `customer`、`sold_price`、`reserved_date`、`sales_staff`、`sales_note`、`sold_date`。

## 4. 明確未做範圍

Step 3A 不包含：

```text
現金 / 銀行餘額 Dashboard
資金帳戶報表
採購付款 Money Flow runtime
刷卡未撥款
私人代墊
多銀行管理 UI
部分收付明細
資金轉帳
月結批次付款
Journal Entry / Sales Invoice / Payment Entry 重構
advance account warning 處理
Money Flow 與 Vehicle Cost 整合
記帳士交接包
成交結案列印
```

## 5. 建議 smoke 清單

後續若做 browser smoke，建議驗證：

1. 新增支出可輸入收付狀態、資金帳戶與交易對象，車輛頁摘要正確顯示。
2. 收訂金並保留可輸入收款狀態與資金帳戶，交易對象由客戶資料推導。
3. 收尾款可輸入收款狀態與資金帳戶，摘要正確顯示。
4. 取消保留 / 退款可輸入退款狀態與退款資金帳戶。
5. 車輛頁重新整理後收支摘要不消失、不重複 render。

## 6. 下一步建議

Step 3A close 後，建議進入：

```text
P1-MVP-OPS Step 3B：採購付款 Money Flow
```

原因：`purchase_price` 只代表購車價；實際購車款何時付、怎麼付、從哪個資金帳戶付，仍需要進 Money Flow。若不補採購付款，現金 / 銀行餘額會缺最大的一類支出。

Step 3B 必須注意：購車付款進 Money Flow，但不可讓管理毛利重複扣除 `purchase_price`。

建議 commit message：

```text
feat: add purchase payment money flow task card
```

## 7. 交接摘要

```text
P1-MVP-OPS Step 3A Minimal Cash Account Runtime 已收尾。
資金帳戶最小資料層已可支撐後續現金 / 銀行 / 待收 / 待付統計。
支出、訂金、尾款、退款已具備資金帳戶與收付狀態。
車輛頁收支摘要已顯示資金帳戶、收付狀態與交易對象。
下一步建議做 Step 3B：採購付款 Money Flow。
```

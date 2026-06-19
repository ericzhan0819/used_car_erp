# P1-UX-TAX-4 Vehicle Management Profit Summary Read-only Service

Last reviewed: 2026-06-19

Phase: `P1-UX-TAX-4`

## 1. 任務背景

P1-UX-TAX-0 已定義 Used Car Vehicle 簡化 UX 與 15-1 tax boundary，明確區分車輛業務頁、會計文件與售車營業稅估算。

P1-UX-TAX-3 已完成 15-1 read-only estimate，以 `purchase_price` 購車價與售車成交價估算售車營業稅，不納入整備、維修、美容、拍場或代辦費。

本任務補上管理損益 summary，讓車輛頁或後續 dashboard 可 read-only 取得老闆看真實賺多少的單車管理毛利。

## 2. 管理損益公式

```text
成交價
- 購車價
- 直接成本
+ 其他直接收入
= 管理毛利
```

其中：

```text
成交價 = Used Car Vehicle.sold_price 或 linked Sales Invoice grand_total
購車價 = Used Car Vehicle.purchase_price
直接成本 = Used Car Vehicle Cost 金額加總，不包含 purchase_price
其他直接收入 = 明確不是訂金 / 尾款 / 貸款撥款的額外收入
管理毛利率 = 管理毛利 / 成交價
```

若車輛尚未售出，service 可回傳成本摘要與 warning，但 `management_gross_profit` 會標示為尚不可完整計算。

## 3. 管理損益 vs 15-1

管理損益與 15-1 是兩套不同用途的數字。

管理損益用於內部經營判斷，可以包含：

```text
整備費
維修費
美容費
拍場費
代辦費
其他直接支出
```

15-1 只用於售車營業稅估算，不包含上述後續支出。`purchase_price` 的語意仍固定為購車價，不得回頭混入整備、維修、美容、拍場、代辦或其他後續支出。

## 4. 訂金 / 尾款收入邊界

訂金收款、尾款收款與貸款撥款只是售車價的收款形式，不是額外收入。

管理損益以 `sold_price` 或 Sales Invoice `grand_total` 作為售車收入基礎，因此訂金 / 尾款不可再次加回收入，避免重複計算。

## 5. Read-only Boundary

本 service 嚴格 read-only。

本階段不建立、不提交、不取消、不刪除、不修改任何文件，不寫回 `Used Car Vehicle`、`Used Car Vehicle Cost`、`Reservation`、`Money Flow`、`Voucher Draft`、`Sales Invoice`、`Journal Entry`、`GL Entry`、`Stock Ledger Entry` 或 Workspace。

本 service 可以 read-only 呼叫 `Vehicle151TaxEstimateService` 取得 15-1 摘要，但管理毛利公式不得扣 15-1 稅額。若回傳 `after_estimated_business_tax_profit_preview`，它只是 preview，不是主要管理毛利。

## 6. Non-goals

本階段不做：

```text
不做 JS
不做 dashboard
不做 DocType JSON
不做正式財報
不做稅務申報
不新增按鈕
不修改 Workspace
不建立或提交任何 ERPNext 文件
```

## 7. 後續

後續建議階段：

```text
P1-UX-TAX-5：Accounting Workspace Dashboard Cleanup
```

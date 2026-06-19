# P1-UX-TAX-3 Vehicle 15-1 Tax Estimate Read-only Service

Last reviewed: 2026-06-19

Phase: `P1-UX-TAX-3`

## 1. 任務背景

P1-UX-TAX-0 已定義 Used Car Vehicle 簡化 UX 與 15-1 tax boundary，明確區分車輛業務頁、會計文件與售車營業稅估算。

P1-UX-TAX-1 已整理 Vehicle form layout，將車輛頁收斂為基本資料、採購、售車、收支、會計狀態與更多資訊。

P1-UX-TAX-2 已提供 read-only accounting status summary，讓車輛頁可取得簡化會計狀態、單一下一步與摘要卡片。

本任務新增 read-only 15-1 tax estimate service，提供售車稅務估算資料來源；本階段不改 UI、不寫回 Vehicle、不建立 Sales Invoice / Journal Entry。

## 2. 15-1 核心規則

15-1 只用在售車營業稅估算。

`purchase_price = 購車價`。

`purchase_price` 不包含：

```text
整備費
維修費
美容費
拍場費
代辦費
其他後續支出
```

整備、維修、美容、拍場、代辦費只能用於管理損益，不得進入 15-1 購入成本。

## 3. 公式

```text
售車銷項稅額 = 售車價 ÷ 1.05 × 5%
15-1 購入可扣抵稅額 = 購車價 ÷ 1.05 × 5%
實際可扣抵 = min(購入可扣抵稅額, 銷項稅額)
預估本車營業稅 = 銷項稅額 - 實際可扣抵
```

service 回傳 raw 金額保留 2 位小數，display 金額四捨五入到整數台幣。

## 4. 315000 / 378000 範例

```text
購車價：315,000
15-1 購入可扣抵稅額 = 315,000 ÷ 1.05 × 5% = 15,000

售車價：378,000
售車銷項稅額 = 378,000 ÷ 1.05 × 5% = 18,000

實際可扣抵 = min(15,000, 18,000) = 15,000
預估本車營業稅 = 18,000 - 15,000 = 3,000
```

## 5. Read-only Boundary

本 service 嚴格 read-only。

本階段不建立、不提交、不取消、不刪除、不修改任何文件，不寫回 `Used Car Vehicle`、`Used Car Vehicle Cost`、`Reservation`、`Money Flow`、`Voucher Draft`、`Sales Invoice`、`Journal Entry`、`GL Entry` 或 `Stock Ledger Entry`。

本 service 不讀 `Used Car Vehicle Cost` 作為 15-1 purchase price，不使用整備、維修、美容、拍場、代辦或其他後續支出推導 15-1 購入成本。

## 6. Non-goals

本階段不做：

```text
不做 JS
不做 dashboard
不做 DocType JSON
不做管理損益 runtime
不做電子發票
不做稅務申報
不新增按鈕
不修改 Workspace
不建立或提交任何 ERPNext 文件
```

## 7. 後續

後續建議階段：

```text
P1-UX-TAX-4：Vehicle Management Profit Summary
P1-UX-TAX-5：Accounting Workspace Dashboard Cleanup
```

# P1-UX-TAX-2 Vehicle Accounting Status Summary Inspector

Last reviewed: 2026-06-19

Phase: `P1-UX-TAX-2`

## 1. 任務背景

P1-UX-TAX-1 已完成 `Used Car Vehicle` form section layout，車輛頁已整理為基本資料、採購、售車、收支、會計狀態、更多資訊。

本任務補上可供 Vehicle 頁使用的 read-only accounting status summary，將正式售車會計流程濃縮成單一業務狀態、單一下一步與簡單摘要卡片。本階段只新增 inspector service，不新增 UI、不寫回 Vehicle 欄位。

## 2. 狀態定義

狀態摘要只回傳下列業務狀態之一：

```text
未開始
待會計確認
已建立發票草稿
發票已提交
預收款已沖轉
會計閉環完成
需補資料
錯誤需處理
```

`會計閉環完成` 代表車輛已售出、Sales Invoice 已提交、formal delivery accounting status 已完成、預收款沖轉 Journal Entry 已提交、Sales Invoice outstanding amount 歸零，且 formal sale accounting closure inspector pass。

`預收款已沖轉` 代表 advance settlement Journal Entry 已提交，但 closure inspector 尚未 pass，或仍有需要 review 的 closure gate。

`錯誤需處理` 用於 Sales Invoice / Journal Entry 已取消、linked 文件不存在、submitted accounting document 缺 GL / SLE，或 closure inspector 回報會計側 blocking errors。

`需補資料` 用於已售出但缺 customer、缺 completed reservation、必要連結缺失或 business link / customer mismatch 等需人工補資料情境。

## 3. 下一步規則

同一時間只回傳一個 next action：

```text
next_action_code
next_action_label
next_action_area
```

若狀態為 `會計閉環完成`，`next_action_code = None`、`next_action_label = 無下一步`、`next_action_area = None`。

其他狀態依目前最接近的 gate 回傳單一下一步，例如確認金流入帳、提交售車發票、同步正式交車狀態、建立預收款沖轉、檢查會計閉環、補齊售車資料或檢查會計異常。

## 4. Read-only Boundary

本 service 嚴格 read-only。

本階段不建立、不提交、不取消、不刪除、不修改任何文件，不寫回 `Used Car Vehicle`、`Reservation`、`Money Flow`、`Voucher Draft`、`Sales Invoice`、`Journal Entry`、`GL Entry` 或 `Stock Ledger Entry`。

允許的行為只有讀取 target vehicle、linked accounting documents、money flow / voucher / journal status、GL / SLE count，以及呼叫既有 read-only formal sale accounting closure inspector。

## 5. Non-goals

本階段不做：

```text
不做 JS
不做 dashboard
不做 DocType JSON
不做 15-1 runtime
不做管理損益 runtime
不新增按鈕
不新增欄位
不修改 Workspace
不建立或提交任何 ERPNext 文件
```

## 6. 後續

後續建議階段：

```text
P1-UX-TAX-3：15-1 Estimate Read-only Service
P1-UX-TAX-4：Vehicle Management Profit Summary
P1-UX-TAX-5：Accounting Workspace Dashboard Cleanup
```

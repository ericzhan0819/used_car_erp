# P1-UX-TAX-1 Used Car Vehicle Form Section Layout Refactor

Last reviewed: 2026-06-19

Phase: `P1-UX-TAX-1`

## 1. 任務背景

P1-UX-TAX-0 已完成 Used Car Vehicle 簡化 UX 與 15-1 稅務邊界規格。正式售車會計閉環已跑通後，accounting runtime 暫停擴張，下一階段改以車輛頁業務語意整理為主。

本任務是 P1-UX-TAX-0 後第一個最小 DocType layout 實作，只重整 `Used Car Vehicle` 表單區塊，讓車輛頁更接近業務操作語言。

## 2. 修改範圍

本階段只修改：

```text
Used Car Vehicle DocType JSON
README / current-state / 本任務文件
```

不新增 Python service，不修改既有 Python runtime，不修改 Workspace JSON，不修改 JS，不新增 test。

## 3. 新表單區塊

`Used Car Vehicle` 表單區塊整理為：

```text
基本資料
採購
售車
收支
會計狀態
更多資訊
```

基本資料放車輛本體資料，例如車牌、VIN / 車身號碼、品牌、車型、年份、顏色、里程、排氣量、燃料、變速系統、車輛狀態與備註。

採購放買進車輛資料，例如 `purchase_price`、車源類型、買入日期、買入憑證、採購備註與採購相關資訊。

售車放賣車資料與簡單銷售狀態，例如成交價、客戶、成交日期、售車稅務模式與售車備註。

收支本階段只保留既有成交與金流摘要，不新增收支 child table，也不新增金流輸入 UI。

會計狀態只放簡單狀態與文件連結，例如 `formal_delivery_status`、`sales_invoice`、`advance_settlement_journal_entry`、處理日期與完成人員。此區塊預設為可折疊，避免會計文件細節佔滿主要表單。

更多資訊放工程、audit、link 與歷史欄位，例如 ERPNext Item、Serial No、Stock Entry、Purchase Invoice、監理 / 稅費旗標與內部備註。此區塊預設為可折疊。

## 4. 15-1 邊界

`purchase_price = 購車價`。

`purchase_price` 不包含：

```text
整備費
維修費
美容費
拍場費
代辦費
其他後續費用
```

15-1 只用於售車營業稅估算。`purchase_price` 作為 15-1 購入可扣抵稅額估算基礎，不代表完整單車管理成本，也不取代正式稅務申報或會計師判斷。

## 5. Non-goals

本階段不做：

```text
不做 runtime
不做 service
不做 JS
不做 Workspace
不做 migrate
不新增按鈕
不改會計流程
不新增 15-1 計算欄位
不改欄位資料型別
不改欄位名稱
不刪除欄位
不改權限 / permlevel
```

## 6. 後續

後續建議階段：

```text
P1-UX-TAX-2：Vehicle Page Accounting Status Summary
P1-UX-TAX-3：15-1 Estimate Read-only Service
P1-UX-TAX-4：Vehicle Management Profit Summary
P1-UX-TAX-5：Accounting Workspace Dashboard Cleanup
```

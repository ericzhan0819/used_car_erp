# P1-MVP-OPS Step 2：Money Flow 主帳欄位盤點

日期：2026-06-25  
專案：Used Car ERP / ERPNext / Frappe  
Repo：`ericzhan0819/used_car_erp`  
本機路徑：`~/frappe/frappe-bench/apps/used_car_erp`  
前置文件：`docs/p1-mvp-ops-used-car-operation-ledger-direction.md`

---

## 1. 本文件目的

本文件執行：

```text
P1-MVP-OPS Step 2：Money Flow 主帳欄位盤點
```

目標是確認目前 `Used Car Money Flow` 是否足以承接新的 MVP 主線：

```text
車行營運管理帳
+ 資金帳
+ 單車損益
+ 文件檢查
+ 成交結案列印
+ 記帳士交接包
```

本階段只做文件盤點，不改 runtime、不改 schema、不新增 DocType、不跑 migrate。

---

## 2. 本階段範圍

### 2.1 本階段有做

盤點：

```text
Used Car Money Flow DocType 欄位
VehicleMoneyFlowService 建立來源
VehicleVoucherService 與 Money Flow 狀態同步
Used Car Vehicle 車輛頁 inline 收支摘要
VehicleManagementProfitSummaryService 對 Money Flow 的消費方式
Used Car Vehicle Cost 與 Money Flow 的重疊 / 斷點
Used Car Reservation 與訂金 / 尾款 Money Flow 關聯
```

### 2.2 本階段不做

```text
不改 JS
不改 Python service
不改 DocType JSON
不新增 DocType
不新增 patch
不跑 bench migrate
不處理 advance account warning
不重構 Payment Entry
不新增 Journal Entry / Sales Invoice runtime
不實作資金帳戶
```

---

## 3. 目前 Used Car Money Flow 欄位盤點

目前 DocType：

```text
used_car_erp/used_car_erp/doctype/used_car_money_flow/used_car_money_flow.json
```

### 3.1 基本欄位

| 欄位 | 類型 | 現況判斷 |
| --- | --- | --- |
| `money_flow_no` | Data | 金流編號，read only，unique，作為 autoname |
| `status` | Select | `待審核 / 已入帳 / 已作廢`，目前是會計審核狀態，不是營運結清狀態 |
| `flow_type` | Select | 金流類型，read only，必填 |
| `direction` | Select | `收入 / 支出`，read only |
| `created_by_service` | Check | 標示由系統流程建立 |

目前 `flow_type` options：

```text
訂金收款
尾款收款
貸款撥款
退款
其他
整備支出
維修支出
美容支出
代辦支出
拍場支出
其他支出
```

判斷：

```text
足以承接目前任務卡的訂金、尾款、退款與一般支出。
尚不足以完整承接資金帳與營運管理帳。
```

---

### 3.2 來源 / 對象欄位

| 欄位 | 類型 | 現況判斷 |
| --- | --- | --- |
| `vehicle` | Link Used Car Vehicle | 已有，且必填，適合作為單車營運主帳主索引 |
| `reservation` | Link Used Car Reservation | 已有，可追蹤訂金 / 尾款 / 退款來源 |
| `stock_no` | Data | 已有，提供車輛編號快照 |
| `customer` | Link Customer | 已有，但 permlevel 1，偏客戶收款 |
| `customer_name` | Data | 已有，適合業務查詢 |
| `customer_phone` | Data | 已有，適合業務查詢 |

缺口：

```text
沒有通用交易對象欄位。
目前 customer 只適合買方 / 客戶，不適合維修廠、拍場、代辦、原車主、老闆代墊人。
```

建議後續新增或設計：

```text
counterparty_type
counterparty_name
counterparty_supplier
counterparty_customer
```

或最小版先用：

```text
counterparty_name：交易對象
```

---

### 3.3 金額 / 日期 / 付款欄位

| 欄位 | 類型 | 現況判斷 |
| --- | --- | --- |
| `amount` | Currency | 已有，permlevel 1，必填 |
| `payment_date` | Date | 已有，必填 |
| `payment_method` | Select | 已有，options：`現金 / 匯款 / 信用卡 / 其他` |
| `payment_reference` | Data | 已有，可放末五碼 / 付款備註 / 付款對象 |
| `notes` | Small Text | 已有，read only |

判斷：

```text
目前可記錄最基本現金 / 匯款 / 信用卡 / 其他。
但 payment_method 不是資金帳戶。
```

關鍵缺口：

```text
沒有資金帳戶欄位。
無法準確區分：現金、主要銀行、其他銀行、待收款、待付款、老闆代墊。
```

例如：

```text
payment_method = 匯款
```

只能知道付款方式是匯款，但不能知道是：

```text
台新銀行
玉山銀行
公司主要銀行
老闆私人帳戶代墊
待收款尚未入帳
```

這會阻擋後續：

```text
現金餘額
銀行餘額
待收款
待付款
資金流水摘要
記帳士交接包
```

---

### 3.4 憑證欄位

| 欄位 | 類型 | 現況判斷 |
| --- | --- | --- |
| `evidence_attachment` | Attach | 已有，label：憑證附件 |

目前車輛頁 inline 摘要會依 `evidence_attachment` 顯示：

```text
有憑證 / 無憑證
```

缺口：

```text
沒有憑證狀態欄位。
沒有憑證類型欄位。
沒有是否已交記帳士欄位。
```

目前只能用是否有附件推測，無法表達：

```text
紙本已在資料夾
附件已上傳
憑證缺漏
憑證待補
已交記帳士
不需憑證
```

注意：`Used Car Vehicle Cost` 目前有較完整的文件 / 憑證資料：

```text
document_type
 documento_no / document_no
review_status
tax_deductibility
vendor_name
```

但這些沒有在 `Used Car Money Flow` 上。

---

### 3.5 會計連結欄位

| 欄位 | 類型 | 現況判斷 |
| --- | --- | --- |
| `voucher_draft` | Link Used Car Voucher Draft | 已有，permlevel 2 |
| `journal_entry` | Link Journal Entry | 已有，permlevel 2 |

判斷：

```text
足以支撐既有 Voucher Draft → Journal Entry 會計輔助流程。
但這是會計輔助層，不應繼續成為 MVP 主帳的主要設計中心。
```

---

## 4. 目前建立來源盤點

目前 `VehicleMoneyFlowService` 建立 Money Flow 的主要入口：

| 入口 | flow_type | direction | 來源 |
| --- | --- | --- | --- |
| `create_general_expense_money_flow` | 整備 / 維修 / 美容 / 代辦 / 拍場 / 其他支出 | 支出 | 車輛頁「新增支出」任務卡 |
| `create_deposit_money_flow_from_reservation` | 訂金收款 | 收入 | 收訂金並保留 |
| `create_final_payment_money_flow_from_reservation` | 尾款收款 | 收入 | 收尾款 |
| `create_deposit_refund_money_flow_from_reservation` | 退款 | 支出 | 取消保留 / 處理訂金 |

### 4.1 一般支出建立現況

`create_general_expense_money_flow` 目前接收：

```text
vehicle
payment_date
flow_type
amount
payment_method
payment_reference
notes
evidence_attachment
```

會建立：

```text
Used Car Money Flow
→ Used Car Voucher Draft
```

判斷：

```text
此路徑最接近新的營運主帳方向。
但它仍會立即建立 Voucher Draft，因此目前 Money Flow 與會計草稿仍綁得太緊。
```

### 4.2 訂金建立現況

`create_deposit_money_flow_from_reservation` 從 `Used Car Reservation` 複製：

```text
vehicle
reservation
stock_no
customer
customer_name
customer_phone
deposit_amount
deposit_date
payment_method
payment_reference
notes
```

缺口：

```text
訂金路徑沒有 evidence_attachment。
訂金路徑沒有資金帳戶。
訂金路徑沒有是否交記帳士 / 憑證狀態。
```

### 4.3 尾款建立現況

`create_final_payment_money_flow_from_reservation` 接收：

```text
reservation_name
amount
payment_method
payment_date
payment_reference
notes
```

缺口：

```text
尾款路徑沒有 evidence_attachment。
尾款路徑沒有資金帳戶。
尾款路徑沒有結清狀態欄位，只能從 status = 已入帳 推測。
```

### 4.4 訂金退款建立現況

`create_deposit_refund_money_flow_from_reservation` 接收：

```text
reservation_name
refund_payment_method
refund_date
refund_reference
refund_notes
```

缺口：

```text
退款路徑沒有 evidence_attachment。
退款路徑沒有資金帳戶。
退款沒有獨立退款原因欄位，只能依 reservation cancellation reason 或 notes 間接理解。
```

---

## 5. 目前消費端盤點

### 5.1 車輛頁 inline 收支摘要

目前 `Used Car Vehicle` JS 會用 `frappe.client.get_list` 讀取 `Used Car Money Flow`：

```text
name
payment_date
flow_type
direction
amount
status
evidence_attachment
```

顯示：

```text
近 20 筆收支紀錄
日期
類型
金額
狀態
憑證
金流編號
```

判斷：

```text
目前只是明細表，不是管理帳摘要。
```

缺口：

```text
沒有小計收入 / 支出
沒有按 flow_type 分類小計
沒有現金 / 銀行 / 待收 / 待付摘要
沒有缺憑證統計
沒有是否交記帳士
沒有待收 / 待付判斷
沒有單車毛利推導
```

---

### 5.2 Voucher Draft / Journal Entry 消費

`VehicleVoucherService` 會根據 Money Flow 建立 `Used Car Voucher Draft`。

會計確認後：

```text
Used Car Voucher Draft.status = 已入帳
Used Car Voucher Draft.journal_entry = Journal Entry
Used Car Money Flow.status = 已入帳
Used Car Money Flow.journal_entry = Journal Entry
```

作廢草稿時：

```text
Used Car Voucher Draft.status = 已作廢
Used Car Money Flow.status = 已作廢
```

判斷：

```text
目前 status 主要代表會計流程狀態，而不是資金實際結清狀態。
```

這對新的營運主帳有風險：

```text
一筆錢可能已實際收付，但尚未入帳。
一筆錢可能是待收 / 待付，不應被視為已收 / 已付。
目前 status 無法完整表達這些營運狀態。
```

---

### 5.3 管理毛利 summary 消費

目前 `VehicleManagementProfitSummaryService` 的成本來源主要是：

```text
Used Car Vehicle.purchase_price
Used Car Vehicle Cost
Used Car Money Flow 的其他直接收入
```

其中直接成本讀取：

```text
Used Car Vehicle Cost
```

Money Flow 只被用來讀：

```text
direction = 收入
flow_type in 其他收入 / 收入 / 其他
```

但目前 `Used Car Money Flow.flow_type` options 只有：

```text
其他
```

沒有：

```text
其他收入
收入
```

判斷：

```text
目前管理毛利和 Money Flow 主帳方向尚未整合。
新增支出任務卡建立的是 Money Flow，不是 Used Car Vehicle Cost。
但管理毛利的直接成本主要讀 Used Car Vehicle Cost，不讀支出型 Money Flow。
```

這是 Step 2 最重要的產品 / 資料流缺口。

---

## 6. 與 Used Car Vehicle Cost 的關係

目前 `Used Car Vehicle Cost` 已有較完整的成本 / 憑證 / 稅務欄位：

```text
vehicle
cost_date
cost_category
amount
capitalization_mode
vendor_name
document_type
document_no
tax_deductibility
review_status
notes
```

優點：

```text
成本分類完整
有廠商 / 付款對象
有憑證類型
有進項稅狀態
有成本確認狀態
適合管理毛利與稅務整理
```

但目前新的「新增支出」業務任務卡主要建立：

```text
Used Car Money Flow
```

而不是：

```text
Used Car Vehicle Cost
```

因此目前存在兩套資料：

```text
Used Car Money Flow = 金流 / 傳票草稿來源
Used Car Vehicle Cost = 管理毛利直接成本來源
```

這對 P1-MVP-OPS 會造成風險：

```text
同一筆維修支出可能只在 Money Flow，有金流但不進管理毛利。
或只在 Vehicle Cost，有成本但不進資金帳。
```

---

## 7. 欄位缺口總表

| 需求 | 目前是否具備 | 現況 | 建議 |
| --- | --- | --- | --- |
| 車輛關聯 | 已具備 | `vehicle` 必填 | 保留 |
| 金流類型 | 部分具備 | 有訂金、尾款、退款、支出 | 後續補採購付款、待收、待付、老闆代墊或改分類模型 |
| 收入 / 支出方向 | 已具備 | `direction` | 保留 |
| 金額 | 已具備 | `amount` | 保留 |
| 日期 | 已具備 | `payment_date` | 可考慮改語意為 transaction_date 或保留 label |
| 付款方式 | 已具備 | 現金 / 匯款 / 信用卡 / 其他 | 保留，但不等於資金帳戶 |
| 資金帳戶 | 缺 | 無法算現金 / 銀行 / 待收 / 待付 | Step 3 優先設計 |
| 交易對象 | 部分具備 | customer 只適合客戶，payment_reference 被拿來兼用 | 建議新增通用 counterparty |
| 憑證附件 | 部分具備 | Money Flow 有 Attach，但訂金 / 尾款 / 退款任務卡未完整傳入 | 補 wiring 或新增憑證模型 |
| 憑證狀態 | 缺 | 只能用有無附件推測 | 建議新增 evidence_status |
| 憑證類型 | 缺 | Money Flow 無，Vehicle Cost 有 | 建議 Money Flow 補 document_type 或與 Vehicle Cost 整合 |
| 是否已結清 | 缺 | status 是會計狀態，不是收付狀態 | 建議新增 settlement_status |
| 是否交記帳士 | 缺 | 無 | 建議新增 accountant_handoff_status |
| 是否影響毛利 | 缺 | 目前靠 flow_type / Vehicle Cost 分開判斷 | 建議新增 affects_management_profit 或整合 Vehicle Cost |
| 是否影響稅務整理 | 缺 | Vehicle Cost 有 tax_deductibility，Money Flow 無 | 建議新增 tax_handling_status 或與 Vehicle Cost 整合 |
| 會計草稿連結 | 已具備 | voucher_draft | 降級為會計輔助 |
| 正式傳票連結 | 已具備 | journal_entry | 降級為會計輔助 |

---

## 8. 關鍵設計判斷

### 8.1 Money Flow 不應只作為 Voucher Draft 前置資料

目前 Money Flow 太接近：

```text
Voucher Draft 的來源文件
```

新的 P1-MVP-OPS 方向要求 Money Flow 成為：

```text
營運主帳
```

因此後續要避免所有設計都以「建立傳票草稿」為中心。

### 8.2 status 不足以表達營運狀態

目前：

```text
status = 待審核 / 已入帳 / 已作廢
```

這是會計處理狀態。

營運管理帳還需要：

```text
已收 / 已付
待收 / 待付
部分收付
已退回
已結清
不需收付
```

建議不要把這些硬塞進現有 `status`，避免破壞既有會計流程。

### 8.3 支出與成本資料目前分裂

現在：

```text
新增支出任務卡 → Money Flow
管理毛利直接成本 → Vehicle Cost
```

後續必須二選一或明確定義同步關係：

#### 方案 A：Money Flow 成為唯一主帳，成本 summary 改讀 Money Flow

優點：

```text
資料入口單一
資金帳、單車損益、收支摘要一致
符合 P1-MVP-OPS 主線
```

缺點：

```text
Money Flow 需要補很多成本 / 憑證 / 稅務欄位
會影響既有 management profit summary
```

#### 方案 B：Money Flow 記資金，Vehicle Cost 記管理成本，建立明確連結

概念：

```text
Money Flow = 這筆錢怎麼收付
Vehicle Cost = 這筆支出如何進單車成本 / 稅務整理
```

需要新增：

```text
Money Flow.linked_vehicle_cost
或 Vehicle Cost.money_flow
```

優點：

```text
保留 Vehicle Cost 已有成本 / 憑證 / 稅務欄位
會計 / 管理成本模型較清楚
```

缺點：

```text
多一層同步與資料一致性風險
業務輸入後要自動建立兩份資料或建立連結
```

### 8.4 建議採用短期過渡方案

短期建議：

```text
Money Flow 作為主入口與資金主帳
Vehicle Cost 暫時保留為成本 / 稅務整理補充資料
下一步先補資金帳戶，不急著合併 Money Flow 與 Vehicle Cost
```

原因：

```text
資金帳戶是現金 / 銀行 / 待收 / 待付的前置基礎
Money Flow 與 Vehicle Cost 整合需要更大設計，不適合 Step 3 直接做 runtime
```

---

## 9. Step 3 建議方向

下一步建議：

```text
P1-MVP-OPS Step 3：資金帳戶最小模型規格
```

先做文件規格，不直接 runtime。

目標：

```text
定義 Used Car Cash Account / 資金帳戶
定義最小資金帳戶：現金、主要銀行、待收款、待付款、老闆代墊、其他
定義 Money Flow 如何連到資金帳戶
定義 payment_method 與 cash_account 的分工
定義哪些 flow_type 預設進哪個資金帳戶
定義不動會計 runtime 的過渡方案
```

建議 commit message：

```text
docs: define minimal cash account model
```

---

## 10. 結論

目前 `Used Car Money Flow` 已足以支撐：

```text
車輛關聯
訂金收款
尾款收款
訂金退款
一般支出
基本付款方式
憑證附件
會計草稿與正式傳票連結
車輛頁近 20 筆收支明細
```

但尚不足以支撐完整 P1-MVP-OPS：

```text
現金餘額
銀行餘額
待收款
待付款
老闆代墊
缺憑證統計
是否交記帳士
資金流水摘要
單車完整管理損益
成交結案明細表
```

最優先缺口是：

```text
資金帳戶
通用交易對象
憑證狀態
營運結清狀態
是否交記帳士
Money Flow 與 Vehicle Cost 的邊界 / 連結
```

因此下一步不應直接改成交 runtime，也不應處理 Payment Entry 或 advance account warning。

下一步應先定義：

```text
P1-MVP-OPS Step 3：資金帳戶最小模型規格
```

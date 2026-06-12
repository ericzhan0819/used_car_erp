# 正式交車 / 出庫 / 銷售文件決策文件

## 目的

本文件定義「確認成交」之後，後續要如何接 ERPNext 原生銷售、庫存與會計文件。

目前系統已完成：

```text
新增車輛
→ 完成入庫
→ 上架
→ 訂金保留
→ 訂金金流 / 傳票草稿
→ 會計確認訂金入帳
→ 尾款收款
→ 尾款金流 / 傳票草稿
→ 會計確認尾款入帳
→ 成交前檢查
→ 確認成交
→ 車輛標記已售出
→ 保留單標記已完成
→ 已售出車輛成交摘要
```

以上流程目前仍然只代表中古車業務流程已完成，不代表 ERPNext 原生銷售、出庫、收入認列或成本結轉已完成。

UX 決策：已售出車輛頁採「下一步操作」模式，使用者只需要按主要下一步按鈕；正式交車入帳前檢查由建立 Sales Invoice 草稿流程自動執行，不作為主要操作入口。

UX 決策：Sales Invoice 草稿建立後，已售出車輛頁會顯示草稿檢查清單，提醒使用者確認客戶、公司、Item、Serial No、Warehouse、金額、Income Account、Update Stock 與 Draft 狀態；正式提交與預收款沖轉仍屬後續階段。

Phase 2.5：已售出車輛最終檢查面板

- 彙整成交狀態、訂金/尾款入帳、ERPNext 庫存連結、Sales Invoice 草稿、成本摘要、損益與預估營業稅、稅務確認狀態。
- 此階段只作人工檢查，不提交 Sales Invoice、不出庫、不做預收款沖轉、不認列收入、不做 COGS。

---

## 目前明確邊界

目前已完成的 `確認成交` 只做業務狀態轉換：

```text
Used Car Vehicle.status = 已售出
Used Car Reservation.status = 已完成
```

目前不做：

```text
不建立 Sales Invoice
不建立 Payment Entry
不建立 Delivery Note
不建立 Stock Entry
不做收入認列
不做 COGS / 成本結轉
不做毛利計算
不處理稅額
不清除應收帳款
```

這個邊界必須保留，避免業務確認成交時直接觸發正式會計與庫存異動。

---

## 核心問題

中古車成交後，系統需要回答三個問題：

1. 何時正式認列銷售收入？
2. 何時將車輛從 ERPNext 庫存出庫？
3. 先前訂金與尾款已入帳到 `預收款 / 暫收款`，正式銷售時要如何沖轉？

目前訂金與尾款的會計處理是保守做法：

```text
借：銀行存款 / 現金
貸：預收款 / 暫收款
```

原因是交車與正式銷售文件尚未完成前，不直接認列收入。

因此正式交車階段不能只建立銷售發票，也必須考慮如何把已收款項從 `預收款 / 暫收款` 沖轉到應收帳款或收入相關科目。

---

## 可選方案比較

### 方案 A：繼續只使用自訂文件，不接 ERPNext 原生銷售 / 庫存

流程：

```text
確認成交
→ 自訂成交摘要
→ 自訂報表匯出給會計師
```

優點：

- 最簡單。
- 不碰 ERPNext 複雜銷售與庫存流程。
- 不容易誤產生正式會計文件。

缺點：

- ERPNext 原生庫存不會真正出庫。
- ERPNext 原生銷售報表沒有資料。
- 無法利用 ERPNext Sales Invoice、Stock Ledger、Gross Profit 等標準報表。
- 長期會變成自訂 ERP，不符合使用 ERPNext 的主要目的。

判斷：

```text
不作為長期主線。
```

可作為短期人工過渡，但不能作為正式解法。

---

### 方案 B：正式交車時建立 Sales Invoice，並使用 Update Stock 出庫

流程：

```text
已售出車輛
→ 正式交車 / 入帳
→ 建立並提交 Sales Invoice
→ Sales Invoice 勾選 Update Stock
→ 指定車輛 Item / Serial No
→ ERPNext 產生收入、應收與庫存出庫 / 成本影響
→ 建立預收款沖轉 Journal Entry
```

優點：

- 文件數量少。
- 對一車一件、序號控管的中古車買賣比較直覺。
- 可以讓 ERPNext 原生 Sales Invoice 承擔銷售收入與出庫。
- 不需要另外建立 Delivery Note。
- 適合作為第一版正式交車流程。

缺點：

- 需要正確處理 Sales Invoice 的 Update Stock、Warehouse、Serial No、收入科目、稅與 COGS。
- 需要另外處理 `預收款 / 暫收款` 沖轉，否則 Sales Invoice 會留下應收帳款。
- 若未來需要正式交車單、交車驗收或物流節點，單靠 Sales Invoice 會不夠細。

判斷：

```text
建議作為第一版正式交車 / 出庫 / 銷售文件主線。
```

原因：目前業務是中古車買賣，不是大量物流出貨；每台車是獨立序號資產。第一版應優先簡化正式文件數量，用 Sales Invoice + Update Stock 完成銷售與出庫，再用一張沖轉 Journal Entry 清掉預收款與應收。

---

### 方案 C：正式交車時先建立 Delivery Note，再建立 Sales Invoice

流程：

```text
已售出車輛
→ 正式交車
→ 建立 Delivery Note 出庫
→ 建立 Sales Invoice 認列收入
→ 建立預收款沖轉 Journal Entry
```

優點：

- 交車與開立銷售發票分開，流程更正式。
- 如果未來需要交車驗收、客戶簽收、車輛文件移交，可以接 Delivery Note。
- 比較適合有倉儲物流或交付節點管理需求的公司。

缺點：

- 文件數量增加。
- 第一版複雜度較高。
- 中古車單台序號買賣短期可能用不到完整 Delivery Note 流程。
- 若 Sales Invoice 與 Delivery Note 對不上，會增加帳務排查成本。

判斷：

```text
保留為第二版。
```

第一版先不採用，除非實際營運需要獨立交車單或交車驗收流程。

---

### 方案 D：只用 Stock Entry 出庫，再用 Journal Entry 認列收入

流程：

```text
已售出車輛
→ Stock Entry 出庫
→ Journal Entry 認列收入 / 成本
```

優點：

- 看似可以避開 Sales Invoice 的複雜欄位。
- 自訂彈性高。

缺點：

- 繞過 ERPNext 標準銷售文件。
- 銷售報表、應收帳款、客戶交易紀錄會不完整。
- 會計與庫存容易脫鉤。
- 長期維護風險高。

判斷：

```text
不採用。
```

---

## 決策

第一版正式交車 / 出庫 / 銷售文件流程採用：

```text
方案 B：Sales Invoice + Update Stock + 預收款沖轉 Journal Entry
```

正式流程暫定為：

```text
已售出車輛
→ 正式交車入帳前檢查
→ 建立 Sales Invoice
→ Sales Invoice 勾選 Update Stock
→ 指定 Item / Serial No / Warehouse
→ 提交 Sales Invoice
→ 建立預收款沖轉 Journal Entry
→ 車輛標記正式交車入帳完成
```

---

## 第一版正式交車流程邊界

第一版要做：

```text
建立正式交車入帳 action
使用已完成保留單與車輛成交摘要作為資料來源
建立 Sales Invoice
Sales Invoice update_stock = 1
Sales Invoice item 使用車輛 item
Sales Invoice serial_no 使用車輛 serial_no
Sales Invoice customer 使用保留單 customer
Sales Invoice 金額使用訂金 + 尾款總額
Sales Invoice posting_date 使用正式交車入帳日期
提交 Sales Invoice
建立預收款沖轉 Journal Entry
回寫車輛與保留單正式銷售文件連結
```

第一版不要做：

```text
不建立 Delivery Note
不建立 Payment Entry
不做貸款撥款複雜流程
不做退款 / 溢收
不做部分尾款未收仍交車
不做自動稅額申報
不做電子發票整合
不做毛利報表
不做反向流程 / 作廢流程
```

---

## 建議新增狀態與欄位

後續 runtime 實作時，建議在 `Used Car Vehicle` 或 `Used Car Reservation` 增加正式交車入帳摘要欄位。

建議車輛欄位：

```text
formal_delivery_section
formal_delivery_status
formal_delivery_posting_date
sales_invoice
advance_settlement_journal_entry
formal_delivery_completed_at
formal_delivery_completed_by
formal_delivery_note
```

建議 `formal_delivery_status` options：

```text
未處理
銷售發票草稿
已完成
```

不建議再新增很多中間狀態，避免車輛狀態與保留單狀態過度複雜。

目前車輛主狀態已經是 `已售出`，正式交車入帳是否完成應作為成交後的文件狀態，不建議再塞進 `Used Car Vehicle.status`。

---

## 正式交車入帳前檢查

正式建立 Sales Invoice 前，應先做 preflight。

檢查條件：

```text
車輛存在
車輛 status = 已售出
車輛 completed_reservation 存在
保留單存在
保留單 status = 已完成
訂金金流已入帳
尾款金流已入帳
訂金正式會計傳票存在
尾款正式會計傳票存在
車輛 item 存在
車輛 serial_no 存在
車輛目前尚未回寫 sales_invoice
車輛目前尚未回寫 advance_settlement_journal_entry
```

若任一條件不符合，應阻止正式交車入帳。

---

## Sales Invoice 建立規則

Sales Invoice 建議資料來源：

| Sales Invoice 欄位 | 建議來源 |
| --- | --- |
| customer | `Used Car Reservation.customer` |
| posting_date | 使用者輸入，預設今天 |
| due_date | 同 posting_date 或依公司付款條件 |
| update_stock | `1` |
| items.item_code | `Used Car Vehicle.item` |
| items.qty | `1` |
| items.serial_no | `Used Car Vehicle.serial_no` |
| items.rate | 訂金金額 + 尾款金額 |
| items.warehouse | 車輛目前所在 warehouse 或系統預設中古車庫存倉 |
| remarks | 關聯車輛、保留單、訂金與尾款金流 |

金額第一版建議：

```text
銷售金額 = reservation.deposit_amount + reservation.final_payment_amount
```

若未來有貸款撥款、折讓、退款、溢收，再擴充為正式成交金額欄位，不要現在提前複雜化。

---

## 預收款沖轉 Journal Entry 規則

目前訂金與尾款已經各自建立正式 Journal Entry，且貸方是 `預收款 / 暫收款`。

當 Sales Invoice 建立後，ERPNext 會產生應收帳款與收入。若不處理沖轉，系統會顯示客戶仍欠款。

因此正式交車入帳時，需要建立一張沖轉傳票：

```text
借：預收款 / 暫收款
貸：應收帳款 / Accounts Receivable
```

金額：

```text
訂金金額 + 尾款金額
```

目的：

```text
把先前已收但暫列負債的金額，沖掉 Sales Invoice 產生的應收帳款。
```

第一版限制：

```text
只處理全額已收款後才正式交車入帳。
不處理部分應收、溢收、退款、貸款未撥款。
```

---

## Payment Entry 決策

第一版不建立 Payment Entry。

原因：

- 訂金與尾款已經透過 `Used Car Money Flow` 與 `Journal Entry` 記錄。
- 若再建立 Payment Entry，容易重複認列收款。
- 目前自訂流程已把成交前收款放在 `預收款 / 暫收款`，正式交車時用 Journal Entry 沖轉較一致。

未來若要改用 ERPNext 原生 Payment Entry，必須重新設計訂金與尾款流程，不應在第一版混用。

---

## Delivery Note 決策

第一版不建立 Delivery Note。

原因：

- 中古車一車一序號，第一版可由 Sales Invoice `update_stock = 1` 完成出庫。
- Delivery Note 會增加文件數量與對帳成本。
- 目前尚未建立交車驗收、客戶簽收、證件移交流程。

未來若需要正式交車單，可以新增第二版：

```text
交車驗收 / 文件移交
→ Delivery Note
→ Sales Invoice
```

但不應與第一版同時做。

---

## 稅與發票邊界

ERPNext `Sales Invoice` 是內部 ERP 銷售文件，不等同於台灣電子發票或正式稅務申報完成。

第一版：

```text
只建立 ERPNext 內部 Sales Invoice
不串接電子發票
不自動申報營業稅
不處理特殊稅務邏輯
```

報稅季仍以 ERPNext 報表、Journal Entry、Sales Invoice 與匯出資料交給會計師整理。

---

## 後續實作順序

建議拆成三個 runtime 階段，不要一次做完。

### Phase 1：正式交車入帳 Preflight

只做檢查，不建立文件。

Phase 1 已實作正式交車入帳前檢查。

此階段只驗證已售出車輛、已完成保留單、成交摘要、Item、Serial No、訂金與尾款入帳資料是否完整。

此階段不建立 Sales Invoice、不出庫、不建立沖轉 Journal Entry。

目標：

```text
已售出車輛
→ 正式交車入帳前檢查
→ 回傳可否建立 Sales Invoice / 沖轉傳票
```

### Phase 2：Sales Invoice Draft Foundation

只建立 Sales Invoice 草稿，不提交。

Phase 2 已實作 Sales Invoice Draft Foundation。

此階段只建立 Sales Invoice 草稿並回寫車輛連結。

Sales Invoice 草稿建立時，item row 需解析並填入公司可用的 income_account；解析順序為 Item Default、Item Group Default、Company default_income_account、非群組 Income Account fallback。

此階段不提交 Sales Invoice、不建立沖轉 Journal Entry、不建立 Payment Entry 或 Delivery Note。

目標：

```text
通過 preflight
→ 建立 Sales Invoice 草稿
→ update_stock = 1
→ item / serial_no / warehouse / customer / amount 正確
→ 回寫 sales_invoice
```

此階段仍不建立沖轉 Journal Entry。

### Phase 3：正式提交與預收款沖轉

在 Sales Invoice 草稿確認正確後：

```text
提交 Sales Invoice
→ 建立預收款沖轉 Journal Entry
→ 回寫 advance_settlement_journal_entry
→ formal_delivery_status = 已完成
```

---

## 第一版禁止事項

後續寫 code 時，第一版禁止：

```text
不要在確認成交時建立 Sales Invoice
不要在確認成交時出庫
不要在確認成交時做收入認列
不要建立 Delivery Note
不要建立 Payment Entry
不要處理貸款撥款
不要處理退款
不要處理溢收
不要處理部分付款交車
不要處理電子發票
不要做毛利報表
不要做反向作廢流程
```

正式交車入帳必須是獨立 action，不可綁在 `確認成交`。

---

## 最終決策摘要

```text
確認成交 = 業務成交完成
正式交車入帳 = ERPNext 銷售、出庫、收入與應收沖轉
```

第一版正式交車入帳採用：

```text
Sales Invoice + Update Stock + 預收款沖轉 Journal Entry
```

第一版不採用：

```text
Delivery Note
Payment Entry
Stock Entry 手動出庫
純 Journal Entry 認列收入
```

核心理由：

```text
中古車一車一序號，第一版應以最少正式文件完成 ERPNext 標準銷售與庫存出庫，同時避免重複收款與帳務脫鉤。
```

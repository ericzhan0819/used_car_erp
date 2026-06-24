# P1-MVP-UX-OPS-2 Step 5：Guided Listing Task Card Spec

日期：2026-06-24  
專案：Used Car ERP / ERPNext / Frappe  
Repo：`ericzhan0819/used_car_erp`  
前置穩定點：`606d48e docs: sync expense dialog smoke current state`

---

## 1. 本階段目的

本文件定義下一張業務任務卡：

```text
整備完成並上架
```

目標是讓使用者在車輛整備完成後，用一張清楚的任務卡完成上架所需的業務資料，而不是直接面對完整 `Used Car Vehicle` DocType 表單。

本階段是規格文件，不做 runtime。

```text
不改 Python service
不改 DocType JSON
不改 JavaScript runtime
不改 Workspace / Page
不改 hooks.py
不建立 / 修改 / 提交任何 ERPNext 會計文件
```

---

## 2. 產品背景

目前已完成：

```text
P1-MVP-UX-OPS-2 Step 4A：Guided Preparation Expense Dialog Runtime
P1-MVP-UX-OPS-2 Step 4B：Preparation Expense Post-Smoke Docs Sync
```

也就是：

```text
車輛頁「新增支出」已改為 shared guided Dialog
支出建立後沿用 Money Flow / Voucher Draft foundation
業務端不顯示會計術語
browser smoke passed
```

車輛買入並完成整備支出紀錄後，下一個自然業務動作是：

```text
整備完成
設定售價資訊
讓車輛進入可銷售狀態
```

因此 Step 5 應先定義「整備完成並上架」任務卡的 UX、欄位、權限與邊界，再進入 runtime。

---

## 3. 業務與會計邊界

### 3.1 業務端要做的事

業務或主管端只處理上架事實：

```text
這台車是否整備完成
這台車何時上架
這台車對外開價是多少
這台車是否有銷售備註
主管是否已填寫內部底價
```

### 3.2 系統要做的事

系統接收任務卡資料後，只應更新車輛業務狀態與上架資訊：

```text
寫入底價 / 開價 / 上架日期 / 銷售備註
車輛狀態改為上架中
刷新車輛頁業務狀態
```

### 3.3 會計端要做的事

本任務卡不產生會計待辦。

上架不是收款、不是成交、不是出庫、不是收入認列，也不是正式會計事件。

會計端不需要因為「整備完成並上架」產生新的 Journal Entry、Sales Invoice、Voucher Draft、Payment Entry 或 Stock Entry。

---

## 4. 業務端禁止字詞

Guided Listing Task Card 內不得出現：

```text
Money Flow
Voucher Draft
Journal Entry
Sales Invoice
GL Entry
Stock Entry
借方
貸方
會計科目
預收款沖轉
15-1
正式交車
收入認列
```

可以使用的業務語意：

```text
整備完成並上架
底價
開價
上架日期
銷售備註
車輛狀態
上架中
```

---

## 5. 入口設計

### 5.1 車輛頁入口

在 `Used Car Vehicle` 表單中，當車輛處於可上架狀態時，應顯示業務語意入口：

```text
整備完成並上架
```

建議優先顯示在：

```text
車輛作業
```

### 5.2 顯示條件

按鈕應只在合理狀態顯示。

建議顯示：

```text
車輛已儲存
車輛狀態 = 整備中
```

可視實務需要擴充為：

```text
車輛狀態 = 庫存中
```

但 Step 5 runtime 初版建議先只支援：

```text
整備中 → 上架中
```

原因：

```text
避免同一張任務卡同時承擔「略過整備」與「完成整備」兩種語意。
```

### 5.3 不顯示條件

按鈕不應顯示於：

```text
草稿
上架中
保留中
已售出
封存
```

若未來需要「重新上架」或「下架後再上架」，應另開任務，不混入本任務卡。

---

## 6. 任務卡欄位規格

### 6.1 必填欄位

```text
vehicle：車輛，由入口帶入，不要求使用者重選
listing_date：上架日期，預設今天
asking_price：開價
```

### 6.2 條件必填欄位

```text
floor_price：底價
```

底價在主管視角應為必填。

若目前權限或 permlevel 尚未完成主管限定，Step 5 runtime 不應自行大改 permission schema。應先用現有權限模型保守處理，並在需要時另開權限任務。

### 6.3 選填欄位

```text
sales_note：銷售備註
```

### 6.4 對應現有欄位

任務卡應優先沿用現有 `Used Car Vehicle` 欄位：

| 任務卡欄位 | 既有欄位 | 說明 |
| --- | --- | --- |
| 底價 | `floor_price` | 內部底線價，不應讓一般業務看到 |
| 開價 | `asking_price` | 對外銷售參考價 |
| 上架日期 | 待 runtime 盤點 | 若無明確欄位，初版可用狀態切換時間，不應在 Step 5A 直接加 schema |
| 銷售備註 | `sales_note` | 對銷售流程有幫助的備註 |
| 車輛狀態 | `status` | 成功後改為 `上架中` |

如果 runtime 盤點發現沒有適合的上架日期欄位，應停下來回報。

Step 5A 不應直接新增 `listing_date` DocType 欄位，除非另開 schema 任務並經確認。

---

## 7. 權限與可見性規則

### 7.1 底價

底價是內部底線價。

產品規則：

```text
底價只有主管看得到
底價只能主管填
一般業務不可看到底價
一般業務不可修改底價
```

對應欄位：

```text
floor_price
```

### 7.2 開價

開價是對外銷售參考價。

產品規則：

```text
開價由主管填寫或核准
一般業務可以看到已核准的開價
一般業務不應自行修改開價
```

對應欄位：

```text
asking_price
```

### 7.3 銷售備註

銷售備註可視為業務可見資訊，但不應混入底價、毛利或會計資訊。

可放內容：

```text
車況賣點
配備說明
賞車注意事項
可公開銷售提醒
```

不應放內容：

```text
底價
內部毛利
會計科目
稅務判斷
傳票或發票資訊
```

### 7.4 權限不足時的處理

若 Step 5 runtime 實作時發現目前角色 / permlevel 無法安全達成底價可見性，不應在同一任務內大改權限。

應停止並回報，另開：

```text
P1-MVP-UX-OPS-2 Step 5P：Guided Listing Permission Boundary
```

或沿用既有 `used-car-field-permlevel-design.md` 補最小權限調整。

---

## 8. 任務卡流程

### 8.1 開啟

```text
車輛頁 → 整備完成並上架
```

系統帶入：

```text
vehicle
vehicle display label
目前車輛狀態
```

車輛顯示建議：

```text
車輛：{車輛編號 / 車牌 / 廠牌車型}
```

### 8.2 填寫

主管視角 Dialog 顯示：

```text
整備完成並上架
車輛資訊
上架日期
底價
開價
銷售備註
```

一般業務視角不應看到底價輸入。

若一般業務沒有權限完成上架，應顯示清楚訊息：

```text
此車已整備完成，請主管填寫價格並上架。
```

不得顯示技術訊息，例如：

```text
No permission for permlevel 1
DocPerm denied
```

### 8.3 送出

主要按鈕文字：

```text
確認上架
```

不得使用：

```text
Submit
Update DocType
建立會計文件
建立 Sales Invoice
```

### 8.4 成功後

成功後建議：

```text
顯示成功訊息：車輛已上架
車輛狀態改為上架中
刷新表單
不跳轉會計文件
不跳轉 ERPNext 技術文件
```

---

## 9. 驗證與阻擋規則

### 9.1 必填驗證

送出前應驗證：

```text
車輛存在
車輛已儲存
車輛狀態允許上架
開價 > 0
上架日期存在
```

主管視角還應驗證：

```text
底價 > 0
```

### 9.2 金額合理性提醒

若同時有底價與開價，建議檢查：

```text
開價 >= 底價
```

若開價小於底價，應阻擋或要求主管確認理由。

Step 5A runtime 初版建議採阻擋：

```text
開價不可低於底價。
```

若未來需要允許特殊促銷或急售，應另開例外理由欄位，不在初版混入。

### 9.3 車輛狀態驗證

如果車輛不是 `整備中`，應提示：

```text
此車目前不是整備中，不能使用「整備完成並上架」。
```

不得顯示：

```text
Invalid workflow state
```

### 9.4 監理 / 稅務旗標提醒

如果車輛有阻擋銷售的監理 / 稅務旗標，例如：

```text
has_unpaid_loan
has_tax_penalty
registration_restricted
insurance_cancelled
plate_cancelled
need_document_check
```

Step 5A runtime 可先不處理 blocking，但文件規格先定義：

```text
阻擋性風險應以業務語意提示
不顯示 15-1 或會計術語
不在本任務卡處理稅務計算
```

若要導入 blocking，應另開小步任務，避免 Step 5A 同時處理上架與風險規則。

---

## 10. 底層行為邊界

Step 5A runtime 應只做最小狀態更新：

```text
更新 floor_price，如有權限且欄位可用
更新 asking_price
更新 sales_note
更新 status = 上架中
```

若有上架日期欄位則更新該欄位；若沒有，不應自行新增 schema。

不應：

```text
建立 Money Flow
建立 Voucher Draft
建立 Journal Entry
建立 Sales Invoice
提交 Sales Invoice
建立 Stock Entry
建立 Payment Entry
修改 15-1 service
修改管理利潤 service
修改會計科目
觸發 formal delivery runtime
```

---

## 11. 與收支摘要的關係

整備完成並上架不會直接改變收支金額。

因此本任務卡成功後：

```text
不新增支出
不新增收入
不建立金流
不建立傳票草稿
```

車輛頁可以刷新，但不應新增 Money Flow 明細或會計狀態。

若上架後顯示摘要，應是業務摘要，例如：

```text
目前狀態：上架中
開價：{asking_price}
```

不得顯示：

```text
Journal Entry
Voucher Draft
Sales Invoice
GL Entry
```

---

## 12. 總覽與列表影響

### 12.1 總覽卡片

車輛上架後，總覽數字應自然反映：

```text
整備中 -1
上架中 +1
```

若現有總覽卡片已根據 `status` 統計，Step 5A runtime 不需要額外修改總覽。

### 12.2 車輛列表

車輛列表可顯示狀態為：

```text
上架中
```

若列表已有開價欄位，應使用 `asking_price`。

不應在列表顯示底價，除非角色為主管且權限設計明確允許。

---

## 13. Step 5A 建議切分

Step 5A 建議做最小 runtime：

```text
P1-MVP-UX-OPS-2 Step 5A：Guided Listing Dialog Runtime
```

範圍：

```text
新增 shared guided listing Dialog
車輛頁接上「整備完成並上架」入口
使用既有欄位 floor_price / asking_price / sales_note / status
成功後 status 改為 上架中
成功後顯示「車輛已上架」
```

不做：

```text
總覽新增新入口
支出列表重設計
會計作業頁重設計
Voucher Draft / Money Flow runtime
Sales Invoice runtime
Journal Entry runtime
DocType schema 大改
permission 大改
```

若發現缺少上架日期欄位，Step 5A 應停止並回報，不要自行新增欄位。

---

## 14. Step 5A 驗收標準

Step 5A 完成後應能驗證：

```text
1. 建立或使用一台狀態為整備中的車輛
2. 在車輛頁看到「整備完成並上架」
3. 點擊後開啟業務語意 Dialog
4. 填寫底價 / 開價 / 上架日期 / 銷售備註
5. 送出後顯示「車輛已上架」
6. 車輛狀態變成「上架中」
7. 不顯示 Money Flow / Voucher Draft / Journal Entry / Sales Invoice 字樣
8. 不建立任何會計或金流文件
9. 總覽 / 列表狀態可反映上架中
```

若目前權限尚無法驗證底價只限主管可見，需在驗收中明確標示：

```text
權限可見性尚未完成，需另開權限任務
```

---

## 15. 明確不做事項

本規格不要求：

```text
不新增 runtime
不改 DocType JSON
不新增 listing_date 欄位
不改 Page / Workspace
不改 hooks.py
不改會計流程
不建立 Money Flow
不建立 Voucher Draft
不建立 Journal Entry
不建立 Sales Invoice
不提交任何 ERPNext 文件
不修改 Stock Entry
不修改 15-1 service
不修改管理利潤 service
不清理測試車資料
不做大規模權限調整
```

Step 5A 實作時若發現缺欄位、權限不足或 schema 不足，應停止並回報，不要在同一任務內擴大範圍。

---

## 16. 下一步

建議下一步：

```text
P1-MVP-UX-OPS-2 Step 5A：Guided Listing Dialog Runtime
```

Step 5A 開始前應先盤點：

```text
Used Car Vehicle 現有 floor_price / asking_price / sales_note / status 欄位
是否存在可用上架日期欄位
車輛頁目前整備 / 上架相關按鈕
目前角色 / permlevel 是否足以隱藏底價
總覽上架中卡片是否依 status 統計
```

建議 commit message：

```text
docs: define guided listing task card
```

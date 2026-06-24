# P1-MVP-UX-OPS-2 Step 4：Preparation Expense Task Card Spec

日期：2026-06-24  
專案：Used Car ERP / ERPNext / Frappe  
Repo：`ericzhan0819/used_car_erp`  
目前 runtime 穩定點：`9aa2a64 feat: replace overview workspace with custom page`

---

## 1. 本階段目的

本文件定義下一張業務任務卡：

```text
新增整備 / 維修 / 美容 / 代辦 / 拍場支出
```

目標是讓業務人員在車輛頁或總覽入口中，以任務卡方式輸入車輛支出事實，而不是直接面對 ERPNext 會計文件或 `Used Car Money Flow` 技術表單。

本階段是規格文件，不做 runtime。

```text
不改 Python service
不改 DocType JSON
不改 JavaScript runtime
不改 Workspace / Page
不改 hooks.py
不建立 / 修改 / 提交任何 ERPNext 文件
```

---

## 2. 產品背景

目前已完成：

```text
/app/總覽 → custom Page
新增買入車輛 → shared guided intake Dialog
Used Car Vehicle List → shared guided intake Dialog
Guided intake → 建立車輛 / 自動入庫 / 狀態進入整備中
```

車輛買入後的下一個自然動作是記錄支出：

```text
整備
維修
美容
代辦
拍場
其他
```

這些支出目前底層已有 Money Flow / Voucher Draft foundation，但業務端不應看到這些名稱或會計術語。

---

## 3. 業務與會計邊界

### 3.1 業務端要做的事

業務端只輸入商業事實：

```text
這台車在哪一天花了多少錢
支出類型是什麼
付款方式是什麼
付款對象是誰
有沒有憑證附件
備註是什麼
```

### 3.2 系統要做的事

系統接收業務輸入後，在背景建立或沿用底層資料流：

```text
Used Car Money Flow
Used Car Voucher Draft
Vehicle cashflow summary
```

這些底層名稱不出現在業務任務卡 UI。

### 3.3 會計端要做的事

會計端之後在會計作業頁審核：

```text
金額
科目
憑證
是否入帳
```

會計端可以看到 Voucher Draft / Journal Entry / 科目等資訊；業務端不看。

---

## 4. 業務端禁止字詞

Preparation Expense Task Card 內不得出現：

```text
Money Flow
Voucher Draft
Journal Entry
Sales Invoice
GL Entry
借方
貸方
會計科目
預收款沖轉
15-1
```

可以使用的業務語意：

```text
新增支出
支出紀錄
憑證附件
付款方式
付款對象
收支摘要
待會計確認
```

`待會計確認` 只能作為狀態輔助字，不能導向會計文件，也不能讓業務修改會計欄位。

---

## 5. 入口設計

### 5.1 車輛頁入口

在 `Used Car Vehicle` 表單中，應有業務語意入口：

```text
新增支出
```

顯示條件：

```text
車輛已儲存
車輛不是取消 / 作廢狀態
```

建議優先顯示在車輛作業群組。

### 5.2 總覽入口

custom `/app/總覽` 未來可加入：

```text
新增支出
```

但 Step 4A 可先只從車輛頁進入，避免使用者未選車輛時多一層搜尋流程。

若總覽要提供 `新增支出`，建議行為是：

```text
先選車輛 → 再開支出任務卡
```

本文件不要求 Step 4A 必須實作總覽入口。

---

## 6. 任務卡欄位規格

### 6.1 必填欄位

```text
vehicle：車輛，由入口帶入，不要求業務重選
expense_date：支出日期，預設今天
expense_type：支出類型
amount：金額
payment_method：付款方式
paid_to：付款對象
```

### 6.2 選填欄位

```text
attachment：憑證附件
note：備註
```

### 6.3 支出類型

業務 UI 顯示：

```text
維修支出
美容支出
代辦支出
拍場支出
整備支出
其他支出
```

若底層 `Used Car Money Flow.flow_type` 目前已有不同命名，Step 4A 應建立 mapping，不應直接把技術 enum 暴露給業務。

### 6.4 付款方式

建議選項：

```text
現金
匯款
信用卡
支票
其他
```

若既有 Money Flow 已有 payment method 欄位或選項，Step 4A 應優先沿用既有欄位；若不存在，先以 Dialog 端自由文字或 select 傳給 service 的既有欄位，不新增 DocType 欄位，除非另開 schema 任務。

### 6.5 憑證附件

若 `Used Car Money Flow` 已有 Attach 欄位，任務卡應支援上傳並寫入該欄位。

若附件欄位不存在，Step 4A 不新增 schema，應先停止並回報，不要自行新增 DocType 欄位。

---

## 7. 任務卡流程

### 7.1 開啟

```text
車輛頁 → 新增支出
```

系統帶入：

```text
vehicle
vehicle display label
```

### 7.2 填寫

Dialog 顯示：

```text
新增支出
車輛：{車輛編號 / 車牌 / 廠牌車型}
支出日期
支出類型
金額
付款方式
付款對象
憑證附件
備註
```

### 7.3 送出

按鈕文字：

```text
建立支出紀錄
```

不得使用：

```text
建立 Money Flow
建立 Voucher Draft
建立 Journal Entry
```

### 7.4 成功後

成功後建議：

```text
顯示成功訊息：支出紀錄已建立
刷新車輛頁收支摘要
不跳轉到 Money Flow
不跳轉到 Voucher Draft
不跳轉到 Journal Entry
```

如果目前車輛頁已有 `查看收支紀錄`，可以保留。

---

## 8. 後端設計邊界

Step 4A runtime 應優先沿用既有 service：

```text
used_car_erp.used_car_erp.services.vehicle_money_flow_service
```

如果既有 service 已有：

```text
create_general_expense_money_flow
```

應優先包裝 / 呼叫它，不重寫 Money Flow 建立邏輯。

後端 service 對業務 Dialog 的 API 名稱可新增薄 wrapper，例如：

```text
run_guided_preparation_expense
```

但該 wrapper 只應：

```text
驗證 vehicle
驗證 amount > 0
驗證 expense_type
轉換業務支出類型到 Money Flow flow_type
呼叫既有 Money Flow service
回傳業務語意 payload
```

不應：

```text
提交 Journal Entry
修改 Sales Invoice
修改 Stock Entry
修改 Serial No
修改會計科目
建立新的會計 runtime
```

---

## 9. 15-1 與管理利潤邊界

支出任務卡建立的支出：

```text
不併入 15-1 購入成本
```

原因：

```text
15-1 購入成本以購車價為核心。
整備 / 維修 / 美容 / 代辦 / 拍場等後續支出，是管理利潤與一般費用視角，不是 15-1 購入成本。
```

這些支出應影響：

```text
車輛收支摘要
管理利潤摘要
會計作業待審核資料
```

不應影響：

```text
15-1 購入成本估算
```

---

## 10. 權限與欄位顯示

業務使用者可輸入：

```text
支出日期
支出類型
金額
付款方式
付款對象
憑證附件
備註
```

業務使用者不可輸入：

```text
會計科目
借方 / 貸方
Journal Entry
Voucher Draft
Sales Invoice
GL Entry
```

若底層 DocType 有 permlevel 限制，Step 4A 應使用既有 permission model，不新增大規模權限改造。

---

## 11. 車輛頁收支摘要行為

建立支出後，車輛頁收支摘要應反映：

```text
支出總額增加
收支摘要刷新
```

若現有 inline cashflow summary service 已可讀到該 Money Flow，Step 4A 只需在成功後刷新表單或重跑 summary render。

不應在車輛頁新增 Money Flow 明細表。

車輛頁仍保持：

```text
業務摘要
不是會計審核頁
```

---

## 12. Step 4A 建議切分

Step 4A 建議做最小 runtime：

```text
P1-MVP-UX-OPS-2 Step 4A：Guided Preparation Expense Dialog Runtime
```

範圍：

```text
新增 shared preparation expense Dialog
車輛頁新增 / 接上「新增支出」入口
新增薄 wrapper service，如必要
呼叫既有 Money Flow service
成功後刷新車輛頁收支摘要
```

不做：

```text
總覽新增支出入口
支出列表重設計
會計作業頁重設計
Voucher Draft 入帳流程重寫
科目選擇 UI
權限大改
DocType schema 大改
```

---

## 13. Step 4A 驗收標準

Step 4A 完成後應能驗證：

```text
1. 在車輛頁點「新增支出」
2. 開啟業務語意 Dialog
3. 填寫支出日期 / 類型 / 金額 / 付款方式 / 付款對象 / 憑證 / 備註
4. 建立支出紀錄
5. 不顯示 Money Flow / Voucher Draft / Journal Entry 字樣
6. 不跳轉會計文件
7. 車輛頁收支摘要刷新
8. 會計底層仍可取得待審核資料
```

測試資料應使用新車輛或明確指定測試車輛，不使用舊殘留資料作為驗收依據。

---

## 14. 明確不做事項

本規格不要求：

```text
不新增 runtime
不改 DocType JSON
不改 Page / Workspace
不改 hooks.py
不改會計流程
不建立 Journal Entry
不提交 Voucher Draft
不新增 Sales Invoice 邏輯
不修改 Stock Entry
不修改 15-1 service
不清理測試車資料
```

Step 4A 實作時若發現缺欄位或 schema 不足，應停止並回報，不要在同一任務內擴大 schema。

---

## 15. 下一步

建議下一步：

```text
P1-MVP-UX-OPS-2 Step 4A：Guided Preparation Expense Dialog Runtime
```

Step 4A 開始前應先盤點：

```text
Used Car Money Flow 欄位
vehicle_money_flow_service 現有 whitelisted methods
車輛頁目前「新增支出」按鈕與 inline cashflow summary render
憑證附件欄位是否已存在
```

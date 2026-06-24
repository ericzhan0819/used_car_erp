# P1-MVP-UX-OPS-2 Step 5A：Guided Listing Dialog Smoke Close

日期：2026-06-24  
專案：Used Car ERP / ERPNext / Frappe  
Repo：`ericzhan0819/used_car_erp`  
前置穩定點：`5963f89 docs: define guided listing task card`

---

## 1. 本文件目的

本文件收尾：

```text
P1-MVP-UX-OPS-2 Step 5A：Guided Listing Dialog Runtime
```

也就是車輛頁「整備完成並上架」業務任務卡 runtime 的 browser smoke 確認紀錄。

本文件只記錄完成狀態與驗證結果，不新增 runtime、不修改 schema、不改會計流程。

---

## 2. 前置 schema 狀態

Step 5A runtime 前先完成 schema 小任務：

```text
ae796a4 feat: add vehicle listing date field
```

Step 5S 內容：

```text
Used Car Vehicle 新增 listing_date 上架日期欄位
label：上架日期
fieldtype：Date
用途：由「整備完成並上架」任務卡寫入
```

此欄位補齊後，Step 5A runtime 不再需要挪用：

```text
reserved_date
sold_date
expected_delivery_date
delivery_date
```

以上欄位仍保留原本保留 / 成交 / 交車語意，不作為上架日期。

---

## 3. Runtime commit

Step 5A runtime commit：

```text
4a004d6 feat: add guided listing dialog
```

本次 runtime 修改檔案：

```text
used_car_erp/public/js/guided_listing_dialog.js
used_car_erp/used_car_erp/doctype/used_car_vehicle/used_car_vehicle.js
used_car_erp/hooks.py
```

---

## 4. Runtime 行為

### 4.1 Shared Dialog

新增 shared namespace：

```text
used_car_erp.guided_listing.open(frm)
```

用途：

```text
讓車輛頁用業務任務卡方式完成「整備完成並上架」
```

### 4.2 車輛頁入口

當車輛符合條件時，車輛頁顯示：

```text
整備完成並上架
```

目前入口條件：

```text
車輛已儲存
車輛狀態 = 整備中
車輛已入庫
```

按下後開啟：

```text
used_car_erp.guided_listing.open(frm)
```

### 4.3 Dialog 欄位

Dialog 以業務語意顯示：

```text
車輛資訊
上架日期
底價
開價
銷售備註
```

對應欄位：

| Dialog 欄位 | Used Car Vehicle 欄位 |
| --- | --- |
| 上架日期 | `listing_date` |
| 底價 | `floor_price` |
| 開價 | `asking_price` |
| 銷售備註 | `sales_note` |
| 車輛狀態 | `status` |

### 4.4 成功後行為

送出後寫入：

```text
listing_date
floor_price
asking_price
sales_note
status = 上架中
```

成功訊息：

```text
車輛已上架
```

成功後刷新表單。

---

## 5. Browser smoke 結果

使用者已完成 browser smoke，結果通過。

確認項目：

```text
Dialog 可正常開啟
可完成上架
listing_date 成功寫回
floor_price 成功寫回
asking_price 成功寫回
sales_note 成功寫回
status 成功變為 上架中
成功訊息顯示「車輛已上架」
```

並確認業務 UI 未暴露以下會計 / 技術字詞：

```text
Money Flow
Voucher Draft
Journal Entry
Sales Invoice
GL Entry
Stock Entry
debit
credit
會計科目
預收款沖轉
15-1
formal delivery
```

---

## 6. 驗證紀錄

Step 5A runtime 實作時已執行：

```text
python -m json.tool used_car_erp/used_car_erp/doctype/used_car_vehicle/used_car_vehicle.json
git diff --check
python -m compileall used_car_erp/hooks.py
```

結果：

```text
passed
```

未執行：

```text
JS lint
```

原因：

```text
used_car_erp app 根目錄沒有 package.json 或既有 JS lint 指令
```

未執行：

```text
bench migrate
```

原因：

```text
Step 5A runtime 未新增 schema；schema 已於 Step 5S 完成並 migrate
```

未執行：

```text
bench restart
```

原因：

```text
本次 runtime 不需要重啟
```

---

## 7. 產品邊界確認

本階段維持原產品邊界：

```text
業務歸業務
會計歸會計
```

「整備完成並上架」不是會計事件。

因此 Step 5A 不做：

```text
不建立 Money Flow
不建立 Voucher Draft
不建立 Journal Entry
不建立 Sales Invoice
不建立 Stock Entry
不修改 15-1 service
不修改管理利潤 service
不修改會計流程
不導向會計文件
不導向 ERPNext 技術文件
```

車輛頁只呈現業務任務卡與業務結果。

---

## 8. 已知限制

底價權限可見性尚未完整驗證。

目前已知規則：

```text
底價應只有主管可見
底價應只有主管可填
一般業務不可看到底價
一般業務不可修改底價
```

但 Step 5A 沒有做權限大改。

若需要落實底價權限，建議另開：

```text
P1-MVP-UX-OPS-2 Step 5P：Guided Listing Permission Boundary
```

Step 5P 應專注於角色、permlevel、欄位顯示與最小權限驗證，不應混入新的上架 runtime。

---

## 9. 目前穩定狀態

目前可視為：

```text
P1-MVP-UX-OPS-2 Step 5 completed
P1-MVP-UX-OPS-2 Step 5S completed
P1-MVP-UX-OPS-2 Step 5A completed
```

也就是：

```text
整備完成並上架任務卡規格已完成
listing_date schema 已補齊
Guided Listing Dialog runtime 已完成
browser smoke passed
```

---

## 10. 下一步建議

下一步有兩個合理方向：

### 方向 A：先補權限邊界

```text
P1-MVP-UX-OPS-2 Step 5P：Guided Listing Permission Boundary
```

適合情境：

```text
要正式區分主管與一般業務
要確保底價只有主管可見 / 可填
要避免一般業務看到內部底線價
```

### 方向 B：進下一張任務卡

```text
P1-MVP-UX-OPS-2 Step 6：Guided Reservation / Deposit Task Card Spec
```

適合情境：

```text
先推完整業務主流程
進入保留 / 收訂金任務卡規格
繼續保持一張卡處理一件事
```

建議若目前仍是開發 MVP，可以先進 Step 6 規格；若要開始分角色試用，則先做 Step 5P。

---

## 11. 建議 commit message

```text
docs: close guided listing dialog smoke
```

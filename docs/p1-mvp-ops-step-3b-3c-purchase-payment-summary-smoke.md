# P1-MVP-OPS Step 3B-3C：Purchase Payment Summary Browser Smoke Close

日期：2026-06-30  
專案：Used Car ERP / ERPNext / Frappe  
Repo：`ericzhan0819/used_car_erp`  
本機路徑：`~/frappe/frappe-bench/apps/used_car_erp`  
Site：`erpnext-coa.test`

---

## 1. 本文件目的

本文件記錄：

```text
P1-MVP-OPS Step 3B-3C：Purchase payment summary browser smoke
```

此階段只記錄 browser smoke 結果，不修改 runtime、不修改 schema、不新增正式會計流程。

---

## 2. 前置完成狀態

前一階段已完成：

```text
P1-MVP-OPS Step 3B-3B：Move purchase payment summary to purchase section
```

commit：

```text
f9c45e5 fix: move purchase payment summary to purchase section
```

已完成能力：

```text
購車付款摘要已由收支摘要上方移至採購 / 買入資料區附近
收支摘要恢復只顯示尚無收支紀錄或近 20 筆收支紀錄
新增購車付款成功後會同步刷新採購區摘要與收支摘要
```

---

## 3. Browser smoke 結果

Browser smoke 結果：

```text
passed
```

驗證來源：

```text
user-confirmed browser smoke passed
```

已確認：

```text
購車付款摘要出現在採購 / 買入資料區附近
購車付款摘要不再出現在收支摘要上方
收支摘要仍正常顯示尚無收支紀錄或近 20 筆收支紀錄
新增購車付款後，採購區摘要與收支摘要可更新
業務頁未新增 Voucher Draft / Journal Entry / Purchase Invoice / Payment Entry 操作入口
```

---

## 4. 本階段未做事項

本階段沒有做：

```text
不改 JS runtime
不改 Python service
不改 DocType schema
不新增 Dashboard 現金 / 銀行總餘額
不新增多銀行管理 UI
不新增資金轉帳
不新增月結批次付款
不建立 Voucher Draft
不建立 Journal Entry
不建立 Purchase Invoice
不建立 Payment Entry
不處理 Payment Reconciliation
不處理 advance account warning
不改管理毛利成本計算
不改 15-1 計算
```

---

## 5. 目前產品語意結論

購車付款摘要位置定調：

```text
購車付款摘要屬於採購 / 買入資料區。
```

原因：

```text
購車價 = 採購事實
購車付款 = 採購款項履約狀態
待付購車款 = 採購應付狀態
```

收支摘要定位：

```text
收支摘要只作為車輛交易明細 / 營運事實列表，不承擔採購狀態摘要。
```

---

## 6. 下一步建議

下一步建議：

```text
P1-MVP-OPS Step 3C：Cash account balance foundation
```

建議先做文件規格，不直接上 runtime：

```text
盤點 Used Car Cash Account 期初餘額
盤點 Money Flow 已付款 / 部分付款 / 待付款對資金餘額的影響
定義現金 / 主要銀行 / 其他 的 read-only balance 計算邊界
定義哪些金流類型進資金餘額
定義哪些狀態不進資金餘額
不新增正式會計文件
不處理 Payment Entry / Journal Entry / Reconciliation
```

---

## 7. 結論

Step 3B-3C 結論：

```text
Purchase payment summary browser smoke passed。
購車付款摘要位置已符合產品語意，位於採購 / 買入資料區附近。
收支摘要已恢復為交易明細列表。
P1-MVP-OPS Step 3B 可視為完成採購付款輸入、摘要與位置修正閉環。
```

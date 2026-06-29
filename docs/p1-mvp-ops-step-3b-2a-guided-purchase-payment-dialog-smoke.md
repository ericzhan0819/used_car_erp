# P1-MVP-OPS Step 3B-2A：Guided Purchase Payment Dialog Browser Smoke Close

日期：2026-06-30  
專案：Used Car ERP / ERPNext / Frappe  
Repo：`ericzhan0819/used_car_erp`  
本機路徑：`~/frappe/frappe-bench/apps/used_car_erp`  
Site：`erpnext-coa.test`

---

## 1. 本文件目的

本文件記錄：

```text
P1-MVP-OPS Step 3B-2A：Guided Purchase Payment Dialog Browser Smoke Close
```

此階段只記錄 browser smoke 結果與 metadata 同步注意事項，不修改 runtime、不修改 schema、不新增會計流程。

---

## 2. 前置完成狀態

前一階段已完成：

```text
P1-MVP-OPS Step 3B-2：Guided Purchase Payment Dialog
```

已完成能力：

```text
車輛頁新增「新增購車付款」按鈕
新增 shared guided purchase payment Dialog
接線至 create_purchase_payment_money_flow
成功後刷新車輛頁收支摘要
```

commit：

```text
4aa3dc4 feat: add guided purchase payment dialog
```

---

## 3. Browser smoke 結果

本次 smoke 結果：

```text
passed after metadata sync
```

已確認：

```text
車輛頁「新增購車付款」按鈕可用
Guided Purchase Payment Dialog 可正常開啟
成功建立購車付款紀錄
成功後車輛頁收支摘要可刷新並顯示購車付款
業務頁未新增 Voucher Draft / Journal Entry / Purchase Invoice / Payment Entry 操作入口
```

---

## 4. 遇到的問題

第一次建立購車付款時出現：

```text
金流類型 cannot be "購車付款". It should be one of "訂金收款", "尾款收款", "貸款撥款", "退款", "其他", "整備支出", "維修支出", "美容支出", "代辦支出", "拍場支出", "其他支出"
```

判斷原因：

```text
Used Car Money Flow.flow_type Select options 已在 repo JSON 更新，但 site DB metadata 尚未同步。
```

這不是 Dialog 接線錯誤，也不是 `create_purchase_payment_money_flow` service 邏輯錯誤。

---

## 5. 解法

執行 metadata 同步後通過：

```bash
cd ~/frappe/frappe-bench
bench --site erpnext-coa.test migrate
bench --site erpnext-coa.test clear-cache
bench restart
```

或等價的小範圍方式：

```bash
cd ~/frappe/frappe-bench
bench --site erpnext-coa.test reload-doc used_car_erp doctype used_car_money_flow
bench --site erpnext-coa.test clear-cache
bench restart
```

本案實務結論：

```text
即使未新增欄位，只要 DocType Select options 有變更，也需要 migrate 或 reload-doc 讓 site DB metadata 同步。
```

---

## 6. 本階段未做事項

本階段沒有做：

```text
不改 JS Dialog runtime
不改 Python service
不改 DocType schema
不新增 Dashboard 現金 / 銀行餘額
不新增購車付款摘要統計
不建立 Voucher Draft
不建立 Journal Entry
不建立 Purchase Invoice
不建立 Payment Entry
不處理 Payment Reconciliation
不處理 advance account warning
```

---

## 7. 下一步建議

下一步建議：

```text
P1-MVP-OPS Step 3B-3：Vehicle purchase payment summary polish
```

建議範圍：

```text
在車輛頁或收支摘要附近補單車購車付款摘要
顯示購車價 / 已記錄購車付款 / 待付款差額
仍不做 Dashboard 總餘額
仍不做正式會計文件
仍不把購車付款重複算入管理毛利成本
```

---

## 8. 結論

Step 3B-2A 結論：

```text
Guided Purchase Payment Dialog runtime 可用。
購車付款可建立為 Used Car Money Flow。
本次唯一問題是 site metadata 未同步，已由 migrate / reload-doc 類操作解決。
Step 3B-2 可視為 browser smoke close。
```

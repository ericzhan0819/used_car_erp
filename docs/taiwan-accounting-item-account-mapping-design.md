# Taiwan Accounting Item Account Mapping Design

Last reviewed: 2026-06-14

Phase: `P1-ACC-2`

本文件定義 `Taiwan Accounting Item Account Mapping`，用來把 ERPNext Account 對應到台灣官方會計項目代號，供未來報表、匯出與會計師檢查資料使用。

---

## 1. Responsibility split

ERPNext Account 是實際記帳科目，承載 Journal Entry、Sales Invoice、Payment Entry 與 GL Entry 的會計 runtime。

Taiwan Accounting Item Code 是台灣官方報表 / 申報分類代號，使用官方 code 作為 document name。

Taiwan Accounting Item Account Mapping 是兩者之間的分類對照層：

```text
ERPNext Account
→ Taiwan Accounting Item Code
→ 台灣官方報表 / 申報分類
```

---

## 2. Mapping key

Mapping 一律使用 `Taiwan Accounting Item Code.code` / document name 作為對應鍵。

`item_name` 不是唯一鍵，不能作為查找、覆蓋或 duplicate 判斷依據。

原因：官方中文名稱可能重複或相似，但官方代號不同。例如：

```text
0100005 營業成本
0300090 營業成本
```

兩者名稱相同，但代表不同官方 code，必須可同時存在並可分別 mapping。

---

## 3. Cardinality

允許多個 ERPNext Account 對應同一個 Taiwan Accounting Item Code。

例如多個銀行科目都可對應：

```text
0201112 銀行存款
```

這符合實務上公司會把不同銀行帳戶拆成多個 ERPNext posting account，但官方申報分類集中到同一項目的情境。

---

## 4. Duplicate rules

同一 company、同一 account、同一 mapping_purpose 僅允許一筆 active mapping。

這避免同一個 ERPNext posting account 在同一用途下被分類到多個官方代號，造成報表歸類不明。

同一 company、同一 mapping_purpose 僅允許一筆 active default mapping。

這讓未來報表或手動建議值可以有單一預設對應，但不限制其他非預設 mapping 存在。

---

## 5. Runtime boundary

此 mapping 不會改變任何 ERPNext accounting runtime。

本階段不修改：

```text
GL Entry
Sales Invoice
Journal Entry
Payment Entry
Sales Taxes and Charges Template
Chart of Accounts
```

也不會自動套用 mapping 到既有文件、不建立會計分錄、不提交文件、不調整稅務 template。

---

## 6. Account safety

Mapping 只接受同公司、非群組、未停用的 ERPNext Account。

Root account 不可編輯、不應 disable，也不應被拿來做 posting mapping。

此 DocType 不修改 ERPNext Account、不建立 Chart of Accounts、不 disable root account、不 disable 任何 ERPNext 內建 Account。

---

## 7. Future usage

未來報表可用此 mapping 產生會計師檢查資料：

```text
ERPNext GL Entry
→ Account
→ Taiwan Accounting Item Account Mapping
→ Taiwan Accounting Item Code
→ 報表 / 匯出 / 會計師檢查資料
```

正式申報分類仍需由會計或會計師確認；本 mapping layer 只提供結構化對照資料。

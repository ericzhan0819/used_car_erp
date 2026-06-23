# P1-MVP-UX-OPS-2 Step 3B-FIX-2：Stock Entry Difference Account Gate

## 1. 問題

Guided intake 入庫時曾出現：

```text
At row #1: you have selected the Difference Account 0100005-UC - 中古車銷貨成本 - O, which is a Cost of Goods Sold type account.
```

## 2. Root cause

`VehicleStockService` 曾 fallback 到銷貨成本科目。

ERPNext 不允許 `account_type = Cost of Goods Sold` 的 Account 作為 Stock Entry Difference Account，因此 Guided intake 在建立車輛後進入入庫階段失敗，可能留下半成品。

## 3. 修正

- 不再 fallback 到銷貨成本科目。
- Stock Entry Difference Account 必須使用有效的 `Company.stock_adjustment_account`。
- Validator 明確拒絕 `account_type = Cost of Goods Sold`。
- Guided intake 在建立車輛、入庫與切換整備中的流程外層增加 savepoint rollback safety。
- Repo 內未找到既有 `frappe.db.savepoint` 或 `rollback(save_point=...)` 寫法；本次依 Frappe v15 API 使用 `frappe.db.savepoint(name)` 與 `frappe.db.rollback(save_point=name)`。

## 4. 不做事項

- 不建立會計科目。
- 不修改 COA。
- 不自動清理殘留測試資料。
- 不修改 Dialog UI。
- 不做 Workspace shortcut。

## 5. 下一步

```text
P1-MVP-UX-OPS-2 Step 3B-SMOKE-RETRY
```

由使用者手動重測 guided intake。

若仍失敗，再依新錯誤開小修。

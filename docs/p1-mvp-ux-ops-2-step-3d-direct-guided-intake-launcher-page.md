# P1-MVP-UX-OPS-2 Step 3D：Direct Guided Intake Launcher Page

## 1. 本階段目的

本階段修正總覽入口，讓使用者在 `/app/總覽` 點「新增買入車輛」後直接開始填表，不需要先進入車輛列表再點一次按鈕。

## 2. 問題

Step 3C 的過渡方案是：

```text
總覽 → Used Car Vehicle List → 再點一次新增買入車輛
```

此流程多一次點擊，不符合任務卡片式 UX。使用者期待從總覽點任務入口後，就直接開始填寫新增買入車輛資料。

## 3. 修正

新增 Page：

```text
guided-vehicle-intake
```

Workspace shortcut 改為：

```text
新增買入車輛 → guided-vehicle-intake Page
```

Page 載入後自動開啟 Step 1 / Step 2 Dialog，並保留 Page primary action「開始新增」，讓使用者關閉 Dialog 後可重新開啟。

## 4. 現有限制

本階段可接受 Page JS 與 List View JS 有少量重複 Dialog code。

未來若 Dialog 邏輯繼續擴張，應抽成 shared launcher/helper，避免重複維護。

## 5. Workspace DB 套用注意事項

本機經驗顯示，單純 `bench migrate` 未必會把 `used_car_overview.json` 寫入 site DB。

本次 Workspace JSON 套用到 `erpnext-coa.test` 時，需使用 `import-doc`。

建議指令：

```bash
bench --site erpnext-coa.test import-doc apps/used_car_erp/used_car_erp/used_car_erp/workspace/used_car_overview/used_car_overview.json
bench --site erpnext-coa.test clear-cache
```

## 6. 不做事項

- 不改 backend
- 不改 DocType JSON
- 不改 List View button
- 不新增其他任務卡
- 不改會計流程
- 不做資料清理

## 7. 下一步

下一步可考慮：

```text
P1-MVP-UX-OPS-2 Step 4：Preparation Expense Task Card Spec
```

# P1-MVP-UX-OPS-2 Step 3C：Overview Shortcut Guided Intake

## 1. 本階段目的

本階段只修正總覽入口，讓 `/app/總覽` 的常用作業不再導向 `Used Car Vehicle` 原生 New Form。

本階段不修改 Dialog、不修改 guided backend，也不調整入庫、整備或會計流程。

## 2. 問題

舊 shortcut：

```text
新增車輛 → Used Car Vehicle New Form
```

問題：

- 會繞過 Guided Vehicle Intake Dialog。
- 會讓業務回到完整 ERPNext DocType 表單。

這不符合目前 UX 主線：業務端應使用任務卡片式輸入，不直接面對完整 ERPNext DocType 新增表單。

## 3. 修正

新 shortcut：

```text
新增買入車輛 → Used Car Vehicle List
```

使用者進入 Used Car Vehicle List 後，再點 List View 上的：

```text
新增買入車輛
```

開啟 Step 1 / Step 2 Dialog，完成 guided vehicle intake。

## 4. 過渡限制

本階段不是直接從 Workspace 打開 Dialog。

直接 Workspace → Dialog 需要 custom Page 或額外 route mechanism，暫不做。

目前接受的過渡 UX：

```text
總覽 → 新增買入車輛 shortcut → Used Car Vehicle List → 新增買入車輛 Dialog
```

## 5. 不做事項

- 不新增 custom Page。
- 不新增 redirect。
- 不改 guided backend。
- 不改 List Dialog。
- 不新增其他任務卡。
- 不改會計流程。

## 6. 下一步

下一步可依使用感受決定：

```text
P1-MVP-UX-OPS-2 Step 3D：Direct Guided Intake Page / Dialog Launcher
```

或先進：

```text
P1-MVP-UX-OPS-2 Step 4：Preparation Expense Task Card
```

本次不決定下一步。

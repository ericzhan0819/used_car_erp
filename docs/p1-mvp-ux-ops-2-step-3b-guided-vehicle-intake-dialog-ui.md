# P1-MVP-UX-OPS-2 Step 3B：Guided Vehicle Intake Dialog UI

## 1. 本階段目的

本階段只做新增買入車輛的最小 Dialog UI，讓業務可用 Step 1 / Step 2 完成新增車輛資料輸入，並呼叫 Step 3A backend orchestrator。

本階段不做 Page、Workspace 或 Dashboard 大改，也不改 DocType JSON 與 backend orchestrator。

## 2. UI 入口

入口在 `Used Car Vehicle` List View。

按鈕名稱：

```text
新增買入車輛
```

按下後開啟新增車輛 Dialog。

## 3. Dialog Flow

```text
Step 1：車輛基本資料
Step 2：收購資料
```

Step 1 收集：

- 廠牌
- 車型
- 年式
- 車牌
- VIN / 車身號碼
- 里程
- 顏色

Step 2 收集：

- 購車價
- 買入來源
- 供應商 / 原車主
- 收購業務
- 牌照稅已繳
- 燃料稅已繳
- 有未清償貸款
- 有欠稅 / 罰款
- 禁止異動
- 動保已註銷
- 已繳銷牌照
- 需要證件確認

## 4. Payload

Dialog 呼叫 Step 3A backend orchestrator：

```text
used_car_erp.used_car_erp.services.guided_vehicle_intake_service.run_guided_vehicle_intake
```

送出的 payload 語意：

- `brand`：廠牌
- `model`：車型
- `year`：年式
- `license_plate`：車牌
- `vin`：VIN / 車身號碼
- `mileage`：里程，後端寫入 `mileage_km`
- `color`：顏色
- `purchase_price`：購車價
- `purchase_source_type`：買入來源，空白時預設 `個人`
- `supplier`：供應商 / 原車主
- `seller`：供應商 / 原車主，後端可映射到原車主姓名
- `purchase_staff`：收購業務
- `license_tax_paid`：牌照稅已繳
- `fuel_tax_paid`：燃料稅已繳
- `has_unpaid_loan`：有未清償貸款
- `has_tax_penalty`：有欠稅 / 罰款
- `registration_restricted`：禁止異動
- `insurance_cancelled`：動保已註銷
- `plate_cancelled`：已繳銷牌照
- `need_document_check`：需要證件確認

## 5. 成功結果

成功後系統完成：

```text
車輛已建立
車輛已入庫
狀態進入整備中
導向新車輛頁
```

UI 顯示：

```text
車輛已建立並進入整備中
```

## 6. 不做事項

- 不做 Workspace shortcut
- 不做自訂 Page
- 不做整備支出任務卡
- 不做上架任務卡
- 不做訂金任務卡
- 不做尾款任務卡
- 不做成交任務卡
- 不做會計作業
- 不改 DocType JSON
- 不改 backend orchestrator

## 7. 下一步

下一步才考慮：

```text
P1-MVP-UX-OPS-2 Step 3C：Guided Vehicle Intake Workspace Shortcut / Polish
```

或依測試結果先修 Dialog UX。

# P1-MVP-UX-OPS-2 Step 3A：Guided Vehicle Intake Backend Orchestrator

## 1. 本階段目的

本階段只建立 `backend orchestrator`，供後續新增車輛任務卡呼叫。

本階段不做 Dialog UI、不做 Page、不改 Workspace、不改 DocType JSON，也不修改車輛表單 JS。

## 2. Runtime 邊界

本階段 runtime 只負責薄 orchestration：

- 建立 `Used Car Vehicle`
- 呼叫既有入庫 service
- 呼叫既有整備狀態 service
- 不重寫 Stock Entry / Item / Serial No
- 不直接建立 Stock Entry / Item / Serial No
- 不建立 Sales Invoice / Journal Entry / Voucher Draft / Money Flow
- 不改 DocType JSON

既有入庫由 `VehicleIntakeService.complete_intake` 處理。

整備狀態由 `VehicleListingService.start_preparation` 處理。

## 3. Payload 欄位

Step 1：車輛基本資料

| 語意欄位 | 實際 fieldname | 備註 |
| --- | --- | --- |
| brand / 廠牌 | `brand` | 直接寫入車輛主檔。 |
| model / 車型 | `model` | 直接寫入車輛主檔。 |
| year / 年式 | `year` | 直接寫入車輛主檔。 |
| license_plate / 車牌 | `license_plate` | 可空白。 |
| vin / VIN / 車身號碼 | `vin` | backend orchestrator 會阻擋空白。 |
| mileage / 里程 | `mileage_km` | payload 同時支援 `mileage` 與 `mileage_km`，寫入 `mileage_km`。 |
| color / 顏色 | `color` | 直接寫入車輛主檔。 |

Step 2：收購資料

| 語意欄位 | 實際 fieldname | 備註 |
| --- | --- | --- |
| purchase_price / 購車價 | `purchase_price` | 必須大於 0。 |
| purchase_source_type / 買入來源 | `purchase_source_type` | 空白時預設為 `個人`。 |
| supplier / 供應商 | `supplier` | 適用同行、拍賣場或其他供應商情境。 |
| seller / 原車主 | `original_owner_name` | 目前只映射原車主姓名；原車主電話可用 `original_owner_phone` 後續補入 UI。 |
| purchase_staff / 收購業務 | `purchase_staff` | 直接寫入採購人員。 |
| 牌照稅已繳 | `license_tax_paid` | checklist flag。 |
| 燃料稅已繳 | `fuel_tax_paid` | checklist flag。 |
| 有未清償貸款 | `has_unpaid_loan` | checklist flag。 |
| 有欠稅 / 罰款 | `has_tax_penalty` | checklist flag。 |
| 禁止異動 | `registration_restricted` | checklist flag。 |
| 動保已註銷 | `insurance_cancelled` | checklist flag。 |
| 已繳銷牌照 | `plate_cancelled` | checklist flag。 |
| 需要證件確認 | `need_document_check` | checklist flag。 |
| 監理 / 稅務備註 | `registration_note` | optional note。 |

待補欄位：

- `seller` 目前只能映射到 `original_owner_name`；若任務卡需要同時輸入原車主電話，應使用既有 `original_owner_phone`，不新增欄位。
- 其他監理 / 稅務細節若現有 fieldname 不足，需另開 DocType 欄位設計任務。

## 4. 成功結果

成功後系統完成：

```text
車輛建立
正式入庫
狀態進入整備中
回傳車輛 route
```

成功回傳包含：

```python
{
    "status": "success",
    "vehicle": vehicle.name,
    "vehicle_status": "整備中",
    "route": ["Form", "Used Car Vehicle", vehicle.name],
    "message": "車輛已建立並進入整備中",
}
```

## 5. 失敗情境

- payload 空白會被拒絕。
- 缺 VIN / 車身號碼會被拒絕。
- 缺購車價或購車價小於等於 0 會被拒絕。
- 既有入庫失敗時不吞錯，由 service 直接回傳清楚錯誤。
- 整備狀態切換失敗時不吞錯，由 service 直接回傳清楚錯誤。

## 6. 下一步

下一步才是：

```text
P1-MVP-UX-OPS-2 Step 3B：Guided Vehicle Intake Dialog UI
```

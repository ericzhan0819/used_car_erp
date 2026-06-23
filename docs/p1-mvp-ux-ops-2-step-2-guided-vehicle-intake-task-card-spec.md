# P1-MVP-UX-OPS-2 Step 2：Guided Vehicle Intake Task Card Spec

## 1. 本文件目的

本文件只定義「新增車輛」任務卡，不定義整備支出、上架、收訂金、收尾款、成交或會計作業流程。

目標：

- 讓業務用任務卡完成新增車輛
- 不讓業務直接面對完整 Used Car Vehicle DocType
- 不暴露會計文件、會計術語與技術欄位
- 建立車輛後自動完成入庫並進入整備中
- 為後續 Step 3 實作提供明確邊界

## 2. UX 原則

- 一張卡處理一件事
- 一次只問目前步驟需要的欄位
- 車輛基本資料與收購資料分開
- Step 1 完成後才進 Step 2
- 只有阻擋邏輯才顯示 banner
- 一般提示放欄位旁
- 業務頁禁止顯示會計技術字詞
- 本任務卡不顯示會計術語，只顯示業務可理解的車輛與收購資料

## 3. 任務入口

車輛頁 / 總覽入口可用：

- `新增車輛`
- `新增買入車輛`

建議：

- 車輛列表或總覽快捷使用 `新增買入車輛`
- Dialog / Task Card 標題使用 `新增車輛`

## 4. Flow Overview

```text
新增車輛
→ Step 1：車輛基本資料
→ 下一步
→ Step 2：收購資料
→ 送出
→ 建立 Used Car Vehicle
→ 自動完成入庫
→ 狀態進入整備中
→ 回到車輛頁或顯示建立成功
```

## 5. Step 1：車輛基本資料

Step 1 只收車輛識別與基本規格，不顯示採購、售車、會計或系統連結欄位。

| UI 顯示名稱 | 可能對應 fieldname | 是否必填 | 備註 |
| --- | --- | --- | --- |
| 廠牌 | `brand` | 產品需求建議必填；現有 DocType 未標必填 | 車輛列表已使用此欄位。 |
| 車型 | `model` | 產品需求建議必填；現有 DocType 未標必填 | 車輛列表已使用此欄位。 |
| 年式 | `year` | 產品需求建議必填；現有 DocType 未標必填 | 現有欄位型別為 Int。 |
| 車牌 | `license_plate` | 選填；現有 DocType 未標必填 | 可先空白，部分買入車輛可能尚未確認車牌。 |
| VIN / 車身號碼 | `vin` | 入庫前建議必填；現有 DocType 未標必填 | 現有完成入庫確認文案要求確認 VIN，Serial No 通常對應 VIN / 車身號碼；Step 3 實作前需確認缺 VIN 是否阻擋入庫。 |
| 里程 | `mileage_km` | 產品需求建議必填；現有 DocType 未標必填 | UI 可顯示為「里程」，底層欄位為 KM。 |
| 顏色 | `color` | 選填；現有 DocType 未標必填 | 現有 label 為「外觀顏色」。 |

Step 1 按鈕：

- `下一步`
- `取消`

Step 1 validation：

- VIN / 車身號碼若現有入庫邏輯必須要有，應標為必填。
- 目前 `Used Car Vehicle` DocType 只有 `status` 標為必填；上述車輛基本資料欄位在 DocType 層未標必填。
- 任務卡可基於產品需求提高必填門檻，但 Step 3 實作前需確認這些阻擋是否會影響現有建車流程。
- 本文件不做 runtime 判斷，只記錄規格。

## 6. Step 2：收購資料

Step 2 只收買入事實與監理 / 稅務旗標，不顯示底層會計文件、正式文件狀態或 ERPNext 技術連結。

買入來源：

- 個人
- 同行
- 拍賣場
- 其他

預設值：

- 個人

| UI 顯示名稱 | 可能對應 fieldname | 是否必填 | 備註 |
| --- | --- | --- | --- |
| 購車價 | `purchase_price` | 入庫前建議必填；現有 DocType 未標必填 | 購車價只代表買進車輛本身價格，不包含整備、維修、美容、拍場費、代辦費或其他後續費用。 |
| 買入來源 | `purchase_source_type` | 建議必填 | 現有預設值為「個人」，選項為個人、同行、拍賣場、其他；後端會依此初步推導稅務模式。 |
| 供應商 / 原車主 | `supplier` / `original_owner_name` / `original_owner_phone` | 依來源情境；現有 DocType 未標必填 | 若來源是同行或拍賣場，可使用 `supplier`；若來源是個人，可使用原車主姓名 / 電話。Step 3 需決定 UI 如何切換。 |
| 收購業務 | `purchase_staff` | 建議必填或預設目前使用者；現有 DocType 未標必填 | 現有 label 為「採購人員」，型別為 User。 |
| 監理 / 稅務旗標 checklist | 見第 7 節 | 選填，風險項依實際狀況勾選 | 本任務卡可全部顯示 checkbox。 |

補充：

- `source` 是現有「來源」欄位，選項包含來店、介紹、網路、車商、客戶換購、拍賣、其他；它不是 Step 2 指定的「買入來源」主欄位。
- `purchase_type` 是現有「採購類型」欄位，選項包含公司買進、委售、客戶換購、拍賣、其他；本任務卡暫不要求顯示。
- 不要新增欄位；若後續發現 `supplier` / 原車主不足以承載需求，再另開任務處理欄位設計。

## 7. 監理 / 稅務旗標 checklist

本任務卡中可以全部顯示 checkbox，讓業務在新增車輛時一次確認。一般車輛檢視模式仍只高亮風險項目。

| UI 顯示名稱 | 可能對應 fieldname | 是否必填 | 備註 |
| --- | --- | --- | --- |
| 牌照稅已繳 | `license_tax_paid` | 選填 | 正常狀態，不應高調警告。 |
| 燃料稅已繳 | `fuel_tax_paid` | 選填 | 正常狀態，不應高調警告。 |
| 有未清償貸款 | `has_unpaid_loan` | 選填 | 風險項目，需紅 / 橘色提示。 |
| 有欠稅 / 罰款 | `has_tax_penalty` | 選填 | 風險項目，需紅 / 橘色提示。 |
| 禁止異動 | `registration_restricted` | 選填 | 風險項目，需紅 / 橘色提示。 |
| 動保已註銷 | `insurance_cancelled` | 選填 | 風險項目，需紅 / 橘色提示。 |
| 已繳銷牌照 | `plate_cancelled` | 選填 | 風險項目，需紅 / 橘色提示。 |
| 需要證件確認 | `need_document_check` | 選填 | 風險項目，需紅 / 橘色提示。 |

注意：

- `license_tax_paid` / `fuel_tax_paid` 屬於正常狀態，不應高調警告。
- 風險項目才需要紅 / 橘色提示。
- 現有車輛表單在檢視模式只顯示已勾選的風險欄位；任務卡輸入模式可全部顯示 checkbox。

## 8. 完成送出後的系統動作

送出後目標行為：

- 建立 Used Car Vehicle
- 自動完成入庫
- 狀態進入整備中

本文件不決定具體實作方式。Step 3 實作前需要確認：

- 現有「完成入庫」按鈕使用 `used_car_vehicle.js` 的 `add_complete_intake_button`，並呼叫 `used_car_erp.used_car_erp.services.vehicle_intake_service.complete_intake`。
- 是否已有 whitelisted method 可供 Dialog 呼叫；目前按鈕呼叫的 `complete_intake` 需在 service 檔確認裝飾與參數。
- 自動入庫是否需要 Item / Serial No / Stock Entry。
- 缺 VIN 是否會阻擋入庫。
- 缺購車價是否會阻擋入庫。
- 建立完成後要 redirect 到車輛頁，還是留在總覽。
- 若入庫失敗，是否保留草稿車輛。
- 自動完成入庫後，是否要直接呼叫既有「開始整備」邏輯，或由 intake service 直接把狀態推進整備中。

## 9. 錯誤與提示規則

頁首 banner 只用於：

- 必填欄位缺漏
- 無法入庫
- 車輛狀態不允許操作
- 監理 / 稅務風險阻擋流程

欄位旁提示用於：

- 買入來源說明
- 15-1 背景推導說明
- VIN / 車身號碼用途
- 購車價用途

不要用藍色 banner 顯示一般說明。

## 10. 禁止出現的字詞

本任務卡不得顯示：

- Sales Invoice
- Journal Entry
- Voucher Draft
- Money Flow
- GL Entry
- 借方 / 貸方
- 會計科目
- 預收款沖轉
- submit
- cancel
- amend

## 11. 實作方案候選

本節只做分析，不實作。

### 方案 A：Frappe Dialog

優點：

- 改動小
- 適合 Step 3 最小實作
- 不需要新增 Page
- 可從 Workspace / 車輛列表按鈕呼叫

缺點：

- 複雜度高時可維護性較差
- 多步 UI 需要 JS 管理 state

### 方案 B：自訂 Page

優點：

- 可做更完整的任務卡 UX
- 後續可擴展多步流程
- 更接近真正業務工作台

缺點：

- 改動較大
- 需要 route / page 設計
- 較不適合第一個小步

本階段建議結論：

`Step 3 最小實作優先使用 Frappe Dialog；等任務卡流程穩定後，再考慮自訂 Page。`

## 12. Step 3 實作邊界建議

下一步實作只做：

- 新增車輛 Dialog
- Step 1 / Step 2
- 建立 Used Car Vehicle
- 嘗試沿用既有入庫邏輯
- 成功後狀態進入整備中
- 成功後導向車輛頁

下一步不做：

- 整備支出任務卡
- 上架任務卡
- 訂金任務卡
- 尾款任務卡
- 成交任務卡
- 會計作業
- 會計文件
- Workspace 大改
- Dashboard 大改
- 權限大改

## 13. 驗收標準

文件層驗收：

- 已明確列出 Step 1 欄位
- 已明確列出 Step 2 欄位
- 已明確列出 checklist 欄位
- 已列出可能 fieldname
- 已列出必填規則
- 已列出送出後系統動作
- 已列出 Step 3 實作邊界
- 已確認不碰 runtime

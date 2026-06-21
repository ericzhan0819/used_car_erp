# P1-MVP-OPS-1 Used Car Main Flow Smoke

Date: 2026-06-22

Phase: `P1-MVP-OPS-1`

Status: Step 1 checklist defined / documentation only

## 1. Purpose

`P1-MVP-OPS-1` turns the work back from `P1-UX-TAX-7` accounting UX cleanup to the used-car MVP main operations flow.

This phase does not expand accounting UX. The goal is to use a manual browser smoke checklist to confirm whether the current used-car operations flow is usable from a real user's point of view:

```text
總覽
→ 車輛建檔
→ 入庫
→ 上架
→ 保留
→ 訂金 / 尾款
→ 確認成交
→ 建立 Sales Invoice 草稿
→ 會計作業查看售車會計候選
```

Step 1 only defines the checklist and recording format. Actual browser smoke is the next step.

## 2. Scope

This step only defines documentation / QA checklist.

No runtime changes are included:

```text
不改 JS
不改 Python service
不改 DocType JSON
不改 Workspace JSON
不改 hooks.py
不改 permission
不跑 migration
不新增 accounting runtime
不新增 tax runtime
```

If the manual smoke finds missing data or unclear UX, record the gap first. Do not fix runtime as part of Step 1.

## 3. Stable information architecture

Current information architecture is fixed as:

```text
總覽 = 經營狀態 Dashboard
車輛管理 = 車輛 CRUD / 車輛狀態入口
會計作業 = 會計待辦與正式會計入口
```

`總覽` is the status landing page. It should not become a tax screen, accounting task center, or old custom dashboard redirect target.

`車輛管理` is the operational vehicle entry. It should carry vehicle list, new vehicle, and status shortcuts.

`會計作業` is where accounting review and formal accounting follow-up should live.

## 4. Main smoke path

Manual browser smoke should follow this path in order:

```text
/app/總覽
→ 車輛管理 / 新增車輛
→ 建立 Used Car Vehicle
→ 填 VIN / 車身號碼、購車價、入庫必要資料
→ 完成入庫
→ 庫存中
→ 開始整備或直接上架
→ 上架中
→ 建立訂金保留
→ 建立訂金金流與傳票草稿
→ 會計作業確認訂金傳票草稿
→ 建立尾款收款
→ 會計作業確認尾款傳票草稿
→ 成交前條件已滿足
→ 確認成交
→ 車輛變成已售出
→ 建立 Sales Invoice 草稿
→ 前往 /app/formal-sale-accounting-candidates
→ 會計作業查看售車會計候選
```

The smoke target is usability and route continuity. It is not a data creation script and not an accounting close test.

## 5. Browser smoke checklist

| Step | 入口 / route | 操作 | Expected result | Notes / gap to record |
|---|---|---|---|---|
| 1 | `/app/總覽` | 開啟總覽 | 顯示經營狀態 Dashboard、6 張 Number Card 與常用作業 | 記錄卡片缺漏、route 錯誤或仍出現舊 dashboard 入口 |
| 2 | `/app/車輛管理` | 開啟車輛管理 | 顯示車輛列表、新增車輛與狀態快速入口 | 記錄 shortcut 缺漏或文案不清楚 |
| 3 | `/app/車輛管理` / 新增車輛 | 點新增車輛 | 開啟新的 `Used Car Vehicle` 表單 | 記錄入口是否不直覺 |
| 4 | `Used Car Vehicle` new form | 填 VIN / 車身號碼、購車價、入庫必要資料並儲存 | 車輛可儲存，保留草稿 / 尚未入庫狀態 | 記錄必填欄位不清楚或缺少提示 |
| 5 | `Used Car Vehicle` form | 執行完成入庫 | 建立 / 綁定 Item、Stock Entry、Serial No，車輛變成庫存中 | 若不能建立資料，記錄錯誤與缺 fixture，不在 Step 1 修資料 |
| 6 | `Used Car Vehicle` form | 從庫存中開始整備或直接上架 | 車輛可進入整備中或上架中 | 記錄按鈕出現時機或文案問題 |
| 7 | `Used Car Vehicle` form | 將整備中車輛上架 | 車輛變成上架中 | 記錄流程是否需要多餘操作 |
| 8 | 上架中車輛 | 建立訂金保留 | 建立 `Used Car Reservation`，車輛變成保留中 | 記錄 customer / 金額 / 日期欄位是否不清楚 |
| 9 | 保留中車輛 | 建立訂金金流與傳票草稿 | 建立訂金 `Used Car Money Flow` 與 `Used Car Voucher Draft` | 記錄是否找不到建立金流入口 |
| 10 | `/app/會計作業` | 開啟待審核傳票草稿並確認訂金入帳 | 會計可找到訂金傳票草稿並建立正式會計傳票 | 記錄正式確認入口缺漏或文案不清楚 |
| 11 | 保留中車輛 | 建立尾款收款 | 建立尾款金流與尾款傳票草稿 | 記錄是否能從車輛頁找到尾款入口 |
| 12 | `/app/會計作業` | 確認尾款傳票草稿 | 會計可找到尾款傳票草稿並建立正式會計傳票 | 記錄會計待辦是否能區分訂金 / 尾款 |
| 13 | 保留中車輛 | 檢查成交前條件 | 畫面可判斷訂金與尾款已入帳，成交前條件已滿足 | 記錄條件提示是否不足 |
| 14 | 保留中車輛 | 確認成交 | 車輛變成已售出，保留單標記已完成 | 記錄確認成交按鈕出現時機是否正確 |
| 15 | 已售出車輛 | 建立 Sales Invoice 草稿 | 建立 Draft Sales Invoice，不 submit、不出庫、不沖轉 | 記錄 readiness blocker 或欄位缺漏 |
| 16 | 已售出車輛 | 點 `前往售車會計候選` 或直接開 route | 開啟 `/app/formal-sale-accounting-candidates` | 記錄 route-only button 是否缺漏 |
| 17 | `/app/formal-sale-accounting-candidates` | 查看售車會計候選 | 頁面維持 read-only，顯示售車會計候選或 empty state | 記錄候選分類、文案或 read-only 邊界問題 |

## 6. Entry checklist

Manual smoke must check these entry points before testing deep workflow details.

| Entry | Expected result | Gap to record |
|---|---|---|
| `/app/總覽` | 顯示 6 張 Number Card：在庫、庫存中、整備中、上架中、保留中、已售出；顯示常用作業 | 卡片缺漏、常用作業缺漏、仍導向舊 dashboard |
| `/app/車輛管理` | 可看到車輛列表、新增車輛、庫存中車輛、整備中車輛、上架中車輛、保留中車輛、已售出車輛 shortcut | shortcut 缺漏、route 錯誤、文案不清楚 |
| `/app/會計作業` | 可看到待審核傳票草稿、單車摘要候選、售車會計候選、金流紀錄、傳票草稿、正式會計傳票 | 會計待辦入口缺漏或正式會計入口混亂 |
| `/app/formal-sale-accounting-candidates` | 頁面可開啟並維持 read-only | 若出現 mutation action 或不能 refresh，記錄為 gap |

## 7. Vehicle state checklist

Manual smoke should find or create vehicles covering these states if the site already has suitable fixtures.

Do not create fixtures only for Step 1. If a state is missing, record it as a gap.

```text
草稿 / 尚未入庫
庫存中
整備中
上架中
保留中
已售出、尚無 Sales Invoice
已售出、有 Sales Invoice 草稿
Sales Invoice 已提交
預收款沖轉 Journal Entry 草稿
已完成 / 預收款沖轉已提交
```

For each state, record:

```text
是否找得到車輛
是否有清楚下一步
是否出現不該出現的高衝擊會計 mutation button
是否有 route-only 入口前往會計作業
是否需要最小 UX / shortcut / 文案修正
```

## 8. Expected current boundaries

Business-side operations currently expected to be usable:

```text
建立車輛
完成入庫
整備 / 上架
建立訂金保留
建立尾款收款
確認成交
建立 Sales Invoice 草稿
```

Formal voucher confirmation belongs in `會計作業`.

Sold vehicle pages should not display these high-impact mutation buttons:

```text
確認銷售發票並出庫
建立預收款沖轉草稿
確認預收款沖轉入帳
修復 Sales Invoice 草稿連結
```

The formal sale accounting follow-up entry is:

```text
會計作業
→ 售車會計候選
→ /app/formal-sale-accounting-candidates
```

`建立 Sales Invoice 草稿` can remain on the sold vehicle page because it creates a draft only. It must not submit Sales Invoice, create GL Entry, create Stock Ledger Entry, create Payment Entry, create Delivery Note, or create advance settlement Journal Entry.

## 9. Gap recording format

Use this format during Step 2 browser smoke:

```text
Route / record:
State:
Observed behavior:
Expected behavior:
Gap type:
Minimal next fix:
Out of scope for this smoke: yes / no
```

Allowed gap types:

```text
找不到入口
文案不清楚
按鈕出現時機不對
資料狀態缺 fixture
功能可用但流程不直覺
需要最小 UX / shortcut / 文案修正
超出本 smoke 階段，不能處理
```

Keep the proposed fix minimal. Prefer route, shortcut, button timing, or copy cleanup before any backend change.

## 10. Non-goals

This phase does not do any of the following:

```text
不新增 accounting runtime
不新增 tax runtime
不重寫 vehicle lifecycle
不做 dashboard 大改
不改 Workspace JSON
不改 Vehicle JS
不建立 / 提交 / 修改 ERPNext 文件
不修 Sales Invoice / Journal Entry runtime
不處理中文 Number Card export path warning
```

Also do not run migration, build, restart, or data-writing bench commands as part of this Step 1 documentation task.

## 11. Suggested Step 2

Step 2 should run the checklist manually in the browser on `erpnext-coa.test`.

Record:

```text
哪一步找不到入口
哪一步文案不清楚
哪一步按鈕出現時機不對
哪一步缺 fixture
哪一步需要最小 shortcut / UX patch
哪一步超出 smoke 階段不能處理
```

Only after the smoke result is recorded should a later step decide the smallest safe runtime, Workspace, or UX patch.

## 12. Suggested commit message

```text
docs: define used car main flow smoke checklist
```

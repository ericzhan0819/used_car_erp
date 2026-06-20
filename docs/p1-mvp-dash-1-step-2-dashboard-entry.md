# P1-MVP-DASH-1 Step 2 Dashboard Entry

Last reviewed: 2026-06-21

Step 2 adds the minimal `中古車管理 Dashboard` Desk Page entry.

Implemented scope:

- New Page route: `used-car-management-dashboard`.
- Static placeholder metric cards for inventory, available, reserved, and monthly sold counts.
- Static placeholder pending task cards for purchase data, final collection, accounting confirmation, and 15-1 review.
- Shortcut cards to existing entry points: new vehicle, vehicle inventory, summary candidates, and accounting operations.

Boundary:

- No data service or dashboard aggregation was added.
- No accounting, tax, permission, or runtime behavior was changed.
- No ERPNext document is created, submitted, cancelled, or modified by this page.

## Step 2A Top-level Overview Workspace

Step 2A adds a top-level `總覽` Workspace as the used-car ERP control entry in the Desk Sidebar.

- New top-level Workspace label / title: `總覽`.
- Dashboard can be reached directly from the Sidebar through the `中古車管理 Dashboard` shortcut.
- The Workspace only includes minimal shortcuts for dashboard, vehicle list, and new vehicle.
- No runtime, service, hooks, permission, accounting, or tax behavior was changed.

## Step 2B Overview Workspace as Dashboard Home

Step 2B changes `總覽` from a shortcut-only Workspace into the Dashboard home surface.

- Sidebar users opening `總覽` now see dashboard-like sections immediately.
- The first screen includes `簡易報表`, `待處理事項`, and `快捷入口` sections.
- Static placeholder shortcut cards are used for MVP metric and pending-task areas; no real data service or runtime aggregation was added.
- The `中古車管理 Dashboard` shortcut remains available under `快捷入口`, but users no longer need to click it to understand the main dashboard structure.
- No sidebar redirect, app include JS, hooks.py change, Python service, whitelisted method, DocType JSON, permission, accounting runtime, or tax runtime change was added.

## Step 3A Overview Workspace Read-only Metric Filters

Step 3A changes the `總覽` Workspace simple report shortcuts from placeholder counts to read-only `stats_filter` counts based on existing `Used Car Vehicle.status` values.

- `簡易報表` now uses explicit Workspace `stats_filter` values for inventory, available, reserved, and sold vehicle counts.
- `本月售出` was renamed to `已售出車輛` because the native Workspace shortcut filter is not suitable for a safe dynamic current-month statistic in this MVP step.
- `待處理事項` no longer shows unfiltered `Used Car Vehicle` counts; it uses a Page shortcut placeholder to avoid fake or misleading pending-task counts until safe task-specific fields or services are introduced.
- `會計作業` shortcut 暫不放入 `總覽` Workspace，因目前站台 Workspace shortcut type 不支援 `Workspace`，會計入口仍保留在 Sidebar 的 Accounting / 會計作業。
- No runtime, service, hooks, permission, accounting, tax, DocType JSON, or dashboard Page JS behavior was changed.

## Step 4A Overview One-click Dashboard Route

Step 4A keeps the Sidebar `總覽` entry provided by the Workspace, but routes users directly to the Dashboard Page.

- Opening `/app/總覽` redirects to `/app/used-car-management-dashboard` through Desk route handling.
- `used-car-management-dashboard` remains the internal route / Page name to avoid Frappe route and Page name risk.
- The user-facing Dashboard name is now consistently `總覽`.
- `中古車管理 Dashboard` is no longer used as a user-facing name.
- This step only cleans up route and naming behavior.
- No runtime write behavior, accounting, tax, 15-1, pending-task cards, DocType JSON, Python service, or whitelisted method was added.

## Step 4B Vehicle Workspace Naming And Overview Navigation Cleanup

Step 4B separates the Dashboard home entry from vehicle CRUD / status navigation.

- `中古車管理` user-facing Workspace wording was changed to `車輛管理`.
- `車輛管理` no longer includes the Dashboard shortcut.
- `總覽` is the Dashboard home entry.
- `總覽` navigation now uses Sidebar click interception plus direct URL `replace` fallback to avoid browser back being trapped by a redirect loop.
- This step does not add runtime write behavior, service code, accounting / tax runtime changes, or DocType JSON changes.

## Step 4B hotfix: Vehicle Workspace document rename

The user-facing `中古車管理` Workspace rename must also rename the Workspace document itself to `車輛管理`; changing only label/title causes `/app/車輛管理` to fail with "Page 車輛管理 not found". The Workspace document was renamed from `中古車管理` to `車輛管理`, while the repository path remains `workspace/used_car_management/used_car_management.json`.

## Step 4C Native Overview Workspace Dashboard

Step 4C changes `總覽` back to a native Workspace dashboard instead of routing through a custom Page.

- `總覽` no longer redirects to `used-car-management-dashboard`.
- `/app/總覽` itself is the native Workspace dashboard entry.
- 庫存狀態 uses Frappe native read-only Number Cards for `在庫`, `庫存中`, `整備中`, `上架中`, `保留中`, and `已售出` counts.
- `used-car-management-dashboard` Page is temporarily kept, but it is no longer the required Sidebar `總覽` entry path.
- The home surface does not show `15-1`, accounting confirmation, pending-task, or low-level workflow wording.
- This step does not add write behavior, service code, permission changes, DocType JSON changes, accounting runtime, or tax runtime.

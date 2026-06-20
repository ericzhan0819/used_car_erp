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

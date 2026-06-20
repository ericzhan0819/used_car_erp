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

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

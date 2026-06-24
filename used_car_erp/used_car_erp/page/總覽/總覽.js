frappe.pages["總覽"].on_page_load = function (wrapper) {
  const page = frappe.ui.make_app_page({
    parent: wrapper,
    title: "總覽",
    single_column: true,
  });

  const $body = $(page.body);
  $body.html(`
    <div class="used-car-overview" style="padding: 16px;">
      <div class="frappe-card" style="padding: 18px; margin-bottom: 16px;">
        <div class="text-muted" style="font-size: 13px;">中古車業務操作面板</div>
        <h2 style="margin: 4px 0 0;">總覽</h2>
      </div>
      <div style="margin-bottom: 18px;">
        <h4 style="margin-bottom: 12px;">庫存狀態卡</h4>
        <div class="overview-status-grid" style="display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 12px;">
          ${render_status_card("整備中", "查看整備中車輛", "整備中")}
          ${render_status_card("上架中", "查看上架中車輛", "上架中")}
          ${render_status_card("保留中", "查看保留中車輛", "保留中")}
          ${render_status_card("已售出", "查看已售出車輛", "已售出")}
          ${render_sales_card()}
        </div>
      </div>
      <div>
        <h4 style="margin-bottom: 12px;">常用作業</h4>
        <div class="frappe-card" style="padding: 16px; display: flex; gap: 10px; flex-wrap: wrap;">
          <button class="btn btn-primary" data-action="new-intake">新增買入車輛</button>
          <button class="btn btn-default" data-action="vehicle-list">車輛列表</button>
        </div>
      </div>
    </div>
  `);

  $body.on("click", "[data-status]", function () {
    frappe.set_route("List", "Used Car Vehicle", { status: $(this).attr("data-status") });
  });

  $body.on("click", "[data-action='new-intake']", function () {
    if (!used_car_erp.guided_vehicle_intake || !used_car_erp.guided_vehicle_intake.open_dialog) {
      frappe.msgprint("新增買入車輛表單尚未載入，請重新整理後再試。");
      return;
    }

    used_car_erp.guided_vehicle_intake.open_dialog();
  });

  $body.on("click", "[data-action='vehicle-list']", function () {
    frappe.set_route("List", "Used Car Vehicle");
  });
};

function render_status_card(title, subtitle, status) {
  return `
    <button class="frappe-card text-left" data-status="${frappe.utils.escape_html(status)}" style="padding: 16px; border: 0; cursor: pointer;">
      <div class="text-muted" style="font-size: 12px;">${frappe.utils.escape_html(subtitle)}</div>
      <div style="font-size: 22px; font-weight: 600; margin-top: 6px;">${frappe.utils.escape_html(title)}</div>
    </button>
  `;
}

function render_sales_card() {
  return `
    <div class="frappe-card" style="padding: 16px;">
      <div class="text-muted" style="font-size: 12px;">待銷售日期欄位確認</div>
      <div style="font-size: 22px; font-weight: 600; margin-top: 6px;">本月銷售</div>
      <div class="text-muted" style="margin-top: 4px;">—</div>
    </div>
  `;
}

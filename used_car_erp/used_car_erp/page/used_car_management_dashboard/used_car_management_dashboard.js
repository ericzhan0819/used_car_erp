frappe.pages["used-car-management-dashboard"].on_page_load = function (wrapper) {
  const page = frappe.ui.make_app_page({
    parent: wrapper,
    title: "中古車管理 Dashboard",
    single_column: true,
  });

  const $body = $(page.body);
  $body.html(`
    <div class="used-car-management-dashboard" style="padding: 16px;">
      <div class="frappe-card" style="padding: 16px; margin-bottom: 12px;">
        <div style="font-weight: 600; margin-bottom: 6px;">中古車業務主控台</div>
        <div class="text-muted" style="font-size: 12px; line-height: 1.7;">
          目前是 MVP 入口，先提供中古車管理常用資訊區塊與操作捷徑。<br>
          本頁不建立、不提交、不修改任何文件，也不讀取即時統計資料。
        </div>
      </div>

      ${render_used_car_dashboard_section("簡易報表", [
        { label: "庫存車輛數", value: "—" },
        { label: "待售車輛數", value: "—" },
        { label: "保留中車輛", value: "—" },
        { label: "本月售出", value: "—" },
      ])}

      ${render_used_car_dashboard_section("待處理事項", [
        { label: "待補購車資料", value: "待接資料" },
        { label: "待收尾款", value: "待接資料" },
        { label: "待會計確認", value: "待接資料" },
        { label: "待 15-1 判斷", value: "待接資料" },
      ])}

      <div class="frappe-card" style="padding: 16px;">
        <div style="font-weight: 600; margin-bottom: 12px;">快捷入口</div>
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 12px;">
          ${render_used_car_dashboard_shortcut("新增車輛", "建立新的中古車車輛資料", "new_vehicle")}
          ${render_used_car_dashboard_shortcut("車輛庫存", "查看中古車車輛清單", "vehicle_inventory")}
          ${render_used_car_dashboard_shortcut("單車摘要候選", "查看唯讀摘要候選清單", "summary_candidates")}
          ${render_used_car_dashboard_shortcut("會計作業", "前往既有會計作業 Workspace", "accounting_operations")}
        </div>
      </div>
    </div>
  `);

  bind_used_car_dashboard_shortcuts($body);
};

function render_used_car_dashboard_section(title, cards) {
  return `
    <div class="frappe-card" style="padding: 16px; margin-bottom: 12px;">
      <div style="font-weight: 600; margin-bottom: 12px;">${frappe.utils.escape_html(title)}</div>
      <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 12px;">
        ${cards.map(render_used_car_dashboard_metric_card).join("")}
      </div>
    </div>
  `;
}

function render_used_car_dashboard_metric_card(card) {
  return `
    <div style="border: 1px solid var(--border-color); border-radius: 8px; padding: 12px; min-height: 82px;">
      <div class="text-muted" style="font-size: 12px; margin-bottom: 8px;">${frappe.utils.escape_html(card.label)}</div>
      <div style="font-size: 22px; font-weight: 600;">${frappe.utils.escape_html(card.value)}</div>
    </div>
  `;
}

function render_used_car_dashboard_shortcut(label, description, action) {
  return `
    <button class="btn btn-default text-left" data-dashboard-action="${frappe.utils.escape_html(action)}" style="height: auto; padding: 12px; white-space: normal;">
      <div style="font-weight: 600; margin-bottom: 6px;">${frappe.utils.escape_html(label)}</div>
      <div class="text-muted" style="font-size: 12px; line-height: 1.5;">${frappe.utils.escape_html(description)}</div>
    </button>
  `;
}

function bind_used_car_dashboard_shortcuts($body) {
  $body.find("button[data-dashboard-action]").on("click", function () {
    const action = $(this).attr("data-dashboard-action");

    if (action === "new_vehicle") {
      frappe.set_route("Form", "Used Car Vehicle", "new-used-car-vehicle");
      return;
    }

    if (action === "vehicle_inventory") {
      frappe.set_route("List", "Used Car Vehicle");
      return;
    }

    if (action === "summary_candidates") {
      frappe.set_route("vehicle-dashboard-summary-candidates");
      return;
    }

    if (action === "accounting_operations") {
      frappe.set_route("Workspaces", "會計作業");
    }
  });
}

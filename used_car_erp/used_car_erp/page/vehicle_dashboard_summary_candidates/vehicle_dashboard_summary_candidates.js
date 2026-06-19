frappe.pages["vehicle-dashboard-summary-candidates"].on_page_load = function (wrapper) {
  const page = frappe.ui.make_app_page({
    parent: wrapper,
    title: "單車摘要候選",
    single_column: true,
  });

  const state = {
    limit: 10,
    report: null,
  };

  const $body = $(page.body);
  $body.html(`
    <div class="vehicle-dashboard-summary-candidates" style="padding: 16px;">
      <div class="frappe-card" style="padding: 16px; margin-bottom: 12px;">
        <div style="font-weight: 600; margin-bottom: 4px;">會計作業候選清單</div>
        <div class="text-muted" style="font-size: 12px;">
          唯讀彙整：會計狀態、15-1 稅務估算、管理損益。此頁只讀候選資料，不建立、不提交、不修改任何文件。
        </div>
      </div>
      <div data-field="candidate-status"></div>
      <div data-field="candidate-table"></div>
    </div>
  `);

  page.set_primary_action("重新整理", () => load_vehicle_dashboard_candidates(page, state, $body), "refresh");

  load_vehicle_dashboard_candidates(page, state, $body);
};

function load_vehicle_dashboard_candidates(page, state, $body) {
  render_vehicle_dashboard_candidate_loading($body);

  frappe.call({
    method:
      "used_car_erp.used_car_erp.services.vehicle_dashboard_summary_service.find_vehicle_dashboard_summary_candidates",
    args: {
      limit: state.limit,
    },
    callback(response) {
      state.report = response.message || {};
      render_vehicle_dashboard_candidate_report(page, state, $body);
    },
    error() {
      render_vehicle_dashboard_candidate_error($body);
    },
  });
}

function render_vehicle_dashboard_candidate_loading($body) {
  $body.find('[data-field="candidate-status"]').html(`
    <div class="frappe-card" style="padding: 12px; margin-bottom: 12px;">
      <span class="indicator blue">讀取中</span>
      <span class="text-muted" style="margin-left: 8px;">正在讀取候選清單...</span>
    </div>
  `);
  $body.find('[data-field="candidate-table"]').html("");
}

function render_vehicle_dashboard_candidate_error($body) {
  $body.find('[data-field="candidate-status"]').html(`
    <div class="frappe-card" style="padding: 12px; margin-bottom: 12px;">
      <span class="indicator red">讀取失敗</span>
      <span class="text-muted" style="margin-left: 8px;">候選清單讀取失敗。此頁只提供唯讀資訊，不影響會計作業流程。</span>
    </div>
  `);
  $body.find('[data-field="candidate-table"]').html("");
}

function render_vehicle_dashboard_candidate_report(page, state, $body) {
  const report = state.report || {};
  const candidates = report.candidates || [];
  const source_statuses = report.source_statuses || {};
  const warnings = report.warnings || [];
  const blocking_errors = report.blocking_errors || [];

  $body.find('[data-field="candidate-status"]').html(`
    <div class="frappe-card" style="padding: 12px; margin-bottom: 12px;">
      <div style="display: flex; gap: 8px; align-items: center; flex-wrap: wrap;">
        ${render_vehicle_dashboard_candidate_status_badge("整體", report.status)}
        ${render_vehicle_dashboard_candidate_status_badge("會計", source_statuses.accounting_status)}
        ${render_vehicle_dashboard_candidate_status_badge("稅務", source_statuses.tax_estimate)}
        ${render_vehicle_dashboard_candidate_status_badge("損益", source_statuses.management_profit)}
      </div>
      ${render_vehicle_dashboard_candidate_messages("待處理", blocking_errors)}
      ${render_vehicle_dashboard_candidate_messages("提醒", warnings)}
    </div>
  `);

  if (!candidates.length) {
    $body.find('[data-field="candidate-table"]').html(`
      <div class="frappe-card" style="padding: 16px;">
        <div class="text-muted">目前沒有候選資料。</div>
      </div>
    `);
    return;
  }

  $body.find('[data-field="candidate-table"]').html(`
    <div class="frappe-card" style="padding: 0; overflow: hidden;">
      <div class="table-responsive">
        <table class="table table-bordered" style="margin: 0;">
          <thead>
            <tr>
              <th>車輛</th>
              <th>銷售發票</th>
              <th>來源</th>
              <th>會計狀態</th>
              <th>15-1 稅務估算狀態</th>
              <th>管理損益狀態</th>
              <th style="width: 120px;">動作</th>
            </tr>
          </thead>
          <tbody>
            ${candidates.map(render_vehicle_dashboard_candidate_row).join("")}
          </tbody>
        </table>
      </div>
      <div class="text-muted" style="font-size: 12px; padding: 12px;">
        此清單只呼叫 read-only candidate service；不建立、不提交、不取消、不寫回任何 ERPNext 文件。
      </div>
    </div>
  `);

  bind_vehicle_dashboard_candidate_actions($body);
}

function render_vehicle_dashboard_candidate_row(row) {
  const sources = row.sources || {};
  const accounting = sources.accounting_status || {};
  const tax = sources.tax_estimate || {};
  const profit = sources.management_profit || {};
  const target = row.vehicle || row.sales_invoice || "";

  return `
    <tr>
      <td>${escape_vehicle_dashboard_candidate_html(row.vehicle || "—")}</td>
      <td>${escape_vehicle_dashboard_candidate_html(row.sales_invoice || "—")}</td>
      <td>${render_vehicle_dashboard_candidate_sources(sources)}</td>
      <td>${escape_vehicle_dashboard_candidate_html(accounting.business_status || accounting.status || source_candidate_label(accounting))}</td>
      <td>${escape_vehicle_dashboard_candidate_html(tax.tax_estimate_status || tax.status || tax.tax_mode_applicability || source_candidate_label(tax))}</td>
      <td>${escape_vehicle_dashboard_candidate_html(profit.management_gross_profit_display || profit.status || source_candidate_label(profit))}</td>
      <td>
        ${render_vehicle_dashboard_candidate_action(row, target)}
      </td>
    </tr>
  `;
}

function render_vehicle_dashboard_candidate_sources(sources) {
  const labels = {
    accounting_status: "會計",
    tax_estimate: "稅務",
    management_profit: "損益",
  };

  return Object.keys(labels)
    .filter((key) => sources[key])
    .map((key) => `<span class="indicator blue" style="margin-right: 4px;">${labels[key]}</span>`)
    .join("") || "—";
}

function render_vehicle_dashboard_candidate_action(row, target) {
  if (!target) {
    return "—";
  }

  const doctype = row.vehicle ? "Used Car Vehicle" : "Sales Invoice";
  const label = row.vehicle ? "開啟車輛" : "開啟發票";

  return `
    <button class="btn btn-xs btn-default" data-doctype="${escape_vehicle_dashboard_candidate_html(doctype)}" data-name="${escape_vehicle_dashboard_candidate_html(target)}">
      ${escape_vehicle_dashboard_candidate_html(label)}
    </button>
  `;
}

function bind_vehicle_dashboard_candidate_actions($body) {
  $body.find("button[data-doctype][data-name]").on("click", function () {
    const doctype = $(this).attr("data-doctype");
    const name = $(this).attr("data-name");
    if (!doctype || !name) {
      return;
    }

    frappe.set_route("Form", doctype, name);
  });
}

function source_candidate_label(source) {
  return source && Object.keys(source).length ? "候選" : "—";
}

function render_vehicle_dashboard_candidate_status_badge(label, status) {
  if (!status) {
    return "";
  }

  const indicator = get_vehicle_dashboard_candidate_status_indicator(status);
  return `<span class="indicator ${indicator}">${escape_vehicle_dashboard_candidate_html(label)}: ${escape_vehicle_dashboard_candidate_html(status)}</span>`;
}

function render_vehicle_dashboard_candidate_messages(label, messages) {
  if (!messages || !messages.length) {
    return "";
  }

  return `
    <div style="border-top: 1px solid var(--border-color); margin-top: 10px; padding-top: 8px;">
      <div style="font-weight: 600; margin-bottom: 4px;">${escape_vehicle_dashboard_candidate_html(label)}</div>
      ${messages
        .map((message) => `<div class="text-muted" style="font-size: 12px;">${escape_vehicle_dashboard_candidate_html(message)}</div>`)
        .join("")}
    </div>
  `;
}

function get_vehicle_dashboard_candidate_status_indicator(status) {
  if (status === "pass" || status === "ready") {
    return "green";
  }
  if (status === "warning" || status === "unknown") {
    return "orange";
  }
  if (status === "fail" || status === "blocked") {
    return "red";
  }
  return "blue";
}

function escape_vehicle_dashboard_candidate_html(value) {
  if (value === undefined || value === null || value === "") {
    return "—";
  }

  return frappe.utils.escape_html(String(value));
}

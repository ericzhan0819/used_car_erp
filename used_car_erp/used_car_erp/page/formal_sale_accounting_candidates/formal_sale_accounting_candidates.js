frappe.pages["formal-sale-accounting-candidates"].on_page_load = function (wrapper) {
  const page = frappe.ui.make_app_page({
    parent: wrapper,
    title: "售車會計候選",
    single_column: true,
  });

  const state = {
    limit: 50,
    report: null,
  };

  const $body = $(page.body);
  $body.html(`
    <div class="formal-sale-accounting-candidates" style="padding: 16px;">
      <div class="frappe-card" style="padding: 16px; margin-bottom: 12px;">
        <div style="font-weight: 600; margin-bottom: 4px;">售車會計候選</div>
        <div class="text-muted" style="font-size: 12px; line-height: 1.7;">
          此頁只顯示售車會計候選，不建立、不提交、不修復任何 ERPNext 文件。
        </div>
      </div>
      <div data-field="candidate-status"></div>
      <div data-field="candidate-summary"></div>
      <div data-field="candidate-table"></div>
    </div>
  `);

  page.set_primary_action("重新整理", () => load_formal_sale_accounting_candidates(state, $body), "refresh");

  load_formal_sale_accounting_candidates(state, $body);
};

const FORMAL_SALE_ACCOUNTING_CATEGORY_LABELS = {
  needs_sales_invoice_recovery: "需技術修復",
  blocked: "需補資料 / blocked",
  needs_sales_invoice_submit: "待確認銷售發票並出庫",
  needs_advance_settlement_draft: "待建立預收款沖轉草稿",
  needs_advance_settlement_submit: "待確認預收款沖轉入帳",
};

const FORMAL_SALE_ACCOUNTING_CATEGORY_INDICATORS = {
  needs_sales_invoice_recovery: "orange",
  blocked: "red",
  needs_sales_invoice_submit: "blue",
  needs_advance_settlement_draft: "blue",
  needs_advance_settlement_submit: "blue",
};

function load_formal_sale_accounting_candidates(state, $body) {
  render_formal_sale_accounting_loading($body);

  frappe.call({
    method:
      "used_car_erp.used_car_erp.services.formal_sale_accounting_candidate_service.run_formal_sale_accounting_candidates",
    args: { limit: state.limit },
    callback(response) {
      state.report = response.message || {};
      render_formal_sale_accounting_report(state, $body);
    },
    error() {
      render_formal_sale_accounting_error($body);
    },
  });
}

function render_formal_sale_accounting_loading($body) {
  $body.find('[data-field="candidate-status"]').html(`
    <div class="frappe-card" style="padding: 12px; margin-bottom: 12px;">
      <span class="indicator blue">讀取中</span>
      <span class="text-muted" style="margin-left: 8px;">正在讀取售車會計候選...</span>
    </div>
  `);
  $body.find('[data-field="candidate-summary"]').html("");
  $body.find('[data-field="candidate-table"]').html("");
}

function render_formal_sale_accounting_error($body) {
  $body.find('[data-field="candidate-status"]').html(`
    <div class="frappe-card" style="padding: 12px; margin-bottom: 12px;">
      <span class="indicator red">讀取失敗</span>
      <span class="text-muted" style="margin-left: 8px;">無法載入候選資料。此頁只提供唯讀資訊，不影響既有會計流程。</span>
    </div>
  `);
  $body.find('[data-field="candidate-summary"]').html("");
  $body.find('[data-field="candidate-table"]').html("");
}

function render_formal_sale_accounting_report(state, $body) {
  const report = state.report || {};
  const candidates = report.candidates || [];
  const warnings = report.warnings || [];
  const blocking_errors = report.blocking_errors || [];

  $body.find('[data-field="candidate-status"]').html(`
    <div class="frappe-card" style="padding: 12px; margin-bottom: 12px;">
      <div style="display: flex; gap: 8px; align-items: center; flex-wrap: wrap;">
        ${render_formal_sale_accounting_status_badge("整體", report.status)}
      </div>
      ${render_formal_sale_accounting_messages("待處理", blocking_errors)}
      ${render_formal_sale_accounting_messages("提醒", warnings)}
    </div>
  `);

  $body.find('[data-field="candidate-summary"]').html(render_formal_sale_accounting_summary(report));

  if (!candidates.length) {
    $body.find('[data-field="candidate-table"]').html(`
      <div class="frappe-card" style="padding: 16px;">
        <div class="text-muted">目前沒有售車會計候選。</div>
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
              <th>分類</th>
              <th>車輛</th>
              <th>車號 / 車牌</th>
              <th>客戶</th>
              <th>成交價</th>
              <th>Sales Invoice</th>
              <th>Sales Invoice 狀態</th>
              <th>預收款沖轉 Journal Entry</th>
              <th>下一步</th>
              <th>阻擋原因 / 提醒</th>
              <th>最後更新時間</th>
              <th style="width: 220px;">操作</th>
            </tr>
          </thead>
          <tbody>
            ${candidates.map(render_formal_sale_accounting_candidate_row).join("")}
          </tbody>
        </table>
      </div>
      <div class="text-muted" style="font-size: 12px; padding: 12px;">
        此清單只呼叫 Step 3 read-only service；操作欄只做 route navigation，不建立、不提交、不修復、不回寫任何文件。
      </div>
    </div>
  `);

  bind_formal_sale_accounting_actions($body);
}

function render_formal_sale_accounting_summary(report) {
  const counts = report.category_counts || {};
  const cards = [
    { label: "候選總數", value: report.candidate_count || 0 },
    { label: "需技術修復", value: counts.needs_sales_invoice_recovery || 0 },
    { label: "需補資料 / blocked", value: counts.blocked || 0 },
    { label: "待確認銷售發票並出庫", value: counts.needs_sales_invoice_submit || 0 },
    { label: "待建立預收款沖轉草稿", value: counts.needs_advance_settlement_draft || 0 },
    { label: "待確認預收款沖轉入帳", value: counts.needs_advance_settlement_submit || 0 },
  ];

  return `
    <div class="frappe-card" style="padding: 16px; margin-bottom: 12px;">
      <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 12px;">
        ${cards.map(render_formal_sale_accounting_summary_card).join("")}
      </div>
    </div>
  `;
}

function render_formal_sale_accounting_summary_card(card) {
  return `
    <div style="border: 1px solid var(--border-color); border-radius: 8px; padding: 12px; min-height: 78px;">
      <div class="text-muted" style="font-size: 12px; margin-bottom: 8px;">${escape_formal_sale_accounting_html(card.label)}</div>
      <div style="font-size: 22px; font-weight: 600;">${escape_formal_sale_accounting_html(card.value)}</div>
    </div>
  `;
}

function render_formal_sale_accounting_candidate_row(row) {
  return `
    <tr>
      <td>${render_formal_sale_accounting_category(row)}</td>
      <td>${escape_formal_sale_accounting_html(row.vehicle)}</td>
      <td>${escape_formal_sale_accounting_html(format_formal_sale_accounting_vehicle_identity(row))}</td>
      <td>${escape_formal_sale_accounting_html(row.customer)}</td>
      <td>${escape_formal_sale_accounting_html(format_formal_sale_accounting_currency(row.sold_price))}</td>
      <td>${escape_formal_sale_accounting_html(row.sales_invoice)}</td>
      <td>${escape_formal_sale_accounting_html(format_formal_sale_accounting_invoice_status(row))}</td>
      <td>${escape_formal_sale_accounting_html(row.advance_settlement_journal_entry)}</td>
      <td>${escape_formal_sale_accounting_html(row.next_step)}</td>
      <td>${escape_formal_sale_accounting_html(format_formal_sale_accounting_messages(row))}</td>
      <td>${escape_formal_sale_accounting_html(row.modified)}</td>
      <td>${render_formal_sale_accounting_route_buttons(row)}</td>
    </tr>
  `;
}

function render_formal_sale_accounting_category(row) {
  const indicator = FORMAL_SALE_ACCOUNTING_CATEGORY_INDICATORS[row.category] || "blue";
  const label = row.category_label || FORMAL_SALE_ACCOUNTING_CATEGORY_LABELS[row.category] || row.category;
  return `<span class="indicator ${indicator}">${escape_formal_sale_accounting_html(label)}</span>`;
}

function format_formal_sale_accounting_vehicle_identity(row) {
  const parts = [row.stock_no, row.license_plate].filter(Boolean);
  return parts.length ? parts.join(" / ") : "";
}

function format_formal_sale_accounting_currency(value) {
  if (value === undefined || value === null || value === "") {
    return "";
  }
  return frappe.format(value, { fieldtype: "Currency" });
}

function format_formal_sale_accounting_invoice_status(row) {
  const status = row.sales_invoice_status || "";
  const docstatus = row.sales_invoice_docstatus;
  if (docstatus === undefined || docstatus === null) {
    return status;
  }
  return status ? `${status} / ${docstatus}` : `docstatus ${docstatus}`;
}

function format_formal_sale_accounting_messages(row) {
  const messages = [];
  if (row.blocking_reasons && row.blocking_reasons.length) {
    messages.push(...row.blocking_reasons);
  }
  if (row.warnings && row.warnings.length) {
    messages.push(...row.warnings);
  }
  return messages.join("；");
}

function render_formal_sale_accounting_route_buttons(row) {
  const routes = [];

  if (row.route_doctype && row.route_name) {
    routes.push({
      doctype: row.route_doctype,
      name: row.route_name,
      label: "開啟主要文件",
    });
  }

  if (row.vehicle) {
    routes.push({ doctype: "Used Car Vehicle", name: row.vehicle, label: "開啟車輛" });
  }
  if (row.sales_invoice) {
    routes.push({ doctype: "Sales Invoice", name: row.sales_invoice, label: "開啟 Sales Invoice" });
  }
  if (row.advance_settlement_journal_entry) {
    routes.push({
      doctype: "Journal Entry",
      name: row.advance_settlement_journal_entry,
      label: "開啟 Journal Entry",
    });
  }

  return unique_formal_sale_accounting_routes(routes)
    .map(render_formal_sale_accounting_route_button)
    .join(" ") || "—";
}

function unique_formal_sale_accounting_routes(routes) {
  const seen = new Set();
  return routes.filter((route) => {
    const key = `${route.doctype}::${route.name}`;
    if (!route.doctype || !route.name || seen.has(key)) {
      return false;
    }
    seen.add(key);
    return true;
  });
}

function render_formal_sale_accounting_route_button(route) {
  return `
    <button class="btn btn-xs btn-default" data-doctype="${escape_formal_sale_accounting_html(route.doctype)}" data-name="${escape_formal_sale_accounting_html(route.name)}" style="margin-bottom: 4px;">
      ${escape_formal_sale_accounting_html(route.label)}
    </button>
  `;
}

function bind_formal_sale_accounting_actions($body) {
  $body.find("button[data-doctype][data-name]").on("click", function () {
    const doctype = $(this).attr("data-doctype");
    const name = $(this).attr("data-name");
    if (!doctype || !name) {
      return;
    }

    frappe.set_route("Form", doctype, name);
  });
}

function render_formal_sale_accounting_status_badge(label, status) {
  if (!status) {
    return "";
  }

  const indicator = get_formal_sale_accounting_status_indicator(status);
  return `<span class="indicator ${indicator}">${escape_formal_sale_accounting_html(label)}: ${escape_formal_sale_accounting_html(status)}</span>`;
}

function render_formal_sale_accounting_messages(label, messages) {
  if (!messages || !messages.length) {
    return "";
  }

  return `
    <div style="border-top: 1px solid var(--border-color); margin-top: 10px; padding-top: 8px;">
      <div style="font-weight: 600; margin-bottom: 4px;">${escape_formal_sale_accounting_html(label)}</div>
      ${messages
        .map((message) => `<div class="text-muted" style="font-size: 12px;">${escape_formal_sale_accounting_html(message)}</div>`)
        .join("")}
    </div>
  `;
}

function get_formal_sale_accounting_status_indicator(status) {
  if (status === "pass") {
    return "green";
  }
  if (status === "partial") {
    return "orange";
  }
  if (status === "fail") {
    return "red";
  }
  return "blue";
}

function escape_formal_sale_accounting_html(value) {
  if (value === undefined || value === null || value === "") {
    return "—";
  }

  return frappe.utils.escape_html(String(value));
}

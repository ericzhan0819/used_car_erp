frappe.ui.form.on("Used Car Vehicle", {
  refresh(frm) {
    apply_vehicle_form_mode(frm);
  },

  after_save(frm) {
    frm._vehicle_edit_mode = false;
    apply_vehicle_form_mode(frm);
  },
});

const SYSTEM_READ_ONLY_FIELDS = [
  "stock_no",
  "total_cost",
  "gross_margin",
  "item",
  "serial_no",
  "stock_entry",
  "purchase_invoice",
  "sales_invoice",
  "formal_delivery_status",
  "formal_delivery_posting_date",
  "advance_settlement_journal_entry",
  "formal_delivery_completed_at",
  "formal_delivery_completed_by",
  "formal_delivery_note",
];

const LAYOUT_FIELD_TYPES = [
  "Section Break",
  "Column Break",
  "Tab Break",
  "HTML",
  "Button",
];

const SOLD_VEHICLE_TAX_METADATA_FIELDS = [
  "purchase_source_type",
  "vehicle_tax_mode",
  "purchase_document_type",
  "purchase_document_no",
  "tax_review_status",
  "tax_review_note",
];

const SALE_WORKFLOW_FIELDS = [
  "customer",
  "sold_price",
  "sold_date",
  "delivery_date",
  "expected_delivery_date",
  "sales_staff",
  "sales_note",
  "vehicle_tax_mode",
  "tax_review_status",
  "tax_review_note",
];

const FORMAL_ACCOUNTING_LOCKED_STATUSES = [
  "銷售發票已提交",
  "預收款沖轉草稿",
  "預收款沖轉已提交",
  "已完成",
];

const ACCOUNTING_TECHNICAL_FIELDS = [
  "completed_reservation",
  "completed_at",
  "completed_by",
  "completion_note",
  "deposit_money_flow",
  "deposit_voucher_draft",
  "deposit_journal_entry",
  "final_money_flow",
  "final_voucher_draft",
  "final_journal_entry",
  "formal_delivery_posting_date",
  "sales_invoice",
  "advance_settlement_journal_entry",
  "formal_delivery_completed_at",
  "formal_delivery_completed_by",
  "formal_delivery_note",
];

function apply_vehicle_form_mode(frm) {
  clear_vehicle_action_buttons(frm);
  set_vehicle_intake_intro(frm);
  apply_vehicle_cashflow_section_label(frm);
  render_vehicle_cashflow_inline_summary(frm);
  apply_tax_fields_visibility(frm);
  apply_purchase_fields_visibility(frm);
  apply_registration_flags_visibility(frm);
  apply_vehicle_business_descriptions(frm);
  hide_vehicle_accounting_surface(frm);
  hide_vehicle_technical_system_links(frm);

  if (frm.is_new()) {
    set_vehicle_fields_read_only(frm, false);
    return;
  }

  if (frm.doc.status === "已售出") {
    add_general_expense_money_flow_button(frm);
    add_sold_vehicle_primary_action_button(frm);
    set_vehicle_fields_read_only(frm, true);
    allow_sold_vehicle_tax_metadata_edit(frm);
    allow_sold_vehicle_sale_workflow_edit(frm);
    return;
  }

  if (is_reserved_vehicle(frm)) {
    load_active_reservation_for_reserved_vehicle(frm);
    add_general_expense_money_flow_button(frm);
    add_reserved_vehicle_secondary_buttons(frm);
    set_vehicle_fields_read_only(frm, true);

    if (frm._vehicle_edit_mode) {
      set_vehicle_fields_read_only(frm, false);

      frm.add_custom_button("取消編輯", () => {
        frm._vehicle_edit_mode = false;
        frm.reload_doc();
      });

      return;
    }

    frm.add_custom_button("編輯資料", () => {
      frm._vehicle_edit_mode = true;
      set_vehicle_fields_read_only(frm, false);
      frm.refresh_fields();
    });

    return;
  }

  add_non_sold_vehicle_primary_action_button(frm);
  add_general_expense_money_flow_button(frm);

  if (frm._vehicle_edit_mode) {
    set_vehicle_fields_read_only(frm, false);

    frm.add_custom_button("取消編輯", () => {
      frm._vehicle_edit_mode = false;
      frm.reload_doc();
    });

    return;
  }

  set_vehicle_fields_read_only(frm, true);

  frm.add_custom_button("編輯資料", () => {
    frm._vehicle_edit_mode = true;
    set_vehicle_fields_read_only(frm, false);
    frm.refresh_fields();
  });
}

function apply_tax_fields_visibility(frm) {
  ["sales_tax_section", "vehicle_tax_mode", "tax_review_status", "tax_review_note", "purchase_document_type"].forEach((fieldname) => {
    if (frm.fields_dict[fieldname]) {
      frm.toggle_display(fieldname, false);
    }
  });
}

function apply_purchase_fields_visibility(frm) {
  ["purchase_commission", "other_payable"].forEach((fieldname) => {
    if (frm.fields_dict[fieldname]) {
      frm.toggle_display(fieldname, false);
      frm.set_df_property(fieldname, "hidden", 1);
    }
  });
}

function apply_registration_flags_visibility(frm) {
  const risk_fields = [
    "has_unpaid_loan",
    "has_tax_penalty",
    "registration_restricted",
    "insurance_cancelled",
    "plate_cancelled",
    "need_document_check",
  ];

  if (frm._vehicle_edit_mode || frm.is_new()) {
    ["tax_registration_flags_section", "tax_registration_flags_column", ...risk_fields].forEach((fieldname) => {
      if (frm.fields_dict[fieldname]) {
        frm.toggle_display(fieldname, true);
      }
    });
    return;
  }

  const has_risk = risk_fields.some((fieldname) => Boolean(frm.doc[fieldname]));
  if (frm.fields_dict.tax_registration_flags_section) {
    frm.toggle_display("tax_registration_flags_section", has_risk);
  }
  if (frm.fields_dict.tax_registration_flags_column) {
    frm.toggle_display("tax_registration_flags_column", has_risk);
  }

  risk_fields.forEach((fieldname) => {
    if (frm.fields_dict[fieldname]) {
      frm.toggle_display(fieldname, Boolean(frm.doc[fieldname]));
    }
  });
}

function apply_vehicle_cashflow_section_label(frm) {
  if (frm.fields_dict.cashflow_summary_section) {
    frm.set_df_property("cashflow_summary_section", "label", "收支摘要");
  }
}

function render_vehicle_cashflow_inline_summary(frm) {
  const wrapper = get_vehicle_cashflow_summary_wrapper(frm);
  if (!wrapper) {
    return;
  }

  wrapper.find(".used-car-cashflow-inline-summary").remove();

  if (frm.is_new() || !frm.doc.name) {
    return;
  }

  const summary = $(render_vehicle_cashflow_summary_loading());
  wrapper.append(summary);

  frappe.call({
    method: "frappe.client.get_list",
    args: {
      doctype: "Used Car Money Flow",
      filters: {
        vehicle: frm.doc.name,
      },
      fields: [
        "name",
        "payment_date",
        "flow_type",
        "direction",
        "amount",
        "status",
        "evidence_attachment",
      ],
      order_by: "payment_date asc, modified asc",
      limit_page_length: 20,
    },
    callback(response) {
      summary.replaceWith(render_vehicle_cashflow_summary(response.message || []));
    },
    error() {
      summary.replaceWith(render_vehicle_cashflow_summary_error());
    },
  });
}

function get_vehicle_cashflow_summary_wrapper(frm) {
  const field = frm.fields_dict.cashflow_summary_section;
  if (!field || !field.wrapper) {
    return null;
  }

  return $(field.wrapper);
}

function render_vehicle_cashflow_summary_loading() {
  return `
    <div class="used-car-cashflow-inline-summary" style="margin: 10px 0 14px; padding: 12px; border: 1px solid var(--border-color); border-radius: 6px;">
      <div class="text-muted">正在讀取收支摘要...</div>
    </div>
  `;
}

function render_vehicle_cashflow_summary_error() {
  return `
    <div class="used-car-cashflow-inline-summary" style="margin: 10px 0 14px; padding: 12px; border: 1px solid var(--border-color); border-radius: 6px;">
      <div class="text-muted">收支摘要讀取失敗。此區塊只提供唯讀資訊，不影響車輛主流程操作。</div>
    </div>
  `;
}

function render_vehicle_cashflow_summary(records) {
  if (!records.length) {
    return `
      <div class="used-car-cashflow-inline-summary" style="margin: 10px 0 14px; padding: 12px; border: 1px solid var(--border-color); border-radius: 6px;">
        <div class="text-muted">尚無收支紀錄</div>
      </div>
    `;
  }

  const rows = records.map(render_vehicle_cashflow_summary_row).join("");
  return `
    <div class="used-car-cashflow-inline-summary" style="margin: 10px 0 14px; border: 1px solid var(--border-color); border-radius: 6px; overflow: hidden;">
      <div style="padding: 10px 12px; font-weight: 600; border-bottom: 1px solid var(--border-color);">近 20 筆收支紀錄</div>
      <div style="overflow-x: auto;">
        <table class="table table-bordered" style="margin: 0; min-width: 680px;">
          <thead>
            <tr>
              <th>日期</th>
              <th>類型</th>
              <th>金額</th>
              <th>狀態</th>
              <th>憑證</th>
              <th>金流編號</th>
            </tr>
          </thead>
          <tbody>${rows}</tbody>
        </table>
      </div>
    </div>
  `;
}

function render_vehicle_cashflow_summary_row(record) {
  const sign = get_vehicle_cashflow_amount_sign(record);
  const amount = format_vehicle_currency(record.amount || 0);
  return `
    <tr>
      <td>${escape_vehicle_dashboard_html(record.payment_date)}</td>
      <td>${escape_vehicle_dashboard_html(record.flow_type)}</td>
      <td style="text-align: right; white-space: nowrap;">${escape_vehicle_dashboard_html(`${sign}${amount}`)}</td>
      <td>${escape_vehicle_dashboard_html(record.status)}</td>
      <td>${record.evidence_attachment ? "有憑證" : "無憑證"}</td>
      <td>${escape_vehicle_dashboard_html(record.name)}</td>
    </tr>
  `;
}

function get_vehicle_cashflow_amount_sign(record) {
  if (record.direction === "收入") {
    return "+";
  }
  if (record.direction === "支出") {
    return "-";
  }

  const expense_flow_types = ["整備支出", "維修支出", "美容支出", "代辦支出", "拍場支出", "其他支出"];
  return expense_flow_types.includes(record.flow_type) ? "-" : "+";
}

function hide_vehicle_accounting_surface(frm) {
  const accounting_fields = [
    "accounting_status_summary_html",
    "accounting_status_section",
    "sales_invoice",
    "formal_delivery_status",
    "formal_delivery_posting_date",
    "advance_settlement_journal_entry",
    "formal_delivery_column",
    "formal_delivery_completed_at",
    "formal_delivery_completed_by",
    "formal_delivery_note",
    "deposit_voucher_draft",
    "deposit_journal_entry",
    "final_voucher_draft",
    "final_journal_entry",
  ];

  const accounting_section_keywords = [
    "會計",
    "Sales Invoice",
    "Journal Entry",
    "Voucher Draft",
    "傳票",
    "稅務估算",
    "正式交車",
    "formal delivery",
  ];

  accounting_fields.forEach((fieldname) => {
    if (!frm.fields_dict[fieldname]) {
      return;
    }

    frm.toggle_display(fieldname, false);
    frm.set_df_property(fieldname, "hidden", 1);
  });

  frm.meta.fields.forEach((df) => {
    if (!df.fieldname || !["Section Break", "Column Break", "HTML"].includes(df.fieldtype)) {
      return;
    }

    const text = [df.label, df.fieldname, df.options].filter(Boolean).join(" ");
    if (!accounting_section_keywords.some((keyword) => text.includes(keyword))) {
      return;
    }

    if (frm.fields_dict[df.fieldname]) {
      frm.toggle_display(df.fieldname, false);
      frm.set_df_property(df.fieldname, "hidden", 1);
    }
  });
}

function hide_vehicle_technical_system_links(frm) {
  [
    "system_links_section",
    "item",
    "serial_no",
    "stock_warehouse",
    "system_links_column",
    "stock_entry",
    "purchase_invoice",
  ].forEach((fieldname) => {
    if (!frm.fields_dict[fieldname]) {
      return;
    }

    frm.toggle_display(fieldname, false);
    frm.set_df_property(fieldname, "hidden", 1);
  });
}

function set_vehicle_fields_read_only(frm, read_only) {
  frm.meta.fields.forEach((df) => {
    if (!df.fieldname || LAYOUT_FIELD_TYPES.includes(df.fieldtype)) {
      return;
    }

    if (SYSTEM_READ_ONLY_FIELDS.includes(df.fieldname)) {
      // 系統產生與 ERPNext 關聯欄位必須持續唯讀，避免使用者覆寫後端同步結果。
      frm.set_df_property(df.fieldname, "read_only", 1);
      return;
    }

    frm.set_df_property(df.fieldname, "read_only", read_only ? 1 : 0);
  });

  frm.refresh_fields();
}

function allow_sold_vehicle_tax_metadata_edit(frm) {
  if (!can_edit_sold_vehicle_tax_metadata(frm)) {
    return;
  }

  SOLD_VEHICLE_TAX_METADATA_FIELDS.forEach((fieldname) => {
    frm.set_df_property(fieldname, "read_only", 0);
  });

  frm.refresh_fields(SOLD_VEHICLE_TAX_METADATA_FIELDS);
}

function allow_sold_vehicle_sale_workflow_edit(frm) {
  if (!can_edit_sold_vehicle_sale_workflow(frm)) {
    if (is_sold_vehicle_formally_locked(frm)) {
      frm.set_intro("此車已售出，售車資料已鎖定。", "orange");
    }
    return;
  }

  SALE_WORKFLOW_FIELDS.forEach((fieldname) => {
    if (frm.fields_dict[fieldname]) {
      frm.set_df_property(fieldname, "read_only", 0);
    }
  });

  frm.refresh_fields(SALE_WORKFLOW_FIELDS.filter((fieldname) => frm.fields_dict[fieldname]));
}

function apply_vehicle_business_descriptions(frm) {
  if (frm.fields_dict.sold_price) {
    frm.set_df_property("sold_price", "description", "成交價屬於售車流程，可作為後續收支與交車確認依據。");
  }
  if (frm.fields_dict.purchase_source_type) {
    frm.set_df_property("purchase_source_type", "description", "業務只需選擇買入來源；買入憑證類型由後續內部流程確認。");
  }
}

function can_edit_sold_vehicle_sale_workflow(frm) {
  return Boolean(!frm.is_new() && frm.doc.status === "已售出" && !is_sold_vehicle_formally_locked(frm));
}

function is_sold_vehicle_formally_locked(frm) {
  return Boolean(
    FORMAL_ACCOUNTING_LOCKED_STATUSES.includes(frm.doc.formal_delivery_status) ||
      frm.doc.formal_delivery_completed_at
  );
}

function can_edit_sold_vehicle_tax_metadata(frm) {
  const allowed_roles = ["System Manager", "Accounts Manager", "Accounts User"];
  const user_roles = frappe.user_roles || [];
  const has_allowed_role =
    frappe.session.user === "Administrator" ||
    allowed_roles.some((role) => user_roles.includes(role));

  return Boolean(
    !frm.is_new() &&
      frm.doc.status === "已售出" &&
      !is_sold_vehicle_formally_locked(frm) &&
      has_allowed_role
  );
}

function clear_vehicle_action_buttons(frm) {
  [
    "編輯資料",
    "取消編輯",
    "建立 ERPNext 商品",
    "正式入庫",
    "完成入庫",
    "開始整備",
    "直接上架",
    "整備完成並上架",
    "下架回庫存",
    "建立訂金保留",
    "建立尾款收款",
    "新增支出",
    "成交前檢查",
    "確認成交",
    "取消保留",
    "正式交車入帳前檢查",
    "建立 Sales Invoice 草稿",
    "開啟 Sales Invoice 草稿",
    "新增單車成本",
    "重新計算成本摘要",
    "重新整理損益與稅務估算",
    "重新整理交車前檢查",
    "正式交車提交前檢查",
    "檢查提交資格",
    "提交 Sales Invoice 並正式出庫",
    "確認銷售發票並出庫",
    "建立預收款沖轉傳票草稿",
    "建立預收款沖轉草稿",
    "提交預收款沖轉傳票",
    "確認預收款沖轉入帳",
    "修復 Sales Invoice 草稿連結",
    "修復銷售發票草稿連結",
    "開啟 Sales Invoice",
    "查看銷售發票",
    "開啟預收款沖轉傳票",
    "查看預收款沖轉傳票",
    "顯示會計技術欄位",
    "隱藏會計技術欄位",
    "顯示文件連結",
    "隱藏文件連結",
    "前往售車會計候選",
  ].forEach((label) => {
    frm.remove_custom_button(label);
  });
}

function render_accounting_status_summary(frm) {
  return;
}

function render_vehicle_dashboard_summary_loading(field) {
  field.$wrapper.html(`
    <div class="frappe-card" style="padding: 16px; margin-bottom: 12px;">
      <div style="font-weight: 600; margin-bottom: 6px;">單車摘要</div>
      <div class="text-muted">正在讀取會計狀態、15-1 稅務估算與管理損益摘要...</div>
    </div>
  `);
}

function render_vehicle_dashboard_summary_error(field) {
  field.$wrapper.html(`
    <div class="frappe-card" style="padding: 16px; margin-bottom: 12px;">
      <div style="font-weight: 600; margin-bottom: 6px;">單車摘要</div>
      <div class="text-muted">摘要讀取失敗。此區塊只提供唯讀資訊，不影響車輛主流程操作。</div>
    </div>
  `);
}

function render_vehicle_dashboard_summary(field, report) {
  const summary = report.vehicle_page_summary || {};
  const accounting = summary.accounting || {};
  const tax = summary.tax_15_1 || {};
  const profit = summary.management_profit || {};
  const warnings = report.warnings || [];
  const blocking_errors = report.blocking_errors || [];
  const cards = [
    {
      label: "會計狀態",
      status: accounting.status,
      rows: [
        ["目前狀態", accounting.business_status || "未處理"],
        ["下一步", accounting.next_action_label || "暫無下一步"],
        ["處理區域", accounting.next_action_area || "—"],
      ],
    },
    {
      label: "15-1 稅務估算",
      status: tax.status,
      rows: [
        ["可扣抵估算", format_vehicle_dashboard_money(tax.allowed_deduction_display)],
        ["預估營業稅", format_vehicle_dashboard_money(tax.estimated_business_tax_display)],
        ["適用狀態", tax.tax_mode_applicability || "待確認"],
      ],
    },
    {
      label: "管理損益",
      status: profit.status,
      rows: [
        ["管理毛利", format_vehicle_dashboard_money(profit.management_gross_profit_display)],
        ["毛利率", profit.management_gross_margin_rate_display || "—"],
        ["直接成本", format_vehicle_dashboard_money(profit.direct_cost_total)],
      ],
    },
  ];

  field.$wrapper.html(`
    <div class="frappe-card" style="padding: 16px; margin-bottom: 12px;">
      <div style="display: flex; justify-content: space-between; gap: 12px; align-items: flex-start; margin-bottom: 12px;">
        <div>
          <div style="font-weight: 600; margin-bottom: 4px;">單車摘要</div>
          <div class="text-muted" style="font-size: 12px;">唯讀彙整：會計狀態、15-1 稅務估算、管理損益</div>
        </div>
        <div style="display: flex; gap: 6px; flex-wrap: wrap; justify-content: flex-end;">
          ${render_vehicle_dashboard_status_badge("整體", report.status)}
          ${render_vehicle_dashboard_status_badge("會計", (report.service_statuses || {}).accounting_status)}
          ${render_vehicle_dashboard_status_badge("稅務", (report.service_statuses || {}).tax_estimate)}
          ${render_vehicle_dashboard_status_badge("損益", (report.service_statuses || {}).management_profit)}
        </div>
      </div>
      <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 12px;">
        ${cards.map(render_vehicle_dashboard_card).join("")}
      </div>
      ${render_vehicle_dashboard_messages("待處理", blocking_errors)}
      ${render_vehicle_dashboard_messages("提醒", warnings)}
      <div class="text-muted" style="font-size: 12px; margin-top: 12px;">
        此區塊只讀既有 summary service；不建立、不提交、不取消任何 ERPNext 文件，也不寫回車輛資料。
      </div>
    </div>
  `);
}

function render_vehicle_dashboard_card(card) {
  return `
    <div style="border: 1px solid var(--border-color); border-radius: 6px; padding: 10px 12px;">
      <div style="display: flex; justify-content: space-between; gap: 8px; margin-bottom: 8px;">
        <div style="font-weight: 600;">${escape_vehicle_dashboard_html(card.label)}</div>
        ${render_vehicle_dashboard_status_badge(null, card.status)}
      </div>
      ${card.rows
        .map(
          ([label, value]) => `
            <div style="display: flex; justify-content: space-between; gap: 12px; margin-top: 6px;">
              <div class="text-muted" style="font-size: 12px;">${escape_vehicle_dashboard_html(label)}</div>
              <div style="font-weight: 500; text-align: right;">${escape_vehicle_dashboard_html(format_vehicle_dashboard_value(value))}</div>
            </div>
          `
        )
        .join("")}
    </div>
  `;
}

function render_vehicle_dashboard_status_badge(label, status) {
  if (!status) {
    return "";
  }

  const indicator = get_vehicle_dashboard_status_indicator(status);
  const text = label ? `${label}: ${status}` : status;
  return `<span class="indicator ${indicator}" style="font-size: 12px; white-space: nowrap;">${escape_vehicle_dashboard_html(text)}</span>`;
}

function render_vehicle_dashboard_messages(label, messages) {
  if (!messages || !messages.length) {
    return "";
  }

  return `
    <div style="border-top: 1px solid var(--border-color); margin-top: 12px; padding-top: 10px;">
      <div style="font-weight: 600; margin-bottom: 4px;">${escape_vehicle_dashboard_html(label)}</div>
      ${messages
        .map((message) => `<div class="text-muted" style="font-size: 12px;">${escape_vehicle_dashboard_html(message)}</div>`)
        .join("")}
    </div>
  `;
}

function get_vehicle_dashboard_status_indicator(status) {
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

function format_vehicle_dashboard_money(value) {
  if (typeof value === "number") {
    return format_vehicle_currency(value);
  }
  return value;
}

function format_vehicle_dashboard_value(value) {
  if (value === undefined || value === null || value === "") {
    return "—";
  }
  return value;
}

function escape_vehicle_dashboard_html(value) {
  return frappe.utils.escape_html(String(format_vehicle_dashboard_value(value)));
}

function get_accounting_flow_status(money_flow, voucher_draft, journal_entry) {
  if (journal_entry) {
    return "已入帳";
  }
  if (voucher_draft) {
    return "傳票草稿";
  }
  if (money_flow) {
    return "已記錄金流";
  }
  return "未記錄";
}

function is_reserved_vehicle(frm) {
  return Boolean(!frm.is_new() && frm.doc.status === "保留中");
}

function get_reserved_vehicle_next_step(frm, active_reservation) {
  const has_deposit_journal_entry = Boolean(active_reservation && active_reservation.journal_entry);
  const has_final_money_flow = Boolean(active_reservation && active_reservation.final_money_flow);
  const has_final_voucher_draft = Boolean(active_reservation && active_reservation.final_voucher_draft);
  const has_final_journal_entry = Boolean(active_reservation && active_reservation.final_journal_entry);

  if (!active_reservation) {
    return {
      current_stage: "保留中，但找不到有效保留單",
      next_step: "請檢查保留資料",
      primary_action: null,
      can_check_delivery: false,
      can_complete_sale: false,
    };
  }

  if (!has_final_money_flow || !has_final_voucher_draft) {
    return {
      current_stage: "已保留，等待建立尾款收款",
      next_step: "建立尾款收款",
      primary_action: "create_final_payment",
      can_check_delivery: false,
      can_complete_sale: false,
    };
  }

  if (!has_deposit_journal_entry || !has_final_journal_entry) {
    return {
      current_stage: "尾款已建立，等待會計確認入帳",
      next_step: "等待會計確認訂金與尾款傳票",
      primary_action: null,
      can_check_delivery: false,
      can_complete_sale: false,
    };
  }

  return {
    current_stage: "訂金與尾款已入帳",
    next_step: "成交前檢查 / 確認成交",
    primary_action: "complete_sale_ready",
    can_check_delivery: true,
    can_complete_sale: true,
  };
}

function load_active_reservation_for_reserved_vehicle(frm) {
  if (!is_reserved_vehicle(frm)) {
    return;
  }

  frappe.call({
    method:
      "used_car_erp.used_car_erp.services.vehicle_reservation_service.get_active_reservation_for_vehicle",
    args: {
      vehicle_name: frm.doc.name,
    },
    callback(response) {
      frm._active_reservation = response.message || null;
      render_reserved_vehicle_status(frm);
      refresh_reserved_vehicle_action_buttons(frm);
    },
    error() {
      // 保留中狀態來源必須是 active Reservation；讀取失敗時採安全預設，不用 Vehicle 成交摘要誤判。
      frm._active_reservation = null;
      render_reserved_vehicle_status(frm);
      refresh_reserved_vehicle_action_buttons(frm);
    },
  });
}

function render_reserved_vehicle_status(frm) {
  if (!is_reserved_vehicle(frm) || !frm.dashboard) {
    return;
  }

  const active_reservation = frm._active_reservation || null;
  const next_step = get_reserved_vehicle_next_step(frm, active_reservation);
  const customer =
    (active_reservation && (active_reservation.customer_name || active_reservation.customer)) ||
    frm.doc.customer ||
    "未填";
  const sold_price = format_vehicle_currency(frm.doc.sold_price || 0);
  const deposit_status = (active_reservation && active_reservation.deposit_status) || "讀取中";
  const final_status = (active_reservation && active_reservation.final_status) || "讀取中";

  const message = [
    "目前狀態：保留中",
    `客戶：${frappe.utils.escape_html(customer)}`,
    `成交價：${frappe.utils.escape_html(sold_price)}`,
    `訂金狀態：${frappe.utils.escape_html(deposit_status)}`,
    `尾款狀態：${frappe.utils.escape_html(final_status)}`,
    `下一步：${frappe.utils.escape_html(next_step.next_step)}`,
  ];

  frm.dashboard.add_comment(message.join("<br>"), "blue", true);
}

function add_reserved_vehicle_primary_action_button(frm, active_reservation) {
  const next_step = get_reserved_vehicle_next_step(frm, active_reservation);

  if (next_step.primary_action === "create_final_payment") {
    add_final_payment_button(frm);
    return;
  }

  if (next_step.can_complete_sale) {
    add_complete_reservation_button(frm);
    return;
  }

  if (next_step.can_check_delivery) {
    add_delivery_preflight_button(frm);
  }
}

function refresh_reserved_vehicle_action_buttons(frm) {
  if (!is_reserved_vehicle(frm)) {
    return;
  }

  frm.remove_custom_button("建立尾款收款");
  frm.remove_custom_button("成交前檢查");
  frm.remove_custom_button("確認成交");

  add_reserved_vehicle_primary_action_button(frm, frm._active_reservation || null);
}

function add_reserved_vehicle_secondary_buttons(frm) {
  add_cancel_reservation_button(frm);
}

function apply_accounting_status_technical_field_visibility(frm) {
  const show = Boolean(frm._show_accounting_technical_fields);
  ACCOUNTING_TECHNICAL_FIELDS.forEach((fieldname) => {
    if (frm.fields_dict[fieldname]) {
      frm.toggle_display(fieldname, show);
    }
  });
}

function add_accounting_status_technical_fields_toggle_button(frm) {
  frm.add_custom_button(
    frm._show_accounting_technical_fields ? "隱藏文件連結" : "顯示文件連結",
    () => {
      frm._show_accounting_technical_fields = !frm._show_accounting_technical_fields;
      apply_accounting_status_technical_field_visibility(frm);
      frm.refresh_fields();
    },
    "更多資訊"
  );
}

function add_formal_delivery_submit_preflight_button(frm) {
  if (frm.is_new() || !frm.doc.name || frm.doc.status !== "已售出") {
    return;
  }

  frm.add_custom_button("檢查提交資格", () => {
    frappe.call({
      method:
        "used_car_erp.used_car_erp.services.vehicle_formal_delivery_service.preflight_formal_delivery_submit_for_vehicle",
      args: {
        vehicle_name: frm.doc.name,
      },
      freeze: true,
      freeze_message: "正在執行正式交車提交前檢查...",
      callback(response) {
        const result = response.message || {};
        frappe.show_alert({
          message: result.ready ? "提交前檢查已通過；目前仍未正式提交。" : "提交前檢查未通過，請查看檢查面板。",
          indicator: result.ready ? "green" : "red",
        });
        frm.reload_doc();
      },
      error() {
        // 提交前檢查只提供唯讀 gate 結果，呼叫失敗不得阻斷已售出車輛頁其他操作。
      },
    });
  });
}

function add_submit_formal_delivery_sales_invoice_button(frm) {
  if (!can_submit_formal_delivery_sales_invoice(frm)) {
    return;
  }

  frm.add_custom_button("確認銷售發票並出庫", () => {
    frappe.confirm(
      [
        "此操作會提交銷售發票，並依 ERPNext update_stock 進行庫存出庫。",
        "",
        "此操作不代表款項已收清，也不會自動建立收款紀錄。",
        "此操作不代表實體交車 / 離場狀態已完成。",
        "",
        "提交後銷售發票將不再是草稿，售車核心資料會進入正式文件鎖定狀態。",
        "請確認客戶、車輛、金額、Serial No、Warehouse 與稅務資料均已確認。",
      ].join("<br>"),
      () => {
        frappe.call({
          method:
            "used_car_erp.used_car_erp.services.vehicle_formal_delivery_service.submit_formal_delivery_sales_invoice_for_vehicle",
          args: {
            vehicle_name: frm.doc.name,
          },
          freeze: true,
          freeze_message: "正在確認銷售發票並出庫...",
          callback(response) {
            const result = response.message || {};
            frappe.show_alert({
              message:
                result.status === "submitted"
                  ? "銷售發票已提交，預收款沖轉與後續收款仍需依實際狀態處理。"
                  : result.message || "Sales Invoice 正式提交前檢查未通過。",
              indicator: result.status === "submitted" ? "green" : "red",
            });
            frm.reload_doc();
          },
        });
      }
    );
  });
}

function add_create_advance_settlement_journal_entry_draft_button(frm) {
  if (!can_create_advance_settlement_journal_entry_draft(frm)) {
    return;
  }

  frm.add_custom_button("建立預收款沖轉草稿", () => {
    frappe.confirm(
      [
        "此操作會建立預收款沖轉 Journal Entry 草稿。",
        "",
        "此草稿會將已入帳的訂金 / 尾款預收款沖轉至 Sales Invoice 應收帳款。",
        "此操作不會提交 Journal Entry。",
        "此操作不會建立 Payment Entry。",
        "此操作只處理預收款沖轉，不代表款項已收清或車輛實體交付狀態已完成。",
        "建立後仍須由會計人工確認與提交。",
      ].join("<br>"),
      () => {
        frappe.call({
          method:
            "used_car_erp.used_car_erp.services.vehicle_formal_delivery_service.create_advance_settlement_journal_entry_draft_for_vehicle",
          args: {
            vehicle_name: frm.doc.name,
          },
          freeze: true,
          freeze_message: "正在建立預收款沖轉 Journal Entry 草稿...",
          callback(response) {
            const result = response.message || {};
            frappe.show_alert({
              message:
                result.status === "draft_created"
                  ? "預收款沖轉 Journal Entry 草稿已建立，仍需會計確認。"
                  : result.message || "預收款沖轉傳票草稿建立前檢查未通過。",
              indicator: result.status === "draft_created" ? "green" : "red",
            });
            frm.reload_doc();
          },
        });
      }
    );
  });
}

function add_submit_advance_settlement_journal_entry_button(frm) {
  if (!can_submit_advance_settlement_journal_entry(frm)) {
    return;
  }

  frm.add_custom_button("確認預收款沖轉入帳", () => {
    frappe.confirm(
      [
        "此操作會提交預收款沖轉 Journal Entry。",
        "",
        "提交後會將已入帳的訂金 / 尾款預收款沖轉至 Sales Invoice 應收帳款。",
        "此操作可能影響正式會計分錄。",
        "此操作不會建立 Payment Entry。",
        "此操作不會建立 Delivery Note 或 Stock Entry。",
        "此操作只處理預收款沖轉，不代表款項已收清或車輛實體交付狀態已完成。",
      ].join("<br>"),
      () => {
        frappe.call({
          method:
            "used_car_erp.used_car_erp.services.vehicle_formal_delivery_service.submit_advance_settlement_journal_entry_for_vehicle",
          args: {
            vehicle_name: frm.doc.name,
          },
          freeze: true,
          freeze_message: "正在提交預收款沖轉 Journal Entry...",
          callback(response) {
            const result = response.message || {};
            frappe.show_alert({
              message:
                result.status === "settlement_submitted"
                  ? "預收款沖轉已提交，後續收款與實體交車狀態仍需分開確認。"
                  : result.message || "預收款沖轉 Journal Entry 提交前檢查未通過。",
              indicator: result.status === "settlement_submitted" ? "green" : "red",
            });
            frm.reload_doc();
          },
        });
      }
    );
  });
}

function add_open_advance_settlement_journal_entry_button(frm) {
  return;
}

function add_open_sales_invoice_button(frm) {
  return;
}

function add_recover_sales_invoice_draft_link_button(frm) {
  frm.remove_custom_button("修復 Sales Invoice 草稿連結");
  frm.remove_custom_button("修復銷售發票草稿連結");
  frm.add_custom_button(
    "修復銷售發票草稿連結",
    () => {
      frappe.confirm(
        "此操作只會在後端確認目前 Sales Invoice 已取消，且剛好存在一張 amended Draft Sales Invoice 時，才會修復車輛連結並回填缺失售車資料。是否繼續？",
        () => {
          frappe.call({
            method:
              "used_car_erp.used_car_erp.services.vehicle_formal_delivery_service.recover_sales_invoice_draft_link_for_vehicle",
            args: {
              vehicle_name: frm.doc.name,
            },
            freeze: true,
            freeze_message: "正在修復 Sales Invoice 草稿連結...",
            callback(response) {
              const result = response.message || {};
              const blockedReasons = result.blocked_reasons || [];
              frappe.show_alert({
                message: result.recovered
                  ? "已修復連結"
                  : blockedReasons.join(" ") || result.message || "Sales Invoice 草稿連結修復未執行。",
                indicator: result.recovered ? "green" : "red",
              });
              frm.reload_doc();
            },
          });
        }
      );
    },
    "技術維護"
  );
}

function add_recover_sales_invoice_draft_link_button_if_needed(frm) {
  if (!can_check_recover_sales_invoice_draft_link(frm)) {
    return;
  }

  frappe.call({
    method:
      "used_car_erp.used_car_erp.services.vehicle_formal_delivery_service.get_sales_invoice_draft_link_recovery_state_for_vehicle",
    args: {
      vehicle_name: frm.doc.name,
    },
    callback(response) {
      const result = response.message || {};
      if (!result.can_recover) {
        return;
      }

      add_recover_sales_invoice_draft_link_button(frm);
    },
    error() {
      // recovery 狀態檢查只是顯示修復按鈕的唯讀 gate，失敗時採安全預設不顯示 mutation 入口。
    },
  });
}

function add_refresh_sold_vehicle_final_check_button(frm) {
  if (frm.is_new() || !frm.doc.name || frm.doc.status !== "已售出") {
    return;
  }

  frm.add_custom_button("重新整理交車前檢查", () => {
    frappe.call({
      method:
        "used_car_erp.used_car_erp.services.vehicle_final_check_service.get_sold_vehicle_final_check_for_vehicle",
      args: {
        vehicle_name: frm.doc.name,
      },
      freeze: true,
      freeze_message: "正在重新整理交車前檢查...",
      callback() {
        frappe.show_alert({
          message: "已重新整理交車前檢查",
          indicator: "green",
        });
        frm.reload_doc();
      },
    });
  });
}

function add_create_vehicle_cost_button(frm) {
  if (frm.is_new() || !frm.doc.name || ["已售出", "封存"].includes(frm.doc.status)) {
    return;
  }

  frm.add_custom_button("新增單車成本", () => {
    frappe.new_doc("Used Car Vehicle Cost", {
      vehicle: frm.doc.name,
      cost_date: frappe.datetime.get_today(),
      capitalization_mode: "單車成本",
      document_type: "無憑證",
      tax_deductibility: "待確認",
      review_status: "待確認",
    });
  });
}

function add_general_expense_money_flow_button(frm) {
  if (frm.is_new() || !frm.doc.name || frm.doc.status === "封存") {
    return;
  }

  const payment_method_field = get_money_flow_payment_method_prompt_field();

  frm.add_custom_button(
    "新增支出",
    () => {
      frappe.prompt(
        [
          {
            fieldname: "payment_date",
            label: "支出日期",
            fieldtype: "Date",
            default: frappe.datetime.get_today(),
            reqd: 1,
          },
          {
            fieldname: "flow_type",
            label: "支出類型",
            fieldtype: "Select",
            options: "整備支出\n維修支出\n美容支出\n代辦支出\n拍場支出\n其他支出",
            reqd: 1,
          },
          {
            fieldname: "amount",
            label: "金額",
            fieldtype: "Currency",
            reqd: 1,
          },
          payment_method_field,
          {
            fieldname: "payment_reference",
            label: "付款參考",
            fieldtype: "Data",
            reqd: 0,
          },
          {
            fieldname: "notes",
            label: "備註",
            fieldtype: "Small Text",
            reqd: 0,
          },
          {
            fieldname: "evidence_attachment",
            label: "憑證附件",
            fieldtype: "Attach",
            reqd: 0,
          },
        ],
        (values) => {
          frappe.call({
            method:
              "used_car_erp.used_car_erp.services.vehicle_money_flow_service.create_general_expense_money_flow",
            args: {
              vehicle: frm.doc.name,
              payment_date: values.payment_date,
              flow_type: values.flow_type,
              amount: values.amount,
              payment_method: values.payment_method,
              payment_reference: values.payment_reference,
              notes: values.notes,
              evidence_attachment: values.evidence_attachment,
            },
            freeze: true,
            freeze_message: "正在建立支出金流...",
            callback(response) {
              const result = response.message || {};
              const message =
                result.money_flow || result.voucher_draft
                  ? [
                      "已建立支出金流與待審核傳票草稿",
                      result.money_flow ? `金流紀錄：${result.money_flow}` : null,
                      result.voucher_draft ? `傳票草稿：${result.voucher_draft}` : null,
                    ]
                      .filter(Boolean)
                      .join("<br>")
                  : "已建立支出金流與待審核傳票草稿";

              frappe.show_alert({
                message,
                indicator: "green",
              });
              frm.reload_doc();
            },
          });
        },
        "新增支出",
        "建立支出"
      );
    },
    "車輛作業"
  );
}

function get_money_flow_payment_method_prompt_field() {
  return {
    fieldname: "payment_method",
    label: "付款方式",
    fieldtype: "Select",
    options: "現金\n匯款\n信用卡\n其他",
    default: "現金",
    reqd: 1,
  };
}

function add_recalculate_cost_summary_button(frm) {
  if (frm.is_new() || !frm.doc.name || ["已售出", "封存"].includes(frm.doc.status)) {
    return;
  }

  frm.add_custom_button("重新計算成本摘要", () => {
    frappe.call({
      method:
        "used_car_erp.used_car_erp.services.vehicle_cost_service.recalculate_vehicle_cost_summary_for_vehicle",
      args: {
        vehicle_name: frm.doc.name,
      },
      freeze: true,
      freeze_message: "正在重新計算成本摘要...",
      callback() {
        frappe.show_alert({
          message: "已重新計算成本摘要",
          indicator: "green",
        });
        frm.reload_doc();
      },
    });
  });
}

function add_refresh_profit_tax_estimate_button(frm) {
  if (frm.is_new() || !frm.doc.name || ["已售出", "封存"].includes(frm.doc.status)) {
    return;
  }

  frm.add_custom_button("重新整理損益與稅務估算", () => {
    frappe.call({
      method:
        "used_car_erp.used_car_erp.services.vehicle_profit_tax_estimate_service.get_vehicle_profit_tax_estimate_for_vehicle",
      args: {
        vehicle_name: frm.doc.name,
      },
      freeze: true,
      freeze_message: "正在重新整理損益與稅務估算...",
      callback() {
        frappe.show_alert({
          message: "已重新整理損益與稅務估算",
          indicator: "green",
        });
        frm.reload_doc();
      },
    });
  });
}

function add_complete_intake_button(frm) {
  if (
    frm.is_new() ||
    !frm.doc.stock_no ||
    frm.doc.serial_no ||
    frm.doc.stock_entry ||
    ["已售出", "封存"].includes(frm.doc.status)
  ) {
    return;
  }

  frm.add_custom_button("完成入庫", () => {
    frappe.confirm(
      "完成入庫會自動建立 ERPNext 商品、套用預設入庫倉庫，並提交 ERPNext Stock Entry。請確認 VIN、採購車價正確。是否繼續？",
      () => {
        frappe.call({
          method:
            "used_car_erp.used_car_erp.services.vehicle_intake_service.complete_intake",
          args: {
            vehicle_name: frm.doc.name,
          },
          freeze: true,
          freeze_message: "正在完成入庫...",
          callback(response) {
            const result = response.message || {};
            const did_create = result.created !== false && result.stock_created !== false;
            frappe.show_alert({
              message: did_create ? "已完成入庫" : result.message || "此車輛已完成入庫",
              indicator: did_create ? "green" : "blue",
            });
            frm.reload_doc();
          },
        });
      }
    );
  });
}

function add_non_sold_vehicle_primary_action_button(frm) {
  if (frm.is_new() || ["已售出", "保留中", "封存"].includes(frm.doc.status)) {
    return;
  }

  if (!frm.doc.serial_no && !frm.doc.stock_entry) {
    add_complete_intake_button(frm);
    return;
  }

  if (frm.doc.status === "庫存中" && is_vehicle_stocked(frm)) {
    add_listing_action_button(
      frm,
      "開始整備",
      "確定將此車輛狀態改為「整備中」？此操作不會異動 ERPNext 庫存。",
      "used_car_erp.used_car_erp.services.vehicle_listing_service.start_preparation",
      "已開始整備"
    );
    return;
  }

  if (frm.doc.status === "整備中" && is_vehicle_stocked(frm)) {
    add_listing_action_button(
      frm,
      "整備完成並上架",
      "確定將此車輛狀態改為「上架中」？此操作不會異動 ERPNext 庫存。",
      "used_car_erp.used_car_erp.services.vehicle_listing_service.list_vehicle",
      "已上架"
    );
    return;
  }

  if (frm.doc.status === "上架中" && is_vehicle_stocked(frm)) {
    add_create_reservation_button(frm);
  }
}

function add_create_reservation_button(frm) {
  frm.add_custom_button("建立訂金保留", () => {
    frappe.prompt(
      [
        {
          fieldname: "existing_customer",
          label: "既有客戶",
          fieldtype: "Link",
          options: "Customer",
          reqd: 0,
        },
        {
          fieldname: "customer_name",
          label: "客戶姓名",
          fieldtype: "Data",
          reqd: 1,
        },
        {
          fieldname: "customer_phone",
          label: "客戶電話",
          fieldtype: "Data",
          reqd: 1,
        },
        {
          fieldname: "deposit_amount",
          label: "訂金金額",
          fieldtype: "Currency",
          reqd: 1,
        },
        {
          fieldname: "payment_method",
          label: "付款方式",
          fieldtype: "Select",
          options: "現金\n匯款\n信用卡\n其他",
          default: "現金",
          reqd: 1,
        },
        {
          fieldname: "deposit_date",
          label: "訂金日期",
          fieldtype: "Date",
          default: frappe.datetime.get_today(),
          reqd: 1,
        },
        {
          fieldname: "payment_reference",
          label: "付款備註 / 末五碼",
          fieldtype: "Data",
          reqd: 0,
        },
        {
          fieldname: "notes",
          label: "備註",
          fieldtype: "Small Text",
          reqd: 0,
        },
      ],
      (values) => {
        frappe.call({
          method:
            "used_car_erp.used_car_erp.services.vehicle_reservation_service.create_reservation",
          args: {
            vehicle_name: frm.doc.name,
            customer: values.existing_customer,
            customer_name: values.customer_name,
            customer_phone: values.customer_phone,
            deposit_amount: values.deposit_amount,
            payment_method: values.payment_method,
            deposit_date: values.deposit_date,
            payment_reference: values.payment_reference,
            notes: values.notes,
          },
          freeze: true,
          freeze_message: "正在建立保留...",
          callback() {
            frappe.show_alert({
              message: "已建立訂金保留",
              indicator: "green",
            });
            frm.reload_doc();
          },
        });
      },
      "建立訂金保留",
      "建立保留"
    );
  });
}

function add_final_payment_button(frm) {
  frm.add_custom_button("建立尾款收款", () => {
    frappe.prompt(
      [
        {
          fieldname: "amount",
          label: "尾款金額",
          fieldtype: "Currency",
          reqd: 1,
        },
        {
          fieldname: "payment_method",
          label: "付款方式",
          fieldtype: "Select",
          options: "現金\n匯款\n信用卡\n其他",
          default: "現金",
          reqd: 1,
        },
        {
          fieldname: "payment_date",
          label: "尾款日期",
          fieldtype: "Date",
          default: frappe.datetime.get_today(),
          reqd: 1,
        },
        {
          fieldname: "payment_reference",
          label: "付款備註 / 末五碼",
          fieldtype: "Data",
          reqd: 0,
        },
        {
          fieldname: "notes",
          label: "備註",
          fieldtype: "Small Text",
          reqd: 0,
        },
      ],
      (values) => {
        frappe.confirm(
          "建立尾款收款後，系統只會建立金流紀錄與傳票草稿，不會交車、出庫、開銷售發票或建立收款單。是否繼續？",
          () => {
            frappe.call({
              method:
                "used_car_erp.used_car_erp.services.vehicle_reservation_service.create_final_payment_for_active_reservation",
              args: {
                vehicle_name: frm.doc.name,
                amount: values.amount,
                payment_method: values.payment_method,
                payment_date: values.payment_date,
                payment_reference: values.payment_reference,
                notes: values.notes,
              },
              freeze: true,
              freeze_message: "正在建立尾款金流...",
              callback() {
                frappe.show_alert({
                  message: "已建立尾款金流與傳票草稿",
                  indicator: "green",
                });
                frm.reload_doc();
              },
            });
          }
        );
      },
      "建立尾款收款",
      "建立尾款"
    );
  });
}

function add_cancel_reservation_button(frm) {
  frm.add_custom_button("取消保留", () => {
    frappe.prompt(
      [
        {
          fieldname: "reason",
          label: "取消原因",
          fieldtype: "Small Text",
          reqd: 1,
        },
      ],
      (values) => {
        frappe.call({
          method:
            "used_car_erp.used_car_erp.services.vehicle_reservation_service.cancel_active_reservation_for_vehicle",
          args: {
            vehicle_name: frm.doc.name,
            reason: values.reason,
          },
          freeze: true,
          freeze_message: "正在取消保留...",
          callback() {
            frappe.show_alert({
              message: "已取消保留，車輛已回到上架中",
              indicator: "green",
            });
            frm.reload_doc();
          },
        });
      },
      "取消保留",
      "取消保留"
    );
  });
}

function add_delivery_preflight_button(frm) {
  frm.add_custom_button("成交前檢查", () => {
    frappe.call({
      method:
        "used_car_erp.used_car_erp.services.vehicle_reservation_service.preflight_delivery_for_active_reservation",
      args: {
        vehicle_name: frm.doc.name,
      },
      freeze: true,
      freeze_message: "正在檢查成交前條件...",
      callback(response) {
        const result = response.message || {};
        frappe.show_alert({
          message: result.message || "此車輛已完成訂金與尾款入帳，可進入成交 / 交車流程。",
          indicator: "green",
        });
        frm.reload_doc();
      },
    });
  });
}

function add_sold_vehicle_next_step_button(frm) {
  frm.add_custom_button("建立 Sales Invoice 草稿", () => {
    frappe.confirm(
      "系統會建立一張 Sales Invoice 草稿，讓你先檢查客戶、車輛、金額、倉庫與收入科目。這一步不會正式出庫、不會認列收入，也不會建立沖轉傳票。是否繼續？",
      () => {
        frappe.prompt(
          [
            {
              fieldname: "posting_date",
              label: "入帳日期",
              fieldtype: "Date",
              default: frappe.datetime.get_today(),
              reqd: 1,
            },
            {
              fieldname: "note",
              label: "備註",
              fieldtype: "Small Text",
              reqd: 0,
            },
          ],
          (values) => {
            frappe.call({
              method:
                "used_car_erp.used_car_erp.services.vehicle_reservation_service.create_sales_invoice_draft_for_vehicle",
              args: {
                vehicle_name: frm.doc.name,
                posting_date: values.posting_date,
                note: values.note,
              },
              freeze: true,
              freeze_message: "正在建立 Sales Invoice 草稿...",
              callback(response) {
                const result = response.message || {};
                frappe.show_alert({
                  message:
                    result.message ||
                    "Sales Invoice 草稿已建立。請打開草稿確認內容，確認無誤後再進行下一階段。",
                  indicator: "green",
                });
                frm.reload_doc();
              },
            });
          },
          "建立 Sales Invoice 草稿",
          "建立草稿"
        );
      }
    );
  });
}

function add_sold_vehicle_primary_action_button(frm) {
  const action = get_sold_vehicle_primary_next_action(frm);

  if (!action || !action.primary_action) {
    return;
  }
}

function add_open_formal_sale_accounting_candidates_button(frm) {
  return;
}

function can_check_recover_sales_invoice_draft_link(frm) {
  return Boolean(
    !frm.is_new() &&
      frm.doc.status === "已售出" &&
      frm.doc.formal_delivery_status === "銷售發票草稿" &&
      frm.doc.sales_invoice
  );
}

function get_sold_vehicle_primary_next_action(frm) {
  if (frm.is_new() || frm.doc.status !== "已售出") {
    return null;
  }

  const status = frm.doc.formal_delivery_status;
  const has_sales_invoice = Boolean(frm.doc.sales_invoice);
  const has_settlement_journal_entry = Boolean(frm.doc.advance_settlement_journal_entry);

  if (status === "已完成") {
    return {
      current_stage: "已售出",
      next_step: "",
      primary_action: null,
      related_documents: [
        ...(has_sales_invoice ? ["sales_invoice"] : []),
        ...(has_settlement_journal_entry ? ["advance_settlement_journal_entry"] : []),
      ],
    };
  }

  if (status === "預收款沖轉已提交" && has_settlement_journal_entry) {
    return {
      current_stage: "已售出",
      next_step: "等待交車完成確認",
      primary_action: null,
      related_documents: [
        ...(has_sales_invoice ? ["sales_invoice"] : []),
        "advance_settlement_journal_entry",
      ],
    };
  }

  if (status === "預收款沖轉草稿" && has_settlement_journal_entry) {
    return {
      current_stage: "已售出",
      next_step: "等待會計作業確認",
      primary_action: null,
      related_documents: [
        ...(has_sales_invoice ? ["sales_invoice"] : []),
        "advance_settlement_journal_entry",
      ],
    };
  }

  if (status === "銷售發票已提交" && has_sales_invoice && !has_settlement_journal_entry) {
    return {
      current_stage: "已售出",
      next_step: "等待會計作業確認",
      primary_action: null,
      related_documents: ["sales_invoice"],
    };
  }

  if (has_sales_invoice && [undefined, null, "", "銷售發票草稿"].includes(status)) {
    return {
      current_stage: "已售出",
      next_step: "等待會計作業確認",
      primary_action: null,
      related_documents: ["sales_invoice"],
    };
  }

  return {
    current_stage: "已售出",
    next_step: "等待會計作業確認",
    primary_action: null,
    related_documents: [],
  };
}

function add_sold_vehicle_progress_comment(frm) {
  if (frm.is_new() || frm.doc.status !== "已售出" || !frm.dashboard) {
    return;
  }

  const simplified_action = get_sold_vehicle_primary_next_action(frm);

  if (simplified_action) {
    const message = [
      `目前階段：${simplified_action.current_stage}`,
      simplified_action.next_step ? `下一步：${simplified_action.next_step}` : "成交流程已完成",
    ];

    frm.dashboard.add_comment(message.join("<br>"), "blue", true);
    return;
  }
}

function build_sales_invoice_draft_checklist_comment() {
  return [
    "Sales Invoice 草稿檢查清單：",
    "✓ 客戶是否正確",
    "✓ 公司是否正確",
    "✓ 車輛 Item 是否正確",
    "✓ Serial No 是否為這台車",
    "✓ Warehouse 是否為車輛所在倉",
    "✓ 金額是否等於訂金 + 尾款",
    "✓ Income Account 是否為正確收入科目",
    "✓ Update Stock 是否已勾選",
    "✓ 狀態是否仍為 Draft / 草稿",
    "確認無誤後，下一階段才會開放正式提交、出庫與預收款沖轉。",
  ].join("<br>");
}

function add_sold_vehicle_final_check_comment(frm) {
  if (frm.is_new() || frm.doc.status !== "已售出" || !frm.doc.name || !frm.dashboard) {
    return;
  }

  frappe.call({
    method:
      "used_car_erp.used_car_erp.services.vehicle_final_check_service.get_sold_vehicle_final_check_for_vehicle",
    args: {
      vehicle_name: frm.doc.name,
    },
    callback(response) {
      const result = response.message;

      if (!result) {
        return;
      }

      const indicator_by_status = {
        ready: "green",
        warning: "orange",
        blocked: "red",
      };
      const message = [
        "交車前最終檢查：",
        `整體狀態：${result.status_label || result.status}`,
        ...result.checks.map((check) => `${final_check_icon(check.state)} ${check.label}：${check.message}`),
        "",
        "此面板只作交車前人工檢查，不會正式提交、出庫、沖轉或入帳。",
      ];

      frm.dashboard.add_comment(
        message.join("<br>"),
        indicator_by_status[result.status] || "blue",
        true
      );
    },
    error() {
      // 最終檢查面板只是唯讀輔助資訊，載入失敗不可阻斷車輛頁既有操作。
    },
  });
}

function add_formal_delivery_submit_preflight_comment(frm) {
  return;
}

function final_check_icon(state) {
  if (state === "ok") {
    return "✓";
  }
  if (state === "warning") {
    return "△";
  }
  return "✕";
}

function add_tax_metadata_comment(frm) {
  if (frm.is_new() || !frm.dashboard || !frm.get_field("tax_review_status")) {
    return;
  }

  const status = frm.doc.tax_review_status;
  let message = "此車輛已有初步稅務資料，正式申報前仍需確認。";
  let indicator = "blue";

  if (["待補資料", "待確認"].includes(status)) {
    message = "售車稅務資料尚未確認；此項只影響售車入帳前檢查，不影響車輛基本資料建檔。";
    indicator = "orange";
  }

  if (["已確認", "已鎖定"].includes(status)) {
    message = "此車輛稅務資料已確認。後續可依此資料產生稅務估算與報表。";
    indicator = "green";
  }

  frm.dashboard.add_comment(message, indicator, true);
}

function add_vehicle_cost_summary_comment(frm) {
  if (frm.is_new() || !frm.dashboard) {
    return;
  }

  const purchase_price = flt(frm.doc.purchase_price || 0);
  const total_cost = flt(frm.doc.total_cost || 0);
  const capitalized_cost_total = Math.max(total_cost - purchase_price, 0);
  const sold_price = flt(frm.doc.sold_price || 0);
  const gross_margin = flt(frm.doc.gross_margin || 0);
  const message = [
    "成本摘要：",
    `購車價：${format_vehicle_currency(purchase_price)}`,
    `累計成本：${format_vehicle_currency(total_cost)}`,
    `單車直接成本：${format_vehicle_currency(capitalized_cost_total)}`,
    `成交價：${format_vehicle_currency(sold_price)}`,
    `預估毛利：${format_vehicle_currency(gross_margin)}`,
    "可使用「新增單車成本」記錄整備、維修、美容、拍場費等直接成本。",
    "此摘要只作管理估算，不是正式會計成本。",
  ];

  frm.dashboard.add_comment(message.join("<br>"), "blue", true);
}

function add_vehicle_profit_tax_estimate_comment(frm) {
  if (frm.is_new() || !frm.doc.name || !frm.dashboard) {
    return;
  }

  frappe.call({
    method:
      "used_car_erp.used_car_erp.services.vehicle_profit_tax_estimate_service.get_vehicle_profit_tax_estimate_for_vehicle",
    args: {
      vehicle_name: frm.doc.name,
    },
    callback(response) {
      const estimate = response.message;

      if (!estimate) {
        return;
      }

      const indicator = estimate.tax_estimate_status === "需確認" ? "orange" : "blue";
      const message = [
        "單車損益與預估營業稅：",
        `成交價：${format_vehicle_currency(estimate.sale_price_tax_inclusive)}`,
        `購車價：${format_vehicle_currency(estimate.purchase_price)}`,
        `單車直接成本：${format_vehicle_currency(estimate.capitalized_cost_total)}`,
        `累計成本：${format_vehicle_currency(estimate.total_cost)}`,
        `預估毛利：${format_vehicle_currency(estimate.gross_margin)}`,
        `稅務模式：${estimate.vehicle_tax_mode || "待確認"}`,
        `預估銷項稅：${format_vehicle_currency(estimate.estimated_output_vat)}`,
        `預估可扣抵稅額：${format_vehicle_currency(estimate.estimated_input_credit)}`,
        `預估應納營業稅：${format_vehicle_currency(estimate.estimated_vat_payable)}`,
        `扣稅後管理毛利：${format_vehicle_currency(estimate.estimated_margin_after_vat)}`,
        `狀態：${estimate.tax_estimate_status || "待確認"}`,
        `備註：${estimate.tax_estimate_note || "此摘要只作管理估算，不是正式申報或會計入帳。"}`,
        "此摘要只作管理估算，不是正式申報或會計入帳。",
      ];

      frm.dashboard.add_comment(message.join("<br>"), indicator, true);
    },
    error() {
      // 摘要載入失敗不可阻斷車輛頁主流程，避免管理估算影響既有銷售與成本作業。
    },
  });
}

function format_vehicle_currency(value) {
  return format_currency(value || 0, frappe.defaults.get_default("currency"));
}

function add_complete_reservation_button(frm) {
  frm.add_custom_button("確認成交", () => {
    frappe.confirm(
      "確認成交前，系統會檢查訂金與尾款是否都已入帳。此操作只會將車輛標記為已售出、保留單標記為已完成，不會交車、出庫、開銷售發票或建立收款單。是否繼續？",
      () => {
        frappe.prompt(
          [
            {
              fieldname: "completion_note",
              label: "成交備註",
              fieldtype: "Small Text",
              reqd: 0,
            },
          ],
          (values) => {
            frappe.call({
              method:
                "used_car_erp.used_car_erp.services.vehicle_reservation_service.complete_active_reservation",
              args: {
                vehicle_name: frm.doc.name,
                completion_note: values.completion_note,
              },
              freeze: true,
              freeze_message: "正在確認成交...",
              callback(response) {
                const result = response.message || {};
                frappe.show_alert({
                  message: result.message || "已確認成交，車輛已標記為已售出。",
                  indicator: "green",
                });
                frm.reload_doc();
              },
            });
          },
          "確認成交",
          "確認成交"
        );
      }
    );
  });
}

function add_listing_action_button(frm, label, confirm_message, method, success_message) {
  frm.add_custom_button(label, () => {
    frappe.confirm(confirm_message, () => {
      frappe.call({
        method,
        args: {
          vehicle_name: frm.doc.name,
        },
        freeze: true,
        freeze_message: "正在更新車輛狀態...",
        callback(response) {
          const result = response.message || {};
          frappe.show_alert({
            message: result.message || success_message,
            indicator: result.changed === false ? "blue" : "green",
          });
          frm.reload_doc();
        },
      });
    });
  });
}

function is_vehicle_stocked(frm) {
  return Boolean(frm.doc.item && frm.doc.serial_no && frm.doc.stock_entry);
}

function set_vehicle_intake_intro(frm) {
  frm.set_intro("");

  if (frm.is_new()) {
    return;
  }

  if (frm.doc.status === "保留中") {
    frm.set_intro("此車輛已保留。下一步請建立尾款收款。", "orange");
    return;
  }

  if (frm.doc.status === "封存") {
    frm.set_intro("此車輛已封存，不可進行一般業務操作。", "orange");
    return;
  }

  if (![undefined, null, "", "草稿"].includes(frm.doc.status)) {
    return;
  }

  if (!frm.doc.vin) {
    frm.set_intro("請先填寫 VIN / 車身號碼後再完成入庫。", "orange");
    return;
  }

  if (!frm.doc.purchase_price) {
    frm.set_intro("請先填寫購車價後再完成入庫。", "orange");
    return;
  }

  frm.set_intro("此車尚未入庫，請按「完成入庫」。", "blue");
}

function can_submit_formal_delivery_sales_invoice(frm) {
  return Boolean(
    !frm.is_new() &&
      frm.doc.name &&
      frm.doc.status === "已售出" &&
      frm.doc.sales_invoice &&
      [undefined, null, "", "銷售發票草稿"].includes(frm.doc.formal_delivery_status)
  );
}

function can_create_advance_settlement_journal_entry_draft(frm) {
  return Boolean(
    !frm.is_new() &&
      frm.doc.name &&
      frm.doc.status === "已售出" &&
      frm.doc.formal_delivery_status === "銷售發票已提交" &&
      frm.doc.sales_invoice &&
      !frm.doc.advance_settlement_journal_entry
  );
}

function can_submit_advance_settlement_journal_entry(frm) {
  return Boolean(
    !frm.is_new() &&
      frm.doc.name &&
      frm.doc.status === "已售出" &&
      frm.doc.formal_delivery_status === "預收款沖轉草稿" &&
      frm.doc.advance_settlement_journal_entry
  );
}

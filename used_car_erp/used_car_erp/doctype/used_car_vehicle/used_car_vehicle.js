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

function apply_vehicle_form_mode(frm) {
  clear_vehicle_action_buttons(frm);
  set_vehicle_intake_intro(frm);
  add_sold_vehicle_progress_comment(frm);
  add_sold_vehicle_final_check_comment(frm);
  add_formal_delivery_submit_preflight_comment(frm);
  add_tax_metadata_comment(frm);
  add_vehicle_cost_summary_comment(frm);
  add_vehicle_profit_tax_estimate_comment(frm);

  if (frm.is_new()) {
    set_vehicle_fields_read_only(frm, false);
    return;
  }

  if (frm.doc.status === "已售出") {
    add_sold_vehicle_primary_action_button(frm);
    add_sold_vehicle_related_document_buttons(frm);
    set_vehicle_fields_read_only(frm, true);
    allow_sold_vehicle_tax_metadata_edit(frm);
    allow_sold_vehicle_sale_workflow_edit(frm);
    return;
  }

  add_complete_intake_button(frm);
  add_listing_workflow_buttons(frm);
  add_create_vehicle_cost_button(frm);
  add_recalculate_cost_summary_button(frm);
  add_refresh_profit_tax_estimate_button(frm);

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

  frm.set_intro("此車已售出，但正式交車完成前仍可由會計修改稅務確認資訊。", "blue");
  frm.refresh_fields(SOLD_VEHICLE_TAX_METADATA_FIELDS);
}

function allow_sold_vehicle_sale_workflow_edit(frm) {
  if (!can_edit_sold_vehicle_sale_workflow(frm)) {
    if (is_sold_vehicle_formally_locked(frm)) {
      frm.set_intro("正式文件已提交，售車資料已鎖定；後續需走修正 / 反轉流程。", "orange");
    }
    return;
  }

  SALE_WORKFLOW_FIELDS.forEach((fieldname) => {
    if (frm.fields_dict[fieldname]) {
      frm.set_df_property(fieldname, "read_only", 0);
    }
  });

  frm.set_intro(
    "此車已售出，但正式入帳鎖定前仍可修正售車資料。若已建立 Sales Invoice 草稿，儲存後會同步更新草稿。",
    "blue"
  );
  frm.refresh_fields(SALE_WORKFLOW_FIELDS.filter((fieldname) => frm.fields_dict[fieldname]));
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
    "建立預收款沖轉傳票草稿",
    "提交預收款沖轉傳票",
    "開啟 Sales Invoice",
    "開啟預收款沖轉傳票",
  ].forEach((label) => {
    frm.remove_custom_button(label);
  });
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

  frm.add_custom_button("提交 Sales Invoice 並正式出庫", () => {
    frappe.confirm(
      [
        "此操作會提交 Sales Invoice，並依 ERPNext update_stock 正式出庫。",
        "",
        "此操作可能影響收入、庫存與成本。",
        "此操作不會自動建立 Payment Entry。",
        "此操作不會自動完成預收款沖轉。",
        "此操作不會完成正式交車入帳。",
        "",
        "提交後 Sales Invoice 將不再是草稿。",
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
          freeze_message: "正在提交 Sales Invoice 並正式出庫...",
          callback(response) {
            const result = response.message || {};
            frappe.show_alert({
              message:
                result.status === "submitted"
                  ? "Sales Invoice 已提交，預收款沖轉仍待後續處理。"
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

  frm.add_custom_button("建立預收款沖轉傳票草稿", () => {
    frappe.confirm(
      [
        "此操作會建立預收款沖轉 Journal Entry 草稿。",
        "",
        "此草稿會將已入帳的訂金 / 尾款預收款沖轉至 Sales Invoice 應收帳款。",
        "此操作不會提交 Journal Entry。",
        "此操作不會建立 Payment Entry。",
        "此操作不會完成正式交車入帳。",
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

  frm.add_custom_button("提交預收款沖轉傳票", () => {
    frappe.confirm(
      [
        "此操作會提交預收款沖轉 Journal Entry。",
        "",
        "提交後會將已入帳的訂金 / 尾款預收款沖轉至 Sales Invoice 應收帳款。",
        "此操作可能影響正式會計分錄。",
        "此操作不會建立 Payment Entry。",
        "此操作不會建立 Delivery Note 或 Stock Entry。",
        "此操作不會完成正式交車入帳。",
        "提交後仍需進行正式交車完成檢查。",
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
                  ? "預收款沖轉 Journal Entry 已提交，正式交車完成仍待後續確認。"
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
  if (!frm.doc.advance_settlement_journal_entry) {
    return;
  }

  frm.add_custom_button("開啟預收款沖轉傳票", () => {
    frappe.set_route("Form", "Journal Entry", frm.doc.advance_settlement_journal_entry);
  });
}

function add_open_sales_invoice_button(frm) {
  if (!frm.doc.sales_invoice) {
    return;
  }

  frm.add_custom_button("開啟 Sales Invoice", () => {
    frappe.set_route("Form", "Sales Invoice", frm.doc.sales_invoice);
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

function add_listing_workflow_buttons(frm) {
  if (frm.is_new() || ["草稿", "已售出", "封存"].includes(frm.doc.status)) {
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
    add_listing_action_button(
      frm,
      "直接上架",
      "確定將此車輛狀態改為「上架中」？此操作不會異動 ERPNext 庫存。",
      "used_car_erp.used_car_erp.services.vehicle_listing_service.list_vehicle",
      "已上架"
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

  if (frm.doc.status === "上架中") {
    if (is_vehicle_stocked(frm)) {
      add_create_reservation_button(frm);
    }

    add_listing_action_button(
      frm,
      "下架回庫存",
      "確定將此車輛從「上架中」改回「庫存中」？此操作不會異動 ERPNext 庫存。",
      "used_car_erp.used_car_erp.services.vehicle_listing_service.unlist_vehicle",
      "已下架回庫存"
    );
    return;
  }

  if (frm.doc.status === "保留中") {
    add_final_payment_button(frm);
    add_delivery_preflight_button(frm);
    add_complete_reservation_button(frm);
    add_cancel_reservation_button(frm);
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

  if (action.primary_action === "submit_sales_invoice") {
    add_submit_formal_delivery_sales_invoice_button(frm);
    return;
  }

  if (action.primary_action === "create_advance_settlement_draft") {
    add_create_advance_settlement_journal_entry_draft_button(frm);
    return;
  }

  if (action.primary_action === "submit_advance_settlement") {
    add_submit_advance_settlement_journal_entry_button(frm);
    return;
  }

  if (action.primary_action === "create_sales_invoice_draft") {
    add_sold_vehicle_next_step_button(frm);
  }
}

function add_sold_vehicle_related_document_buttons(frm) {
  const action = get_sold_vehicle_primary_next_action(frm);

  if (!action) {
    return;
  }

  if (action.related_documents.includes("sales_invoice")) {
    add_open_sales_invoice_button(frm);
  }

  if (action.related_documents.includes("advance_settlement_journal_entry")) {
    add_open_advance_settlement_journal_entry_button(frm);
  }
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
      current_stage: "正式交車入帳流程已完成",
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
      current_stage: "預收款沖轉 Journal Entry 已提交",
      next_step: "等待正式交車完成檢查",
      primary_action: null,
      related_documents: [
        ...(has_sales_invoice ? ["sales_invoice"] : []),
        "advance_settlement_journal_entry",
      ],
    };
  }

  if (status === "預收款沖轉草稿" && has_settlement_journal_entry) {
    return {
      current_stage: "預收款沖轉 Journal Entry 草稿已建立",
      next_step: "提交預收款沖轉 Journal Entry",
      primary_action: "submit_advance_settlement",
      related_documents: [
        ...(has_sales_invoice ? ["sales_invoice"] : []),
        "advance_settlement_journal_entry",
      ],
    };
  }

  if (status === "銷售發票已提交" && has_sales_invoice && !has_settlement_journal_entry) {
    return {
      current_stage: "Sales Invoice 已提交並出庫",
      next_step: "建立預收款沖轉 Journal Entry 草稿",
      primary_action: "create_advance_settlement_draft",
      related_documents: ["sales_invoice"],
    };
  }

  if (has_sales_invoice && [undefined, null, "", "銷售發票草稿"].includes(status)) {
    return {
      current_stage: "Sales Invoice 草稿已建立",
      next_step: "提交 Sales Invoice 並正式出庫",
      primary_action: "submit_sales_invoice",
      related_documents: ["sales_invoice"],
    };
  }

  return {
    current_stage: "已完成成交，Sales Invoice 草稿尚未建立",
    next_step: "建立 Sales Invoice 草稿",
    primary_action: "create_sales_invoice_draft",
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
      simplified_action.next_step ? `下一步：${simplified_action.next_step}` : "正式交車入帳流程已完成",
    ];

    frm.dashboard.add_comment(message.join("<br>"), "blue", true);
    return;
  }

  const sales_invoice_submitted = frm.doc.formal_delivery_status === "銷售發票已提交";
  const settlement_draft_created =
    frm.doc.formal_delivery_status === "預收款沖轉草稿" && frm.doc.advance_settlement_journal_entry;
  const settlement_submitted =
    frm.doc.formal_delivery_status === "預收款沖轉已提交" && frm.doc.advance_settlement_journal_entry;
  const sales_invoice_status = sales_invoice_submitted
    ? "Sales Invoice 已正式提交並出庫"
    : settlement_submitted
      ? "Sales Invoice 已正式提交並出庫"
    : settlement_draft_created
      ? "Sales Invoice 已正式提交並出庫"
      : frm.doc.sales_invoice
      ? "Sales Invoice 草稿已建立"
      : "Sales Invoice 草稿尚未建立";
  const next_step = sales_invoice_submitted
    ? "建立預收款沖轉 Journal Entry 草稿"
    : settlement_submitted
      ? "正式交車完成檢查"
    : settlement_draft_created
      ? "會計確認並提交預收款沖轉 Journal Entry"
    : frm.doc.sales_invoice
      ? "開啟並檢查 Sales Invoice 草稿"
      : "建立 Sales Invoice 草稿";
  const progress_comment = [
    "流程進度：",
    "✓ 訂金已入帳",
    "✓ 尾款已入帳",
    "✓ 已確認成交",
    `✓ ${sales_invoice_status}`,
    `下一步：${next_step}`,
  ];

  if (settlement_submitted) {
    progress_comment.push(
      "",
      "預收款沖轉 Journal Entry 已提交。",
      "Sales Invoice 已提交並出庫。",
      "正式交車完成仍待後續確認。"
    );
  } else if (settlement_draft_created) {
    progress_comment.push(
      "",
      "預收款沖轉 Journal Entry 草稿已建立。",
      "仍需會計人工確認與提交。",
      "正式交車入帳尚未完成。"
    );
  } else if (frm.doc.advance_settlement_journal_entry) {
    progress_comment.push(
      "",
      "預收款沖轉傳票草稿已建立，等待會計確認。",
      "正式交車入帳尚未完成。"
    );
  } else if (sales_invoice_submitted) {
    progress_comment.push(
      "",
      "Sales Invoice 已正式提交並出庫。",
      "預收款沖轉仍待後續處理。",
      "正式交車入帳尚未完成。"
    );
  } else if (frm.doc.sales_invoice) {
    progress_comment.push("", build_sales_invoice_draft_checklist_comment());
  }

  frm.dashboard.add_comment(
    progress_comment.join("<br>"),
    "blue",
    true
  );
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
  if (frm.is_new() || frm.doc.status !== "已售出" || !frm.doc.name || !frm.dashboard) {
    return;
  }

  frappe.call({
    method:
      "used_car_erp.used_car_erp.services.vehicle_formal_delivery_service.preflight_formal_delivery_submit_for_vehicle",
    args: {
      vehicle_name: frm.doc.name,
    },
    callback(response) {
      const result = response.message;

      if (!result) {
        return;
      }

      const sales_invoice_submitted = frm.doc.formal_delivery_status === "銷售發票已提交";
      const blocked_reasons = result.blocked_reasons || [];
      const readiness_result = result.ready
        ? "判斷結果：目前資料已通過提交前檢查，可進入下一階段人工確認。"
        : "判斷結果：目前尚不可進入正式提交階段。";
      const blocked_message = blocked_reasons.length
        ? ["待處理項目：", ...blocked_reasons.map((reason) => `- ${reason}`)]
        : ["待處理項目：請查看上方檢查項目。"];
      const message = [
        sales_invoice_submitted ? "正式交車提交狀態（Phase 3B）：" : "正式交車提交前檢查（Phase 3A）：",
        `整體狀態：${result.status_label || result.status}`,
        ...result.checks.map((check) => `${final_check_icon(check.state)} ${check.label}：${check.message}`),
        "",
        "判斷結果：",
        readiness_result,
      ];

      if (!result.ready) {
        message.push("", ...blocked_message);
      }

      if (sales_invoice_submitted) {
        message.push(
          "",
          "Sales Invoice 已正式提交並出庫。",
          "預收款沖轉仍待後續處理。",
          "正式交車入帳尚未完成。"
        );
      } else {
        message.push(
          "",
          "注意：",
          "此檢查只代表「資料可進入下一階段人工確認」。",
          "目前尚未提交 Sales Invoice，尚未正式出庫，尚未沖轉預收款，尚未完成正式交車入帳。",
          "尚未正式提交 Sales Invoice。",
          "尚未正式出庫。",
          "尚未沖轉預收款。"
        );
      }

      frm.dashboard.add_comment(message.join("<br>"), result.ready ? "green" : "red", true);
    },
    error() {
      // 正式交車 preflight 面板只是唯讀輔助資訊，載入失敗不可阻斷車輛頁既有操作。
    },
  });
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

  if (frm.doc.status === "庫存中" && is_vehicle_stocked(frm)) {
    frm.set_intro("此車輛已完成入庫。下一步可開始整備，或直接上架銷售。", "green");
    return;
  }

  if (frm.doc.status === "整備中") {
    frm.set_intro("此車輛正在整備中。整備完成後可上架銷售。", "blue");
    return;
  }

  if (frm.doc.status === "上架中") {
    frm.set_intro("此車輛已上架。若客戶已下訂金，可建立訂金保留，車輛將改為保留中。", "green");
    return;
  }

  if (frm.doc.status === "保留中") {
    frm.set_intro("此車輛已保留。可建立尾款收款；系統只會建立金流紀錄與傳票草稿，正式入帳仍由會計在「會計作業」確認。交車與出庫流程尚未開放。", "orange");
    return;
  }

  if (frm.doc.status === "已售出") {
    if (frm.doc.formal_delivery_status === "預收款沖轉草稿" && frm.doc.advance_settlement_journal_entry) {
      frm.set_intro("預收款沖轉 Journal Entry 草稿已建立。仍需會計人工確認與提交；正式交車入帳尚未完成。", "blue");
      return;
    }

    if (frm.doc.formal_delivery_status === "預收款沖轉已提交" && frm.doc.advance_settlement_journal_entry) {
      frm.set_intro("預收款沖轉 Journal Entry 已提交。Sales Invoice 已提交並出庫。正式交車完成仍待後續確認。", "green");
      return;
    }

    if (frm.doc.advance_settlement_journal_entry) {
      frm.set_intro("預收款沖轉傳票草稿已建立，等待會計確認。正式交車入帳尚未完成。", "blue");
      return;
    }

    if (frm.doc.formal_delivery_status === "銷售發票已提交") {
      frm.set_intro("Sales Invoice 已正式提交並出庫。預收款沖轉仍待後續處理；正式交車入帳尚未完成。", "green");
      return;
    }

    if (frm.doc.sales_invoice) {
      frm.set_intro("Sales Invoice 草稿已建立。請先開啟草稿並依檢查清單確認內容；正式提交後只會出庫，預收款沖轉仍待後續處理。", "blue");
      return;
    }

    frm.set_intro("此車輛已完成成交，訂金與尾款已完成入帳。下一步是建立 Sales Invoice 草稿，供人工檢查銷售資料；目前不會正式出庫或認列收入。", "blue");
    return;
  }

  if (frm.doc.status === "封存") {
    frm.set_intro("此車輛已封存，不可進行一般業務操作。", "orange");
    return;
  }

  if (frm.doc.stock_entry || frm.doc.serial_no) {
    frm.set_intro("此車輛已完成入庫，已連結 ERPNext 商品、Serial No 與 Stock Entry。", "green");
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

  frm.set_intro("下一步：按「完成入庫」，系統會自動建立 ERPNext 商品並完成庫存入庫。", "blue");
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

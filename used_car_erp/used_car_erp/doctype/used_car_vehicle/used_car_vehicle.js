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
  "purchase_invoice",
  "sales_invoice",
];

const LAYOUT_FIELD_TYPES = [
  "Section Break",
  "Column Break",
  "Tab Break",
  "HTML",
  "Button",
];

function apply_vehicle_form_mode(frm) {
  clear_vehicle_mode_buttons(frm);

  if (frm.is_new()) {
    set_vehicle_fields_read_only(frm, false);
    return;
  }

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

function clear_vehicle_mode_buttons(frm) {
  ["編輯資料", "取消編輯"].forEach((label) => {
    frm.remove_custom_button(label);
  });
}

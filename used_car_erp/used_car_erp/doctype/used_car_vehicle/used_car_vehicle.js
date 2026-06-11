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
];

const LAYOUT_FIELD_TYPES = [
  "Section Break",
  "Column Break",
  "Tab Break",
  "HTML",
  "Button",
];

function apply_vehicle_form_mode(frm) {
  clear_vehicle_action_buttons(frm);
  set_vehicle_intake_intro(frm);

  if (frm.is_new()) {
    set_vehicle_fields_read_only(frm, false);
    return;
  }

  add_complete_intake_button(frm);
  add_listing_workflow_buttons(frm);

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
  ].forEach((label) => {
    frm.remove_custom_button(label);
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
  if (frm.is_new() || ["草稿", "保留中", "已售出", "封存"].includes(frm.doc.status)) {
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
    add_listing_action_button(
      frm,
      "下架回庫存",
      "確定將此車輛從「上架中」改回「庫存中」？此操作不會異動 ERPNext 庫存。",
      "used_car_erp.used_car_erp.services.vehicle_listing_service.unlist_vehicle",
      "已下架回庫存"
    );
  }
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
    frm.set_intro("此車輛已上架，可準備銷售。訂金保留與銷售流程尚未開放。", "green");
    return;
  }

  if (frm.doc.status === "保留中") {
    frm.set_intro("此車輛已保留。保留 / 訂金流程將在後續階段處理。", "orange");
    return;
  }

  if (frm.doc.status === "已售出") {
    frm.set_intro("此車輛已售出，不可再進行整備或上架操作。", "green");
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
    frm.set_intro("請先填寫採購車價後再完成入庫。", "orange");
    return;
  }

  frm.set_intro("下一步：按「完成入庫」，系統會自動建立 ERPNext 商品並完成庫存入庫。", "blue");
}

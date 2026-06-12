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
    "建立訂金保留",
    "建立尾款收款",
    "取消保留",
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

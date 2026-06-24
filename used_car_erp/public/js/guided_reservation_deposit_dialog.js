frappe.provide("used_car_erp.guided_reservation_deposit");

(function () {
  const PAYMENT_METHODS = ["現金", "匯款", "信用卡", "其他"];

  function open(frm) {
    if (!frm || !frm.doc || !frm.doc.name) {
      frappe.msgprint("請先開啟有效車輛後再收訂金並保留。");
      return;
    }

    if (!validate_vehicle(frm)) {
      return;
    }

    const dialog = new frappe.ui.Dialog({
      title: "收訂金並保留",
      fields: [
        {
          fieldname: "vehicle_info",
          label: "車輛資訊",
          fieldtype: "Small Text",
          read_only: 1,
          default: get_vehicle_display_text(frm),
        },
        { fieldname: "customer_name", label: "客戶姓名", fieldtype: "Data", reqd: 1 },
        { fieldname: "customer_phone", label: "客戶電話", fieldtype: "Data", reqd: 1 },
        { fieldname: "sold_price", label: "成交價", fieldtype: "Currency", reqd: 1 },
        { fieldname: "deposit_amount", label: "訂金金額", fieldtype: "Currency", reqd: 1 },
        {
          fieldname: "payment_method",
          label: "付款方式",
          fieldtype: "Select",
          options: PAYMENT_METHODS.join("\n"),
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
        { fieldname: "payment_reference", label: "付款備註 / 末五碼", fieldtype: "Data", reqd: 0 },
        { fieldname: "notes", label: "備註", fieldtype: "Small Text", reqd: 0 },
      ],
      primary_action_label: "確認收訂金並保留",
      primary_action(values) {
        if (!validate_values(frm, values)) {
          return;
        }

        create_reservation(frm, dialog, values);
      },
    });

    dialog.show();
  }

  function get_vehicle_display_text(frm) {
    const parts = [frm.doc.stock_no, frm.doc.license_plate, frm.doc.brand, frm.doc.model, frm.doc.name].filter(Boolean);
    return parts.join(" / ");
  }

  function validate_vehicle(frm) {
    if (!frm.doc.name) {
      frappe.msgprint("請先開啟有效車輛後再收訂金並保留。");
      return false;
    }
    if (frm.doc.status !== "上架中") {
      frappe.msgprint("此車目前不是上架中，不能使用「收訂金並保留」。");
      return false;
    }
    if (!is_vehicle_stocked_for_reservation(frm)) {
      frappe.msgprint("此車尚未完成入庫，不能使用「收訂金並保留」。");
      return false;
    }

    return true;
  }

  function is_vehicle_stocked_for_reservation(frm) {
    if (typeof is_vehicle_stocked === "function") {
      return is_vehicle_stocked(frm);
    }

    return Boolean(frm.doc.serial_no && frm.doc.stock_entry);
  }

  function validate_values(frm, values) {
    if (!validate_vehicle(frm)) {
      return false;
    }
    if (!values.customer_name) {
      frappe.msgprint("請填寫客戶姓名。");
      return false;
    }
    if (!values.customer_phone) {
      frappe.msgprint("請填寫客戶電話。");
      return false;
    }
    if (flt(values.sold_price) <= 0) {
      frappe.msgprint("成交價必須大於 0。");
      return false;
    }
    if (flt(values.deposit_amount) <= 0) {
      frappe.msgprint("訂金金額必須大於 0。");
      return false;
    }
    if (flt(values.deposit_amount) > flt(values.sold_price)) {
      frappe.msgprint("訂金不能大於成交價。");
      return false;
    }
    if (!values.payment_method || !PAYMENT_METHODS.includes(values.payment_method)) {
      frappe.msgprint("請選擇付款方式。");
      return false;
    }
    if (!values.deposit_date) {
      frappe.msgprint("請選擇訂金日期。");
      return false;
    }

    return true;
  }

  function create_reservation(frm, dialog, values) {
    frappe.call({
      method: "used_car_erp.used_car_erp.services.vehicle_reservation_service.create_reservation",
      args: {
        vehicle_name: frm.doc.name,
        customer_name: values.customer_name,
        customer_phone: values.customer_phone,
        sold_price: values.sold_price,
        deposit_amount: values.deposit_amount,
        payment_method: values.payment_method,
        deposit_date: values.deposit_date,
        payment_reference: values.payment_reference,
        notes: values.notes,
      },
      freeze: true,
      freeze_message: "正在收訂金並保留...",
      callback() {
        frappe.show_alert({
          message: "已收訂金，車輛已保留",
          indicator: "green",
        });
        dialog.hide();
        frm.reload_doc();
      },
    });
  }

  used_car_erp.guided_reservation_deposit.open = open;
})();

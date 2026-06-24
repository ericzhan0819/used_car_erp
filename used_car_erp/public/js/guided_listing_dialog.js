frappe.provide("used_car_erp.guided_listing");

(function () {
  function open(frm) {
    if (!frm || !frm.doc || !frm.doc.name) {
      frappe.msgprint("請先開啟有效車輛後再上架。");
      return;
    }

    if (frm.doc.status !== "整備中") {
      frappe.msgprint("此車目前不是整備中，不能使用「整備完成並上架」。");
      return;
    }

    const dialog = new frappe.ui.Dialog({
      title: "整備完成並上架",
      fields: [
        {
          fieldname: "vehicle_info",
          label: "車輛資訊",
          fieldtype: "Small Text",
          read_only: 1,
          default: get_vehicle_display_text(frm),
        },
        {
          fieldname: "listing_date",
          label: "上架日期",
          fieldtype: "Date",
          default: frm.doc.listing_date || frappe.datetime.get_today(),
          reqd: 1,
        },
        {
          fieldname: "floor_price",
          label: "底價",
          fieldtype: "Currency",
          default: frm.doc.floor_price,
          reqd: 1,
        },
        {
          fieldname: "asking_price",
          label: "開價",
          fieldtype: "Currency",
          default: frm.doc.asking_price,
          reqd: 1,
        },
        {
          fieldname: "sales_note",
          label: "銷售備註",
          fieldtype: "Small Text",
          default: frm.doc.sales_note,
          reqd: 0,
        },
      ],
      primary_action_label: "確認上架",
      primary_action(values) {
        if (!validate_values(frm, values)) {
          return;
        }

        update_vehicle_listing(frm, dialog, values);
      },
    });

    dialog.show();
  }

  function get_vehicle_display_text(frm) {
    const parts = [frm.doc.stock_no, frm.doc.license_plate, frm.doc.brand, frm.doc.model, frm.doc.name].filter(Boolean);
    return parts.join(" / ");
  }

  function validate_values(frm, values) {
    if (!frm.doc.name) {
      frappe.msgprint("請先開啟有效車輛後再上架。");
      return false;
    }
    if (frm.doc.status !== "整備中") {
      frappe.msgprint("此車目前不是整備中，不能使用「整備完成並上架」。");
      return false;
    }
    if (!values.listing_date) {
      frappe.msgprint("請填寫上架日期。");
      return false;
    }
    if (flt(values.floor_price) <= 0) {
      frappe.msgprint("底價必須大於 0。");
      return false;
    }
    if (flt(values.asking_price) <= 0) {
      frappe.msgprint("開價必須大於 0。");
      return false;
    }
    if (flt(values.asking_price) < flt(values.floor_price)) {
      frappe.msgprint("開價不可低於底價。");
      return false;
    }

    return true;
  }

  function update_vehicle_listing(frm, dialog, values) {
    frappe.call({
      method: "frappe.client.set_value",
      args: {
        doctype: "Used Car Vehicle",
        name: frm.doc.name,
        fieldname: {
          listing_date: values.listing_date,
          floor_price: values.floor_price,
          asking_price: values.asking_price,
          sales_note: values.sales_note,
          status: "上架中",
        },
      },
      freeze: true,
      freeze_message: "正在更新車輛上架資訊...",
      callback() {
        frappe.show_alert({
          message: "車輛已上架",
          indicator: "green",
        });
        dialog.hide();
        frm.reload_doc();
      },
    });
  }

  used_car_erp.guided_listing.open = open;
})();

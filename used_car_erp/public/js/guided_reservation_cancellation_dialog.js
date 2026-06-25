frappe.provide("used_car_erp.guided_reservation_cancellation");

(function () {
  const PAYMENT_METHODS = ["現金", "匯款", "信用卡", "其他"];

  function open(frm) {
    if (!frm || !frm.doc || !frm.doc.name) {
      frappe.msgprint("請先開啟有效車輛後再取消保留。");
      return;
    }

    if (!validate_vehicle(frm)) {
      return;
    }

    get_active_reservation(frm, (active_reservation) => {
      if (!validate_reservation(active_reservation)) {
        return;
      }

      const deposit_posted = is_deposit_posted(active_reservation);
      const dialog = new frappe.ui.Dialog({
        title: "取消保留 / 處理訂金",
        fields: build_fields(frm, active_reservation, deposit_posted),
        primary_action_label: "確認取消保留",
        primary_action(values) {
          if (!validate_values(frm, active_reservation, deposit_posted, values)) {
            return;
          }

          cancel_reservation(frm, dialog, deposit_posted, values);
        },
      });

      dialog.show();
    });
  }

  function build_fields(frm, active_reservation, deposit_posted) {
    const fields = [
      {
        fieldname: "vehicle_info",
        label: "車輛資訊",
        fieldtype: "Small Text",
        read_only: 1,
        default: get_vehicle_display_text(frm),
      },
      {
        fieldname: "customer_info",
        label: "客戶資訊",
        fieldtype: "Small Text",
        read_only: 1,
        default: get_customer_display_text(active_reservation),
      },
      {
        fieldname: "sale_info",
        label: "成交價",
        fieldtype: "Data",
        read_only: 1,
        default: format_dialog_currency(frm.doc.sold_price || 0) || "未填",
      },
      {
        fieldname: "deposit_info",
        label: "訂金金額",
        fieldtype: "Data",
        read_only: 1,
        default: format_dialog_currency(active_reservation.deposit_amount || 0) || "未填",
      },
      {
        fieldname: "deposit_status",
        label: "訂金狀態",
        fieldtype: "Data",
        read_only: 1,
        default: get_business_deposit_status(active_reservation),
      },
      {
        fieldname: "final_status",
        label: "尾款狀態",
        fieldtype: "Data",
        read_only: 1,
        default: get_business_final_status(active_reservation),
      },
      {
        fieldname: "notice",
        label: "處理方式",
        fieldtype: "Small Text",
        read_only: 1,
        default: deposit_posted
          ? "取消保留後，訂金將進入退款內部處理。"
          : "取消保留後，尚未完成的訂金資料會一併取消。",
      },
      {
        fieldname: "reason",
        label: "取消原因",
        fieldtype: "Small Text",
        reqd: 1,
      },
    ];

    if (deposit_posted) {
      fields.push(
        {
          fieldname: "refund_amount",
          label: "退款金額",
          fieldtype: "Currency",
          read_only: 1,
          default: active_reservation.deposit_amount,
        },
        {
          fieldname: "refund_payment_method",
          label: "退款方式",
          fieldtype: "Select",
          options: PAYMENT_METHODS.join("\n"),
          default: "現金",
          reqd: 1,
        },
        {
          fieldname: "settlement_status",
          label: "退款狀態",
          fieldtype: "Select",
          options: "已付款\n待付款",
          default: "已付款",
          reqd: 1,
        },
        {
          fieldname: "cash_account",
          label: "退款資金帳戶",
          fieldtype: "Link",
          options: "Used Car Cash Account",
          reqd: 0,
        },
        {
          fieldname: "refund_date",
          label: "退款日期",
          fieldtype: "Date",
          default: frappe.datetime.get_today(),
          reqd: 1,
        },
        { fieldname: "refund_reference", label: "付款備註 / 末五碼", fieldtype: "Data", reqd: 0 },
        { fieldname: "refund_notes", label: "退款備註", fieldtype: "Small Text", reqd: 0 }
      );
    }

    return fields;
  }

  function get_active_reservation(frm, callback) {
    if (frm._active_reservation) {
      callback(frm._active_reservation);
      return;
    }

    frappe.call({
      method: "used_car_erp.used_car_erp.services.vehicle_reservation_service.get_active_reservation_for_vehicle",
      args: {
        vehicle_name: frm.doc.name,
      },
      freeze: true,
      freeze_message: "正在讀取保留資料...",
      callback(response) {
        frm._active_reservation = response.message || null;
        callback(frm._active_reservation);
      },
      error() {
        frm._active_reservation = null;
        frappe.msgprint("找不到此車輛的有效保留資料，請先確認保留狀態。");
      },
    });
  }

  function get_vehicle_display_text(frm) {
    const parts = [frm.doc.stock_no, frm.doc.license_plate, frm.doc.brand, frm.doc.model, frm.doc.name].filter(Boolean);
    return parts.join(" / ");
  }

  function get_customer_display_text(active_reservation) {
    const parts = [
      active_reservation.customer_name || active_reservation.customer,
      active_reservation.customer_phone,
    ].filter(Boolean);
    return parts.join(" / ") || "未填";
  }

  function get_business_deposit_status(active_reservation) {
    return is_deposit_posted(active_reservation) ? "已完成內部確認" : "內部處理中";
  }

  function get_business_final_status(active_reservation) {
    return active_reservation.final_money_flow || active_reservation.final_voucher_draft ? "已記錄尾款" : "尚未記錄尾款";
  }

  function is_deposit_posted(active_reservation) {
    return Boolean(active_reservation && active_reservation.journal_entry);
  }

  function validate_vehicle(frm) {
    if (!frm.doc.name) {
      frappe.msgprint("請先開啟有效車輛後再取消保留。");
      return false;
    }
    if (frm.doc.status !== "保留中") {
      frappe.msgprint("此車目前不是保留中，不能取消保留。");
      return false;
    }

    return true;
  }

  function validate_reservation(active_reservation) {
    if (!active_reservation) {
      frappe.msgprint("找不到此車輛的有效保留資料，請先確認保留狀態。");
      return false;
    }
    if (active_reservation.final_money_flow || active_reservation.final_voucher_draft) {
      frappe.msgprint("此車已記錄尾款，請先由管理者或會計處理後再取消。");
      return false;
    }

    return true;
  }

  function validate_values(frm, active_reservation, deposit_posted, values) {
    if (!validate_vehicle(frm) || !validate_reservation(active_reservation)) {
      return false;
    }
    if (!values.reason) {
      frappe.msgprint("請填寫取消原因。");
      return false;
    }
    if (deposit_posted) {
      if (flt(values.refund_amount) !== flt(active_reservation.deposit_amount)) {
        frappe.msgprint("退款金額需等於訂金金額。");
        return false;
      }
      if (!values.refund_payment_method || !PAYMENT_METHODS.includes(values.refund_payment_method)) {
        frappe.msgprint("請選擇退款方式。");
        return false;
      }
      if (!values.settlement_status) {
        frappe.msgprint("請選擇退款狀態。");
        return false;
      }
      if (values.settlement_status === "已付款" && !values.cash_account) {
        frappe.msgprint("已退回訂金時需要選擇退款資金帳戶。");
        return false;
      }
      if (!values.refund_date) {
        frappe.msgprint("請選擇退款日期。");
        return false;
      }
    }

    return true;
  }

  function cancel_reservation(frm, dialog, deposit_posted, values) {
    frappe.call({
      method:
        "used_car_erp.used_car_erp.services.vehicle_reservation_service.cancel_active_reservation_with_deposit_handling",
      args: {
        vehicle_name: frm.doc.name,
        reason: values.reason,
        refund_payment_method: deposit_posted ? values.refund_payment_method : undefined,
        refund_date: deposit_posted ? values.refund_date : undefined,
        refund_reference: deposit_posted ? values.refund_reference : undefined,
        refund_notes: deposit_posted ? values.refund_notes : undefined,
        cash_account: deposit_posted ? values.cash_account : undefined,
        settlement_status: deposit_posted ? values.settlement_status : undefined,
      },
      freeze: true,
      freeze_message: "正在取消保留...",
      callback(response) {
        const result = response.message || {};
        frappe.show_alert({
          message: result.refund_required ? "已取消保留，訂金退款待內部確認" : "已取消保留",
          indicator: "green",
        });
        dialog.hide();
        frm.reload_doc();
      },
    });
  }

  function format_dialog_currency(value) {
    if (value === undefined || value === null || value === "") {
      return "";
    }
    if (typeof format_currency === "function") {
      return format_currency(value);
    }
    return String(value);
  }

  used_car_erp.guided_reservation_cancellation.open = open;
})();

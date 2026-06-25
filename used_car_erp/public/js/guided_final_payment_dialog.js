frappe.provide("used_car_erp.guided_final_payment");

(function () {
  const PAYMENT_METHODS = ["現金", "匯款", "信用卡", "其他"];
  const SETTLEMENT_STATUSES = ["已收款", "待收款"];

  function open(frm) {
    if (!frm || !frm.doc || !frm.doc.name) {
      frappe.msgprint("請先開啟有效車輛後再收尾款。");
      return;
    }

    if (!validate_vehicle(frm)) {
      return;
    }

    get_active_reservation(frm, (active_reservation) => {
      if (!validate_reservation(active_reservation)) {
        return;
      }

      const sale_summary = get_sale_summary(frm, active_reservation);

      const dialog = new frappe.ui.Dialog({
        title: "收尾款",
        fields: [
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
            fieldname: "deposit_info",
            label: "訂金資訊",
            fieldtype: "Small Text",
            read_only: 1,
            default: get_deposit_display_text(active_reservation),
          },
          {
            fieldname: "sale_summary",
            label: "收款摘要",
            fieldtype: "Small Text",
            read_only: 1,
            default: get_sale_summary_display_text(sale_summary),
          },
          {
            fieldname: "amount",
            label: "尾款金額",
            fieldtype: "Currency",
            default: sale_summary.suggested_final_payment > 0 ? sale_summary.suggested_final_payment : undefined,
            reqd: 1,
          },
          {
            fieldname: "payment_method",
            label: "付款方式",
            fieldtype: "Select",
            options: PAYMENT_METHODS.join("\n"),
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
            fieldname: "settlement_status",
            label: "收款狀態",
            fieldtype: "Select",
            options: SETTLEMENT_STATUSES.join("\n"),
            default: "已收款",
            reqd: 1,
          },
          {
            fieldname: "cash_account",
            label: "資金帳戶",
            fieldtype: "Link",
            options: "Used Car Cash Account",
            reqd: 0,
          },
          { fieldname: "payment_reference", label: "付款備註 / 末五碼", fieldtype: "Data", reqd: 0 },
          { fieldname: "notes", label: "備註", fieldtype: "Small Text", reqd: 0 },
        ],
        primary_action_label: "確認收尾款",
        primary_action(values) {
          if (!validate_values(frm, active_reservation, values)) {
            return;
          }

          create_final_payment(frm, dialog, values);
        },
      });

      dialog.show();
    });
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

  function get_deposit_display_text(active_reservation) {
    const amount = format_dialog_currency(active_reservation.deposit_amount);
    const parts = [
      amount ? `訂金金額：${amount}` : null,
      active_reservation.deposit_date ? `訂金日期：${active_reservation.deposit_date}` : null,
      active_reservation.payment_method ? `付款方式：${active_reservation.payment_method}` : null,
    ].filter(Boolean);
    return parts.join("\n") || "未填";
  }

  function get_sale_summary(frm, active_reservation) {
    const sold_price = flt(frm.doc.sold_price || 0);
    const deposit_amount = flt(active_reservation.deposit_amount || 0);
    return {
      sold_price,
      deposit_amount,
      suggested_final_payment: Math.max(sold_price - deposit_amount, 0),
    };
  }

  function get_sale_summary_display_text(sale_summary) {
    const parts = [];
    parts.push(
      sale_summary.sold_price > 0
        ? `成交價：${format_dialog_currency(sale_summary.sold_price)}`
        : "成交價：尚未填寫"
    );
    parts.push(
      sale_summary.deposit_amount > 0
        ? `訂金：${format_dialog_currency(sale_summary.deposit_amount)}`
        : "訂金：尚未填寫"
    );
    parts.push(
      sale_summary.sold_price > 0 && sale_summary.deposit_amount > 0
        ? `建議尾款：${format_dialog_currency(sale_summary.suggested_final_payment)}`
        : "建議尾款：成交價或訂金不足，請人工確認"
    );
    return parts.join("\n");
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

  function validate_vehicle(frm) {
    if (!frm.doc.name) {
      frappe.msgprint("請先開啟有效車輛後再收尾款。");
      return false;
    }
    if (frm.doc.status !== "保留中") {
      frappe.msgprint("此車目前不是保留中，不能使用「收尾款」。");
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
      frappe.msgprint("此車已記錄尾款，不能重複收尾款。");
      return false;
    }

    return true;
  }

  function validate_values(frm, active_reservation, values) {
    if (!validate_vehicle(frm) || !validate_reservation(active_reservation)) {
      return false;
    }
    if (flt(values.amount) <= 0) {
      frappe.msgprint("尾款金額必須大於 0。");
      return false;
    }
    if (!values.payment_method || !PAYMENT_METHODS.includes(values.payment_method)) {
      frappe.msgprint("請選擇付款方式。");
      return false;
    }
    if (!values.payment_date) {
      frappe.msgprint("請選擇尾款日期。");
      return false;
    }
    if (!values.settlement_status || !SETTLEMENT_STATUSES.includes(values.settlement_status)) {
      frappe.msgprint("請選擇收款狀態。");
      return false;
    }
    if (values.settlement_status === "已收款" && !values.cash_account) {
      frappe.msgprint("已收款的尾款需要選擇資金帳戶。");
      return false;
    }

    return true;
  }

  function create_final_payment(frm, dialog, values) {
    frappe.call({
      method: "used_car_erp.used_car_erp.services.vehicle_reservation_service.create_final_payment_for_active_reservation",
      args: {
        vehicle_name: frm.doc.name,
        amount: values.amount,
        payment_method: values.payment_method,
        payment_date: values.payment_date,
        settlement_status: values.settlement_status,
        cash_account: values.cash_account,
        payment_reference: values.payment_reference,
        notes: values.notes,
      },
      freeze: true,
      freeze_message: "正在收尾款...",
      callback() {
        frappe.show_alert({
          message: "已收尾款",
          indicator: "green",
        });
        dialog.hide();
        frm.reload_doc();
      },
    });
  }

  used_car_erp.guided_final_payment.open = open;
})();

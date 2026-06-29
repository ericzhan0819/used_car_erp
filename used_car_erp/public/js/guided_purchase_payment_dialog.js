frappe.provide("used_car_erp.guided_purchase_payment");

(function () {
  const PAYMENT_METHODS = ["現金", "匯款", "信用卡", "其他"];
  const SETTLEMENT_STATUSES = ["已付款", "待付款", "部分付款"];

  function open(frm) {
    if (!frm || !frm.doc || !frm.doc.name || frm.is_new()) {
      frappe.msgprint("請先儲存車輛後再新增購車付款。");
      return;
    }

    const dialog = new frappe.ui.Dialog({
      title: "新增購車付款",
      fields: [
        {
          fieldname: "vehicle_info",
          label: "車輛資訊",
          fieldtype: "Small Text",
          read_only: 1,
          default: get_vehicle_display_text(frm),
        },
        {
          fieldname: "purchase_price_info",
          label: "購車價資訊",
          fieldtype: "Small Text",
          read_only: 1,
          default: get_purchase_price_display_text(frm),
        },
        { fieldname: "payment_date", label: "付款日期", fieldtype: "Date", default: frappe.datetime.get_today(), reqd: 1 },
        {
          fieldname: "amount",
          label: "購車付款金額",
          fieldtype: "Currency",
          default: flt(frm.doc.purchase_price) > 0 ? frm.doc.purchase_price : undefined,
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
          fieldname: "settlement_status",
          label: "收付狀態",
          fieldtype: "Select",
          options: SETTLEMENT_STATUSES.join("\n"),
          default: "已付款",
          reqd: 1,
        },
        { fieldname: "cash_account", label: "資金帳戶", fieldtype: "Link", options: "Used Car Cash Account", reqd: 0 },
        { fieldname: "counterparty_name", label: "交易對象", fieldtype: "Data", reqd: 1 },
        { fieldname: "payment_reference", label: "付款備註 / 末五碼", fieldtype: "Data", reqd: 0 },
        { fieldname: "evidence_attachment", label: "憑證附件", fieldtype: "Attach", reqd: 0 },
        { fieldname: "notes", label: "備註", fieldtype: "Small Text", reqd: 0 },
      ],
      primary_action_label: "建立購車付款紀錄",
      primary_action(values) {
        if (!validate_values(frm, values)) {
          return;
        }
        create_purchase_payment_record(frm, dialog, values);
      },
    });

    dialog.show();
  }

  function get_vehicle_display_text(frm) {
    const parts = [frm.doc.stock_no, frm.doc.license_plate, frm.doc.brand, frm.doc.model, frm.doc.name].filter(Boolean);
    return parts.join(" / ");
  }

  function get_purchase_price_display_text(frm) {
    const purchasePrice = flt(frm.doc.purchase_price || 0);
    if (purchasePrice <= 0) {
      return "購車價尚未填寫，請確認付款金額";
    }
    return `購車價：${format_dialog_currency(purchasePrice)}`;
  }

  function validate_values(frm, values) {
    if (!frm.doc.name || frm.is_new()) {
      frappe.msgprint("請先儲存車輛後再新增購車付款。");
      return false;
    }
    if (!values.payment_date) {
      frappe.msgprint("請選擇付款日期。");
      return false;
    }
    if (flt(values.amount) <= 0) {
      frappe.msgprint("購車付款金額必須大於 0。");
      return false;
    }
    if (!values.payment_method || !PAYMENT_METHODS.includes(values.payment_method)) {
      frappe.msgprint("請選擇付款方式。");
      return false;
    }
    if (!values.settlement_status || !SETTLEMENT_STATUSES.includes(values.settlement_status)) {
      frappe.msgprint("請選擇收付狀態。");
      return false;
    }
    if (["已付款", "部分付款"].includes(values.settlement_status) && !values.cash_account) {
      frappe.msgprint("已付款或部分付款的購車付款需要選擇資金帳戶。");
      return false;
    }
    if (!values.counterparty_name) {
      frappe.msgprint("請填寫交易對象。");
      return false;
    }

    return true;
  }

  function create_purchase_payment_record(frm, dialog, values) {
    frappe.call({
      method: "used_car_erp.used_car_erp.services.vehicle_money_flow_service.create_purchase_payment_money_flow",
      args: {
        vehicle: frm.doc.name,
        amount: values.amount,
        payment_date: values.payment_date,
        payment_method: values.payment_method,
        settlement_status: values.settlement_status,
        cash_account: values.cash_account,
        counterparty_name: values.counterparty_name,
        payment_reference: values.payment_reference,
        evidence_attachment: values.evidence_attachment,
        notes: values.notes,
      },
      freeze: true,
      freeze_message: "正在建立購車付款紀錄...",
      callback() {
        frappe.show_alert({
          message: "購車付款紀錄已建立",
          indicator: "green",
        });
        dialog.hide();

        if (typeof render_vehicle_cashflow_inline_summary === "function") {
          render_vehicle_cashflow_inline_summary(frm);
          if (typeof render_vehicle_purchase_payment_inline_summary === "function") {
            render_vehicle_purchase_payment_inline_summary(frm);
          }
          return;
        }

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

  used_car_erp.guided_purchase_payment.open = open;
})();

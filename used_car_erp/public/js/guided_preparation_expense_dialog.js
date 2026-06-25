frappe.provide("used_car_erp.guided_preparation_expense");

(function () {
  const EXPENSE_FLOW_TYPES = ["維修支出", "美容支出", "代辦支出", "拍場支出", "整備支出", "其他支出"];
  const PAYMENT_METHODS = ["現金", "匯款", "信用卡", "其他"];
  const SETTLEMENT_STATUSES = ["已付款", "待付款"];

  function open(frm) {
    if (!frm || !frm.doc || !frm.doc.name) {
      frappe.msgprint("請先開啟有效車輛後再新增支出。");
      return;
    }

    const dialog = new frappe.ui.Dialog({
      title: "新增支出",
      fields: [
        {
          fieldname: "vehicle_info",
          label: "車輛資訊",
          fieldtype: "Small Text",
          read_only: 1,
          default: get_vehicle_display_text(frm),
        },
        { fieldname: "payment_date", label: "支出日期", fieldtype: "Date", default: frappe.datetime.get_today(), reqd: 1 },
        { fieldname: "flow_type", label: "支出類型", fieldtype: "Select", options: EXPENSE_FLOW_TYPES.join("\n"), reqd: 1 },
        { fieldname: "amount", label: "金額", fieldtype: "Currency", reqd: 1 },
        {
          fieldname: "payment_method",
          label: "付款方式",
          fieldtype: "Select",
          options: PAYMENT_METHODS.join("\n"),
          default: "現金",
          reqd: 1,
        },
        {
          fieldname: "counterparty_name",
          label: "交易對象",
          fieldtype: "Data",
          reqd: 0,
          description: "例如維修廠、美容店、代辦、拍場或其他付款對象",
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
        { fieldname: "payment_reference", label: "付款對象 / 付款參考", fieldtype: "Data", reqd: 1 },
        { fieldname: "evidence_attachment", label: "憑證附件", fieldtype: "Attach", reqd: 0 },
        { fieldname: "notes", label: "備註", fieldtype: "Small Text", reqd: 0 },
      ],
      primary_action_label: "建立支出紀錄",
      primary_action(values) {
        if (!validate_values(frm, values)) {
          return;
        }
        create_expense_record(frm, dialog, values);
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
      frappe.msgprint("請先開啟有效車輛後再新增支出。");
      return false;
    }
    if (!values.payment_date) {
      frappe.msgprint("請填寫支出日期。");
      return false;
    }
    if (!values.flow_type) {
      frappe.msgprint("請選擇支出類型。");
      return false;
    }
    if (flt(values.amount) <= 0) {
      frappe.msgprint("金額必須大於 0。");
      return false;
    }
    if (!values.payment_method) {
      frappe.msgprint("請選擇付款方式。");
      return false;
    }
    if (!values.settlement_status) {
      frappe.msgprint("請選擇收付狀態。");
      return false;
    }
    if (values.settlement_status === "已付款" && !values.cash_account) {
      frappe.msgprint("已付款的支出需要選擇資金帳戶。");
      return false;
    }
    if (!values.payment_reference) {
      frappe.msgprint("請填寫付款對象 / 付款參考。");
      return false;
    }
    return true;
  }

  function create_expense_record(frm, dialog, values) {
    frappe.call({
      method: "used_car_erp.used_car_erp.services.vehicle_money_flow_service.create_general_expense_money_flow",
      args: {
        vehicle: frm.doc.name,
        payment_date: values.payment_date,
        flow_type: values.flow_type,
        amount: values.amount,
        payment_method: values.payment_method,
        payment_reference: values.payment_reference,
        cash_account: values.cash_account,
        settlement_status: values.settlement_status,
        counterparty_name: values.counterparty_name,
        notes: values.notes,
        evidence_attachment: values.evidence_attachment,
      },
      freeze: true,
      freeze_message: "正在建立支出紀錄...",
      callback() {
        frappe.show_alert({
          message: "支出紀錄已建立",
          indicator: "green",
        });
        dialog.hide();

        if (typeof render_vehicle_cashflow_inline_summary === "function") {
          render_vehicle_cashflow_inline_summary(frm);
          return;
        }

        frm.reload_doc();
      },
    });
  }

  used_car_erp.guided_preparation_expense.open = open;
})();

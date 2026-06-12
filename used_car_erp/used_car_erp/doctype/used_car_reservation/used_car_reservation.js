frappe.ui.form.on("Used Car Reservation", {
  refresh(frm) {
    frm.set_intro("訂金保留只作為中古車業務保留紀錄，不代表 ERPNext 會計收款憑證。", "blue");

    if (frm.doc.status !== "有效") {
      return;
    }

    if (frm.doc.final_money_flow || frm.doc.final_voucher_draft) {
      frm.set_intro("此保留紀錄已建立尾款金流與傳票草稿，請到「會計作業」確認入帳。", "green");
      frm.add_custom_button("成交前檢查", () => preflight_delivery(frm));
      return;
    }

    frm.add_custom_button("建立尾款收款", () => create_final_payment(frm));
    frm.add_custom_button("成交前檢查", () => preflight_delivery(frm));
  },
});

function create_final_payment(frm) {
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
              "used_car_erp.used_car_erp.services.vehicle_money_flow_service.create_final_payment_money_flow_from_reservation",
            args: {
              reservation_name: frm.doc.name,
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
}

function preflight_delivery(frm) {
  frappe.call({
    method:
      "used_car_erp.used_car_erp.services.vehicle_reservation_service.preflight_delivery_for_active_reservation",
    args: {
      vehicle_name: frm.doc.vehicle,
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
}

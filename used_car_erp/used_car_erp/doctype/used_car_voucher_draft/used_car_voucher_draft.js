frappe.ui.form.on("Used Car Voucher Draft", {
  refresh(frm) {
    frm.set_intro("");

    if (frm.doc.status === "待審核") {
      frm.add_custom_button("確認入帳", () => confirm_voucher_draft(frm));
      frm.add_custom_button("退回草稿", () => reject_voucher_draft(frm));
      frm.add_custom_button("作廢草稿", () => void_voucher_draft(frm));
      return;
    }

    if (frm.doc.status === "已入帳") {
      frm.set_intro("此傳票草稿已正式入帳。", "green");
      return;
    }

    if (frm.doc.status === "已退回") {
      frm.set_intro("此傳票草稿已退回，請會計確認後重新處理。", "orange");
      return;
    }

    if (frm.doc.status === "已作廢") {
      frm.set_intro("此傳票草稿已作廢。", "red");
    }
  },
});

function confirm_voucher_draft(frm) {
  frappe.prompt(
    [
      {
        fieldname: "review_note",
        label: "審核備註",
        fieldtype: "Small Text",
        reqd: 0,
      },
    ],
    (values) => {
      frappe.confirm(
        "確認後將建立正式會計傳票並入帳，請確認借貸科目與金額無誤。是否繼續？",
        () => {
          frappe.call({
            method:
              "used_car_erp.used_car_erp.services.vehicle_voucher_service.confirm_voucher_draft",
            args: {
              voucher_draft_name: frm.doc.name,
              review_note: values.review_note,
            },
            freeze: true,
            freeze_message: "正在確認入帳...",
            callback() {
              frappe.show_alert({ message: "已確認入帳", indicator: "green" });
              frm.reload_doc();
            },
          });
        }
      );
    },
    "確認入帳",
    "確認入帳"
  );
}

function reject_voucher_draft(frm) {
  frappe.prompt(
    [{ fieldname: "reason", label: "退回原因", fieldtype: "Small Text", reqd: 1 }],
    (values) => {
      frappe.call({
        method:
          "used_car_erp.used_car_erp.services.vehicle_voucher_service.reject_voucher_draft",
        args: { voucher_draft_name: frm.doc.name, reason: values.reason },
        freeze: true,
        freeze_message: "正在退回草稿...",
        callback() {
          frappe.show_alert({ message: "已退回傳票草稿。", indicator: "orange" });
          frm.reload_doc();
        },
      });
    },
    "退回草稿",
    "退回草稿"
  );
}

function void_voucher_draft(frm) {
  frappe.prompt(
    [{ fieldname: "reason", label: "作廢原因", fieldtype: "Small Text", reqd: 1 }],
    (values) => {
      frappe.call({
        method:
          "used_car_erp.used_car_erp.services.vehicle_voucher_service.void_voucher_draft",
        args: { voucher_draft_name: frm.doc.name, reason: values.reason },
        freeze: true,
        freeze_message: "正在作廢草稿...",
        callback() {
          frappe.show_alert({ message: "已作廢傳票草稿。", indicator: "red" });
          frm.reload_doc();
        },
      });
    },
    "作廢草稿",
    "作廢草稿"
  );
}

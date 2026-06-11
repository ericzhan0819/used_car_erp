frappe.ui.form.on("Used Car Reservation", {
  refresh(frm) {
    frm.set_intro("訂金保留只作為中古車業務保留紀錄，不代表 ERPNext 會計收款憑證。", "blue");
  },
});

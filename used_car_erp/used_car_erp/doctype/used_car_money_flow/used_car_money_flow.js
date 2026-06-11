frappe.ui.form.on("Used Car Money Flow", {
  refresh(frm) {
    if (frm.doc.status === "已入帳") {
      frm.set_intro("此金流紀錄已完成正式入帳。", "green");
      return;
    }

    if (frm.doc.status === "待審核") {
      frm.set_intro("此金流紀錄已產生傳票草稿，等待會計審核入帳。", "orange");
      return;
    }

    if (frm.doc.status === "已作廢") {
      frm.set_intro("此金流紀錄已作廢，不會建立正式會計傳票。", "red");
    }
  },
});

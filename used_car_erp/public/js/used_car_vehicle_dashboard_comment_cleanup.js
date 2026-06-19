(function () {
  const DUPLICATE_DASHBOARD_COMMENT_PREFIXES = [
    "目前階段：",
    "流程進度：",
    "交車前最終檢查：",
    "正式交車提交狀態",
    "正式交車提交前檢查",
    "成本摘要：",
    "單車損益與預估營業稅：",
  ];

  function is_duplicate_vehicle_dashboard_comment(text) {
    const normalized = String(text || "").trim();
    return DUPLICATE_DASHBOARD_COMMENT_PREFIXES.some((prefix) => normalized.startsWith(prefix));
  }

  function patch_vehicle_dashboard_comment(frm) {
    if (!frm.dashboard || frm._used_car_dashboard_comment_cleanup_applied) {
      return;
    }

    const original_add_comment = frm.dashboard.add_comment.bind(frm.dashboard);
    frm.dashboard.add_comment = function (text, alert_class, permanent) {
      if (is_duplicate_vehicle_dashboard_comment(text)) {
        return;
      }

      return original_add_comment(text, alert_class, permanent);
    };
    frm._used_car_dashboard_comment_cleanup_applied = true;
  }

  function clear_initial_duplicate_dashboard_comment(frm) {
    if (!frm.dashboard || frm.is_new() || frm.doc.status === "保留中") {
      return;
    }

    // The main Used Car Vehicle script may already have rendered a synchronous
    // legacy cost / progress dashboard comment before this cleanup hook runs.
    // The Step 3 summary HTML now owns those read-only numbers and next-step
    // labels, so clear the dashboard headline for non-reserved vehicles only.
    frm.dashboard.clear_comment();
  }

  frappe.ui.form.on("Used Car Vehicle", {
    refresh(frm) {
      patch_vehicle_dashboard_comment(frm);
      clear_initial_duplicate_dashboard_comment(frm);
    },
  });
})();

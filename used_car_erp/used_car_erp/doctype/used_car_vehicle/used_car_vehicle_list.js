frappe.listview_settings["Used Car Vehicle"] = {
  add_fields: [
    "status",
    "stock_no",
    "license_plate",
    "brand",
    "model",
    "year",
    "mileage_km",
    "asking_price",
    "purchase_price",
    "branch_location",
  ],

  onload(listview) {
    listview.page.add_inner_button("新增買入車輛", () => {
      if (!used_car_erp.guided_vehicle_intake || !used_car_erp.guided_vehicle_intake.open_dialog) {
        frappe.msgprint("新增買入車輛表單尚未載入，請重新整理後再試。");
        return;
      }

      used_car_erp.guided_vehicle_intake.open_dialog();
    });
  },

  get_indicator(doc) {
    const status = doc.status || "草稿";
    const status_map = {
      草稿: "gray",
      庫存中: "blue",
      整備中: "orange",
      上架中: "green",
      保留中: "yellow",
      已售出: "grey",
      封存: "red",
    };

    return [status, status_map[status] || "gray", `status,=,${status}`];
  },
};

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

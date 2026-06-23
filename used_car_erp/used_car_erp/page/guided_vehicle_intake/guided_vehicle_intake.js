frappe.pages["guided-vehicle-intake"].on_page_load = function (wrapper) {
  const page = frappe.ui.make_app_page({
    parent: wrapper,
    title: "新增買入車輛",
    single_column: true,
  });

  const state = {
    dialog_opened: false,
  };

  const $body = $(page.body);
  $body.html(`
    <div class="guided-vehicle-intake" style="padding: 16px;">
      <div class="frappe-card" style="padding: 16px; margin-bottom: 12px;">
        <div style="font-weight: 600; margin-bottom: 4px;">新增買入車輛</div>
        <div class="text-muted" style="font-size: 12px; line-height: 1.7;">
          請依步驟填寫車輛基本資料與收購資料。
        </div>
      </div>
    </div>
  `);

  const open_dialog = () => {
    if (state.dialog_opened) {
      return;
    }
    state.dialog_opened = true;
    show_guided_vehicle_intake_step_1(null, state);
  };

  page.set_primary_action("開始新增", open_dialog, "add");
  setTimeout(open_dialog, 200);
};

function show_guided_vehicle_intake_step_1(existing_values, state) {
  const dialog = new frappe.ui.Dialog({
    title: "新增車輛 - 車輛基本資料",
    fields: [
      {
        fieldname: "brand",
        label: "廠牌",
        fieldtype: "Data",
      },
      {
        fieldname: "model",
        label: "車型",
        fieldtype: "Data",
      },
      {
        fieldname: "year",
        label: "年式",
        fieldtype: "Int",
      },
      {
        fieldname: "license_plate",
        label: "車牌",
        fieldtype: "Data",
      },
      {
        fieldname: "vin",
        label: "VIN / 車身號碼",
        fieldtype: "Data",
        reqd: 1,
      },
      {
        fieldname: "mileage",
        label: "里程",
        fieldtype: "Int",
      },
      {
        fieldname: "color",
        label: "顏色",
        fieldtype: "Data",
      },
    ],
    primary_action_label: "下一步",
    primary_action(values) {
      if (!values.vin) {
        frappe.msgprint("請先填寫 VIN / 車身號碼。");
        return;
      }

      dialog.hide();
      show_guided_vehicle_intake_step_2(values, state);
    },
  });

  dialog.onhide = () => {
    if (state) {
      state.dialog_opened = false;
    }
  };

  dialog.set_values(existing_values || {});
  dialog.show();
}

function show_guided_vehicle_intake_step_2(vehicle_values, state) {
  const dialog = new frappe.ui.Dialog({
    title: "新增車輛 - 收購資料",
    fields: [
      {
        fieldname: "purchase_price",
        label: "購車價",
        fieldtype: "Currency",
        reqd: 1,
      },
      {
        fieldname: "purchase_source_type",
        label: "買入來源",
        fieldtype: "Select",
        options: "個人\n同行\n拍賣場\n其他",
        default: "個人",
      },
      {
        fieldname: "seller",
        label: "客戶 / 原車主",
        fieldtype: "Data",
      },
      {
        fieldname: "purchase_staff",
        label: "收購業務",
        fieldtype: "Link",
        options: "User",
      },
      {
        fieldname: "tax_flags_section",
        label: "監理 / 稅務確認",
        fieldtype: "Section Break",
      },
      {
        fieldname: "license_tax_paid",
        label: "牌照稅已繳",
        fieldtype: "Check",
      },
      {
        fieldname: "fuel_tax_paid",
        label: "燃料稅已繳",
        fieldtype: "Check",
      },
      {
        fieldname: "has_unpaid_loan",
        label: "有未清償貸款",
        fieldtype: "Check",
      },
      {
        fieldname: "has_tax_penalty",
        label: "有欠稅 / 罰款",
        fieldtype: "Check",
      },
      {
        fieldname: "tax_flags_column",
        fieldtype: "Column Break",
      },
      {
        fieldname: "registration_restricted",
        label: "禁止異動",
        fieldtype: "Check",
      },
      {
        fieldname: "insurance_cancelled",
        label: "動保已註銷",
        fieldtype: "Check",
      },
      {
        fieldname: "plate_cancelled",
        label: "已繳銷牌照",
        fieldtype: "Check",
      },
      {
        fieldname: "need_document_check",
        label: "需要證件確認",
        fieldtype: "Check",
      },
    ],
    primary_action_label: "建立車輛",
    primary_action(values) {
      if (flt(values.purchase_price) <= 0) {
        frappe.msgprint("請先填寫有效的購車價。");
        return;
      }

      values.purchase_source_type = values.purchase_source_type || "個人";
      create_guided_vehicle_intake(dialog, vehicle_values, values);
    },
    secondary_action_label: "返回上一步",
    secondary_action() {
      dialog.hide();
      if (state) {
        state.dialog_opened = true;
      }
      show_guided_vehicle_intake_step_1(vehicle_values, state);
    },
  });

  dialog.onhide = () => {
    if (state) {
      state.dialog_opened = false;
    }
  };

  dialog.set_value("purchase_source_type", "個人");
  dialog.show();
}

function create_guided_vehicle_intake(dialog, vehicle_values, purchase_values) {
  const payload = {
    brand: vehicle_values.brand,
    model: vehicle_values.model,
    year: vehicle_values.year,
    license_plate: vehicle_values.license_plate,
    vin: vehicle_values.vin,
    mileage: vehicle_values.mileage,
    color: vehicle_values.color,
    purchase_price: purchase_values.purchase_price,
    purchase_source_type: purchase_values.purchase_source_type || "個人",
    seller: purchase_values.seller,
    original_owner_name: purchase_values.seller,
    purchase_staff: purchase_values.purchase_staff,
    license_tax_paid: purchase_values.license_tax_paid,
    fuel_tax_paid: purchase_values.fuel_tax_paid,
    has_unpaid_loan: purchase_values.has_unpaid_loan,
    has_tax_penalty: purchase_values.has_tax_penalty,
    registration_restricted: purchase_values.registration_restricted,
    insurance_cancelled: purchase_values.insurance_cancelled,
    plate_cancelled: purchase_values.plate_cancelled,
    need_document_check: purchase_values.need_document_check,
  };

  frappe.call({
    method:
      "used_car_erp.used_car_erp.services.guided_vehicle_intake_service.run_guided_vehicle_intake",
    args: {
      payload: JSON.stringify(payload),
    },
    freeze: true,
    freeze_message: "正在建立車輛...",
    callback(response) {
      const result = response.message || {};
      const route = result.route;
      const vehicle_name = result.vehicle;

      frappe.show_alert({
        message: result.message || "車輛已建立並進入整備中",
        indicator: "green",
      });
      dialog.hide();

      if (Array.isArray(route) && route.length) {
        frappe.set_route(...route);
        return;
      }
      if (vehicle_name) {
        frappe.set_route("Form", "Used Car Vehicle", vehicle_name);
      }
    },
  });
}

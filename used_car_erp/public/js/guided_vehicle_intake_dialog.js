frappe.provide("used_car_erp.guided_vehicle_intake");

(function () {
  function open_step_1(existing_values) {
    const dialog = new frappe.ui.Dialog({
      title: "新增車輛 - 車輛基本資料",
      fields: [
        { fieldname: "brand", label: "廠牌", fieldtype: "Data" },
        { fieldname: "model", label: "車型", fieldtype: "Data" },
        { fieldname: "variant_trim", label: "車款等級", fieldtype: "Data" },
        { fieldname: "year", label: "年式", fieldtype: "Int" },
        { fieldname: "license_plate", label: "車牌", fieldtype: "Data" },
        { fieldname: "vin", label: "VIN / 車身號碼", fieldtype: "Data", reqd: 1 },
        { fieldname: "engine_no", label: "引擎號碼", fieldtype: "Data" },
        { fieldname: "mileage_km", label: "里程", fieldtype: "Int" },
        { fieldname: "color", label: "外觀顏色", fieldtype: "Data" },
        { fieldname: "interior_color", label: "內裝顏色", fieldtype: "Data" },
      ],
      primary_action_label: "下一步",
      primary_action(values) {
        if (!values.vin) {
          frappe.msgprint("請先填寫 VIN / 車身號碼。");
          return;
        }

        dialog.hide();
        open_step_2(values);
      },
    });

    dialog.set_values(existing_values || {});
    dialog.show();
  }

  function open_step_2(vehicle_values, existing_values) {
    const dialog = new frappe.ui.Dialog({
      title: "新增車輛 - 車籍 / 規格資料",
      fields: [
        { fieldname: "manufacture_date", label: "出廠日期", fieldtype: "Date" },
        { fieldname: "license_date", label: "領牌日期", fieldtype: "Date" },
        { fieldname: "fuel_type", label: "燃料類型", fieldtype: "Select", options: "\n汽油\n柴油\n油電\n電動\n其他" },
        { fieldname: "engine_cc", label: "排氣量 CC", fieldtype: "Float" },
        { fieldname: "transmission", label: "變速系統", fieldtype: "Select", options: "\n自排\n手排\nCVT\n其他" },
        { fieldname: "specs_column", fieldtype: "Column Break" },
        { fieldname: "drivetrain", label: "驅動方式", fieldtype: "Select", options: "\n2WD\n前驅\n後驅\nAWD\n4WD\n其他" },
        { fieldname: "doors", label: "車門數", fieldtype: "Int" },
        { fieldname: "seats", label: "座位數", fieldtype: "Int" },
      ],
      primary_action_label: "下一步",
      primary_action(values) {
        dialog.hide();
        open_step_3(vehicle_values, values);
      },
      secondary_action_label: "返回上一步",
      secondary_action() {
        dialog.hide();
        open_step_1(vehicle_values);
      },
    });

    dialog.set_values(existing_values || {});
    dialog.show();
  }

  function open_step_3(vehicle_values, specs_values, existing_values) {
    const dialog = new frappe.ui.Dialog({
      title: "新增車輛 - 收購資料",
      fields: [
        { fieldname: "purchase_price", label: "購車價", fieldtype: "Currency", reqd: 1 },
        { fieldname: "purchase_source_type", label: "買入來源", fieldtype: "Select", options: "個人\n同行\n拍賣場\n其他", default: "個人" },
        { fieldname: "seller", label: "客戶 / 原車主", fieldtype: "Data" },
        { fieldname: "original_owner_phone", label: "原車主電話", fieldtype: "Data" },
        { fieldname: "purchase_staff", label: "收購業務", fieldtype: "Link", options: "User" },
        { fieldname: "purchase_date", label: "收購日期", fieldtype: "Date" },
        { fieldname: "purchase_document_no", label: "買入憑證號碼 / 備註", fieldtype: "Data" },
        { fieldname: "purchase_note", label: "收購備註", fieldtype: "Small Text" },
        { fieldname: "purchase_column", fieldtype: "Column Break" },
        { fieldname: "purchase_type", label: "採購類型", fieldtype: "Select", options: "\n公司買進\n委售\n客戶換購\n拍賣\n其他" },
        { fieldname: "source", label: "來源", fieldtype: "Select", options: "\n來店\n介紹\n網路\n車商\n客戶換購\n拍賣\n其他" },
        { fieldname: "expected_received_date", label: "預計進車日期", fieldtype: "Date" },
        { fieldname: "received_date", label: "實際進車日期", fieldtype: "Date" },
        { fieldname: "referral_name", label: "介紹人姓名", fieldtype: "Data" },
        { fieldname: "referral_phone", label: "介紹人電話", fieldtype: "Data" },
      ],
      primary_action_label: "下一步",
      primary_action(values) {
        if (flt(values.purchase_price) <= 0) {
          frappe.msgprint("請先填寫有效的購車價。");
          return;
        }

        values.purchase_source_type = values.purchase_source_type || "個人";
        dialog.hide();
        open_step_4(vehicle_values, specs_values, values);
      },
      secondary_action_label: "返回上一步",
      secondary_action() {
        dialog.hide();
        open_step_2(vehicle_values, specs_values);
      },
    });

    dialog.set_values(Object.assign({ purchase_source_type: "個人" }, existing_values || {}));
    dialog.show();
  }

  function open_step_4(vehicle_values, specs_values, purchase_values, existing_values) {
    const dialog = new frappe.ui.Dialog({
      title: "新增車輛 - 稅費 / 監理狀態",
      fields: [
        { fieldname: "license_tax_paid", label: "牌照稅已繳", fieldtype: "Check" },
        { fieldname: "fuel_tax_paid", label: "燃料稅已繳", fieldtype: "Check" },
        { fieldname: "has_unpaid_loan", label: "有未清償貸款", fieldtype: "Check" },
        { fieldname: "has_tax_penalty", label: "有欠稅 / 罰款", fieldtype: "Check" },
        { fieldname: "tax_flags_column", fieldtype: "Column Break" },
        { fieldname: "registration_restricted", label: "禁止異動", fieldtype: "Check" },
        { fieldname: "insurance_cancelled", label: "動保已註銷", fieldtype: "Check" },
        { fieldname: "plate_cancelled", label: "已繳銷牌照", fieldtype: "Check" },
        { fieldname: "need_document_check", label: "需要證件確認", fieldtype: "Check" },
        { fieldname: "dates_section", label: "到期日與備註", fieldtype: "Section Break" },
        { fieldname: "license_tax_due_date", label: "牌照稅到期日", fieldtype: "Date" },
        { fieldname: "fuel_tax_due_date", label: "燃料稅到期日", fieldtype: "Date" },
        { fieldname: "insurance_expiry_date", label: "保險到期日", fieldtype: "Date" },
        { fieldname: "registration_note", label: "監理 / 稅務備註", fieldtype: "Small Text" },
        { fieldname: "notes", label: "備註", fieldtype: "Small Text" },
      ],
      primary_action_label: "建立車輛",
      primary_action(values) {
        create_guided_vehicle_intake(dialog, vehicle_values, specs_values, purchase_values, values);
      },
      secondary_action_label: "返回上一步",
      secondary_action() {
        dialog.hide();
        open_step_3(vehicle_values, specs_values, purchase_values);
      },
    });

    dialog.set_values(existing_values || {});
    dialog.show();
  }

  function create_guided_vehicle_intake(dialog, vehicle_values, specs_values, purchase_values, registration_values) {
    const payload = Object.assign({}, vehicle_values, specs_values, purchase_values, registration_values, {
      mileage: vehicle_values.mileage_km,
      purchase_source_type: purchase_values.purchase_source_type || "個人",
      seller: purchase_values.seller,
      original_owner_name: purchase_values.seller,
    });

    frappe.call({
      method: "used_car_erp.used_car_erp.services.guided_vehicle_intake_service.run_guided_vehicle_intake",
      args: { payload: JSON.stringify(payload) },
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

  used_car_erp.guided_vehicle_intake.open_dialog = function () {
    open_step_1();
  };

  used_car_erp.guided_vehicle_intake.open = used_car_erp.guided_vehicle_intake.open_dialog;
})();

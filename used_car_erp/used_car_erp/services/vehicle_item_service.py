import frappe


class VehicleItemService:
	def create_item_for_vehicle(self, vehicle_name: str):
		vehicle = frappe.get_doc("Used Car Vehicle", vehicle_name)
		vehicle.check_permission("write")

		if vehicle.item:
			return {
				"item": vehicle.item,
				"created": False,
				"message": "此車輛已連結既有 ERPNext 商品。",
			}

		if not vehicle.stock_no:
			frappe.throw("車輛必須先儲存並取得系統車輛編號，才能建立 ERPNext 商品。")

		if frappe.db.exists("Item", vehicle.stock_no):
			self._link_vehicle_item(vehicle, vehicle.stock_no)
			return {
				"item": vehicle.stock_no,
				"created": False,
				"message": "已連結既有 ERPNext 商品。",
			}

		item = frappe.get_doc(self._build_item_doc(vehicle)).insert()
		self._link_vehicle_item(vehicle, item.name)

		return {
			"item": item.name,
			"created": True,
			"message": "已建立 ERPNext 商品並連結至車輛。",
		}

	def _build_item_doc(self, vehicle):
		item_doc = {
			"doctype": "Item",
			"item_code": vehicle.stock_no,
			"item_name": self._build_item_name(vehicle),
			"item_group": self._get_item_group(),
			"stock_uom": self._get_stock_uom(),
			"is_stock_item": 1,
			"description": self._build_description(vehicle),
		}

		item_meta = frappe.get_meta("Item")
		if item_meta.has_field("has_serial_no"):
			# 中古車需預留 VIN/序號能力，但實際 Serial No 必須跟正式入庫一起建立，避免無庫存序號。
			item_doc["has_serial_no"] = 1
		if item_meta.has_field("serial_no_series"):
			# 只設定未來入庫可用的序號規則，本 service 不建立 Serial No document。
			item_doc["serial_no_series"] = f"{vehicle.stock_no}-.###"

		return item_doc

	def _link_vehicle_item(self, vehicle, item_name: str):
		# 只回寫 Item link，避免影響 stock_no、狀態、序號或後續進銷存欄位。
		vehicle.db_set("item", item_name)

	def _build_item_name(self, vehicle):
		parts = [vehicle.brand, vehicle.model, vehicle.year, vehicle.license_plate]
		item_name = " ".join(str(part).strip() for part in parts if part)
		return item_name or vehicle.stock_no

	def _build_description(self, vehicle):
		parts = [
			f"車輛編號：{vehicle.stock_no}",
			f"廠牌：{vehicle.brand}" if vehicle.brand else None,
			f"車型：{vehicle.model}" if vehicle.model else None,
			f"年式：{vehicle.year}" if vehicle.year else None,
			f"車牌：{vehicle.license_plate}" if vehicle.license_plate else None,
			f"VIN：{vehicle.vin}" if vehicle.vin else None,
		]
		return "<br>".join(part for part in parts if part)

	def _get_item_group(self):
		for item_group in ("Products", "產品"):
			if frappe.db.exists("Item Group", {"name": item_group, "is_group": 0}):
				return item_group

		item_group = frappe.db.get_value("Item Group", {"is_group": 0}, "name", order_by="name asc")
		if not item_group:
			frappe.throw("找不到可用的 Item Group，請先建立非群組 Item Group。")

		return item_group

	def _get_stock_uom(self):
		for stock_uom in ("Nos", "NOS", "Unit"):
			if frappe.db.exists("UOM", stock_uom):
				return stock_uom

		stock_uom = frappe.db.get_value("UOM", {}, "name", order_by="name asc")
		if not stock_uom:
			frappe.throw("找不到可用的 UOM，請先建立 UOM。")

		return stock_uom


@frappe.whitelist()
def create_item_for_vehicle(vehicle_name: str):
	service = VehicleItemService()
	return service.create_item_for_vehicle(vehicle_name)


def verify_vehicle_item_service():
	service = VehicleItemService()
	vehicle = None
	item_name = None
	stock_no = None
	verification = {}

	try:
		vehicle = frappe.get_doc(
			{
				"doctype": "Used Car Vehicle",
				"brand": "Toyota",
				"model": "Altis",
				"year": 2020,
				"license_plate": "VERIFY-ITEM",
				"vin": f"VERIFY-ITEM-{frappe.generate_hash(length=10)}",
			}
		).insert()
		stock_no = vehicle.stock_no

		purchase_invoice_count = frappe.db.count("Purchase Invoice")
		sales_invoice_count = frappe.db.count("Sales Invoice")

		result = service.create_item_for_vehicle(vehicle.name)
		item_name = result.get("item")

		vehicle.reload()
		serial_no_created = bool(frappe.db.exists("Serial No", {"item_code": item_name}))

		if not item_name:
			frappe.throw("Vehicle Item Service did not return an Item.")
		if not frappe.db.exists("Item", item_name):
			frappe.throw("Vehicle Item Service did not create or link an existing Item.")
		if vehicle.item != item_name:
			frappe.throw("Used Car Vehicle.item was not linked to the created Item.")
		if vehicle.stock_no != stock_no:
			frappe.throw("Used Car Vehicle.stock_no was changed unexpectedly.")
		if vehicle.serial_no:
			frappe.throw("Used Car Vehicle.serial_no should remain empty in this foundation step.")
		if serial_no_created:
			frappe.throw("Serial No should not be created by Vehicle Item Service.")
		if frappe.db.count("Purchase Invoice") != purchase_invoice_count:
			frappe.throw("Purchase Invoice should not be created by Vehicle Item Service.")
		if frappe.db.count("Sales Invoice") != sales_invoice_count:
			frappe.throw("Sales Invoice should not be created by Vehicle Item Service.")

		verification = {
			"vehicle_name": vehicle.name,
			"stock_no": stock_no,
			"item": item_name,
			"item_created": result.get("created"),
			"vehicle_item_linked": vehicle.item == item_name,
			"serial_no_created": False,
		}
	finally:
		try:
			if vehicle and frappe.db.exists("Used Car Vehicle", vehicle.name):
				frappe.db.set_value("Used Car Vehicle", vehicle.name, "item", None)
				frappe.delete_doc("Used Car Vehicle", vehicle.name, force=True)
			if item_name and frappe.db.exists("Item", item_name):
				frappe.delete_doc("Item", item_name, force=True)
			frappe.db.commit()
		except Exception as exc:
			frappe.db.rollback()
			frappe.throw(f"Vehicle Item Service verification cleanup failed: {exc}")

	verification["cleaned_up"] = True
	return verification

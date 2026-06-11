import frappe
from frappe.utils import flt

from used_car_erp.used_car_erp.services.vehicle_item_service import VehicleItemService
from used_car_erp.used_car_erp.services.vehicle_stock_service import VehicleStockService


class VehicleIntakeService:
	def complete_intake(self, vehicle_name: str):
		vehicle = frappe.get_doc("Used Car Vehicle", vehicle_name)
		vehicle.check_permission("write")

		if vehicle.stock_entry:
			return self._already_completed_response(vehicle, "此車輛已完成入庫，不會重複建立 Stock Entry。")
		if vehicle.serial_no:
			return self._already_completed_response(vehicle, "此車輛已有 ERPNext 序號，不會重複建立入庫資料。")

		self._validate_vehicle_ready_for_intake(vehicle)
		default_warehouse_applied = self._apply_default_stock_warehouse_if_missing(vehicle)

		item_result = {"item": vehicle.item, "created": False}
		if not vehicle.item:
			item_result = VehicleItemService().create_item_for_vehicle(vehicle.name)

		vehicle.reload()
		stock_result = VehicleStockService().stock_in_vehicle(vehicle.name)
		vehicle.reload()

		return {
			"item": vehicle.item,
			"stock_entry": vehicle.stock_entry,
			"serial_no": vehicle.serial_no,
			"status": vehicle.status,
			"item_created": bool(item_result.get("created")),
			"stock_created": bool(stock_result.get("created")),
			"created": bool(stock_result.get("created")),
			"default_warehouse_applied": default_warehouse_applied,
			"message": stock_result.get("message") or "已完成車輛入庫。",
		}

	def _validate_vehicle_ready_for_intake(self, vehicle):
		if not vehicle.vin:
			frappe.throw("車輛必須填寫車身號碼 / VIN，才能完成入庫。")
		if flt(vehicle.purchase_price) <= 0:
			frappe.throw("車輛採購車價必須大於 0，才能完成入庫。")
		if vehicle.status in ("已售出", "封存"):
			frappe.throw("已售出或封存車輛不可完成入庫。")

	def _apply_default_stock_warehouse_if_missing(self, vehicle):
		if vehicle.stock_warehouse:
			return False

		warehouse = self._resolve_default_stock_warehouse()
		# 缺少入庫倉庫時才補預設值，避免覆寫使用者已指定的 Warehouse。
		vehicle.db_set("stock_warehouse", warehouse)
		vehicle.stock_warehouse = warehouse
		return True

	def _resolve_default_stock_warehouse(self):
		preferred_warehouse = "商店 - O"
		if frappe.db.exists(
			"Warehouse",
			{"name": preferred_warehouse, "is_group": 0, "account": ["is", "set"]},
		):
			return preferred_warehouse

		warehouse = frappe.db.get_value(
			"Warehouse",
			{"is_group": 0, "account": ["is", "set"]},
			"name",
			order_by="name asc",
		)
		if not warehouse:
			frappe.throw("找不到已綁定庫存科目的入庫倉庫，請先設定 Warehouse Account。")

		return warehouse

	def _already_completed_response(self, vehicle, message: str):
		return {
			"item": vehicle.item,
			"stock_entry": vehicle.stock_entry,
			"serial_no": vehicle.serial_no,
			"status": vehicle.status,
			"item_created": False,
			"stock_created": False,
			"created": False,
			"default_warehouse_applied": False,
			"message": message,
		}


@frappe.whitelist()
def complete_intake(vehicle_name: str):
	service = VehicleIntakeService()
	return service.complete_intake(vehicle_name)


def verify_vehicle_intake_service():
	service = VehicleIntakeService()
	vehicle = None
	item_name = None
	stock_entry_name = None
	serial_no = None
	item_existed_before = False
	serial_existed_before = False
	verification = {"cleaned_up": False}

	purchase_invoice_count = frappe.db.count("Purchase Invoice")
	sales_invoice_count = frappe.db.count("Sales Invoice")
	payment_entry_count = frappe.db.count("Payment Entry")

	try:
		vehicle = frappe.get_doc(
			{
				"doctype": "Used Car Vehicle",
				"brand": "Toyota",
				"model": "Altis",
				"year": 2020,
				"license_plate": "VERIFY-INTAKE",
				"vin": f"VERIFY-INTAKE-{frappe.generate_hash(length=10)}",
				"purchase_price": 300000,
			}
		).insert()
		stock_no = vehicle.stock_no
		item_existed_before = bool(frappe.db.exists("Item", stock_no))
		serial_existed_before = bool(frappe.db.exists("Serial No", vehicle.vin))

		result = service.complete_intake(vehicle.name)
		item_name = result.get("item")
		stock_entry_name = result.get("stock_entry")
		serial_no = result.get("serial_no")

		vehicle.reload()
		stock_entry = frappe.get_doc("Stock Entry", stock_entry_name)

		if not vehicle.item or vehicle.item != item_name:
			frappe.throw("Vehicle Intake Service verification did not create and write back Item.")
		if not vehicle.stock_warehouse:
			frappe.throw("Vehicle Intake Service verification did not apply default stock warehouse.")
		if not stock_entry_name or stock_entry.docstatus != 1:
			frappe.throw("Vehicle Intake Service verification did not submit Stock Entry.")
		if not serial_no or vehicle.serial_no != serial_no:
			frappe.throw("Vehicle Intake Service verification did not write back Serial No.")
		if vehicle.status != "庫存中":
			frappe.throw("Vehicle Intake Service verification did not update status to 庫存中.")
		if frappe.db.count("Purchase Invoice") != purchase_invoice_count:
			frappe.throw("Vehicle Intake Service must not create Purchase Invoice.")
		if frappe.db.count("Sales Invoice") != sales_invoice_count:
			frappe.throw("Vehicle Intake Service must not create Sales Invoice.")
		if frappe.db.count("Payment Entry") != payment_entry_count:
			frappe.throw("Vehicle Intake Service must not create Payment Entry.")

		verification = {
			"vehicle_name": vehicle.name,
			"stock_no": stock_no,
			"item": item_name,
			"stock_warehouse": vehicle.stock_warehouse,
			"stock_entry": stock_entry_name,
			"serial_no": serial_no,
			"status": vehicle.status,
			"item_created": result.get("item_created"),
			"stock_entry_submitted": stock_entry.docstatus == 1,
			"serial_no_created": bool(frappe.db.exists("Serial No", serial_no)),
			"default_warehouse_applied": result.get("default_warehouse_applied"),
			"cleaned_up": False,
		}
	finally:
		try:
			stock_entry_cancelled = False
			if stock_entry_name and frappe.db.exists("Stock Entry", stock_entry_name):
				stock_entry = frappe.get_doc("Stock Entry", stock_entry_name)
				if stock_entry.docstatus == 1:
					stock_entry.cancel()
					stock_entry_cancelled = True
				elif stock_entry.docstatus == 0:
					frappe.delete_doc("Stock Entry", stock_entry_name, force=True)
					stock_entry_cancelled = True
			if vehicle and frappe.db.exists("Used Car Vehicle", vehicle.name):
				frappe.db.set_value(
					"Used Car Vehicle",
					vehicle.name,
					{"serial_no": None, "stock_entry": None, "item": None},
				)
				frappe.delete_doc("Used Car Vehicle", vehicle.name, force=True)
			if stock_entry_cancelled and not serial_existed_before and serial_no and frappe.db.exists("Serial No", serial_no):
				try:
					frappe.delete_doc("Serial No", serial_no, force=True)
				except Exception:
					# 已取消庫存仍可能保留序號歷史，清理不得繞過 ERPNext 標準完整性限制。
					verification["serial_no_cleanup_skipped"] = True
			if stock_entry_cancelled and not item_existed_before and item_name and frappe.db.exists("Item", item_name):
				try:
					frappe.delete_doc("Item", item_name, force=True)
				except Exception:
					# Item 若被已取消庫存紀錄引用，保留標準限制並回報，不使用破壞性 SQL。
					verification["item_cleanup_skipped"] = True
			frappe.db.commit()
			verification["cleaned_up"] = True
		except Exception as exc:
			frappe.db.rollback()
			frappe.throw(f"Vehicle Intake Service verification cleanup failed: {exc}")

	return verification

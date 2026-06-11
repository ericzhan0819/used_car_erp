import frappe

from used_car_erp.used_car_erp.services.vehicle_intake_service import VehicleIntakeService


class VehicleListingService:
	BLOCKED_STATUSES = ("草稿", "保留中", "已售出", "封存")

	def start_preparation(self, vehicle_name: str):
		vehicle = self._get_vehicle_for_listing_action(vehicle_name)
		if vehicle.status != "庫存中":
			frappe.throw("只有庫存中車輛可以開始整備。")

		return self._set_status(vehicle, "整備中", "車輛已進入整備中。")

	def list_vehicle(self, vehicle_name: str):
		vehicle = self._get_vehicle_for_listing_action(vehicle_name)
		if vehicle.status not in ("庫存中", "整備中"):
			frappe.throw("只有庫存中或整備中車輛可以上架。")

		return self._set_status(vehicle, "上架中", "車輛已上架，可準備銷售。")

	def unlist_vehicle(self, vehicle_name: str):
		vehicle = self._get_vehicle_for_listing_action(vehicle_name)
		if vehicle.status != "上架中":
			frappe.throw("只有上架中車輛可以下架回庫存。")

		return self._set_status(vehicle, "庫存中", "車輛已下架並回到庫存中。")

	def _get_vehicle_for_listing_action(self, vehicle_name: str):
		vehicle = frappe.get_doc("Used Car Vehicle", vehicle_name)
		vehicle.check_permission("write")
		self._validate_vehicle_can_change_listing_status(vehicle)
		self._validate_stocked_vehicle(vehicle)
		return vehicle

	def _validate_vehicle_can_change_listing_status(self, vehicle):
		if vehicle.is_new():
			frappe.throw("車輛必須先儲存，才能進行整備或上架操作。")
		if vehicle.status in self.BLOCKED_STATUSES:
			frappe.throw("此車輛狀態不可進行整備或上架操作。")

	def _validate_stocked_vehicle(self, vehicle):
		if not vehicle.item or not vehicle.serial_no or not vehicle.stock_entry:
			frappe.throw("此車輛尚未完成入庫，不能進行整備或上架操作。")

	def _set_status(self, vehicle, new_status: str, message: str):
		previous_status = vehicle.status
		changed = previous_status != new_status
		if changed:
			# Listing 階段只允許更新 Used Car Vehicle 狀態，避免誤動 ERPNext 庫存、序號或會計資料。
			vehicle.db_set("status", new_status)
			vehicle.reload()

		return {
			"vehicle_name": vehicle.name,
			"stock_no": vehicle.stock_no,
			"previous_status": previous_status,
			"status": vehicle.status,
			"changed": changed,
			"message": message,
		}


@frappe.whitelist()
def start_preparation(vehicle_name: str):
	service = VehicleListingService()
	return service.start_preparation(vehicle_name)


@frappe.whitelist()
def list_vehicle(vehicle_name: str):
	service = VehicleListingService()
	return service.list_vehicle(vehicle_name)


@frappe.whitelist()
def unlist_vehicle(vehicle_name: str):
	service = VehicleListingService()
	return service.unlist_vehicle(vehicle_name)


def verify_vehicle_listing_service():
	service = VehicleListingService()
	vehicle = None
	item_name = None
	stock_entry_name = None
	serial_no = None
	item_existed_before = False
	serial_existed_before = False
	verification = {"cleaned_up": False}

	try:
		vehicle = frappe.get_doc(
			{
				"doctype": "Used Car Vehicle",
				"brand": "Toyota",
				"model": "Altis",
				"year": 2020,
				"license_plate": "VERIFY-LISTING",
				"vin": f"VERIFY-LISTING-{frappe.generate_hash(length=10)}",
				"purchase_price": 300000,
			}
		).insert()
		stock_no = vehicle.stock_no
		item_existed_before = bool(frappe.db.exists("Item", stock_no))
		serial_existed_before = bool(frappe.db.exists("Serial No", vehicle.vin))

		intake_result = VehicleIntakeService().complete_intake(vehicle.name)
		item_name = intake_result.get("item")
		stock_entry_name = intake_result.get("stock_entry")
		serial_no = intake_result.get("serial_no")
		vehicle.reload()

		if vehicle.status != "庫存中":
			frappe.throw("Vehicle Listing Service verification requires initial status 庫存中 after intake.")

		before_counts = _listing_verification_doc_counts()
		transitions = []

		transitions.append(service.start_preparation(vehicle.name))
		vehicle.reload()
		if vehicle.status != "整備中":
			frappe.throw("Vehicle Listing Service verification did not update status to 整備中.")

		transitions.append(service.list_vehicle(vehicle.name))
		vehicle.reload()
		if vehicle.status != "上架中":
			frappe.throw("Vehicle Listing Service verification did not update status to 上架中.")

		transitions.append(service.unlist_vehicle(vehicle.name))
		vehicle.reload()
		if vehicle.status != "庫存中":
			frappe.throw("Vehicle Listing Service verification did not return status to 庫存中.")

		transitions.append(service.list_vehicle(vehicle.name))
		vehicle.reload()
		if vehicle.status != "上架中":
			frappe.throw("Vehicle Listing Service verification did not allow direct listing from 庫存中.")

		after_counts = _listing_verification_doc_counts()
		if after_counts != before_counts:
			frappe.throw("Vehicle Listing Service must not create stock, sales, payment, delivery, or accounting documents.")

		verification = {
			"vehicle_name": vehicle.name,
			"stock_no": stock_no,
			"item": item_name,
			"serial_no": serial_no,
			"stock_entry": stock_entry_name,
			"transitions": transitions,
			"stock_entry_count_unchanged_after_listing": after_counts["Stock Entry"] == before_counts["Stock Entry"],
			"purchase_invoice_count_unchanged": after_counts["Purchase Invoice"] == before_counts["Purchase Invoice"],
			"sales_invoice_count_unchanged": after_counts["Sales Invoice"] == before_counts["Sales Invoice"],
			"payment_entry_count_unchanged": after_counts["Payment Entry"] == before_counts["Payment Entry"],
			"delivery_note_count_unchanged": after_counts["Delivery Note"] == before_counts["Delivery Note"],
			"journal_entry_count_unchanged": after_counts["Journal Entry"] == before_counts["Journal Entry"],
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
					# 已取消 Stock Entry 仍可能留下序號歷史，清理不得繞過 ERPNext 標準限制。
					verification["serial_no_cleanup_skipped"] = True
			if stock_entry_cancelled and not item_existed_before and item_name and frappe.db.exists("Item", item_name):
				try:
					frappe.delete_doc("Item", item_name, force=True)
				except Exception:
					# Item 若已被庫存歷史引用，保留標準完整性限制並回報，不使用破壞性 SQL。
					verification["item_cleanup_skipped"] = True
			frappe.db.commit()
			verification["cleaned_up"] = True
		except Exception as exc:
			frappe.db.rollback()
			frappe.throw(f"Vehicle Listing Service verification cleanup failed: {exc}")

	return verification


def _listing_verification_doc_counts():
	return {
		"Stock Entry": frappe.db.count("Stock Entry"),
		"Purchase Invoice": frappe.db.count("Purchase Invoice"),
		"Sales Invoice": frappe.db.count("Sales Invoice"),
		"Payment Entry": frappe.db.count("Payment Entry"),
		"Delivery Note": frappe.db.count("Delivery Note"),
		"Journal Entry": frappe.db.count("Journal Entry"),
	}

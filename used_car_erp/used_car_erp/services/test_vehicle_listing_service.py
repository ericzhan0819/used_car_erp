import frappe
from frappe.tests.utils import FrappeTestCase

from used_car_erp.used_car_erp.services.vehicle_intake_service import VehicleIntakeService
from used_car_erp.used_car_erp.services.vehicle_item_service import VehicleItemService
from used_car_erp.used_car_erp.services.vehicle_listing_service import VehicleListingService


class TestVehicleListingService(FrappeTestCase):
	def setUp(self):
		self.service = VehicleListingService()
		self.intake_service = VehicleIntakeService()
		self.item_service = VehicleItemService()
		self.created_vehicles = []
		self.created_items = []
		self.created_stock_entries = []
		self.created_serial_nos = []

	def tearDown(self):
		for stock_entry_name in reversed(self.created_stock_entries):
			if frappe.db.exists("Stock Entry", stock_entry_name):
				stock_entry = frappe.get_doc("Stock Entry", stock_entry_name)
				if stock_entry.docstatus == 1:
					stock_entry.cancel()

		for vehicle_name in reversed(self.created_vehicles):
			if frappe.db.exists("Used Car Vehicle", vehicle_name):
				frappe.db.set_value(
					"Used Car Vehicle",
					vehicle_name,
					{"serial_no": None, "stock_entry": None, "item": None},
				)
				frappe.delete_doc("Used Car Vehicle", vehicle_name, force=True)

		for serial_no in reversed(self.created_serial_nos):
			if frappe.db.exists("Serial No", serial_no):
				try:
					frappe.delete_doc("Serial No", serial_no, force=True)
				except Exception:
					pass

		for item_name in reversed(self.created_items):
			if frappe.db.exists("Item", item_name):
				try:
					frappe.delete_doc("Item", item_name, force=True)
				except Exception:
					pass

		frappe.db.commit()

	def test_start_preparation_allows_stocked_to_preparation(self):
		vehicle = self._make_stocked_vehicle()
		result = self.service.start_preparation(vehicle.name)
		vehicle.reload()

		self.assertTrue(result.get("changed"))
		self.assertEqual(result.get("previous_status"), "庫存中")
		self.assertEqual(vehicle.status, "整備中")

	def test_list_vehicle_allows_preparation_to_listed(self):
		vehicle = self._make_stocked_vehicle()
		self.service.start_preparation(vehicle.name)

		result = self.service.list_vehicle(vehicle.name)
		vehicle.reload()

		self.assertTrue(result.get("changed"))
		self.assertEqual(result.get("previous_status"), "整備中")
		self.assertEqual(vehicle.status, "上架中")

	def test_list_vehicle_allows_stocked_to_listed(self):
		vehicle = self._make_stocked_vehicle()
		result = self.service.list_vehicle(vehicle.name)
		vehicle.reload()

		self.assertTrue(result.get("changed"))
		self.assertEqual(result.get("previous_status"), "庫存中")
		self.assertEqual(vehicle.status, "上架中")

	def test_unlist_vehicle_allows_listed_to_stocked(self):
		vehicle = self._make_stocked_vehicle()
		self.service.list_vehicle(vehicle.name)

		result = self.service.unlist_vehicle(vehicle.name)
		vehicle.reload()

		self.assertTrue(result.get("changed"))
		self.assertEqual(result.get("previous_status"), "上架中")
		self.assertEqual(vehicle.status, "庫存中")

	def test_draft_vehicle_cannot_start_preparation(self):
		vehicle = self._make_vehicle(status="草稿")
		self.item_service.create_item_for_vehicle(vehicle.name)
		vehicle.reload()
		frappe.db.set_value(
			"Used Car Vehicle",
			vehicle.name,
			{"serial_no": vehicle.vin, "stock_entry": "TEST-STOCK-ENTRY"},
		)

		self.assertRaises(frappe.ValidationError, self.service.start_preparation, vehicle.name)

	def test_unstocked_vehicle_cannot_be_listed(self):
		vehicle = self._make_vehicle()
		self.assertRaises(frappe.ValidationError, self.service.list_vehicle, vehicle.name)

	def test_reserved_sold_and_archived_vehicles_cannot_operate(self):
		for status in ("保留中", "已售出", "封存"):
			vehicle = self._make_stocked_vehicle()
			frappe.db.set_value("Used Car Vehicle", vehicle.name, "status", status)
			self.assertRaises(frappe.ValidationError, self.service.list_vehicle, vehicle.name)

	def test_listing_workflow_does_not_create_stock_entry(self):
		vehicle = self._make_stocked_vehicle()
		before_count = frappe.db.count("Stock Entry")

		self.service.start_preparation(vehicle.name)
		self.service.list_vehicle(vehicle.name)
		self.service.unlist_vehicle(vehicle.name)

		self.assertEqual(frappe.db.count("Stock Entry"), before_count)

	def test_listing_workflow_does_not_create_sales_payment_delivery_or_journal_documents(self):
		vehicle = self._make_stocked_vehicle()
		before_counts = self._restricted_doc_counts()

		self.service.start_preparation(vehicle.name)
		self.service.list_vehicle(vehicle.name)
		self.service.unlist_vehicle(vehicle.name)

		self.assertEqual(self._restricted_doc_counts(), before_counts)

	def _make_vehicle(self, **overrides):
		vehicle_data = {
			"doctype": "Used Car Vehicle",
			"brand": "Toyota",
			"model": "Altis",
			"year": 2020,
			"license_plate": f"TST-LIST-{frappe.generate_hash(length=6)}",
			"vin": f"TST-LIST-{frappe.generate_hash(length=10)}",
			"purchase_price": 300000,
		}
		vehicle_data.update(overrides)
		vehicle = frappe.get_doc(vehicle_data).insert()
		self.created_vehicles.append(vehicle.name)
		return vehicle

	def _make_stocked_vehicle(self):
		vehicle = self._make_vehicle()
		result = self.intake_service.complete_intake(vehicle.name)
		self._track_intake_result(result)
		vehicle.reload()
		return vehicle

	def _track_intake_result(self, result):
		if result.get("stock_entry"):
			self.created_stock_entries.append(result.get("stock_entry"))
		if result.get("serial_no"):
			self.created_serial_nos.append(result.get("serial_no"))
		if result.get("item"):
			self.created_items.append(result.get("item"))

	def _restricted_doc_counts(self):
		return {
			"Sales Invoice": frappe.db.count("Sales Invoice"),
			"Payment Entry": frappe.db.count("Payment Entry"),
			"Delivery Note": frappe.db.count("Delivery Note"),
			"Journal Entry": frappe.db.count("Journal Entry"),
		}

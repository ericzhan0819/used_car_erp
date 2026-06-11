import frappe
from frappe.tests.utils import FrappeTestCase

from used_car_erp.used_car_erp.services.vehicle_intake_service import VehicleIntakeService


class TestVehicleIntakeService(FrappeTestCase):
	def setUp(self):
		self.service = VehicleIntakeService()
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

	def test_complete_intake_creates_item_when_vehicle_item_is_empty(self):
		vehicle = self._make_vehicle()
		result = self.service.complete_intake(vehicle.name)
		self._track_result(result)
		vehicle.reload()

		self.assertTrue(result.get("item_created"))
		self.assertTrue(vehicle.item)
		self.assertTrue(frappe.db.exists("Item", vehicle.item))

	def test_complete_intake_applies_default_warehouse_when_empty(self):
		vehicle = self._make_vehicle()
		result = self.service.complete_intake(vehicle.name)
		self._track_result(result)
		vehicle.reload()

		self.assertTrue(result.get("default_warehouse_applied"))
		self.assertTrue(vehicle.stock_warehouse)

	def test_complete_intake_stocks_in_and_writes_links_and_status(self):
		vehicle = self._make_vehicle()
		result = self.service.complete_intake(vehicle.name)
		self._track_result(result)
		vehicle.reload()

		self.assertTrue(result.get("stock_created"))
		self.assertEqual(vehicle.stock_entry, result.get("stock_entry"))
		self.assertEqual(vehicle.serial_no, result.get("serial_no"))
		self.assertEqual(vehicle.status, "庫存中")
		self.assertEqual(frappe.db.get_value("Stock Entry", vehicle.stock_entry, "docstatus"), 1)
		self.assertEqual(frappe.db.get_value("Serial No", vehicle.serial_no, "item_code"), vehicle.item)

	def test_complete_intake_does_not_repeat_for_stocked_vehicle(self):
		vehicle = self._make_vehicle()
		first = self.service.complete_intake(vehicle.name)
		self._track_result(first)

		second = self.service.complete_intake(vehicle.name)
		self.assertFalse(second.get("stock_created"))
		self.assertFalse(second.get("created"))
		self.assertEqual(second.get("stock_entry"), first.get("stock_entry"))

	def test_complete_intake_requires_vin(self):
		vehicle = self._make_vehicle(vin=None)
		self.assertRaises(frappe.ValidationError, self.service.complete_intake, vehicle.name)

	def test_complete_intake_requires_positive_purchase_price(self):
		for purchase_price in (None, 0):
			vehicle = self._make_vehicle(purchase_price=purchase_price)
			self.assertRaises(frappe.ValidationError, self.service.complete_intake, vehicle.name)

	def test_complete_intake_rejects_sold_or_archived_vehicle(self):
		for status in ("已售出", "封存"):
			vehicle = self._make_vehicle(status=status)
			self.assertRaises(frappe.ValidationError, self.service.complete_intake, vehicle.name)

	def test_complete_intake_does_not_create_financial_documents(self):
		before_counts = self._financial_doc_counts()
		vehicle = self._make_vehicle()
		result = self.service.complete_intake(vehicle.name)
		self._track_result(result)

		self.assertEqual(self._financial_doc_counts(), before_counts)

	def _make_vehicle(self, **overrides):
		vehicle_data = {
			"doctype": "Used Car Vehicle",
			"brand": "Toyota",
			"model": "Altis",
			"year": 2020,
			"license_plate": f"TST-INTAKE-{frappe.generate_hash(length=6)}",
			"vin": f"TST-INTAKE-{frappe.generate_hash(length=10)}",
			"purchase_price": 300000,
		}
		vehicle_data.update(overrides)
		vehicle = frappe.get_doc(vehicle_data).insert()
		self.created_vehicles.append(vehicle.name)
		return vehicle

	def _track_result(self, result):
		if result.get("stock_entry"):
			self.created_stock_entries.append(result.get("stock_entry"))
		if result.get("serial_no"):
			self.created_serial_nos.append(result.get("serial_no"))
		if result.get("item"):
			self.created_items.append(result.get("item"))

	def _financial_doc_counts(self):
		return {
			"Purchase Invoice": frappe.db.count("Purchase Invoice"),
			"Sales Invoice": frappe.db.count("Sales Invoice"),
			"Payment Entry": frappe.db.count("Payment Entry"),
		}

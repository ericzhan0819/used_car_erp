import frappe
from frappe.tests.utils import FrappeTestCase

from used_car_erp.used_car_erp.services.vehicle_item_service import VehicleItemService
from used_car_erp.used_car_erp.services.vehicle_stock_service import VehicleStockService


class TestVehicleStockService(FrappeTestCase):
	def setUp(self):
		self.service = VehicleStockService()
		self.item_service = VehicleItemService()
		self.created_vehicles = []
		self.created_items = []
		self.created_stock_entries = []
		self.created_serial_nos = []
		self.warehouse = frappe.db.get_value("Warehouse", {"is_group": 0}, "name", order_by="name asc")

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
				frappe.delete_doc("Item", item_name, force=True)

		frappe.db.commit()

	def test_stock_in_vehicle_requires_item(self):
		vehicle = self._make_vehicle(create_item=False)
		self.assertRaises(frappe.ValidationError, self.service.stock_in_vehicle, vehicle.name)

	def test_stock_in_vehicle_requires_vin(self):
		vehicle = self._make_vehicle(vin=None)
		self.assertRaises(frappe.ValidationError, self.service.stock_in_vehicle, vehicle.name)

	def test_stock_in_vehicle_requires_stock_warehouse(self):
		vehicle = self._make_vehicle(stock_warehouse=None)
		self.assertRaises(frappe.ValidationError, self.service.stock_in_vehicle, vehicle.name)

	def test_stock_in_vehicle_requires_positive_purchase_price(self):
		vehicle = self._make_vehicle(purchase_price=0)
		self.assertRaises(frappe.ValidationError, self.service.stock_in_vehicle, vehicle.name)

	def test_stock_in_vehicle_rejects_sold_or_archived_vehicle(self):
		for status in ("已售出", "封存"):
			vehicle = self._make_vehicle(status=status)
			self.assertRaises(frappe.ValidationError, self.service.stock_in_vehicle, vehicle.name)

	def test_successful_stock_in_writes_links_and_status(self):
		before_counts = self._financial_doc_counts()
		vehicle = self._make_vehicle()

		result = self.service.stock_in_vehicle(vehicle.name)
		self._track_stock_result(result)

		vehicle.reload()
		self.assertTrue(result.get("created"))
		self.assertEqual(vehicle.serial_no, vehicle.vin)
		self.assertEqual(vehicle.stock_entry, result.get("stock_entry"))
		self.assertEqual(vehicle.status, "庫存中")
		self.assertEqual(frappe.db.get_value("Stock Entry", result.get("stock_entry"), "docstatus"), 1)
		self.assertEqual(frappe.db.get_value("Serial No", vehicle.vin, "item_code"), vehicle.item)
		self.assertEqual(self._financial_doc_counts(), before_counts)

	def test_repeated_call_does_not_create_duplicate_stock_entry(self):
		vehicle = self._make_vehicle()
		first = self.service.stock_in_vehicle(vehicle.name)
		self._track_stock_result(first)

		second = self.service.stock_in_vehicle(vehicle.name)
		self.assertFalse(second.get("created"))
		self.assertEqual(second.get("stock_entry"), first.get("stock_entry"))

	def test_stock_in_does_not_create_financial_documents(self):
		before_counts = self._financial_doc_counts()
		vehicle = self._make_vehicle()
		result = self.service.stock_in_vehicle(vehicle.name)
		self._track_stock_result(result)
		self.assertEqual(self._financial_doc_counts(), before_counts)

	def _make_vehicle(self, create_item=True, **overrides):
		if not self.warehouse and overrides.get("stock_warehouse", self.warehouse) is not None:
			frappe.throw("找不到可用的非群組 Warehouse，無法建立入庫測試資料。")

		vehicle_data = {
			"doctype": "Used Car Vehicle",
			"brand": "Toyota",
			"model": "Altis",
			"year": 2020,
			"license_plate": f"TST-STOCK-{frappe.generate_hash(length=6)}",
			"vin": f"TST-STOCK-{frappe.generate_hash(length=10)}",
			"purchase_price": 300000,
			"stock_warehouse": self.warehouse,
		}
		vehicle_data.update(overrides)
		vehicle = frappe.get_doc(vehicle_data).insert()
		self.created_vehicles.append(vehicle.name)

		if create_item:
			result = self.item_service.create_item_for_vehicle(vehicle.name)
			self.created_items.append(result.get("item"))
			vehicle.reload()

		return vehicle

	def _track_stock_result(self, result):
		if result.get("stock_entry"):
			self.created_stock_entries.append(result.get("stock_entry"))
		if result.get("serial_no"):
			self.created_serial_nos.append(result.get("serial_no"))

	def _financial_doc_counts(self):
		return {
			"Purchase Invoice": frappe.db.count("Purchase Invoice"),
			"Sales Invoice": frappe.db.count("Sales Invoice"),
			"Payment Entry": frappe.db.count("Payment Entry"),
		}

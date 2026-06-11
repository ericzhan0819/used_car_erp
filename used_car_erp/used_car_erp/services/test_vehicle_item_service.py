import frappe
from frappe.tests.utils import FrappeTestCase

from used_car_erp.used_car_erp.services.vehicle_item_service import VehicleItemService


class TestVehicleItemService(FrappeTestCase):
	def setUp(self):
		self.service = VehicleItemService()
		self.item_names = set()

	def tearDown(self):
		for vehicle_name in frappe.get_all(
			"Used Car Vehicle",
			filters={"vin": ["like", "TEST-ITEM-SERVICE-%"]},
			pluck="name",
		):
			vehicle = frappe.get_doc("Used Car Vehicle", vehicle_name)
			if vehicle.item:
				frappe.db.set_value("Used Car Vehicle", vehicle.name, "item", None)
			frappe.delete_doc("Used Car Vehicle", vehicle.name, force=True)

		for item_name in self.item_names:
			if frappe.db.exists("Item", item_name) and not frappe.db.exists(
				"Used Car Vehicle", {"item": item_name}
			):
				frappe.delete_doc("Item", item_name, force=True)

	def test_create_item_for_vehicle_creates_item_and_links_vehicle(self):
		vehicle = self._create_vehicle()

		result = self.service.create_item_for_vehicle(vehicle.name)
		self.item_names.add(result["item"])
		vehicle.reload()

		self.assertTrue(result["created"])
		self.assertTrue(result["item"])
		self.assertTrue(frappe.db.exists("Item", result["item"]))
		self.assertEqual(vehicle.item, result["item"])
		self.assertEqual(vehicle.stock_no, result["item"])

	def test_repeated_call_does_not_create_second_item(self):
		vehicle = self._create_vehicle()
		first_result = self.service.create_item_for_vehicle(vehicle.name)
		self.item_names.add(first_result["item"])

		second_result = self.service.create_item_for_vehicle(vehicle.name)

		self.assertFalse(second_result["created"])
		self.assertEqual(second_result["item"], first_result["item"])
		self.assertEqual(frappe.db.count("Item", {"item_code": vehicle.stock_no}), 1)

	def test_existing_item_is_linked_when_vehicle_item_is_empty(self):
		vehicle = self._create_vehicle()
		item = self._create_item(vehicle.stock_no)
		self.item_names.add(item.name)

		result = self.service.create_item_for_vehicle(vehicle.name)
		self.item_names.add(result["item"])
		vehicle.reload()

		self.assertFalse(result["created"])
		self.assertEqual(result["item"], item.name)
		self.assertEqual(vehicle.item, item.name)

	def test_service_does_not_create_serial_or_invoices(self):
		vehicle = self._create_vehicle()
		purchase_invoice_count = frappe.db.count("Purchase Invoice")
		sales_invoice_count = frappe.db.count("Sales Invoice")

		result = self.service.create_item_for_vehicle(vehicle.name)
		vehicle.reload()

		self.assertFalse(frappe.db.exists("Serial No", {"item_code": result["item"]}))
		self.assertFalse(vehicle.serial_no)
		self.assertEqual(frappe.db.count("Purchase Invoice"), purchase_invoice_count)
		self.assertEqual(frappe.db.count("Sales Invoice"), sales_invoice_count)

	def _create_vehicle(self):
		return frappe.get_doc(
			{
				"doctype": "Used Car Vehicle",
				"brand": "Toyota",
				"model": "Altis",
				"year": 2020,
				"license_plate": "TEST-ITEM",
				"vin": f"TEST-ITEM-SERVICE-{frappe.generate_hash(length=10)}",
			}
		).insert()

	def _create_item(self, item_code):
		return frappe.get_doc(
			{
				"doctype": "Item",
				"item_code": item_code,
				"item_name": item_code,
				"item_group": self.service._get_item_group(),
				"stock_uom": self.service._get_stock_uom(),
				"is_stock_item": 1,
			}
		).insert()

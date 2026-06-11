import frappe
from frappe.tests.utils import FrappeTestCase


class TestUsedCarVehicle(FrappeTestCase):
	def tearDown(self):
		frappe.delete_doc_if_exists("Used Car Vehicle", "TEST-VEHICLE-001", force=True)

	def test_create_vehicle_uses_stock_no_and_default_status(self):
		frappe.delete_doc_if_exists("Used Car Vehicle", "TEST-VEHICLE-001", force=True)

		vehicle = frappe.get_doc(
			{
				"doctype": "Used Car Vehicle",
				"stock_no": "TEST-VEHICLE-001",
				"vin": "TEST-VIN-001",
			}
		).insert()

		self.assertEqual(vehicle.name, "TEST-VEHICLE-001")
		self.assertEqual(vehicle.status, "Draft")
